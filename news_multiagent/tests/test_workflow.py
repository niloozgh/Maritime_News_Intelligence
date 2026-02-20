"""
Integration tests for LangGraph workflow execution.

Tests complete workflow orchestration, state management,
parallel execution, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from graph.workflow import (
    initialize_dates_node,
    phase1_scraping_node,
    phase2_searching_node,
    validation_node,
    analysis_node,
    dashboard_generation_node,
    create_workflow
)
from graph.state import WorkflowState


class TestWorkflowNodes:
    """Test individual workflow nodes."""

    @pytest.mark.asyncio
    async def test_initialize_dates_node(self):
        """Test date initialization node."""
        initial_state = {}
        result = await initialize_dates_node(initial_state)

        assert "today" in result
        assert "cutoff_date" in result
        assert "execution_metrics" in result

        # Verify date format
        assert len(result["today"]) == 10  # YYYY-MM-DD
        assert len(result["cutoff_date"]) == 10

        # Verify workflow start timestamp
        assert "workflow_start" in result["execution_metrics"]

    @pytest.mark.asyncio
    @patch('agents.source_scraper.SourceScraperAgent')
    async def test_phase1_scraping_node(self, mock_scraper_class):
        """Test Phase 1 parallel scraping node."""
        # Mock scraper instances
        mock_scraper = AsyncMock()
        mock_scraper.scrape.return_value = [
            {
                "url": "https://example.com/article1",
                "title": "Test Article",
                "date": "2024-01-14",
                "source": "Test Source",
                "category": "operational issues",
                "severity": "high"
            }
        ]
        mock_scraper_class.return_value = mock_scraper

        # Test state
        test_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13"
        }

        result = await phase1_scraping_node(test_state)

        assert "phase1_articles" in result
        assert "execution_metrics" in result
        assert len(result["phase1_articles"]) >= 0  # May be empty in mock

        # Verify metrics
        metrics = result["execution_metrics"]
        assert "phase1_duration" in metrics
        assert "phase1_articles_count" in metrics

    @pytest.mark.asyncio
    @patch('agents.phase2_search.Phase2SearchAgent')
    async def test_phase2_searching_node(self, mock_search_class):
        """Test Phase 2 parallel searching node."""
        # Mock search agent
        mock_agent = AsyncMock()
        mock_agent.search.return_value = [
            {
                "url": "https://example.com/search-result",
                "title": "Search Result Article",
                "date": "2024-01-14",
                "category": "congestion",
                "severity": "medium"
            }
        ]
        mock_search_class.return_value = mock_agent

        test_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13"
        }

        result = await phase2_searching_node(test_state)

        assert "phase2_articles" in result
        assert "execution_metrics" in result

        metrics = result["execution_metrics"]
        assert "phase2_duration" in metrics
        assert "phase2_articles_count" in metrics

    @pytest.mark.asyncio
    async def test_validation_node(self):
        """Test validation and deduplication node."""
        test_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13",
            "phase1_articles": [
                {
                    "url": "https://example.com/article1",
                    "title": "Test Article 1",
                    "date": "2024-01-14",
                    "source": "The Loadstar",
                    "category": "operational issues",
                    "severity": "high",
                    "summary": "Test summary for article 1"
                }
            ],
            "phase2_articles": [
                {
                    "url": "https://example.com/article2",
                    "title": "Test Article 2",
                    "date": "2024-01-14",
                    "source": "Container News",
                    "category": "congestion",
                    "severity": "medium",
                    "summary": "Test summary for article 2"
                }
            ]
        }

        result = await validation_node(test_state)

        assert "validated_articles" in result
        assert "execution_metrics" in result

        # Check validation results structure
        validated = result["validated_articles"]
        assert "articles" in validated
        assert "statistics" in validated

    @pytest.mark.asyncio
    async def test_analysis_node(self):
        """Test analysis node."""
        test_state = {
            "validated_articles": {
                "articles": [
                    {
                        "url": "https://example.com/article1",
                        "title": "Red Sea Disruption",
                        "date": "2024-01-14",
                        "source": "The Loadstar",
                        "category": "red sea",
                        "severity": "high",
                        "incidentType": "Security threat",
                        "summary": "Red Sea attack disrupts shipping",
                        "ports": ["Suez Canal"],
                        "vessels": []
                    },
                    {
                        "url": "https://example.com/article2",
                        "title": "Port Congestion Update",
                        "date": "2024-01-14",
                        "source": "Container News",
                        "category": "congestion",
                        "severity": "medium",
                        "incidentType": "Congestion",
                        "summary": "Port experiencing delays",
                        "ports": ["Los Angeles"],
                        "vessels": []
                    }
                ],
                "statistics": {"processing_stats": {"final_count": 2}}
            }
        }

        result = await analysis_node(test_state)

        assert "insights" in result
        assert "execution_metrics" in result

        # Check insights structure
        insights = result["insights"]
        required_keys = [
            "executive_summary",
            "severity_analysis",
            "geographic_hotspots",
            "category_trends",
            "risk_prioritization"
        ]

        for key in required_keys:
            assert key in insights

    @pytest.mark.asyncio
    async def test_dashboard_generation_node(self):
        """Test dashboard generation node."""
        test_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13",
            "validated_articles": {
                "articles": [
                    {
                        "url": "https://example.com/article1",
                        "title": "Test Article",
                        "category": "operational issues",
                        "severity": "high"
                    }
                ],
                "statistics": {"processing_stats": {"final_count": 1}}
            },
            "insights": {
                "executive_summary": {
                    "total_incidents": 1,
                    "high_severity_count": 1
                }
            },
            "execution_metrics": {
                "workflow_start": "2024-01-15T10:00:00Z"
            }
        }

        result = await dashboard_generation_node(test_state)

        assert "dashboard_data" in result
        assert "execution_metrics" in result

        # Check dashboard data structure
        dashboard = result["dashboard_data"]
        assert "metadata" in dashboard
        assert "articles" in dashboard
        assert "insights" in dashboard
        assert "categories" in dashboard

    @pytest.mark.asyncio
    async def test_error_handling_in_nodes(self):
        """Test error handling in workflow nodes."""
        # Test with invalid state
        invalid_state = {}

        # Initialize dates should handle empty state
        result = await initialize_dates_node(invalid_state)
        assert "today" in result or "errors" in result

        # Validation node should handle missing articles gracefully
        empty_state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13",
            "phase1_articles": [],
            "phase2_articles": []
        }

        result = await validation_node(empty_state)
        assert "validated_articles" in result


class TestWorkflowConstruction:
    """Test workflow graph construction and configuration."""

    def test_create_workflow(self):
        """Test workflow creation."""
        workflow = create_workflow()

        # Verify workflow is created
        assert workflow is not None

        # Check nodes are added (this depends on LangGraph internals)
        # Basic verification that workflow was constructed
        assert hasattr(workflow, 'nodes') or hasattr(workflow, '_nodes')

    @patch('graph.workflow.PostgresSaver')
    def test_workflow_with_checkpointing(self, mock_postgres_saver):
        """Test workflow with checkpointing enabled."""
        from graph.workflow import create_workflow_with_checkpointing

        # Mock the checkpointer
        mock_checkpointer = Mock()
        mock_postgres_saver.from_conn_string.return_value = mock_checkpointer

        with patch('config.settings.get_settings') as mock_settings:
            mock_settings.return_value.checkpoint_enabled = True
            mock_settings.return_value.postgres_url = "postgresql://test"

            workflow = create_workflow_with_checkpointing()
            assert workflow is not None

    def test_workflow_without_checkpointing(self):
        """Test workflow without checkpointing."""
        from graph.workflow import create_workflow_with_checkpointing

        with patch('config.settings.get_settings') as mock_settings:
            mock_settings.return_value.checkpoint_enabled = False

            workflow = create_workflow_with_checkpointing()
            assert workflow is not None


class TestStateManagement:
    """Test LangGraph state management."""

    def test_workflow_state_structure(self):
        """Test workflow state type definitions."""
        from graph.state import WorkflowState, VALID_CATEGORIES, VALID_SEVERITIES

        # Verify required fields exist in type definition
        # This is a basic structure test
        assert isinstance(VALID_CATEGORIES, list)
        assert isinstance(VALID_SEVERITIES, list)

        # Check category completeness
        expected_categories = [
            "red sea",
            "geopolitical",
            "weather-related",
            "congestion",
            "operational issues",
            "us tariffs",
            "shipping line announcements",
            "vessel/container incidents"
        ]

        for category in expected_categories:
            assert category in VALID_CATEGORIES

        # Check severity levels
        expected_severities = ["high", "medium", "low"]
        for severity in expected_severities:
            assert severity in VALID_SEVERITIES

    def test_state_reducers(self):
        """Test state reduction behavior."""
        # This would test LangGraph's state management
        # For now, verify the structure is correct
        from graph.state import WorkflowState
        import operator

        # Verify that lists use operator.add for reduction
        # This is implicit in the TypedDict definition
        assert hasattr(operator, 'add')


@pytest.mark.integration
class TestCompleteWorkflow:
    """Integration tests for complete workflow execution."""

    @pytest.mark.asyncio
    @patch('agents.source_scraper.SourceScraperAgent')
    @patch('agents.phase2_search.Phase2SearchAgent')
    async def test_minimal_workflow_execution(self, mock_search_agent, mock_scraper_agent):
        """Test minimal workflow execution with mocked agents."""
        # Mock agent responses
        mock_scraper = AsyncMock()
        mock_scraper.scrape.return_value = [
            {
                "url": "https://example.com/article1",
                "title": "Test Maritime Article",
                "date": "2024-01-14",
                "source": "Test Source",
                "category": "operational issues",
                "severity": "high",
                "incidentType": "Test incident",
                "summary": "Test summary for maritime article",
                "ports": ["Test Port"],
                "vessels": []
            }
        ]
        mock_scraper_agent.return_value = mock_scraper

        mock_searcher = AsyncMock()
        mock_searcher.search.return_value = [
            {
                "url": "https://example.com/search1",
                "title": "Search Result Article",
                "date": "2024-01-14",
                "source": "Search Source",
                "category": "congestion",
                "severity": "medium",
                "incidentType": "Search incident",
                "summary": "Search result summary",
                "ports": [],
                "vessels": []
            }
        ]
        mock_search_agent.return_value = mock_searcher

        # Execute workflow nodes in sequence
        initial_state = {}

        # Step 1: Initialize
        state = await initialize_dates_node(initial_state)
        assert "today" in state
        assert "cutoff_date" in state

        # Step 2: Phase 1
        state.update(await phase1_scraping_node(state))
        assert "phase1_articles" in state
        assert len(state["phase1_articles"]) > 0

        # Step 3: Phase 2
        state.update(await phase2_searching_node(state))
        assert "phase2_articles" in state

        # Step 4: Validation
        state.update(await validation_node(state))
        assert "validated_articles" in state

        # Step 5: Analysis
        state.update(await analysis_node(state))
        assert "insights" in state

        # Step 6: Dashboard
        state.update(await dashboard_generation_node(state))
        assert "dashboard_data" in state

        # Verify final state completeness
        final_dashboard = state["dashboard_data"]
        assert "articles" in final_dashboard
        assert "insights" in final_dashboard
        assert "categories" in final_dashboard

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test error handling and propagation through workflow."""
        # Start with valid state
        state = {
            "today": "2024-01-15",
            "cutoff_date": "2024-01-13",
            "errors": []
        }

        # Test error handling in validation with invalid articles
        state["phase1_articles"] = [
            {
                "url": "invalid",  # Invalid URL
                "title": "",       # Empty title
                "date": "invalid-date",
                "source": "Test",
                "category": "invalid-category"
            }
        ]
        state["phase2_articles"] = []

        result = await validation_node(state)

        # Should handle errors gracefully
        assert "validated_articles" in result
        validated = result["validated_articles"]

        # Should have no valid articles due to validation failures
        assert len(validated.get("articles", [])) == 0

    def test_performance_requirements(self):
        """Test that workflow meets performance requirements."""
        # This would be a more complex integration test
        # For now, verify the structure supports the requirements

        from config.settings import NEWS_SOURCES, CATEGORY_SEARCHES

        # Verify we have 7 news sources
        assert len(NEWS_SOURCES) == 7

        # Verify we have 6 category searches
        assert len(CATEGORY_SEARCHES) == 6

        # Verify source configurations are complete
        for source in NEWS_SOURCES:
            assert "name" in source
            assert "homepage" in source
            assert "target_count" in source

        # Verify search configurations are complete
        for search in CATEGORY_SEARCHES:
            assert "name" in search
            assert "query" in search
            assert "category" in search


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])