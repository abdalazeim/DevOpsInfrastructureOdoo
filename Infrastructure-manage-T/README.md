# مدير البنية التحتية لنظام أودو (Odoo Infrastructure Manager)

## 📌 وصف النظام

نظام **Odoo Infrastructure Manager** هو أداة احترافية لأتمتة إعداد وإدارة بيئات Odoo باستخدام Docker وTraefik، بواجهة Terminal تفاعلية سهلة الاستخدام.

يدعم جميع إصدارات **Ubuntu Server** و **Ubuntu Desktop** بدءًا من **Ubuntu 22.04 LTS وحتى أحدث إصدار مستقر**، مع إمكانية إدارة Odoo 17 وOdoo 18 وOdoo 19 وقواعد بيانات PostgreSQL، وتخصيص إعدادات الخادم والشبكات والنطاقات والتخزين في كل تجربة.

يوفر النظام التثبيت والإعداد التلقائي، ومراقبة الخدمات، وإدارة السجلات، والنسخ الاحتياطي والاستعادة، مع حفظ ملفات الإعداد وإمكانية إعادة تنفيذ العمليات بأمان.

---

## 🌟 مميزات المشروع

- **بنية متعددة الإصدارات (Multi-Version Odoo)**:
  - تشغيل **Odoo 17.0** مع **PostgreSQL 16** على المنفذ `10017`.
  - تشغيل **Odoo 18.0** مع **PostgreSQL 17** على المنفذ `10018`.
  - تشغيل **Odoo 19.0** مع **PostgreSQL 18** على المنفذ `10019`.
  - عزل كامل لكل إصدار في شبكة داخلية مستقلة (`odoo17_internal` / `odoo18_internal` / `odoo19_internal`)، مع ربطها بشبكة البروكسي المشتركة `proxy`.
  - تثبيت موحّد عبر `automation/scripts/install-odoo.sh <17|18|19>` بأسلوب minhng92 (مجلد مستقل، `postgresql/`، `addons/`، `etc/`، و`entrypoint.sh`).
- **إدارة عبر الطرفية فقط**:
  - واجهة قوائم نصية افتراضية وواجهة Textual تفاعلية.
  - أوامر CLI لتنفيذ العمليات والأتمتة مع عرض الخطوات والسجلات.
  - لا يتطلب مدير البنية التحتية Node.js أو واجهة ويب أو خادم HTTP محليًا.
- **pgAdmin بأسلوب Websoft9**:
  - حاوية `dpage/pgadmin4` على شبكة `proxy` الخارجية.
  - بيانات الدخول من `.env` (`PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD`) دون أي قاعدة PostgreSQL تجريبية.
  - منفذ قابل للضبط عبر `PGADMIN_HTTP_PORT` (افتراضيًا `5050`).
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
  - كتابة سكربتات باش صارمة تعتمد `set -Eeuo pipefail`، وتطبيع أسطر CRLF إلى LF قبل التنفيذ.
  - فصل طبقة الواجهة عن طبقة التنفيذ عبر مكتبة `subprocess` بقوائم وسائط معقمة لمنع حقن الأوامر (Command Injection).
  - فك آمن للأرشيف عبر `safe_extractall` يرفض المسارات المطلقة و`..` والروابط الرمزية والملفات الخاصة (Tar Slip / Symlink Escape).
  - `ExecutionService` يقرأ stdout/stderr عبر خيوط متزامنة مع مهلة 300 ثانية، ما يمنع الجمود (Deadlock) عند امتلاء المخازن المؤقتة.

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
│   ├── odoo18/                 # Compose وإعدادات Odoo 18 + PostgreSQL 17
│   ├── odoo19/                 # Compose وإعدادات Odoo 19 + PostgreSQL 18
│   └── pgadmin/                # pgAdmin 4 على شبكة proxy الخارجية
├── profiles/                   # ملفات التكوين القابلة لإعادة الاستخدام (YAML)
│   ├── example.yaml
│   ├── devops-odoo-prod.yaml
│   └── local-dev.yaml
├── templates/                  # قوالب البيئة (env.template) وسكربت الدخول
├── tests/                      # اختبارات الوحدة والتكامل مع Pytest / Unittest
├── docs/                       # التوثيق الهندسي، الأمان، وخطة التعافي من الكوارث
├── bootstrap-odoo-infra.sh     # تثبيت Docker/Ansible وتوليد .env وأسرار عشوائية
├── launch-odoo-infra.sh        # نقطة إطلاق موحدة (TUI افتراضيًا أو Textual)
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
# الطريقة الموصى بها: يثبت Docker (عبر get.docker.com الرسمي) وAnsible،
# ثم يولّد .env بكلمات مرور عشوائية وهاش Basic Auth وصلاحيات 0600.
sudo ./bootstrap-odoo-infra.sh --install-docker --with-ansible

