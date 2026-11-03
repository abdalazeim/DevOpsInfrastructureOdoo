"""HTTP helpers shared by all API views."""
import json

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse


def parse_json_body(request):
    """Parse a JSON request body into a dict.

    Returns ``(data, error_response)``. On success ``error_response`` is
    ``None``; on malformed input ``data`` is ``None`` and ``error_response``
    is a ready-to-return 400 ``JsonResponse``.
    """
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, api_error("بيانات غير صالحة", status=400)


def error_response(message, status=400):
    """Shortcut for a consistent failure JSON response."""
    return api_error(message, status=status)


def api_response(data=None, message="", success=True, status=200, errors=None):
    """Standardized API response envelope.

    The canonical format used across the whole template::

        {"success": true, "message": "...", "data": {...}, "errors": null}
    """
    payload = {
        "success": success,
        "message": message,
        "data": data,
        "errors": errors,
    }
    return JsonResponse(payload, status=status)


def api_error(message, status=400, errors=None):
    """Shortcut for a standardized failure envelope."""
    payload = {
        "success": False,
        "message": message,
        "error": message,
        "data": None,
        "errors": errors,
    }
    return JsonResponse(payload, status=status)


def drf_exception_handler(exc, context):
    """DRF exception handler that keeps the unified API envelope.

    Maps DRF ``APIException`` subclasses (validation, authentication,
    permissions, not-found, ...) onto::

        {"success": false, "message": "...", "error": "...", "data": null, "errors": ...}

    Returns ``None`` for non-DRF exceptions so Django's default handling kicks in.
    """
    from rest_framework.exceptions import APIException
    from rest_framework.response import Response

    if not isinstance(exc, APIException):
        return None

    if isinstance(exc.detail, (dict, list)):
        message = exc.default_detail
        errors = exc.detail
    else:
        message = str(exc.detail)
        errors = None

    payload = {
        "success": False,
        "message": message,
        "error": message,
        "data": None,
        "errors": errors,
    }
    return Response(payload, status=exc.status_code)


def paginate_queryset(queryset, request, page_size=20, max_page_size=100):
    """Paginate a queryset using ``page`` / ``page_size`` query params.

    Returns ``(page_obj, page_meta)`` where ``page_meta`` contains
    pagination information that can be merged into the response envelope.
    """
    raw_size = request.GET.get("page_size", str(page_size))
    try:
        size = min(int(raw_size), max_page_size)
    except (TypeError, ValueError):
        size = page_size
    if size < 1:
        size = page_size

    paginator = Paginator(queryset, size)

    raw_page = request.GET.get("page", "1")
    try:
        page_obj = paginator.page(raw_page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    meta = {
        "page": page_obj.number,
        "page_size": size,
        "total": paginator.count,
        "pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }
    return page_obj, meta


def api_response_paginated(data=None, meta=None, message="", success=True, status=200, errors=None):
    """Paginated response with the standard envelope: ``data.items`` + ``data.meta``."""
    payload = {
        "items": data,
        "meta": meta or {},
    }
    return api_response(payload, message=message, success=success, status=status, errors=errors)
