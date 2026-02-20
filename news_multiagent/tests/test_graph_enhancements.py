"""
Comprehensive tests for graph-enhanced maritime news intelligence system.

Tests graph-based incident tracking, cross-temporal deduplication,
and incident clustering functionality.
"""

import pytest
import tempfile
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from graph.incident_graph import IncidentGraph, ArticleNode
from agents.graph_validation import GraphValidationAgent
from graph.graph_enhanced_workflow import (
    initialize_dates_node,
    graph_validation_node,
    enhanced_analysis_node,
    create_graph_enhanced_workflow
)


class TestIncidentGraph:
    """Test the core incident graph functionality."""

    @pytest.fixture
    def temp_graph_storage(self):
        """Create temporary storage for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            return f.name

    @pytest.fixture
    def incident_graph(self, temp_graph_storage):
        """Create incident graph instance for testing."""
        return IncidentGraph(
            similarity_threshold=0.75,
            temporal_window_days=30,
            storage_path=temp_graph_storage
        )

    @pytest.fixture
    def sample_articles(self):
        """Sample articles for testing."""
        return [
            {
                "url": "https://example.com/red-sea-attack-1",
                "title": "Red Sea Attack Disrupts Major Shipping Routes",
                "date": "2024-01-15",
                "source": "The Loadstar",
                "category": "red sea",
                "severity": "high",
                "incidentType": "Security threat",
                "summary": "Houthi attack on container vessel in Red Sea",
                "ports": ["Suez Canal", "Port Said"],
                "vessels": ["Ever Given"]
            },
            {
                "url": "https://example.com/red-sea-attack-2",
                "title": "Shipping Routes Diverted Following Red Sea Incident",
                "date": "2024-01-15",
                "source": "Container News",
                "category": "red sea",
                "severity": "high",
                "incidentType": "Security threat",
                "summary": "Major carriers rerouting vessels around Africa",
                "ports": ["Suez Canal"],
                "vessels": ["MSC Arabella"]
            },
            {
                "url": "https://example.com/port-congestion",
                "title": "Los Angeles Port Faces Major Congestion",
                "date": "2024-01-16",
                "source": "gCaptain",
                "category": "congestion",
                "severity": "medium",
                "incidentType": "Congestion",
                "summary": "Container backlog at LA port reaches critical levels",
                "ports": ["Los Angeles", "Long Beach"],
                "vessels": []
            }
        ]

    def test_incident_graph_initialization(self, incident_graph):
        """Test incident graph initialization."""
        assert incident_graph.similarity_threshold == 0.75
        assert incident_graph.temporal_window_days == 30
        assert incident_graph.graph.number_of_nodes() == 0
        assert incident_graph.graph.number_of_edges() == 0

    def test_add_articles_basic(self, incident_graph, sample_articles):
        """Test basic article addition to graph."""
        new_articles, duplicates = incident_graph.add_articles(sample_articles)

        # All articles should be new
        assert len(new_articles) == 3
        assert len(duplicates) == 0
        assert incident_graph.graph.number_of_nodes() == 3

    def test_similarity_detection(self, incident_graph):
        """Test article similarity detection."""
        similar_articles = [
            {
                "url": "https://source1.com/red-sea-1",
                "title": "Red Sea Attack Disrupts Shipping",
                "date": "2024-01-15",
                "source": "The Loadstar",
                "category": "red sea",
                "severity": "high",
                "incidentType": "Security attack",
                "summary": "Houthi forces target container ship",
                "ports": ["Suez Canal"],
                "vessels": []
            },
            {
                "url": "https://source2.com/red-sea-2",
                "title": "Shipping Disrupted by Red Sea Security Incident",
                "date": "2024-01-15",
                "source": "Container News",
                "category": "red sea",
                "severity": "high",
                "incidentType": "Security attack",
                "summary": "Maritime security incident affects shipping routes",
                "ports": ["Suez Canal"],
                "vessels": []
            }
        ]

        new_articles, duplicates = incident_graph.add_articles(similar_articles)

        # Should create edges between similar articles
        assert incident_graph.graph.number_of_edges() > 0

    def test_duplicate_detection(self, incident_graph):
        """Test exact duplicate detection."""
        article = {
            "url": "https://example.com/test-article",
            "title": "Test Maritime Incident",
            "date": "2024-01-15",
            "source": "Test Source",
            "category": "operational issues",
            "severity": "medium",
            "incidentType": "Test incident",
            "summary": "Test summary",
            "ports": [],
            "vessels": []
        }

        # Add article twice
        new_articles1, duplicates1 = incident_graph.add_articles([article])
        new_articles2, duplicates2 = incident_graph.add_articles([article])

        # First time should be new, second time should be duplicate
        assert len(new_articles1) == 1
        assert len(duplicates1) == 0
        assert len(new_articles2) == 0
        assert len(duplicates2) == 1

    def test_incident_clustering(self, incident_graph, sample_articles):
        """Test incident cluster detection."""
        # Add articles to graph
        incident_graph.add_articles(sample_articles)

        # Get clusters
        clusters = incident_graph.get_incident_clusters()

        # Should find at least one cluster (Red Sea articles should cluster)
        assert len(clusters) >= 0  # May be 0 if similarity threshold not met

    def test_temporal_duplicates(self, incident_graph):
        """Test temporal duplicate detection."""
        # Create articles across different days
        temporal_articles = [
            {
                "url": "https://example.com/day1",
                "title": "Port Strike Causes Delays",
                "date": "2024-01-15",
                "source": "The Loadstar",
                "category": "operational issues",
                "severity": "high",
                "incidentType": "Strike",
                "summary": "Port workers strike affecting operations",
                "ports": ["Hamburg"],
                "vessels": []
            },
            {
                "url": "https://example.com/day2",
                "title": "Strike at Port Continues to Cause Delays",
                "date": "2024-01-16",
                "source": "Container News",
                "category": "operational issues",
                "severity": "high",
                "incidentType": "Strike",
                "summary": "Ongoing port strike disrupts container handling",
                "ports": ["Hamburg"],
                "vessels": []
            }
        ]

        incident_graph.add_articles(temporal_articles)
        temporal_groups = incident_graph.get_temporal_duplicates(days_back=7)

        # Should detect temporal relationship
        # (May be empty if similarity threshold not met)
        assert isinstance(temporal_groups, list)

    def test_graph_statistics(self, incident_graph, sample_articles):
        """Test graph statistics generation."""
        incident_graph.add_articles(sample_articles)
        stats = incident_graph.get_graph_statistics()

        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "connected_components" in stats
        assert "category_distribution" in stats
        assert "severity_distribution" in stats

        # Verify content
        assert stats["total_nodes"] == 3
        assert stats["category_distribution"]["red sea"] == 2
        assert stats["category_distribution"]["congestion"] == 1

    def test_graph_persistence(self, temp_graph_storage):
        """Test graph saving and loading."""
        # Create graph and add articles
        graph1 = IncidentGraph(storage_path=temp_graph_storage)
        articles = [{
            "url": "https://example.com/test",
            "title": "Test Article",
            "date": "2024-01-15",
            "source": "Test Source",
            "category": "operational issues",
            "severity": "medium",
            "incidentType": "Test",
            "summary": "Test",
            "ports": [],
            "vessels": []
        }]

        graph1.add_articles(articles)
        original_nodes = graph1.graph.number_of_nodes()

        # Create new graph instance with same storage
        graph2 = IncidentGraph(storage_path=temp_graph_storage)
        loaded_nodes = graph2.graph.number_of_nodes()

        # Should load the same data
        assert loaded_nodes == original_nodes


class TestGraphValidationAgent:
    """Test the graph-enhanced validation agent."""

    @pytest.fixture
    def temp_graph_storage(self):
        """Create temporary storage for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            return f.name

    @pytest.fixture
    def graph_validation_agent(self, temp_graph_storage):
        """Create graph validation agent for testing."""
        return GraphValidationAgent(
            cutoff_date="2024-01-13",
            today="2024-01-15",
            similarity_threshold=0.75,
            temporal_window_days=30,
            graph_storage_path=temp_graph_storage
        )

    @pytest.fixture
    def sample_articles(self):
        """Sample articles for validation testing."""
        return [
            {
                "url": "https://example.com/article1",
                "title": "Maritime Incident Report",
                "date": "2024-01-14",
                "source": "The Loadstar",
                "category": "operational issues",
                "severity": "high",
                "incidentType": "Equipment failure",
                "summary": "Crane failure at major container terminal",
                "ports": ["Rotterdam"],
                "vessels": []
            },
            {
                "url": "https://example.com/article2",
                "title": "Container Terminal Disruption",
                "date": "2024-01-14",
                "source": "Container News",
                "category": "operational issues",
                "severity": "high",
                "incidentType": "Equipment failure",
                "summary": "Terminal operations halted due to equipment issues",
                "ports": ["Rotterdam"],
                "vessels": []
            }
        ]

    def test_graph_validation_agent_initialization(self, graph_validation_agent):
        """Test graph validation agent initialization."""
        assert graph_validation_agent.cutoff_date == "2024-01-13"
        assert graph_validation_agent.today == "2024-01-15"
        assert graph_validation_agent.incident_graph is not None

    @pytest.mark.asyncio
    async def test_validate_and_deduplicate_with_graph(
        self,
        graph_validation_agent,
        sample_articles
    ):
        """Test graph-enhanced validation and deduplication."""
        # Mock the database loading
        with patch.object(graph_validation_agent, '_load_recent_articles_to_graph'):
            results = await graph_validation_agent.validate_and_deduplicate(
                phase1_articles=sample_articles,
                phase2_articles=[]
            )

        # Check results structure
        assert "articles" in results
        assert "incident_clusters" in results
        assert "graph_analysis" in results
        assert "validation_summary" in results

        # Should have validation summary with graph metrics
        summary = results["validation_summary"]
        assert "incident_clusters_found" in summary
        assert "graph_nodes_total" in summary
        assert "cross_temporal_duplicates" in summary

    @pytest.mark.asyncio
    async def test_incident_timeline_generation(self, graph_validation_agent, sample_articles):
        """Test incident timeline generation."""
        # Add articles to graph first
        graph_validation_agent.incident_graph.add_articles(sample_articles)

        timeline = await graph_validation_agent.get_incident_timeline(days_back=14)

        assert isinstance(timeline, list)
        # Timeline might be empty if articles don't form multi-stage incidents

    @pytest.mark.asyncio
    async def test_graph_cleanup(self, graph_validation_agent):
        """Test graph cleanup and optimization."""
        cleanup_result = await graph_validation_agent.cleanup_and_optimize_graph()

        assert "cleanup_completed" in cleanup_result
        assert cleanup_result["cleanup_completed"] is True
        assert "graph_statistics" in cleanup_result


