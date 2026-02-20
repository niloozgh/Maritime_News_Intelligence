"""
LangGraph Workflow for Multi-Agent Maritime News Intelligence

Orchestrates parallel execution of source scrapers, validation, and analysis
with proper state management and checkpointing.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict

import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from .state import WorkflowState
from ..agents.source_scraper import SourceScraperAgent
from ..agents.phase2_search import Phase2SearchAgent
from ..agents.validation import ValidationAgent
from ..agents.analysis import AnalysisAgent
from ..config.settings import get_settings, NEWS_SOURCES, CATEGORY_SEARCHES
from ..utils.date_utils import calculate_dates
from ..utils.logging_config import log_workflow_state, get_logger
from ..database.operations import save_workflow_results

logger = get_logger(__name__)


async def initialize_dates_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Initialize workflow with current date calculations.

    Args:
        state: Current workflow state

    Returns:
        State update with today and cutoff_date
    """
    logger.info("Initializing workflow dates")

    try:
        today, cutoff_date = calculate_dates()

        state_update = {
            "today": today,
            "cutoff_date": cutoff_date,
            "execution_metrics": {
                "workflow_start": datetime.utcnow().isoformat(),
                "phase": "initialization"
            }
        }

        log_workflow_state(state_update, "initialize_dates")

        logger.info(
            "Date initialization completed",
            today=today,
            cutoff_date=cutoff_date
        )

        return state_update

    except Exception as e:
        logger.error("Failed to initialize dates", error=str(e), exc_info=True)
        return {
            "errors": [{
                "node": "initialize_dates",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def phase1_scraping_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute Phase 1: Parallel source scraping using 7 specialized agents.

    Args:
        state: Current workflow state

    Returns:
        State update with phase1_articles
    """
    logger.info("Starting Phase 1: Parallel source scraping")
    phase_start = datetime.utcnow()

    try:
        cutoff_date = state["cutoff_date"]
        today = state["today"]

        # Create source scraper agents
        scrapers = []
        for source_config in NEWS_SOURCES:
            agent = SourceScraperAgent(
                source_config=source_config,
                cutoff_date=cutoff_date,
                today=today
            )
            scrapers.append(agent)

        logger.info(f"Created {len(scrapers)} source scraper agents")

        # Execute scrapers in parallel
        scraper_results = await asyncio.gather(
            *[scraper.scrape() for scraper in scrapers],
            return_exceptions=True
        )

        # Process results and handle exceptions
        all_articles = []
        errors = []

        for i, result in enumerate(scraper_results):
            if isinstance(result, Exception):
                error_info = {
                    "node": "phase1_scraping",
                    "source": NEWS_SOURCES[i]["name"],
                    "error": str(result),
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_info)
                logger.error(
                    "Source scraper failed",
                    source=NEWS_SOURCES[i]["name"],
                    error=str(result)
                )
            else:
                all_articles.extend(result)
                logger.info(
                    "Source scraper completed",
                    source=NEWS_SOURCES[i]["name"],
                    articles_found=len(result)
                )

        phase_duration = (datetime.utcnow() - phase_start).total_seconds()

        state_update = {
            "phase1_articles": all_articles,
            "execution_metrics": {
                "phase1_duration": phase_duration,
                "phase1_articles_count": len(all_articles),
                "phase1_sources_success": len([r for r in scraper_results if not isinstance(r, Exception)]),
                "phase1_sources_failed": len([r for r in scraper_results if isinstance(r, Exception)])
            }
        }

        if errors:
            state_update["errors"] = errors

        log_workflow_state(state_update, "phase1_scraping")

        logger.info(
            "Phase 1 completed",
            articles_found=len(all_articles),
            duration_seconds=phase_duration,
            success_rate=f"{(len(scrapers) - len(errors)) / len(scrapers) * 100:.1f}%"
        )

        return state_update

    except Exception as e:
        logger.error("Phase 1 scraping failed", error=str(e), exc_info=True)
        return {
            "phase1_articles": [],
            "errors": [{
                "node": "phase1_scraping",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def phase2_searching_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute Phase 2: Parallel category gap searches using 6 specialized agents.

    Args:
        state: Current workflow state

    Returns:
        State update with phase2_articles
    """
    logger.info("Starting Phase 2: Parallel category gap searches")
    phase_start = datetime.utcnow()

    try:
        cutoff_date = state["cutoff_date"]
        today = state["today"]

        # Create search agents
        search_agents = []
        for search_config in CATEGORY_SEARCHES:
            agent = Phase2SearchAgent(
                search_config=search_config,
                cutoff_date=cutoff_date,
                today=today
            )
            search_agents.append(agent)

        logger.info(f"Created {len(search_agents)} category search agents")

        # Execute searches in parallel
        search_results = await asyncio.gather(
            *[agent.search() for agent in search_agents],
            return_exceptions=True
        )

        # Process results
        all_search_articles = []
        errors = []

        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                error_info = {
                    "node": "phase2_searching",
                    "search": CATEGORY_SEARCHES[i]["name"],
                    "error": str(result),
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_info)
                logger.error(
                    "Category search failed",
                    search=CATEGORY_SEARCHES[i]["name"],
                    error=str(result)
                )
            else:
                all_search_articles.extend(result)
                logger.info(
                    "Category search completed",
                    search=CATEGORY_SEARCHES[i]["name"],
                    articles_found=len(result)
                )

        phase_duration = (datetime.utcnow() - phase_start).total_seconds()

        state_update = {
            "phase2_articles": all_search_articles,
            "execution_metrics": {
                **state.get("execution_metrics", {}),
                "phase2_duration": phase_duration,
                "phase2_articles_count": len(all_search_articles),
                "phase2_searches_success": len([r for r in search_results if not isinstance(r, Exception)]),
                "phase2_searches_failed": len([r for r in search_results if isinstance(r, Exception)])
            }
        }

        if errors:
            state_update["errors"] = errors

        log_workflow_state(state_update, "phase2_searching")

        logger.info(
            "Phase 2 completed",
            articles_found=len(all_search_articles),
            duration_seconds=phase_duration
        )

        return state_update

    except Exception as e:
        logger.error("Phase 2 searching failed", error=str(e), exc_info=True)
        return {
            "phase2_articles": [],
            "errors": [{
                "node": "phase2_searching",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def validation_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute validation and deduplication of all articles.

    Args:
        state: Current workflow state

    Returns:
        State update with validated_articles
    """
    logger.info("Starting article validation and deduplication")
    validation_start = datetime.utcnow()

    try:
        phase1_articles = state.get("phase1_articles", [])
        phase2_articles = state.get("phase2_articles", [])
        cutoff_date = state["cutoff_date"]
        today = state["today"]

        # Initialize validation agent
        validation_agent = ValidationAgent(
            cutoff_date=cutoff_date,
            today=today
        )

        # Perform validation and deduplication
        validation_results = await validation_agent.validate_and_deduplicate(
            phase1_articles=phase1_articles,
            phase2_articles=phase2_articles
        )

        validation_duration = (datetime.utcnow() - validation_start).total_seconds()

        state_update = {
            "validated_articles": validation_results,
            "execution_metrics": {
                **state.get("execution_metrics", {}),
                "validation_duration": validation_duration,
                "total_input_articles": len(phase1_articles) + len(phase2_articles),
                "final_validated_articles": len(validation_results.get("articles", []))
            }
        }

        log_workflow_state(state_update, "validation")

        logger.info(
            "Validation completed",
            input_articles=len(phase1_articles) + len(phase2_articles),
            validated_articles=len(validation_results.get("articles", [])),
            duration_seconds=validation_duration
        )

        return state_update

    except Exception as e:
        logger.error("Validation failed", error=str(e), exc_info=True)
        return {
            "validated_articles": {"articles": [], "statistics": {}},
            "errors": [{
                "node": "validation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def analysis_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute comprehensive analysis of validated articles.

    Args:
        state: Current workflow state

    Returns:
        State update with insights
    """
    logger.info("Starting comprehensive article analysis")
    analysis_start = datetime.utcnow()

    try:
        validated_data = state.get("validated_articles", {})
        validated_articles = validated_data.get("articles", [])

        if not validated_articles:
            logger.warning("No validated articles to analyze")
            return {
                "insights": {"error": "No articles to analyze"},
                "execution_metrics": {
                    **state.get("execution_metrics", {}),
                    "analysis_duration": 0,
                    "analysis_articles": 0
                }
            }

        # Initialize analysis agent
        analysis_agent = AnalysisAgent()

        # Generate comprehensive analysis
        insights = await analysis_agent.analyze(validated_articles)

        analysis_duration = (datetime.utcnow() - analysis_start).total_seconds()

        state_update = {
            "insights": insights,
            "execution_metrics": {
                **state.get("execution_metrics", {}),
                "analysis_duration": analysis_duration,
                "analysis_articles": len(validated_articles)
            }
        }

        log_workflow_state(state_update, "analysis")

        logger.info(
            "Analysis completed",
            articles_analyzed=len(validated_articles),
            insights_generated=len(insights),
            duration_seconds=analysis_duration
        )

        return state_update

    except Exception as e:
        logger.error("Analysis failed", error=str(e), exc_info=True)
        return {
            "insights": {"error": str(e)},
            "errors": [{
                "node": "analysis",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def dashboard_generation_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Generate React/TypeScript dashboard from analysis results.

    Args:
        state: Current workflow state

    Returns:
        State update with dashboard_data
    """
    logger.info("Starting dashboard generation")
    dashboard_start = datetime.utcnow()

    try:
        insights = state.get("insights", {})
        validated_data = state.get("validated_articles", {})
        execution_metrics = state.get("execution_metrics", {})

        # Generate dashboard data structure
        dashboard_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "date_range": {
                    "cutoff_date": state["cutoff_date"],
                    "today": state["today"]
                },
                "execution_metrics": execution_metrics
            },
            "articles": validated_data.get("articles", []),
            "statistics": validated_data.get("statistics", {}),
            "insights": insights,
            "categories": [
                "red sea",
                "geopolitical",
                "weather-related",
                "congestion",
                "operational issues",
                "us tariffs",
                "shipping line announcements",
                "vessel/container incidents"
            ],
            "severity_levels": ["high", "medium", "low"]
        }

        dashboard_duration = (datetime.utcnow() - dashboard_start).total_seconds()

        # Calculate final execution metrics
        workflow_start = execution_metrics.get("workflow_start")
        total_duration = (datetime.utcnow() - datetime.fromisoformat(workflow_start)).total_seconds() if workflow_start else 0

        final_metrics = {
            **execution_metrics,
            "dashboard_duration": dashboard_duration,
            "total_workflow_duration": total_duration,
            "workflow_end": datetime.utcnow().isoformat(),
            "success_rate": "100%" if not state.get("errors") else f"{((len(NEWS_SOURCES) + len(CATEGORY_SEARCHES)) - len(state.get('errors', []))) / (len(NEWS_SOURCES) + len(CATEGORY_SEARCHES)) * 100:.1f}%"
        }

        state_update = {
            "dashboard_data": dashboard_data,
            "execution_metrics": final_metrics
        }

        log_workflow_state(state_update, "dashboard_generation")

        logger.info(
            "Dashboard generation completed",
            total_articles=len(dashboard_data["articles"]),
            total_duration_seconds=total_duration,
            duration_seconds=dashboard_duration
        )

        # Save results to database
        try:
            await save_workflow_results(state)
            logger.info("Workflow results saved to database")
        except Exception as db_error:
            logger.error("Failed to save workflow results", error=str(db_error))

        return state_update

    except Exception as e:
        logger.error("Dashboard generation failed", error=str(e), exc_info=True)
        return {
            "dashboard_data": {"error": str(e)},
            "errors": [{
                "node": "dashboard_generation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


def create_workflow() -> StateGraph:
    """
    Create and configure the LangGraph workflow.

    Returns:
        Configured StateGraph with all nodes and edges
    """
    logger.info("Creating LangGraph workflow")

    # Initialize workflow graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("initialize_dates", initialize_dates_node)
    workflow.add_node("phase1_scraping", phase1_scraping_node)
    workflow.add_node("phase2_searching", phase2_searching_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("dashboard_generation", dashboard_generation_node)

    # Add edges (workflow flow)
    workflow.set_entry_point("initialize_dates")
    workflow.add_edge("initialize_dates", "phase1_scraping")
    workflow.add_edge("phase1_scraping", "phase2_searching")
    workflow.add_edge("phase2_searching", "validation")
    workflow.add_edge("validation", "analysis")
    workflow.add_edge("analysis", "dashboard_generation")
    workflow.add_edge("dashboard_generation", END)

    logger.info("LangGraph workflow created successfully")
    return workflow


def create_workflow_with_checkpointing() -> StateGraph:
    """
    Create workflow with PostgreSQL checkpointing enabled.

    Returns:
        Compiled StateGraph with checkpointing
    """
    settings = get_settings()

    # Create base workflow
    workflow = create_workflow()

    if settings.checkpoint_enabled:
        try:
            # Initialize PostgreSQL checkpointer
            checkpointer = PostgresSaver.from_conn_string(settings.postgres_url)

            # Compile with checkpointing
            compiled_workflow = workflow.compile(checkpointer=checkpointer)

            logger.info("Workflow compiled with PostgreSQL checkpointing")
            return compiled_workflow

        except Exception as e:
            logger.warning(
                "Failed to enable checkpointing, using memory-only mode",
                error=str(e)
            )

    # Fallback to memory-only compilation
    compiled_workflow = workflow.compile()
    logger.info("Workflow compiled without checkpointing")
    return compiled_workflow