# Odoo Multi-Version Deployment

نظام نشر موحد لبيئات Odoo متعددة الإصدارات باستخدام Docker و Ansible و Traefik و Jenkins.

## نظرة عامة

يدعم المستودع نشر نسختين مستقلتين لكل من Odoo 17 و Odoo 19 على نفس الخادم، مع عزل كل نسخة في شبكتها الداخلية الخاصة، وربطها بشبكة Traefik المشتركة للوصول عبر HTTPS.

## هيكل الملفات

```
Odoo-MultiVersion-Deployment/
├── Jenkinsfile                  # Pipeline موحد يدعم Odoo 17 و Odoo 19
├── Jenkins/
│   ├── install-odoo17.Jenkinsfile
│   ├── install-odoo19.Jenkinsfile
│   ├── backup.Jenkinsfile
│   ├── restore.Jenkinsfile
│   ├── verify-backups.Jenkinsfile
│   └── system-config-backup.Jenkinsfile
├── scripts/
│   ├── install-odoo17.sh        # سكريبت تثبيت Odoo 17 عبر Terminal
│   ├── install-odoo19.sh        # سكريبت تثبيت Odoo 19 عبر Terminal
│   ├── health-check.sh          # فحص صحة الخدمات
│   ├── backup.sh                # نسخ احتياطية لقواعد البيانات والملفات
│   ├── restore.sh               # استعادة نسخ احتياطية مع تدابير الأمان
│   ├── verify-backups.sh        # فحص سلامة النسخ الاحتياطية
│   ├── list-backups.sh          # عرض جميع النسخ الاحتياطية المتوفرة
│   ├── backup-system-config.sh    # نسخ إعدادات نظام Ubuntu والبنية التحتية
│   └── restore-system-config.sh   # استعادة إعدادات نظام Ubuntu
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini
│   ├── group_vars/
│   │   └── all.yml
│   ├── playbooks/
│   │   ├── install-odoo17.yml
│   │   ├── install-odoo19.yml
│   │   ├── backup.yml
│   │   ├── restore.yml
│   │   ├── verify.yml
│   │   └── system-config-backup.yml
│   ├── roles/
│   │   ├── system/              # إعداد المجلدات والشبكات
│   │   ├── permissions/         # إدارة الصلاحيات والأمان
│   │   ├── docker/              # نشر حاويات Docker Compose
│   │   ├── postgresql/          # إعداد وتحقق PostgreSQL
│   │   ├── odoo/                # إعداد وتحقق Odoo
│   │   ├── traefik/             # إعداد وتحقق Traefik
│   │   ├── backup/              # نسخ احتياطي لـ Odoo
│   │   ├── restore/             # استعادة نسخ Odoo الاحتياطية
│   │   ├── verify/              # التحقق من سلامة النسخ الاحتياطية
│   │   └── system-config-backup/  # نسخ إعدادات نظام Ubuntu
│   └── templates/
│       └── odoo/
│           └── odoo.conf.j2     # قالب إعدادات Odoo
├── versions/
│   ├── odoo17.yml               # إعدادات نسخ Odoo 17
│   └── odoo19.yml               # إعدادات نسخ Odoo 19
├── docker/
│   ├── odoo17-compose.yml.j2    # قالب Docker Compose لـ Odoo 17
│   └── odoo19-compose.yml.j2    # قالب Docker Compose لـ Odoo 19
├── backup/
│   ├── backup-policy.yml        # سياسة النسخ الاحتياطي
│   ├── retention.yml            # سياسة الاحتفاظ بالنسخ
│   └── manifest-schema.json     # مخطط ملف manifest.json
├── requirements.yml             # متطلبات مجموعات Ansible
├── .gitignore
└── README.md
```

## الإعدادات

| المكون | Odoo 17 | Odoo 19 |
|--------|---------|---------|
| صورة Odoo Docker | `odoo:17` | `odoo:19` |
| PostgreSQL | 16 | 18 |
| PGDATA المسار | `/var/lib/postgresql/data` | `/var/lib/postgresql/18/docker` |
| المنفذ الداخلي Odoo | 8069 | 8069 |
| المنفذ الداخلي Live Chat | 8072 | 8072 |
| عدد النسخ | 2 | 2 |
| Traefik | مشترك | مشترك |
| بيانات PostgreSQL | مستقلة | مستقلة |
| مستخدم الحاوية | 999:999 | 999:999 |

## النطاقات

