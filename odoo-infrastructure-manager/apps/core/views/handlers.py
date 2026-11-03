import logging

from django.http import JsonResponse

logger = logging.getLogger("apps.api")


def handler404(request, exception=None):
    return JsonResponse(
        {
            "success": False,
            "message": "الصفحة غير موجودة",
            "error": "الصفحة غير موجودة",
            "data": None,
        },
        status=404,
    )


def handler403(request, exception=None):
    from apps.core.utils.logging import log_security_event

    log_security_event(
        "csrf_or_forbidden",
        user=request.user,
        request=request,
    )
    return JsonResponse(
        {
            "success": False,
            "message": "غير مصرح بالوصول",
            "error": "غير مصرح بالوصول",
            "data": None,
        },
        status=403,
    )


def handler500(request):
    logger.error("Unhandled server error on %s", request.path)
    return JsonResponse(
        {
            "success": False,
            "message": "حدث خطأ غير متوقع",
            "error": "حدث خطأ غير متوقع",
            "data": None,
        },
        status=500,
    )
