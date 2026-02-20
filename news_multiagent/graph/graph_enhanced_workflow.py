"""
Graph-Enhanced LangGraph Workflow for Maritime News Intelligence

Enhanced workflow that uses graph-based incident tracking, cross-temporal
deduplication, and incident clustering for superior news analysis.
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
from ..agents.graph_validation import GraphValidationAgent
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
    logger.info("Initializing graph-enhanced workflow dates")

    try:
        today, cutoff_date = calculate_dates()

        state_update = {
            "today": today,
            "cutoff_date": cutoff_date,
            "execution_metrics": {
                "workflow_start": datetime.utcnow().isoformat(),
                "phase": "initialization",
                "graph_enhanced": True
            },
            "graph_metrics": {
                "initialization_time": datetime.utcnow().isoformat()
            }
        }

        log_workflow_state(state_update, "initialize_dates")

        logger.info(
            "Graph-enhanced date initialization completed",
            today=today,
            cutoff_date=cutoff_date,
            enhanced_features=["cross_temporal_deduplication", "incident_clustering", "graph_analysis"]
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
    logger.info("Starting Phase 1: Parallel source scraping (Graph-Enhanced)")
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

        logger.info(f"Created {len(scrapers)} source scraper agents for graph workflow")

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

        log_workflow_state(state_update, "phase1_scraping_graph")

        logger.info(
            "Phase 1 completed (ready for graph processing)",
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
    logger.info("Starting Phase 2: Parallel category gap searches (Graph-Enhanced)")
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

        logger.info(f"Created {len(search_agents)} category search agents for graph workflow")

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

        log_workflow_state(state_update, "phase2_searching_graph")

        logger.info(
            "Phase 2 completed (ready for graph processing)",
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


async def graph_validation_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute graph-enhanced validation and deduplication of all articles.

    Args:
        state: Current workflow state

    Returns:
        State update with validated_articles, incident_clusters, and graph_analysis
    """
    logger.info("Starting graph-enhanced validation and incident clustering")
    validation_start = datetime.utcnow()

    try:
        phase1_articles = state.get("phase1_articles", [])
        phase2_articles = state.get("phase2_articles", [])
        cutoff_date = state["cutoff_date"]
        today = state["today"]

        # Initialize graph-enhanced validation agent
        graph_validation_agent = GraphValidationAgent(
            cutoff_date=cutoff_date,
            today=today,
            similarity_threshold=0.75,
            temporal_window_days=30,
            graph_storage_path="./data/incident_graph.pkl"
        )

        # Perform graph-enhanced validation and clustering
        validation_results = await graph_validation_agent.validate_and_deduplicate(
            phase1_articles=phase1_articles,
            phase2_articles=phase2_articles
        )

        # Extract incident timeline
        incident_timeline = await graph_validation_agent.get_incident_timeline(days_back=14)

        # Get graph metrics
        graph_stats = graph_validation_agent.incident_graph.get_graph_statistics()

        validation_duration = (datetime.utcnow() - validation_start).total_seconds()

        state_update = {
            "validated_articles": validation_results,
            "incident_clusters": validation_results.get("incident_clusters", []),
            "graph_analysis": validation_results.get("graph_analysis", {}),
            "cross_temporal_duplicates": validation_results.get("deduplicated_articles", []),
            "incident_timeline": incident_timeline,
            "execution_metrics": {
                **state.get("execution_metrics", {}),
                "validation_duration": validation_duration,
                "total_input_articles": len(phase1_articles) + len(phase2_articles),
                "final_validated_articles": len(validation_results.get("articles", [])),
                "graph_validation_enabled": True
            },
            "graph_metrics": {
                **state.get("graph_metrics", {}),
                "graph_nodes": graph_stats["total_nodes"],
                "graph_edges": graph_stats["total_edges"],
                "connected_components": graph_stats["connected_components"],
                "incident_clusters_found": len(validation_results.get("incident_clusters", [])),
                "cross_temporal_duplicates_removed": len(validation_results.get("deduplicated_articles", [])),
                "validation_duration": validation_duration
            }
        }

        log_workflow_state(state_update, "graph_validation")

        logger.info(
            "Graph-enhanced validation completed",
            input_articles=len(phase1_articles) + len(phase2_articles),
            validated_articles=len(validation_results.get("articles", [])),
            incident_clusters=len(validation_results.get("incident_clusters", [])),
            cross_temporal_duplicates=len(validation_results.get("deduplicated_articles", [])),
            graph_nodes=graph_stats["total_nodes"],
            duration_seconds=validation_duration
        )

        return state_update

    except Exception as e:
        logger.error("Graph validation failed", error=str(e), exc_info=True)
        return {
            "validated_articles": {"articles": [], "statistics": {}},
            "incident_clusters": [],
            "graph_analysis": {},
            "cross_temporal_duplicates": [],
            "incident_timeline": [],
            "errors": [{
                "node": "graph_validation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def enhanced_analysis_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute comprehensive analysis enhanced with graph insights.

    Args:
        state: Current workflow state

    Returns:
        State update with enhanced insights
    """
    logger.info("Starting graph-enhanced comprehensive analysis")
    analysis_start = datetime.utcnow()

    try:
        validated_data = state.get("validated_articles", {})
        validated_articles = validated_data.get("articles", [])
        incident_clusters = state.get("incident_clusters", [])
        incident_timeline = state.get("incident_timeline", [])
        graph_analysis = state.get("graph_analysis", {})

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

        # Generate base analysis
        base_insights = await analysis_agent.analyze(validated_articles)

        # Enhance with graph insights
        enhanced_insights = {
            **base_insights,
            "graph_enhanced_analysis": {
                "incident_clusters": {
                    "total_clusters": len(incident_clusters),
                    "multi_source_incidents": len([c for c in incident_clusters if len(c) >= 2]),
                    "major_incidents": len([c for c in incident_clusters if len(c) >= 3]),
                    "cluster_analysis": self._analyze_incident_clusters(incident_clusters),
                },
                "temporal_development": {
                    "incidents_with_timeline": len(incident_timeline),
                    "longest_developing_incident": self._find_longest_incident(incident_timeline),
                    "timeline_summary": self._summarize_incident_timelines(incident_timeline)
                },
                "cross_temporal_insights": {
                    "duplicates_removed": len(state.get("cross_temporal_duplicates", [])),
                    "deduplication_effectiveness": self._calculate_deduplication_effectiveness(state),
                    "persistent_incidents": self._identify_persistent_incidents(incident_timeline)
                },
                "graph_network_analysis": graph_analysis.get("statistics", {}),
                "enhanced_recommendations": self._generate_graph_enhanced_recommendations(
                    incident_clusters, incident_timeline, base_insights
                )
            }
        }

        analysis_duration = (datetime.utcnow() - analysis_start).total_seconds()

        state_update = {
            "insights": enhanced_insights,
            "execution_metrics": {
                **state.get("execution_metrics", {}),
                "analysis_duration": analysis_duration,
                "analysis_articles": len(validated_articles),
                "graph_enhanced_analysis": True
            },
            "graph_metrics": {
                **state.get("graph_metrics", {}),
                "analysis_clusters_processed": len(incident_clusters),
                "timeline_incidents_analyzed": len(incident_timeline),
                "analysis_duration": analysis_duration
            }
        }

        log_workflow_state(state_update, "enhanced_analysis")

        logger.info(
            "Graph-enhanced analysis completed",
            articles_analyzed=len(validated_articles),
            incident_clusters_analyzed=len(incident_clusters),
            timeline_incidents=len(incident_timeline),
            duration_seconds=analysis_duration
        )

        return state_update

    except Exception as e:
        logger.error("Enhanced analysis failed", error=str(e), exc_info=True)
        return {
            "insights": {"error": str(e)},
            "errors": [{
                "node": "enhanced_analysis",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


async def graph_dashboard_generation_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Generate enhanced React/TypeScript dashboard with graph insights.

    Args:
        state: Current workflow state

    Returns:
        State update with enhanced dashboard_data
    """
    logger.info("Starting graph-enhanced dashboard generation")
    dashboard_start = datetime.utcnow()

    try:
        insights = state.get("insights", {})
        validated_data = state.get("validated_articles", {})
        incident_clusters = state.get("incident_clusters", [])
        incident_timeline = state.get("incident_timeline", [])
        graph_analysis = state.get("graph_analysis", {})
        execution_metrics = state.get("execution_metrics", {})
        graph_metrics = state.get("graph_metrics", {})

        # Generate enhanced dashboard data structure
        enhanced_dashboard_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "graph_enhanced": True,
                "date_range": {
                    "cutoff_date": state["cutoff_date"],
                    "today": state["today"]
                },
                "execution_metrics": execution_metrics,
                "graph_metrics": graph_metrics
            },
            "articles": validated_data.get("articles", []),
            "statistics": validated_data.get("statistics", {}),
            "insights": insights,

            # Graph-enhanced features
            "incident_clusters": incident_clusters,
            "incident_timeline": incident_timeline,
            "graph_analysis": graph_analysis,
            "cross_temporal_duplicates": state.get("cross_temporal_duplicates", []),

            # Enhanced dashboard components
            "dashboard_enhancements": {
                "cluster_visualization": self._prepare_cluster_visualization_data(incident_clusters),
                "timeline_visualization": self._prepare_timeline_visualization_data(incident_timeline),
                "network_graph_data": self._prepare_network_graph_data(graph_analysis),
                "deduplication_stats": self._prepare_deduplication_stats(state)
            },

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
            "graph_enhanced_features": True,
            "success_rate": "100%" if not state.get("errors") else f"{((len(NEWS_SOURCES) + len(CATEGORY_SEARCHES)) - len(state.get('errors', []))) / (len(NEWS_SOURCES) + len(CATEGORY_SEARCHES)) * 100:.1f}%"
        }

        final_graph_metrics = {
            **graph_metrics,
            "dashboard_generation_duration": dashboard_duration,
            "total_graph_processing_time": sum([
                graph_metrics.get("validation_duration", 0),
                graph_metrics.get("analysis_duration", 0),
                dashboard_duration
            ])
        }

        state_update = {
            "dashboard_data": enhanced_dashboard_data,
            "execution_metrics": final_metrics,
            "graph_metrics": final_graph_metrics
        }

        log_workflow_state(state_update, "graph_dashboard_generation")

        logger.info(
            "Graph-enhanced dashboard generation completed",
            total_articles=len(enhanced_dashboard_data["articles"]),
            incident_clusters=len(incident_clusters),
            incident_timeline_entries=len(incident_timeline),
            total_duration_seconds=total_duration,
            graph_processing_time=final_graph_metrics["total_graph_processing_time"]
        )

        # Save results to database with graph enhancements
        try:
            await save_workflow_results(state)
            logger.info("Graph-enhanced workflow results saved to database")
        except Exception as db_error:
            logger.error("Failed to save graph-enhanced workflow results", error=str(db_error))

        return state_update

    except Exception as e:
        logger.error("Graph-enhanced dashboard generation failed", error=str(e), exc_info=True)
        return {
            "dashboard_data": {"error": str(e)},
            "errors": [{
                "node": "graph_dashboard_generation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }


# Helper functions for graph analysis
def _analyze_incident_clusters(clusters: List[List[Dict]]) -> Dict:
    """Analyze incident clusters for insights."""
    if not clusters:
        return {"analysis": "No incident clusters found"}

    return {
        "largest_cluster_size": max(len(c) for c in clusters),
        "average_cluster_size": sum(len(c) for c in clusters) / len(clusters),
        "cluster_severity_distribution": {
            severity: len([c for c in clusters
                         if any(a.get("severity") == severity for a in c)])
            for severity in ["high", "medium", "low"]
        }
    }


def _find_longest_incident(timeline: List[Dict]) -> Dict:
    """Find the incident with the longest development timeline."""
    if not timeline:
        return {}

    longest = max(timeline, key=lambda x: len(x.get("development_stages", [])))
    return {
        "incident_id": longest.get("incident_id", ""),
        "incident_type": longest.get("incident_type", ""),
        "development_stages": len(longest.get("development_stages", [])),
        "total_articles": longest.get("total_articles", 0)
    }


def _summarize_incident_timelines(timeline: List[Dict]) -> Dict:
    """Summarize all incident timelines."""
    if not timeline:
        return {"summary": "No timeline data available"}

    return {
        "total_incidents_tracked": len(timeline),
        "incidents_with_multiple_stages": len([t for t in timeline
                                             if len(t.get("development_stages", [])) > 1]),
        "average_development_stages": sum(len(t.get("development_stages", []))
                                        for t in timeline) / len(timeline)
    }


def _calculate_deduplication_effectiveness(state: WorkflowState) -> Dict:
    """Calculate deduplication effectiveness metrics."""
    total_input = len(state.get("phase1_articles", [])) + len(state.get("phase2_articles", []))
    duplicates_removed = len(state.get("cross_temporal_duplicates", []))
    final_count = len(state.get("validated_articles", {}).get("articles", []))

    return {
        "total_input_articles": total_input,
        "duplicates_removed": duplicates_removed,
        "final_unique_articles": final_count,
        "deduplication_rate": (duplicates_removed / total_input * 100) if total_input > 0 else 0,
        "uniqueness_rate": (final_count / total_input * 100) if total_input > 0 else 0
    }


def _identify_persistent_incidents(timeline: List[Dict]) -> List[Dict]:
    """Identify incidents that persist across multiple days."""
    persistent = []
    for incident in timeline:
        stages = incident.get("development_stages", [])
        if len(stages) > 2:  # More than 2 days of development
            persistent.append({
                "incident_id": incident.get("incident_id", ""),
                "incident_type": incident.get("incident_type", ""),
                "duration_days": len(stages),
                "severity": incident.get("severity", "unknown")
            })

    return sorted(persistent, key=lambda x: x["duration_days"], reverse=True)


def _generate_graph_enhanced_recommendations(
    clusters: List[List[Dict]],
    timeline: List[Dict],
    base_insights: Dict
) -> List[Dict]:
    """Generate recommendations enhanced with graph insights."""
    recommendations = []

    # Multi-source incident recommendations
    major_clusters = [c for c in clusters if len(c) >= 3]
    for cluster in major_clusters[:3]:  # Top 3 major incidents
        primary_article = cluster[0]
        recommendations.append({
            "type": "multi_source_incident",
            "priority": "high",
            "title": f"Multi-source incident confirmed: {primary_article.get('incident_type', 'Unknown')}",
            "description": f"Incident reported by {len(cluster)} sources, requiring immediate attention",
            "affected_areas": list(set().union(*[a.get("ports", []) for a in cluster])),
            "confidence": "high",
            "sources_count": len(cluster)
        })

    # Persistent incident recommendations
    long_incidents = [t for t in timeline if len(t.get("development_stages", [])) > 3]
    for incident in long_incidents[:2]:  # Top 2 long-running incidents
        recommendations.append({
            "type": "persistent_incident",
            "priority": "medium",
            "title": f"Long-developing incident: {incident.get('incident_type', 'Unknown')}",
            "description": f"Incident developing over {len(incident.get('development_stages', []))} days",
            "development_stages": len(incident.get("development_stages", [])),
            "confidence": "medium"
        })

    return recommendations


def _prepare_cluster_visualization_data(clusters: List[List[Dict]]) -> Dict:
    """Prepare data for cluster visualization."""
    return {
        "nodes": [
            {
                "id": f"cluster_{i}",
                "size": len(cluster),
                "severity": max(a.get("severity", "low") for a in cluster),
                "category": cluster[0].get("category", "unknown") if cluster else "unknown",
                "articles": len(cluster)
            }
            for i, cluster in enumerate(clusters)
        ],
        "total_clusters": len(clusters),
        "largest_cluster": max(len(c) for c in clusters) if clusters else 0
    }


def _prepare_timeline_visualization_data(timeline: List[Dict]) -> Dict:
    """Prepare data for timeline visualization."""
    return {
        "incidents": [
            {
                "id": incident.get("incident_id", ""),
                "start_date": incident.get("date_range", {}).get("start", ""),
                "end_date": incident.get("date_range", {}).get("end", ""),
                "stages": len(incident.get("development_stages", [])),
                "severity": incident.get("severity", "unknown"),
                "type": incident.get("incident_type", "")
            }
            for incident in timeline
        ],
        "total_incidents": len(timeline)
    }


def _prepare_network_graph_data(graph_analysis: Dict) -> Dict:
    """Prepare data for network graph visualization."""
    stats = graph_analysis.get("statistics", {})
    return {
        "nodes_count": stats.get("total_nodes", 0),
        "edges_count": stats.get("total_edges", 0),
        "connected_components": stats.get("connected_components", 0),
        "density": stats.get("density", 0),
        "clustering_coefficient": stats.get("average_clustering", 0)
    }


def _prepare_deduplication_stats(state: WorkflowState) -> Dict:
    """Prepare deduplication statistics for dashboard."""
    return {
        "cross_temporal_duplicates": len(state.get("cross_temporal_duplicates", [])),
        "incident_clusters": len(state.get("incident_clusters", [])),
        "timeline_incidents": len(state.get("incident_timeline", [])),
        "deduplication_effectiveness": _calculate_deduplication_effectiveness(state)
    }


def create_graph_enhanced_workflow() -> StateGraph:
    """
    Create and configure the graph-enhanced LangGraph workflow.

    Returns:
        Configured StateGraph with all nodes and edges including graph enhancements
    """
    logger.info("Creating graph-enhanced LangGraph workflow")

    # Initialize workflow graph
    workflow = StateGraph(WorkflowState)

    # Add nodes with graph enhancements
    workflow.add_node("initialize_dates", initialize_dates_node)
    workflow.add_node("phase1_scraping", phase1_scraping_node)
    workflow.add_node("phase2_searching", phase2_searching_node)
    workflow.add_node("graph_validation", graph_validation_node)
    workflow.add_node("enhanced_analysis", enhanced_analysis_node)
    workflow.add_node("graph_dashboard_generation", graph_dashboard_generation_node)

    # Add edges (workflow flow)
    workflow.set_entry_point("initialize_dates")
    workflow.add_edge("initialize_dates", "phase1_scraping")
    workflow.add_edge("phase1_scraping", "phase2_searching")
    workflow.add_edge("phase2_searching", "graph_validation")
    workflow.add_edge("graph_validation", "enhanced_analysis")
    workflow.add_edge("enhanced_analysis", "graph_dashboard_generation")
    workflow.add_edge("graph_dashboard_generation", END)

    logger.info("Graph-enhanced LangGraph workflow created successfully")
    return workflow


def create_graph_enhanced_workflow_with_checkpointing() -> StateGraph:
    """
    Create graph-enhanced workflow with PostgreSQL checkpointing enabled.

    Returns:
        Compiled StateGraph with checkpointing and graph enhancements
    """
    settings = get_settings()

    # Create base workflow
    workflow = create_graph_enhanced_workflow()

    if settings.checkpoint_enabled:
        try:
            # Initialize PostgreSQL checkpointer
            checkpointer = PostgresSaver.from_conn_string(settings.postgres_url)

            # Compile with checkpointing
            compiled_workflow = workflow.compile(checkpointer=checkpointer)

            logger.info("Graph-enhanced workflow compiled with PostgreSQL checkpointing")
            return compiled_workflow

        except Exception as e:
            logger.warning(
                "Failed to enable checkpointing for graph workflow, using memory-only mode",
                error=str(e)
            )

    # Fallback to memory-only compilation
    compiled_workflow = workflow.compile()
    logger.info("Graph-enhanced workflow compiled without checkpointing")
    return compiled_workflow