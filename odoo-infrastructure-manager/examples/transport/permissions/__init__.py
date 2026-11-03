"""Transport module permission catalog.

Registered into the central permission registry via ``apps.ready()``.
"""

PERMISSIONS = [
    {"code": "transport_view", "label": "عرض وحدة النقل", "group": "transport"},
    {
        "code": "transport_manage",
        "label": "إدارة وحدة النقل (إضافة/تعديل/حذف)",
        "group": "transport",
    },
    {"code": "nav_transport", "label": "قائمة النقل", "group": "nav"},
]

GROUPS = [
    {"key": "transport", "label": "النقل", "icon": "fa-truck"},
]
