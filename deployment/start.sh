#!/bin/bash

# Production startup script for Linux/Unix
export ENVIRONMENT=production

echo "Starting Budget Management System in production mode..."

# Load production environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

# Start with Gunicorn
exec gunicorn src.main:app -c deployment/gunicorn.conf.py --log-config deployment/logging.conf
