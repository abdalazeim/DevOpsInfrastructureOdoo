from django.http import JsonResponse

from apps.core.services.audit_service import log_audit
from apps.core.services.system_settings import _invalidate
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body
from ...models.settings import SystemSetting


@api_login_required
@api_permission_required("settings_manage")
def list_system_settings(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err

        key = (data.get("key") or "").strip()
        value = (data.get("value") or "").strip()
        description = (data.get("description") or "").strip()
        category = (data.get("category") or "general").strip()
        is_active = data.get("is_active", True)

        if not key:
            return JsonResponse(
                {"success": False, "error": "المفتاح مطلوب"}, status=400
            )

        setting, created = SystemSetting.objects.update_or_create(
            key=key,
            defaults={
                "value": value,
                "description": description,
                "category": category,
                "is_active": bool(is_active),
            },
        )
        _invalidate()

        log_audit(
            request,
            action="create" if created else "update",
            module="settings",
            object_id=str(setting.id),
            object_repr=setting.key,
            new_value={"key": key, "value": value, "category": category},
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم حفظ الإعداد بنجاح",
                "created": created,
                "setting": {
                    "id": setting.id,
                    "key": setting.key,
                    "value": setting.value,
                    "description": setting.description,
                    "category": setting.category,
                    "category_label": setting.get_category_display(),
                    "is_active": setting.is_active,
                    "created_at": setting.created_at.isoformat(),
                    "updated_at": setting.updated_at.isoformat(),
                },
            },
            status=201 if created else 200,
        )

    category_filter = request.GET.get("category", "")
    settings_qs = SystemSetting.objects.all()
    if category_filter:
        settings_qs = settings_qs.filter(category=category_filter)
    data = []
    for s in settings_qs:
        data.append(
            {
                "id": s.id,
                "key": s.key,
                "value": s.value,
                "description": s.description,
                "category": s.category,
                "category_label": s.get_category_display(),
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
        )
    return JsonResponse({"settings": data})


@api_login_required
@api_permission_required("settings_manage")
def list_all_settings(request):
    """Return every setting grouped by category (read-only, GET)."""
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    settings_qs = SystemSetting.objects.all().order_by("category", "key")
    data = []
    for s in settings_qs:
        data.append(
            {
                "id": s.id,
                "key": s.key,
                "value": s.value,
                "description": s.description,
                "category": s.category,
                "category_label": s.get_category_display(),
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
        )
    return JsonResponse({"settings": data})


@api_login_required
@api_permission_required("settings_manage")
def update_system_setting(request, setting_id):
    try:
        setting = SystemSetting.objects.get(id=setting_id)
    except SystemSetting.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "الإعداد غير موجود"}, status=404
        )

    if request.method in ("PUT", "PATCH"):
        data, err = parse_json_body(request)
        if err:
            return err

        if "value" in data:
            setting.value = str(data["value"])
        if "description" in data:
            setting.description = str(data["description"])
        if "category" in data:
            setting.category = data["category"]
        if "is_active" in data:
            setting.is_active = bool(data["is_active"])

        setting.save()
        _invalidate()

        log_audit(
            request,
            action="update",
            module="settings",
            object_id=str(setting.id),
            object_repr=setting.key,
            new_value={"key": setting.key, "value": setting.value},
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم تحديث الإعداد بنجاح",
                "setting": {
                    "id": setting.id,
                    "key": setting.key,
                    "value": setting.value,
                    "description": setting.description,
                    "category": setting.category,
                    "category_label": setting.get_category_display(),
                    "is_active": setting.is_active,
                    "created_at": setting.created_at.isoformat(),
                    "updated_at": setting.updated_at.isoformat(),
                },
            }
        )

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@api_login_required
@api_permission_required("settings_manage")
def bulk_save_settings(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data, err = parse_json_body(request)
    if err:
        return err

    settings_list = data.get("settings", [])
    category = data.get("category", "general")
    saved = []

    for item in settings_list:
        key = (item.get("key") or "").strip()
        value = str(item.get("value", "")).strip()
        description = (item.get("description") or "").strip()
        if not key:
            continue
        setting, created = SystemSetting.objects.update_or_create(
            key=key,
            defaults={
                "value": value,
                "description": description or key,
                "category": category,
                "is_active": True,
            },
        )
        saved.append(key)

    _invalidate()

    log_audit(
        request,
        action="update",
        module="settings",
        object_repr="حفظ الإعدادات الجماعي",
        new_value={"keys": saved, "category": category},
    )

    return JsonResponse(
        {
            "success": True,
            "message": f"تم حفظ {len(saved)} إعداد بنجاح",
            "saved": saved,
        }
    )
