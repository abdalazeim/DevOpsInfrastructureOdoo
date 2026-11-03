from django.http import JsonResponse

from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body
from ...models import SystemRole
from ...permissions.catalog import get_all_permissions


@api_login_required
@api_permission_required("users_manage")
def list_roles(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err

        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse(
                {"success": False, "error": "اسم الصلاحية مطلوب"}, status=400
            )

        role = SystemRole.objects.create(
            name=name,
            description=(data.get("description") or "").strip(),
            permissions=data.get("permissions", []),
        )
        log_audit(
            request,
            action="create",
            module="accounts",
            object_id=role.id,
            object_repr=role.name,
        )
        return JsonResponse(
            {
                "success": True,
                "message": "تم إضافة الصلاحية بنجاح",
                "role": {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "permissions": role.permissions,
                    "created_at": role.created_at.isoformat(),
                },
            },
            status=201,
        )

    roles = SystemRole.objects.all()
    data = [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": r.permissions,
            "created_at": r.created_at.isoformat(),
        }
        for r in roles
    ]
    return JsonResponse(data, safe=False)


@api_login_required
@api_permission_required("users_manage")
def edit_role(request, role_id):
    try:
        role = SystemRole.objects.get(id=role_id)
    except SystemRole.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "الصلاحية غير موجودة"}, status=404
        )

    if request.method in ("PUT", "PATCH"):
        data, err = parse_json_body(request)
        if err:
            return err

        if "name" in data:
            role.name = data["name"].strip()
        if "description" in data:
            role.description = data["description"].strip()
        if "permissions" in data:
            role.permissions = data["permissions"]
        role.save()

        log_audit(
            request,
            action="update",
            module="accounts",
            object_id=role.id,
            object_repr=role.name,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم تحديث الصلاحية بنجاح",
                "role": {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "permissions": role.permissions,
                    "created_at": role.created_at.isoformat(),
                },
            }
        )

    elif request.method == "DELETE":
        log_audit(
            request,
            action="delete",
            module="accounts",
            object_id=role.id,
            object_repr=role.name,
        )
        role.delete()
        return JsonResponse({"success": True, "message": "تم حذف الصلاحية بنجاح"})

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@api_login_required
@api_permission_required("users_manage")
def seed_default_roles(request):
    if SystemRole.objects.exists():
        return JsonResponse(
            {"success": False, "error": "الصلاحيات موجودة مسبقاً"}, status=400
        )

    all_codes = [p["code"] for p in get_all_permissions()]
    nav_codes = [p["code"] for p in get_all_permissions() if p["group"] == "nav"]
    manage_codes = [p["code"] for p in get_all_permissions() if p["group"] == "actions"]

    roles_data = [
        {
            "name": "مدير النظام",
            "description": "صلاحية كاملة - جميع أقسام النظام وإدارة المستخدمين والإعدادات",
            "permissions": all_codes,
        },
        {
            "name": "مشرف",
            "description": "إدارة شاملة - القوائم والتقارير والإعدادات",
            "permissions": list(dict.fromkeys([*nav_codes, *manage_codes])),
        },
        {
            "name": "مستخدم",
            "description": "صلاحيات أساسية - عرض المعلومات فقط",
            "permissions": ["nav_dashboard"],
        },
    ]

    created = []
    for r in roles_data:
        SystemRole.objects.create(**r)
        created.append(r["name"])

    return JsonResponse(
        {
            "success": True,
            "message": "تم إنشاء الصلاحيات الافتراضية",
            "created": created,
        }
    )
