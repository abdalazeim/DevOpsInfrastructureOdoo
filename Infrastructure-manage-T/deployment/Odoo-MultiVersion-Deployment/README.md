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
│   └── install-odoo19.Jenkinsfile
├── scripts/
│   ├── install-odoo17.sh        # سكريبت تثبيت Odoo 17 عبر Terminal
│   ├── install-odoo19.sh        # سكريبت تثبيت Odoo 19 عبر Terminal
│   ├── health-check.sh          # فحص صحة الخدمات
│   └── backup.sh                # نسخ احتياطية لقواعد البيانات والملفات
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini
│   ├── group_vars/
│   │   └── all.yml
│   ├── playbooks/
│   │   ├── install-odoo17.yml
│   │   └── install-odoo19.yml
│   ├── roles/
│   │   ├── system/              # إعداد المجلدات والشبكات
│   │   ├── docker/              # نشر حاويات Docker Compose
│   │   ├── postgresql/          # إعداد وتحقق PostgreSQL
│   │   ├── odoo/                # إعداد وتحقق Odoo
│   │   └── traefik/             # إعداد وتحقق Traefik
│   └── templates/
├── versions/
│   ├── odoo17.yml               # إعدادات نسخ Odoo 17
│   └── odoo19.yml               # إعدادات نسخ Odoo 19
├── docker/
│   ├── odoo17-compose.yml.j2    # قالب Docker Compose لـ Odoo 17
│   └── odoo19-compose.yml.j2    # قالب Docker Compose لـ Odoo 19
├── backups/
├── requirements.yml             # متطلبات مجموعات Ansible
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

## ملاحظة تقنية مهمة

مستودع Odoo 19 يستخدم مسار تخزين PostgreSQL 18 الجديد `/var/lib/postgresql/18/docker`، لذلك يجب الحفاظ على المسار الصحيح عند تطوير Compose Template، وعدم استخدام مسار PostgreSQL القديم دون مراجعة.

قبل الإنتاج، يجب استبدال كلمات المرور الافتراضية ومراجعة استخدام `user: root` وصلاحيات الملفات.

## إضافة إصدارات مستقبلية

لإضافة إصدار جديد (مثل Odoo 18 أو 20):
1. أضف ملف إعدادات في `versions/odooXX.yml`
2. أضف قالب Docker Compose في `docker/odooXX-compose.yml.j2`
3. أضف سكريبت تثبيت في `scripts/install-odooXX.sh`
4. أضف Playbook في `ansible/playbooks/install-odooXX.yml`
5. أضف خيار في `Jenkinsfile` إذا لزم الأمر

لا حاجة لإعادة بناء النظام من الصفر بفضل إعادة استخدام الأدوار المشتركة.