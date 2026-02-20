"""
Analysis prompts for generating maritime intelligence insights.
"""

from typing import List, Dict


def generate_analysis_prompt(validated_articles: List[Dict]) -> str:
    """
    Generate prompt for comprehensive maritime news analysis.

    Args:
        validated_articles: List of validated articles

    Returns:
        Analysis prompt for Claude
    """
    return f"""You are a senior maritime intelligence analyst with expertise in global shipping operations.

# MISSION
Analyze {len(validated_articles)} validated maritime news articles to generate actionable intelligence for shipping operations teams.

# ANALYSIS OBJECTIVES

## 1. Executive Risk Assessment
- Overall threat level (HIGH/MEDIUM/LOW)
- Critical incidents requiring immediate attention
- Emerging risk patterns
- Operational impact summary

## 2. Geographic Risk Mapping
Identify hotspots in key regions:
- Red Sea/Suez Canal (security, route diversions)
- US Ports (West Coast: LA/LB/Oakland; East Coast: NY/NJ/Savannah)
- European Hubs (Rotterdam, Hamburg, Antwerp, Felixstowe)
- Asia-Pacific (Shanghai, Singapore, Hong Kong, Busan)
- Middle East (Jebel Ali, Kuwait, Dammam)

## 3. Category Intelligence
Analyze trends across:
- **Red Sea**: Houthi attacks, military operations, route diversions
- **Geopolitical**: Sanctions, trade wars, vessel seizures
- **Weather-Related**: Storms, port closures, seasonal impacts
- **Congestion**: Port delays, berth availability, capacity constraints
- **Operational Issues**: Strikes, equipment failures, system outages
- **US Tariffs**: Trade policy impacts, customs delays
- **Shipping Line Announcements**: Service changes, capacity adjustments
- **Vessel/Container Incidents**: Collisions, groundings, cargo losses

## 4. Operational Recommendations
Generate specific actions for:
- Route optimization decisions
- Port selection alternatives
- Risk mitigation strategies
- Schedule adjustments
- Contingency planning

# INTELLIGENCE PRIORITIES

## Immediate Alerts (HIGH Severity)
- Port closures affecting major trade lanes
- Security threats blocking shipping routes
- Severe weather events closing multiple ports
- Major vessel incidents affecting port operations

## Tactical Monitoring (MEDIUM Severity)
- Service disruptions with workaround options
- Moderate congestion with manageable delays
- Policy changes with operational implications

## Strategic Awareness (LOW Severity)
- Industry trends and market intelligence
- Future service enhancements
- Resolved incidents with lessons learned

# OUTPUT STRUCTURE

Generate comprehensive intelligence report with:

1. **Executive Summary**
   - Overall risk level and key concerns
   - Critical incidents count
   - Primary affected regions
   - Immediate actions required

2. **Geographic Hotspots**
   - Risk-ranked regions with impact scores
   - Port-specific incident analysis
   - Route implications and alternatives

3. **Category Trends**
   - Incident volume by category
   - Risk progression analysis
   - Pattern identification

4. **Operational Intelligence**
   - High-priority risks requiring immediate response
   - Medium-priority situations for tactical planning
   - Strategic considerations for route planning

5. **Client Recommendations**
   - Specific actionable steps
   - Risk mitigation strategies
   - Alternative routing suggestions
   - Timeline for decision-making

# ANALYSIS STANDARDS
- Focus on operational impact over statistical analysis
- Prioritize actionable intelligence over general information
- Emphasize time-sensitive risks requiring immediate decisions
- Consider cascading effects and interconnected impacts
- Maintain objectivity while highlighting critical risks

Generate professional maritime intelligence suitable for senior operations management."""

    return prompt.strip()


def generate_dashboard_prompt(analysis_results: Dict) -> str:
    """
    Generate prompt for dashboard content creation.

    Args:
        analysis_results: Comprehensive analysis results

    Returns:
        Dashboard generation prompt
    """
    return f"""You are a data visualization specialist creating an executive maritime intelligence dashboard.

# MISSION
Transform analysis results into a comprehensive React/TypeScript dashboard for maritime operations management.

# DASHBOARD REQUIREMENTS

## Structure
- 8 category tabs with article filtering
- Severity-based filtering (All, High, Medium, Low)
- Interactive article cards with metadata
- Summary statistics and risk indicators
- Comprehensive methodology footer

## Category Tabs
1. Red Sea (security threats, route diversions)
2. Geopolitical (sanctions, trade tensions)
3. Weather-Related (storms, port closures)
4. Congestion (port delays, capacity issues)
5. Operational Issues (strikes, equipment failures)
6. US Tariffs (trade policy impacts)
7. Shipping Line Announcements (service changes)
8. Vessel/Container Incidents (accidents, groundings)

## Article Card Format
Each article should display:
- Severity indicator (color-coded)
- Source authority badge
- Publication date
- Incident type and category
- Port/vessel tags
- Summary with operational impact
- Direct link to full article

## Statistics Panel
- Total articles processed
- Severity distribution
- Geographic spread
- Category breakdown
- Risk trend indicators

Generate complete React/TypeScript code with:
- Professional maritime industry styling
- Responsive design for desktop/tablet
- Interactive filtering and sorting
- Clear risk visualization
- Export capabilities for reports

Focus on executive-level presentation with actionable intelligence."""

    return prompt.strip()