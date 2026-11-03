from django.http import JsonResponse

from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body
from ...models import User, UserProfile
from ...services.permission_service import get_effective_permissions


@api_login_required
@api_permission_required("users_manage")
def list_users(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err

        username = (data.get("username") or "").strip()
        full_name = (data.get("full_name") or "").strip()
        password = data.get("password", "")
        phone = (data.get("phone") or "").strip()
        job_title = (data.get("job_title") or "").strip()
        department = (data.get("department") or "").strip()
        employee_number = (data.get("employee_number") or "").strip()
        group_id = data.get("group_id")
        system_role_id = data.get("system_role_id")
        permissions = data.get("permissions")
        email = (data.get("email") or "").strip()

        if not username:
            return JsonResponse(
                {"success": False, "error": "اسم المستخدم مطلوب"}, status=400
            )
        if User.objects.filter(username=username).exists():
            return JsonResponse(
                {"success": False, "error": "اسم المستخدم موجود مسبقاً"}, status=400
            )
        if password and len(password) < 8:
            return JsonResponse(
                {
                    "success": False,
                    "error": "كلمة المرور قصيرة جداً (8 أحرف على الأقل)",
                },
                status=400,
            )

        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            job_title=job_title,
            department=department,
            employee_number=employee_number,
            is_active_user=True,
        )
        if password:
            user.set_password(password)
            user.save()

        UserProfile.objects.create(
            user=user,
            group_id=group_id if group_id else None,
            system_role_id=system_role_id if system_role_id else None,
            permissions=permissions if permissions else [],
        )

        log_audit(
            request,
            action="create",
            module="accounts",
            object_id=user.id,
            object_repr=user.username,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم إضافة المستخدم بنجاح",
                "user": _user_to_dict(user),
            },
            status=201,
        )

    users = User.objects.select_related("profile__group", "profile__system_role").all()
    data = [_user_to_dict(u) for u in users]
    return JsonResponse(data, safe=False)


def _user_to_dict(user):
    profile = getattr(user, "profile", None)
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.get_full_name(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": getattr(user, "phone", ""),
        "job_title": getattr(user, "job_title", ""),
        "department": getattr(user, "department", ""),
        "employee_number": getattr(user, "employee_number", ""),
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "date_joined": user.date_joined.isoformat() if user.date_joined else "",
        "group_id": profile.group_id if profile else None,
        "group_name": profile.group.name if profile and profile.group else None,
        "system_role_id": profile.system_role_id if profile else None,
        "system_role_name": (
            profile.system_role.name if profile and profile.system_role else None
        ),
        "permissions": get_effective_permissions(user),
    }


@api_login_required
@api_permission_required("users_manage")
def edit_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "المستخدم غير موجود"}, status=404
        )

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method in ("PUT", "PATCH"):
        data, err = parse_json_body(request)
        if err:
            return err

        if "full_name" in data:
            name_parts = data["full_name"].strip().split(" ", 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        if "email" in data:
            user.email = data["email"]
        if "phone" in data:
            user.phone = data["phone"]
        if "job_title" in data:
            user.job_title = data["job_title"]
        if "department" in data:
            user.department = data["department"]
        if "employee_number" in data:
            user.employee_number = data["employee_number"]
        if "is_active" in data:
            user.is_active = bool(data["is_active"])
        if "username" in data:
            new_username = data["username"].strip()
            if new_username and new_username != user.username:
                if (
                    User.objects.filter(username=new_username)
                    .exclude(id=user.id)
                    .exists()
                ):
                    return JsonResponse(
                        {"success": False, "error": "اسم المستخدم موجود مسبقاً"},
                        status=400,
                    )
                user.username = new_username
        if "password" in data and data["password"]:
            user.set_password(data["password"])

        user.save()

        if "group_id" in data:
            profile.group_id = data["group_id"] if data["group_id"] else None
        if "system_role_id" in data:
            profile.system_role_id = (
                data["system_role_id"] if data["system_role_id"] else None
            )
        if "permissions" in data:
            profile.permissions = data["permissions"]
        profile.save()

        log_audit(
            request,
            action="update",
            module="accounts",
            object_id=user.id,
            object_repr=user.username,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم تحديث المستخدم بنجاح",
                "user": _user_to_dict(user),
            }
        )

    elif request.method == "DELETE":
        if user.is_superuser:
            last_super_count = (
                User.objects.filter(is_superuser=True, is_active=True)
                .exclude(id=user.id)
                .count()
            )
            if last_super_count == 0:
                return JsonResponse(
                    {"success": False, "error": "لا يمكن حذف آخر مسؤول في النظام"},
                    status=400,
                )
        user.delete()
        log_audit(
            request,
            action="delete",
            module="accounts",
            object_id=user.id,
            object_repr=user.username,
        )
        return JsonResponse({"success": True, "message": "تم حذف المستخدم بنجاح"})

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
