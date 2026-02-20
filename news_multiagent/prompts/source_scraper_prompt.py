"""
Systematic Scraping Prompts for Claude Computer Use

Generates comprehensive prompts that guide Claude through structured
web scraping of maritime news sources with date validation.
"""

from typing import Dict


def generate_scraping_prompt(source_config: Dict, cutoff_date: str, today: str) -> str:
    """
    Generate systematic scraping prompt for Claude Computer Use.

    Args:
        source_config: Source configuration (name, homepage, target_count)
        cutoff_date: Earliest acceptable date (YYYY-MM-DD)
        today: Current date (YYYY-MM-DD)

    Returns:
        Comprehensive scraping prompt for Claude
    """

    source_name = source_config["name"]
    homepage = source_config["homepage"]
    target_count = source_config["target_count"]

    return f"""You are an expert maritime news scraper specializing in operational disruptions.

# MISSION
Systematically scrape {source_name} ({homepage}) to find {target_count}+ recent maritime shipping articles with immediate operational impact.

# CRITICAL CONSTRAINTS
- TODAY: {today}
- CUTOFF_DATE: {cutoff_date}
- ONLY accept articles with publication dates BETWEEN {cutoff_date} and {today}
- REJECT articles with only "updated" or "last modified" timestamps
- REJECT articles older than cutoff date or future-dated

# SYSTEMATIC SCRAPING PROTOCOL

## Step 1: Homepage Analysis
Use web_fetch to load: {homepage}

Identify:
- News section links
- Recent article headlines (last 3-7 days)
- Pagination controls
- Article URL patterns

## Step 2: Article Discovery
For EACH promising article:
1. Use web_fetch to load the full article page
2. Extract publication date from article CONTENT using these methods:
   - Article byline (e.g., "Published: January 15, 2024")
   - URL date patterns (e.g., /2024/01/15/)
   - Meta tags: <meta property="article:published_time">
   - Relative timestamps ("3 hours ago", "Yesterday")
   - Date in article text near headline

## Step 3: Date Validation (IMMEDIATE)
For each article date found:
- Convert to YYYY-MM-DD format
- IF date < {cutoff_date}: REJECT immediately
- IF date > {today}: REJECT immediately
- IF only "updated/modified" date: REJECT immediately
- ONLY proceed if date in valid range

## Step 4: Content Analysis (Only for date-validated articles)
Extract these fields:

**Required Fields:**
- url: Full article URL
- title: Article headline
- date: Publication date (YYYY-MM-DD format)
- source: "{source_name}"
- category: ONE of [red sea, geopolitical, weather-related, congestion, operational issues, us tariffs, shipping line announcements, vessel/container incidents]
- severity: high/medium/low based on operational impact
- incidentType: Brief incident description
- summary: 2-3 sentence summary of operational impact

**Optional Fields:**
- ports: List of affected ports/terminals
- vessels: List of mentioned vessels/ships

## Step 5: Operational Impact Filter
INCLUDE articles about:
✓ Active disruptions (port closures, strikes, severe congestion)
✓ Security threats (Red Sea attacks, vessel seizures)
✓ Weather incidents (storms closing ports, typhoon delays)
✓ Resolved major incidents (ship departures after repairs)
✓ Service changes with operational impact
✓ Tariff/policy changes affecting shipping

EXCLUDE articles about:
✗ Market analysis/statistics only
✗ Corporate earnings/appointments
✗ Individual accidents without port closure
✗ Tanker news (unless blocking shipping lanes)
✗ Historical retrospectives
✗ General industry trends

## Step 6: Categorization Rules

**red sea**: Red Sea/Suez security, Houthi attacks, route diversions around Africa
**geopolitical**: Sanctions, trade wars, vessel seizures, diplomatic tensions
**weather-related**: Storms, hurricanes, typhoons, ice conditions, port weather closures
**congestion**: Port congestion, berth delays, terminal capacity issues, long queues
**operational issues**: Equipment failures, strikes, IT outages, terminal closures
**us tariffs**: US tariff policies, trade restrictions, customs delays
**shipping line announcements**: Service changes, route adjustments, capacity changes
**vessel/container incidents**: Collisions, groundings, fires, container losses

## Step 7: Severity Assignment

**HIGH**: Immediate major disruption
- Port closures/strikes
- Severe congestion (>7 day delays)
- Security threats blocking lanes
- Major vessel incidents closing ports

**MEDIUM**: Moderate/potential disruption OR resolved major incidents
- Vessel departures after repairs
- Service adjustments
- Minor congestion (2-7 day delays)
- Weather warnings

**LOW**: Informational updates
- Service enhancements
- Minor operational updates
- Resolved minor incidents

# OUTPUT FORMAT
Return ONLY a JSON array of validated articles:

```json
[
  {{
    "url": "https://example.com/article1",
    "title": "Port of Los Angeles Strike Causes Major Delays",
    "date": "2024-01-15",
    "source": "{source_name}",
    "category": "operational issues",
    "severity": "high",
    "incidentType": "Port strike",
    "summary": "Longshoremen strike at Port of Los Angeles causing 5-day container delays affecting US West Coast operations.",
    "ports": ["Los Angeles"],
    "vessels": []
  }}
]
```

# SUCCESS CRITERIA
- Find minimum {target_count} articles with valid dates
- Each article MUST have publication date in range [{cutoff_date}, {today}]
- Focus on operational disruption impact
- Accurate categorization and severity assessment
- NO corporate news, market analysis, or irrelevant content

Start by analyzing {homepage} and systematically work through recent articles. Validate dates IMMEDIATELY before spending time on content analysis."""

    return prompt.strip()


def generate_category_search_prompt(search_config: Dict, cutoff_date: str, today: str) -> str:
    """
    Generate prompt for Phase 2 category gap searches.

    Args:
        search_config: Search configuration (query, category, target_count)
        cutoff_date: Earliest acceptable date
        today: Current date

    Returns:
        Comprehensive search prompt for Claude
    """

    query = search_config["query"]
    category = search_config["category"]
    target_count = search_config.get("target_count", 5)

    return f"""You are conducting a targeted search for maritime shipping news gaps.

# MISSION
Execute web search for: "{query}"
Find {target_count}+ recent articles in category: {category}

# CONSTRAINTS
- TODAY: {today}
- CUTOFF_DATE: {cutoff_date}
- Only articles published between {cutoff_date} and {today}
- Focus on operational impact to shipping

# SEARCH PROTOCOL

## Step 1: Execute Search
Use web_search with query: "{query}"
Review top 15 results for maritime shipping relevance

## Step 2: Article Processing
For each promising result:
1. Use web_fetch to load full article
2. Extract publication date from content (NOT search metadata)
3. Validate date is in range [{cutoff_date}, {today}]
4. If valid, extract full metadata

## Step 3: Category Focus
Ensure articles fit category: {category}
Apply same operational impact filter as source scraping

# OUTPUT
JSON array of {target_count}+ validated articles in same format as source scraping.
Focus on filling gaps not covered by primary source scraping."""

    return prompt.strip()