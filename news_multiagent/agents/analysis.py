"""
Analysis Agent for Maritime News Intelligence

Generates operational insights, risk assessments, and actionable intelligence
from validated maritime news articles.
"""

import structlog
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime

from ..utils.logging_config import LoggingMixin
from ..graph.state import VALID_CATEGORIES, VALID_SEVERITIES

logger = structlog.get_logger(__name__)


class AnalysisAgent(LoggingMixin):
    """
    Specialized agent for analyzing validated maritime news articles.

    Generates comprehensive insights including:
    - Severity distribution analysis
    - Geographic hotspot identification
    - Category trend analysis
    - Risk prioritization
    - Client-specific alerts
    """

    def __init__(self):
        """Initialize analysis agent."""
        self.logger = logger.bind(agent="analysis")

        # Risk scoring weights
        self.severity_weights = {
            "high": 10,
            "medium": 5,
            "low": 1
        }

        # Geographic regions for hotspot analysis
        self.geographic_regions = {
            "red_sea_suez": ["suez", "red sea", "aden", "djibouti", "bab el mandeb"],
            "us_west_coast": ["los angeles", "long beach", "oakland", "seattle", "tacoma"],
            "us_east_coast": ["new york", "newark", "savannah", "charleston", "miami"],
            "europe_north": ["rotterdam", "hamburg", "antwerp", "felixstowe", "bremen"],
            "asia_pacific": ["shanghai", "singapore", "hong kong", "busan", "ningbo"],
            "middle_east": ["dubai", "jebel ali", "doha", "kuwait", "dammam"],
            "mediterranean": ["valencia", "barcelona", "genoa", "piraeus", "alexandria"]
        }

    async def analyze(self, validated_articles: List[Dict]) -> Dict[str, Any]:
        """
        Generate comprehensive analysis from validated articles.

        Args:
            validated_articles: List of validated article dictionaries

        Returns:
            Dictionary containing analysis results and insights
        """
        self.log_operation_start(
            "article_analysis",
            article_count=len(validated_articles)
        )

        try:
            if not validated_articles:
                self.logger.warning("No articles to analyze")
                return self._empty_analysis()

            # Generate all analysis components
            analysis_results = {
                "executive_summary": self._generate_executive_summary(validated_articles),
                "severity_analysis": self._analyze_severity_distribution(validated_articles),
                "geographic_hotspots": self._identify_geographic_hotspots(validated_articles),
                "category_trends": self._analyze_category_trends(validated_articles),
                "risk_prioritization": self._prioritize_risks(validated_articles),
                "temporal_analysis": self._analyze_temporal_patterns(validated_articles),
                "operational_alerts": self._generate_operational_alerts(validated_articles),
                "source_reliability": self._analyze_source_reliability(validated_articles),
                "incident_tracking": self._track_incidents(validated_articles),
                "client_recommendations": self._generate_client_recommendations(validated_articles)
            }

            self.log_operation_success(
                "article_analysis",
                insights_generated=len(analysis_results),
                high_risk_incidents=len([a for a in validated_articles if a["severity"] == "high"])
            )

            return analysis_results

        except Exception as e:
            self.log_operation_error("article_analysis", e)
            return self._empty_analysis(error=str(e))

    def _generate_executive_summary(self, articles: List[Dict]) -> Dict[str, Any]:
        """Generate executive summary of maritime situation."""
        total_articles = len(articles)
        high_severity = len([a for a in articles if a["severity"] == "high"])
        medium_severity = len([a for a in articles if a["severity"] == "medium"])

        # Top categories
        category_counts = Counter(a["category"] for a in articles)
        top_categories = category_counts.most_common(3)

        # Active regions
        all_ports = []
        for article in articles:
            if article.get("ports"):
                all_ports.extend(article["ports"])
        top_regions = Counter(all_ports).most_common(5)

        return {
            "total_incidents": total_articles,
            "high_severity_count": high_severity,
            "medium_severity_count": medium_severity,
            "critical_alert": high_severity > 3,
            "top_categories": [{"category": cat, "count": count} for cat, count in top_categories],
            "affected_regions": [{"region": region, "incidents": count} for region, count in top_regions],
            "overall_risk_level": self._calculate_overall_risk_level(articles),
            "key_highlights": self._extract_key_highlights(articles)
        }

    def _analyze_severity_distribution(self, articles: List[Dict]) -> Dict[str, Any]:
        """Analyze distribution of article severities."""
        severity_counts = Counter(a["severity"] for a in articles)
        total = len(articles)

        distribution = {}
        for severity in VALID_SEVERITIES:
            count = severity_counts.get(severity, 0)
            distribution[severity] = {
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 1)
            }

        return {
            "distribution": distribution,
            "total_articles": total,
            "risk_score": sum(
                severity_counts.get(sev, 0) * weight
                for sev, weight in self.severity_weights.items()
            ),
            "severity_trend": self._calculate_severity_trend(articles)
        }

    def _identify_geographic_hotspots(self, articles: List[Dict]) -> Dict[str, Any]:
        """Identify geographic regions with high incident concentration."""
        region_incidents = defaultdict(list)
        port_incidents = Counter()

        for article in articles:
            ports = article.get("ports", [])
            if not ports:
                continue

            for port in ports:
                port_lower = port.lower()
                port_incidents[port] += 1

                # Map to regions
                for region, keywords in self.geographic_regions.items():
                    if any(keyword in port_lower for keyword in keywords):
                        region_incidents[region].append({
                            "port": port,
                            "severity": article["severity"],
                            "category": article["category"],
                            "incident_type": article.get("incidentType", "unknown")
                        })
                        break

        # Calculate risk scores by region
        hotspots = []
        for region, incidents in region_incidents.items():
            risk_score = sum(
                self.severity_weights.get(inc["severity"], 1)
                for inc in incidents
            )
            hotspots.append({
                "region": region,
                "incident_count": len(incidents),
                "risk_score": risk_score,
                "severity_breakdown": Counter(inc["severity"] for inc in incidents),
                "top_incident_types": Counter(inc["incident_type"] for inc in incidents).most_common(3)
            })

        # Sort by risk score
        hotspots.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "hotspots": hotspots[:10],  # Top 10 risk regions
            "port_incidents": dict(port_incidents.most_common(15)),
            "total_affected_ports": len(port_incidents),
            "geographic_spread": len(region_incidents)
        }

    def _analyze_category_trends(self, articles: List[Dict]) -> Dict[str, Any]:
        """Analyze trends across news categories."""
        category_analysis = {}

        for category in VALID_CATEGORIES:
            category_articles = [a for a in articles if a["category"] == category]
            if not category_articles:
                continue

            severity_dist = Counter(a["severity"] for a in category_articles)
            incident_types = Counter(a.get("incidentType", "unknown") for a in category_articles)

            category_analysis[category] = {
                "total_incidents": len(category_articles),
                "severity_distribution": dict(severity_dist),
                "risk_score": sum(
                    severity_dist.get(sev, 0) * weight
                    for sev, weight in self.severity_weights.items()
                ),
                "top_incident_types": dict(incident_types.most_common(5)),
                "recent_trend": self._calculate_category_trend(category_articles)
            }

        # Sort categories by risk score
        sorted_categories = sorted(
            category_analysis.items(),
            key=lambda x: x[1]["risk_score"],
            reverse=True
        )

        return {
            "category_breakdown": dict(sorted_categories),
            "highest_risk_category": sorted_categories[0] if sorted_categories else None,
            "category_diversity": len(category_analysis),
            "trend_summary": self._generate_category_trend_summary(category_analysis)
        }

    def _prioritize_risks(self, articles: List[Dict]) -> Dict[str, Any]:
        """Prioritize risks based on severity, impact, and operational relevance."""
        high_priority_risks = []
        medium_priority_risks = []

        for article in articles:
            risk_score = self.severity_weights.get(article["severity"], 1)

            # Boost score for certain categories
            category_multipliers = {
                "red sea": 1.5,
                "operational issues": 1.3,
                "congestion": 1.2,
                "weather-related": 1.1
            }

            multiplier = category_multipliers.get(article["category"], 1.0)
            final_score = risk_score * multiplier

            risk_item = {
                "title": article["title"],
                "url": article["url"],
                "category": article["category"],
                "severity": article["severity"],
                "risk_score": final_score,
                "incident_type": article.get("incidentType", "unknown"),
                "summary": article.get("summary", ""),
                "ports": article.get("ports", []),
                "vessels": article.get("vessels", []),
                "date": article["date"]
            }

            if final_score >= 10:
                high_priority_risks.append(risk_item)
            elif final_score >= 3:
                medium_priority_risks.append(risk_item)

        # Sort by risk score
        high_priority_risks.sort(key=lambda x: x["risk_score"], reverse=True)
        medium_priority_risks.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "high_priority": high_priority_risks,
            "medium_priority": medium_priority_risks,
            "risk_distribution": {
                "critical": len(high_priority_risks),
                "elevated": len(medium_priority_risks),
                "normal": len(articles) - len(high_priority_risks) - len(medium_priority_risks)
            },
            "immediate_action_required": len(high_priority_risks) > 0
        }

    def _analyze_temporal_patterns(self, articles: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in incidents."""
        dates = [article["date"] for article in articles]
        date_counts = Counter(dates)

        # Group by date
        daily_incidents = {}
        for date, count in date_counts.items():
            daily_incidents[date] = {
                "total": count,
                "high_severity": len([a for a in articles if a["date"] == date and a["severity"] == "high"]),
                "categories": list(set(a["category"] for a in articles if a["date"] == date))
            }

        return {
            "daily_breakdown": daily_incidents,
            "peak_incident_date": max(date_counts, key=date_counts.get) if date_counts else None,
            "incident_velocity": len(date_counts),  # Number of days with incidents
            "temporal_trend": "increasing" if self._is_trend_increasing(date_counts) else "stable"
        }

    def _generate_operational_alerts(self, articles: List[Dict]) -> List[Dict]:
        """Generate specific operational alerts for immediate attention."""
        alerts = []

        # Critical severity articles become immediate alerts
        for article in articles:
            if article["severity"] == "high":
                alerts.append({
                    "level": "CRITICAL",
                    "title": f"High-Severity Incident: {article['title'][:80]}",
                    "category": article["category"],
                    "impact": self._assess_operational_impact(article),
                    "recommended_actions": self._recommend_actions(article),
                    "url": article["url"],
                    "date": article["date"]
                })

        # Special alerts for specific conditions
        red_sea_articles = [a for a in articles if a["category"] == "red sea"]
        if len(red_sea_articles) >= 2:
            alerts.append({
                "level": "WARNING",
                "title": f"Elevated Red Sea Activity: {len(red_sea_articles)} incidents",
                "category": "geopolitical",
                "impact": "Route diversions and delays likely",
                "recommended_actions": ["Monitor Suez transit", "Consider Cape route", "Review security protocols"],
                "articles": len(red_sea_articles)
            })

        return sorted(alerts, key=lambda x: x["level"] == "CRITICAL", reverse=True)

    def _analyze_source_reliability(self, articles: List[Dict]) -> Dict[str, Any]:
        """Analyze reliability and coverage of news sources."""
        source_stats = defaultdict(lambda: {
            "article_count": 0,
            "high_severity": 0,
            "categories_covered": set(),
            "unique_incidents": 0
        })

        for article in articles:
            source = article["source"]
            source_stats[source]["article_count"] += 1
            if article["severity"] == "high":
                source_stats[source]["high_severity"] += 1
            source_stats[source]["categories_covered"].add(article["category"])

        # Convert sets to lists and calculate metrics
        reliability_analysis = {}
        for source, stats in source_stats.items():
            reliability_analysis[source] = {
                "total_articles": stats["article_count"],
                "high_severity_articles": stats["high_severity"],
                "categories_covered": list(stats["categories_covered"]),
                "category_diversity": len(stats["categories_covered"]),
                "reliability_score": self._calculate_source_reliability(stats)
            }

        return reliability_analysis

    def _track_incidents(self, articles: List[Dict]) -> Dict[str, Any]:
        """Track and categorize different types of incidents."""
        incident_types = Counter(a.get("incidentType", "unknown") for a in articles)

        # Group related incidents
        incident_families = {
            "port_operations": ["port closure", "strike", "terminal closure", "berth delays"],
            "vessel_incidents": ["collision", "grounding", "fire", "mechanical failure"],
            "security_threats": ["attack", "seizure", "piracy", "threat"],
            "weather_events": ["storm", "hurricane", "typhoon", "ice", "fog"],
            "supply_chain": ["congestion", "delays", "capacity", "equipment shortage"]
        }

        family_counts = defaultdict(int)
        for incident_type, count in incident_types.items():
            categorized = False
            for family, keywords in incident_families.items():
                if any(keyword in incident_type.lower() for keyword in keywords):
                    family_counts[family] += count
                    categorized = True
                    break
            if not categorized:
                family_counts["other"] += count

        return {
            "incident_types": dict(incident_types.most_common(10)),
            "incident_families": dict(family_counts),
            "total_incident_types": len(incident_types),
            "most_common_incident": incident_types.most_common(1)[0] if incident_types else None
        }

    def _generate_client_recommendations(self, articles: List[Dict]) -> List[Dict]:
        """Generate specific recommendations for clients."""
        recommendations = []

        # Route optimization recommendations
        red_sea_incidents = len([a for a in articles if a["category"] == "red sea"])
        if red_sea_incidents >= 2:
            recommendations.append({
                "priority": "high",
                "category": "routing",
                "title": "Consider Red Sea Route Alternatives",
                "description": f"With {red_sea_incidents} Red Sea incidents reported, evaluate Cape of Good Hope routing",
                "impact": "Potential 10-14 day delay but increased security",
                "action_items": [
                    "Review current Red Sea transits",
                    "Analyze Cape route economics",
                    "Coordinate with security teams"
                ]
            })

        # Port congestion recommendations
        congestion_ports = set()
        for article in articles:
            if article["category"] == "congestion" and article.get("ports"):
                congestion_ports.update(article["ports"])

        if congestion_ports:
            recommendations.append({
                "priority": "medium",
                "category": "operations",
                "title": "Port Congestion Mitigation",
                "description": f"Congestion reported at {len(congestion_ports)} ports",
                "impact": "Potential delays and demurrage costs",
                "affected_ports": list(congestion_ports),
                "action_items": [
                    "Review schedules for affected ports",
                    "Consider alternative ports",
                    "Negotiate flexible arrival windows"
                ]
            })

        return recommendations

    # Helper methods
    def _calculate_overall_risk_level(self, articles: List[Dict]) -> str:
        """Calculate overall risk level."""
        high_count = len([a for a in articles if a["severity"] == "high"])
        total = len(articles)

        if high_count >= 5 or (total > 0 and high_count / total > 0.3):
            return "HIGH"
        elif high_count >= 2 or (total > 0 and high_count / total > 0.1):
            return "MEDIUM"
        else:
            return "LOW"

    def _extract_key_highlights(self, articles: List[Dict]) -> List[str]:
        """Extract key highlights from articles."""
        highlights = []

        # High severity incidents
        high_sev_articles = [a for a in articles if a["severity"] == "high"]
        for article in high_sev_articles[:3]:  # Top 3
            highlights.append(f"HIGH RISK: {article['incidentType']} - {article['title'][:60]}...")

        # Major categories
        category_counts = Counter(a["category"] for a in articles)
        for category, count in category_counts.most_common(2):
            if count >= 2:
                highlights.append(f"{count} incidents in {category.replace('_', ' ').title()} category")

        return highlights[:5]  # Maximum 5 highlights

    def _calculate_severity_trend(self, articles: List[Dict]) -> str:
        """Calculate if severity is trending up or down."""
        # Simplified trend analysis
        dates = sorted(set(a["date"] for a in articles))
        if len(dates) < 2:
            return "insufficient_data"

        # Compare first half vs second half
        mid_point = len(dates) // 2
        early_dates = dates[:mid_point]
        recent_dates = dates[mid_point:]

        early_high = len([a for a in articles if a["date"] in early_dates and a["severity"] == "high"])
        recent_high = len([a for a in articles if a["date"] in recent_dates and a["severity"] == "high"])

        if recent_high > early_high * 1.5:
            return "escalating"
        elif recent_high < early_high * 0.5:
            return "improving"
        else:
            return "stable"

    def _calculate_category_trend(self, category_articles: List[Dict]) -> str:
        """Calculate trend for specific category."""
        if len(category_articles) < 3:
            return "insufficient_data"
        return "stable"  # Simplified

    def _generate_category_trend_summary(self, category_analysis: Dict) -> str:
        """Generate summary of category trends."""
        if not category_analysis:
            return "No significant trends detected"

        highest_risk = max(category_analysis.items(), key=lambda x: x[1]["risk_score"])
        return f"Primary concern: {highest_risk[0].replace('_', ' ').title()} ({highest_risk[1]['total_incidents']} incidents)"

    def _is_trend_increasing(self, date_counts: Counter) -> bool:
        """Check if incident trend is increasing."""
        if len(date_counts) < 2:
            return False

        dates = sorted(date_counts.keys())
        mid_point = len(dates) // 2
        early_avg = sum(date_counts[d] for d in dates[:mid_point]) / mid_point
        recent_avg = sum(date_counts[d] for d in dates[mid_point:]) / (len(dates) - mid_point)

        return recent_avg > early_avg * 1.2

    def _assess_operational_impact(self, article: Dict) -> str:
        """Assess operational impact of an incident."""
        severity = article["severity"]
        category = article["category"]

        impact_matrix = {
            ("high", "operational issues"): "Immediate service disruption likely",
            ("high", "red sea"): "Route diversions and significant delays",
            ("high", "weather-related"): "Port closures and vessel delays",
            ("high", "congestion"): "Extended berth waiting times",
            ("medium", "operational issues"): "Potential service adjustments",
            ("medium", "congestion"): "Moderate delays expected"
        }

        return impact_matrix.get((severity, category), "Monitor for operational impact")

    def _recommend_actions(self, article: Dict) -> List[str]:
        """Recommend specific actions based on article."""
        category = article["category"]
        severity = article["severity"]

        action_map = {
            "red sea": ["Review security protocols", "Consider route alternatives", "Monitor situation"],
            "operational issues": ["Contact local agents", "Review service schedules", "Prepare contingency plans"],
            "weather-related": ["Monitor weather updates", "Secure cargo", "Review port schedules"],
            "congestion": ["Optimize arrival times", "Consider port alternatives", "Negotiate demurrage terms"]
        }

        actions = action_map.get(category, ["Monitor situation closely"])

        if severity == "high":
            actions.insert(0, "Immediate assessment required")

        return actions

    def _calculate_source_reliability(self, stats: Dict) -> float:
        """Calculate reliability score for news source."""
        article_count = stats["article_count"]
        category_diversity = len(stats["categories_covered"])
        high_severity = stats["high_severity"]

        # Simple scoring formula
        diversity_score = min(category_diversity / 3, 1.0)  # Max 3 categories
        volume_score = min(article_count / 5, 1.0)  # Max 5 articles
        quality_score = (high_severity / article_count) if article_count > 0 else 0

        return round((diversity_score + volume_score + quality_score) / 3 * 10, 1)

    def _empty_analysis(self, error: str = None) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "executive_summary": {"total_incidents": 0, "critical_alert": False},
            "severity_analysis": {"distribution": {}, "risk_score": 0},
            "geographic_hotspots": {"hotspots": [], "total_affected_ports": 0},
            "category_trends": {"category_breakdown": {}},
            "risk_prioritization": {"high_priority": [], "medium_priority": []},
            "temporal_analysis": {"daily_breakdown": {}},
            "operational_alerts": [],
            "source_reliability": {},
            "incident_tracking": {"incident_types": {}},
            "client_recommendations": [],
            "error": error
        }