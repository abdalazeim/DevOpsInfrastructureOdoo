from django.shortcuts import render


def login_page(request):
    return render(request, "pages/login.html")


def index(request):
    context = {
        "nav_sections": [
            {
                "title": "القائمة الرئيسية",
                "items": [
                    {
                        "label": "لوحة التحكم",
                        "icon": "fa-th-large",
                        "id": "nav-dashboard",
                        "onclick": "showPage('dashboard')",
                        "active": True,
                    },
                    {
                        "label": "العناصر التجريبية",
                        "icon": "fa-cubes",
                        "id": "nav-example",
                        "onclick": "showPage('example')",
                    },
                    {
                        "label": "التقارير",
                        "icon": "fa-chart-pie",
                        "id": "nav-reports",
                        "onclick": "showPage('reports')",
                    },
                    {
                        "label": "إدارة البنية التحتية لأودو",
                        "icon": "fa-server",
                        "id": "nav-infrastructure",
                        "onclick": "window.location.href='/infrastructure/'",
                    },
                ],
            },
            {
                "title": "إعدادات النظام",
                "items": [
                    {
                        "label": "الإعدادات العامة",
                        "icon": "fa-cog",
                        "id": "nav-settings",
                        "onclick": "showPage('settings')",
                    },
                    {
                        "label": "النسخ الاحتياطية",
                        "icon": "fa-database",
                        "id": "nav-backup",
                        "onclick": "showPage('backup')",
                    },
                    {
                        "label": "إدارة المستخدمين",
                        "icon": "fa-users",
                        "id": "nav-users",
                        "onclick": "showPage('users')",
                    },
                ],
            },
        ],
        "profile_menu": [
            {"label": "الإعدادات", "icon": "fa-cog", "onclick": "showPage('settings')"},
            {"label": "المستخدمين", "icon": "fa-users", "onclick": "showPage('users')"},
        ],
    }
    return render(request, "pages/index.html", context)


def example_page(request):
    """Demonstrates the modular template architecture (layouts/components/partials)."""
    context = {
        "page_title": "صفحة المثال",
        "page_subtitle": "نموذج للهيكلة النمطية للقوالب (Master Template)",
        "breadcrumbs": [
            {"label": "الرئيسية", "url": "/"},
            {"label": "صفحة المثال"},
        ],
        "nav_sections": [
            {
                "title": "القائمة الرئيسية",
                "items": [
                    {
                        "label": "لوحة التحكم",
                        "icon": "fa-th-large",
                        "id": "nav-example-dashboard",
                        "onclick": "alert('لوحة التحكم')",
                        "active": True,
                    },
                    {
                        "label": "الوحدات",
                        "icon": "fa-cubes",
                        "id": "nav-example-modules",
                        "onclick": "alert('الوحدات')",
                    },
                ],
            },
            {
                "title": "الإعدادات",
                "items": [
                    {
                        "label": "الإعدادات العامة",
                        "icon": "fa-cog",
                        "id": "nav-example-settings",
                        "onclick": "alert('الإعدادات')",
                    },
                ],
            },
        ],
        "profile_menu": [
            {"label": "الملف الشخصي", "icon": "fa-user", "onclick": "alert('الملف')"},
        ],
    }
    return render(request, "pages/example_page.html", context)
