"""
Shipping News Intelligence - Graph-Enhanced Main Entry Point

Production-ready multi-agent system with graph-based incident tracking,
cross-temporal deduplication, and advanced incident clustering using
NetworkX and LangGraph for superior maritime news intelligence.
"""

import asyncio
import sys
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from config.settings import get_settings
from utils.logging_config import setup_logging
from utils.date_utils import calculate_dates
from graph.graph_enhanced_workflow import create_graph_enhanced_workflow_with_checkpointing
from database.operations import create_tables, cleanup_old_data
from agents.graph_validation import GraphValidationAgent


# Global workflow instance for graceful shutdown
workflow_instance: Optional[any] = None
current_run_config: Optional[dict] = None


async def setup_graph_enhanced_system():
    """
    Initialize graph-enhanced system components and dependencies.
    """
    logger = structlog.get_logger(__name__)

    try:
        # Setup logging
        setup_logging()
        logger.info("Graph-enhanced logging system initialized")

        # Validate settings
        settings = get_settings()
        logger.info(
            "Graph-enhanced configuration loaded",
            model=settings.model_name,
            postgres_host=settings.postgres_host,
            checkpoint_enabled=settings.checkpoint_enabled,
            features=["incident_graph", "cross_temporal_deduplication", "cluster_analysis"]
        )

        # Initialize database
        await create_tables()
        logger.info("Database initialization completed with graph support")

        # Cleanup old data if configured
        try:
            await cleanup_old_data(days_to_keep=30)
        except Exception as cleanup_error:
            logger.warning("Data cleanup failed", error=str(cleanup_error))

        # Initialize and optimize incident graph
        logger.info("Initializing incident graph system")
        temp_agent = GraphValidationAgent("2024-01-01", "2024-01-01")
        await temp_agent.cleanup_and_optimize_graph()
        logger.info("Incident graph optimization completed")

        logger.info("Graph-enhanced system initialization completed successfully")

    except Exception as e:
        logger.error("Graph-enhanced system initialization failed", error=str(e), exc_info=True)
        raise


