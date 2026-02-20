"""
Validation prompts for article quality control and deduplication.
"""

from typing import List, Dict


def generate_validation_prompt(articles: List[Dict]) -> str:
    """
    Generate prompt for article validation and deduplication.

    Args:
        articles: List of articles to validate

    Returns:
        Validation prompt for Claude
    """
    return f"""You are a maritime news validation specialist responsible for quality control.

# MISSION
Review {len(articles)} maritime news articles and perform:
1. Quality validation
2. Deduplication
3. Authority ranking
4. Final categorization

# VALIDATION CRITERIA

## Required Fields Check
- URL (valid format)
- Title (minimum 10 characters)
- Date (YYYY-MM-DD format)
- Source (authoritative maritime source)
- Category (one of 8 valid categories)
- Severity (high/medium/low)
- Summary (minimum 20 characters)

## Content Quality
- Operational relevance to shipping
- Clear incident description
- Specific geographic or vessel details
- Recent publication (within date range)

## Deduplication Rules
- Same URL → remove duplicate
- Similar titles (>80% match) → keep more authoritative source
- Same incident → consolidate or keep primary source

# SOURCE AUTHORITY RANKING
1. The Loadstar (10)
2. Container News (9)
3. Maersk (8)
4. CMA CGM (8)
5. gCaptain (7)
6. Kuehne+Nagel (6)
7. Port News (5)

# OUTPUT FORMAT
Return JSON with:
```json
{{
  "valid_articles": [
    // All validated and deduplicated articles
  ],
  "rejected_articles": [
    {{
      "url": "rejected_url",
      "reason": "specific rejection reason"
    }}
  ],
  "statistics": {{
    "total_processed": {len(articles)},
    "valid_count": 0,
    "duplicate_count": 0,
    "quality_rejected": 0
  }}
}}
```

Focus on operational impact and authority-based deduplication."""


def generate_analysis_prompt(validated_articles: List[Dict]) -> str:
    """
    Generate prompt for comprehensive maritime news analysis.

    Args:
        validated_articles: List of validated articles

    Returns:
        Analysis prompt for Claude
    """
    return f"""You are a maritime intelligence analyst specializing in operational risk assessment.

# MISSION
Analyze {len(validated_articles)} validated maritime news articles to generate:
1. Executive risk summary
2. Geographic hotspot identification
3. Category trend analysis
4. Operational recommendations

# ANALYSIS FRAMEWORK

## Risk Assessment Matrix
- HIGH: Port closures, strikes, severe congestion, security threats
- MEDIUM: Service disruptions, moderate delays, resolved incidents
- LOW: Informational updates, minor operational changes

## Geographic Focus Areas
- Red Sea / Suez Canal (security, diversions)
- US West Coast (LA, Long Beach, Oakland, Seattle)
- US East Coast (NY/NJ, Savannah, Charleston)
- European Hubs (Rotterdam, Hamburg, Antwerp)
- Asia-Pacific (Shanghai, Singapore, Hong Kong)

## Category Analysis
Track trends across:
- red sea (Houthi attacks, route diversions)
- geopolitical (sanctions, trade tensions)
- weather-related (storms, port closures)
- congestion (delays, capacity issues)
- operational issues (strikes, equipment failures)
- us tariffs (trade policy impacts)
- shipping line announcements (service changes)
- vessel/container incidents (accidents, groundings)

# OUTPUT REQUIREMENTS
Generate comprehensive analysis with:
- Executive summary with key risk indicators
- Geographic hotspot ranking with impact scores
- Category trend analysis with operational implications
- Prioritized client recommendations
- Immediate action alerts for HIGH severity incidents

Focus on actionable intelligence for shipping operations decision-making."""

    return prompt.strip()