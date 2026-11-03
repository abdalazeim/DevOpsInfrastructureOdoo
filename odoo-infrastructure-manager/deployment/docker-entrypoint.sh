#!/bin/sh
# ==============================================================================
# Docker entrypoint — apply migrations (unless skipped) then run the server.
# ==============================================================================
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting web server..."
exec "$@"