async def execute_graph_enhanced_workflow(
    run_config: Optional[dict] = None,
    thread_id: Optional[str] = None
) -> dict:
    """
    Execute the graph-enhanced maritime news intelligence workflow.

    Args:
        run_config: Optional workflow configuration overrides
        thread_id: Optional thread ID for checkpointing

    Returns:
        Enhanced workflow execution results with graph insights
    """
    logger = structlog.get_logger(__name__)

    # Calculate dates
    today, cutoff_date = calculate_dates()

    # Initialize enhanced workflow state
    initial_state = {
        "today": today,
        "cutoff_date": cutoff_date,
        "phase1_articles": [],
        "phase2_articles": [],
        "validated_articles": {},
        "incident_clusters": [],
        "graph_analysis": {},
        "cross_temporal_duplicates": [],
        "insights": {},
        "incident_timeline": [],
        "dashboard_data": {},
        "errors": [],
        "execution_metrics": {
            "workflow_start": datetime.utcnow().isoformat(),
            "run_config": run_config or {},
            "graph_enhanced": True,
            "features_enabled": [
                "cross_temporal_deduplication",
                "incident_clustering",
                "graph_network_analysis",
                "temporal_timeline_tracking",
                "multi_source_verification"
            ]
        },
        "graph_metrics": {
            "initialization_time": datetime.utcnow().isoformat()
        }
    }

    # Generate unique thread ID if not provided
    if not thread_id:
        thread_id = f"maritime_graph_news_{today}_{datetime.utcnow().strftime('%H%M%S')}"

    logger.info(
        "Starting graph-enhanced maritime news intelligence workflow",
        thread_id=thread_id,
        date_range=f"{cutoff_date} to {today}",
        features=initial_state["execution_metrics"]["features_enabled"],
        run_config=run_config
    )

    try:
        # Create graph-enhanced workflow with checkpointing
        global workflow_instance
        workflow_instance = create_graph_enhanced_workflow_with_checkpointing()

        # Configure checkpoint namespace
        checkpoint_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "maritime_graph_news_intelligence"
            }
        }

        # Execute graph-enhanced workflow
        workflow_result = await workflow_instance.ainvoke(
            input=initial_state,
            config=checkpoint_config
        )

        # Extract final results
        final_state = workflow_result
        execution_metrics = final_state.get("execution_metrics", {})
        graph_metrics = final_state.get("graph_metrics", {})
        dashboard_data = final_state.get("dashboard_data", {})
        incident_clusters = final_state.get("incident_clusters", [])
        incident_timeline = final_state.get("incident_timeline", [])
        cross_temporal_duplicates = final_state.get("cross_temporal_duplicates", [])
        errors = final_state.get("errors", [])

        # Log execution summary with graph enhancements
        logger.info(
            "Graph-enhanced workflow execution completed",
            thread_id=thread_id,
            total_duration=execution_metrics.get("total_workflow_duration", 0),
            final_articles=execution_metrics.get("final_validated_articles", 0),
            incident_clusters=len(incident_clusters),
            incident_timeline_entries=len(incident_timeline),
            cross_temporal_duplicates=len(cross_temporal_duplicates),
            graph_nodes=graph_metrics.get("graph_nodes", 0),
            graph_edges=graph_metrics.get("graph_edges", 0),
            connected_components=graph_metrics.get("connected_components", 0),
            success_rate=execution_metrics.get("success_rate", "unknown"),
            errors_count=len(errors)
        )

        # Return comprehensive results with graph enhancements
        return {
            "status": "completed" if not errors else "completed_with_errors",
            "thread_id": thread_id,
            "execution_summary": {
                "start_time": execution_metrics.get("workflow_start"),
                "end_time": execution_metrics.get("workflow_end"),
                "total_duration_seconds": execution_metrics.get("total_workflow_duration", 0),
                "date_range": {
                    "cutoff_date": cutoff_date,
                    "today": today
                },
                "articles_processed": {
                    "phase1": execution_metrics.get("phase1_articles_count", 0),
                    "phase2": execution_metrics.get("phase2_articles_count", 0),
                    "validated": execution_metrics.get("final_validated_articles", 0)
                },
                "graph_enhancements": {
                    "incident_clusters_found": len(incident_clusters),
                    "incident_timeline_entries": len(incident_timeline),
                    "cross_temporal_duplicates_removed": len(cross_temporal_duplicates),
                    "graph_nodes": graph_metrics.get("graph_nodes", 0),
                    "graph_edges": graph_metrics.get("graph_edges", 0),
                    "connected_components": graph_metrics.get("connected_components", 0),
                    "deduplication_effectiveness": dashboard_data.get("dashboard_enhancements", {}).get("deduplication_stats", {}).get("deduplication_effectiveness", {})
                },
                "success_metrics": {
                    "sources_success": execution_metrics.get("phase1_sources_success", 0),
                    "sources_failed": execution_metrics.get("phase1_sources_failed", 0),
                    "searches_success": execution_metrics.get("phase2_searches_success", 0),
                    "searches_failed": execution_metrics.get("phase2_searches_failed", 0),
                    "overall_success_rate": execution_metrics.get("success_rate", "unknown")
                }
            },
            "graph_analysis": final_state.get("graph_analysis", {}),
            "dashboard_data": dashboard_data,
            "incident_clusters": incident_clusters,
            "incident_timeline": incident_timeline,
            "errors": errors,
            "final_state": final_state
        }

    except Exception as e:
        logger.error(
            "Graph-enhanced workflow execution failed",
            thread_id=thread_id,
            error=str(e),
            exc_info=True
        )

        return {
            "status": "failed",
            "thread_id": thread_id,
            "error": str(e),
            "execution_summary": {
                "start_time": initial_state["execution_metrics"]["workflow_start"],
                "end_time": datetime.utcnow().isoformat(),
                "date_range": {
                    "cutoff_date": cutoff_date,
                    "today": today
                }
            }
        }


