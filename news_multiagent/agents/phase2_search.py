"""
Phase 2 Search Agent for Category Gap Searches

Performs targeted web searches to fill gaps in news coverage using
category-specific queries with Claude Computer Use tools.
"""

import asyncio
import json
import structlog
from typing import Dict, List
from anthropic import AsyncAnthropic

from ..config.settings import get_settings
from ..prompts.source_scraper_prompt import generate_category_search_prompt
from ..utils.logging_config import LoggingMixin

logger = structlog.get_logger(__name__)


class Phase2SearchAgent(LoggingMixin):
    """
    Specialized agent for executing category-based gap searches.

    Uses web_search and web_fetch to find articles in specific categories
    that may not be covered by primary source scraping.
    """

    def __init__(
        self,
        search_config: Dict,
        cutoff_date: str,
        today: str,
        max_retries: int = 3
    ):
        """
        Initialize Phase 2 search agent.

        Args:
            search_config: Search configuration with query, category, target_count
            cutoff_date: Earliest acceptable article date (YYYY-MM-DD)
            today: Current date (YYYY-MM-DD)
            max_retries: Maximum retry attempts
        """
        self.search_config = search_config
        self.cutoff_date = cutoff_date
        self.today = today
        self.max_retries = max_retries

        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        self.logger = logger.bind(
            search_name=search_config["name"],
            query=search_config["query"],
            category=search_config["category"]
        )

    async def search(self) -> List[Dict]:
        """
        Execute category-specific search for maritime news gaps.

        Returns:
            List of validated article dictionaries
        """
        self.log_operation_start(
            "category_search",
            search_name=self.search_config["name"],
            query=self.search_config["query"]
        )

        for attempt in range(self.max_retries):
            try:
                # Generate search prompt
                prompt = generate_category_search_prompt(
                    search_config=self.search_config,
                    cutoff_date=self.cutoff_date,
                    today=self.today
                )

                # Call Claude with Computer Use tools
                response = await self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,
                    temperature=0.1,
                    tools=[
                        {
                            "name": "web_search",
                            "description": "Search the web for information",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "web_fetch",
                            "description": "Fetch content from a URL",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string", "description": "URL to fetch"}
                                },
                                "required": ["url"]
                            }
                        }
                    ],
                    messages=[{"role": "user", "content": prompt}]
                )

                # Extract articles from response
                articles = self._extract_articles_from_response(response)

                # Validate articles
                validated_articles = []
                for article in articles:
                    if await self._validate_article(article):
                        validated_articles.append(article)

                self.log_operation_success(
                    "category_search",
                    articles_found=len(validated_articles),
                    attempt=attempt + 1
                )

                return validated_articles

            except Exception as e:
                self.log_operation_error(
                    "category_search",
                    e,
                    attempt=attempt + 1
                )

                if attempt == self.max_retries - 1:
                    self.logger.error("All search retry attempts exhausted")
                    return []

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return []

    def _extract_articles_from_response(self, response) -> List[Dict]:
        """
        Extract article data from Claude's search response.

        Args:
            response: Anthropic API response

        Returns:
            List of article dictionaries
        """
        try:
            content = response.content[0].text

            # Find JSON array in response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                articles = json.loads(json_str)

                self.logger.debug(
                    "Extracted articles from search response",
                    raw_count=len(articles)
                )

                return articles

        except (json.JSONDecodeError, IndexError, AttributeError) as e:
            self.logger.error(
                "Failed to extract articles from search response",
                error=str(e),
                response_preview=str(response)[:200]
            )

        return []

    async def _validate_article(self, article: Dict) -> bool:
        """
        Validate search result article.

        Args:
            article: Article dictionary to validate

        Returns:
            True if article is valid
        """
        try:
            # Check required fields
            required_fields = ["url", "title", "date", "category", "severity"]
            for field in required_fields:
                if not article.get(field):
                    self.logger.debug(
                        "Search article missing required field",
                        field=field,
                        url=article.get("url", "unknown")
                    )
                    return False

            # Ensure article matches expected category
            expected_category = self.search_config["category"]
            if article["category"] != expected_category:
                self.logger.debug(
                    "Article category mismatch",
                    expected=expected_category,
                    actual=article["category"],
                    url=article["url"]
                )
                # Allow but warn - Claude might have better categorization

            # Validate date range
            from ..utils.date_utils import is_date_in_range
            article_date = article["date"]
            if not is_date_in_range(article_date, self.cutoff_date, self.today):
                self.logger.debug(
                    "Search article date out of range",
                    article_date=article_date,
                    cutoff_date=self.cutoff_date,
                    today=self.today,
                    url=article["url"]
                )
                return False

            return True

        except Exception as e:
            self.logger.error(
                "Search article validation error",
                error=str(e),
                article_url=article.get("url", "unknown")
            )
            return False