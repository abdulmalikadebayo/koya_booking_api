#!/bin/bash
set -e

# migrate
python src/manage.py migrate

PYTHONPATH=src gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
