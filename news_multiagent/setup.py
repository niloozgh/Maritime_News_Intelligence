#!/usr/bin/env python3
"""
Maritime Intelligence Engine - Setup Configuration

Professional Python package setup for hackathon submission.
Demonstrates enterprise-grade packaging and dependency management.
"""

from setuptools import setup, find_packages
import os
import sys

# Ensure Python 3.9+
if sys.version_info < (3, 9):
    sys.exit("Maritime Intelligence Engine requires Python 3.9 or higher")

# Read long description from README
def read_long_description():
    """Read project description from README.md"""
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from file
def read_requirements(filename):
    """Read requirements from requirements file"""
    try:
        with open(filename, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []

# Project metadata
PACKAGE_NAME = "maritime-intelligence"
VERSION = "1.0.0"
DESCRIPTION = "AI-Powered Maritime News Intelligence with Graph-Based Analysis"
AUTHOR = "AI Engineering Team"
AUTHOR_EMAIL = "engineering@maritime-intelligence.ai"
URL = "https://github.com/yourusername/maritime-intelligence-engine"
LICENSE = "MIT"

# Python version requirements
PYTHON_REQUIRES = ">=3.9"

# Package classifiers for PyPI (demonstrates professional standards)
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Financial and Insurance Industry",
    "Intended Audience :: Manufacturing",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Scientific/Engineering :: Information Analysis",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
    "Environment :: Console",
    "Natural Language :: English",
]

# Keywords for discoverability
KEYWORDS = [
    "ai", "artificial-intelligence", "machine-learning",
    "graph-algorithms", "networkx", "langgraph",
    "maritime", "shipping", "supply-chain",
    "news-analysis", "intelligence", "clustering",
    "performance-optimization", "multi-agent-systems",
    "real-time-processing", "enterprise-ai"
]

# Core requirements
CORE_REQUIREMENTS = [
    # Core AI/ML frameworks
    "networkx>=3.2.1",
    "scipy>=1.11.0",
    "pandas>=2.1.0",
    "numpy>=1.24.0",

    # LangGraph and multi-agent systems
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "anthropic>=0.34.0",

    # Web scraping and data processing
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "playwright>=1.40.0",

    # Configuration and environment management
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",

    # Database and persistence
    "asyncpg>=0.29.0",
    "sqlalchemy>=2.0.25",
    "alembic>=1.13.0",

    # Logging and monitoring
    "structlog>=23.2.0",
    "prometheus-client>=0.19.0",

    # Date and time utilities
    "python-dateutil>=2.8.0",
    "pytz>=2023.3",
]

# Development requirements
DEV_REQUIREMENTS = [
    # Testing
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.0",

    # Code quality
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",

    # Documentation
    "sphinx>=7.1.0",
    "sphinx-rtd-theme>=1.3.0",

    # Performance profiling
    "memory-profiler>=0.61.0",
    "py-spy>=0.3.14",
]

# Optional extras for enhanced functionality
EXTRAS_REQUIRE = {
    "dev": DEV_REQUIREMENTS,
    "visualization": ["plotly>=5.15.0", "dash>=2.14.0"],
    "ml-extended": ["scikit-learn>=1.3.0", "xgboost>=2.0.0"],
    "cloud": ["boto3>=1.34.0", "google-cloud-storage>=2.10.0"],
    "monitoring": ["sentry-sdk>=1.38.0", "datadog>=0.47.0"],
    "all": DEV_REQUIREMENTS + [
        "plotly>=5.15.0", "dash>=2.14.0",
        "scikit-learn>=1.3.0", "xgboost>=2.0.0",
        "boto3>=1.34.0", "google-cloud-storage>=2.10.0",
        "sentry-sdk>=1.38.0", "datadog>=0.47.0"
    ]
}

# Console scripts for easy CLI access
CONSOLE_SCRIPTS = [
    "maritime-intelligence=maritime_intelligence.cli:main",
    "maritime-demo=maritime_intelligence.demo:run_demo",
    "maritime-benchmark=maritime_intelligence.benchmark:run_benchmark",
]

# Package data to include
PACKAGE_DATA = {
    "maritime_intelligence": [
        "config/*.yaml",
        "config/*.json",
        "prompts/*.txt",
        "templates/*.html",
        "static/*",
    ]
}

# Main setup configuration
setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,

    # Package discovery
    packages=find_packages(exclude=["tests*", "docs*", "examples*"]),
    package_data=PACKAGE_DATA,
    include_package_data=True,

    # Python and dependency requirements
    python_requires=PYTHON_REQUIRES,
    install_requires=CORE_REQUIREMENTS,
    extras_require=EXTRAS_REQUIRE,

    # Entry points for CLI tools
    entry_points={
        "console_scripts": CONSOLE_SCRIPTS,
    },

    # Package metadata for discovery and classification
    classifiers=CLASSIFIERS,
    keywords=" ".join(KEYWORDS),
    platforms=["any"],
    zip_safe=False,

    # Project URLs for enhanced discoverability
    project_urls={
        "Documentation": "https://maritime-intelligence.readthedocs.io/",
        "Source Code": "https://github.com/yourusername/maritime-intelligence-engine",
        "Issue Tracker": "https://github.com/yourusername/maritime-intelligence-engine/issues",
        "Demo": "https://maritime-intelligence-demo.com",
        "Changelog": "https://github.com/yourusername/maritime-intelligence-engine/blob/main/CHANGELOG.md",
    },
)

# Post-installation success message
def post_install_message():
    """Display success message after installation"""
    print("\n" + "="*60)
    print("🌊 Maritime Intelligence Engine Successfully Installed! 🚀")
    print("="*60)
    print("")
    print("Quick Start Commands:")
    print("  maritime-demo              # Run interactive demo")
    print("  maritime-benchmark         # Performance benchmarks")
    print("  maritime-intelligence --help  # Full CLI options")
    print("")
    print("Next Steps:")
    print("1. Copy .env.example to .env and add your API keys")
    print("2. Run 'maritime-demo' to see the intelligence in action")
    print("3. Check README.md for detailed usage examples")
    print("")
    print("🏆 Built for hackathons • 🧠 Advanced AI engineering")
    print("="*60)
    print("")

if __name__ == "__main__":
    post_install_message()