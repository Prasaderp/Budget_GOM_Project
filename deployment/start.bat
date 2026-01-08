@echo off
REM Production startup script for Windows

echo Starting Budget Management System in production mode...

REM Set production environment
set ENVIRONMENT=production

REM Start with Gunicorn
gunicorn src.main:app -c deployment/gunicorn.conf.py --log-config deployment/logging.conf
