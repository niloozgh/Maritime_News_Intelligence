"""
LangGraph State Definition for Maritime Intelligence Engine

Defines the workflow state structure with proper reducers for multi-agent coordination.
"""

import operator
from typing import Annotated, Dict, List, TypedDict


class WorkflowState(TypedDict):
    """
    Complete workflow state for the multi-agent news processing system.

    Uses Annotated types with reducers for proper state management across agents.
    Enhanced with graph-based incident tracking and cross-temporal deduplication.
    """

    # Date management
    today: str  # Format: YYYY-MM-DD
    cutoff_date: str  # Format: YYYY-MM-DD (today - 2 days)

    # Phase 1: Source scraping results
    phase1_articles: Annotated[List[Dict], operator.add]  # Articles from 7 sources

    # Phase 2: Category gap search results
    phase2_articles: Annotated[List[Dict], operator.add]  # Articles from 6 searches

    # Graph-enhanced validation and analysis results
    validated_articles: Dict  # Deduplicated and validated articles
    incident_clusters: Annotated[List[List[Dict]], operator.add]  # Graph-based incident clusters
    graph_analysis: Dict  # Comprehensive graph analysis results
    cross_temporal_duplicates: Annotated[List[Dict], operator.add]  # Articles found across multiple days

    # Analysis and intelligence
    insights: Dict  # Generated operational insights
    incident_timeline: Annotated[List[Dict], operator.add]  # Timeline of incident development
    dashboard_data: Dict  # Final dashboard output with graph enhancements

    # Error tracking and monitoring
    errors: Annotated[List[Dict], operator.add]  # All errors encountered
    execution_metrics: Dict  # Performance and timing metrics
    graph_metrics: Dict  # Graph-specific performance metrics


# Article schema for validation
ARTICLE_SCHEMA = {
    "url": str,
    "title": str,
    "date": str,  # YYYY-MM-DD format
    "source": str,
    "category": str,  # One of 8 categories
    "severity": str,  # high/medium/low
    "incidentType": str,
    "summary": str,
    "ports": List[str],
    "vessels": List[str]
}

# Valid categories for articles
VALID_CATEGORIES = [
    "red sea",
    "geopolitical",
    "weather-related",
    "congestion",
    "operational issues",
    "us tariffs",
    "shipping line announcements",
    "vessel/container incidents"
]

# Valid severity levels
VALID_SEVERITIES = ["high", "medium", "low"]