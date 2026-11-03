"""Scaffold a new business module and register it automatically.

Usage::

    python manage.py startmodule purchase_orders --label "أوامر الشراء"

The command creates ``apps/modules/<name>/`` following the ``example`` module
layout and wires the module into the running system:

- adds the app to ``INSTALLED_APPS`` (``config/settings/base.py``)
- mounts ``modules/<name>/`` under ``config/api_urls.py``
- registers a sidebar item, a SPA page and a page script
- adds permission codes (``<name>_view`` / ``<name>_manage`` / ``nav_<name>``)
- runs ``makemigrations`` for the new app (unless ``--skip-migrations``)
"""

import os
import re
import subprocess
import sys

from django.core.management.base import BaseCommand, CommandError

# Directory that contains the business modules.
_MODULES_DIR = os.path.join("apps", "modules")

_RESERVED_NAMES = {
    "core",
    "accounts",
    "example",
    "config",
    "static",
    "templates",
    "tests",
}

# Token placeholders replaced in every generated file.
NAME_TOKEN = "@@NAME@@"
CLASS_TOKEN = "@@CLASS@@"
LABEL_TOKEN = "@@LABEL@@"
DB_TABLE_TOKEN = "@@DB_TABLE@@"


class Command(BaseCommand):
    help = "إنشاء وحدة أعمال جديدة وتسجيلها تلقائياً في النظام"

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="اسم الوحدة بصيغة snake_case")
        parser.add_argument(
            "--label",
            default="",
            help="التسمية الظاهرة للوحدة (عربية/إنجليزية). الافتراضي: اسم مقروء من الاسم",
        )
        parser.add_argument(
            "--skip-migrations",
            action="store_true",
            help="عدم تشغيل makemigrations تلقائياً بعد الإنشاء",
        )

    # ─────────────────────────────────────────────────────────────────
    #  Validation / helpers
    # ─────────────────────────────────────────────────────────────────
    def _validate(self, name):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise CommandError(
                "اسم الوحدة يجب أن يكون snake_case صالحاً "
                "(حروف إنجليزية صغيرة وأرقام وشرطة سفلية فقط)."
            )
        if name in _RESERVED_NAMES:
            raise CommandError(f"الاسم '{name}' محجوز. اختر اسماً آخر.")
        module_dir = os.path.join(_MODULES_DIR, name)
        if os.path.exists(module_dir):
            raise CommandError(f"الوحدة '{name}' موجودة بالفعل في {module_dir}.")

    @staticmethod
    def _to_class(name):
        return "".join(part.capitalize() for part in name.split("_"))

    @staticmethod
    def _humanize(name):
        return name.replace("_", " ").title()

    # ─────────────────────────────────────────────────────────────────
    #  File creation
    # ─────────────────────────────────────────────────────────────────
    def _write(self, path, content, *, module_name, label):
        content = (
            content.replace(NAME_TOKEN, module_name)
            .replace(CLASS_TOKEN, self._to_class(module_name))
            .replace(DB_TABLE_TOKEN, module_name + "_items")
            .replace(LABEL_TOKEN, label)
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def _scaffold_module(self, name, label):
        cls = self._to_class(name)
        base = os.path.join(_MODULES_DIR, name)

        files = {
            "__init__.py": f'"""{{label}} module."""\n'.replace("{label}", label),
            "apps.py": APPS_PY,
            "admin.py": ADMIN_PY,
            "urls.py": URLS_PY,
            os.path.join("models", "__init__.py"): MODELS_INIT_PY,
            os.path.join("models", f"{name}_item.py"): MODEL_PY,
            os.path.join("repositories", "__init__.py"): REPO_INIT_PY,
            os.path.join("repositories", f"{name}_repository.py"): REPOSITORY_PY,
            os.path.join("serializers", "__init__.py"): SERIALIZER_INIT_PY,
            os.path.join("serializers", f"{name}_serializer.py"): SERIALIZER_PY,
            os.path.join("services", "__init__.py"): SERVICE_INIT_PY,
            os.path.join("services", f"{name}_service.py"): SERVICE_PY,
            os.path.join("views", "__init__.py"): VIEWS_INIT_PY,
            os.path.join("views", f"{name}_views.py"): VIEWS_PY,
            os.path.join("permissions", "__init__.py"): PERMISSIONS_PY,
            os.path.join("tests", "__init__.py"): "",
            os.path.join("tests", "test_smoke.py"): TESTS_PY,
            os.path.join("migrations", "__init__.py"): "",
        }
        for rel, content in files.items():
            path = os.path.join(base, rel)
            self._write(path, content, module_name=name, label=label)
            display = os.path.join("apps", "modules", name, rel)
            self.stdout.write(f"  created {display}")

        # Page script (under static/js/modules/<name>.js)
        js_path = os.path.join("static", "js", "modules", f"{name}.js")
        self._write(js_path, PAGE_JS, module_name=name, label=label)
        self.stdout.write(f"  created {js_path}")

        return base, cls

    # ─────────────────────────────────────────────────────────────────
    #  Registration (edit existing files)
    # ─────────────────────────────────────────────────────────────────
    def _patch_file(self, path, anchor, addition, *, module_name, count=1):
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        occurrences = content.count(anchor)
        if occurrences < count:
            raise CommandError(
                f"تعذر تسجيل الوحدة: لم يتم العثور على نقطة الإدراج في {path}."
            )
        content = content.replace(anchor, anchor + addition)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def _register(self, name, label):
        cls = self._to_class(name)

        # 1) INSTALLED_APPS
        anchor = '    "apps.modules.example",\n'
        self._patch_file(
            "config/settings/base.py",
            anchor,
            f'    "apps.modules.{name}",\n',
            module_name=name,
        )
        self.stdout.write("  registered in config/settings/base.py (INSTALLED_APPS)")

        # 2) API routes
        anchor = (
            '    path("modules/example/", include("apps.modules.example.urls")),\n'
        )
        self._patch_file(
            "config/api_urls.py",
            anchor,
            f'    path("modules/{name}/", include("apps.modules.{name}.urls")),\n',
            module_name=name,
        )
        self.stdout.write("  registered in config/api_urls.py")

        # 3) Server-rendered sidebar item (apps/core/views/main.py)
        anchor = (
            "                    {\n"
            '                        "label": "التقارير",\n'
            '                        "icon": "fa-chart-pie",\n'
            '                        "id": "nav-reports",\n'
            '                        "onclick": "showPage(\'reports\')",\n'
            "                    },\n"
        )
        addition = (
            "                    {\n"
            f'                        "label": "{label}",\n'
            '                        "icon": "fa-cubes",\n'
            f'                        "id": "nav-{name}",\n'
            f'                        "onclick": "showPage(\'{name}\')",\n'
            "                    },\n"
        )
        self._patch_file(
            "apps/core/views/main.py", anchor, addition, module_name=name
        )
        self.stdout.write("  registered sidebar item in apps/core/views/main.py")

        # 4) SPA registry in static/js/main.js
        anchor = "  { id: 'reports', label: 'التقارير', icon: 'fa-chart-pie', perm: 'nav_reports' },\n"
        addition = f"  {{ id: '{name}', label: '{label}', icon: 'fa-cubes', perm: 'nav_{name}' }},\n"
        self._patch_file("static/js/main.js", anchor, addition, module_name=name)

        anchor = "  reports: 'التقارير',\n"
        addition = f"  {name}: '{label}',\n"
        self._patch_file("static/js/main.js", anchor, addition, module_name=name)

        anchor = (
            "  else if (page === 'reports' && typeof auditReports !== 'undefined') { auditReports.init(); }\n"
        )
        addition = (
            "  else if (typeof window['moduleInit_' + basePage] === 'function') { window['moduleInit_' + basePage](); }\n"
        )
        self._patch_file("static/js/main.js", anchor, addition, module_name=name)
        self.stdout.write("  registered page in static/js/main.js (nav + titles + loader)")

        # 5) SPA page container in templates/pages/index.html
        anchor = "  <!-- ===== REPORTS PAGE ===== -->\n"
        addition = self._page_html(name, label, cls)
        self._patch_file(
            "templates/pages/index.html", anchor, addition, module_name=name
        )

        anchor = "<script src=\"{% static 'js/audit-reports.js' %}?v=1\"></script>\n"
        addition = (
            "<script src=\"{% static 'js/modules/"
            + name
            + ".js' %}?v=1\"></script>\n"
        )
        self._patch_file("templates/pages/index.html", anchor, addition, module_name=name)
        self.stdout.write("  registered page container in templates/pages/index.html")

        return cls

    @staticmethod
    def _page_html(name, label, cls):
        return (
            "  <!-- ===== {label} MODULE PAGE ===== -->\n"
            f'  <div class="page-content" id="page-{name}">\n'
            '    <div class="section-header">\n'
            "      <div>\n"
            f'        <div class="section-title">{label}</div>\n'
            f'        <div class="section-subtitle">إدارة سجلات {label}</div>\n'
            "      </div>\n"
            '      <div class="btn-toolbar-wrap">\n'
            f'        <button class="btn btn-accent btn-sm" onclick="open{cls}Modal()"><i class="fas fa-plus me-1"></i> إضافة</button>\n'
            "      </div>\n"
            "    </div>\n"
            '    <div class="data-card">\n'
            '      <div style="overflow-x:auto;">\n'
            f'        <table class="table table-sm" id="{name}-table" style="font-size:13px;margin:0;">\n'
            '          <thead style="background:#f1f5f9;"><tr>\n'
            "            <th>الكود</th><th>الاسم</th><th>الوصف</th><th>الكمية</th><th>الحالة</th><th>إجراءات</th>\n"
            "          </tr></thead>\n"
            f'          <tbody id="{name}-tbody"></tbody>\n'
            "        </table>\n"
            "      </div>\n"
            "    </div>\n"
            "\n"
            f"    <!-- {label} Add Modal -->\n"
            f'    <div class="modal fade" id="{name}Modal" tabindex="-1" aria-hidden="true">\n'
            '      <div class="modal-dialog modal-dialog-centered">\n'
            "        <div class=\"modal-content\">\n"
            "          <div class=\"modal-header\">\n"
            f'            <h5 class="modal-title">إضافة {label}</h5>\n'
            '            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="إغلاق"></button>\n'
            "          </div>\n"
            '          <div class="modal-body">\n'
            f'            <form id="{name}Form">\n'
            "              <div class=\"mb-3\">\n"
            '                <label class="form-label">الكود <span class="required">*</span></label>\n'
            f'                <input type="text" class="form-control" id="{name}-code" required>\n'
            "              </div>\n"
            "              <div class=\"mb-3\">\n"
            '                <label class="form-label">الاسم <span class="required">*</span></label>\n'
            f'                <input type="text" class="form-control" id="{name}-name" required>\n'
            "              </div>\n"
            "              <div class=\"mb-3\">\n"
            '                <label class="form-label">الوصف</label>\n'
            f'                <textarea class="form-control" id="{name}-desc" rows="2"></textarea>\n'
            "              </div>\n"
            "              <div class=\"mb-3\">\n"
            '                <label class="form-label">الكمية</label>\n'
            f'                <input type="number" class="form-control" id="{name}-qty" value="0" min="0">\n'
            "              </div>\n"
            "            </form>\n"
            "          </div>\n"
            "          <div class=\"modal-footer\">\n"
            '            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">إلغاء</button>\n'
            f'            <button type="button" class="btn btn-accent" onclick="save{cls}Item()"><i class="fas fa-save me-1"></i> حفظ</button>\n'
            "          </div>\n"
            "        </div>\n"
            "      </div>\n"
            "    </div>\n"
            "  </div>\n"
        ).format(label=label)

    # ─────────────────────────────────────────────────────────────────
    #  Command entry
    # ─────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        name = options["module_name"].strip().lower()
        self._validate(name)

        label = options.get("label") or self._humanize(name)
        self.stdout.write(f"إنشاء وحدة '{name}' (الاسم الظاهر: {label}) ...")
        self.stdout.write("  scaffolding files ...")
        base, cls = self._scaffold_module(name, label)

        self.stdout.write("  registering module ...")
        self._register(name, label)

        if not options.get("skip_migrations"):
            try:
                self.stdout.write("  generating migrations ...")
                result = subprocess.run(
                    [sys.executable, "manage.py", "makemigrations", name],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    self.stdout.write("  migration generated")
                else:
                    self.stdout.write(self.style.WARNING(result.stderr.strip()))
            except Exception as exc:  # noqa: BLE001 - best-effort
                self.stdout.write(
                    self.style.WARNING(
                        f"  تعذر تشغيل makemigrations تلقائياً: {exc}\n"
                        f"  نفّذ يدوياً: python manage.py makemigrations {name}"
                    )
                )

        self.stdout.write(self.style.SUCCESS("\nتم إنشاء الوحدة وتسجيلها بنجاح:\n"))
        self.stdout.write(f"  - مجلد الوحدة  : {base}")
        self.stdout.write(f"  - الكلاس الرئيسي: {cls}Item")
        self.stdout.write(
            f"  - API           : /api/modules/{name}/items/  (GET/POST)"
        )
        self.stdout.write(
            f"  - الصلاحيات     : {name}_view , {name}_manage , nav_{name}"
        )
        self.stdout.write("\nالخطوات التالية:")
        self.stdout.write(f"  1) python manage.py migrate")
        self.stdout.write(
            f"  2) عيّن صلاحيات {name}_manage للمستخدمين من صفحة إدارة المستخدمين"
        )
        self.stdout.write(
            f"  3) عدّل النماذج في {os.path.join(base, 'models')} لتناسب مجال عملك"
        )
        self.stdout.write(
            f"  4) شغّل الاختبارات: python manage.py test apps/modules/{name} --settings=config.settings.test"
        )


# ======================================================================
#  Generated file templates (placeholders: @@NAME@@, @@CLASS@@, @@LABEL@@)
# ======================================================================

APPS_PY = '''"""App config for @@LABEL@@."""

from django.apps import AppConfig


class @@CLASS@@Config(AppConfig):
    name = "apps.modules.@@NAME@@"
    verbose_name = "@@LABEL@@"

    def ready(self):
        from apps.accounts.permissions.catalog import register_permissions

        from .permissions import GROUPS, PERMISSIONS

        register_permissions(PERMISSIONS, GROUPS)
'''

ADMIN_PY = '''from django.contrib import admin

from .models import @@CLASS@@Item


@admin.register(@@CLASS@@Item)
class @@CLASS@@ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "quantity", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")
'''

URLS_PY = '''from django.urls import path

from . import views

app_name = "@@NAME@@"

urlpatterns = [
    path("stats/", views.module_stats, name="module-stats"),
    path("items/", views.list_items, name="item-list"),
    path("items/create/", views.create_item, name="item-create"),
    path("items/<int:item_id>/", views.get_item, name="item-detail"),
    path("items/<int:item_id>/update/", views.update_item, name="item-update"),
    path("items/<int:item_id>/delete/", views.delete_item, name="item-delete"),
]
'''

MODELS_INIT_PY = '''from .@@NAME@@_item import @@CLASS@@Item

__all__ = ["@@CLASS@@Item"]
'''

MODEL_PY = '''"""@@LABEL@@ — generic entity generated by ``startmodule``."""

from django.db import models

from apps.core.models import BaseModel


class @@CLASS@@Item(BaseModel):
    """A minimal CRUD entity for the @@LABEL@@ module.

    Extend with your own domain fields. ``BaseModel`` already provides
    timestamps, created_by/updated_by and is_active.
    """

    name = models.CharField(max_length=255, verbose_name="الاسم")
    code = models.CharField(
        max_length=100, unique=True, verbose_name="الكود",
        help_text="كود فريد يستخدم كمعرّف مرجعي",
    )
    description = models.TextField(blank=True, default="", verbose_name="الوصف")
    quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية")
    sort_order = models.IntegerField(default=0, verbose_name="ترتيب الفرز")

    class Meta:
        db_table = "@@DB_TABLE@@"
        verbose_name = "@@LABEL@@"
        verbose_name_plural = "@@LABEL@@"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
'''

REPO_INIT_PY = '''from .@@NAME@@_repository import @@CLASS@@ItemRepository

__all__ = ["@@CLASS@@ItemRepository"]
'''

REPOSITORY_PY = '''"""@@LABEL@@ repository (data-access layer)."""

from django.db.models import Q

from apps.core.repositories import BaseRepository

from ..models import @@CLASS@@Item


class @@CLASS@@ItemRepository(BaseRepository):
    model = @@CLASS@@Item

    def search(self, term=""):
        qs = self.get_queryset()
        if term:
            qs = qs.filter(Q(name__icontains=term) | Q(code__icontains=term))
        return qs
'''

SERIALIZER_INIT_PY = '''from .@@NAME@@_serializer import (
    serialize_@@NAME@@_item as serialize_@@NAME@@_item,
    serialize_@@NAME@@_item_list as serialize_@@NAME@@_item_list,
)

__all__ = ["serialize_@@NAME@@_item", "serialize_@@NAME@@_item_list"]
'''

SERIALIZER_PY = '''"""@@LABEL@@ serializers (plain dict serializers)."""


def serialize_@@NAME@@_item(item):
    return {
        "id": item.pk,
        "name": item.name,
        "code": item.code,
        "description": item.description,
        "quantity": item.quantity,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def serialize_@@NAME@@_item_list(items):
    return [serialize_@@NAME@@_item(item) for item in items]
'''

SERVICE_INIT_PY = '''from .@@NAME@@_service import @@CLASS@@ItemService

__all__ = ["@@CLASS@@ItemService"]
'''

SERVICE_PY = '''"""@@LABEL@@ service layer (business logic + audit trail)."""

import logging

from django.db import transaction

from apps.core.services.audit_service import log_audit
from apps.core.utils.exceptions import BusinessRuleError, ConflictError

from ..models import @@CLASS@@Item
from ..repositories import @@CLASS@@ItemRepository

logger = logging.getLogger("apps.api")

repository = @@CLASS@@ItemRepository()


class @@CLASS@@ItemService:
    """Service for :class:`~apps.modules.@@NAME@@.models.@@CLASS@@Item`."""

    def create(self, request=None, *, user=None, data=None):
        name = (data or {}).get("name", "").strip()
        code = (data or {}).get("code", "").strip()
        if not name or not code:
            raise BusinessRuleError("الاسم والكود مطلوبان")

        if repository.exists(code=code):
            raise ConflictError("الكود مستخدم مسبقاً")

        with transaction.atomic():
            item = repository.create(
                name=name,
                code=code,
                description=(data or {}).get("description", ""),
                quantity=int((data or {}).get("quantity", 0) or 0),
                sort_order=int((data or {}).get("sort_order", 0) or 0),
            )
            log_audit(
                request,
                action="create",
                module="@@NAME@@",
                object_id=str(item.pk),
                object_repr=item.name,
                new_value={"code": item.code, "name": item.name},
                user=user,
            )
        logger.info("%s created: %s (%s)", "@@CLASS@@Item", item.name, item.code)
        return item

    def update(self, obj_id, request=None, *, user=None, data=None):
        item = repository.get_by_id(obj_id)
        old_value = {"code": item.code, "name": item.name}

        code = (data or {}).get("code")
        if code and repository.exists(code=code).exclude(pk=item.pk).exists():
            raise ConflictError("الكود مستخدم مسبقاً")

        with transaction.atomic():
            if (data or {}).get("name") is not None:
                item.name = str((data or {}).get("name")).strip()
            if code is not None:
                item.code = str(code).strip()
            item.description = (data or {}).get("description", item.description)
            item.quantity = int((data or {}).get("quantity", item.quantity) or 0)
            item.sort_order = int((data or {}).get("sort_order", item.sort_order) or 0)
            item.save()
            log_audit(
                request,
                action="update",
                module="@@NAME@@",
                object_id=str(item.pk),
                object_repr=item.name,
                old_value=old_value,
                new_value={"code": item.code, "name": item.name},
                user=user,
            )
        return item

    def delete(self, obj_id, request=None, *, user=None):
        item = repository.get_by_id(obj_id)
        with transaction.atomic():
            item.delete()
            log_audit(
                request,
                action="delete",
                module="@@NAME@@",
                object_id=str(obj_id),
                object_repr=item.name,
                user=user,
            )
        return item

    def stats(self):
        qs = repository.get_queryset()
        return {
            "total": qs.count(),
            "active": qs.filter(is_active=True).count(),
        }
'''

VIEWS_INIT_PY = '''from .@@NAME@@_views import (
    create_item as create_item,
    delete_item as delete_item,
    get_item as get_item,
    list_items as list_items,
    module_stats as module_stats,
    update_item as update_item,
)
'''

VIEWS_PY = '''"""@@LABEL@@ module API views (CRUD + stats)."""

from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.exceptions import AppError, exception_to_response
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    parse_json_body,
    paginate_queryset,
)

from ..repositories import @@CLASS@@ItemRepository
from ..serializers import serialize_@@NAME@@_item, serialize_@@NAME@@_item_list
from ..services import @@CLASS@@ItemService

service = @@CLASS@@ItemService()
repository = @@CLASS@@ItemRepository()


@api_login_required
@api_permission_required("@@NAME@@_view")
def list_items(request):
    term = request.GET.get("q", "").strip()
    page_obj, meta = paginate_queryset(repository.search(term), request)
    return api_response_paginated(
        serialize_@@NAME@@_item_list(list(page_obj)), meta, message="تم تحميل القائمة"
    )


@api_login_required
@api_permission_required("@@NAME@@_view")
def module_stats(request):
    return api_response(service.stats(), message="تم تحميل الإحصائيات")


@api_login_required
@api_permission_required("@@NAME@@_manage")
def create_item(request):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        item = service.create(request, data=data)
        return api_response(
            serialize_@@NAME@@_item(item), message="تم الإنشاء بنجاح", status=201
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("@@NAME@@_manage")
def update_item(request, item_id):
    if request.method not in ("PUT", "PATCH"):
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        item = service.update(item_id, request, data=data)
        return api_response(serialize_@@NAME@@_item(item), message="تم التحديث بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("@@NAME@@_manage")
def delete_item(request, item_id):
    if request.method != "DELETE":
        return api_error("Method not allowed", status=405)
    try:
        service.delete(item_id, request)
        return api_response(message="تم الحذف بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("@@NAME@@_view")
def get_item(request, item_id):
    try:
        item = repository.get_by_id(item_id)
        return api_response(serialize_@@NAME@@_item(item))
    except AppError as exc:
        return exception_to_response(exc)
'''

PERMISSIONS_PY = '''"""@@LABEL@@ permission catalog.

Registered into the central permission registry via ``apps.ready()``.
"""

PERMISSIONS = [
    {"code": "@@NAME@@_view", "label": "عرض @@LABEL@@", "group": "@@NAME@@"},
    {
        "code": "@@NAME@@_manage",
        "label": "إدارة @@LABEL@@ (إضافة/تعديل/حذف)",
        "group": "@@NAME@@",
    },
    {"code": "nav_@@NAME@@", "label": "قائمة @@LABEL@@", "group": "nav"},
]

GROUPS = [
    {"key": "@@NAME@@", "label": "@@LABEL@@", "icon": "fa-cubes"},
]
'''

TESTS_PY = '''"""Smoke tests for the @@LABEL@@ module (CRUD + audit trail)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.core.models import AuditLog

from ..models import @@CLASS@@Item

User = get_user_model()


@override_settings(ALLOWED_HOSTS=["*"])
class @@CLASS@@ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")

    def _url(self, path):
        return "/api/modules/@@NAME@@" + path

    def test_list_empty(self):
        resp = self.client.get(self._url("/items/"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["items"], [])

    def test_stats(self):
        resp = self.client.get(self._url("/stats/"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_create_item_logs_audit(self):
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "عنصر", "code": "ABC-1", "quantity": 5},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(@@CLASS@@Item.objects.filter(code="ABC-1").exists())
        self.assertTrue(
            AuditLog.objects.filter(action="create", module="@@NAME@@").exists()
        )

    def test_create_duplicate_code_conflicts(self):
        @@CLASS@@Item.objects.create(name="أ", code="DUP-1")
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "ب", "code": "DUP-1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_update_item(self):
        item = @@CLASS@@Item.objects.create(name="قديم", code="UPD-1")
        resp = self.client.patch(
            self._url(f"/items/{item.pk}/update/"),
            data={"name": "جديد"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.name, "جديد")

    def test_delete_item(self):
        item = @@CLASS@@Item.objects.create(name="حذف", code="DEL-1")
        resp = self.client.delete(self._url(f"/items/{item.pk}/delete/"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(@@CLASS@@Item.objects.filter(pk=item.pk).exists())
'''

PAGE_JS = '''// ============================================================
//  @@LABEL@@ module page (auto-generated by startmodule)
// ============================================================
(function () {
  var MODULE = '@@NAME@@';
  var MOD_API = API_BASE + '/modules/' + MODULE;

  function getEl(id) { return document.getElementById(id); }

  async function loadItems() {
    var tbody = getEl(MODULE + '-tbody');
    if (!tbody) return;
    try {
      var data = await apiFetchJSON(MOD_API + '/items/');
      var items = (data && data.data && data.data.items) || [];
      tbody.innerHTML = items.map(function (it) {
        var status = it.is_active
          ? '<span class="badge bg-success">نشط</span>'
          : '<span class="badge bg-secondary">معطل</span>';
        return '<tr>'
          + '<td>' + escapeHtml(it.code) + '</td>'
          + '<td>' + escapeHtml(it.name) + '</td>'
          + '<td>' + escapeHtml(it.description || '—') + '</td>'
          + '<td>' + it.quantity + '</td>'
          + '<td>' + status + '</td>'
          + '<td><button class="btn btn-sm btn-outline-danger" onclick="delete@@CLASS@@Item(' + it.id + ')"><i class="fas fa-trash"></i></button></td>'
          + '</tr>';
      }).join('');
    } catch (e) {
      showToast('فشل تحميل بيانات الوحدة', 'error');
    }
  }

  window['open@@CLASS@@Modal'] = function () {
    getEl(MODULE + '-code').value = '';
    getEl(MODULE + '-name').value = '';
    getEl(MODULE + '-desc').value = '';
    getEl(MODULE + '-qty').value = '0';
    var modalEl = getEl(MODULE + 'Modal');
    if (modalEl && window.bootstrap && bootstrap.Modal) {
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
  };

  window['save@@CLASS@@Item'] = async function () {
    var code = getEl(MODULE + '-code').value.trim();
    var name = getEl(MODULE + '-name').value.trim();
    if (!code || !name) { showToast('الكود والاسم مطلوبان', 'error'); return; }
    try {
      await apiFetchJSON(MOD_API + '/items/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: code,
          name: name,
          description: getEl(MODULE + '-desc').value,
          quantity: parseInt(getEl(MODULE + '-qty').value || '0', 10)
        })
      });
      var modalEl = getEl(MODULE + 'Modal');
      if (modalEl && window.bootstrap && bootstrap.Modal) {
        bootstrap.Modal.getInstance(modalEl) && bootstrap.Modal.getInstance(modalEl).hide();
      }
      showToast('تم الحفظ بنجاح', 'success');
      loadItems();
    } catch (e) {
      showToast('فشل الحفظ', 'error');
    }
  };

  window['delete@@CLASS@@Item'] = async function (id) {
    if (!confirm('هل أنت متأكد من الحذف؟')) return;
    try {
      await apiFetchJSON(MOD_API + '/items/' + id + '/delete/', { method: 'DELETE' });
      showToast('تم الحذف بنجاح', 'success');
      loadItems();
    } catch (e) { showToast('فشل الحذف', 'error'); }
  };

  window['moduleInit_' + MODULE] = function () { loadItems(); };
})();
'''
