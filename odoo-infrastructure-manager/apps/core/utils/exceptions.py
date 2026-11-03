"""Unified exception hierarchy for the template.

Domain-agnostic exceptions that any module can raise; views/services catch
them and return the standardized API error envelope.
"""


class AppError(Exception):
    """Base class for all application errors."""

    status_code = 400
    default_message = "حدث خطأ"

    def __init__(self, message=None, status_code=None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppError):
    default_message = "بيانات غير صالحة"


class PermissionDenied(AppError):
    status_code = 403
    default_message = "ليس لديك صلاحية للوصول"


class NotFoundError(AppError):
    status_code = 404
    default_message = "العنصر غير موجود"


class ConflictError(AppError):
    status_code = 409
    default_message = "تعارض في البيانات"


class BusinessRuleError(AppError):
    status_code = 422
    default_message = "لا يمكن تنفيذ العملية وفقاً للقواعد"


class SystemError(AppError):
    status_code = 500
    default_message = "خطأ في النظام"


def exception_to_response(exc):
    """Convert an :class:`AppError` into a ready JSON response envelope."""
    from apps.core.utils.http import api_error

    return api_error(exc.message, status=exc.status_code)