# أو يدويًا:
cp templates/env.template .env
chmod 600 .env
nano .env
```

### 4. تشغيل النظام
```bash
# واجهة Terminal التفاعلية (الافتراضي)
./launch-odoo-infra.sh

# تشغيل واجهة Textual داخل الطرفية
./launch-odoo-infra.sh --action textual
```

خيارات `bootstrap-odoo-infra.sh` المهمة:
- `--skip-docker` / `--skip-ansible` لتخطي التثبيت.
- `--docker-version <ver>` و`--docker-mirror <url>` و`--docker-dry-run`.
- `--regenerate-env` لإعادة توليد الأسرار (ينشئ نسخة احتياطية من `.env` القديم).

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

# نشر بيئة Odoo 17 / 18 / 19 فقط
python3 app/main.py --action odoo17
python3 app/main.py --action odoo18
python3 app/main.py --action odoo19

# نشر كامل البنية التحتية دفعة واحدة
python3 app/main.py --action full

# فحص صحة الحاويات والخدمات والشبكة
python3 app/main.py --action health

# تشغيل واجهة Textual داخل الطرفية
python3 app/main.py --action textual
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
   - `odoo18.yourdomain.com` ➔ `IP_ADDRESS`
   - `odoo19.yourdomain.com` ➔ `IP_ADDRESS`
   - `pgadmin.yourdomain.com` ➔ `IP_ADDRESS`
   - `traefik.yourdomain.com` ➔ `IP_ADDRESS`
2. تأكد من أن المنافذ **80** و **443** مفتوحة على جدار الحماية (UFW أو Security Groups)، وأن لوحة تحكم Traefik لا تُنشر على أي منفذ إدارة مباشر (`api.insecure` معطّل دائمًا، والمنفذ 10090 غير مستخدم).
3. اضبط البريد الإلكتروني الخاص بك في المتغير `ACME_EMAIL` داخل ملف `.env`، وسيتولى Traefik إصدار وتجديد الشهادات تلقائياً مع تخزينها في الملف المشفر `acme.json` بصلاحيات `0600`.

---

## 💾 دليل النسخ الاحتياطي والاستعادة (Backup & Recovery)

### أخذ نسخة احتياطية فورية:
```bash
# Odoo 17
bash automation/scripts/backup-db.sh 17 odoo17_prod 7

# Odoo 18
bash automation/scripts/backup-db.sh 18 odoo18_prod 7

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

لتشغيل حزمة الاختبارات:
```bash
python3 -m unittest discover tests -v
```

تشمل الاختبارات:
- رفض المسارات الخطرة عند فك الأرشيف (Tar Slip، المسارات المطلقة، الروابط الرمزية والصلبة، والملفات الخاصة).
- فحص تعارض المنافذ والنطاقات وصيغ البريد الإلكتروني وسجلات الـ Cron.
- بناء أوامر Docker Compose و Ansible مع أعلام الفحص (`--check`) و (`--dry-run`).
- اختبار تسلسل خطوات نشر Odoo 17 و Odoo 18 و Odoo 19 و Traefik.

---

## 🛡️ خطة الأمان والتراجع (Security & Rollback Plan)

- **التراجع في حال فشل الترقية**: يتم استرجاع نسخة الأمان التلقائية المخزنة في مجلد `safety_pre_restore`.
- **التشغيل بدون صلاحيات مفرطة**: تعمل كافة حاويات Traefik و Odoo بمستخدمين معزولين وخيارات `no-new-privileges:true`.
- **المنع الصارم لأوامر الحذف الجماعي**: الأداة لا تنفذ أبداً `down -v` أو تمس وحدات التخزين المستدامة (Persistent Volumes) إلا بعد طلب تأكيد خطي صريح يبيّن حجم الضرر المحتمل.