| النسخة | النطاق |
|--------|--------|
| Odoo 17 - النسخة 1 | `odoo1.devops-odoo.com` |
| Odoo 17 - النسخة 2 | `odoo2.devops-odoo.com` |
| Odoo 19 - النسخة 1 | `odoo19-1.devops-odoo.com` |
| Odoo 19 - النسخة 2 | `odoo19-2.devops-odoo.com` |

## مجلدات البيانات

| المكون | المسار |
|--------|--------|
| Odoo 17 - النسخة 1 | `/data/odoo17/instance1` |
| Odoo 17 - النسخة 2 | `/data/odoo17/instance2` |
| Odoo 19 - النسخة 1 | `/data/odoo19/instance1` |
| Odoo 19 - النسخة 2 | `/data/odoo19/instance2` |

## التشغيل عبر Terminal

### Odoo 17

```bash
cd /opt/Odoo-MultiVersion-Deployment
sudo ./scripts/install-odoo17.sh
```

### Odoo 19

```bash
cd /opt/Odoo-MultiVersion-Deployment
sudo ./scripts/install-odoo19.sh
```

## التشغيل عبر Jenkins

| الزر | الوصف |
|------|--------|
| Install Odoo 17 – Two Instances | يثبّت نسختي Odoo 17 مع PostgreSQL 16 |
| Install Odoo 19 – Two Instances | يثبّت نسختي Odoo 19 مع PostgreSQL 18 |
| Backup Odoo | نسخ احتياطي شامل أو انتقائي لنُسخ Odoo |
| Restore Odoo | استعادة نسخة احتياطية مع تأكيد إلزامي |
| Verify Backups | فحص سلامة جميع النسخ الاحتياطية |
| System Config Backup | نسخ إعدادات نظام Ubuntu والبنية التحتية |

## ملاحظة تقنية مهمة

مستودع Odoo 19 يستخدم مسار تخزين PostgreSQL 18 الجديد `/var/lib/postgresql/18/docker`، لذلك يجب الحفاظ على المسار الصحيح عند تطوير Compose Template، وعدم استخدام مسار PostgreSQL القديم دون مراجعة.

قبل الإنتاج، يجب استبدال كلمات المرور الافتراضية ومراجعة استخدام صلاحيات الملفات. جميع الحاويات تشغل بمستخدم غير جذر (UID 999) وفق مبدأ أقل صلاحية كافية.

## 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 17** | `odoo17` | `odoo17` | `odoo17-instance1/2` |
| **Odoo 19** | `odoo19` | `odoo19` | `odoo19-instance1/2` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو Ansible Vault.

## 💾 النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)

### نظرة عامة

يدعم النظام نسخًا احتياطية شاملة لكل مكون من مكونات النشر، مع دعم أربع عمليات رئيسية: **Backup، Restore، Verify، Schedule**.

### ما الذي نحفظه لكل نسخة Odoo

| العنصر | ما الذي نحفظه | الأداة المستخدمة |
|--------|--------------|----------------|
| **PostgreSQL** | قواعد البيانات والمستخدمون والصلاحيات | `pg_dump` |
| **Filestore** | المرفقات والصور والملفات المرفوعة | `tar` + `zstd` |
| **Custom Addons** | الإضافات والتعديلات البرمجية المخصصة | `tar` + `zstd` |
| **Odoo Configuration** | ملفات `odoo.conf` وإعدادات الحاوية | `tar` + `zstd` |
| **Docker Compose** | ملفات تشغيل الحاويات (`docker-compose.yml`) | Git |
| **Environment** | متغيرات التشغيل والأسرار المشفرة | Ansible Vault |
| **Traefik** | إعدادات التوجيه والشهادات (SSL/TLS) | Ansible |
| **Ansible** | Playbooks و Roles و Inventory | Git |
| **Jenkins** | إعدادات خطوط الأنابيب والملفات المهمة | Jenkins Backup Plugin |
| **Git** | رقم Commit والإصدار المستخدم في النشر | Git (tag / commit hash) |

### أنواع النسخ الاحتياطي المدعومة

| النوع | الوظيفة |
|-------|----------|
| **Full Backup** | نسخ شامل لجميع بيانات النسخة وإعداداتها |
| **Database Backup** | نسخ قواعد البيانات فقط |
| **Filestore Backup** | نسخ المرفقات والملفات |
| **Configuration Backup** | نسخ الإعدادات وملفات التشغيل |
| **Complete Infrastructure Backup** | نسخ جميع نسخ Odoo وملفات البنية التحتية |
| **Pre-Update Backup** | نسخ تلقائي قبل تحديث Odoo أو الإضافات |

