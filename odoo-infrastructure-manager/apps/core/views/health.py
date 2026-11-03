from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Basic application health check — no database required."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "django-enterprise-template",
            "version": "1.0.0",
        }
    )


def health_db(request):
    """Health check that verifies database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = "ok"
        db_error = None
    except Exception as exc:  # pragma: no cover - depends on environment
        db_status = "error"
        db_error = str(exc)

    status = 200 if db_status == "ok" else 503
    return JsonResponse(
        {
            "status": "ok" if db_status == "ok" else "degraded",
            "database": db_status,
            "error": db_error,
        },
        status=status,
    )
