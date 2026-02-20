"""
Source Scraper Agent using Claude Sonnet 4 with Computer Use

Scrapes individual news sources using Claude's web_search and web_fetch tools
for systematic article extraction and validation.
"""

import asyncio
import json
import structlog
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic
from datetime import datetime

from ..config.settings import get_settings
from ..prompts.source_scraper_prompt import generate_scraping_prompt
from ..utils.date_utils import parse_article_date, is_date_in_range

logger = structlog.get_logger(__name__)


class SourceScraperAgent:
    """
    Specialized agent for scraping individual news sources using Claude Computer Use.

    Uses web_search and web_fetch tools to systematically extract and validate
    maritime news articles from specified sources.
    """

    def __init__(
        self,
        source_config: Dict,
        cutoff_date: str,
        today: str,
        max_retries: int = 3
    ):
        """
        Initialize the source scraper agent.

        Args:
            source_config: Configuration with name, homepage, target_count
            cutoff_date: Earliest acceptable article date (YYYY-MM-DD)
            today: Current date (YYYY-MM-DD)
            max_retries: Maximum retry attempts for failed operations
        """
        self.source_config = source_config
        self.cutoff_date = cutoff_date
        self.today = today
        self.max_retries = max_retries

        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        self.logger = logger.bind(
            source=source_config["name"],
            homepage=source_config["homepage"],
            target_count=source_config["target_count"]
        )

    async def scrape(self) -> List[Dict]:
        """
        Execute systematic scraping of the assigned news source.

        Returns:
            List of validated article dictionaries
        """
        self.logger.info("Starting source scraping", source=self.source_config["name"])

        for attempt in range(self.max_retries):
            try:
                # Generate systematic scraping prompt
                prompt = generate_scraping_prompt(
                    source_config=self.source_config,
                    cutoff_date=self.cutoff_date,
                    today=self.today
                )

                # Call Claude with Computer Use tools
                response = await self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # Latest available model
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

                # Validate and filter articles
                validated_articles = []
                for article in articles:
                    if await self._validate_article(article):
                        validated_articles.append(article)

                self.logger.info(
                    "Source scraping completed",
                    articles_found=len(validated_articles),
                    attempt=attempt + 1
                )

                return validated_articles

            except Exception as e:
                self.logger.error(
                    "Source scraping failed",
                    error=str(e),
                    attempt=attempt + 1,
                    exc_info=True
                )

                if attempt == self.max_retries - 1:
                    self.logger.error("All retry attempts exhausted")
                    return []

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return []

    def _extract_articles_from_response(self, response) -> List[Dict]:
        """
        Extract article data from Claude's response.

        Args:
            response: Anthropic API response

        Returns:
            List of article dictionaries
        """
        try:
            # Look for JSON in the response content
            content = response.content[0].text

            # Find JSON array in response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                articles = json.loads(json_str)

                self.logger.debug(
                    "Extracted articles from response",
                    raw_count=len(articles)
                )

                return articles

        except (json.JSONDecodeError, IndexError, AttributeError) as e:
            self.logger.error(
                "Failed to extract articles from response",
                error=str(e),
                response_preview=str(response)[:200]
            )

        return []

    async def _validate_article(self, article: Dict) -> bool:
        """
        Validate article data and date range.

        Args:
            article: Article dictionary to validate

        Returns:
            True if article is valid and in date range
        """
        try:
            # Check required fields
            required_fields = ["url", "title", "date", "source", "category", "severity"]
            for field in required_fields:
                if not article.get(field):
                    self.logger.debug(
                        "Article missing required field",
                        field=field,
                        url=article.get("url", "unknown")
                    )
                    return False

            # Validate date range
            article_date = article["date"]
            if not is_date_in_range(article_date, self.cutoff_date, self.today):
                self.logger.debug(
                    "Article date out of range",
                    article_date=article_date,
                    cutoff_date=self.cutoff_date,
                    today=self.today,
                    url=article["url"]
                )
                return False

            # Validate category
            from ..graph.state import VALID_CATEGORIES, VALID_SEVERITIES

            if article["category"] not in VALID_CATEGORIES:
                self.logger.debug(
                    "Invalid article category",
                    category=article["category"],
                    url=article["url"]
                )
                return False

            if article["severity"] not in VALID_SEVERITIES:
                self.logger.debug(
                    "Invalid article severity",
                    severity=article["severity"],
                    url=article["url"]
                )
                return False

            return True

        except Exception as e:
            self.logger.error(
                "Article validation error",
                error=str(e),
                article_url=article.get("url", "unknown")
            )
            return False