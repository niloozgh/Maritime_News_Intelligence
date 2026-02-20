# Multi-stage Dockerfile for Shipping News Intelligence

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.6.1

# Copy dependency files
WORKDIR /app
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root \
    && rm -rf $POETRY_CACHE_DIR

# Stage 2: Runtime image
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user
RUN groupadd -r maritime && useradd -r -g maritime maritime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=maritime:maritime . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R maritime:maritime /app/logs /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from config.settings import get_settings; asyncio.run(get_settings().postgres_url and print('healthy') or exit(1))"

# Switch to non-root user
USER maritime

# Expose port (if running web server)
EXPOSE 8000

# Default command
CMD ["python", "main.py"]

# Labels for metadata
LABEL maintainer="Maritime Intelligence Engine" \
      version="1.0.0" \
      description="Multi-agent maritime news intelligence system" \
      org.opencontainers.image.title="Maritime Intelligence Engine" \
      org.opencontainers.image.description="Production-ready multi-agent system for maritime shipping news analysis" \
      org.opencontainers.image.vendor="Maritime Intelligence Engine" \
      org.opencontainers.image.version="1.0.0"