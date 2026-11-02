# مدير البنية التحتية لنظام أودو (Odoo Infrastructure Manager)

## 📌 وصف النظام

نظام **Odoo Infrastructure Manager** هو أداة احترافية لأتمتة إعداد وإدارة بيئات Odoo باستخدام Docker وTraefik، بواجهة Terminal تفاعلية سهلة الاستخدام.

يدعم جميع إصدارات **Ubuntu Server** و **Ubuntu Desktop** بدءًا من **Ubuntu 22.04 LTS وحتى أحدث إصدار مستقر**، مع إمكانية إدارة Odoo 17 وOdoo 19 وقواعد بيانات PostgreSQL، وتخصيص إعدادات الخادم والشبكات والنطاقات والتخزين في كل تجربة.

يوفر النظام التثبيت والإعداد التلقائي، ومراقبة الخدمات، وإدارة السجلات، والنسخ الاحتياطي والاستعادة، مع حفظ ملفات الإعداد وإمكانية إعادة تنفيذ العمليات بأمان.

---

## 🌟 مميزات المشروع

- **بنية متعددة الإصدارات (Multi-Version Odoo)**:
  - تشغيل **Odoo 17.0** مع **PostgreSQL 16**.
  - تشغيل **Odoo 19.0** مع **PostgreSQL 18**.
  - عزل كامل لكل إصدار في شبكة داخلية مستقلة، مع ربطهما بشبكة البروكسي المشتركة `proxy`.
- **توجيه وحماية Traefik v3.7**:
  - توجيه تلقائي عبر الدومينات الفرعية.
  - إصدار شهادات SSL/TLS مجانية عبر **Let's Encrypt (ACME)**.
  - تحويل حركة المرور تلقائياً من HTTP (منفذ 80) إلى HTTPS (منفذ 443).
  - حماية لوحة تحكم Traefik عبر مصادقة Basic Auth وتدابير الأمان الرأسية (Security Headers).
  - دعم مسار WebSocket / Livechat على المنفذ 8072 بشكل مستقل.
- **إدارة آمنة للأسرار والبيانات**:
  - عدم تخزين كلمات المرور نهائياً داخل ملفات YAML أو مستودع Git.
  - قراءة الأسرار حصرياً من ملف البيئة المحمي `.env` بصلاحيات `0600`.
  - عزل قواعد بيانات PostgreSQL تماماً داخل الحاويات وعدم فتح المنفذ 5432 للعامة.
- **النسخ الاحتياطي والاستعادة الذكية**:
  - أخذ نسخ احتياطية مضغوطة من قواعد البيانات عبر `pg_dump` مع أرشيف مرفقات Odoo (Filestore).
  - فحص سلامة الملفات عبر بصمة التشفير **SHA256**.
  - تطبيق سياسة الاحتفاظ بالنسخ (Retention Policy) وحذف النسخ القديمة تلقائياً.
  - آلية استعادة ذكية تأخذ نسخة أمان تلقائية (Safety Backup) قبل الكتابة فوق أي قاعدة بيانات قائمة وتتطلب تأكيداً كتابياً صريحاً لمنع الأخطاء البشرية.
- **التنفيذ الآمن والأتمتة**:
  - التحقق المسبق من صحة الإعدادات، عدم تعارض المنافذ، وتوفر المتطلبات.
  - دعم وضع المحاكاة والمعاينة (**Dry-Run**) قبل أي تعديل على النظام الفعلي.
  - كتابة سكربتات باش صارمة تعتمد `set -Eeuo pipefail`.
  - فصل طبقة الواجهة عن طبقة التنفيذ عبر مكتبة `subprocess` بقوائم وسائط معقمة لمنع حقن الأوامر (Command Injection).

---

## 📁 هيكلية المشروع (Project Architecture)

