import logging
from functools import wraps

from django.http import JsonResponse

from apps.accounts.services.permission_service import has_permission
from apps.core.utils.http import api_error
from apps.core.utils.logging import log_security_event


def api_login_required(view_func):
    """Require authentication for API views, return 401 JSON instead of redirect."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            log_security_event(
                "anonymous_access_denied",
                request=request,
                level=logging.INFO,
            )
            return api_error("يجب تسجيل الدخول أولاً", status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def api_permission_required(*perm_codes):
    """Require specific permission codes for API views."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_permission(request.user, *perm_codes):
                return view_func(request, *args, **kwargs)
            log_security_event(
                "permission_denied",
                user=request.user,
                request=request,
                extra={"required": ",".join(perm_codes)},
            )
            return api_error("ليس لديك صلاحية للوصول", status=403)

        return wrapper

    return decorator
