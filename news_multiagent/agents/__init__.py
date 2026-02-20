"""
Maritime Intelligence Engine - Multi-Agent System

This package contains specialized agents for maritime news processing:
- SourceScraperAgent: Scrapes individual news sources using Claude Computer Use
- ValidationAgent: Validates and deduplicates articles
- AnalysisAgent: Generates operational insights
- Phase2SearchAgent: Performs category-based gap searches
"""

from .source_scraper import SourceScraperAgent
from .validation import ValidationAgent
from .analysis import AnalysisAgent
from .phase2_search import Phase2SearchAgent

__all__ = [
    "SourceScraperAgent",
    "ValidationAgent",
    "AnalysisAgent",
    "Phase2SearchAgent"
]