```
odoo-infrastructure-manager/
├── app/                        # النواة البرمجية بلغة بايثون
│   ├── main.py                 # نقطة الدخول الرئيسية للـ CLI والـ TUI
│   ├── ui/                     # واجهات المستخدم التفاعلية (TUI & Terminal)
│   ├── services/               # خدمات Docker, Ansible, Backups, Execution, Health
│   ├── workflows/              # مسارات العمل: إعداد الخادم، نشر Traefik، نشر Odoo
│   ├── validators/             # مدققات الإعدادات والنظام والمنافذ
│   └── models/                 # نماذج البيانات للملفات والعمليات والصحة
├── automation/
│   ├── ansible/                # كتب تشغيل Ansible لإعداد خادم Ubuntu وDocker
│   │   ├── playbook.yml
│   │   ├── inventory.ini
│   │   └── roles/ (baseline, docker)
│   └── scripts/                # سكربتات باش معقمة (init, setup, deploy, backup, restore, health)
├── deployment/
│   ├── traefik/                # إعدادات Docker Compose و Traefik v3.7 Static Config
│   ├── odoo17/                 # Compose وإعدادات Odoo 17 + PostgreSQL 16
│   └── odoo19/                 # Compose وإعدادات Odoo 19 + PostgreSQL 18
├── profiles/                   # ملفات التكوين القابلة لإعادة الاستخدام (YAML)
│   ├── example.yaml
│   ├── devops-odoo-prod.yaml
│   └── local-dev.yaml
├── templates/                  # قوالب Jinja2 لملفات Compose و Odoo Config
├── tests/                      # اختبارات الوحدة والتكامل مع Pytest / Unittest
├── docs/                       # التوثيق الهندسي، الأمان، وخطة التعافي من الكوارث
├── .env.example                # نموذج المتغيرات البيئية والأسرار
├── .gitignore
├── pyproject.toml              # مواصفات الحزمة البرمجية
└── README.md                   # التوثيق الشامل
```

---

## 🚀 التثبيت والبدء السريع

### 1. المتطلبات الأساسية
- خادم أو جهاز يعمل بنظام **Ubuntu Server** أو **Ubuntu Desktop** (بدءاً من **Ubuntu 22.04 LTS وحتى أحدث إصدار مستقر**).
- Python 3.10 أو أحدث.
- Docker Engine و Docker Compose v2.

### 2. استنساخ المستودع وتجهيز البيئة
```bash
git clone <repository_url> odoo-infrastructure-manager
cd odoo-infrastructure-manager

# إنشاء البيئة الافتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت الحزم المطلوبة
pip install -e .
```

### 3. إعداد ملف الأسرار وتأمين الصلاحيات
```bash
cp templates/env.template .env
chmod 600 .env

# تحرير كلمات المرور الحقيقية في .env
nano .env
```

---

## 🖥️ تشغيل الواجهة التفاعلية (Terminal TUI)

لتشغيل واجهة الـ Terminal التفاعلية:
```bash
python3 app/main.py
# أو عبر الأمر المباشر إذا تم تثبيت الحزمة
odoo-manager
```

### خيارات سطر الأوامر (CLI Flags):
```bash
# خيار الفحص المسبق الذكي الشامل وعرض جدول المكونات
python3 app/main.py --action preflight

# تشغيل التدقيق وفحص التوافق لملف إعداد معين
python3 app/main.py --action validate --profile profiles/devops-odoo-prod.yaml

# معاينة تنفيذ تجهيز الخادم دون أي تعديل فعلي (Dry-Run)
python3 app/main.py --action prep --profile profiles/example.yaml --dry-run

# نشر Traefik v3.7 فقط
python3 app/main.py --action traefik

# نشر بيئة Odoo 17 فقط
python3 app/main.py --action odoo17

# نشر بيئة Odoo 19 فقط
python3 app/main.py --action odoo19

# نشر كامل البنية التحتية دفعة واحدة
python3 app/main.py --action full

# فحص صحة الحاويات والخدمات والشبكة
python3 app/main.py --action health
```

---

## 🔍 الفحص المسبق والتثبيت الذكي والنسخ الشاملة

عند تشغيل النظام، يبدأ بفحص شامل وغير مدمر للبيئة الحالية قبل إجراء أي تغييرات:

1. **فحص المتطلبات والحزم**: التحقق من إصدار Ubuntu، وجود Docker Engine، Docker Compose v2، Traefik، Ansible، والأدوات (`curl`, `jq`, `ufw`, `tar`, `gzip`).
2. **عرض حالة التثبيت والإعداد**: إذا كانت الأداة مثبتة، يعرض النظام حالتها وإصدارها ومسارها وتفاصيل إعدادها، **دون إعادة تثبيتها أو تعديلها**.
3. **التثبيت التلقائي الذكي**: إذا كانت إحدى الأدوات المطلوبة غير مثبتة، يعرض النظام اسمها وسبب الحاجة إليها، ويتيح تثبيتها تلقائياً بعد موافقة صريحة من المستخدم.
4. **النسخ الاحتياطي الوقائي الشامل**: خيار إلزامي لإنشاء نسخة احتياطية كاملة تشمل:
   - ملفات الإعداد والملفات الشخصية (`profiles/*.yaml`).
   - ملفات البيئة والأسرار (`.env`).
   - ملفات Docker Compose وتكوينات Traefik وشهادات SSL (`acme.json`).
   - قواعد بيانات PostgreSQL ومجلدات البيانات الدائمة.
