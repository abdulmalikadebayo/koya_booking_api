#!/bin/bash
set -e

# migrate
python src/manage.py migrate

# 2 workers x 4 threads: simultaneous bookings are handled in parallel, and the
# database (row and advisory locks) keeps them correct. Each thread keeps one
# connection (CONN_MAX_AGE), so this stays well inside the pooler's limit.
PYTHONPATH=src exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout 60 \
    --access-logfile -
