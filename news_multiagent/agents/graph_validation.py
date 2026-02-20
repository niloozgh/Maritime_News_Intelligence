"""
Graph-Enhanced Validation Agent

Enhanced validation agent that uses graph-based deduplication and
incident clustering for superior article processing.
"""

import asyncio
from typing import Dict, List, Set, Tuple, Optional
import structlog
from datetime import datetime

from .validation import ValidationAgent
from ..graph.incident_graph import IncidentGraph
from ..utils.logging_config import LoggingMixin
from ..database.operations import get_recent_articles

logger = structlog.get_logger(__name__)


class GraphValidationAgent(ValidationAgent):
    """
    Enhanced validation agent with graph-based deduplication and clustering.

    Features:
    - Cross-temporal deduplication using incident graph
    - Topic clustering using connected components
    - Persistent incident tracking across workflow runs
    - Enhanced similarity detection
    """

    def __init__(
        self,
        cutoff_date: str,
        today: str,
        similarity_threshold: float = 0.75,
        temporal_window_days: int = 30,
        graph_storage_path: str = "./data/incident_graph.pkl"
    ):
        """
        Initialize graph-enhanced validation agent.

        Args:
            cutoff_date: Earliest acceptable date (YYYY-MM-DD)
            today: Current date (YYYY-MM-DD)
            similarity_threshold: Threshold for article similarity
            temporal_window_days: Days to look back for cross-temporal deduplication
            graph_storage_path: Path to persist incident graph
        """
        super().__init__(cutoff_date, today, similarity_threshold)

        # Initialize incident graph
        self.incident_graph = IncidentGraph(
            similarity_threshold=similarity_threshold,
            temporal_window_days=temporal_window_days,
            storage_path=graph_storage_path
        )

        self.logger.info(
            "Graph validation agent initialized",
            graph_nodes=self.incident_graph.graph.number_of_nodes(),
            graph_edges=self.incident_graph.graph.number_of_edges(),
            temporal_window=temporal_window_days
        )

    async def validate_and_deduplicate(
        self,
        phase1_articles: List[Dict],
        phase2_articles: List[Dict]
    ) -> Dict[str, any]:
        """
        Enhanced validation with graph-based deduplication and clustering.

        Args:
            phase1_articles: Articles from source scraping
            phase2_articles: Articles from category searches

        Returns:
            Enhanced validation results with graph analysis
        """
        self.log_operation_start(
            "graph_validation",
            phase1_count=len(phase1_articles),
            phase2_count=len(phase2_articles)
        )

        try:
            # Step 1: Basic validation (inherited from parent)
            all_articles = phase1_articles + phase2_articles
            valid_articles = []

            for article in all_articles:
                if self._validate_article_structure(article):
                    valid_articles.append(article)

            self.logger.info(
                "Basic validation completed",
                input_articles=len(all_articles),
                valid_articles=len(valid_articles)
            )

            # Step 2: Load recent articles for cross-temporal analysis
            await self._load_recent_articles_to_graph()

            # Step 3: Graph-based deduplication and clustering
            new_articles, deduplicated_articles = self.incident_graph.add_articles(valid_articles)

            self.logger.info(
                "Graph-based deduplication completed",
                new_articles=len(new_articles),
                deduplicated_articles=len(deduplicated_articles)
            )

            # Step 4: Get incident clusters
            incident_clusters = self.incident_graph.get_incident_clusters()

            # Step 5: Enhanced quality filtering with graph context
            final_articles = self._apply_graph_enhanced_filtering(new_articles, incident_clusters)

            # Step 6: Priority sorting with graph insights
            sorted_articles = self._sort_with_graph_priority(final_articles, incident_clusters)

            # Step 7: Generate comprehensive statistics
            graph_stats = self.incident_graph.get_graph_statistics()
            enhanced_stats = self._generate_enhanced_validation_stats(
                all_articles, valid_articles, new_articles, final_articles,
                incident_clusters, deduplicated_articles, graph_stats
            )

            # Step 8: Export graph analysis
            graph_analysis = self.incident_graph.export_graph_analysis()

            self.log_operation_success(
                "graph_validation",
                final_articles=len(sorted_articles),
                incident_clusters=len(incident_clusters),
                graph_nodes=self.incident_graph.graph.number_of_nodes()
            )

            return {
                "articles": sorted_articles,
                "statistics": enhanced_stats,
                "incident_clusters": incident_clusters,
                "graph_analysis": graph_analysis,
                "deduplicated_articles": deduplicated_articles,
                "validation_summary": {
                    "total_processed": len(all_articles),
                    "valid_after_structure_check": len(valid_articles),
                    "new_articles_added": len(new_articles),
                    "cross_temporal_duplicates": len(deduplicated_articles),
                    "final_article_count": len(sorted_articles),
                    "incident_clusters_found": len(incident_clusters),
                    "graph_nodes_total": self.incident_graph.graph.number_of_nodes(),
                    "graph_edges_total": self.incident_graph.graph.number_of_edges()
                }
            }

        except Exception as e:
            self.log_operation_error("graph_validation", e)
            return {
                "articles": [],
                "statistics": {},
                "incident_clusters": [],
                "graph_analysis": {},
                "validation_summary": {"error": str(e)}
            }

    async def _load_recent_articles_to_graph(self):
        """Load recent articles from database into graph for cross-temporal analysis."""
        try:
            # Get articles from last temporal window
            recent_articles = await get_recent_articles(
                days=self.incident_graph.temporal_window_days,
                limit=1000
            )

            if recent_articles:
                # Convert database articles to graph format
                graph_articles = []
                for article in recent_articles:
                    graph_article = {
                        "url": article["url"],
                        "title": article["title"],
                        "date": article["publication_date"],
                        "source": article["source"],
                        "category": article["category"],
                        "severity": article["severity"],
                        "incidentType": article.get("incident_type", ""),
                        "summary": article.get("summary", ""),
                        "ports": article.get("ports", []),
                        "vessels": article.get("vessels", []),
                        "workflow_run_id": article.get("workflow_date", "")
                    }
                    graph_articles.append(graph_article)

                # Add to graph (will handle duplicates automatically)
                self.incident_graph.add_articles(graph_articles)

                self.logger.info(
                    "Loaded recent articles into graph",
                    articles_loaded=len(graph_articles)
                )

        except Exception as e:
            self.logger.warning(
                "Failed to load recent articles into graph",
                error=str(e)
            )

    def _apply_graph_enhanced_filtering(
        self,
        articles: List[Dict],
        incident_clusters: List[List[Dict]]
    ) -> List[Dict]:
        """
        Apply quality filters enhanced with graph context.

        Args:
            articles: New articles to filter
            incident_clusters: Current incident clusters

        Returns:
            Filtered articles with graph-enhanced quality assessment
        """
        filtered_articles = []

        # Create cluster lookup for context
        cluster_lookup = {}
        for cluster in incident_clusters:
            for article in cluster:
                cluster_lookup[article.get("url", "")] = cluster

        for article in articles:
            # Apply basic quality filters
            if not self._basic_quality_check(article):
                continue

            # Enhanced filtering with graph context
            article_url = article["url"]
            related_cluster = cluster_lookup.get(article_url, [])

            # Boost quality score if part of significant incident cluster
            if len(related_cluster) >= 3:  # Multi-source incident
                article["cluster_significance"] = "high"
                article["related_articles_count"] = len(related_cluster)
            elif len(related_cluster) == 2:
                article["cluster_significance"] = "medium"
                article["related_articles_count"] = len(related_cluster)
            else:
                article["cluster_significance"] = "single"
                article["related_articles_count"] = 1

            # Add graph-enhanced metadata
            article["graph_enhanced"] = True

            filtered_articles.append(article)

        self.logger.info(
            "Graph-enhanced filtering completed",
            input_count=len(articles),
            output_count=len(filtered_articles)
        )

        return filtered_articles

    def _sort_with_graph_priority(
        self,
        articles: List[Dict],
        incident_clusters: List[List[Dict]]
    ) -> List[Dict]:
        """
        Sort articles with graph-based priority enhancement.

        Args:
            articles: Articles to sort
            incident_clusters: Incident clusters for priority boosting

        Returns:
            Priority-sorted articles
        """
        def enhanced_sort_key(article: Dict) -> Tuple[int, int, int, str]:
            # Base priority from parent class
            severity_priority = {"high": 3, "medium": 2, "low": 1}
            authority = self._get_source_authority(article["source"])

            # Graph-enhanced priority
            cluster_significance = article.get("cluster_significance", "single")
            cluster_boost = {"high": 3, "medium": 2, "single": 1}

            return (
                -severity_priority.get(article["severity"], 0),
                -cluster_boost.get(cluster_significance, 1),
                -authority,
                -article["date"]  # Newer first
            )

        sorted_articles = sorted(articles, key=enhanced_sort_key)

        # Add ranking information
        for i, article in enumerate(sorted_articles):
            article["graph_priority_rank"] = i + 1

        self.logger.info(
            "Graph-priority sorting completed",
            total_articles=len(sorted_articles),
            high_priority_clusters=len([a for a in sorted_articles
                                      if a.get("cluster_significance") == "high"])
        )

        return sorted_articles

    def _basic_quality_check(self, article: Dict) -> bool:
        """Basic quality checks inherited from parent but extracted."""
        # Check minimum title length
        if len(article["title"].strip()) < 10:
            return False

        # Check for required summary
        if not article.get("summary") or len(article["summary"].strip()) < 20:
            return False

        # Validate incident type
        if not article.get("incidentType"):
            return False

        return True

    def _generate_enhanced_validation_stats(
        self,
        original: List[Dict],
        valid: List[Dict],
        new: List[Dict],
        final: List[Dict],
        clusters: List[List[Dict]],
        duplicates: List[Dict],
        graph_stats: Dict
    ) -> Dict[str, any]:
        """Generate comprehensive validation statistics with graph insights."""
        base_stats = super()._generate_validation_stats(original, valid, new, final)

        # Add graph-specific statistics
        enhanced_stats = {
            **base_stats,
            "graph_statistics": graph_stats,
            "incident_clustering": {
                "total_clusters": len(clusters),
                "multi_source_incidents": len([c for c in clusters if len(c) >= 2]),
                "major_incidents": len([c for c in clusters if len(c) >= 3]),
                "largest_cluster_size": max(len(c) for c in clusters) if clusters else 0,
                "average_cluster_size": sum(len(c) for c in clusters) / len(clusters) if clusters else 0
            },
            "deduplication_effectiveness": {
                "cross_temporal_duplicates_found": len(duplicates),
                "deduplication_rate": len(duplicates) / len(original) if original else 0,
                "unique_incidents_identified": len(clusters),
                "redundancy_reduction": (len(duplicates) / len(original) * 100) if original else 0
            },
            "cluster_analysis": {
                "high_significance_clusters": len([a for a in final
                                                 if a.get("cluster_significance") == "high"]),
                "single_source_articles": len([a for a in final
                                             if a.get("cluster_significance") == "single"]),
                "cluster_coverage_rate": (len(final) - len([a for a in final
                                                          if a.get("cluster_significance") == "single"])) / len(final) if final else 0
            }
        }

        return enhanced_stats

    async def get_incident_timeline(self, days_back: int = 14) -> List[Dict]:
        """
        Generate incident timeline showing how stories developed over time.

        Args:
            days_back: Number of days to analyze

        Returns:
            Timeline of incidents with development tracking
        """
        clusters = self.incident_graph.get_incident_clusters()
        timeline = []

        for i, cluster in enumerate(clusters):
            if len(cluster) < 2:  # Skip single-article clusters
                continue

            # Sort cluster articles by date
            cluster_articles = sorted(cluster, key=lambda x: x.get("date", ""))

            # Create incident timeline
            incident_timeline = {
                "incident_id": f"incident_{i}",
                "incident_type": cluster_articles[0].get("incident_type", "Unknown"),
                "category": cluster_articles[0].get("category", "unknown"),
                "severity": max(a.get("severity", "low") for a in cluster_articles),
                "date_range": {
                    "start": cluster_articles[0].get("date", ""),
                    "end": cluster_articles[-1].get("date", "")
                },
                "development_stages": [],
                "total_articles": len(cluster_articles),
                "sources_involved": list(set(a.get("source", "") for a in cluster_articles)),
                "geographic_impact": {
                    "ports": list(set().union(*[a.get("ports", []) for a in cluster_articles])),
                    "vessels": list(set().union(*[a.get("vessels", []) for a in cluster_articles]))
                }
            }

            # Track development stages
            current_date = None
            current_stage = []

            for article in cluster_articles:
                article_date = article.get("date", "")

                if article_date != current_date:
                    if current_stage:
                        incident_timeline["development_stages"].append({
                            "date": current_date,
                            "articles": current_stage,
                            "stage_summary": self._summarize_stage(current_stage)
                        })

                    current_date = article_date
                    current_stage = [article]
                else:
                    current_stage.append(article)

            # Add final stage
            if current_stage:
                incident_timeline["development_stages"].append({
                    "date": current_date,
                    "articles": current_stage,
                    "stage_summary": self._summarize_stage(current_stage)
                })

            timeline.append(incident_timeline)

        return sorted(timeline, key=lambda x: len(x["development_stages"]), reverse=True)

    def _summarize_stage(self, stage_articles: List[Dict]) -> str:
        """Summarize a development stage of an incident."""
        if len(stage_articles) == 1:
            return f"Initial report from {stage_articles[0].get('source', 'unknown source')}"
        else:
            sources = [a.get('source', 'unknown') for a in stage_articles]
            return f"Multi-source confirmation ({len(sources)} sources: {', '.join(sources[:3])}{'...' if len(sources) > 3 else ''})"

    async def cleanup_and_optimize_graph(self):
        """Cleanup old articles and optimize graph performance."""
        self.log_operation_start("graph_cleanup")

        try:
            # Remove articles older than temporal window
            self.incident_graph.cleanup_old_articles(days_to_keep=90)

            # Get optimization statistics
            stats = self.incident_graph.get_graph_statistics()

            self.log_operation_success(
                "graph_cleanup",
                nodes_remaining=stats["total_nodes"],
                edges_remaining=stats["total_edges"],
                connected_components=stats["connected_components"]
            )

            return {
                "cleanup_completed": True,
                "graph_statistics": stats,
                "optimization_metrics": {
                    "nodes_remaining": stats["total_nodes"],
                    "edges_remaining": stats["total_edges"],
                    "density": stats["density"],
                    "clustering_coefficient": stats["average_clustering"]
                }
            }

        except Exception as e:
            self.log_operation_error("graph_cleanup", e)
            return {"cleanup_completed": False, "error": str(e)}