---

مرخص بموجب رخصة **Apache-2.0**. مطور بعناية لمهندسي الـ DevOps ومديري الأنظمة.

## فحص Python وPostgreSQL واختيار مكان التثبيت

من القائمة الرئيسية اختر `16`، أو شغّل:

```bash
./launch-odoo-infra.sh --action runtimes
```

اختر Python أو PostgreSQL، ثم الجهاز أو Docker. يعرض الفحص إصدارات ومسارات البرامج المكتشفة على الجهاز، أو صور Docker والحاويات وحالتها. لا يعد وجود عميل PostgreSQL وحده تثبيتًا للخادم، ولا يعني وجود صورة Docker تشغيل حاوية.

خيارات Python: 3.10 و3.11 و3.12 وإدخال إصدار أحدث. خيارات PostgreSQL: 15 و16 و17 و18. الفحص محدود بالمسارات والصور المعروفة؛ يعرض أخطاء الوصول منفصلة عن عدم العثور على تثبيت.

توصيات المشروع التي تظهر عند اختيار Python، وفق إعدادات صاحب المشروع:

- Odoo 17: Python 3.10 أو 3.11.
- Odoo 18: Python 3.11 موصى به.
- Odoo 19: Python 3.12 موصى به بشدة.

هذه توصيات للاختيار وليست منعًا لبقية الإصدارات. تثبيت Python على الجهاز لا يغيّر إصدار Python داخل حاويات Odoo.

تثبيت Python على Ubuntu متاح للإصدارات 3.10 و3.11 و3.12: يعرض أوامر apt، ويضيف deadsnakes PPA للإصدارين 3.11 و3.12، ثم يطلب تأكيد التنفيذ ويعرض المخرجات مباشرة. يتوقف عند فشل أي أمر ويتحقق من الإصدار وvenv وensurepip بعد التثبيت. توفر الحزم يعتمد على إصدار Ubuntu والمستودعات؛ لا يغيّر python3 الافتراضي ولا ينزل get-pip.py. يمكن معاينة الأوامر فقط باستخدام `--action runtimes --dry-run`. تثبيت Python وPostgreSQL داخل Docker وإصدارات Python الأحدث ما زال ينتظر طرق التثبيت. يتطلب تشغيل المدير نفسه وجود Python مسبقًا؛ تثبيته الأولي يجب أن يتم من سكربت الإقلاع قبل تشغيل المدير.

### PostgreSQL على Ubuntu

يدعم خيار `runtimes` تثبيت PostgreSQL 15 و16 و17 و18 على الجهاز. يعرض الخطة ويطلب التأكيد، ثم يثبت `postgresql-common` ويشغل سكربت إعداد PGDG الرسمي تفاعليًا، ويحدث فهرس apt ويثبت الخادم والعميل المطابقين للإصدار و`libpq-dev`. يعرض إصدار الخادم و`pg_lsclusters` وحالة خدمة PostgreSQL دون pager. يتوقف عند أول فشل؛ نجاح الخدمة العامة لا يثبت جاهزية كل cluster.

يمكن اختيار حزمة `postgresql-<version>-pgvector` أيضًا. تثبيت الحزمة منفصل عن تفعيل الإضافة: بعد إنشاء قاعدة Odoo والاتصال بها، ينفذ المسؤول `CREATE EXTENSION IF NOT EXISTS vector;`. لا تنفذ الأداة SQL تلقائيًا على قاعدة بيانات.

