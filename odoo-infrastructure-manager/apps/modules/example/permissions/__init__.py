"""Example module permission catalog (generic/demo).

Registered into the central permission registry via ExampleConfig.ready().
"""

PERMISSIONS = [
    {"code": "example_view", "label": "عرض العناصر", "group": "example"},
    {"code": "example_manage", "label": "إدارة العناصر (إضافة/تعديل/حذف)", "group": "example"},
    {"code": "nav_example", "label": "قائمة المثال", "group": "nav"},
]

GROUPS = [
    {"key": "example", "label": "عناصر المثال", "icon": "fa-cubes"},
]
