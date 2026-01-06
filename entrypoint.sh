#!/bin/bash
set -e

echo "Starting News Scraper Container..."
echo "Timezone: $TZ"
echo "Current time: $(date)"

# Create lock directory
mkdir -p /tmp

# Export environment variables to a file for cron
printenv | grep -v "no_proxy" >> /etc/environment

# Load crontab
echo "Loading crontab..."
crontab /app/crontab

# Verify crontab loaded
echo "Verifying crontab..."
crontab -l | head -5

# Start cron in foreground
echo "Starting cron service..."
cron -f
