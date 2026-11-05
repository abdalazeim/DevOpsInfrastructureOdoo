# ⚙️ دليل تثبيت Ansible على Ubuntu Server

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الأداة:** Ansible - أداة أتمتة إعداد وإدارة السيرفرات  
> **حالات الاستخدام:** إدارة Docker، Traefik، PostgreSQL، Odoo، Jenkins  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [مقدمة عن Ansible](#-مقدمة-عن-Ansible)
2. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
3. [الطريقة الأولى: التثبيت اليدوي خطوة بخطوة](#-الطريقة-الأولى-التثبيت-اليدوي-خطوة-بخطوة)
4. [إنشاء هيكل مشروع Ansible](#-إنشاء-هيكل-مشروع-Ansible)
5. [إعداد ملف Inventory](#-إعداد-ملف-Inventory)
6. [اختبار اتصال Ansible](#-اختبار-اتصال-Ansible)
7. [تثبيت Collections أساسية](#-تثبيت-Collections-أساسية)
8. [إعداد ملف إعدادات Ansible](#-إعداد-ملف-إعدادات-Ansible)
9. [الاختبار النهائي لـ Ansible](#-الاختبار-الن Final-ل-Ansible)
10. [أوامر إدارة Ansible الأساسية](#-أوامر-إدارة-Ansible-أساسية)
11. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
12. [إزالة Ansible بالكامل](#-إزالة-Ansible-بشكل-كامل)
13. [المعلومات التقنية](#-المعلومات-التقنية)
14. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🎯 مقدمة عن Ansible

**Ansible** هي أداة أتمتة مفتوحة المصدر تستخدم لتثبيت وإعداد وإدارة السيرفرات والبنية التحتية. تعتمد على لغة YAML لكتابة تعليمات التشغيل (Playbooks) ولا تتطلب تثبيت أي عميل (Agentless) على الخوادم المستهدفة.

### ✅ ما يمكن إدارةه عبر Ansible في هذا النظام:

| المكون | الغرض |
|--------|-------|
| Docker | إدارة محركات Docker والحاويات والصور |
| Traefik | إدارة البروكسي العكسي والشهادات (SSL) |
| PostgreSQL | إدارة قواعد بيانات Odoo |
| Odoo 17/18/19 | نشر وإدارة نسخ Odoo المتعددة |
| Jenkins | إدارة خادم التكامل والنشر المستمر (CI/CD) |

---

## 2. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | نظام تشغيل مدعوم | `cat /etc/os-release` | Ubuntu 22.04 LTS / 24.04 LTS |
| 2 | Python 3 | `python3 --version` | `sudo apt install -y python3` |
| 3 | pip | `pip3 --version` | `sudo apt install -y python3-pip` |
| 4 | صلاحيات جذر (sudo) | `id` | — |
| 5 | اتصال إنترنت | `ping -c 4 ppa.launchpad.net` | — |

---

## 3. 🚀 الطريقة الأولى: التثبيت اليدوي خطوة بخطوة

اتبع هذه التترتيب exactement لتثبيت Ansible على نظام Ubuntu Server.

### الخطوة 1: تحديث النظام

```bash
sudo apt update
sudo apt upgrade -y
```

### الخطوة 2: تثبيت Python و Pip والمتطلبات الأساسية

```bash
sudo apt install -y python3 python3-pip python3-venv software-properties-common
```

| الحزمة | الغرض |
|--------|-------|
| `python3` | لغة البرمجة الأساسية لـ Ansible |
| `python3-pip` | مدير حزم بايثون |
| `python3-venv` | إنشاء بيئات افتراضية لبايثون |
| `software-properties-common` | إدارة مستودعات PPA |

### الخطوة 3: إضافة مستودع Ansible الرسمي عبر PPA

```bash
sudo add-apt-repository --yes --update ppa:ansible/ansible
```

### الخطوة 4: تثبيت Ansible

```bash
sudo apt install -y ansible
```

### الخطوة 5: التحقق من إصدار Ansible

```bash
ansible --version
```

### الخطوة 6: التحقق من تثبيت Ansible Core

```bash
ansible --core-version
```

---

## 4. 📁 إنشاء هيكل مشروع Ansible

```bash
# إنشاء هيكل المجلدات
mkdir -p ~/ansible-project/{inventory,playbooks,roles,group_vars,host_vars}

# الانتقال إلى مجلد المشروع
cd ~/ansible-project
```

### 📂 هيكل المجلدات المُنشأ

```
ansible-project/
├── inventory/           # ملفات تعريف المخزون (الخوادم المستهدفة)
│   └── hosts.ini        # ملف المخزون الرئيسي
├── playbooks/           # ملفات تشغيل الأتمتة (YAML)
│   └── site.yml         # ملف التشغيل الرئيسي
├── roles/               # الأدوار القابلة لإعادة الاستخدام
├── group_vars/          # متغيرات المجموعات
└── host_vars/           # متغيرات المضيفين الفرديين
```

---

## 5. 🖥️ إعداد ملف Inventory

أنشئ ملف المخزون لتحديد الخوادم التي سيديرها Ansible:

```bash
nano inventory/hosts.ini
```

### محتوى ملف `inventory/hosts.ini`:

```ini
[local]
localhost ansible_connection=local
```

### شرح ملف المخزون:

| القسم | المضيف | نوع الاتصال | الغرض |
|-------|--------|-------------|-------|
| `[local]` | `localhost` | `ansible_connection=local` | إدارة السيرفر المحلي مباشرة |

---

## 6. 🔌 اختبار اتصال Ansible

```bash
ansible all -i inventory/hosts.ini -m ping
```

### ✅ النتيجة المتوقعة:

```json
localhost | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

---

## 7. 📦 تثبيت Collections أساسية

تثبيت المجموعات (Collections) الأساسية لإدارة Docker والنظام:

```bash
# مجموعة إدارة Docker
ansible-galaxy collection install community.docker

# مجموعة إدارة النظام (POSIX)
ansible-galaxy collection install ansible.posix

# مجموعة الأدوات العامة
ansible-galaxy collection install community.general
```

### الخطوة 8: عرض Collections المثبتة

```bash
ansible-galaxy collection list
```

---

## 8. ⚙️ إعداد ملف إعدادات Ansible

أنشئ ملف الإعدادات لتخصيص سلوك Ansible:

```bash
nano ansible.cfg
```

### محتوى ملف `ansible.cfg`:

```ini
[defaults]
inventory = ./inventory/hosts.ini
host_key_checking = True
retry_files_enabled = False
interpreter_python = auto_silent

[privilege_escalation]
become = False
```

### شرح الإعدادات:

| الإعداد | القيمة | الوصف |
|--------|--------|-------|
| `inventory` | `./inventory/hosts.ini` | مسار ملف المخزون الافتراضي |
| `host_key_checking` | `True` | التحقق من مفاتيح SSH للمضيفين البعيدين |
| `retry_files_enabled` | `False` | تعطيل ملفات إعادة المحاولة (.retry) |
| `interpreter_python` | `auto_silent` | تحديد مترجم بايثون تلقائياً |
| `become` | `False` | تعطيل الصلاحيات الجذرية افتراضياً |

---

## 9. ✅ الاختبار النهائي لـ Ansible

```bash
ansible localhost -m setup
```

هذا الأمر يعرض جميع حقائق (facts) النظام المحلي لتأكيد أن Ansible يعمل بشكل صحيح.

---

## 10. 📋 أوامر إدارة Ansible الأساسية

| العملية | الأمر | الوصف |
|---------|-------|-------|
| عرض الإصدار | `ansible --version` | عرض إصدار Ansible المثبت |
| اختبار الاتصال | `ansible all -m ping` | اختبار الاتصال مع جميع المضيفين |
| عرض الأجهزة | `ansible-inventory --list` | عرض جميع المضيفين في المخزون |
| فحص Playbook | `ansible-playbook --syntax-check site.yml` | التحقق من صحة بناء playbook |
| تنفيذ Playbook | `ansible-playbook site.yml` | تشغيل playbook للتنفيذ |
| تنفيذ بصلاحيات Root | `ansible-playbook site.yml --become` | تشغيل playbook بصلاحيات مشرف |
| عرض المجموعات | `ansible-galaxy collection list` | عرض جميع المجموعات المثبتة |
| عرض حقائق النظام | `ansible localhost -m setup` | عرض معلومات النظام المفصلة |

---

## 11. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: أمر add-apt-repository غير موجود

```bash
sudo apt install -y software-properties-common
```

### ❌ مشكلة: تعذر الاتصال بمستودع PPA

```bash
# التحقق من اتصال الإنترنت
ping -c 4 ppa.launchpad.net

# إذا كنت خلف بروكسي، قم بتعيين متغيرات البيئة
export http_proxy=http://proxy.server:port/
export https_proxy=http://proxy.server:port/
```

### ❌ مشكلة: خطأ في مفتاح SSH للمضيف البعيد

```bash
# تعطيل فحص مفتاح SSH مؤقتاً (للسيرفرات المحلية فقط)
ansible all -i inventory/hosts.ini -m ping -o StrictHostKeyChecking=no

# أو قم بتعديل ansible.cfg:
# host_key_checking = False
```

### ❌ مشكلة: رفض الصلاحية (Permission Denied)

```bash
# تنفيذ الأمر بصلاحيات مشرف
ansible-playbook site.yml --become

# أو تعيين become = True في ansible.cfg
```

### ❌ مشكلة: مجموعة غير مثبتة (Collection Not Found)

```bash
# إعادة تثبيت المجموعة الناقصة
ansible-galaxy collection install community.docker --force
```

---

## 12. 🗑️ إزالة Ansible بالكامل

إذا كنت ترغب في إزالة Ansible تمامًا من النظام:

```bash
# إزالة حزمة Ansible
sudo apt-get purge -y ansible

# إزالة التبعيات غير المستخدمة
sudo apt-get autoremove -y

# إضافة مستودع PPA (اختياري)
sudo add-apt-repository --remove ppa:ansible/ansible

# إزالة مجلد المشروع (اختياري)
rm -rf ~/ansible-project
```

---

## 13. ℹ️ المعلومات التقنية

| العنصر | القيمة |
|--------|--------|
| الأداة | Ansible Core |
| لغة التكوين | YAML |
| بروتوكول الاتصال | SSH (للمضيفين البعيدين)، محلي (للسيرفر الحالي) |
| نمط العمل | Agentless (لا يتطلب عميل على السيرفر المستهدف) |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS / 24.04 LTS |
| متطلبات بايثون | Python 3.8+ |
| ملف المخزون الافتراضي | `./inventory/hosts.ini` |
| ملف الإعدادات الافتراضي | `ansible.cfg` |
| المجموعات الأساسية | `community.docker`, `ansible.posix`, `community.general` |
| الموقع الرسمي | https://docs.ansible.com/ |

---

## 14. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | Ansible يعتمد على SSH للاتصال بالسيرفرات البعيدة. تأكد من فتح منفذ SSH (22) في جدار الحماية. | 🔹 معلومات |
| 2 | خيار `--become` يمنح صلاحيات root لتنفيذ الأوامر. استخدمه بحذر فقط عند الحاجة. | 🔴 أمني |
| 3 | ملف `ansible.cfg` يحتوي على إعدادات حساسة. لا تشاركه مع أطراف غير موثوقة. | 🔴 أمني |
| 4 | ملف المخزون (`hosts.ini`) يحتوي على عناوين الخوادم. احمِه من الوصول غير المصرح به. | 🔴 أمني |
| 5 | مجموعات Ansible Galaxy تُحمل من الإنترنت. تأكد من مصداقية المجموعة قبل التثبيت. | 🔹 معلومات |
| 6 | عند إدارة سيرفرات بعيدة، استخدم مفاتيح SSH بدلاً من كلمات المرور لأمان أعلى. | 🔹 معلومات |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Ansible الرسمي:

🔗 https://docs.ansible.com/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
