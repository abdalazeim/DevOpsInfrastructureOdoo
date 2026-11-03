"""Sync endpoints for offline-first mobile (Android) clients.

Provides push/pull synchronization for Flutter/Android apps with offline-first
support. Follows the idempotent mutation pattern with client-generated UUIDs.
"""

import logging

from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.core.utils.decorators import api_login_required
from apps.core.services.sync_service import execute_once, pull_changes
from apps.core.utils.exceptions import AppError, exception_to_response
from apps.core.utils.http import api_error, api_response, parse_json_body

logger = logging.getLogger("apps.api")


@api_login_required
def sync_push(request):
    """Push batch mutations from client to server.

    Expected body:
        {
            "operations": [
                {
                    "operation_id": "<uuid>",
                    "kind": "<mutation.kind>",
                    "payload": { ... }
                }
            ]
        }

    Returns per-operation results: applied / rejected / conflict.
    Idempotent: duplicate operation_id returns recorded result.
    """
    if request.method != "POST":
        return api_error("Method not allowed", status=405)

    data, err = parse_json_body(request)
    if err:
        return err
    if not isinstance(data, dict):
        return api_error("Request body must be a JSON object", status=400)

    operations = data.get("operations", [])
    if not isinstance(operations, list):
        return api_error("operations must be a list", status=400)

    if len(operations) > 100:
        return api_error("A sync batch cannot exceed 100 operations", status=400)

    results = [
        execute_once(request.user, op)
        if isinstance(op, dict)
        else {
            "operation_id": None,
            "status": "rejected",
            "error": "Each operation must be an object",
            "code": "invalid_operation",
            "replayed": False,
        }
        for op in operations
    ]

    logger.info("Sync push: %d operations from user %s", len(operations), request.user.id)

    return api_response({
        "results": results,
        "processed": len(results),
    }, message="تم معالجة العمليات")


@api_login_required
def sync_pull(request):
    """Pull changes from server since a cursor timestamp.

    Query params:
        since=<ISO timestamp> - return records updated after this timestamp
        models=<comma-separated> - optional model filter

    Returns:
        {
            "rows": { "<model>": [ ...records... ] },
            "tombstones": [ { "model": "...", "id": "...", "deleted_at": "..." } ],
            "cursor": "<latest updated_at>"
        }
    """
    if request.method != "GET":
        return api_error("Method not allowed", status=405)

    since = request.GET.get("since")
    models_param = request.GET.get("models", "")

    # A cursor is server-issued; parse and normalize it before querying models.
    since_dt = None
    if since:
        since_dt = parse_datetime(since)
        if since_dt is None:
            return api_error("Invalid 'since' timestamp format", status=400)
        if timezone.is_naive(since_dt):
            since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())

    model_list = [m.strip() for m in models_param.split(",") if m.strip()] if models_param else []
    cursor = timezone.now()
    try:
        result = pull_changes(
            request.user,
            since=since_dt,
            cursor=cursor,
            requested_models=model_list,
        )
        return api_response(result, message="تم سحب التحديثات")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
def sync_endpoint(request):
    """Single sync URL: POST pushes operations; GET pulls server changes."""
    if request.method == "POST":
        return sync_push(request)
    if request.method == "GET":
        return sync_pull(request)
    return api_error("Method not allowed", status=405)