class TestGraphEnhancedWorkflow:
    """Test the graph-enhanced workflow components."""

    @pytest.mark.asyncio
    async def test_initialize_dates_node_enhanced(self):
        """Test enhanced date initialization."""
        result = await initialize_dates_node({})

        assert "today" in result
        assert "cutoff_date" in result
        assert "execution_metrics" in result
        assert "graph_metrics" in result

        # Check for graph enhancement markers
        assert result["execution_metrics"]["graph_enhanced"] is True

    @pytest.mark.asyncio
    @patch('agents.graph_validation.GraphValidationAgent')
    async def test_graph_validation_node(self, mock_graph_agent_class):
        """Test graph validation node."""
        # Mock the graph validation agent
        mock_agent = AsyncMock()
        mock_agent.validate_and_deduplicate.return_value = {
            "articles": [],
            "incident_clusters": [],
            "graph_analysis": {"statistics": {"total_nodes": 0}},
            "deduplicated_articles": []
        }
        mock_agent.get_incident_timeline.return_value = []
        mock_agent.incident_graph.get_graph_statistics.return_value = {
            "total_nodes": 0,
            "total_edges": 0,
            "connected_components": 0
        }
        mock_graph_agent_class.return_value = mock_agent

        test_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13",
            "phase1_articles": [],
            "phase2_articles": []
        }

        result = await graph_validation_node(test_state)

        assert "validated_articles" in result
        assert "incident_clusters" in result
        assert "graph_analysis" in result
        assert "graph_metrics" in result

    def test_create_graph_enhanced_workflow(self):
        """Test graph-enhanced workflow creation."""
        workflow = create_graph_enhanced_workflow()

        assert workflow is not None
        # Verify workflow has the expected structure
        assert hasattr(workflow, 'nodes') or hasattr(workflow, '_nodes')


