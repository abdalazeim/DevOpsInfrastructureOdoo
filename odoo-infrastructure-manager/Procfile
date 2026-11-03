# ==============================================================================
# Render Procfile — Django Enterprise Starter Template
# ==============================================================================
# web:      Production web server (Gunicorn) — see gunicorn.conf.py
# release:  Runs BEFORE each deploy — applies migrations automatically.
#           If this fails, Render rolls back the deploy (zero downtime).

web: gunicorn config.wsgi:application --config gunicorn.conf.py
release: python manage.py migrate --noinput --settings=config.settings.production
