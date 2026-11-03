# النشر

الإعداد المحلي يستخدم SQLite افتراضيًا. يتطلب الإنتاج PostgreSQL وHTTPS وأسماء
مضيفين صريحة وأسرارًا خارج المستودع.

## Docker Compose المحلي

انسخ `deployment/docker/.env.example` إلى `deployment/docker/.env`، ثم غيّر
المفاتيح وكلمة مرور قاعدة البيانات واحتفظ بتطابق `DATABASE_URL` مع متغيرات
PostgreSQL. شغّل الأوامر من `deployment/docker/`:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

تكون قاعدة البيانات وRedis وDjango على loopback فقط؛ افتح
`http://127.0.0.1:8001/`. استخدم `docker compose down` للإيقاف.

## Compose الإنتاجي

من مجلد المشروع، وفّر `SECRET_KEY` و`DATABASE_URL` و`DJANGO_ALLOWED_HOSTS`
و`TLS_CERTIFICATE_PATH` و`TLS_CERTIFICATE_KEY_PATH`. يجب أن تشير ملفات TLS إلى
شهادة ومفتاح موجودين على مضيف Docker، ويجب أن يحتوي `DATABASE_URL` على بيانات
PostgreSQL مرمّزة في URL. شغّل:

```powershell
docker compose -f deployment/docker/docker-compose.prod.yml up --build -d
```

يُعرّض Nginx فقط على المنفذين 80 و443. راجع إعدادات أسماء المضيفين و
`CSRF_TRUSTED_ORIGINS` و`CORS_ALLOWED_ORIGINS` قبل استقبال حركة خارجية.

## Gunicorn أو Render

يعمل `Procfile` مع Gunicorn، ويعرّف `render.yaml` خدمة ويب وقاعدة بيانات. اضبط
`DJANGO_SETTINGS_MODULE=config.settings.production` والقيم المطلوبة نفسها في
لوحة المنصة. لا تستخدم `runserver` في الإنتاج.

تفاصيل إعدادات البيئة في `../development/SETUP.md`، وإرشادات النسخ الاحتياطي
والاستعادة في `../database/DATABASE.md`.
