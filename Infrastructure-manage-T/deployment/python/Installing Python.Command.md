# 🐍 دليل تثبيت Python على Ubuntu Server

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الأداة:** Python 3 - لغة البرمجة الأساسية لتشغيل Odoo وAnsible وأدوات الأتمتة  
> **الإصدارات المدعومة:** Python 3.10, 3.11, 3.12  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [مقدمة عن Python](#-مقدمة-عن-Python)
2. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
3. [الطريقة الأولى: التثبيت عبر مستودعات Ubuntu الرسمية](#-الطريقة-الأولى-التثبيت-عبر-مستودعات-Uubuntu-الرسمية)
4. [الطريقة الثانية: التثبيت عبر مستودع Deadsnakes PPA (للإصدارات الأحدث)](#-الطريقة-الثانية-التثبيت-عبر-مستودع-Deadsnakes-PPA)
5. [التحقق من تثبيت Python](#-التحقق-من-تثبيت-Python)
6. [إنشاء بيئة افتراضية (Virtual Environment)](#-إنشاء-بيئة-افتراضية-Virtual-Environment)
7. [تثبيت الحزم الأساسية عبر pip](#-تثبيت-الحزم-الأساسية-عبر-pip)
8. [إدارة إصدارات Python المتعددة](#-إدارة-إصدارات-Python-المتعددة)
9. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
10. [إزالة Python (اختياري)](#-إزالة-Python-اختياري)
11. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
12. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🎯 مقدمة عن Python

**Python** هي لغة برمجة عالية المستوى تُستخدم على نطاق واسع في تطوير الويب، أتمتة البنية التحتية، تحليل البيانات، والذكاء الاصطناعي. في هذا النظام، تُستخدم Python لتشغيل:

- **Odoo 17/18/19** - إطار عمل تخطيط موارد المؤسسات (ERP)
- **Ansible** - أداة أتمتة إعداد وإدارة السيرفرات
- **أدوات النشر والنقل** - سكريبتات النشر وإدارة الحاويات

### ✅ ما يمكن تشغيله عبر Python في هذا النظام:

| المكون | الغرض |
|--------|-------|
| Odoo Server | تشغيل خادم Odoo 17/18/19 |
| Ansible | أتمتة إعداد السيرفرات والبنية التحتية |
| pip | مدير حزم Python لتثبيت المكتبات والمكونات |
| venv | إنشاء بيئات افتراضية لعزل الحزم عن النظام |

---

## 2. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | نظام تشغيل مدعوم | `cat /etc/os-release` | Ubuntu 22.04 LTS / 24.04 LTS |
| 2 | صلاحيات جذر (sudo) | `id` | — |
| 3 | مساحة قرصية حرة | `df -h /` | 2 جيجابايت على الأقل |
| 4 | اتصال إنترنت | `ping -c 4 archive.ubuntu.com` | — |

---

## 3. 🚀 الطريقة الأولى: التثبيت عبر مستودعات Ubuntu الرسمية

هذه الطريقة تُثبّت إصدار Python المتاح في مستودعات Ubuntu الرسمية (عادةً 3.10 أو 3.12 حسب إصدار Ubuntu).

### الخطوة 1: تحديث النظام

```bash
sudo apt update
sudo apt upgrade -y
```

### الخطوة 2: تثبيت Python 3 ومدير الحزم pip

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
```

### الخطوة 3: تثبيت أدوات البناء الأساسية (لحزم Python التي تتطلب تجميع)

```bash
sudo apt install -y build-essential libssl-dev libffi-dev python3-setuptools
```

### الخطوة 4: التحقق من إصدار Python المثبت

```bash
python3 --version
pip3 --version
```

---

## 4. ⚡ الطريقة الثانية: التثبيت عبر مستودع Deadsnakes PPA (للإصدارات الأحدث)

إذا كنت تحتاج إلى إصدار Python أحدث من المتاح في مستودعات Ubuntu الرسمية (مثل Python 3.11 أو 3.12 على Ubuntu 22.04)، استخدم مستودع Deadsnakes PPA.

### الخطوة 1: تثبيت أداة إضافة المستودعات

```bash
sudo apt install -y software-properties-common
```

### الخطوة 2: إضافة مستودع Deadsnakes PPA

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
```

### الخطوة 3: تثبيت إصدار Python المطلوب

```bash
# لتثبيت Python 3.11
sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev

# لتثبيت Python 3.12
sudo apt install -y python3.12 python3.12-pip python3.12-venv python3.12-dev
```

### الخطوة 4: تعيين الإصدار الافتراضي (اختياري)

```bash
# عرض إصدارات Python المتاحة
ls /usr/bin/python3*

# تعيين إصدار افتراضي (مثال: Python 3.12)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --config python3
```

---

## 5. ✅ التحقق من تثبيت Python

نفذ الأوامر التالية للتحقق من أن Python مثبت ويعمل بشكل صحيح:

```bash
# التحقق من إصدار Python
python3 --version

# التحقق من إصدار pip
pip3 --version

# اختبار تشغيل سكريبت Python بسيط
python3 -c "print('Python works correctly!')"

# التحقق من قدرة Python على استيراد الوحدات الأساسية
python3 -c "import sys; print(f'Python path: {sys.executable}')"
python3 -c "import venv; print('venv module available')"
```

### ✅ النتيجة المتوقعة:

```text
Python 3.12.3
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
Python works correctly!
Python path: /usr/bin/python3
venv module available
```

---

## 6. 📦 إنشاء بيئة افتراضية (Virtual Environment)

تسمح البيئات الافتراضية بعزل حزم Python عن النظام العام لكل مشروع، مما يمنع التعارض بين الإصدارات.

### إنشاء بيئة افتراضية لمشروع Odoo:

```bash
# إنشاء مجلد المشروع
mkdir -p ~/odoo-venv
cd ~/odoo-venv

# إنشاء البيئة الافتراضية
python3 -m venv venv

# تفعيل البيئة الافتراضية
source venv/bin/activate

# التحقق من تفعيل البيئة
which python
which pip
```

### ⚙️ أوامر إدارة البيئة الافتراضية:

| العملية | الأمر | الوصف |
|---------|-------|-------|
| تفعيل البيئة | `source venv/bin/activate` | تفعيل البيئة الافتراضية |
| إلغاء تفعيل البيئة | `deactivate` | الخروج من البيئة الافتراضية والعودة للنظام |
| عرض الحزم المثبتة | `pip list` | عرض جميع الحزم المثبتة في البيئة |
| تثبيت حزمة | `pip install <package>` | تثبيت حزمة Python في البيئة |
| إزالة حزمة | `pip uninstall <package>` | إزالة حزمة Python من البيئة |
| حفظ قائمة الحزم | `pip freeze > requirements.txt` | حفظ قائمة الحزم المثبتة |
| تثبيت من قائمة | `pip install -r requirements.txt` | تثبيت الحزم من ملف المتطلبات |

---

## 7. 📚 تثبيت الحزم الأساسية عبر pip

بعد تفعيل البيئة الافتراضية، ثبّت الحزم الأساسية المطلوبة لـ Odoo وAnsible:

```bash
# تفعيل البيئة الافتراضية أولاً
source ~/odoo-venv/venv/bin/activate

# تثبيت الحزم الأساسية
pip install --upgrade pip
pip install wheel setuptools

# حزم Odoo الأساسية (اختياري - وفقاً لإصدار Odoo)
pip install psycopg2-binary pylint

# حزم Ansible (إذا كنت ستستخدم Ansible)
pip install ansible

# عرض الحزم المثبتة
pip list
```

---

## 8. 🔄 إدارة إصدارات Python المتعددة

إذا كنت بحاجة إلى العمل بإصدارات متعددة من Python على نفس السيرفر:

```bash
# عرض 모든 إصدارات Python المثبتة
ls /usr/bin/python3*

# التحقق من إصدار Python الحالي
python3 --version

# تشغيل إصدار محدد مباشرة
python3.10 --version
python3.11 --version
python3.12 --version

# إنشاء بيئة افتراضية بإصدار محدد
python3.11 -m venv ~/odoo17-venv
python3.12 -m venv ~/odoo19-venv

# تفعيل بيئة محددة
source ~/odoo17-venv/bin/activate
```

---

## 8. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: أمر python3 غير موجود

```bash
# تثبيت Python 3
sudo apt install -y python3
```

### ❌ مشكلة: أمر pip3 غير موجود

```bash
# تثبيت pip لـ Python 3
sudo apt install -y python3-pip
```

### ❌ مشكلة: خطأ في تحميل الحزم (SSL Certificate Error)

```bash
# تثبيت شهادات SSL المحدثة
sudo apt install -y ca-certificates
sudo update-ca-certificates
```

### ❌ مشكلة: خطأ في تجميع حزم Python (Missing Build Tools)

```bash
# تثبيت أدوات البناء الأساسية
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

### ❌ مشكلة: environment not activated

```bash
# تأكد من تفعيل البيئة قبل تثبيت الحزم
source ~/odoo-venv/venv/bin/activate
which python
which pip
```

---

## 10. 🗑️ إزالة Python (اختياري)

إذا كنت ترغب في إزالة Python من النظام:

```bash
# إزالة Python 3 وحزمه المرتبطة
sudo apt-get purge -y python3 python3-pip python3-venv python3-dev

# إزالة التبعيات غير المستخدمة
sudo apt-get autoremove -y

# إزالة بيئات Python الافتراضية (اختياري)
rm -rf ~/odoo-venv
```

> ⚠️ **تحذير:** إزالة Python من نظام Ubuntu قد تؤثر على أدوات النظام التي تعتمد عليه (مثل Ubuntu Software Center، بعض سكريبتات النظام). يُنصح بعدم إزالة Python إلا إذا كان ضرورياً.

---

## 11. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| اللغة | Python 3 |
| مدير الحزم | pip |
| أداة العزل | venv |
| إصدارات Ubuntu المدعومة | 22.04 LTS، 24.04 LTS |
| إصدارات Python الشائعة | 3.10، 3.11، 3.12 |
| المسار التنفيذي الافتراضي | `/usr/bin/python3` |
| مسار حزم النظام | `/usr/lib/python3/dist-packages/` |
| مسار حزم المستخدم | `~/.local/lib/python3.*/site-packages/` |
| مستودع الإصدارات الأحدث | Deadsnakes PPA (`ppa:deadsnakes/ppa`) |

### البنية الداخلية للمجلد:

```
deployment/python/
├── Installing Python.Command.md    # هذا الدليل الشامل والمفصل
```

---

## 12. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | لا تستخدم `sudo pip install` لتثبيت الحزم في النظام العام، استخدم البيئات الافتراضية (venv) بدلاً من ذلك. | 🔴 أمني |
| 2 | Python المثبت عبر apt يتم إدارته بواسطة النظام ولا ينبغي تعديله يدوياً في مجلدات النظام. | 🔴 أمني |
| 3 | البيئات الافتراضية تُعزل الحزم عن النظام، يُنصح باستخدامها لكل مشروع Odoo منفصل. | 🔹 معلومات |
| 4 | عند التثبيت عبر Deadsnakes PPA، تأكد من أن المستودع موثوق ومحدث. | 🔹 معلومات |
| 5 | بعض حزم Python تتطلب أدوات بناء (build-essential) لتجميعها من المصدر. | 🔹 معلومات |
| 6 | تفعيل البيئة الافتراضية يؤثر على جلسة المحطة الحالية فقط، وليس على الجلسات الأخرى. | 🔹 معلومات |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Python الرسمي:

🔗 https://docs.python.org/3/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
