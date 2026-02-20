"""
Graph-Based Incident Tracking for Maritime News Intelligence

Implements a persistent graph structure to handle:
1. Topic clustering (same incident from multiple sources)
2. Cross-temporal deduplication (same news across different dates)
3. Connected components analysis for incident relationships
"""

import networkx as nx
import hashlib
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from difflib import SequenceMatcher
import structlog
import json
import pickle
from pathlib import Path
from collections import defaultdict
import time

from ..utils.logging_config import LoggingMixin
from ..database.operations import get_recent_articles

logger = structlog.get_logger(__name__)


@dataclass
class ArticleNode:
    """Represents an article node in the incident graph."""

    url: str
    title: str
    date: str
    source: str
    category: str
    severity: str
    content_hash: str
    incident_type: str
    ports: List[str]
    vessels: List[str]
    summary: str
    workflow_run_id: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "date": self.date,
            "source": self.source,
            "category": self.category,
            "severity": self.severity,
            "content_hash": self.content_hash,
            "incident_type": self.incident_type,
            "ports": self.ports,
            "vessels": self.vessels,
            "summary": self.summary,
            "workflow_run_id": self.workflow_run_id
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ArticleNode':
        """Create from dictionary."""
        return cls(**data)


class IncidentGraph(LoggingMixin):
    """
    Graph-based incident tracking system for maritime news.

    Features:
    - Topic clustering using connected components
    - Cross-temporal deduplication
    - Similarity-based edge creation
    - Persistent graph storage
    """

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        temporal_window_days: int = 30,
        storage_path: str = "./data/incident_graph.pkl",
        enable_performance_optimizations: bool = True
    ):
        """
        Initialize incident graph.

        Args:
            similarity_threshold: Threshold for creating similarity edges
            temporal_window_days: Days to look back for cross-temporal deduplication
            storage_path: Path to persist graph data
            enable_performance_optimizations: Enable fast indexing and caching
        """
        self.similarity_threshold = similarity_threshold
        self.temporal_window_days = temporal_window_days
        self.storage_path = Path(storage_path)
        self.enable_performance_optimizations = enable_performance_optimizations

        # Create NetworkX directed graph
        self.graph = nx.DiGraph()

        # Performance optimization indexes
        if self.enable_performance_optimizations:
            self._init_performance_indexes()

        # Create data directory if needed
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing graph if available
        self._load_graph()

        self.logger.info(
            "Incident graph initialized",
            nodes=self.graph.number_of_nodes(),
            edges=self.graph.number_of_edges(),
            similarity_threshold=similarity_threshold,
            temporal_window=temporal_window_days,
            performance_optimizations=enable_performance_optimizations
        )

    def _init_performance_indexes(self):
        """Initialize performance optimization indexes."""
        # Fast content hash lookup for exact duplicates
        self.content_hash_index = {}  # hash -> node_id
        self.url_index = {}  # url -> node_id

        # Category-based indexes for faster similarity search
        self.category_index = defaultdict(set)  # category -> set of node_ids

        # Temporal indexes for time-based queries
        self.date_index = defaultdict(set)  # date -> set of node_ids

        # Similarity calculation cache
        self.similarity_cache = {}  # (node1_hash, node2_hash) -> similarity_score
        self.max_cache_size = 1000

        # Topic continuation tracking
        self.topic_timelines = defaultdict(list)  # topic_signature -> chronological articles

        self.logger.debug("Performance indexes initialized")

    def add_articles(self, articles: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Add articles to graph with optimized deduplication and clustering.

        Args:
            articles: List of article dictionaries

        Returns:
            Tuple of (new_articles, deduplicated_articles)
        """
        start_time = time.time()
        self.log_operation_start("add_articles", article_count=len(articles))

        new_articles = []
        deduplicated_articles = []
        performance_stats = {
            "hash_lookups": 0,
            "similarity_calculations": 0,
            "cache_hits": 0,
            "temporal_filtered": 0
        }

        for article in articles:
            # Convert to ArticleNode
            article_node = self._create_article_node(article)

            # OPTIMIZATION 1: Fast exact duplicate detection using indexes
            duplicate_node_id = self._find_duplicate_optimized(article_node, performance_stats)

            if duplicate_node_id:
                # Found duplicate - merge information
                self._merge_duplicate_information(duplicate_node_id, article_node)
                deduplicated_articles.append(article)

                self.logger.debug(
                    "Duplicate article detected",
                    new_url=article_node.url,
                    existing_node_id=duplicate_node_id,
                    detection_method="hash_index"
                )

            else:
                # Add as new node
                node_id = self._generate_node_id(article_node)
                self.graph.add_node(node_id, **article_node.to_dict())

                # OPTIMIZATION 2: Update performance indexes
                if self.enable_performance_optimizations:
                    self._update_indexes(node_id, article_node)

                # OPTIMIZATION 3: Find similar articles with temporal/category filtering
                similar_nodes = self._find_similar_articles_optimized(article_node, performance_stats)
                for similar_node_id, similarity_score in similar_nodes:
                    self._create_similarity_edge(node_id, similar_node_id, similarity_score)

                # OPTIMIZATION 4: Track topic continuation
                if self.enable_performance_optimizations:
                    self._update_topic_timeline(node_id, article_node)

                new_articles.append(article)

                self.logger.debug(
                    "New article added",
                    url=article_node.url,
                    node_id=node_id,
                    similar_articles=len(similar_nodes)
                )

        # Save updated graph
        self._save_graph()

        processing_time = time.time() - start_time
        self.log_operation_success(
            "add_articles",
            new_articles=len(new_articles),
            deduplicated_articles=len(deduplicated_articles),
            total_nodes=self.graph.number_of_nodes(),
            processing_time_seconds=processing_time,
            performance_stats=performance_stats
        )

        return new_articles, deduplicated_articles

    def get_incident_clusters(self) -> List[List[Dict]]:
        """
        Get incident clusters using connected components analysis.

        Returns:
            List of incident clusters, each containing related articles
        """
        self.log_operation_start("get_incident_clusters")

        # Convert to undirected graph for connected components
        undirected_graph = self.graph.to_undirected()

        # Find connected components
        components = list(nx.connected_components(undirected_graph))

        # Convert to incident clusters
        clusters = []
        for component in components:
            if len(component) > 1:  # Only multi-article clusters
                cluster_articles = []
                for node_id in component:
                    article_data = self.graph.nodes[node_id]
                    cluster_articles.append(article_data)

                # Sort by date and severity
                cluster_articles.sort(
                    key=lambda x: (x.get("date", ""), x.get("severity", "") == "high"),
                    reverse=True
                )

                clusters.append(cluster_articles)

        # Sort clusters by size and severity
        clusters.sort(key=lambda c: (len(c), sum(1 for a in c if a.get("severity") == "high")), reverse=True)

        self.log_operation_success(
            "get_incident_clusters",
            cluster_count=len(clusters),
            largest_cluster=max(len(c) for c in clusters) if clusters else 0
        )

        return clusters

    def get_temporal_duplicates(self, days_back: int = 7) -> List[List[Dict]]:
        """
        Find articles that appeared across multiple days.

        Args:
            days_back: Number of days to analyze

        Returns:
            List of temporal duplicate groups
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Group articles by content similarity within time window
        recent_articles = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("date", "") >= cutoff_date:
                recent_articles.append((node_id, data))

        # Find temporal duplicates
        temporal_groups = []
        processed_nodes = set()

        for node_id, data in recent_articles:
            if node_id in processed_nodes:
                continue

            # Find all similar articles for this node
            similar_group = [data]
            processed_nodes.add(node_id)

            for other_id, other_data in recent_articles:
                if other_id == node_id or other_id in processed_nodes:
                    continue

                # Check content similarity
                if self._calculate_content_similarity(data, other_data) > self.similarity_threshold:
                    similar_group.append(other_data)
                    processed_nodes.add(other_id)

            if len(similar_group) > 1:
                temporal_groups.append(similar_group)

        return temporal_groups

    def get_topic_timelines(self, min_articles: int = 2, days_back: int = 30) -> Dict[str, List[Dict]]:
        """
        Get topic continuation timelines.

        Args:
            min_articles: Minimum articles required for a timeline
            days_back: Number of days to look back

        Returns:
            Dictionary of topic_signature -> chronological articles
        """
        if not self.enable_performance_optimizations:
            return {}

        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        filtered_timelines = {}

        for topic_signature, timeline in self.topic_timelines.items():
            # Filter by date and minimum article count
            recent_articles = [
                article for article in timeline
                if article["date"] >= cutoff_date
            ]

            if len(recent_articles) >= min_articles:
                filtered_timelines[topic_signature] = recent_articles

        return filtered_timelines

    def analyze_topic_development(self, topic_signature: str) -> Dict:
        """
        Analyze how a topic has developed over time.

        Args:
            topic_signature: Topic to analyze

        Returns:
            Development analysis with stages and trends
        """
        if topic_signature not in self.topic_timelines:
            return {"error": "Topic not found"}

        timeline = self.topic_timelines[topic_signature]
        if len(timeline) < 2:
            return {"error": "Insufficient articles for analysis"}

        # Analyze development stages
        stages = self._identify_development_stages(timeline)

        # Analyze trends
        severity_trend = self._analyze_severity_trend(timeline)
        source_diversity = len(set(article["source"] for article in timeline))

        # Calculate development metrics
        date_span = (
            datetime.strptime(timeline[-1]["date"], "%Y-%m-%d") -
            datetime.strptime(timeline[0]["date"], "%Y-%m-%d")
        ).days

        return {
            "topic_signature": topic_signature,
            "article_count": len(timeline),
            "date_span_days": date_span,
            "source_diversity": source_diversity,
            "development_stages": stages,
            "severity_trend": severity_trend,
            "timeline_summary": {
                "first_report": {
                    "date": timeline[0]["date"],
                    "source": timeline[0]["source"],
                    "title": timeline[0]["title"]
                },
                "latest_report": {
                    "date": timeline[-1]["date"],
                    "source": timeline[-1]["source"],
                    "title": timeline[-1]["title"]
                }
            },
            "continuation_indicators": {
                "is_ongoing": date_span <= 7 and len(timeline) >= 3,
                "is_escalating": severity_trend == "escalating",
                "multi_source_confirmation": source_diversity >= 3
            }
        }

    def _identify_development_stages(self, timeline: List[Dict]) -> List[Dict]:
        """Identify development stages in a topic timeline."""
        stages = []

        # Group articles by time periods
        if len(timeline) <= 2:
            stages.append({
                "stage": "initial_reports",
                "article_count": len(timeline),
                "date_range": f"{timeline[0]['date']} to {timeline[-1]['date']}"
            })
        else:
            # Divide into initial, development, and current stages
            third = len(timeline) // 3

            stages.append({
                "stage": "initial_reports",
                "article_count": third,
                "date_range": f"{timeline[0]['date']} to {timeline[third-1]['date']}"
            })

            if len(timeline) > 3:
                stages.append({
                    "stage": "development",
                    "article_count": third,
                    "date_range": f"{timeline[third]['date']} to {timeline[2*third-1]['date']}"
                })

            stages.append({
                "stage": "current_status",
                "article_count": len(timeline) - 2*third,
                "date_range": f"{timeline[2*third]['date']} to {timeline[-1]['date']}"
            })

        return stages

    def _analyze_severity_trend(self, timeline: List[Dict]) -> str:
        """Analyze severity trend over time."""
        severity_values = {"low": 1, "medium": 2, "high": 3}

        # Convert severities to numbers
        severity_scores = []
        for article in timeline:
            score = severity_values.get(article.get("severity", "medium"), 2)
            severity_scores.append(score)

        if len(severity_scores) < 2:
            return "stable"

        # Simple trend analysis
        first_half_avg = sum(severity_scores[:len(severity_scores)//2]) / (len(severity_scores)//2)
        second_half_avg = sum(severity_scores[len(severity_scores)//2:]) / (len(severity_scores) - len(severity_scores)//2)

        if second_half_avg > first_half_avg + 0.3:
            return "escalating"
        elif second_half_avg < first_half_avg - 0.3:
            return "de-escalating"
        else:
            return "stable"

    def get_graph_statistics(self) -> Dict:
        """Get comprehensive graph statistics."""
        stats = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "connected_components": nx.number_connected_components(self.graph.to_undirected()),
            "average_clustering": nx.average_clustering(self.graph.to_undirected()) if self.graph.number_of_nodes() > 0 else 0,
            "density": nx.density(self.graph),
        }

        # Category distribution
        categories = {}
        for _, data in self.graph.nodes(data=True):
            cat = data.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        stats["category_distribution"] = categories

        # Severity distribution
        severities = {}
        for _, data in self.graph.nodes(data=True):
            sev = data.get("severity", "unknown")
            severities[sev] = severities.get(sev, 0) + 1
        stats["severity_distribution"] = severities

        # Temporal distribution
        dates = {}
        for _, data in self.graph.nodes(data=True):
            date = data.get("date", "unknown")
            dates[date] = dates.get(date, 0) + 1
        stats["temporal_distribution"] = dict(sorted(dates.items())[-30:])  # Last 30 days

        return stats

    def cleanup_old_articles(self, days_to_keep: int = 90):
        """
        Remove articles older than specified days.

        Args:
            days_to_keep: Number of days of articles to retain
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")

        nodes_to_remove = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("date", "") < cutoff_date:
                nodes_to_remove.append(node_id)

        self.graph.remove_nodes_from(nodes_to_remove)
        self._save_graph()

        self.logger.info(
            "Cleaned up old articles",
            removed_count=len(nodes_to_remove),
            remaining_nodes=self.graph.number_of_nodes()
        )

    def _create_article_node(self, article: Dict) -> ArticleNode:
        """Create ArticleNode from article dictionary."""
        content_hash = self._calculate_content_hash(article)

        return ArticleNode(
            url=article["url"],
            title=article["title"],
            date=article["date"],
            source=article["source"],
            category=article["category"],
            severity=article["severity"],
            content_hash=content_hash,
            incident_type=article.get("incidentType", ""),
            ports=article.get("ports", []),
            vessels=article.get("vessels", []),
            summary=article.get("summary", ""),
            workflow_run_id=article.get("workflow_run_id", "")
        )

    def _calculate_content_hash(self, article: Dict) -> str:
        """Calculate content hash for deduplication."""
        # Use title + date + key content for hash
        content = f"{article['title']}{article['date']}{article.get('summary', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_node_id(self, article_node: ArticleNode) -> str:
        """Generate unique node ID."""
        # Use URL + content hash for uniqueness
        base_id = f"{article_node.source}_{article_node.content_hash}"
        return hashlib.md5(base_id.encode()).hexdigest()[:12]

    def _find_duplicate(self, article_node: ArticleNode) -> Optional[str]:
        """Find exact duplicate of article (legacy method)."""
        for node_id, data in self.graph.nodes(data=True):
            # Check URL match
            if data.get("url") == article_node.url:
                return node_id

            # Check content hash match
            if data.get("content_hash") == article_node.content_hash:
                return node_id

        return None

    def _find_duplicate_optimized(self, article_node: ArticleNode, stats: Dict) -> Optional[str]:
        """Find exact duplicate using performance indexes."""
        if not self.enable_performance_optimizations:
            return self._find_duplicate(article_node)

        stats["hash_lookups"] += 1

        # Fast URL lookup
        if article_node.url in self.url_index:
            return self.url_index[article_node.url]

        # Fast content hash lookup
        if article_node.content_hash in self.content_hash_index:
            return self.content_hash_index[article_node.content_hash]

        return None

    def _update_indexes(self, node_id: str, article_node: ArticleNode):
        """Update all performance indexes for new node."""
        # Update hash indexes
        self.content_hash_index[article_node.content_hash] = node_id
        self.url_index[article_node.url] = node_id

        # Update category index
        self.category_index[article_node.category].add(node_id)

        # Update date index
        self.date_index[article_node.date].add(node_id)

    def _find_similar_articles(self, article_node: ArticleNode) -> List[Tuple[str, float]]:
        """Find similar articles for edge creation (legacy method)."""
        similar_articles = []

        for node_id, data in self.graph.nodes(data=True):
            # Skip same category restriction to find cross-category similarities
            similarity_score = self._calculate_similarity(article_node.to_dict(), data)

            if similarity_score >= self.similarity_threshold:
                similar_articles.append((node_id, similarity_score))

        return similar_articles

    def _find_similar_articles_optimized(self, article_node: ArticleNode, stats: Dict) -> List[Tuple[str, float]]:
        """Find similar articles with performance optimizations."""
        if not self.enable_performance_optimizations:
            return self._find_similar_articles(article_node)

        similar_articles = []
        candidate_nodes = set()

        # OPTIMIZATION 1: Category-based filtering (same and related categories)
        related_categories = [article_node.category]
        # Add cross-category relationships if configured
        if article_node.category == "red_sea":
            related_categories.extend(["geopolitical", "shipping_line_announcements"])
        elif article_node.category == "operational_issues":
            related_categories.append("congestion")

        for category in related_categories:
            candidate_nodes.update(self.category_index[category])

        # OPTIMIZATION 2: Temporal filtering (only check articles within window)
        article_date = datetime.strptime(article_node.date, "%Y-%m-%d")
        temporal_candidates = set()

        for days_back in range(self.temporal_window_days):
            check_date = (article_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            temporal_candidates.update(self.date_index[check_date])

        # Intersect category and temporal candidates
        final_candidates = candidate_nodes & temporal_candidates
        stats["temporal_filtered"] = len(candidate_nodes) - len(final_candidates)

        # OPTIMIZATION 3: Cached similarity calculations
        article_signature = self._get_article_signature(article_node)

        for node_id in final_candidates:
            node_data = self.graph.nodes[node_id]
            node_signature = self._get_article_signature_from_data(node_data)

            cache_key = tuple(sorted([article_signature, node_signature]))

            if cache_key in self.similarity_cache:
                similarity_score = self.similarity_cache[cache_key]
                stats["cache_hits"] += 1
            else:
                similarity_score = self._calculate_similarity(article_node.to_dict(), node_data)
                stats["similarity_calculations"] += 1

                # Cache the result (with size limit)
                if len(self.similarity_cache) < self.max_cache_size:
                    self.similarity_cache[cache_key] = similarity_score

            if similarity_score >= self.similarity_threshold:
                similar_articles.append((node_id, similarity_score))

        return similar_articles

    def _get_article_signature(self, article_node: ArticleNode) -> str:
        """Generate signature for caching."""
        return f"{article_node.category}_{article_node.content_hash[:8]}"

    def _get_article_signature_from_data(self, node_data: Dict) -> str:
        """Generate signature from node data."""
        return f"{node_data.get('category', '')}_{node_data.get('content_hash', '')[:8]}"

    def _update_topic_timeline(self, node_id: str, article_node: ArticleNode):
        """Update topic continuation timeline tracking."""
        # Generate topic signature based on key characteristics
        topic_signature = self._generate_topic_signature(article_node)

        # Add to timeline with chronological ordering
        timeline_entry = {
            "node_id": node_id,
            "date": article_node.date,
            "title": article_node.title,
            "source": article_node.source,
            "severity": article_node.severity,
            "incident_type": article_node.incident_type
        }

        self.topic_timelines[topic_signature].append(timeline_entry)

        # Keep timeline sorted by date
        self.topic_timelines[topic_signature].sort(key=lambda x: x["date"])

        # Limit timeline size to prevent memory issues
        if len(self.topic_timelines[topic_signature]) > 50:
            self.topic_timelines[topic_signature] = self.topic_timelines[topic_signature][-50:]

    def _generate_topic_signature(self, article_node: ArticleNode) -> str:
        """Generate topic signature for continuation tracking."""
        # Combine category + key ports/vessels + incident type
        key_elements = [article_node.category]

        # Add significant ports (major shipping routes)
        major_ports = ["suez", "panama", "singapore", "rotterdam", "shanghai", "los angeles"]
        article_ports = [p.lower() for p in article_node.ports]
        relevant_ports = [p for p in major_ports if any(port in p or p in port for port in article_ports)]
        key_elements.extend(relevant_ports)

        # Add incident type if significant
        if article_node.incident_type:
            key_elements.append(article_node.incident_type.lower())

        return "_".join(key_elements)

    def _calculate_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate comprehensive similarity between articles."""
        scores = []

        # Title similarity (weight: 0.4)
        title_sim = SequenceMatcher(None,
                                   article1.get("title", "").lower(),
                                   article2.get("title", "").lower()).ratio()
        scores.append(title_sim * 0.4)

        # Incident type similarity (weight: 0.3)
        incident_sim = SequenceMatcher(None,
                                     article1.get("incident_type", "").lower(),
                                     article2.get("incident_type", "").lower()).ratio()
        scores.append(incident_sim * 0.3)

        # Geographic similarity - ports and vessels (weight: 0.2)
        geo_sim = self._calculate_geographic_similarity(article1, article2)
        scores.append(geo_sim * 0.2)

        # Temporal proximity (weight: 0.1)
        temporal_sim = self._calculate_temporal_similarity(
            article1.get("date", ""),
            article2.get("date", "")
        )
        scores.append(temporal_sim * 0.1)

        return sum(scores)

    def _calculate_content_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate content-based similarity."""
        # Title + summary similarity
        text1 = f"{article1.get('title', '')} {article1.get('summary', '')}"
        text2 = f"{article2.get('title', '')} {article2.get('summary', '')}"

        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _calculate_geographic_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate geographic similarity based on ports and vessels."""
        ports1 = set(p.lower() for p in article1.get("ports", []))
        ports2 = set(p.lower() for p in article2.get("ports", []))

        vessels1 = set(v.lower() for v in article1.get("vessels", []))
        vessels2 = set(v.lower() for v in article2.get("vessels", []))

        # Jaccard similarity for ports and vessels
        port_sim = len(ports1 & ports2) / len(ports1 | ports2) if (ports1 | ports2) else 0
        vessel_sim = len(vessels1 & vessels2) / len(vessels1 | vessels2) if (vessels1 | vessels2) else 0

        return (port_sim + vessel_sim) / 2

    def _calculate_temporal_similarity(self, date1: str, date2: str) -> float:
        """Calculate temporal similarity (closer dates = higher similarity)."""
        try:
            dt1 = datetime.strptime(date1, "%Y-%m-%d")
            dt2 = datetime.strptime(date2, "%Y-%m-%d")

            day_diff = abs((dt1 - dt2).days)

            # Similarity decreases with time difference
            if day_diff == 0:
                return 1.0
            elif day_diff <= 3:
                return 0.8
            elif day_diff <= 7:
                return 0.5
            elif day_diff <= 14:
                return 0.2
            else:
                return 0.0

        except ValueError:
            return 0.0

    def _create_similarity_edge(self, node1: str, node2: str, similarity: float):
        """Create bidirectional similarity edge."""
        self.graph.add_edge(node1, node2, weight=similarity, edge_type="similarity")
        self.graph.add_edge(node2, node1, weight=similarity, edge_type="similarity")

    def _merge_duplicate_information(self, existing_node_id: str, new_article: ArticleNode):
        """Merge information from duplicate article into existing node."""
        existing_data = self.graph.nodes[existing_node_id]

        # Update with more authoritative source if needed
        source_authority = {
            "The Loadstar": 10, "Container News": 9, "Maersk": 8, "CMA CGM": 8,
            "gCaptain": 7, "Kuehne+Nagel": 6, "Port News": 5
        }

        existing_authority = source_authority.get(existing_data.get("source", ""), 1)
        new_authority = source_authority.get(new_article.source, 1)

        if new_authority > existing_authority:
            # Update with more authoritative information
            self.graph.nodes[existing_node_id].update(new_article.to_dict())

    def _save_graph(self):
        """Save graph and performance indexes to persistent storage."""
        try:
            graph_data = {
                "nodes": dict(self.graph.nodes(data=True)),
                "edges": list(self.graph.edges(data=True)),
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "node_count": self.graph.number_of_nodes(),
                    "edge_count": self.graph.number_of_edges(),
                    "performance_optimizations": self.enable_performance_optimizations
                }
            }

            # Save performance indexes if enabled
            if self.enable_performance_optimizations:
                graph_data["performance_indexes"] = {
                    "content_hash_index": self.content_hash_index,
                    "url_index": self.url_index,
                    "category_index": {k: list(v) for k, v in self.category_index.items()},
                    "date_index": {k: list(v) for k, v in self.date_index.items()},
                    "topic_timelines": dict(self.topic_timelines)
                }

            with open(self.storage_path, 'wb') as f:
                pickle.dump(graph_data, f)

            self.logger.debug("Graph saved successfully", path=str(self.storage_path))

        except Exception as e:
            self.logger.error("Failed to save graph", error=str(e))

    def _load_graph(self):
        """Load graph and performance indexes from persistent storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'rb') as f:
                    graph_data = pickle.load(f)

                # Reconstruct graph
                self.graph.add_nodes_from(graph_data["nodes"].items())
                self.graph.add_edges_from(graph_data["edges"])

                # Load performance indexes if available and enabled
                if (self.enable_performance_optimizations and
                    "performance_indexes" in graph_data):
                    indexes = graph_data["performance_indexes"]

                    self.content_hash_index = indexes.get("content_hash_index", {})
                    self.url_index = indexes.get("url_index", {})

                    # Convert category and date indexes back to defaultdict(set)
                    self.category_index = defaultdict(set)
                    for category, node_list in indexes.get("category_index", {}).items():
                        self.category_index[category] = set(node_list)

                    self.date_index = defaultdict(set)
                    for date, node_list in indexes.get("date_index", {}).items():
                        self.date_index[date] = set(node_list)

                    # Load topic timelines
                    self.topic_timelines = defaultdict(list)
                    for topic, timeline in indexes.get("topic_timelines", {}).items():
                        self.topic_timelines[topic] = timeline

                elif self.enable_performance_optimizations:
                    # Rebuild indexes from existing graph data
                    self._rebuild_performance_indexes()

                metadata = graph_data.get("metadata", {})
                self.logger.info(
                    "Graph loaded successfully",
                    nodes=len(graph_data["nodes"]),
                    edges=len(graph_data["edges"]),
                    saved_at=metadata.get("saved_at"),
                    performance_optimizations_loaded=self.enable_performance_optimizations
                )
            else:
                self.logger.info("No existing graph found, starting fresh")

        except Exception as e:
            self.logger.error("Failed to load graph, starting fresh", error=str(e))
            self.graph = nx.DiGraph()
            if self.enable_performance_optimizations:
                self._init_performance_indexes()

    def _rebuild_performance_indexes(self):
        """Rebuild performance indexes from existing graph data."""
        self.logger.info("Rebuilding performance indexes from existing graph")

        for node_id, data in self.graph.nodes(data=True):
            # Rebuild hash indexes
            if "content_hash" in data:
                self.content_hash_index[data["content_hash"]] = node_id
            if "url" in data:
                self.url_index[data["url"]] = node_id

            # Rebuild category index
            if "category" in data:
                self.category_index[data["category"]].add(node_id)

            # Rebuild date index
            if "date" in data:
                self.date_index[data["date"]].add(node_id)

            # Rebuild topic timelines (simplified - won't be as complete as real-time tracking)
            if all(key in data for key in ["category", "date", "title", "source", "severity"]):
                topic_signature = self._generate_topic_signature_from_data(data)
                timeline_entry = {
                    "node_id": node_id,
                    "date": data["date"],
                    "title": data["title"],
                    "source": data["source"],
                    "severity": data["severity"],
                    "incident_type": data.get("incident_type", "")
                }
                self.topic_timelines[topic_signature].append(timeline_entry)

        # Sort all topic timelines by date
        for topic_signature in self.topic_timelines:
            self.topic_timelines[topic_signature].sort(key=lambda x: x["date"])

    def _generate_topic_signature_from_data(self, data: Dict) -> str:
        """Generate topic signature from node data for rebuilding indexes."""
        key_elements = [data.get("category", "")]

        # Add significant ports
        major_ports = ["suez", "panama", "singapore", "rotterdam", "shanghai", "los angeles"]
        article_ports = [p.lower() for p in data.get("ports", [])]
        relevant_ports = [p for p in major_ports if any(port in p or p in port for port in article_ports)]
        key_elements.extend(relevant_ports)

        # Add incident type if significant
        if data.get("incident_type"):
            key_elements.append(data["incident_type"].lower())

        return "_".join(key_elements)

    def export_graph_analysis(self) -> Dict:
        """Export comprehensive graph analysis."""
        clusters = self.get_incident_clusters()
        temporal_duplicates = self.get_temporal_duplicates()
        stats = self.get_graph_statistics()

        return {
            "statistics": stats,
            "incident_clusters": [
                {
                    "cluster_id": f"cluster_{i}",
                    "article_count": len(cluster),
                    "severity_levels": list(set(a.get("severity") for a in cluster)),
                    "categories": list(set(a.get("category") for a in cluster)),
                    "date_range": {
                        "earliest": min(a.get("date", "") for a in cluster),
                        "latest": max(a.get("date", "") for a in cluster)
                    },
                    "primary_article": cluster[0],  # Most authoritative/recent
                    "related_articles": len(cluster) - 1
                }
                for i, cluster in enumerate(clusters)
            ],
            "temporal_duplicates": [
                {
                    "duplicate_group_id": f"dup_{i}",
                    "article_count": len(group),
                    "date_span": {
                        "earliest": min(a.get("date", "") for a in group),
                        "latest": max(a.get("date", "") for a in group)
                    },
                    "sources": list(set(a.get("source") for a in group)),
                    "primary_url": group[0].get("url", "")
                }
                for i, group in enumerate(temporal_duplicates)
            ],
            "deduplication_metrics": {
                "total_articles_processed": stats["total_nodes"],
                "incident_clusters_found": len(clusters),
                "temporal_duplicates_found": len(temporal_duplicates),
                "deduplication_rate": len(temporal_duplicates) / stats["total_nodes"] if stats["total_nodes"] > 0 else 0
            }
        }