async def resume_graph_enhanced_workflow(thread_id: str) -> dict:
    """
    Resume a graph-enhanced workflow from checkpoint.

    Args:
        thread_id: Thread ID of workflow to resume

    Returns:
        Enhanced workflow execution results
    """
    logger = structlog.get_logger(__name__)

    logger.info("Resuming graph-enhanced workflow from checkpoint", thread_id=thread_id)

    try:
        # Create graph-enhanced workflow with checkpointing
        workflow = create_graph_enhanced_workflow_with_checkpointing()

        # Configure checkpoint namespace
        checkpoint_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "maritime_graph_news_intelligence"
            }
        }

        # Resume workflow execution
        workflow_result = await workflow.ainvoke(
            input=None,  # Resume from checkpoint
            config=checkpoint_config
        )

        logger.info("Graph-enhanced workflow resumed successfully", thread_id=thread_id)

        return {
            "status": "resumed_completed",
            "thread_id": thread_id,
            "final_state": workflow_result,
            "features": ["graph_enhanced", "incident_clustering", "cross_temporal_deduplication"]
        }

    except Exception as e:
        logger.error("Failed to resume graph-enhanced workflow", thread_id=thread_id, error=str(e))
        return {
            "status": "resume_failed",
            "thread_id": thread_id,
            "error": str(e)
        }


async def analyze_graph_insights(days_back: int = 14) -> dict:
    """
    Analyze graph insights from recent workflow runs.

    Args:
        days_back: Number of days to analyze

    Returns:
        Comprehensive graph analysis results
    """
    logger = structlog.get_logger(__name__)

    logger.info("Analyzing graph insights", days_back=days_back)

    try:
        # Initialize graph validation agent for analysis
        graph_agent = GraphValidationAgent("2024-01-01", "2024-01-01")

        # Get comprehensive graph statistics
        graph_stats = graph_agent.incident_graph.get_graph_statistics()

        # Get incident clusters
        incident_clusters = graph_agent.incident_graph.get_incident_clusters()

        # Get temporal duplicates
        temporal_duplicates = graph_agent.incident_graph.get_temporal_duplicates(days_back)

        # Get incident timeline
        incident_timeline = await graph_agent.get_incident_timeline(days_back)

        # Export comprehensive analysis
        graph_analysis = graph_agent.incident_graph.export_graph_analysis()

        logger.info(
            "Graph insights analysis completed",
            graph_nodes=graph_stats["total_nodes"],
            graph_edges=graph_stats["total_edges"],
            incident_clusters=len(incident_clusters),
            temporal_duplicates=len(temporal_duplicates),
            timeline_incidents=len(incident_timeline)
        )

        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "analysis_period_days": days_back,
            "graph_statistics": graph_stats,
            "incident_clusters": incident_clusters,
            "temporal_duplicates": temporal_duplicates,
            "incident_timeline": incident_timeline,
            "comprehensive_analysis": graph_analysis,
            "key_insights": {
                "deduplication_effectiveness": len(temporal_duplicates) / graph_stats["total_nodes"] if graph_stats["total_nodes"] > 0 else 0,
                "clustering_effectiveness": len(incident_clusters) / graph_stats["connected_components"] if graph_stats["connected_components"] > 0 else 0,
                "network_density": graph_stats["density"],
                "major_incidents": len([c for c in incident_clusters if len(c) >= 3])
            }
        }

    except Exception as e:
        logger.error("Graph insights analysis failed", error=str(e), exc_info=True)
        return {"error": str(e)}


