"""
Date utilities for maritime news processing.

Handles date parsing, validation, and range checking for article publication dates.
Supports multiple date formats and relative time expressions.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog
from dateutil.parser import parse as parse_date
import pytz

logger = structlog.get_logger(__name__)


def calculate_dates() -> Tuple[str, str]:
    """
    Calculate today and cutoff date (today - 2 days).

    Returns:
        Tuple of (today, cutoff_date) in YYYY-MM-DD format
    """
    today = datetime.now(pytz.UTC).date()
    cutoff_date = today - timedelta(days=2)

    return today.strftime("%Y-%m-%d"), cutoff_date.strftime("%Y-%m-%d")


def parse_article_date(date_str: str, reference_date: Optional[datetime] = None) -> Optional[str]:
    """
    Parse article publication date from various formats.

    Supports:
    - YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY
    - "X hours ago", "X days ago", "Yesterday"
    - ISO datetime strings
    - Natural language dates

    Args:
        date_str: Date string to parse
        reference_date: Reference date for relative parsing (defaults to now)

    Returns:
        Date in YYYY-MM-DD format or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    if reference_date is None:
        reference_date = datetime.now(pytz.UTC)

    date_str = date_str.strip()

    try:
        # Handle relative time expressions
        relative_match = re.search(
            r'(\d+)\s+(hours?|days?|weeks?)\s+ago',
            date_str.lower()
        )
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)

            if 'hour' in unit:
                target_date = reference_date - timedelta(hours=amount)
            elif 'day' in unit:
                target_date = reference_date - timedelta(days=amount)
            elif 'week' in unit:
                target_date = reference_date - timedelta(weeks=amount)
            else:
                return None

            return target_date.strftime("%Y-%m-%d")

        # Handle "yesterday", "today"
        if 'yesterday' in date_str.lower():
            target_date = reference_date - timedelta(days=1)
            return target_date.strftime("%Y-%m-%d")

        if 'today' in date_str.lower():
            return reference_date.strftime("%Y-%m-%d")

        # Handle standard date formats
        parsed_date = parse_date(date_str, fuzzy=True)

        # If no timezone info, assume UTC
        if parsed_date.tzinfo is None:
            parsed_date = pytz.UTC.localize(parsed_date)

        return parsed_date.strftime("%Y-%m-%d")

    except Exception as e:
        logger.debug(
            "Failed to parse date",
            date_str=date_str,
            error=str(e)
        )
        return None


def is_date_in_range(date_str: str, cutoff_date: str, today: str) -> bool:
    """
    Check if date is within valid range [cutoff_date, today].

    Args:
        date_str: Date to check (YYYY-MM-DD format)
        cutoff_date: Earliest acceptable date (YYYY-MM-DD)
        today: Latest acceptable date (YYYY-MM-DD)

    Returns:
        True if date is in valid range
    """
    try:
        # Convert strings to date objects
        check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
        today_date = datetime.strptime(today, "%Y-%m-%d").date()

        # Check if date is in range [cutoff_date, today]
        return cutoff <= check_date <= today_date

    except (ValueError, TypeError) as e:
        logger.debug(
            "Date range validation failed",
            date_str=date_str,
            cutoff_date=cutoff_date,
            today=today,
            error=str(e)
        )
        return False


def extract_date_from_url(url: str) -> Optional[str]:
    """
    Extract date from URL patterns.

    Common patterns:
    - /2024/01/15/article-title
    - /news/2024-01-15-article
    - /article/20240115/title

    Args:
        url: URL to analyze

    Returns:
        Date in YYYY-MM-DD format or None
    """
    if not url:
        return None

    # Pattern 1: /YYYY/MM/DD/
    pattern1 = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if pattern1:
        year, month, day = pattern1.groups()
        return f"{year}-{month}-{day}"

    # Pattern 2: YYYY-MM-DD
    pattern2 = re.search(r'(\d{4}-\d{2}-\d{2})', url)
    if pattern2:
        return pattern2.group(1)

    # Pattern 3: YYYYMMDD
    pattern3 = re.search(r'/(\d{8})/', url)
    if pattern3:
        date_str = pattern3.group(1)
        try:
            parsed = datetime.strptime(date_str, "%Y%m%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def normalize_date_format(date_str: str) -> Optional[str]:
    """
    Normalize various date formats to YYYY-MM-DD.

    Args:
        date_str: Date string in any supported format

    Returns:
        Normalized date string or None if parsing fails
    """
    if not date_str:
        return None

    # Try multiple parsing approaches
    parsing_methods = [
        parse_article_date,
        lambda d: extract_date_from_url(d),
        lambda d: parse_date(d, fuzzy=True).strftime("%Y-%m-%d") if d else None
    ]

    for method in parsing_methods:
        try:
            result = method(date_str)
            if result and re.match(r'\d{4}-\d{2}-\d{2}', result):
                return result
        except Exception:
            continue

    logger.debug("All date parsing methods failed", date_str=date_str)
    return None