import logging

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import api_error, api_response, parse_json_body
from apps.core.utils.logging import log_security_event
from ..services.permission_service import get_effective_permissions


def _user_profile_dict(user):
    profile = getattr(user, "profile", None)
    return {
        "id": user.id,
        "name": user.get_full_name() or user.username,
        "username": user.username,
        "email": user.email,
        "phone": getattr(user, "phone", ""),
        "job_title": getattr(user, "job_title", ""),
        "department": getattr(user, "department", ""),
        "employee_number": getattr(user, "employee_number", ""),
        "role": "admin" if user.is_superuser else "user",
        "is_superuser": user.is_superuser,
        "permissions": get_effective_permissions(user),
        "system_role_name": (
            profile.system_role.name
            if profile and profile.system_role
            else ("مدير النظام" if user.is_superuser else "مستخدم")
        ),
        "group_name": profile.group.name if profile and profile.group else None,
        "group_id": profile.group_id if profile else None,
        "system_role_id": profile.system_role_id if profile else None,
    }


@csrf_exempt
@ensure_csrf_cookie
def auth_login(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return api_error("اسم المستخدم وكلمة المرور مطلوبان", status=400)
        # Validate password length to prevent DoS
        if len(password) > 128:
            return api_error("كلمة المرور طويلة جداً", status=400)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                log_security_event(
                    "login_disabled_account",
                    user=user,
                    request=request,
                    extra={"message": "حساب غير نشط"},
                )
                return api_error("الحساب غير نشط", status=403)
            login(request, user)
            log_audit(
                request,
                action="login",
                module="accounts",
                object_id=str(user.id),
                object_repr=user.username,
            )
            log_security_event(
                "login_success",
                user=user,
                request=request,
                level=logging.INFO,
            )
            profile = _user_profile_dict(user)
            return api_response(
                {"user": profile},
                message="تم تسجيل الدخول بنجاح",
            )
        log_security_event(
            "login_failed",
            request=request,
            extra={"username": username},
        )
        return api_error("بيانات تسجيل الدخول غير صحيحة", status=401)
    return api_error("Method not allowed", status=405)


def auth_logout(request):
    if request.method not in ("POST", "DELETE"):
        return api_error("Method not allowed", status=405)

    refresh = ""
    if request.body:
        data, err = parse_json_body(request)
        if not err and isinstance(data, dict):
            refresh = (data.get("refresh") or "").strip()

    if refresh:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken

            RefreshToken(refresh).blacklist()
        except Exception:
            pass

    if request.user.is_authenticated:
        log_audit(
            request,
            action="logout",
            module="accounts",
            object_id=str(request.user.id),
            object_repr=request.user.username,
        )
        log_security_event(
            "logout",
            user=request.user,
            request=request,
            level=logging.INFO,
        )
        logout(request)
    return api_response(message="تم تسجيل الخروج بنجاح")


def auth_status(request):
    if request.user.is_authenticated:
        profile = _user_profile_dict(request.user)
        return api_response({"logged_in": True, "user": profile})
    return api_response({"logged_in": False, "user": None})


@api_login_required
def auth_me(request):
    return api_response(
        {"user": _user_profile_dict(request.user), "logged_in": True}
    )