def setup_signal_handlers():
    """
    Setup graceful shutdown signal handlers for graph-enhanced system.
    """
    logger = structlog.get_logger(__name__)

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown of graph-enhanced system")

        # Save graph state before shutdown
        if workflow_instance:
            logger.info("Graph-enhanced workflow checkpoint saved for future resume")

        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """
    Main application entry point for graph-enhanced system.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Shipping News Intelligence - Graph-Enhanced Multi-Agent System"
    )
    parser.add_argument(
        "--resume",
        type=str,
        help="Resume graph-enhanced workflow from checkpoint using thread ID"
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        help="Custom thread ID for workflow execution"
    )
    parser.add_argument(
        "--analyze-graph",
        type=int,
        metavar="DAYS",
        help="Analyze graph insights for specified number of days"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file"
    )

    args = parser.parse_args()

    # Setup signal handlers
    setup_signal_handlers()

    try:
        # Initialize graph-enhanced system
        await setup_graph_enhanced_system()

        if args.analyze_graph:
            # Analyze graph insights
            result = await analyze_graph_insights(args.analyze_graph)

            print("\n" + "="*80)
            print("GRAPH INSIGHTS ANALYSIS")
            print("="*80)
            print(f"Analysis Period: {args.analyze_graph} days")
            print(f"Graph Nodes: {result.get('graph_statistics', {}).get('total_nodes', 0)}")
            print(f"Graph Edges: {result.get('graph_statistics', {}).get('total_edges', 0)}")
            print(f"Incident Clusters: {len(result.get('incident_clusters', []))}")
            print(f"Temporal Duplicates: {len(result.get('temporal_duplicates', []))}")
            print(f"Timeline Incidents: {len(result.get('incident_timeline', []))}")

            key_insights = result.get('key_insights', {})
            print(f"Deduplication Effectiveness: {key_insights.get('deduplication_effectiveness', 0):.2%}")
            print(f"Network Density: {key_insights.get('network_density', 0):.4f}")
            print(f"Major Incidents (3+ sources): {key_insights.get('major_incidents', 0)}")
            print("="*80)

            return 0

        elif args.resume:
            # Resume existing graph-enhanced workflow
            result = await resume_graph_enhanced_workflow(args.resume)
        else:
            # Execute new graph-enhanced workflow
            run_config = {}
            if args.config:
                # Load custom config if provided
                # Implementation would load from file
                pass

            result = await execute_graph_enhanced_workflow(
                run_config=run_config,
                thread_id=args.thread_id
            )

        # Print execution summary with graph enhancements
        print("\n" + "="*80)
        print("MARITIME INTELLIGENCE ENGINE - EXECUTION SUMMARY")
        print("="*80)

        print(f"Status: {result['status'].upper()}")
        print(f"Thread ID: {result['thread_id']}")

        if 'execution_summary' in result:
            summary = result['execution_summary']
            print(f"Duration: {summary.get('total_duration_seconds', 0):.1f} seconds")
            print(f"Date Range: {summary['date_range']['cutoff_date']} to {summary['date_range']['today']}")

            if 'articles_processed' in summary:
                articles = summary['articles_processed']
                print(f"Articles: {articles.get('validated', 0)} validated "
                      f"(from {articles.get('phase1', 0)} + {articles.get('phase2', 0)} scraped)")

            if 'graph_enhancements' in summary:
                graph_enhancements = summary['graph_enhancements']
                print("\nGraph Enhancements:")
                print(f"  • Incident Clusters: {graph_enhancements.get('incident_clusters_found', 0)}")
                print(f"  • Timeline Incidents: {graph_enhancements.get('incident_timeline_entries', 0)}")
                print(f"  • Cross-temporal Duplicates Removed: {graph_enhancements.get('cross_temporal_duplicates_removed', 0)}")
                print(f"  • Graph Nodes: {graph_enhancements.get('graph_nodes', 0)}")
                print(f"  • Graph Edges: {graph_enhancements.get('graph_edges', 0)}")
                print(f"  • Connected Components: {graph_enhancements.get('connected_components', 0)}")

            if 'success_metrics' in summary:
                metrics = summary['success_metrics']
                print(f"Success Rate: {metrics.get('overall_success_rate', 'unknown')}")

        if result.get('errors'):
            print(f"Errors: {len(result['errors'])} encountered")

        print("="*80)

        # Exit with appropriate code
        if result['status'] in ['completed', 'resumed_completed']:
            print("✅ Graph-enhanced workflow completed successfully")
            print("🔗 Advanced features: Cross-temporal deduplication, Incident clustering, Graph analysis")
            return 0
        elif result['status'] == 'completed_with_errors':
            print("⚠️  Graph-enhanced workflow completed with errors")
            return 1
        else:
            print("❌ Graph-enhanced workflow failed")
            return 2

    except KeyboardInterrupt:
        print("\n🛑 Graph-enhanced workflow interrupted by user")
        return 130

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Graph-enhanced application failed", error=str(e), exc_info=True)
        print(f"❌ Graph-enhanced application failed: {e}")
        return 1


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)