"""
Validation Agent for Article Deduplication and Quality Control

Handles deduplication, date validation, and quality filtering of articles
from both Phase 1 (source scraping) and Phase 2 (category searches).
"""

from typing import Dict, List, Set, Tuple
import structlog
from urllib.parse import urlparse
from difflib import SequenceMatcher

from ..utils.date_utils import is_date_in_range, normalize_date_format
from ..utils.logging_config import LoggingMixin
from ..graph.state import VALID_CATEGORIES, VALID_SEVERITIES

logger = structlog.get_logger(__name__)


class ValidationAgent(LoggingMixin):
    """
    Specialized agent for validating and deduplicating maritime news articles.

    Performs comprehensive validation including:
    - Date range validation
    - URL and title deduplication
    - Content similarity detection
    - Metadata validation
    - Authority-based ranking
    """

    def __init__(self, cutoff_date: str, today: str, similarity_threshold: float = 0.8):
        """
        Initialize validation agent.

        Args:
            cutoff_date: Earliest acceptable date (YYYY-MM-DD)
            today: Current date (YYYY-MM-DD)
            similarity_threshold: Threshold for content similarity detection
        """
        self.cutoff_date = cutoff_date
        self.today = today
        self.similarity_threshold = similarity_threshold

        # Authority ranking for source prioritization
        self.source_authority = {
            "The Loadstar": 10,
            "Container News": 9,
            "Maersk": 8,
            "CMA CGM": 8,
            "gCaptain": 7,
            "Kuehne+Nagel": 6,
            "Port News": 5,
            "Unknown": 1
        }

        self.logger.info(
            "Validation agent initialized",
            cutoff_date=cutoff_date,
            today=today,
            similarity_threshold=similarity_threshold
        )

    async def validate_and_deduplicate(
        self,
        phase1_articles: List[Dict],
        phase2_articles: List[Dict]
    ) -> Dict[str, any]:
        """
        Validate and deduplicate articles from both phases.

        Args:
            phase1_articles: Articles from source scraping
            phase2_articles: Articles from category searches

        Returns:
            Dictionary with validated articles and statistics
        """
        self.log_operation_start(
            "article_validation",
            phase1_count=len(phase1_articles),
            phase2_count=len(phase2_articles)
        )

        try:
            # Combine all articles
            all_articles = phase1_articles + phase2_articles
            self.logger.info("Starting validation", total_articles=len(all_articles))

            # Step 1: Basic validation
            valid_articles = []
            invalid_count = 0

            for article in all_articles:
                if self._validate_article_structure(article):
                    valid_articles.append(article)
                else:
                    invalid_count += 1

            self.logger.info(
                "Basic validation completed",
                valid_articles=len(valid_articles),
                invalid_articles=invalid_count
            )

            # Step 2: Deduplication
            deduplicated_articles = self._deduplicate_articles(valid_articles)

            # Step 3: Final quality checks
            final_articles = self._apply_quality_filters(deduplicated_articles)

            # Step 4: Sort by priority
            sorted_articles = self._sort_by_priority(final_articles)

            # Generate statistics
            stats = self._generate_validation_stats(
                all_articles, valid_articles, deduplicated_articles, sorted_articles
            )

            self.log_operation_success(
                "article_validation",
                final_article_count=len(sorted_articles),
                **stats
            )

            return {
                "articles": sorted_articles,
                "statistics": stats,
                "validation_summary": {
                    "total_processed": len(all_articles),
                    "valid_after_structure_check": len(valid_articles),
                    "valid_after_deduplication": len(deduplicated_articles),
                    "final_article_count": len(sorted_articles)
                }
            }

        except Exception as e:
            self.log_operation_error("article_validation", e)
            return {
                "articles": [],
                "statistics": {},
                "validation_summary": {"error": str(e)}
            }

    def _validate_article_structure(self, article: Dict) -> bool:
        """
        Validate article structure and required fields.

        Args:
            article: Article dictionary to validate

        Returns:
            True if article has valid structure
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

            # Validate date format and range
            date_str = article["date"]
            normalized_date = normalize_date_format(date_str)
            if not normalized_date:
                self.logger.debug(
                    "Invalid date format",
                    date=date_str,
                    url=article["url"]
                )
                return False

            # Update article with normalized date
            article["date"] = normalized_date

            # Check date range
            if not is_date_in_range(normalized_date, self.cutoff_date, self.today):
                self.logger.debug(
                    "Article date out of range",
                    date=normalized_date,
                    cutoff_date=self.cutoff_date,
                    today=self.today,
                    url=article["url"]
                )
                return False

            # Validate category and severity
            if article["category"] not in VALID_CATEGORIES:
                self.logger.debug(
                    "Invalid category",
                    category=article["category"],
                    url=article["url"]
                )
                return False

            if article["severity"] not in VALID_SEVERITIES:
                self.logger.debug(
                    "Invalid severity",
                    severity=article["severity"],
                    url=article["url"]
                )
                return False

            # Validate URL format
            parsed_url = urlparse(article["url"])
            if not parsed_url.scheme or not parsed_url.netloc:
                self.logger.debug(
                    "Invalid URL format",
                    url=article["url"]
                )
                return False

            return True

        except Exception as e:
            self.logger.debug(
                "Article validation error",
                error=str(e),
                url=article.get("url", "unknown")
            )
            return False

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles using multiple strategies.

        Args:
            articles: List of validated articles

        Returns:
            Deduplicated article list
        """
        if not articles:
            return []

        # Track seen URLs and titles
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        deduplicated = []

        # Group similar articles for comparison
        similarity_groups = []

        for article in articles:
            url = article["url"]
            title = article["title"].lower().strip()

            # Check for exact URL duplicates
            if url in seen_urls:
                self.logger.debug("Duplicate URL detected", url=url)
                continue

            # Check for exact title duplicates
            if title in seen_titles:
                self.logger.debug("Duplicate title detected", title=title[:50])
                continue

            # Check for similar titles
            is_similar = False
            for existing_article in deduplicated:
                similarity = SequenceMatcher(
                    None,
                    title,
                    existing_article["title"].lower().strip()
                ).ratio()

                if similarity >= self.similarity_threshold:
                    self.logger.debug(
                        "Similar article detected",
                        similarity=round(similarity, 3),
                        existing_title=existing_article["title"][:50],
                        new_title=title[:50]
                    )

                    # Keep the one from more authoritative source
                    if self._get_source_authority(article["source"]) > \
                       self._get_source_authority(existing_article["source"]):
                        # Replace existing with new more authoritative article
                        deduplicated.remove(existing_article)
                        seen_urls.remove(existing_article["url"])
                        seen_titles.remove(existing_article["title"].lower().strip())
                    else:
                        is_similar = True
                    break

            if not is_similar:
                deduplicated.append(article)
                seen_urls.add(url)
                seen_titles.add(title)

        self.logger.info(
            "Deduplication completed",
            original_count=len(articles),
            deduplicated_count=len(deduplicated),
            removed_count=len(articles) - len(deduplicated)
        )

        return deduplicated

    def _apply_quality_filters(self, articles: List[Dict]) -> List[Dict]:
        """
        Apply final quality filters to articles.

        Args:
            articles: Deduplicated articles

        Returns:
            Quality-filtered articles
        """
        filtered_articles = []

        for article in articles:
            # Check minimum title length
            if len(article["title"].strip()) < 10:
                self.logger.debug(
                    "Article title too short",
                    title=article["title"],
                    url=article["url"]
                )
                continue

            # Check for required summary
            if not article.get("summary") or len(article["summary"].strip()) < 20:
                self.logger.debug(
                    "Article summary too short or missing",
                    url=article["url"]
                )
                continue

            # Validate incident type
            if not article.get("incidentType"):
                self.logger.debug(
                    "Missing incident type",
                    url=article["url"]
                )
                continue

            filtered_articles.append(article)

        self.logger.info(
            "Quality filtering completed",
            input_count=len(articles),
            output_count=len(filtered_articles),
            filtered_out=len(articles) - len(filtered_articles)
        )

        return filtered_articles

    def _sort_by_priority(self, articles: List[Dict]) -> List[Dict]:
        """
        Sort articles by priority (severity, authority, date).

        Args:
            articles: Quality-filtered articles

        Returns:
            Priority-sorted articles
        """
        def sort_key(article: Dict) -> Tuple[int, int, str]:
            # Severity priority (higher is better)
            severity_priority = {
                "high": 3,
                "medium": 2,
                "low": 1
            }

            # Source authority
            authority = self._get_source_authority(article["source"])

            # Date (newer is better)
            date = article["date"]

            return (
                -severity_priority.get(article["severity"], 0),  # Negative for desc sort
                -authority,  # Negative for desc sort
                -date  # Negative for desc sort (newer dates come first)
            )

        sorted_articles = sorted(articles, key=sort_key)

        self.logger.info(
            "Article sorting completed",
            total_articles=len(sorted_articles),
            high_severity=len([a for a in sorted_articles if a["severity"] == "high"]),
            medium_severity=len([a for a in sorted_articles if a["severity"] == "medium"]),
            low_severity=len([a for a in sorted_articles if a["severity"] == "low"])
        )

        return sorted_articles

    def _get_source_authority(self, source: str) -> int:
        """Get authority score for source."""
        return self.source_authority.get(source, 1)

    def _generate_validation_stats(
        self,
        original: List[Dict],
        valid: List[Dict],
        deduplicated: List[Dict],
        final: List[Dict]
    ) -> Dict[str, any]:
        """Generate comprehensive validation statistics."""
        # Category distribution
        category_dist = {}
        severity_dist = {}
        source_dist = {}

        for article in final:
            category = article["category"]
            severity = article["severity"]
            source = article["source"]

            category_dist[category] = category_dist.get(category, 0) + 1
            severity_dist[severity] = severity_dist.get(severity, 0) + 1
            source_dist[source] = source_dist.get(source, 0) + 1

        return {
            "processing_stats": {
                "original_count": len(original),
                "valid_after_structure": len(valid),
                "after_deduplication": len(deduplicated),
                "final_count": len(final),
                "rejection_rate": round((len(original) - len(final)) / len(original) * 100, 2) if original else 0
            },
            "category_distribution": category_dist,
            "severity_distribution": severity_dist,
            "source_distribution": source_dist,
            "date_range": {
                "cutoff_date": self.cutoff_date,
                "today": self.today,
                "articles_in_range": len(final)
            }
        }