# Odoo 18 Multi-Instance Deployment

نظام نشر مستقل لإصدارات Odoo 18 باستخدام Docker و Ansible و Traefik و Jenkins.

## نظرة overview

يدعم هذا المستودع نشر نسختين مستقلتين من Odoo 18 على نفس الخادم، مع عزل كل نسخة في شبكتها الداخلية الخاصة، وربطها بشبكة Traefik المشتركة للوصول عبر HTTPS.

## هيكل الملفات

```
odoo18/
├── Jenkinsfile                  # Pipeline Jenkins لـ Odoo 18
├── Jenkins/
│   └── install-odoo18.Jenkinsfile
├── scripts/
│   ├── install-odoo18.sh        # سكريبت تثبيت Odoo 18 عبر Terminal
│   ├── health-check.sh          # فحص صحة الخدمات
│   └── backup.sh                # نسخ احتياطية لقواعد البيانات والملفات
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini
│   ├── group_vars/
│   │   └── all.yml
│   ├── playbooks/
│   │   └── install-odoo18.yml
│   ├── roles/
│   │   ├── system/              # إعداد المجلدات والشبكات
│   │   ├── docker/              # نشر حاويات Docker Compose
│   │   ├── postgresql/          # إعداد وتحقق PostgreSQL
│   │   ├── odoo/                # إعداد وتحقق Odoo
│   │   └── traefik/             # إعداد وتحقق Traefik
│   └── templates/
├── versions/
│   └── odoo18.yml               # إعدادات نسخ Odoo 18
├── docker/
│   └── odoo18-compose.yml.j2    # قالب Docker Compose لـ Odoo 18
├── backups/
├── requirements.yml             # متطلبات مجموعات Ansible
└── README.md
```

## الإعدادات

| المكون | Odoo 18 |
|--------|---------|
| صورة Odoo Docker | `odoo:18` |
| PostgreSQL | 17 |
| PGDATA المسار | `/var/lib/postgresql/data` |
| المنفذ الداخلي Odoo | 8069 |
| المنفذ الداخلي Live Chat | 8072 |
| عدد النسخ | 2 |
| Traefik | مشترك |
| بيانات PostgreSQL | مستقلة |

## النطاقات

| النسخة | النطاق |
|--------|--------|
| Odoo 18 - النسخة 1 | `odoo18-1.devops-odoo.com` |
| Odoo 18 - النسخة 2 | `odoo18-2.devops-odoo.com` |

## مجلدات البيانات

| المكون | المسار |
|--------|--------|
| Odoo 18 - النسخة 1 | `/data/odoo18/instance1` |
| Odoo 18 - النسخة 2 | `/data/odoo18/instance2` |

## التشغيل عبر Terminal

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo18
sudo ./scripts/install-odoo18.sh
```

## التشغيل عبر Jenkins

| الزر | الوصف |
|------|--------|
| Install Odoo 18 – Two Instances | يثبّت نسختي Odoo 18 مع PostgreSQL 17 |

## 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 18** | `odoo18` | `odoo18` | `odoo18` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو ملف `.env` أو Ansible Vault.

## ملاحظة تقنية importante

يجب استبدال كلمات المرور الافتراضية ومراجعة استخدام `user: root` وصلاحيات الملفات قبل الإنتاج.