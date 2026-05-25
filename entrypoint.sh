#!/bin/sh
set -e
uv run python manage.py migrate --noinput
uv run python manage.py seed_categories
exec uv run gunicorn config.wsgi:application --bind 0.0.0.0:8002 --workers 2
