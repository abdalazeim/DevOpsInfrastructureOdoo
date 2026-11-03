# وحدة عينة — النقل (اختيارية)

هذه الوحدة **ليست جزءًا من القالب الأساسي**. تمثل مجال نظام نقل بضائع كمثال متقدم.

لا تُحمَّل افتراضيًا. لتفعيلها في مشروع تجريبي للمجال الأصلي فقط:

```env
ENABLE_DOMAIN_SAMPLES=True
```

ثم:

```bash
python manage.py migrate transport
```

للمشاريع الجديدة: اتركها معطّلة وأنشئ وحدتك عبر:

```bash
python manage.py startmodule your_domain --label "مجالك"
```
