from django.http import JsonResponse

from apps.core.utils.decorators import api_login_required, api_permission_required
from ...models.settings import SystemSetting


@api_login_required
@api_permission_required("settings_manage")
def seed_default_settings(request):
    if SystemSetting.objects.exists():
        return JsonResponse(
            {"success": False, "error": "الإعدادات موجودة مسبقاً"}, status=400
        )

    defaults = [
        ("company_name", "", "اسم الشركة/المؤسسة", "general"),
        ("company_address", "", "عنوان الشركة", "general"),
        ("company_phone", "", "رقم هاتف الشركة", "general"),
        ("company_email", "", "البريد الإلكتروني للشركة", "general"),
        ("ui_font_family", "Cairo", "خط الواجهة (Cairo أو Tajawal)", "general"),
        ("ui_language", "ar", "لغة الواجهة الافتراضية (ar/en)", "general"),
        ("notification_enabled", "true", "تفعيل الإشعارات", "notifications"),
        ("backup_auto", "true", "النسخ الاحتياطي التلقائي", "backup"),
        ("backup_interval_days", "7", "عدد الأيام بين النسخ الاحتياطية", "backup"),
        ("backup_max_files", "10", "الحد الأقصى لعدد ملفات النسخ الاحتياطي", "backup"),
    ]

    created = []
    for key, value, desc, cat in defaults:
        SystemSetting.objects.create(
            key=key, value=value, description=desc, category=cat
        )
        created.append(key)

    return JsonResponse(
        {
            "success": True,
            "message": "تم إنشاء الإعدادات الافتراضية",
            "created": created,
        }
    )
