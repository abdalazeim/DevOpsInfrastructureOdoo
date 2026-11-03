# مشغّل سطح المكتب الاختياري

تغلّف هذه الإضافة واجهة Django المحلية داخل تطبيق Windows يستخدم Waitress. تعمل
على `127.0.0.1` فقط، وتحفظ SQLite والملفات بجوار التطبيق؛ شغّلها من مجلد يملك
المستخدم صلاحية الكتابة فيه.

## البناء

ثبّت متطلبات سطح المكتب ثم شغّل:

```powershell
pip install -r requirements-desktop.txt
python desktop/build.py --clean
```

ينشئ البناء `dist\Django Enterprise Starter\Django Enterprise Starter.exe`.
يُنشئ PyInstaller ملف المواصفات عند البناء؛ لا يوجد ملف مواصفات يدوي مستقل.

## إنشاء أول حساب إداري

لا يأتي التطبيق بحساب أو كلمة مرور ثابتة. في PowerShell، عيّن اسم المستخدم
وكلمة مرور قوية قبل التشغيل الأول؛ سيرحّل التطبيق قاعدة البيانات وينشئ الحساب
عند ضبط `DJANGO_SEED_ADMIN`:

```powershell
$env:DJANGO_SEED_ADMIN = 'True'
$env:DJANGO_ADMIN_USERNAME = 'admin'
$env:DJANGO_ADMIN_PASSWORD = '<strong-unique-password>'
& '.\dist\Django Enterprise Starter\Django Enterprise Starter.exe'
Remove-Item Env:DJANGO_SEED_ADMIN, Env:DJANGO_ADMIN_USERNAME, Env:DJANGO_ADMIN_PASSWORD
```

يُنشأ مفتاح Django عشوائي ويُحفظ في `.desktop-secret-key` بجوار قاعدة البيانات.
احتفظ بالملف نفسه عند نقل بيانات التطبيق؛ تغييره يسجّل خروج الجلسات الحالية.

## الحدود التشغيلية

- هذا المشغّل أداة محلية للاستخدام الفردي، وليس بديلًا عن نشر Django الإنتاجي.
- يتطلب أول تشغيل اتصالًا محليًا، ويفتح المتصفح على عنوان `127.0.0.1`.
- للإنتاج استخدم إعداد `config.settings.production` وخدمة WSGI خلف HTTPS.
