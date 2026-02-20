#!/usr/bin/env python3
"""
Quick Test Script - Run this to see the optimizations in action!

Usage: python quick_test.py
"""

import sys
import time
from datetime import datetime, timedelta

# Add the project root to sys.path so we can import modules
sys.path.append('/home/niloufar/datascience-jupyter/datascience-jupyter/10_AI_Projects/News_Agent/news_multiagent')

try:
    from graph.incident_graph import IncidentGraph
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)

def create_test_articles():
    """Create sample articles to test with."""

    # Create a Red Sea incident that develops over time (topic continuation)
    red_sea_timeline = []
    base_date = datetime.now() - timedelta(days=10)

    for i, (title, severity) in enumerate([
        ("Houthi attack on container ship in Red Sea", "high"),
        ("Major shipping lines suspend Red Sea operations", "high"),
        ("Red Sea diversions cause global shipping delays", "medium"),
        ("Some carriers resume limited Red Sea transits", "low")
    ]):
        red_sea_timeline.append({
            "url": f"https://loadstar.com/red-sea-{i}",
            "title": title,
            "date": (base_date + timedelta(days=i*2)).strftime("%Y-%m-%d"),
            "source": "The Loadstar",
            "category": "red_sea",
            "severity": severity,
            "incidentType": "security_threat",
            "ports": ["Suez Canal"],
            "vessels": ["MSC Aries"],
            "summary": f"Red Sea incident development stage {i+1}"
        })

    # Create some duplicate articles (same incident, different sources)
    duplicates = [
        {
            "url": "https://container-news.com/red-sea-duplicate",
            "title": "Houthis attack container ship in Red Sea corridor",  # Similar to first article
            "date": base_date.strftime("%Y-%m-%d"),
            "source": "Container News",
            "category": "red_sea",
            "severity": "high",
            "incidentType": "security_threat",
            "ports": ["Suez Canal"],
            "vessels": ["MSC Aries"],
            "summary": "Duplicate report of Red Sea attack"
        }
    ]

    # Create unrelated articles
    other_articles = [
        {
            "url": "https://gcaptain.com/port-congestion",
            "title": "Port of Los Angeles sees increased congestion",
            "date": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
            "source": "gCaptain",
            "category": "congestion",
            "severity": "medium",
            "incidentType": "port_congestion",
            "ports": ["Port of Los Angeles"],
            "vessels": [],
            "summary": "West Coast port congestion report"
        }
    ]

    return red_sea_timeline + duplicates + other_articles

def test_optimized_performance():
    """Test the optimized graph performance."""

    print("🌊 MARITIME NEWS MARITIME NEWS - QUICK PERFORMANCE TEST")
    print("=" * 55)

    # Create test data
    articles = create_test_articles()
    print(f"📝 Created {len(articles)} test articles")

    # Test with optimizations enabled
    print("\n🚀 Testing WITH optimizations:")
    print("-" * 35)

    graph = IncidentGraph(
        similarity_threshold=0.7,
        temporal_window_days=30,
        enable_performance_optimizations=True
    )

    start_time = time.time()
    new_articles, deduplicated = graph.add_articles(articles)
    processing_time = time.time() - start_time

    print(f"⏱️  Processing time: {processing_time:.3f} seconds")
    print(f"📄 New articles: {len(new_articles)}")
    print(f"🔄 Deduplicated: {len(deduplicated)}")
    print(f"📊 Total nodes in graph: {graph.graph.number_of_nodes()}")
    print(f"🔗 Total edges in graph: {graph.graph.number_of_edges()}")

    # Test topic continuation
    print("\n📈 Topic continuation analysis:")
    print("-" * 35)

    timelines = graph.get_topic_timelines(min_articles=2, days_back=15)

    if timelines:
        for topic_signature, timeline in timelines.items():
            print(f"\n🎯 Found timeline: {topic_signature}")
            print(f"   📰 Articles: {len(timeline)}")
            print(f"   📅 Dates: {timeline[0]['date']} → {timeline[-1]['date']}")

            # Show the story progression
            print("   📖 Story progression:")
            for i, article in enumerate(timeline):
                print(f"      {i+1}. [{article['date']}] {article['title'][:40]}...")

            # Analyze development
            analysis = graph.analyze_topic_development(topic_signature)
            if "error" not in analysis:
                print(f"   🔍 Analysis:")
                print(f"      • Severity trend: {analysis['severity_trend']}")
                print(f"      • Source diversity: {analysis['source_diversity']}")

                if analysis["continuation_indicators"]["is_ongoing"]:
                    print("      • 🚨 ONGOING STORY detected!")
                if analysis["continuation_indicators"]["is_escalating"]:
                    print("      • ⬆️  ESCALATING situation!")
    else:
        print("   📝 No multi-article timelines found (need more test data)")

    # Show incident clusters
    print("\n🔗 Incident clustering:")
    print("-" * 25)

    clusters = graph.get_incident_clusters()
    if clusters:
        for i, cluster in enumerate(clusters[:3]):  # Show top 3 clusters
            print(f"\n📊 Cluster {i+1}:")
            print(f"   📄 Articles: {len(cluster)}")
            print(f"   🏷️  Categories: {list(set(a.get('category') for a in cluster))}")
            print(f"   📅 Date range: {min(a.get('date', '') for a in cluster)} → {max(a.get('date', '') for a in cluster)}")
    else:
        print("   📝 No multi-article clusters found")

    print("\n" + "=" * 55)
    print("✅ QUICK TEST COMPLETE!")
    print("\n💡 Key Features Demonstrated:")
    print("   🚀 Fast processing with optimized similarity checks")
    print("   🔄 Automatic duplicate detection across sources")
    print("   📈 Topic continuation tracking over time")
    print("   🔗 Intelligent incident clustering")

    return graph

def main():
    """Run the quick test."""
    try:
        graph = test_optimized_performance()

        print(f"\n🛠️  Graph stats:")
        stats = graph.get_graph_statistics()
        print(f"   📊 Total articles: {stats['total_nodes']}")
        print(f"   🔗 Connections: {stats['total_edges']}")
        print(f"   📈 Connected components: {stats['connected_components']}")
        print(f"   🏷️  Categories: {list(stats['category_distribution'].keys())}")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        print("This might be due to missing dependencies or import issues.")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()