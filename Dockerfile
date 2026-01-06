# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Dhaka

# Install system dependencies including cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    tzdata \
    cron \
    procps \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy crontab, wrapper script and entrypoint
COPY crontab /app/crontab
COPY run_scraper.sh /app/run_scraper.sh
COPY entrypoint.sh /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p logs output /tmp

# Make scripts executable
RUN chmod +x /app/entrypoint.sh && \
    chmod +x /app/run_scraper.sh

# Setup cron permissions
RUN chmod 0644 /app/crontab

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=40s --retries=3 \
    CMD pgrep -x cron > /dev/null || exit 1

# Use ENTRYPOINT instead of CMD to prevent override by Coolify
ENTRYPOINT ["/app/entrypoint.sh"]
