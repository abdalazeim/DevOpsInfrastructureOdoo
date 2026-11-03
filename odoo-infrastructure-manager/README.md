# Odoo Infrastructure Manager

منصة Django لإدارة جرد البنية التحتية ومراقبتها وتشغيل مهام Semaphore المعتمدة. تجمع واجهة تشغيل مرئية مع أدوات CLI/TUI القديمة.

## خريطة المشروع

- `config/`: إعدادات Django والمسارات وطبقة الأمان.
- `apps/`: تطبيقات الويب ووحدات المجال: اللوحة، الجرد، المشاريع، قواعد البيانات، الأتمتة، النسخ الاحتياطي والمراقبة.
- `infrastructure_engine/`: نماذج التشغيل والخدمات وسير العمل وواجهات الطرفية لمحرك البنية التحتية.
- `profiles/`, `infra_templates/`, `infra_deployment/`, `automation_files/`: ملفات تعريف البيئات وقوالب وملفات التشغيل الآلي.
- `templates/`, `static/`: واجهة الويب وأصولها.
- `data/`, `logs/`, `media/`, `staticfiles/`: بيانات التشغيل والملفات المولدة محليًا.
- `requirements/`: اعتماديات الأساس والتطوير والإنتاج والاختبار. تبقى `requirements.txt` و`requirements-dev.txt` كمدخلي تثبيت للتوافق.

تظل الاستيرادات القديمة من `app.models` و`app.services` و`app.workflows` صالحة عبر طبقة توافق؛ التنفيذ الأساسي لهذه الحزم موجود في `infrastructure_engine/`.

## المكونات

- Django وDjango REST Framework وSimpleJWT وdrf-spectacular.
- SQLite محليًا، وPostgreSQL في الإنتاج.
- واجهة Django عربية RTL مع دعم الإنجليزية.
- مصادقة الجلسات للويب وJWT للتطبيقات.
- مثال CRUD في `apps/modules/example`.
- وحدة النقل القديمة معزولة في `examples/transport` ولا تدخل التطبيق أو الترحيلات الافتراضية.
- Docker read-only اختياري، Prometheus للمقاييس، Semaphore للقوالب المعتمدة، وسجل تدقيق للإجراءات.

## التشغيل المحلي

يتطلب Python متوافقًا مع الإصدارات المثبتة في `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

افتح `http://127.0.0.1:8000/` للوحة، ثم استخدم صفحات الإدارة داخل النظام. واجهة Django Admin معطلة ومحذوفة من المسارات. أنشئ حساب دخول عبر `python manage.py createsuperuser`. راجع [دليل Infrastructure Manager](docs/INFRASTRUCTURE_MANAGER.md) لإعداد موفري البيانات والأتمتة.

## البيئات والإعدادات

| البيئة | قيمة `DJANGO_SETTINGS_MODULE` | قاعدة البيانات |
| --- | --- | --- |
| تطوير | `config.settings.development` | SQLite افتراضيًا |
| اختبار | `config.settings.test` | SQLite في الذاكرة |
| إنتاج | `config.settings.production` | PostgreSQL عبر `DATABASE_URL` |
| سطح مكتب | `config.settings.desktop` | بحسب إعداد الحزمة |

لا تحفظ الأسرار في المستودع. يتطلب إعداد الإنتاج `SECRET_KEY` و`DATABASE_URL` و`DJANGO_ALLOWED_HOSTS` بأسماء مضيفين صريحة. الإعداد يرفض `*`، ويشترط PostgreSQL، ويفرض HTTPS وملفات تعريف ارتباط آمنة. اقرأ [دليل الإعداد والنشر](docs/development/SETUP.md) و[دليل الأمان](docs/security/SECURITY.md).

لضبط الهوية واللغة محليًا، حدّث `SITE_TITLE` و`SITE_SUBTITLE` و`APP_FONT_FAMILY` و`LANGUAGE_CODE` و`TZ` في `.env`. اللغتان المتاحتان هما العربية والإنجليزية.

## REST API

- عقد موحد: `{success, message, data, errors}`.
- استخدم `/api/v1/` للمشاريع الجديدة؛ مسارات `/api/` موجودة للتوافق مع الواجهة القديمة.
- تسجيل JWT: `POST /api/v1/auth/token/`، وتجديد الرمز: `POST /api/v1/auth/token/refresh/`.
- مثال CRUD: `/api/v1/modules/example/items/`.
- مخطط OpenAPI: `/api/v1/schema/`، وواجهة Swagger: `/api/v1/docs/`.

راجع [عقد API](docs/api/API_CONTRACT.md) لمخطط الدخول والاستجابات والترقيم والأخطاء.

## إنشاء وحدة جديدة

```powershell
python manage.py startmodule records --label "السجلات"
python manage.py migrate
```

الأمر ينشئ هيكل الوحدة ويضيف تسجيلها إلى الإعدادات والمسارات وواجهة SPA والصلاحيات، ثم ينشئ ترحيلًا. راجع الناتج وعدّل قواعده ونموذجه قبل اعتماد الترحيل. دليل الإضافة في [ADDING_MODULE.md](docs/development/ADDING_MODULE.md).

الوحدات تحت `apps/modules/<name>/` وتبقى مستقلة عن `core` و`accounts`. فعّل عينة النقل اختياريًا فقط بوضع `ENABLE_DOMAIN_SAMPLES=True`، ثم نفّذ الترحيلات؛ تفاصيلها في `examples/transport/SAMPLE.md`.

## قاعدة البيانات والنسخ الاحتياطي

- عيّن `DATABASE_URL` إلى PostgreSQL للإنتاج، ثم شغّل `python manage.py migrate` عند كل إصدار يتضمن ترحيلات.
- أنشئ نسخة احتياطية عبر `python manage.py backup_db`.
- تحفظ النسخ في `BACKUP_DIR`؛ اختبر الاستعادة على قاعدة منفصلة قبل الاعتماد على النسخة.
- إعدادات PostgreSQL وعمليات الاستعادة موثقة في [DATABASE.md](docs/database/DATABASE.md).

## الاختبارات والفحوص

```powershell
python manage.py test --settings=config.settings.test
python manage.py check
python manage.py makemigrations --check
python scripts\verify_api.py
```

لتجربة OpenAPI وتحديث التوثيق، افتح `/api/v1/docs/`. أدوات التحقق الموجودة موصوفة في [TESTING.md](docs/development/TESTING.md).

## النشر

- Render: أكمل `DATABASE_URL` و`DJANGO_ALLOWED_HOSTS` و`CSRF_TRUSTED_ORIGINS` في إعدادات الخدمة.
- Docker: أنشئ قيمًا سرية لـ`POSTGRES_PASSWORD` و`DATABASE_URL` و`SECRET_KEY` و`DJANGO_ALLOWED_HOSTS` قبل تشغيل `deployment/docker/docker-compose.prod.yml`.
- لا تُعرّض قاعدة PostgreSQL أو Redis على منافذ عامة في Compose الإنتاجي.

راجع [DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) قبل النشر.

## استرجاع نقطة ما قبل إعادة الهندسة

نسخة المصدر السابقة للقالبين محفوظة في مجلد `_restore_points` بجذر مساحة العمل، باسم `pre-reengineering-source-20261029.zip`.
