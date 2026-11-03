from django.http import JsonResponse

from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body
from ...models import UserGroup


@api_login_required
@api_permission_required("users_manage")
def list_groups(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err

        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse(
                {"success": False, "error": "اسم المجموعة مطلوب"}, status=400
            )
        if UserGroup.objects.filter(name=name).exists():
            return JsonResponse(
                {"success": False, "error": "المجموعة موجودة مسبقاً"}, status=400
            )

        group = UserGroup.objects.create(
            name=name,
            description=(data.get("description") or "").strip(),
        )
        log_audit(
            request,
            action="create",
            module="accounts",
            object_id=group.id,
            object_repr=group.name,
        )
        return JsonResponse(
            {
                "success": True,
                "message": "تم إضافة المجموعة بنجاح",
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "created_at": group.created_at.isoformat(),
                },
            },
            status=201,
        )

    groups = UserGroup.objects.all()
    data = [
        {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "created_at": g.created_at.isoformat(),
        }
        for g in groups
    ]
    return JsonResponse(data, safe=False)


@api_login_required
@api_permission_required("users_manage")
def edit_group(request, group_id):
    try:
        group = UserGroup.objects.get(id=group_id)
    except UserGroup.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "المجموعة غير موجودة"}, status=404
        )

    if request.method in ("PUT", "PATCH"):
        data, err = parse_json_body(request)
        if err:
            return err

        if "name" in data:
            name = data["name"].strip()
            if name and name != group.name:
                if UserGroup.objects.filter(name=name).exclude(id=group_id).exists():
                    return JsonResponse(
                        {"success": False, "error": "المجموعة موجودة مسبقاً"},
                        status=400,
                    )
                group.name = name
        if "description" in data:
            group.description = data["description"].strip()
        group.save()

        log_audit(
            request,
            action="update",
            module="accounts",
            object_id=group.id,
            object_repr=group.name,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم تحديث المجموعة بنجاح",
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "created_at": group.created_at.isoformat(),
                },
            }
        )

    elif request.method == "DELETE":
        log_audit(
            request,
            action="delete",
            module="accounts",
            object_id=group.id,
            object_repr=group.name,
        )
        group.delete()
        return JsonResponse({"success": True, "message": "تم حذف المجموعة بنجاح"})

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
