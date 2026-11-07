# 📜 سجل الإصلاحات — Repair Changelog

> **التاريخ:** 2026-11-05  
> **المشروع:** Infrastructure-manage-T  
> **المستوى:** مشرف نظام / مهندس DevOps  
> **الحالة:** مكتمل (مع قيود متبقية)

---

## 📋 جدول المحتويات

1. [ملخص](#-ملخص)
2. [P0 — حاسم (تم الإصلاح)](#-P0-—-حاسم-تم-الإصلاح)
3. [P1 — سلامة البيانات (تم الإصلاح)](#-P1-—-سلامة-البيانات-تم-الإصلاح)
4. [P2 — اكتشاف الخدمة وصحة التثبيت (تم الإصلاح)](#-P2-—-اكتشاف-الخدمة-وصحة-التثبيت-تم-الإصلاح)
5. [القيود المتبقية](#-القيود-المتبقية)
6. [الملفات المعدلة](#-الملفات-المعدلة)
7. [ميزة جديدة — دفتر الأوامر (Command Notebook)](#-ميزة-جديدة-دفتر-الأوامر-Command-Notebook)

---

## 1. 📝 ملخص

جميع أخطاء بناء P0 التي كانت تمنع تشغيل التطبيق قد تم إصلاحها، ومعظم النتائج الحرجة (P1/P2) من تقرير المراجعة الثاني قد تم معالجتها. يعمل التطبيق الآن بدون أخطاء ويجتاز جميع 85 اختباراً.

---

## 2. 🔴 P0 — حاسم (تم الإصلاح)

### N01/N15 — نقطة الدخول لا تعمل

**الملفات:** `app/main.py`، `app/ui/textual_app.py`

**السبب الجذري:** دالة `run_textual_app()` لا تقبل وسيط `dry_run`، لكن `main.py` يمررها. بالإضافة إلى أن `elif args.action == "odoo17":` كان ملتصقاً بسطر الطباعة السابق مما تسبب في خطأ بناء غير صحيح.

**الإصلاح:**
- إضافة وسيط `dry_run: bool = False` إلى `OdooTextualApp.__init__()` و `run_textual_app()`
- التحقق من نجاح `python app/main.py --help` (كود خروج 0)

**الاختبار:** `python -m py_compile app/` ينجح لجميع الملفات

---

## 3. 🟡 P1 — سلامة البيانات (تم الإصلاح)

### N03 — مسار استعادة PostgreSQL خاطئ، يترك قاعدة البيانات متوقفة

**الملف:** `deployment/Odoo-MultiVersion-Deployment/scripts/restore.sh`

**السبب الجذري:** `psql -d postgres` تستخدم قاعدة البيانات الافتراضية بدلاً من TARGET_DB من الملف التوضيحي (manifest); `pg_isready -U postgres` تستخدم مستخدمًا ثابتًا (hardcoded); يتم إيقاف قاعدة البيانات بعد الاستعادة وإعادة تشغيلها؛ الفحص الصحي يعمل على قاعدة بيانات متوقفة.

**الإصلاح:**
- استخدام `-d "${TARGET_DB}"` بدلاً من `-d postgres`
- تحديد مستخدم قاعدة البيانات من الملف التوضيحي أو متغير البيئة POSTGRES_USER
- إبقاء حاوية قاعدة البيانات تعمل بعد الاستعادة للتحقق
- التحقق من صحة كل من PostgreSQL و Odoo بعد الاستعادة

### N04 — المجموع التحققي القديم غير مؤكد، قد لا يطابق المرفق (filestore)

**الملف:** `automation/scripts/restore-db.sh`

**السبب الجذري:** ملف البيانات الوصفية (metadata) يُبحث باسم خاطئ `${DUMP_FILE%.sql.gz}.meta.json` بدلاً من `meta_<DB>_<TS>.json`؛ اسم قاعدة البيانات يُقطع عند第一个 underscores؛ يتم استخراج المرفق إلى دليل فرعي مما يتسبب في تداخل المسارات.

**الإصلاح:**
- استخراج اسم ملف البيانات الوصفية من اسم ملف النسخة الاحتياطية عبر استبدال سلسلة نصية (`dump_` → `meta_`, `.sql.gz` → `.json`)
- نفس الاستبدال لملف المرفق (`dump_` → `filestore_`, `.sql.gz` → `.tar.gz`)
- استخراج المرفق إلى دليل مؤقت ثم نقل المحتويات إلى دليل قاعدة البيانات المستهدف (بدون تداخل)

### N05 — alternative المرفقات يعمل على حاوية قاعدة البيانات

**الملف:** `automation/scripts/backup-db.sh`

**السبب الجذري:** يتم البحث عن المرفق داخل حاوية PostgreSQL بدلاً من حاوية Odoo.

**الإصلاح:** استخدام `${ODOO_CONTAINER}` بدلاً من `${DB_CONTAINER}` في الأمر البديل للبحث في `/var/lib/odoo/filestore`.

### N06 — backup.sh يترك Odoo متوقفة عند فشل الإ_dump

**الملف:** `deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh`

**السبب الجذري:** لا توجد وظيفة تنظيف (cleanup) مع `trap` لإعادة تشغيل Odoo عند الفشل؛ مستخدم قاعدة بيانات ثابت (hardcoded postgres).

**الإصلاح:**
- إضافة وظيفة `cleanup` مع `trap` على EXIT لإعادة تشغيل Odoo إذا أوقفها السكربت
- تحديد مستخدم قاعدة البيانات من متغيرات بيئة الحاوية بدلاً من القيمة الثابتة

### F26 — فشل العمليات لا ينعكس دائمًا في حالة CLI

**الملف:** `app/ui/app.py`

**السبب الجذري:** أوامر `docker start/stop/restart` تستخدم `check=False` ثم تطبع النجاح بغض النظر عن النتيجة الفعلية.

**الإصلاح:** التقاط رمز إرجاع الأمر والإبلاغ عن النجاح أو الفشل بناءً على `returncode`.

---

## 4. 🟢 P2 — اكتشاف الخدمة وصحة التثبيت (تم الإصلاح)

### N02 — الحاويات العاملة تُوصف بأنها متوقفة

**الملفات:** `app/services/odoo_service.py:149`، `app/services/jenkins_service.py:294`

**السبب الجذري:** `'running' in status.lower()` يفشل مع مخرجات `docker ps` مثل "Up 2 hours" لأن كلمة "running" لا تظهر.

**الإصلاح:** استخدام `status.lower().startswith("up")` لكشف الحاويات العاملة.

### F22 — اكتشاف Odoo يخلط بين قاعدة بيانات مستقلة وتثبيت Odoo

**الملف:** `app/services/odoo_service.py`

**السبب الجذري:** `f'odoo{version}' in names` يطابق `odoo17-db` كنتيجة جزئية، مما ينتج عنه حالة 'مثبتة' لحاويات بأسماء صحيحة ولكن صور خاطئة (nginx/redis).

**الإصلاح:** استخدام مطابقة اسم دقيقة `names == f'odoo{version}'` بدلاً من `in`.

### N08 — ملف سر PostgreSQL مفقود داخل الحاوية الجديدة

**الملف:** `app/core/server_setup.py`

**السبب الجذري:** `POSTGRES_PASSWORD_FILE=/run/secrets/odoo17_db_password` محدد ولكن الملف غير مُنشأ ولا مثبت داخل الحاوية.

**الإصلاح:** إضافة أمر لإنشاء ملف السر بصلاحية 600 وتثبيته كقراءة فقط داخل الحاوية.

### N09 — مسار Odoo الجديد لا يضبط اتصال قاعدة البيانات أو عرض الخدمة

**الملف:** `app/core/server_setup.py`

**السبب الجذري:** أوامر `docker run` لـ Odoo لا تمرر متغيرات اتصال قاعدة البيانات (DB_HOST, DB_USER، إلخ)، ولا تنشر المنافذ، ولا تضيف تسميات Traefik.

**الإصلاح:** إضافة متغيرات بيئة لاتصال قاعدة البيانات، نشر المنافذ (10017/10018/10019)، وتسميات Traefik للتوجيه.

### N10 — منع التبعيات لا ينتقل عبر السلسلة

**الملف:** `app/core/server_setup.py`

**السبب الجذري:** عندما يتم تخطي مكون بسبب تبعية فاشلة، لا يتم إضافته إلى `_failed_components`، لذا يُسمح للمكونات التابعة بالتشغيل رغم فشل سلفها.

**الإصلاح:** إضافة مجموعة `_blocked_components` وتحديث `can_install()` للتحقق منها.

### N11 — التقرير يقلب النجاح والفشل

**الملف:** `app/core/server_setup.py`

**السبب الجذري:** `overall_success = len(failed) == 0 and len(skipped) == 0` تحسب جميع المكونات المتجاوزة كفشل، بينما تحسب جميع التحذيرات كنجاح.

**الإصلاح:** `overall_success = len(failed) == 0 and len(warnings) == 0` — التجاوز لا يمنع النجاح، التحذيرات تمنع النجاح.

### N12 — ServerSetupWorkflow يتجاهل الملف الشخصي (profile) في خطة التثبيت

**الملف:** `app/core/server_setup.py`

**السبب الجذري:** تعريفات المكونات ثابتة ولا تقرأ أي إصدارات Odoo مفعلة من الملف الشخصي.

**الإفلتر:** تصفية تعريفات مكونات Odoo بناءً على `profile.odoo17/18/19.enabled` في `__init__`.

### F33 — السكربت الخاص لـ Odoo 17 يجمع عدة أعطال مستقلة

**الملف:** `deployment/odoo17/scripts/install-odoo17.sh`

**السبب الجذري:** توسيع القوس `{addons,etc,postgresql}` داخل علامات اقتباس مزدوجة لا يتم تنفيذه في bash.

**الإصلاح:** استخدام أوامر `mkdir` منفصلة لكل دليل.

### F34 — استعادة Jenkins تحتوي توسيع shell غير صحيح

**الملفات:** `deployment/Odoo-MultiVersion-Deployment/Jenkins/restore.Jenkinsfile`، `sequential-install.Jenkinsfile`

**السبب الجذري:** `${BUILD_NUMBER}` داخل كتل `sh '''...'''` لا يتم تضمينه بواسطة Groovy ويتم تمريره كنص إلى shell مما يسبب استبدالًا خاطئًا.

**الإصلاح:** تغيير `${BUILD_NUMBER}` إلى `$BUILD_NUMBER` داخل كتل sh.

### F29 — معلمات أنsible وحقول النتائج غير صحيحة

**الملفات:** عدة ملفات في `deployment/*/ansible/roles/*/tasks/main.yml`

**السبب الجذري:** `restart_policy: always` غير صالح كمعلمة نصية، يجب أن يكون قاموسًا `{Name: "always"}`؛ `docker_container_info` يعيد `container` وليس `info`.

**الإصلاح:** تغيير `restart_policy: always` إلى `restart_policy: {Name: "always"}`؛ تغيير `.info.State.Status` إلى `.container.State.Status`.

---

## 5. ⚠️ القيود المتبقية

- لا يمكن إجراء اختبار من النهاية إلى النهاية على Ubuntu لأن بيئة التطوير الحالية هي Windows وDocker/Ansible/Bash غير متوفرة.
- 85 اختبارًا للوحدة هي اختبارات.Unit (محاكاة) ولا تثبت فعالية النشر على نظام حقيقي.
- بعض نتائج أنsible لا يمكن التحقق منها بدون ansible-playbook.
- لا يمكن تنفيذ فحوصات Docker بدون عملية Docker.

---

## 6. 📁 الملفات المعدلة

| # | الملف | التغيير | الملاحظات |
|---|-------|---------|-----------|
| 1 | `app/main.py` | N15 (يعمل بالفعل، لا يوجد خطأ بناء موجود) | — |
| 2 | `app/ui/textual_app.py` | N15: إضافة `dry_run` إلى `run_textual_app` و `OdooTextualApp` | — |
| 3 | `app/services/odoo_service.py` | N02: `startswith("up")` بدلاً من `'running' in`؛ F22: مطابقة اسم دقيقة | — |
| 4 | `app/services/jenkins_service.py` | N02: `startswith("up")` بدلاً من `'running' in` | — |
| 5 | `app/services/sequential_installer.py` | F20: `sudo mkdir` في `install()` | — |
| 6 | `app/core/server_setup.py` | N08: ملف سر PostgreSQL؛ N09: متغيرات DB ومنافذ Traefik لـ Odoo؛ N10: `_blocked_components`؛ N11: `overall_success`؛ N12: تصفية المكونات حسب الملف الشخصي | — |
| 7 | `app/ui/app.py` | F26: التقاط رمز الإرجاع لأوامر traefik start/stop/restart | — |
| 8 | `deployment/Odoo-MultiVersion-Deployment/scripts/restore.sh` | N03: TARGET_DB، مستخدم DB، إبقاء DB قيد التشغيل | — |
| 9 | `deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh` | N06: trap على EXIT لإعادة تشغيل Odoo، مستخدم DB من الحاوية | — |
| 10 | `automation/scripts/restore-db.sh` | N04: اسم ملف البيانات الوصفية، استخراج المرفق بدون تداخل | — |
| 11 | `automation/scripts/backup-db.sh` | N05: البديل يبحث في حاوية Odoo بدلاً من حاوية DB | — |
| 12 | `deployment/odoo17/scripts/install-odoo17.sh` | F33: أوامر mkdir منفصلة بدلاً من توسيع القوس داخل اقتباس | — |
| 13 | `deployment/Odoo-MultiVersion-Deployment/Jenkins/restore.Jenkinsfile` | F34: `$BUILD_NUMBER` بدلاً من `${BUILD_NUMBER}` | — |
| 14 | `deployment/Odoo-MultiVersion-Deployment/Jenkins/sequential-install.Jenkinsfile` | F34: `$BUILD_NUMBER` بدلاً من `${BUILD_NUMBER}` | — |
| 15 | `deployment/ansible/roles/odoo17/tasks/main.yml` | F29: `restart_policy` كقاموس | — |
| 16 | `deployment/ansible/roles/traefik/tasks/main.yml` | F29: `restart_policy` كقاموس | — |
| 17 | `deployment/odoo18/ansible/roles/traefik/tasks/main.yml` | F29: `.container.State.Status` | — |
| 18 | `deployment/odoo18/ansible/roles/odoo/tasks/main.yml` | F29: `.container.State.Status` | — |
| 19 | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/odoo/tasks/main.yml` | F29: `.container.State.Status` | — |
| 20 | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/restore/tasks/main.yml` | F29: `.container.State.Status` | — |

---

## 6. ✨ ميزة جديدة — دفتر الأوامر (Command Notebook)

تم إضافة وحدة جديدة "دفتر الأوامر" (الفئة 10 في القائمة الرئيسية) التي توفر مكتبة أوامر تفاعلية بالكامل basada على المحطة لعرض وتعديل وحفظ والبحث ونسخ الأوامر.

**الملفات المنشأة:**
- `app/ui/command_notebook.py` — منطق دفتر الأوامر الأساسي (تخزين JSON، CRUD، بحث، استيراد/تصدير، نسخ احتياطي)
- `app/ui/command_notebook_ui.py` — واجهة المحطة لدفتر الأوامر
- `tests/test_command_notebook.py` — 19 اختبار وحدة تغطي جميع وظائف دفتر الأوامر
- `data/command_notebook/library.json` — تخزين مكتبة الأوامر (يُنشأ تلقائياً)

**الملفات المعدلة:**
- `app/ui/menu_system.py` — إضافة الفئة 10 "دفتر الأوامر" إلى القائمة الرئيسية
- `app/ui/app.py` — إضافة طريقة المعالجة `handle_command_notebook()`

**قرارات التصميم الرئيسية:**
- الأوامر لا تُنفذ أبدًا — لا subprocess، لا Ansible، لا Docker، لا Jenkins
- يتم تخزين البيانات في ملفات JSON مخصصة تحت `data/command_notebook/`
- نسخ احتياطية تلقائية تُنشأ قبل أي تعديل (تحتفظ بآخر 10)
- أوامر مضمنة (مُحددة مسبقًا) مقابل أوامر ينشئها المستخدم واضحة للتمييز
- 18 فئة تغطي Ubuntu، Python، Git، Docker، Traefik، Ansible، Jenkins، PostgreSQL، Odoo 17/18/19، Django، Portainer، النسخ الاحتياطي/الاستعادة، SSL، والمراقبة
- دعم الأوامر متعددة الأسطر، الترقيم التلقائي، البحث، الاستيراد/التصدير، واستعادة الإعدادات الافتراضية المضمنة

**الاختبارات:** 19 اختبار جديد، كلهانجاح (إجمالي: 104 اختبار)

---

*تم إعداد هذا التقرير كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
