#!/bin/bash
set -e

echo "Starting News Scraper Container..."
echo "Timezone: $TZ"
echo "Current time: $(date)"

# Create lock directory
mkdir -p /tmp

# Load crontab
echo "Loading crontab..."
crontab /app/crontab

# Start cron in foreground
echo "Starting cron service..."
cron -f
