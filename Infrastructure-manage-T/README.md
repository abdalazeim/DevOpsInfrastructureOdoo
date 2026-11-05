# Odoo Infrastructure Manager - مدير البنية التحتية لنظام أودو

> نظام احترافي لأتمتة إعداد وإدارة بيئات Odoo متعددة الإصدارات باستخدام Docker وTraefik وAnsible وJenkins، بواجهة Terminal تفاعلية سهلة الاستخدام.

---

## 📋 جدول المحتويات

- [نظرة عامة](#نظرة-عامة)
- [المميزات الرئيسية](#المميزات-الرئيسية)
- [الإصدارات المدعومة](#الإصدارات-المدعومة)
- [بنية المشروع](#بينة-المشروع)
- [التثبيت والبدء السريع](#التثبيت-والبدء-السريع)
- [التثبيت عبر Terminal](#التثبيت-عبر-Terminal)
- [التثبيت عبر Jenkins](#التثبيت-عبر-Jenkins)
- [إعدادات الإصدارات](#إعدادات-الإصدارات)
- [الأمان والتشفير](#الأمان-والتشفير)
- [النطاقات وشهادات SSL/TLS](#النطاقات-وشهادات-SSLTLS)
- [النسخ الاحتياطي والاستعادة](#النسخ-الاحتياطي-والاستعادة)
- [مراقبة الصحة والفحص](#مراقبة-الصحة-والفحص)
- [اختبارات الجودة](#اختبارات-الجودة)
- [خطة الأمان والتراجع](#خطة-الأمان-والتراجع)
- [المساهمة والترخيص](#المساهمة-والترخيص)

---

## نظرة عامة

**Odoo Infrastructure Manager** هو أداة DevOps شاملة لنشر وإدارة بيئات Odoo متعددة الإصدارات على نفس الخادم باستخدام تقنيات حاويات Docker، وموزع العكسي Traefik v3.7، وقواعد بيانات PostgreSQL معزولة لكل إصدار.

يدعم النظام نشر **3 إصدارات من Odoo** مع **نسختين مستقلتين لكل إصدار**، بإجمالي **6 نسخ Odoo** تعمل بشكل متوازٍ على خادم واحد، مع عزل كامل بين الشبكات والبيانات والقواعد.

---

## المميزات الرئيسية

| الفئة | المميزات |
|-------|----------|
| **دعم متعدد الإصدارات** | Odoo 17 (PostgreSQL 16)، Odoo 18 (PostgreSQL 17)، Odoo 19 (PostgreSQL 18) |
| **عزل كامل** | شبكة داخلية مستقلة لكل إصدار، شبكات بيانات مستقلة، حاويات معزولة |
| **وصول عبر HTTPS** | Traefik v3.7 مع شهادات Let's Encrypt تلقائية، تحويل HTTP إلى HTTPS |
| **إدارة عبر Terminal** | واجهة قوائم تفاعلية (TUI)، أوامر CLI، سكربتات تثبيت بنقرة واحدة |
| **نشر عبر Jenkins** | خطوط أنابيب (Pipelines) آلية لكل إصدار مع زر "Build Now" |
| **إدارة الأسرار** | كلمات مرور من متغيرات البيئة `.env` بصلاحية `0600`، geen تخزين في Git |
| **النسخ الاحتياطي** | نسخ مضغوطة من قواعد البيانات مع أرشيف المرفقات، بصمة SHA256 |
| **الأمان المتقدم** | فحص المسارات الخطرة (Tar Slip)، منع حقن الأوامر، `no-new-privileges` |

---

## الإصدارات المدعومة

| الإصدار | صورة Odoo | PostgreSQL | PGDATA المسار | المنفذ الداخلي Odoo | المنفذ الداخلي Live Chat | عدد النسخ | النطاقات |
|---------|------------|-------------|----------------|----------------------|--------------------------|-----------|----------|
| **Odoo 17** | `odoo:17` | 16 | `/var/lib/postgresql/data` | 8069 | 8072 | 2 | `${ODOO17_INSTANCE1_DOMAIN}`、`${ODOO17_INSTANCE2_DOMAIN}` |
| **Odoo 18** | `odoo:18` | 17 | `/var/lib/postgresql/data` | 8069 | 8072 | 2 | `${ODOO18_INSTANCE1_DOMAIN}`、`${ODOO18_INSTANCE2_DOMAIN}` |
| **Odoo 19** | `odoo:19` | 18 | `/var/lib/postgresql/18/docker` | 8069 | 8072 | 2 | `${ODOO19_INSTANCE1_DOMAIN}`、`${ODOO19_INSTANCE2_DOMAIN}` |

### تفاصيل النشر

| المكون | الإعداد |
|--------|---------|
| **محرك الحاويات** | Docker Engine + Docker Compose v2 |
| **موزع العكسي** | Traefik v3.7 (شبكة مشتركة `proxy`) |
| **أتمتة النشر** | Ansible (أدوار مشتركة: system, docker, postgresql, odoo, traefik) |
| **تكامل CI/CD** | Jenkins Pipeline مع زرين مستقلين لكل إصدار |
| **تخزين البيانات** | `/data/odoo17/`, `/data/odoo18/`, `/data/odoo19/` |
| **ملفات الإعداد** | `/opt/odoo17/`, `/opt/odoo18/`, `/opt/odoo19/` |
| **النسخ الاحتياطية** | `/data/backups/odoo17/`, `/data/backups/odoo18/`, `/data/backups/odoo19/` |

---

## بينة المشروع

```
odoo-infrastructure-manager/
├── app/
│   ├── main.py                 # نقطة الدخول الرئيسية (CLI و TUI)
│   ├── ui/                     # واجهات المستخدم التفاعلية
│   ├── services/               # خدمات Docker, Ansible, Backups, Health
│   ├── workflows/              # مسارات النشر لكل إصدار
│   ├── validators/             # مدققات الإعدادات والنظام والمنافذ
│   └── models/                 # نماذج البيانات
├── automation/
│   ├── ansible/                # كتب تشغيل Ansible
│   └── scripts/                # سكربتات باش معقمة (init, setup, deploy, backup, restore, health)
├── deployment/
│   ├── traefik/                # إعدادات Traefik v3.7 و Docker Compose
│   ├── odoo17/                 # Odoo 17 + PostgreSQL 16
│   ├── odoo18/                 # Odoo 18 + PostgreSQL 17
│   ├── odoo19/                 # Odoo 19 + PostgreSQL 18
│   └── pgadmin/                # pgAdmin 4 على شبكة proxy
├── profiles/                   # ملفات التكوين القابلة لإعادة الاستخدام (YAML)
├── templates/                  # قوالب البيئة (.env.template) وسكربت الدخول
├── tests/                      # اختبارات الوحدة والتكامل
├── docs/                       # التوثيق الهندسي والأمان
├── bootstrap-odoo-infra.sh     # تثبيت Docker/Ansible وتوليد .env
├── launch-odoo-infra.sh        # نقطة الإطلاق الموحدة
├── .env.example                # نموذج المتغيرات البيئية
├── .gitignore
├── pyproject.toml
└── README.md                   # هذا الملف
```

---

## التثبيت والبدء السريع

### 1. المتطلبات الأساسية

| المتطلب | الحد الأدنى | الموصى به |
|----------|-----------|-----------|
| نظام التشغيل | Ubuntu Server 22.04 LTS | Ubuntu Server 24.04 LTS |
| Python | 3.10+ | 3.12+ |
| Docker Engine | 20.10+ | 24.0+ |
| Docker Compose | v2+ | v2.20+ |
| Ansible | 2.12+ | 2.16+ |
| ذاكرة RAM | 4 GB | 8 GB+ |
| مساحة قرص | 50 GB | 100 GB+ |

### 2. استنساخ المستودع وتجهيز البيئة

```bash
# استنساخ المستودع
git clone https://github.com/your-org/Odoo-MultiVersion-Deployment.git
cd odoo-infrastructure-manager

# إنشاء البيئة الافتراضية لـ Python
python3 -m venv venv
source venv/bin/activate

# تثبيت الحزم المطلوبة
pip install -e .
```

### 3. إعداد ملف الأسرار وتأمين الصلاحيات

```bash
# الطريقة الموصى بها (تثبيت Docker + Ansible وتوليد .env تلقائياً)
sudo ./bootstrap-odoo-infra.sh --install-docker --with-ansible

# أو يدوياً:
cp templates/env.template .env
chmod 600 .env
nano .env
```

> ⚠️ **ملاحظة أمان**: ملف `.env` يحوي كلمات مرور حساسة، يجب أن تكون صلاحياته `0600` فقط، ولا يُرفع أبداً إلى مستودع Git.

### 4. تشغيل النظام

```bash
# واجهة Terminal التفاعلية (الافتراضي)
./launch-odoo-infra.sh

# واجهة Textual داخل الطرفية
./launch-odoo-infra.sh --action textual

# الفحص المسبق الشامل
python3 app/main.py --action preflight

# نشر Traefik فقط
python3 app/main.py --action traefik

# نشر Odoo 17 فقط
python3 app/main.py --action odoo17

# نشر Odoo 18 فقط
python3 app/main.py --action odoo18

# نشر Odoo 19 فقط
python3 app/main.py --action odoo19

# نشر كامل البنية التحتية
python3 app/main.py --action full
```

---

## التثبيت عبر Terminal

يمكن تثبيت كل إصدار باستخدام سكريبت واحد ينفذ جميع مراحل النشر تلقائياً عبر Ansible Playbook.

### Odoo 17

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo17
sudo ./scripts/install-odoo17.sh
```

### Odoo 18

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo18
sudo ./scripts/install-odoo18.sh
```

### Odoo 19

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/install-odoo19.sh
```

> كل سكريبت يقوم بما يلي:
> 1. فحص المتطلبات الأساسية (Docker, Docker Compose, Ansible)
> 2. إنشاء المجلدات والشبكات (`/opt`, `/data`, شبكة `proxy`)
> 3. تشغيل Ansible Playbook لنشر الحاويات
> 4. إجراء فحوصات صحة الخدمات (Odoo, PostgreSQL, Traefik)
> 5. عرض تقرير نهائي مع الروابط المتاحة

---

## التثبيت عبر Jenkins

يوفر النظام خط أنابيب (Pipeline) مستقل لكل إصدار يمكن تفعيله بزر "Build Now" في واجهة Jenkins.

| الزر | الإصدار | PostgreSQL | عدد النسخ |
|------|---------|------------|-----------|
| Install Odoo 17 – Two Instances | Odoo 17 | 16 | 2 |
| Install Odoo 18 – Two Instances | Odoo 18 | 17 | 2 |
| Install Odoo 19 – Two Instances | Odoo 19 | 18 | 2 |

### ملفات Jenkins

| الملف | المسار | الوصف |
|------|--------|-------|
| Jenkinsfile (رئيسي) | `Jenkinsfile` | Pipeline موحد يدعم جميع الإصدارات |
| Jenkinsfile (Odoo 17) | `Jenkins/install-odoo17.Jenkinsfile` | Pipeline مخصص لـ Odoo 17 |
| Jenkinsfile (Odoo 18) | `Jenkins/install-odoo18.Jenkinsfile` | Pipeline مخصص لـ Odoo 18 |
| Jenkinsfile (Odoo 19) | `Jenkins/install-odoo19.Jenkinsfile` | Pipeline مخصص لـ Odoo 19 |

### مراحل كل Pipeline

1. **Checkout GitHub** - استنساخ الكود من المستودع
2. **Pre-Deployment Validation** - فحص المتطلبات وإنشاء المجلدات
3. **Ansible Preparation** - تثبيت مجموعات Ansible والتحقق من ملفات الإعداد
4. **Secrets Configuration** - تشفير كلمات المرور باستخدام Ansible Vault
5. **Docker Deployment** - نشر الحاويات عبر Ansible Playbook
6. **Health Checks** - فحص صحة جميع الخدمات والحاويات
7. **Deployment Report** - عرض تقرير النشر والروابط المتاحة

---

## إعدادات الإصدارات

### ملفات الإصدارات (versions/)

| الملف | المسار | المحتوى |
|-------|--------|---------|
| Odoo 17 | `versions/odoo17.yml` | إعدادات نسختي Odoo 17 (instance1, instance2) |
| Odoo 18 | `versions/odoo18.yml` | إعدادات نسختي Odoo 18 (instance1, instance2) |
| Odoo 19 | `versions/odoo19.yml` | إعدادات نسختي Odoo 19 (instance1, instance2) |

### مثال على هيكل ملف الإصدار

```yaml
odoo_version: "19"
postgres_version: "18"
odoo_image: "odoo:19"
postgres_image: "postgres:18"

odoo_instances:
  - name: instance1
    domain: ${ODOO19_INSTANCE1_DOMAIN}
    data_path: /data/odoo19/instance1
    db_name: odoo19_db1
    db_user: odoo19_instance1
    container_name: odoo19-instance1
  - name: instance2
    domain: ${ODOO19_INSTANCE2_DOMAIN}
    data_path: /data/odoo19/instance2
    db_name: odoo19_db2
    db_user: odoo19_instance2
    container_name: odoo19-instance2
```

### 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 17** | `odoo17` | `odoo17` | `odoo17` |
| **Odoo 18** | `odoo18` | `odoo18` | `odoo18` |
| **Odoo 19** | `odoo19` | `odoo19` | `odoo19` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر:
> - **Jenkins Credentials** (في واجهة Jenkins)
> - **ملف `.env`** (بصلاحيات `0600`)
> - **Ansible Vault** (لتشفير الأسرار)

> 📋 **كيفية التغيير**:
> 1. عدّل ملف `versions/odoo17.yml` / `odoo18.yml` / `odoo19.yml`
> 2. أو مرّر متغيرات البيئة: `ODOO_ADMIN_PASSWORD` و `POSTGRES_PASSWORD`
> 3. أو استخدم واجهة Jenkins لإدخال كلمات مرور مخصصة قبل بدء البناء

---

## الأمان والتشفير

| ميزة | التفاصيل |
|------|----------|
| **حماية ملف `.env`** | صلاحية `0600` فقط، قراءة من المستخدم الجذر فقط |
| **عدم تخزين الأسرار في Git** | كلمات المرور تُقرأ حصرياً من متغيرات البيئة |
| **عزل PostgreSQL** | المنفذ 5432 غير مفتوح للعامة، الوصول فقط عبر شبكة داخلية |
| **Traefik Basic Auth** | حماية لوحة تحكم Traefik عبر مصادقة أساسية |
| **أمان الحاويات** | `no-new-privileges: true` على جميع حاويات Traefik و Odoo |
| **فحص المسارات الخطرة** | رفض المسارات المطلقة و `..` والروابط الرمزية (Tar Slip Protection) |
| **منع حقن الأوامر** | استخدام `subprocess` بقوائم وسائط معقمة، `shell=False` |
| **تراجع آمن** | نسخة أمان تلقائية قبل أي استعادة لقاعدة بيانات |

---

## 💾 النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)

### نظرة عامة على النسخ الاحتياطي

يدعم النظام نسخًا احتياطية شاملة لكل مكون من مكونات النشر، مع إمكانية الاستعادة التلقائية والآمنة عند حدوث أي عطل أو كارثة.

| العنصر | ما الذي نحفظه | الأداة المستخدمة | التردد المقترح |
|--------|--------------|----------------|---------------|
| **PostgreSQL** | قواعد البيانات والمستخدمون والصلاحيات | `pg_dump` / `backup-db.sh` | يومي |
| **Filestore** | المرفقات والصور والملفات المرفوعة | `tar.gz` / `backup.sh` | يومي |
| **Custom Addons** | الإضافات والتعديلات البرمجية المخصصة | Git / `tar.gz` | عند كل تعديل |
| **Odoo Configuration** | ملفات `odoo.conf` وإعدادات الحاوية | `cp` / Ansible | عند كل تعديل |
| **Docker Compose** | ملفات تشغيل الحاويات (`docker-compose.yml`) | Git | عند كل تعديل |
| **Environment** | متغيرات التشغيل والأسرار المشفرة (`.env`) | `chmod 600` + Git (مشفّر) | عند كل تعديل |
| **Traefik** | إعدادات التوجيه والشهادات (SSL/TLS) | `cp` + GPG | أسبوعي |
| **Ansible** | Playbooks و Roles و Inventory | Git | عند كل تعديل |
| **Jenkins** | إعدادات خطوط الأنابيب والملفات المهمة | Jenkins Backup Plugin | أسبوعي |
| **Git** | رقم Commit والإصدار المستخدم في النشر | Git (tag / commit hash) | كل عملية نشر |

### أخذ نسخة احتياطية فورية

```bash
# Odoo 17 - النسخة 1
bash automation/scripts/backup-db.sh 17 odoo17_prod 7

# Odoo 18 - النسخة 1
bash automation/scripts/backup-db.sh 18 odoo18_prod 7

# Odoo 19 - النسخة 1
bash automation/scripts/backup-db.sh 19 odoo19_prod 14

# نسخ احتياطي لملفات المرفقات (Filestore)
bash scripts/backup.sh instance1 /data/backups/odoo17
bash scripts/backup.sh instance2 /data/backups/odoo17

# نسخ احتياطي لإعدادات Traefik والشهادات
tar -czf /data/backups/traefik_$(date +%Y%m%d).tar.gz /etc/traefik /opt/traefik

# نسخ احتياطي لإعدادات Ansible و Jenkins
tar -czf /data/backups/ansible_jenkins_$(date +%Y%m%d).tar.gz ansible/ Jenkins/
```

### محتويات النسخة الاحتياطية لكل قاعدة بيانات

| الملف | الوصف | الصيغة |
|-------|-------|--------|
| `dump_odooXX_prod_YYYYMMDD_HHMMSS.sql.gz` | تفريغ قاعدة بيانات PostgreSQL (البيانات والمستخدمين والصلاحيات) | SQL مضغوط بـ gzip |
| `filestore_odooXX_prod_YYYYMMDD_HHMMSS.tar.gz` | أرشيف مرفقات Odoo (Filestore - الصور والملفات المرفوعة) | tar.gz |
| `custom_addons_odooXX_YYYYMMDD_HHMMSS.tar.gz` | الإضافات والتعديلات البرمجية المخصصة | tar.gz |
| `odoo_config_XX_YYYYMMDD_HHMMSS.tar.gz` | ملفات إعدادات Odoo (`odoo.conf`) | tar.gz |
| `docker_compose_XX_YYYYMMDD_HHMMSS.tar.gz` | ملفات Docker Compose لكل نسخة | tar.gz |
| `env_encrypted_XX_YYYYMMDD_HHMMSS.gpg` | متغيرات البيئة والأسرار المشفرة | GPG مشفر |
| `metadata_odooXX_prod_YYYYMMDD_HHMMSS.json` | بيانات وصفية وبصمة التشفير (SHA256) + رقم Commit Git | JSON |

### استعادة قاعدة بيانات (مع تدابير الأمان)

```bash
# استعادة قاعدة بيانات Odoo 17
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force

# استعادة قاعدة بيانات Odoo 18
bash automation/scripts/restore-db.sh 18 /opt/odoo-infrastructure/backups/odoo18/dump_odoo18_prod_XXXX.sql.gz odoo18_prod --force

# استعادة قاعدة بيانات Odoo 19
bash automation/scripts/restore-db.sh 19 /opt/odoo-infrastructure/backups/odoo19/dump_odoo19_prod_XXXX.sql.gz odoo19_prod --force
```

> ⚠️ **أمان الاستعادة**: عند تمرير `--force`، يقوم النظام تلقائياً بتوليد نسخة أمان احتياطية في مجلد `safety_pre_restore` قبل الكتابة فوق أي قاعدة بيانات قائمة، ويتطلب تأكيداً كتابياً صريحاً (`RESTORE-SNAPSHOT-<ID>`).

## 🔄 طريقة الاستعادة (Restore)

الاستعادة أهم من عملية النسخ نفسها. يجب ألا يكون زر الاستعادة مجرد فك ضغط للملفات.

### أنواع الاستعادة المدعومة

| النوع | الوصف | الاستخدام |
|-------|-------|-----------|
| **Restore to Existing Instance** | استعادة النسخة فوق نسخة موجودة بعد أخذ احتياط إضافي منها | الاستعادة العادية للإصدار الحالي |
| **Restore as New Instance** | إنشاء نسخة جديدة مستقلة للاختبار دون التأثير على النسخة الأصلية | الاختبار والتطوير |

### خطوات الاستعادة التلقائية

عند اختيار نسخة احتياطية، ينفذ النظام الخطوات التالية:

| الخطوة | الإجراء | التفاصيل |
|-------|---------|----------|
| 1 | فحص سلامة الملفات | التحقق من SHA256 و checksums لجميع ملفات النسخة |
| 2 | التحقق من الإصدارات | التأكد من توافق إصدار Odoo و PostgreSQL مع النسخة الاحتياطية |
| 3 | التحقق من المساحة | التأكد من وجود مساحة تخزين كافية للاستعادة |
| 4 | إيقاف Odoo | إيقاف الحاوية المستهدفة قبل الاستبدال |
| 5 | نسخة احتياطية للحالة الحالية | أخذ نسخة احتياطية من الحالة الحالية قبل الاستبدال (حالة الطوارئ) |
| 6 | استعادة PostgreSQL | إنشاء قاعدة البيانات واستعادة البيانات من `pg_dump` |
| 7 | استعادة Filestore | استعادة المرفقات والصور في مسارها الصحيح |
| 8 | استعادة Custom Addons | استعادة الإضافات والتعديلات البرمجية المتوافقة |
| 9 | ضبط الصلاحيات | تعيين صلاحيات الملفات والمجلدات correctamente |
| 10 | تشغيل Odoo | إعادة تشغيل الحاوية وتأكيد عملها |
| 11 | اختبارات التحقق | اختبار قاعدة البيانات والمرفقات والوصول عبر المتصفح |
| 12 | تقرير الاستعادة | تسجيل تقرير كامل بعملية الاستعادة ونتيجتها |

### ضمانات الاستعادة

> ✅ **لا تحذف قاعدة البيانات الحالية أو تستبدل ملفاتها قبل التحقق من النسخة الاحتياطية الجديدة.**
> ✅ **إذا فشلت الاستعادة، يتم العودة تلقائياً إلى الحالة السابقة.**
> ✅ **عملية الإيقاف والإعادة محمية بـ `try/finally` لضمان عدم بقاء الخدمة متوقفة.**

### أوامر الاستعادة

```bash
# استعادة إلى نسخة موجودة (Odoo 17)
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force

# استعادة إلى نسخة موجودة (Odoo 18)
bash automation/scripts/restore-db.sh 18 /opt/odoo-infrastructure/backups/odoo18/dump_odoo18_prod_XXXX.sql.gz odoo18_prod --force

# استعادة إلى نسخة موجودة (Odoo 19)
bash automation/scripts/restore-db.sh 19 /opt/odoo-infrastructure/backups/odoo19/dump_odoo19_prod_XXXX.sql.gz odoo19_prod --force

# استعادة كنسخة جديدة (للاختبار)
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_test --new-instance
```

## 🔧 تشغيل النسخ الاحتياطي من Jenkins وTerminal

### خطوط أنابيب Jenkins للنسخ الاحتياطي والاستعادة

يوفر النظام ثلاثة خطوط أنابيب (Pipelines) مستقلة في Jenkins:

| pipeline | الغرض | الزر |
|----------|--------|------|
| **Backup-Odoo** | نسخ احتياطي شامل لجميع نسخ Odoo 17 و19 أو نسخة محددة | `Build Now` |
| **Restore-Odoo** | استعادة نسخة احتياطية مع تأكيد مطلوب | `Build Now` (يتطلب تأكيد) |
| **Verify-Backups** | فحص سلامة الملفات وقواعد البيانات وتجربة الاستعادة في بيئة اختبار | `Build Now` |

#### Pipeline 1: Backup-Odoo

يؤدي نسخًا احتياطيًا شاملاً لبيانات Odoo وFilestore والإعدادات.

```groovy
// مراحل Backup-Odoo:
// 1. اختيار الإصدار والنسخة (أو all)
// 2. التحقق من مساحة التخزين
// 3. أخذ نسخة احتياطية من PostgreSQL وFilestore
// 4. إنشاء ملف Manifest و Checksums
// 5. رفع النسخة إلى موقع التخزين الآمن
```

#### Pipeline 2: Restore-Odoo

يؤدي استعادة نسخة احتياطية مع تأكيد صريح من المستخدم.

```groovy
// مراحل Restore-Odoo:
// 1. اختيار النسخة الاحتياطية للتاريخ والإصدار
// 2. تأكيد الاستعادة (مطلوب)
// 3. فحص سلامة النسخة (SHA256)
// 4. إيقاف Odoo المستهدف
// 5. أخذ نسخة احتياطية من الحالة الحالية
// 6. استعادة PostgreSQL وFilestore وAddons
// 7. تشغيل Odoo وإجراء اختبارات التحقق
// 8. تقرير الاستعادة النهائي
```

#### Pipeline 3: Verify-Backups

يؤدي فحصًا تلقائيًا لسلامة جميع النسخ الاحتياطية.

```groovy
// مراحل Verify-Backups:
// 1. فحص جميع ملفات النسخ الاحتياطية
// 2. التحقق من SHA256 و checksums
// 3. تجربة استعادة في بيئة اختبار معزولة
// 4. تقرير التحقق النهائي
```

### التشغيل عبر Terminal

```bash
# نسخ احتياطي
./scripts/backup.sh instance1 /data/backups/odoo17
./scripts/backup.sh instance2 /data/backups/odoo17

# استعادة
bash automation/scripts/restore-db.sh 17 <backup_file> <database_name> --force

# فحص صحة النسخ
./scripts/health-check.sh instance1 8069 8072
```

### خطة الاستعاشة من الكوارث (Disaster Recovery Plan)

| السيناريو | الإجراء | الوقت المستهدف للتعافي (RTO) |
|-----------|---------|---------------------------|
| فشل حاوية Odoo | إعادة تشغيل الحاوية من صورة Docker | < 5 دقائق |
| تلف قاعدة بيانات | استعادة من أحدث نسخة احتياطية (pg_dump) | < 30 دقيقة |
| فقدان ملفات المرفقات | استعادة من أرشيف Filestore (tar.gz) | < 15 دقيقة |
| فقدان شهادات SSL | إعادة إصدار شهادات Let's Encrypt عبر Traefik | < 10 دقائق |
| فشل الخادم بالكامل | نشر النظام على خادم جديد باستخدام Jenkins Pipeline | < ساعة واحدة |
| تلف ملفات الإعداد (.env) | استعادة من نسخة Git أو النسخ الاحتياطية المشفرة | < 10 دقائق |

### سياسة الاحتفاظ بالنسخ (Retention Policy)

| نوع النسخة | فترة الاحتفاظ | الحذف التلقائي |
|-----------|--------------|---------------|
| نسخ يومية | 7 أيام | نعم (بعد انتهاء المدة) |
| نسخ أسبوعية | 4 أسابيع | نعم |
| نسخ شهرية | 3 أشهر | نعم |
| نسخ سنوية | سنة واحدة | نعم |

### 명령 النسخ الاحتياطي عبر Ansible

```bash
# نسخ احتياطي لجميع نسخ Odoo 17
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml

# نسخ احتياطي لنسخة محددة
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml -e "instance=instance1"
```

### أوامر النسخ الاحتياطي والاستعادة عبر Terminal (مستقلة)

```bash
# نسخ شامل لجميع نسخ Odoo
sudo ./scripts/backup.sh --all

# نسخ Odoo 17 فقط
sudo ./scripts/backup.sh --version 17

# نسخ Odoo 18 فقط
sudo ./scripts/backup.sh --version 18

# نسخ Odoo 19 فقط
sudo ./scripts/backup.sh --version 19

# نسخ نسخة محددة
sudo ./scripts/backup.sh --instance odoo17-instance1
sudo ./scripts/backup.sh --instance odoo18-instance1
sudo ./scripts/backup.sh --instance odoo19-instance1

# فحص النسخ الاحتياطية وسلامة الملفات
sudo ./scripts/verify-backups.sh

# عرض جميع النسخ الاحتياطية المتوفرة
sudo ./scripts/list-backups.sh

# استعادة نسخة احتياطية باستخدام معرف النسخة
sudo ./scripts/restore.sh --backup-id BACKUP_ID

# استعادة مع تحديد الإصدار والنسخة
sudo ./scripts/restore.sh --version 17 --instance instance1 --backup-id odoo17-instance1-20261104
```

---

## النطاقات وشهادات SSL/TLS

### النطاقات المدعومة

| الخدمة | النطاق |
|-------|--------|
| Odoo 17 - النسخة 1 | `${ODOO17_INSTANCE1_DOMAIN}` |
| Odoo 17 - النسخة 2 | `${ODOO17_INSTANCE2_DOMAIN}` |
| Odoo 18 - النسخة 1 | `${ODOO18_INSTANCE1_DOMAIN}` |
| Odoo 18 - النسخة 2 | `${ODOO18_INSTANCE2_DOMAIN}` |
| Odoo 19 - النسخة 1 | `${ODOO19_INSTANCE1_DOMAIN}` |
| Odoo 19 - النسخة 2 | `${ODOO19_INSTANCE2_DOMAIN}` |
| pgAdmin | `${PGADMIN_DOMAIN}` |
| Traefik Dashboard | `${TRAEFIK_DASHBOARD_DOMAIN}` |

### إعداد DNS

```text
${ODOO17_INSTANCE1_DOMAIN}    ➔  IP_ADDRESS
${ODOO17_INSTANCE2_DOMAIN}    ➔  IP_ADDRESS
${ODOO18_INSTANCE1_DOMAIN} ➔  IP_ADDRESS
${ODOO18_INSTANCE2_DOMAIN} ➔  IP_ADDRESS
${ODOO19_INSTANCE1_DOMAIN} ➔  IP_ADDRESS
${ODOO19_INSTANCE2_DOMAIN} ➔  IP_ADDRESS
${PGADMIN_DOMAIN}   ➔  IP_ADDRESS
${TRAEFIK_DASHBOARD_DOMAIN}   ➔  IP_ADDRESS
```

### متطلبات جدار الحماية

| المنفذ | البروتوكول | الغرض |
|-------|-----------|-------|
| 80 | TCP | HTTP (تحويل تلقائي إلى HTTPS) |
| 443 | TCP | HTTPS (Let's Encrypt) |
| 8072 | TCP | WebSocket / Live Chat (داخلي) |
| 5432 | TCP | PostgreSQL (داخلي فقط، غير مفتوح للعامة) |

### شهادات SSL

- إصدار شهادات مجانية عبر **Let's Encrypt (ACME)**
- تحويل تلقائي من HTTP (منفذ 80) إلى HTTPS (منفذ 443)
- تخزين الشهادات في `acme.json` بصلاحية `0600`
- تجديد تلقائي للشهادات قبل انتهاء صلاحيتها

---

## النسخ الاحتياطي والاستعادة

### أخذ نسخة احتياطية

```bash
# Odoo 17
bash automation/scripts/backup-db.sh 17 odoo17_prod 7

# Odoo 18
bash automation/scripts/backup-db.sh 18 odoo18_prod 7

# Odoo 19
bash automation/scripts/backup-db.sh 19 odoo19_prod 14
```

### محتويات النسخة الاحتياطية

| الملف | الوصف |
|-------|-------|
| `dump_odooXX_prod_YYYYMMDD_HHMMSS.sql.gz` | تفريغ قاعدة بيانات PostgreSQL |
| `filestore_odooXX_prod_YYYYMMDD_HHMMSS.tar.gz` | أرشيف مرفقات Odoo (Filestore) |
| `metadata_odooXX_prod_YYYYMMDD_HHMMSS.json` | بيانات وصفية وبصمة SHA256 |

### استعادة قاعدة بيانات

```bash
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force
```

> ⚠️ **أمان الاستعادة**: عند تمرير `--force`، يقوم النظام تلقائياً بتوليد نسخة أمان احتياطية في مجلد `safety_pre_restore` قبل الكتابة فوق أي قاعدة بيانات قائمة، ويتطلب تأكيداً كتابياً صريحاً (`RESTORE-SNAPSHOT-<ID>`).

---

## مراقبة الصحة والفحص

### فحص صحة الخدمات

```bash
# فحص جميع الخدمات
python3 app/main.py --action health

# فحص نسخة معينة عبر سكريبت
./scripts/health-check.sh instance1 8069 8072
```

### نقاط الفحص

| المكون | طريقة الفحص | المعيار |
|-------|-------------|---------|
| Docker Engine | `docker --version` | versión مثبتة ومستجيبة |
| Docker Compose | `docker compose version` | v2+ |
| PostgreSQL | `pg_isready -U <user> -d <db>` | accepting connections |
| Odoo HTTP | `wget --spider http://localhost:8069/web/database/selector` | استجابة HTTP 200 |
| Traefik | `docker network inspect proxy` | شبكة موجودة ونشطة |
| حاويات Odoo | `docker inspect --format='{{.State.Status}}'` | حالة `running` |

---

## اختبارات الجودة

```bash
# تشغيل جميع الاختبارات
python3 -m unittest discover tests -v

# اختبار مكون معين
python3 -m unittest tests.test_security -v
```

### نطاق الاختبارات

| نوع الاختبار | التفاصيل |
|-------------|----------|
| أمان فك الأرشيف | رفض المسارات الخطرة (Tar Slip، المسارات المطلقة، الروابط الرمزية) |
| تعارض المنافذ | التحقق من عدم تعارض المنافذ بين الإصدارات |
| صحة النطاقات | التحقق من صيغ النطاقات وسجلات DNS |
| أوامر Docker Compose | بناء الأوامر مع أعلام `--check` و `--dry-run` |
| تسلسل خطوات النشر | اختبار تسلسل نشر Odoo 17، 18، 19 و Traefik |

---

## خطة الأمان والتراجع (Security & Rollback Plan)

| السيناريو | الإجراء |
|-----------|---------|
| فشل ترقية Odoo | استرجاع نسخة الأمان من مجلد `safety_pre_restore` |
| تلف قاعدة بيانات | استعادة من نسخة احتياطية مع تأكيد صريح `--force` |
| اختراق أمان | عزل الحاويات المتأثرة، تغيير كلمات المرور فوراً |
| تعطل Traefik | التحقق من شبكة `proxy` وشهادات SSL، إعادة تشغيل الحاوية |

###禁止事项 (محظورات)

- ✅ لا تنفيذ `down -v` إلا بعد تأكيد خطي صريح
- ✅ لا مسح وحدات التخزين المستدامة (Persistent Volumes) بدون تأكيد
- ✅ لا تخزين كلمات المرور في ملفات YAML أو Git
- ✅ لا فتح منفذ PostgreSQL 5432 للعامة

---

## المساهمة والترخيص

### المساهمة

نرحب بالمساهمات من مجتمع المطورين. يرجى:

1. Fork المستودع
2. إنشاء فرع جديد للميزة (`git checkout -b feature/amazing-feature`)
3. committing التغييرات (`git commit -m 'Add amazing feature'`)
4. Push إلى الفرع (`git push origin feature/amazing-feature`)
5. فتح طلب سحب (Pull Request)

### الترخيص

مرخص بموجب رخصة **Apache-2.0**. مطور بعناية لمهندسي DevOps ومديري الأنظمة.

---

## 연락 والدعم

لأي استفسارات أو دعم تقني، يرجى فتح Issue في مستودع المشروع على GitHub.

---

**تم التحديث في:** نوفمبر 2026  
**الإصدار:** 1.0.0  
**الحالة:** producción ready