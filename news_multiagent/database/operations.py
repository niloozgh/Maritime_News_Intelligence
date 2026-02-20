"""
Database operations for workflow persistence and data retrieval.

Handles saving workflow results, querying articles, and managing
database connections with proper async support.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from .models import Base, WorkflowRun, Article, SourceReliability, IncidentTracking
from ..config.settings import get_settings
from ..graph.state import WorkflowState

logger = structlog.get_logger(__name__)


async def create_tables():
    """
    Create all database tables if they don't exist.
    """
    settings = get_settings()

    try:
        # Use sync engine for table creation
        engine = create_engine(settings.postgres_url)
        Base.metadata.create_all(engine)
        engine.dispose()

        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def get_async_session() -> AsyncSession:
    """
    Get async database session.

    Returns:
        Configured AsyncSession
    """
    settings = get_settings()

    async_engine = create_async_engine(
        settings.postgres_async_url,
        echo=False,
        pool_size=5,
        max_overflow=10
    )

    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    return async_session()


async def save_workflow_results(state: WorkflowState) -> str:
    """
    Save complete workflow results to database.

    Args:
        state: Final workflow state

    Returns:
        Workflow run ID
    """
    logger.info("Saving workflow results to database")

    try:
        session = await get_async_session()

        try:
            # Extract data from state
            execution_metrics = state.get("execution_metrics", {})
            validated_data = state.get("validated_articles", {})
            articles_list = validated_data.get("articles", [])
            insights = state.get("insights", {})
            errors = state.get("errors", [])

            # Create workflow run record
            workflow_run = WorkflowRun(
                cutoff_date=state["cutoff_date"],
                today_date=state["today"],
                status="completed" if not errors else "completed_with_errors",
                total_duration_seconds=execution_metrics.get("total_workflow_duration", 0),
                phase1_duration_seconds=execution_metrics.get("phase1_duration", 0),
                phase2_duration_seconds=execution_metrics.get("phase2_duration", 0),
                validation_duration_seconds=execution_metrics.get("validation_duration", 0),
                analysis_duration_seconds=execution_metrics.get("analysis_duration", 0),
                dashboard_duration_seconds=execution_metrics.get("dashboard_duration", 0),
                phase1_articles_found=execution_metrics.get("phase1_articles_count", 0),
                phase2_articles_found=execution_metrics.get("phase2_articles_count", 0),
                total_articles_processed=execution_metrics.get("total_input_articles", 0),
                final_articles_count=execution_metrics.get("final_validated_articles", 0),
                sources_success=execution_metrics.get("phase1_sources_success", 0),
                sources_failed=execution_metrics.get("phase1_sources_failed", 0),
                searches_success=execution_metrics.get("phase2_searches_success", 0),
                searches_failed=execution_metrics.get("phase2_searches_failed", 0),
                success_rate_percent=float(execution_metrics.get("success_rate", "0").rstrip("%")),
                errors_encountered=errors,
                execution_metrics=execution_metrics,
                insights_summary=_extract_insights_summary(insights)
            )

            session.add(workflow_run)
            await session.flush()  # Get the ID

            # Save articles
            for article_data in articles_list:
                article = Article(
                    workflow_run_id=workflow_run.id,
                    url=article_data["url"],
                    title=article_data["title"],
                    source=article_data["source"],
                    publication_date=article_data["date"],
                    category=article_data["category"],
                    severity=article_data["severity"],
                    incident_type=article_data.get("incidentType", ""),
                    summary=article_data.get("summary", ""),
                    ports=article_data.get("ports", []),
                    vessels=article_data.get("vessels", []),
                    operational_impact=article_data.get("operationalImpact", ""),
                    processing_phase=article_data.get("processing_phase", "unknown"),
                    validation_status="validated",
                    raw_data=article_data
                )
                session.add(article)

            await session.commit()

            logger.info(
                "Workflow results saved successfully",
                workflow_run_id=str(workflow_run.id),
                articles_saved=len(articles_list)
            )

            return str(workflow_run.id)

        except Exception as e:
            await session.rollback()
            raise e

        finally:
            await session.close()

    except Exception as e:
        logger.error("Failed to save workflow results", error=str(e), exc_info=True)
        raise


async def get_recent_articles(days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent articles from database.

    Args:
        days: Number of days back to search
        limit: Maximum number of articles to return

    Returns:
        List of article dictionaries
    """
    logger.info(f"Fetching recent articles (last {days} days, limit {limit})")

    try:
        session = await get_async_session()

        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()

            # Query recent articles
            query = text("""
                SELECT
                    a.id, a.url, a.title, a.source, a.publication_date,
                    a.category, a.severity, a.incident_type, a.summary,
                    a.ports, a.vessels, a.operational_impact, a.risk_score,
                    a.scraped_at, w.run_date as workflow_date
                FROM articles a
                JOIN workflow_runs w ON a.workflow_run_id = w.id
                WHERE a.publication_date >= :cutoff_date
                  AND a.validation_status = 'validated'
                ORDER BY a.publication_date DESC, a.scraped_at DESC
                LIMIT :limit
            """)

            result = await session.execute(
                query,
                {"cutoff_date": cutoff_date.strftime("%Y-%m-%d"), "limit": limit}
            )

            articles = []
            for row in result:
                articles.append({
                    "id": str(row.id),
                    "url": row.url,
                    "title": row.title,
                    "source": row.source,
                    "publication_date": row.publication_date,
                    "category": row.category,
                    "severity": row.severity,
                    "incident_type": row.incident_type,
                    "summary": row.summary,
                    "ports": row.ports or [],
                    "vessels": row.vessels or [],
                    "operational_impact": row.operational_impact,
                    "risk_score": row.risk_score,
                    "scraped_at": row.scraped_at.isoformat() if row.scraped_at else None,
                    "workflow_date": row.workflow_date.isoformat() if row.workflow_date else None
                })

            logger.info(f"Retrieved {len(articles)} recent articles")
            return articles

        finally:
            await session.close()

    except Exception as e:
        logger.error("Failed to fetch recent articles", error=str(e), exc_info=True)
        return []


