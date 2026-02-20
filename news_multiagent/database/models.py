"""
SQLAlchemy models for maritime news intelligence database.

Defines PostgreSQL tables for articles, workflow runs, and related data
with proper indexing and constraints.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, Float,
    Boolean, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class WorkflowRun(Base):
    """
    Tracks individual workflow executions with performance metrics.
    """
    __tablename__ = "workflow_runs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    cutoff_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    today_date = Column(String(10), nullable=False)   # YYYY-MM-DD

    # Execution metrics
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed
    total_duration_seconds = Column(Float)
    phase1_duration_seconds = Column(Float)
    phase2_duration_seconds = Column(Float)
    validation_duration_seconds = Column(Float)
    analysis_duration_seconds = Column(Float)
    dashboard_duration_seconds = Column(Float)

    # Article counts
    phase1_articles_found = Column(Integer, default=0)
    phase2_articles_found = Column(Integer, default=0)
    total_articles_processed = Column(Integer, default=0)
    final_articles_count = Column(Integer, default=0)

    # Success metrics
    sources_success = Column(Integer, default=0)
    sources_failed = Column(Integer, default=0)
    searches_success = Column(Integer, default=0)
    searches_failed = Column(Integer, default=0)
    success_rate_percent = Column(Float)

    # Error tracking
    errors_encountered = Column(JSON)  # List of error details

    # Results data
    execution_metrics = Column(JSON)
    insights_summary = Column(JSON)

    # Relationships
    articles = relationship("Article", back_populates="workflow_run", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_workflow_runs_date', 'run_date'),
        Index('idx_workflow_runs_status', 'status'),
        CheckConstraint("status IN ('running', 'completed', 'failed')", name='check_status'),
    )

    def __repr__(self):
        return f"<WorkflowRun(id={self.id}, date={self.run_date}, status={self.status})>"


class Article(Base):
    """
    Stores individual maritime news articles with metadata and classification.
    """
    __tablename__ = "articles"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    workflow_run_id = Column(UUID, ForeignKey("workflow_runs.id"), nullable=False)

    # Article identification
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)

    # Date information
    publication_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Classification
    category = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    incident_type = Column(String(200))

    # Content
    summary = Column(Text)
    content_snippet = Column(Text)

    # Geographic and vessel information
    ports = Column(ARRAY(String), default=list)
    vessels = Column(ARRAY(String), default=list)
    affected_regions = Column(ARRAY(String), default=list)

    # Analysis results
    operational_impact = Column(Text)
    risk_score = Column(Float)
    priority_ranking = Column(Integer)

    # Processing metadata
    processing_phase = Column(String(20))  # phase1, phase2
    validation_status = Column(String(20), default="pending")  # pending, validated, rejected
    validation_notes = Column(Text)

    # Full article data (JSON)
    raw_data = Column(JSON)  # Complete article data from scraping

    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="articles")

    # Indexes
    __table_args__ = (
        Index('idx_articles_url', 'url'),
        Index('idx_articles_publication_date', 'publication_date'),
        Index('idx_articles_category', 'category'),
        Index('idx_articles_severity', 'severity'),
        Index('idx_articles_source', 'source'),
        Index('idx_articles_workflow_run', 'workflow_run_id'),
        Index('idx_articles_ports', 'ports', postgresql_using='gin'),
        Index('idx_articles_vessels', 'vessels', postgresql_using='gin'),
        CheckConstraint(
            "category IN ('red sea', 'geopolitical', 'weather-related', 'congestion', "
            "'operational issues', 'us tariffs', 'shipping line announcements', "
            "'vessel/container incidents')",
            name='check_category'
        ),
        CheckConstraint(
            "severity IN ('high', 'medium', 'low')",
            name='check_severity'
        ),
        CheckConstraint(
            "validation_status IN ('pending', 'validated', 'rejected')",
            name='check_validation_status'
        ),
        CheckConstraint(
            "processing_phase IN ('phase1', 'phase2')",
            name='check_processing_phase'
        ),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...', category={self.category})>"


class SourceReliability(Base):
    """
    Tracks reliability metrics for news sources over time.
    """
    __tablename__ = "source_reliability"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    source_name = Column(String(100), nullable=False)
    measurement_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Reliability metrics
    articles_processed = Column(Integer, default=0)
    articles_validated = Column(Integer, default=0)
    high_severity_articles = Column(Integer, default=0)
    categories_covered = Column(Integer, default=0)
    reliability_score = Column(Float)

    # Authority ranking
    authority_rank = Column(Integer)
    industry_standing = Column(String(20))  # primary, secondary, supplementary

    # Performance metrics
    average_response_time = Column(Float)
    success_rate = Column(Float)
    content_quality_score = Column(Float)

    __table_args__ = (
        Index('idx_source_reliability_name_date', 'source_name', 'measurement_date'),
        Index('idx_source_reliability_score', 'reliability_score'),
    )


class IncidentTracking(Base):
    """
    Tracks ongoing incidents across multiple articles and sources.
    """
    __tablename__ = "incident_tracking"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    incident_key = Column(String(200), nullable=False, unique=True)  # Generated identifier

    # Incident classification
    incident_type = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)

    # Geographic information
    primary_location = Column(String(200))
    affected_ports = Column(ARRAY(String))
    affected_regions = Column(ARRAY(String))

    # Timeline
    first_reported = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    estimated_resolution = Column(DateTime)
    status = Column(String(20), default="active")  # active, monitoring, resolved

    # Impact assessment
    operational_impact = Column(Text)
    estimated_disruption_days = Column(Integer)
    affected_vessels_count = Column(Integer)
    financial_impact_estimate = Column(String(50))

    # Source tracking
    reporting_sources = Column(ARRAY(String))
    source_articles = Column(ARRAY(String))  # URLs
    confidence_level = Column(Float)  # 0.0 to 1.0

    # Analysis
    risk_assessment = Column(JSON)
    recommendations = Column(ARRAY(Text))

    __table_args__ = (
        Index('idx_incident_tracking_key', 'incident_key'),
        Index('idx_incident_tracking_status', 'status'),
        Index('idx_incident_tracking_severity', 'severity'),
        Index('idx_incident_tracking_location', 'primary_location'),
        Index('idx_incident_tracking_dates', 'first_reported', 'last_updated'),
        CheckConstraint(
            "status IN ('active', 'monitoring', 'resolved')",
            name='check_incident_status'
        ),
    )