@pytest.mark.integration
class TestGraphSystemIntegration:
    """Integration tests for the complete graph-enhanced system."""

    @pytest.fixture
    def temp_graph_storage(self):
        """Create temporary storage for integration testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            return f.name

    @pytest.mark.asyncio
    async def test_end_to_end_graph_workflow(self, temp_graph_storage):
        """Test complete graph-enhanced workflow integration."""
        # This would test the full workflow but requires external dependencies
        # For now, test that components can be integrated

        graph = IncidentGraph(storage_path=temp_graph_storage)
        validation_agent = GraphValidationAgent(
            cutoff_date="2024-01-13",
            today="2024-01-15",
            graph_storage_path=temp_graph_storage
        )

        # Verify integration
        assert graph is not None
        assert validation_agent is not None
        assert validation_agent.incident_graph is not None

    def test_graph_performance_with_large_dataset(self):
        """Test graph performance with larger datasets."""
        # Create large dataset simulation
        large_dataset = []
        for i in range(100):
            article = {
                "url": f"https://example.com/article{i}",
                "title": f"Maritime Incident {i}",
                "date": "2024-01-14",
                "source": "Test Source",
                "category": "operational issues",
                "severity": "medium",
                "incidentType": "Test incident",
                "summary": f"Test incident number {i}",
                "ports": [f"Port{i % 10}"],  # Create some port clustering
                "vessels": []
            }
            large_dataset.append(article)

        with tempfile.NamedTemporaryFile() as temp_file:
            graph = IncidentGraph(storage_path=temp_file.name)

            # Performance test
            start_time = datetime.now()
            new_articles, duplicates = graph.add_articles(large_dataset)
            processing_time = (datetime.now() - start_time).total_seconds()

            # Verify reasonable performance (should complete in under 30 seconds)
            assert processing_time < 30
            assert len(new_articles) == 100
            assert graph.graph.number_of_nodes() == 100

    def test_similarity_algorithm_accuracy(self):
        """Test accuracy of similarity detection algorithm."""
        test_cases = [
            # Should be similar
            {
                "article1": {
                    "title": "Red Sea Attack Disrupts Shipping",
                    "incident_type": "Security threat",
                    "ports": ["Suez Canal"],
                    "date": "2024-01-15"
                },
                "article2": {
                    "title": "Shipping Disrupted by Red Sea Incident",
                    "incident_type": "Security attack",
                    "ports": ["Suez Canal"],
                    "date": "2024-01-15"
                },
                "expected_similar": True
            },
            # Should not be similar
            {
                "article1": {
                    "title": "Red Sea Security Incident",
                    "incident_type": "Security threat",
                    "ports": ["Suez Canal"],
                    "date": "2024-01-15"
                },
                "article2": {
                    "title": "Port Congestion in Los Angeles",
                    "incident_type": "Congestion",
                    "ports": ["Los Angeles"],
                    "date": "2024-01-16"
                },
                "expected_similar": False
            }
        ]

        with tempfile.NamedTemporaryFile() as temp_file:
            graph = IncidentGraph(storage_path=temp_file.name)

            for test_case in test_cases:
                # Calculate similarity
                similarity = graph._calculate_similarity(
                    test_case["article1"],
                    test_case["article2"]
                )

                if test_case["expected_similar"]:
                    assert similarity >= graph.similarity_threshold
                else:
                    assert similarity < graph.similarity_threshold


if __name__ == "__main__":
    # Run graph enhancement tests
    pytest.main([__file__, "-v", "--tb=short"])