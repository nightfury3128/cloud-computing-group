#!/usr/bin/env bash
# Azure App Service Linux startup command.
# Set in the App Service general settings as the "Startup Command".
set -euo pipefail
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers=2 \
    --threads=4 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    wsgi:app
