"""Seed generic baseline data for a fresh Django Enterprise Template database.

This command only touches Core (SystemSettings + LookupCategory) and is
deliberately business-agnostic. Business modules provide their own seed
data inside their own management commands.
"""

import json

from django.core.management.base import BaseCommand
from django.test import RequestFactory

from apps.accounts.models import User
from apps.core.models import LookupCategory
from apps.core.views.settings import seed_default_settings


class Command(BaseCommand):
    help = "زرع البيانات الأساسية العامة (Core): الإعدادات وقيم التصنيفات"

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stderr.write(self.style.ERROR("لا يوجد مستخدم مشرف. قم بإنشائه أولاً."))
            return
        factory = RequestFactory()

        def call(view_func):
            req = factory.post("/api/settings/seed")
            req.user = admin
            resp = view_func(req)
            data = getattr(resp, "content", b"{}")
            try:
                body = json.loads(data)
            except Exception:
                body = {}
            ok = getattr(resp, "status_code", None) in (200, 201) and body.get(
                "success", True
            )
            return ok, body.get("message", "")

        self.stdout.write("-- إعدادات النظام --")
        ok, msg = call(seed_default_settings)
        self.stdout.write(f"  [{'OK' if ok else '!!'}] عام: {msg}")

        self.stdout.write("-- قيم التصنيفات (مثال) --")
        for category, names in [
            ("general", ["قيمة 1", "قيمة 2", "قيمة 3"]),
            ("location", ["الموقع 1", "الموقع 2", "الموقع 3"]),
        ]:
            for sort_order, name in enumerate(names):
                LookupCategory.objects.get_or_create(
                    category=category,
                    name=name,
                    defaults={"sort_order": sort_order, "is_active": True},
                )
            count = LookupCategory.objects.filter(category=category).count()
            self.stdout.write(f"  [OK] {category}: {count}")

        self.stdout.write(self.style.SUCCESS("اكتمل زرع البيانات الأساسية العامة (Core)."))