### أخذ نسخة احتياطية عبر Terminal

```bash
# نسخ نسخة محددة
cd /opt/Odoo-MultiVersion-Deployment
sudo ./scripts/backup.sh instance1 odoo17 /data/backups/odoo17
sudo ./scripts/backup.sh instance2 odoo17 /data/backups/odoo17
sudo ./scripts/backup.sh instance1 odoo19 /data/backups/odoo19
sudo ./scripts/backup.sh instance2 odoo19 /data/backups/odoo19

# إذا لم يتم تحديد الإصدار، يتم اكتشافه تلقائيًا من الحاويات العاملة
sudo ./scripts/backup.sh instance1 /data/backups
```

### استعادة نسخة احتياطية عبر Terminal

```bash
# استعادة نسخة احتياطية موجودة
sudo ./scripts/restore.sh odoo17-instance1-20261104 odoo17 instance1 existing

# استعادة كنسخة جديدة
sudo ./scripts/restore.sh odoo17-instance1-20261104 odoo17 instance1 new-instance odoo17-instance3
```

### فحص وعرض النسخ الاحتياطية

```bash
# فحص سلامة جميع النسخ
sudo ./scripts/verify-backups.sh /data/backups

# عرض جميع النسخ المتوفرة
sudo ./scripts/list-backups.sh /data/backups

# عرض نسخ إصدار معين فقط
sudo ./scripts/list-backups.sh /data/backups odoo17
```

### تنظيم مجلدات النسخ الاحتياطية

```
/data/backups/
├── odoo17/
│   ├── instance1/
│   │   └── 2026-11-04_020000/
│   │       ├── database_20261104_020000.sql
│   │       ├── filestore_20261104_020000.tar.zst
│   │       ├── addons_20261104_020000.tar.zst
│   │       ├── config_20261104_020000.tar.zst
│   │       ├── manifest.json
│   │       └── checksums.sha256
│   │
│   └── instance2/
│
├── odoo19/
│   ├── instance1/
│   │   └── 2026-11-04_020000/
│   │       ├── database_20261104_020000.sql
│   │       ├── filestore_20261104_020000.tar.zst
│   │       ├── addons_20261104_020000.tar.zst
│   │       ├── config_20261104_020000.tar.zst
│   │       ├── manifest.json
│   │       └── checksums.sha256
│   │
│   └── instance2/
│
├── infrastructure/
│   ├── ansible/
│   ├── traefik/
│   └── docker/
│
├── jenkins/
│
└── reports/
```

### ملف معلومات النسخة الاحتياطية (Manifest)

```json
{
  "backup_id": "odoo17-instance1-20261104",
  "odoo_version": "17",
  "postgres_version": "16",
  "instance": "instance1",
  "database": "odoo17_db1",
  "backup_type": "full",
  "created_at": "2026-11-04T02:00:00+02:00",
  "database_backup": "database_20261104_020000.sql",
  "filestore_backup": "filestore_20261104_020000.tar.zst",
  "addons_backup": "addons_20261104_020000.tar.zst",
  "config_backup": "config_20261104_020000.tar.zst",
  "integrity_check": "sha256",
  "status": "completed"
}
```

### عملية النسخ الاحتياطي الصحيحة (Ansible Role)

1. إنشاء مجلدات النسخ الاحتياطي
2. التحقق من مساحة التخزين المتاحة
3. إيقاف حاويات Odoo مؤقتًا (محمية بـ `block/rescue/always` لضمان إعادة التشغيل حتى عند الفشل)
4. تصدير قاعدة البيانات باستخدام `pg_dump`
5. نسخ Filestore باستخدام `tar` + `zstd`
6. نسخ Custom Addons باستخدام `tar` + `zstd`
7. نسخ إعدادات Odoo باستخدام `tar` + `zstd`
8. إنشاء ملف Manifest (manifest.json)
9. إنشاء Checksums (SHA256)
10. إعادة تشغيل حاويات Odoo (في قسم `always`)
11. تسجيل نتيجة العملية

### سياسة الاحتفاظ (Retention)

يتم الاحتفاظ بنسخ يومية لمدة 7 أيام، وأسبوعية لمدة 4 أسابيع، وشهرية لمدة 3 أشهر، وسنوية لمدة سنة واحدة.

