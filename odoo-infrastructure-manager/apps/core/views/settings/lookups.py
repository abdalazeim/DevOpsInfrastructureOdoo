from django.http import JsonResponse

from apps.accounts.services.permission_service import has_permission
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body
from ...models.settings import LookupCategory


@api_login_required
def list_lookups(request):
    if request.method == "POST":
        if not has_permission(request.user, "settings_manage"):
            return JsonResponse(
                {"success": False, "error": "ليس لديك صلاحية للوصول"}, status=403
            )
        data, err = parse_json_body(request)
        if err:
            return err

        category = (data.get("category") or "").strip()
        name = (data.get("name") or "").strip()
        name_en = (data.get("name_en") or "").strip()
        sort_order = data.get("sort_order", 0)
        is_active = data.get("is_active", True)

        if not category:
            return JsonResponse(
                {"success": False, "error": "التصنيف مطلوب"}, status=400
            )
        if not name:
            return JsonResponse({"success": False, "error": "الاسم مطلوب"}, status=400)

        lookup = LookupCategory.objects.create(
            category=category,
            name=name,
            name_en=name_en,
            sort_order=int(sort_order) if sort_order else 0,
            is_active=bool(is_active),
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم إضافة القيمة بنجاح",
                "lookup": {
                    "id": lookup.id,
                    "category": lookup.category,
                    "name": lookup.name,
                    "name_en": lookup.name_en,
                    "sort_order": lookup.sort_order,
                    "is_active": lookup.is_active,
                    "extra_data": lookup.extra_data,
                    "created_at": lookup.created_at.isoformat(),
                },
            },
            status=201,
        )

    lookups = LookupCategory.objects.filter(is_active=True)
    category_filter = request.GET.get("category", "")
    if category_filter:
        lookups = lookups.filter(category=category_filter)
    data = []
    for cat in lookups:
        data.append(
            {
                "id": cat.id,
                "category": cat.category,
                "name": cat.name,
                "name_en": cat.name_en,
                "sort_order": cat.sort_order,
                "is_active": cat.is_active,
                "extra_data": cat.extra_data,
                "created_at": cat.created_at.isoformat(),
            }
        )
    return JsonResponse({"lookups": data})


@api_login_required
@api_permission_required("settings_manage")
def update_lookup(request, lookup_id):
    try:
        lookup = LookupCategory.objects.get(id=lookup_id)
    except LookupCategory.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "القيمة غير موجودة"}, status=404
        )

    if request.method == "GET":
        return JsonResponse(
            {
                "id": lookup.id,
                "category": lookup.category,
                "name": lookup.name,
                "name_en": lookup.name_en,
                "sort_order": lookup.sort_order,
                "is_active": lookup.is_active,
                "extra_data": lookup.extra_data,
            }
        )

    if request.method in ("PUT", "PATCH"):
        data, err = parse_json_body(request)
        if err:
            return err

        if "category" in data:
            lookup.category = data["category"]
        if "name" in data:
            lookup.name = data["name"].strip()
        if "name_en" in data:
            lookup.name_en = data["name_en"].strip()
        if "sort_order" in data:
            try:
                lookup.sort_order = int(data["sort_order"])
            except (TypeError, ValueError):
                pass
        if "is_active" in data:
            lookup.is_active = bool(data["is_active"])
        if "extra_data" in data:
            lookup.extra_data = data["extra_data"]

        lookup.save()

        return JsonResponse(
            {
                "success": True,
                "message": "تم تحديث القيمة بنجاح",
                "lookup": {
                    "id": lookup.id,
                    "category": lookup.category,
                    "name": lookup.name,
                    "name_en": lookup.name_en,
                    "sort_order": lookup.sort_order,
                    "is_active": lookup.is_active,
                    "extra_data": lookup.extra_data,
                    "created_at": lookup.created_at.isoformat(),
                },
            }
        )

    elif request.method == "DELETE":
        lookup.delete()
        return JsonResponse({"success": True, "message": "تم حذف القيمة بنجاح"})

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