المصدر: [دليل PostgreSQL الرسمي لتثبيت Ubuntu](https://www.postgresql.org/download/linux/ubuntu/). توفر الحزم يعتمد على إصدار Ubuntu والمعمارية والمستودع.

### فحص Docker Engine

من القائمة `16` اختر `3. Docker Engine`. يعرض الفحص مسار العميل وإصداره، وإصدار المحرك وDocker context وCompose ومعلومات الحاويات والتخزين المتاحة. يميز بين عدم اكتشاف التثبيت، وعميل لا يعمل، ورفض الصلاحيات، وعدم الوصول للمحرك، والمحرك المستجيب. عدم الوصول لا يعني أن Docker غير مثبت. الفحص نفسه لا يعدل الخدمات؛ ويمكن بعده فتح خطة تثبيت المحرك المحلي. قد يكون اتصال الفحص الحالي بمحرك بعيد. يستخدم الفحص المسبق نفس التشخيص.

### تثبيت Docker Engine من القائمة

اختر `16` ثم `3`، وافتح خطة التثبيت بعد عرض الحالة. يتوفر أحدث إصدار مستقر أو اختيار VERSION_STRING من الإصدارات المشتركة بين docker-ce وdocker-ce-cli بعد إعداد المستودع. يكتشف المثبت Ubuntu codename والمعمارية، ويضيف مفتاح Docker وملف docker.sources، ثم يثبت Engine وCLI وcontainerd.io وBuildx وCompose.

تعرض الحزم المتعارضة قبل التنفيذ، ويطلب apt تأكيد الإزالة مع عرض تأثيرها. لا ينفذ المثبت purge أو حذف بيانات Docker. إزالة الحزم قد توقف خدمات قائمة. إذا ألغيت اختيار الإصدار بعد إعداد المستودع، يبقى إعداد المستودع محفوظًا.

يتحقق المسار من خدمة Docker والمحرك المحلي وCompose وBuildx. يمكن تفعيل اختبار hello-world؛ ينزل الصورة ويشغل حاوية مؤقتة. إضافة مستخدم إلى مجموعة docker اختيارية، تمنحه صلاحيات واسعة، وتتطلب تسجيل الخروج والدخول لتفعيلها.

للمعاينة دون تعديل استخدم `./launch-odoo-infra.sh --action runtimes --dry-run`. يتطلب اكتشاف الحزم والمعمارية Ubuntu وdpkg حتى في المعاينة. هذا المسار مستقل عن خيار Docker القديم في bootstrap.

المصدر: [تثبيت Docker Engine على Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

### Docker Compose كإضافة مستقلة

اختر القائمة `16` ثم `4` لعرض نتيجة `docker compose version`. إذا كانت الإضافة تعمل يعرض الإصدار دون إعادة التثبيت. إذا غاب عميل Docker يوجهك لإعداد Engine أولًا. عند تعذر تشغيل Compose يعرض الخطأ وخطة `apt-get update` ثم `apt-get install -y docker-compose-plugin`، ويتحقق بعد التنفيذ. يجب أن يكون مستودع Docker الرسمي مجهزًا؛ مسار تثبيت Engine يجهزه. تدعم هذه القائمة `--dry-run` ولا تحتاج إلى اتصال بالمحرك لقراءة إصدار Compose.

### Portainer

اختر القائمة `16` ثم `5`. يفحص المسار حاويات Portainer CE/EE والصورة القديمة المعروفة، بما فيها الحاويات المتوقفة أو ذات الاسم المخصص، ويعرض الاسم والصورة والحالة والمنافذ. يرفض التثبيت عند تعذر الاتصال أو تعارض الاسم؛ الصور المخصصة غير المعروفة قد لا تُكتشف.

إذا لم توجد حاوية يعرض خطة Portainer CE LTS على محرك Linux المحلي، مع volume دائم `portainer_data` (يعاد استخدامه إن وجد)، ومقبس Docker، ومنفذ HTTPS قابل للاختيار افتراضيًا 9443. منفذ Edge 8000 اختياري. بعد موافقة المستخدم يفحص تعارض المنافذ ويثبت الحاوية ويتحقق من حالتها دون حذف حاويات قائمة. يتطلب صلاحية الوصول للمقبس `/var/run/docker.sock`؛ لا يحاول تشغيل الأوامر تلقائيًا بـ sudo.

إدارة التثبيت تتم عبر Terminal؛ Portainer نفسه يوفر لوحة ويب على `https://<SERVER-IP>:9443` لإكمال الإعداد الأولي. الشهادة الافتراضية ذاتية التوقيع، وقد يلزم رمز إعداد من سجلات الحاوية. تحقق تشغيل الحاوية لا يعني اختبار جاهزية HTTPS. يمكن استخدام `--action runtimes --dry-run` للمعاينة.

المصدر: [تثبيت Portainer CE على Docker/Linux](https://docs.portainer.io/start/install-ce/server/docker/linux).