5. **استعادة النسخ الاحتياطية**: استعراض النسخ السابقة واستعادتها مع التحقق من سلامة الأرشيف عبر **SHA256** وطلب كتابة رمز تأكيد صريح (`RESTORE-SNAPSHOT-<ID>`).
6. **تقرير نهائي**: جدول يوضح حالة كل مكون: مثبت، غير مثبت، يحتاج تحديثاً، أو به مشكلة، مع إصدار المكون والإجراء الموصى به.

---

## ⚙️ إعدادات النطاقات (DNS) وشهادات SSL/TLS

لاستخدام النطاقات الحقيقية وشهادات Let's Encrypt التلقائية:
1. قم بإنشاء سجلات **A Record** في مزود الـ DNS الخاص بك، بحيث تشير النطاقات التالية إلى عنوان IP العام للخادم:
   - `odoo17.yourdomain.com` ➔ `IP_ADDRESS`
   - `odoo19.yourdomain.com` ➔ `IP_ADDRESS`
   - `traefik.yourdomain.com` ➔ `IP_ADDRESS`
2. تأكد من أن المنافذ **80** و **443** مفتوحة على جدار الحماية (UFW أو Security Groups).
3. اضبط البريد الإلكتروني الخاص بك في المتغير `ACME_EMAIL` داخل ملف `.env`، وسيتولى Traefik إصدار وتجديد الشهادات تلقائياً مع تخزينها في الملف المشفر `acme.json` بصلاحيات `0600`.

---

## 💾 دليل النسخ الاحتياطي والاستعادة (Backup & Recovery)

### أخذ نسخة احتياطية فورية:
```bash
# Odoo 17
bash automation/scripts/backup-db.sh 17 odoo17_prod 7

# Odoo 19
bash automation/scripts/backup-db.sh 19 odoo19_prod 14
```
سيقوم السكربت بحفظ:
1. تفريغ قاعدة البيانات بصيغة `dump_odoo17_prod_YYYYMMDD_HHMMSS.sql.gz`.
2. أرشيف الملفات المرفقة بصيغة `filestore_odoo17_prod_YYYYMMDD_HHMMSS.tar.gz`.
3. ملف البيانات الوصفية وبصمة `SHA256`.

### استعادة قاعدة بيانات مع تدابير الأمان:
```bash
# لن تتم الاستعادة على قاعدة بيانات قائمة إلا بتأكيد صريح:
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force
```
> **ملاحظة أمان فائقة الأهمية**: عند تمرير `--force`، يقوم النظام تلقائياً بتوليد نسخة أمان احتياطية في المجلد `safety_pre_restore` قبل حذف أو إعادة بناء القاعدة القديمة.

---

## 🧪 الاختبارات وضمان الجودة

لتشغيل حزمة الاختبارات الشاملة (25 اختبار وحدة وتكامل):
```bash
python3 -m unittest discover tests -v
```

تشمل الاختبارات:
- التحقق من رفض المسارات الخطرة مثل جذر النظام `/` أو `/etc`.
- فحص تعارض المنافذ والنطاقات وصيغ البريد الإلكتروني وسجلات الـ Cron.
- بناء أوامر Docker Compose و Ansible مع أعلام الفحص (`--check`) و (`--dry-run`).
- اختبار تسلسل خطوات نشر Odoo 17 و Odoo 19 و Traefik.

---

## 🛡️ خطة الأمان والتراجع (Security & Rollback Plan)

- **التراجع في حال فشل الترقية**: يتم استرجاع نسخة الأمان التلقائية المخزنة في مجلد `safety_pre_restore`.
- **التشغيل بدون صلاحيات مفرطة**: تعمل كافة حاويات Traefik و Odoo بمستخدمين معزولين وخيارات `no-new-privileges:true`.
- **المنع الصارم لأوامر الحذف الجماعي**: الأداة لا تنفذ أبداً `down -v` أو تمس وحدات التخزين المستدامة (Persistent Volumes) إلا بعد طلب تأكيد خطي صريح يبيّن حجم الضرر المحتمل.

---

مرخص بموجب رخصة **Apache-2.0**. مطور بعناية لمهندسي الـ DevOps ومديري الأنظمة.
