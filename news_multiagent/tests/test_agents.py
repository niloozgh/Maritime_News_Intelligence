"""
Unit tests for maritime news intelligence agents.

Tests agent functionality, date validation, article processing,
and error handling with comprehensive coverage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from agents.source_scraper import SourceScraperAgent
from agents.validation import ValidationAgent
from agents.analysis import AnalysisAgent
from agents.phase2_search import Phase2SearchAgent
from utils.date_utils import parse_article_date, is_date_in_range, calculate_dates
from config.settings import get_settings


class TestDateUtils:
    """Test date parsing and validation utilities."""

    def test_calculate_dates(self):
        """Test date calculation for workflow."""
        today, cutoff_date = calculate_dates()

        assert isinstance(today, str)
        assert isinstance(cutoff_date, str)
        assert len(today) == 10  # YYYY-MM-DD format
        assert len(cutoff_date) == 10

        # Verify cutoff is 2 days before today
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        cutoff_dt = datetime.strptime(cutoff_date, "%Y-%m-%d")
        assert (today_dt - cutoff_dt).days == 2

    def test_parse_article_date_formats(self):
        """Test parsing various date formats."""
        test_cases = [
            ("2024-01-15", "2024-01-15"),
            ("15/01/2024", "2024-01-15"),
            ("January 15, 2024", "2024-01-15"),
            ("3 hours ago", None),  # Relative dates need reference
            ("yesterday", None),    # Relative dates need reference
        ]

        for input_date, expected in test_cases:
            result = parse_article_date(input_date)
            if expected:
                assert result == expected
            # For relative dates, test with reference
            if "ago" in input_date or "yesterday" in input_date:
                ref_date = datetime(2024, 1, 15, 12, 0, 0)
                result = parse_article_date(input_date, ref_date)
                assert result is not None

    def test_is_date_in_range(self):
        """Test date range validation."""
        # Valid range
        assert is_date_in_range("2024-01-15", "2024-01-13", "2024-01-17") is True

        # Date too early
        assert is_date_in_range("2024-01-12", "2024-01-13", "2024-01-17") is False

        # Date too late
        assert is_date_in_range("2024-01-18", "2024-01-13", "2024-01-17") is False

        # Edge cases - exact boundaries
        assert is_date_in_range("2024-01-13", "2024-01-13", "2024-01-17") is True
        assert is_date_in_range("2024-01-17", "2024-01-13", "2024-01-17") is True


class TestSourceScraperAgent:
    """Test source scraper agent functionality."""

    @pytest.fixture
    def source_config(self):
        """Sample source configuration."""
        return {
            "name": "Test Source",
            "homepage": "https://example.com/news",
            "target_count": 3
        }

    @pytest.fixture
    def scraper_agent(self, source_config):
        """Create scraper agent instance."""
        return SourceScraperAgent(
            source_config=source_config,
            cutoff_date="2024-01-13",
            today="2024-01-15"
        )

    def test_scraper_initialization(self, scraper_agent, source_config):
        """Test scraper agent initialization."""
        assert scraper_agent.source_config == source_config
        assert scraper_agent.cutoff_date == "2024-01-13"
        assert scraper_agent.today == "2024-01-15"
        assert scraper_agent.max_retries == 3

    @pytest.mark.asyncio
    async def test_validate_article(self, scraper_agent):
        """Test article validation logic."""
        # Valid article
        valid_article = {
            "url": "https://example.com/article1",
            "title": "Port Strike Causes Delays",
            "date": "2024-01-14",
            "source": "Test Source",
            "category": "operational issues",
            "severity": "high",
            "summary": "Strike at major port causing significant delays"
        }

        result = await scraper_agent._validate_article(valid_article)
        assert result is True

        # Invalid article - missing required field
        invalid_article = valid_article.copy()
        del invalid_article["title"]

        result = await scraper_agent._validate_article(invalid_article)
        assert result is False

        # Invalid article - date out of range
        old_article = valid_article.copy()
        old_article["date"] = "2024-01-10"  # Before cutoff

        result = await scraper_agent._validate_article(old_article)
        assert result is False

    def test_extract_articles_from_response(self, scraper_agent):
        """Test extracting articles from API response."""
        # Mock API response with JSON array
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '''
        Some text before
        [
            {
                "url": "https://example.com/article1",
                "title": "Test Article",
                "date": "2024-01-14",
                "category": "operational issues",
                "severity": "high"
            }
        ]
        Some text after
        '''

        articles = scraper_agent._extract_articles_from_response(mock_response)
        assert len(articles) == 1
        assert articles[0]["url"] == "https://example.com/article1"
        assert articles[0]["title"] == "Test Article"


class TestValidationAgent:
    """Test validation agent functionality."""

    @pytest.fixture
    def validation_agent(self):
        """Create validation agent instance."""
        return ValidationAgent(
            cutoff_date="2024-01-13",
            today="2024-01-15",
            similarity_threshold=0.8
        )

    @pytest.fixture
    def sample_articles(self):
        """Sample articles for testing."""
        return [
            {
                "url": "https://example.com/article1",
                "title": "Port Strike Causes Major Delays",
                "date": "2024-01-14",
                "source": "The Loadstar",
                "category": "operational issues",
                "severity": "high",
                "summary": "Strike at port causing delays"
            },
            {
                "url": "https://example.com/article2",
                "title": "Port Strike Causes Major Delays",  # Duplicate title
                "date": "2024-01-14",
                "source": "Container News",
                "category": "operational issues",
                "severity": "high",
                "summary": "Strike at port causing delays"
            },
            {
                "url": "https://example.com/article3",
                "title": "Weather Delays at Port",
                "date": "2024-01-15",
                "source": "gCaptain",
                "category": "weather-related",
                "severity": "medium",
                "summary": "Storm causing delays"
            }
        ]

    @pytest.mark.asyncio
    async def test_validation_and_deduplication(self, validation_agent, sample_articles):
        """Test complete validation and deduplication process."""
        # Test with articles from both phases
        phase1_articles = sample_articles[:2]
        phase2_articles = sample_articles[2:]

        results = await validation_agent.validate_and_deduplicate(
            phase1_articles=phase1_articles,
            phase2_articles=phase2_articles
        )

        assert "articles" in results
        assert "statistics" in results
        assert "validation_summary" in results

        # Should have 2 articles after deduplication (removed duplicate)
        validated_articles = results["articles"]
        assert len(validated_articles) == 2

        # Check that higher authority source was kept
        loadstar_article = next(
            (a for a in validated_articles if a["source"] == "The Loadstar"),
            None
        )
        assert loadstar_article is not None

    def test_validate_article_structure(self, validation_agent):
        """Test article structure validation."""
        # Valid article
        valid_article = {
            "url": "https://example.com/article1",
            "title": "Test Article Title",
            "date": "2024-01-14",
            "source": "Test Source",
            "category": "operational issues",
            "severity": "high",
            "summary": "Valid summary text"
        }

        result = validation_agent._validate_article_structure(valid_article)
        assert result is True

        # Invalid category
        invalid_article = valid_article.copy()
        invalid_article["category"] = "invalid_category"

        result = validation_agent._validate_article_structure(invalid_article)
        assert result is False

    def test_deduplicate_articles(self, validation_agent, sample_articles):
        """Test article deduplication logic."""
        # Create articles with same title but different sources
        articles = [
            {
                "url": "https://source1.com/article1",
                "title": "Same Title Article",
                "source": "The Loadstar",  # Higher authority
                "category": "operational issues",
                "severity": "high"
            },
            {
                "url": "https://source2.com/article2",
                "title": "Same Title Article",
                "source": "Port News",    # Lower authority
                "category": "operational issues",
                "severity": "high"
            }
        ]

        deduplicated = validation_agent._deduplicate_articles(articles)

        # Should keep only the higher authority source
        assert len(deduplicated) == 1
        assert deduplicated[0]["source"] == "The Loadstar"

    def test_sort_by_priority(self, validation_agent, sample_articles):
        """Test article priority sorting."""
        sorted_articles = validation_agent._sort_by_priority(sample_articles)

        # First article should be high severity
        assert sorted_articles[0]["severity"] == "high"

        # Within same severity, higher authority sources first
        high_severity_articles = [a for a in sorted_articles if a["severity"] == "high"]
        if len(high_severity_articles) > 1:
            assert high_severity_articles[0]["source"] == "The Loadstar"


class TestAnalysisAgent:
    """Test analysis agent functionality."""

    @pytest.fixture
    def analysis_agent(self):
        """Create analysis agent instance."""
        return AnalysisAgent()

    @pytest.fixture
    def sample_validated_articles(self):
        """Sample validated articles for analysis."""
        return [
            {
                "url": "https://example.com/article1",
                "title": "Red Sea Attack Disrupts Shipping",
                "date": "2024-01-14",
                "source": "The Loadstar",
                "category": "red sea",
                "severity": "high",
                "ports": ["Suez Canal", "Port Said"],
                "vessels": ["Ever Given"],
                "incidentType": "Security threat"
            },
            {
                "url": "https://example.com/article2",
                "title": "Port Congestion in Los Angeles",
                "date": "2024-01-15",
                "source": "Container News",
                "category": "congestion",
                "severity": "medium",
                "ports": ["Los Angeles", "Long Beach"],
                "vessels": [],
                "incidentType": "Congestion"
            },
            {
                "url": "https://example.com/article3",
                "title": "Storm Closes Hamburg Port",
                "date": "2024-01-15",
                "source": "gCaptain",
                "category": "weather-related",
                "severity": "high",
                "ports": ["Hamburg"],
                "vessels": [],
                "incidentType": "Weather closure"
            }
        ]

    @pytest.mark.asyncio
    async def test_comprehensive_analysis(self, analysis_agent, sample_validated_articles):
        """Test complete analysis generation."""
        results = await analysis_agent.analyze(sample_validated_articles)

        # Check all analysis components are present
        required_keys = [
            "executive_summary",
            "severity_analysis",
            "geographic_hotspots",
            "category_trends",
            "risk_prioritization",
            "temporal_analysis",
            "operational_alerts",
            "source_reliability",
            "incident_tracking",
            "client_recommendations"
        ]

        for key in required_keys:
            assert key in results

    def test_generate_executive_summary(self, analysis_agent, sample_validated_articles):
        """Test executive summary generation."""
        summary = analysis_agent._generate_executive_summary(sample_validated_articles)

        assert summary["total_incidents"] == 3
        assert summary["high_severity_count"] == 2
        assert summary["medium_severity_count"] == 1
        assert summary["critical_alert"] is False  # Only 2 high severity

        # Check top categories
        assert "top_categories" in summary
        assert len(summary["top_categories"]) > 0

    def test_analyze_severity_distribution(self, analysis_agent, sample_validated_articles):
        """Test severity distribution analysis."""
        analysis = analysis_agent._analyze_severity_distribution(sample_validated_articles)

        assert analysis["total_articles"] == 3
        assert analysis["distribution"]["high"]["count"] == 2
        assert analysis["distribution"]["medium"]["count"] == 1
        assert analysis["distribution"]["low"]["count"] == 0

        # Check percentages
        assert analysis["distribution"]["high"]["percentage"] == 66.7
        assert analysis["distribution"]["medium"]["percentage"] == 33.3

    def test_identify_geographic_hotspots(self, analysis_agent, sample_validated_articles):
        """Test geographic hotspot identification."""
        hotspots = analysis_agent._identify_geographic_hotspots(sample_validated_articles)

        assert "hotspots" in hotspots
        assert "port_incidents" in hotspots
        assert "total_affected_ports" in hotspots

        # Should identify port incidents
        port_incidents = hotspots["port_incidents"]
        assert "Los Angeles" in port_incidents or "Hamburg" in port_incidents

    def test_prioritize_risks(self, analysis_agent, sample_validated_articles):
        """Test risk prioritization."""
        risks = analysis_agent._prioritize_risks(sample_validated_articles)

        assert "high_priority" in risks
        assert "medium_priority" in risks
        assert "immediate_action_required" in risks

        # Red Sea incident should be high priority
        high_priority = risks["high_priority"]
        red_sea_risk = next(
            (r for r in high_priority if r["category"] == "red sea"),
            None
        )
        assert red_sea_risk is not None

    @pytest.mark.asyncio
    async def test_empty_analysis(self, analysis_agent):
        """Test analysis with no articles."""
        results = await analysis_agent.analyze([])

        assert "executive_summary" in results
        assert results["executive_summary"]["total_incidents"] == 0


class TestPhase2SearchAgent:
    """Test Phase 2 search agent functionality."""

    @pytest.fixture
    def search_config(self):
        """Sample search configuration."""
        return {
            "name": "Port Closures",
            "query": "port closure OR terminal closed",
            "category": "operational issues",
            "target_count": 5
        }

    @pytest.fixture
    def search_agent(self, search_config):
        """Create Phase 2 search agent."""
        return Phase2SearchAgent(
            search_config=search_config,
            cutoff_date="2024-01-13",
            today="2024-01-15"
        )

    def test_search_agent_initialization(self, search_agent, search_config):
        """Test search agent initialization."""
        assert search_agent.search_config == search_config
        assert search_agent.cutoff_date == "2024-01-13"
        assert search_agent.today == "2024-01-15"

    @pytest.mark.asyncio
    async def test_validate_search_article(self, search_agent):
        """Test search result validation."""
        # Valid search result
        valid_article = {
            "url": "https://example.com/search-result",
            "title": "Port Closure Announcement",
            "date": "2024-01-14",
            "category": "operational issues",
            "severity": "high"
        }

        result = await search_agent._validate_article(valid_article)
        assert result is True

        # Invalid - date out of range
        invalid_article = valid_article.copy()
        invalid_article["date"] = "2024-01-10"  # Before cutoff

        result = await search_agent._validate_article(invalid_article)
        assert result is False


@pytest.mark.integration
class TestSystemIntegration:
    """Integration tests for complete system functionality."""

    @pytest.mark.asyncio
    async def test_workflow_state_management(self):
        """Test LangGraph state management."""
        from graph.state import WorkflowState
        from graph.workflow import initialize_dates_node

        # Test initial state
        initial_state = {}
        result = await initialize_dates_node(initial_state)

        assert "today" in result
        assert "cutoff_date" in result
        assert "execution_metrics" in result

    def test_settings_configuration(self):
        """Test settings loading and validation."""
        settings = get_settings()

        # Required settings should be accessible
        assert hasattr(settings, 'model_name')
        assert hasattr(settings, 'max_tokens')
        assert hasattr(settings, 'postgres_host')

        # Validate defaults
        assert settings.model_name == "claude-3-5-sonnet-20241022"
        assert settings.max_tokens == 8000
        assert settings.temperature == 0.1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])