async def get_workflow_history(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent workflow run history.

    Args:
        limit: Maximum number of workflow runs to return

    Returns:
        List of workflow run summaries
    """
    logger.info(f"Fetching workflow history (limit {limit})")

    try:
        session = await get_async_session()

        try:
            query = text("""
                SELECT
                    id, run_date, cutoff_date, today_date, status,
                    total_duration_seconds, final_articles_count,
                    sources_success, sources_failed, success_rate_percent
                FROM workflow_runs
                ORDER BY run_date DESC
                LIMIT :limit
            """)

            result = await session.execute(query, {"limit": limit})

            workflows = []
            for row in result:
                workflows.append({
                    "id": str(row.id),
                    "run_date": row.run_date.isoformat() if row.run_date else None,
                    "date_range": f"{row.cutoff_date} to {row.today_date}",
                    "status": row.status,
                    "duration_seconds": row.total_duration_seconds,
                    "articles_found": row.final_articles_count,
                    "sources_success": row.sources_success,
                    "sources_failed": row.sources_failed,
                    "success_rate": row.success_rate_percent
                })

            logger.info(f"Retrieved {len(workflows)} workflow runs")
            return workflows

        finally:
            await session.close()

    except Exception as e:
        logger.error("Failed to fetch workflow history", error=str(e), exc_info=True)
        return []


async def get_articles_by_category(category: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get articles by specific category.

    Args:
        category: Article category to filter by
        days: Number of days back to search

    Returns:
        List of articles in category
    """
    logger.info(f"Fetching articles for category: {category}")

    try:
        session = await get_async_session()

        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()

            query = text("""
                SELECT
                    a.url, a.title, a.source, a.publication_date,
                    a.severity, a.incident_type, a.summary,
                    a.ports, a.vessels, a.risk_score
                FROM articles a
                JOIN workflow_runs w ON a.workflow_run_id = w.id
                WHERE a.category = :category
                  AND a.publication_date >= :cutoff_date
                  AND a.validation_status = 'validated'
                ORDER BY a.severity DESC, a.publication_date DESC
            """)

            result = await session.execute(
                query,
                {"category": category, "cutoff_date": cutoff_date.strftime("%Y-%m-%d")}
            )

            articles = []
            for row in result:
                articles.append({
                    "url": row.url,
                    "title": row.title,
                    "source": row.source,
                    "publication_date": row.publication_date,
                    "severity": row.severity,
                    "incident_type": row.incident_type,
                    "summary": row.summary,
                    "ports": row.ports or [],
                    "vessels": row.vessels or [],
                    "risk_score": row.risk_score
                })

            logger.info(f"Retrieved {len(articles)} articles for category {category}")
            return articles

        finally:
            await session.close()

    except Exception as e:
        logger.error(f"Failed to fetch articles for category {category}", error=str(e))
        return []


async def update_source_reliability_metrics():
    """
    Update source reliability metrics based on recent performance.
    """
    logger.info("Updating source reliability metrics")

    try:
        session = await get_async_session()

        try:
            # Calculate metrics for each source over last 30 days
            cutoff_date = (datetime.utcnow() - timedelta(days=30)).date()

            query = text("""
                SELECT
                    source,
                    COUNT(*) as total_articles,
                    COUNT(*) FILTER (WHERE validation_status = 'validated') as validated_articles,
                    COUNT(*) FILTER (WHERE severity = 'high') as high_severity_articles,
                    COUNT(DISTINCT category) as categories_covered
                FROM articles a
                JOIN workflow_runs w ON a.workflow_run_id = w.id
                WHERE a.publication_date >= :cutoff_date
                GROUP BY source
            """)

            result = await session.execute(
                query,
                {"cutoff_date": cutoff_date.strftime("%Y-%m-%d")}
            )

            for row in result:
                # Calculate reliability score
                validation_rate = (row.validated_articles / row.total_articles) if row.total_articles > 0 else 0
                quality_score = (row.high_severity_articles / row.total_articles) if row.total_articles > 0 else 0
                diversity_score = min(row.categories_covered / 8, 1.0)  # 8 total categories

                reliability_score = (validation_rate + quality_score + diversity_score) / 3 * 10

                # Save/update reliability record
                reliability_record = SourceReliability(
                    source_name=row.source,
                    articles_processed=row.total_articles,
                    articles_validated=row.validated_articles,
                    high_severity_articles=row.high_severity_articles,
                    categories_covered=row.categories_covered,
                    reliability_score=reliability_score
                )

                session.add(reliability_record)

            await session.commit()

            logger.info("Source reliability metrics updated successfully")

        finally:
            await session.close()

    except Exception as e:
        logger.error("Failed to update source reliability metrics", error=str(e))


async def cleanup_old_data(days_to_keep: int = 30):
    """
    Clean up old workflow data beyond retention period.

    Args:
        days_to_keep: Number of days of data to retain
    """
    logger.info(f"Cleaning up data older than {days_to_keep} days")

    try:
        session = await get_async_session()

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Delete old workflow runs (articles will cascade delete)
            delete_query = text("""
                DELETE FROM workflow_runs
                WHERE run_date < :cutoff_date
            """)

            result = await session.execute(
                delete_query,
                {"cutoff_date": cutoff_date}
            )

            await session.commit()

            logger.info(f"Cleaned up {result.rowcount} old workflow runs")

        finally:
            await session.close()

    except Exception as e:
        logger.error("Failed to cleanup old data", error=str(e))


def _extract_insights_summary(insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key insights for database storage.

    Args:
        insights: Full insights dictionary

    Returns:
        Summarized insights for database
    """
    if not insights or "error" in insights:
        return {"error": insights.get("error", "No insights generated")}

    executive_summary = insights.get("executive_summary", {})
    risk_prioritization = insights.get("risk_prioritization", {})

    return {
        "total_incidents": executive_summary.get("total_incidents", 0),
        "high_severity_count": executive_summary.get("high_severity_count", 0),
        "overall_risk_level": executive_summary.get("overall_risk_level", "UNKNOWN"),
        "critical_alert": executive_summary.get("critical_alert", False),
        "high_priority_risks": len(risk_prioritization.get("high_priority", [])),
        "medium_priority_risks": len(risk_prioritization.get("medium_priority", [])),
        "key_highlights": executive_summary.get("key_highlights", [])[:3]  # Top 3
    }