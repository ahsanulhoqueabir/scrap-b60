#!/bin/bash
# Wrapper script to run scrapers with proper environment

# Load environment variables
source /etc/environment 2>/dev/null || true

# Set Python path
export PYTHONPATH=/app

# Run the scraper passed as argument
python "$@"
