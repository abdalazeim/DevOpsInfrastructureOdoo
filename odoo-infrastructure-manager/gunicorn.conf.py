"""
Gunicorn Configuration — Django Enterprise Starter Template
========================================================
Used by Render via Procfile: web: gunicorn config.wsgi:application --config gunicorn.conf.py
"""

import multiprocessing
import os

# ─── Server Socket ────────────────────────────────────────────────
# Render injects the $PORT env var (e.g. 10000). Bind to it so the
# platform's health checks and router can reach the app.
bind = os.environ.get("GUNICORN_BIND", f"0.0.0.0:{os.environ.get('PORT', '8000')}")
backlog = 2048

# ─── Worker Processes ─────────────────────────────────────────────
workers = os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

# ─── Logging ──────────────────────────────────────────────────────
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
access_log_format = (
    '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)

# ─── Process Name ─────────────────────────────────────────────────
proc_name = os.environ.get("GUNICORN_PROC_NAME", "django-template")

# ─── Security ─────────────────────────────────────────────────────
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