## 🖥️ نسخ إعدادات نظام Ubuntu والبنية التحتية (System Configuration Backup)

### نظرة عامة

يوفر هذا النظام نسخًا احتياطية مستقلة لإعدادات نظام Ubuntu والبنية التحتية، منفصلة عن نسخ قواعد بيانات Odoo وملفاتها. يشمل ذلك إعدادات الشبكة، SSH، Docker، النظام، المشاريع في /opt، والجداول المجدولة.

### ما الذي يُحفظ

| العنصر | المسار | الوصف |
|--------|--------|-------|
| إعدادات الشبكة | `/etc/netplan` | تكوين بطاقات الشبكة وعناوين IP |
| إعدادات SSH | `/etc/ssh` | مفاتيح المضيف والإعدادات |
| Docker Daemon | `/etc/docker` | إعدادات محرك Docker |
| تقسيم الأقراص | `/etc/fstab` | ملف تقسيمات الأقراص |
| اسم المضيف | `/etc/hostname` | اسم المضيف للنظام |
| سجلات المضيفين | `/etc/hosts` | ملف hosts |
| حزم النظام | `/etc/apt` | قائمة الحزم المثبتة |
| خدمات النظام | `/etc/systemd/system` | ملفات خدمات systemd |
| المهام المجدولة | `/etc/cron.d` | ملفات Cron المجدولة |
| جدار الحماية | `/etc/ufw` | إعدادات UFW (Debian/Ubuntu) |
| المشاريع | `/opt` | مجلدات وملفات المشاريع |
| معلومات النظام | `system-info/` | hostnamectl, lsblk, findmnt, df, ip, docker |

### أخذ نسخة احتياطية لإعدادات النظام

```bash
# تشغيل السكربت مباشرة (يجب بصلاحيات الجذر)
sudo ./scripts/backup-system-config.sh

# مع التشفير
export ENCRYPT=true
export ENCRYPT_PASSWORD="your-secure-password"
sudo ./scripts/backup-system-config.sh

# عبر Jenkins Pipeline
# استخدم Pipeline: system-config-backup.Jenkinsfile
```

### استعادة إعدادات النظام

```bash
# استعادة نسخة احتياطية معينة
sudo ./scripts/restore-system-config.sh 2026-11-04_020000

# العملية مرحلية - تُطلب تأكيد قبل كل مرحلة استعادة
# لا تُستعاد الإعدادات الحساسة بشكل أعمى (Netplan, SSH, fstab)
```

### تحذيرات أمنية

> ⚠️ **تنبيه مهم**: إعدادات Netplan و SSH و fstab قد تختلف بعد إعادة تثبيت النظام (تغيير بطاقات الشبكة، UUID الأقراص، عناوين IP). يُنصح بمراجعة كل إعداد قبل استعادته لتجنب فقدان الوصول إلى الخادم.

> 🔒 **التشفير**: الأرشيف غير المشفر قد يحتوي على مفاتيح SSH وكلمات مرور. استخدم التشفير قبل نقل الأرشيف خارج الخادم.

### Jenkins Pipeline

| الخط | الوصف |
|------|-------|
| `system-config-backup.Jenkinsfile` | نسخ إعدادات نظام Ubuntu مع خيارات التشفير والتحقق |

## إدارة الصلاحيات (Permissions)

يُطبّق مبدأ أقل صلاحية كافية (Least Privilege) على جميع مكونات النظام:

- جميع حاويات Docker تشغل بمستخدم `999:999` (غير جذر)
- مجلدات بيانات PostgreSQL بصلاحية `0700` لمستخدم `999:999`
- ملفات إعدادات Odoo بصلاحية `0640` لمستخدم `999:999`
- مستخدم système `odoo` مضاف لمجموعة `docker`
- sock Docker بمجموعة `docker` وصلاحية `0660`

## إضافة إصدارات مستقبلية

لإضافة إصدار جديد (مثل Odoo 18 أو 20):

1. أضف ملف إعدادات في `versions/odooXX.yml`
2. أضف قالب Docker Compose في `docker/odooXX-compose.yml.j2`
3. أضف سكريبت تثبيت في `scripts/install-odooXX.sh`
4. أضف Playbook في `ansible/playbooks/install-odooXX.yml`
5. أضف خيار في `Jenkinsfile` إذا لزم الأمر

لا حاجة لإعادة بناء النظام من الصفر بفضل إعادة استخدام الأدوار المشتركة.