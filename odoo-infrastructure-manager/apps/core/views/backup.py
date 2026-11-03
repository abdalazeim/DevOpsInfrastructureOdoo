from datetime import datetime

from django.http import FileResponse, JsonResponse

from apps.core.services.audit_service import log_audit
from apps.core.services.backup_service import (
    do_backup,
    do_restore,
    format_size,
    get_backup_dir,
    validate_filename,
)
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import parse_json_body


@api_login_required
@api_permission_required("backup_manage")
def create_backup(request):
    if request.method == "POST":
        try:
            backup_dir = get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = backup_dir / f"backup_{timestamp}.dump"
            filename = do_backup(dest)

            log_audit(
                request,
                action="create",
                module="backup",
                object_id=filename,
                object_repr="إنشاء نسخة احتياطية",
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "تم إنشاء النسخة الاحتياطية بنجاح",
                    "filename": filename,
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@api_login_required
@api_permission_required("backup_manage")
def list_backups(request):
    try:
        backup_dir = get_backup_dir()
        if not backup_dir.exists():
            return JsonResponse([], safe=False)

        backups = []
        for f in sorted(
            backup_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            if f.is_file() and f.suffix in (".dump", ".json"):
                stats = f.stat()
                backups.append(
                    {
                        "filename": f.name,
                        "size": stats.st_size,
                        "size_display": format_size(stats.st_size),
                        "created_at": datetime.fromtimestamp(
                            stats.st_mtime
                        ).isoformat(),
                    }
                )
        return JsonResponse(backups, safe=False)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Failed to list backups")
        return JsonResponse(
            {"success": False, "error": "فشل في تحميل قائمة النسخ الاحتياطية"},
            status=500,
        )


@api_login_required
@api_permission_required("backup_manage")
def download_backup(request, filename):
    if not validate_filename(filename):
        return JsonResponse({"success": False, "error": "اسم ملف غير صالح"}, status=400)
    backup_dir = get_backup_dir()
    file_path = backup_dir / filename
    file_path = file_path.resolve()
    if not str(file_path).startswith(str(backup_dir.resolve())):
        return JsonResponse({"success": False, "error": "اسم ملف غير صالح"}, status=400)
    if file_path.exists():
        return FileResponse(
            open(file_path, "rb"), as_attachment=True, filename=filename
        )
    return JsonResponse({"success": False, "error": "الملف غير موجود"}, status=404)


@api_login_required
@api_permission_required("backup_manage")
def restore_backup(request):
    if request.method == "POST":
        data, err = parse_json_body(request)
        if err:
            return err
        try:
            filename = data.get("filename")
            if not validate_filename(filename):
                return JsonResponse(
                    {"success": False, "error": "اسم ملف غير صالح"}, status=400
                )
            backup_dir = get_backup_dir()
            src = backup_dir / filename
            src = src.resolve()
            if not str(src).startswith(str(backup_dir.resolve())):
                return JsonResponse(
                    {"success": False, "error": "اسم ملف غير صالح"}, status=400
                )
            if not src.exists():
                return JsonResponse(
                    {"success": False, "error": "ملف النسخة غير موجود"}, status=404
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore = backup_dir / f"pre_restore_{timestamp}.dump"
            do_backup(pre_restore)
            do_restore(src)

            log_audit(
                request,
                action="update",
                module="backup",
                object_id=filename,
                object_repr="استعادة نسخة احتياطية",
                new_value={"filename": filename},
            )

            return JsonResponse(
                {"success": True, "message": "تم استعادة النسخة الاحتياطية بنجاح"}
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@api_login_required
@api_permission_required("backup_manage")
def delete_backup(request, filename):
    if request.method == "DELETE":
        try:
            if not validate_filename(filename):
                return JsonResponse(
                    {"success": False, "error": "اسم ملف غير صالح"}, status=400
                )
            backup_dir = get_backup_dir()
            file_path = backup_dir / filename
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(backup_dir.resolve())):
                return JsonResponse(
                    {"success": False, "error": "اسم ملف غير صالح"}, status=400
                )
            if file_path.exists():
                file_path.unlink()
                log_audit(
                    request,
                    action="delete",
                    module="backup",
                    object_id=filename,
                    object_repr="حذف نسخة احتياطية",
                )
                return JsonResponse(
                    {"success": True, "message": "تم حذف النسخة الاحتياطية"}
                )
            return JsonResponse(
                {"success": False, "error": "الملف غير موجود"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
