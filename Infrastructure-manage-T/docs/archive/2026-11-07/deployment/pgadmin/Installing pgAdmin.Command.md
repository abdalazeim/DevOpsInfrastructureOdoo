# 🐘 دليل تثبيت pgAdmin 4 على Ubuntu باستخدام Docker

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الأداة:** pgAdmin 4 - واجهة ويب لإدارة PostgreSQL  
> **التخزين:** مجلد مستقل (`/opt/pgadmin/data`) لحفظ الإعدادات وقواعد البيانات والاتصالات  
> **المنفذ:** 5050 (واجهة الويب HTTP)  
> **صورة Docker:** `dpage/pgadmin4:latest`  
> **المستوى:** مشرف نظام / مسؤول قاعدة بيانات  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [مقدمة عن pgAdmin 4](#-مقدمة-عن-pgAdmin-4)
2. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
3. [الطريقة الأولى: التثبيت اليدوي خطوة بخطوة](#-الطريقة-الأولى-التثبيت-اليدوي-خطوة-بخطوة)
4. [التحقق من تشغيل pgAdmin](#-التحقق-من-تشغيل-pgAdmin)
5. [الوصول إلى لوحة التحكم](#-الوصول-إلى-لوحة-التحكم)
6. [ربط pgAdmin بسيرفر PostgreSQL](#-ربط-pgAdmin-بسيرفر-PostgreSQL)
7. [إدارة pgAdmin (تشغيل، إيقاف، إعادة تشغيل، تحديث)](#-إدارة-pgAdmin)
8. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
9. [إزالة pgAdmin بالكامل](#-إزالة-pgAdmin-بشكل-كامل)
10. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
11. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🎯 مقدمة عن pgAdmin 4

**pgAdmin 4** هي أداة إدارة مفتوحة المصدر لقواعد بيانات PostgreSQL tramite واجهة ويب. تتيح إنشاء قواعد البيانات والمستخدمين، وتنفيذ استعلامات SQL، ومراقبة الاتصالات، وإدارة صلاحيات الوصول.

### ✅ ما يمكن إدارةه عبر pgAdmin في هذا النظام:

| المكون | الغرض |
|--------|-------|
| PostgreSQL | إدارة قواعد بيانات Odoo 17/18/19 |
| مستخدمو PostgreSQL | إنشاء وإدارة مستخدمي قواعد البيانات |
| استعلامات SQL | تنفيذ استعلامات مخصصة مباشرة على القاعدة |
| الاتصالات | مراقبة وإدارة اتصالات العملاء بقاعدة البيانات |
| النسخ الاحتياطي | إنشاء واستعادة نسخ احتياطية لقواعد البيانات |

---

## 2. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | Docker Engine | `docker --version` | راجع دليل تثبيت Docker |
| 2 | Docker Compose | `docker compose version` | يُثبّت مع Docker Engine |
| 3 | صلاحيات جذر (sudo) | `id` | — |
| 4 | منفذ 5050 فارغ | `ss -tulnp | grep :5050` | — |
| 5 | مساحة قرصية حرة | `df -h /opt` | 5 جيجابايت على الأقل |

---

## 3. 🚀 الطريقة الأولى: التثبيت اليدوي خطوة بخطوة

اتبع هذه التترتيب exactement لتثبيت pgAdmin 4 على نظام Ubuntu Server باستخدام Docker.

### الخطوة 1: إنشاء مجلد لحفظ بيانات pgAdmin

```bash
sudo mkdir -p /opt/pgadmin/data
```

هذا المجلد سيحفظ جميع إعدادات pgAdmin، الاتصالات المحفوظة، وقواعد بيانات الخوادم المرتبطة.

### الخطوة 2: ضبط صلاحيات المجلد

صورة pgAdmin الرسمية تعمل افتراضيًا بالمستخدم ذي **UID 5050**:

```bash
sudo chown -R 5050:5050 /opt/pgadmin/data
```

### الخطوة 3: تحميل صورة pgAdmin

```bash
sudo docker pull dpage/pgadmin4:latest
```

### الخطوة 4: إنشاء وتشغيل حاوية pgAdmin

> ⚠️ **استبدل البريد وكلمة المرور بالقيم الخاصة بك قبل التنفيذ.**

```bash
sudo docker run -d \
  --name pgadmin \
  --restart unless-stopped \
  -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD='CHANGE_THIS_STRONG_PASSWORD' \
  -v /opt/pgadmin/data:/var/lib/pgadmin \
  dpage/pgadmin4:latest
```

#### جدول خيارات التشغيل (Run Options)

| الخيار | القيمة | الغرض |
|--------|--------|-------|
| `-d` | — | تشغيل الحاوية في الخلفية (Detached mode) |
| `--name` | `pgadmin` | naming الحاوية لسهولة الإدارة |
| `--restart` | `unless-stopped` | إعادة التشغيل التلقائي إلا إذا تم إيقافها يدوياً |
| `-p` | `5050:80` | منفذ واجهة pgAdmin الويب (المضيف:الحاوية) |
| `-e` | `PGADMIN_DEFAULT_EMAIL` | البريد الإلكتروني للمدير الافتراضي |
| `-e` | `PGADMIN_DEFAULT_PASSWORD` | كلمة مرور المدير الافتراضي |
| `-v` | `/opt/pgadmin/data:/var/lib/pgadmin` | تخزين إعدادات pgAdmin في مجلد مستقل على المضيف |

---

## 4. ✅ التحقق من تشغيل pgAdmin

```bash
sudo docker ps --filter name=pgadmin
```

### الخطوة 5: عرض سجلات التشغيل

```bash
sudo docker logs --tail=100 pgadmin
```

---

## 3. 🌐 الوصول إلى لوحة التحكم

افتح متصفح الويب وانتقل إلى:

```
http://SERVER-IP:5050
```

استبدل `SERVER-IP` بعنوان IP الفعلي للسيرفر الخاص بك.

### 🔐 تسجيل الدخول

سجّل الدخول بالبريد وكلمة المرور اللذين حددتهما في الخطوة 4:
- **البريد الإلكتروني:** `admin@example.com` (أو القيمة التي حددتها)
- **كلمة المرور:** `CHANGE_THIS_STRONG_PASSWORD` (أو القيمة التي حددتها)

---

## 6. 🔗 ربط pgAdmin بسيرفر PostgreSQL

من داخل واجهة pgAdmin:

1. اضغط على **Add New Server** (إضافة خادم جديد).
2. في التبويب **General** أدخل اسم الاتصال، مثل `Odoo PostgreSQL`.
3. انتقل إلى التبويب **Connection**.
4. أدخل بيانات PostgreSQL كما في الجدول أدناه:

| الحقل | القيمة | الوصف |
|-------|--------|-------|
| Host name/address | اسم حاوية PostgreSQL أو عنوانها | مثال: `odoo17-db` أو `localhost` |
| Port | `5432` | منفذ PostgreSQL الافتراضي |
| Maintenance database | `postgres` | قاعدة البيانات للصيانة |
| Username | مستخدم PostgreSQL | مثال: `odoo` |
| Password | كلمة مرور PostgreSQL | كلمة مرور المستخدم |

> ⚠️ **مهم:** إذا كانت PostgreSQL في حاوية Docker أخرى، يجب أن تكون الحاويتان على **شبكة Docker مشتركة**، ويُستخدم اسم خدمة PostgreSQL أو اسم الحاوية بدلاً من `localhost`.

### 📋 مثال على اتصال بـ Odoo 17:

| الحقل | القيمة |
|-------|--------|
| Host name/address | `odoo17-db` |
| Port | `5432` |
| Maintenance database | `postgres` |
| Username | `odoo` |
| Password | `odoo17` |

---

## 9. ⚙️ إدارة pgAdmin

### إعادة تشغيل pgAdmin

```bash
sudo docker restart pgadmin
```

### إيقاف pgAdmin

```bash
sudo docker stop pgadmin
```

### تشغيل pgAdmin (بعد الإيقاف)

```bash
sudo docker start pgadmin
```

### متابعة السجلات في الوقت الفعلي

```bash
sudo docker logs -f pgadmin
```

---

## 10. 🔄 تحديث pgAdmin

```bash
# 1. تحميل أحدث صورة
sudo docker pull dpage/pgadmin4:latest

# 2. إيقاف الحاوية الحالية
sudo docker stop pgadmin

# 3. حذف الحاوية الحالية (البيانات محفوظة في المجلد /opt/pgadmin/data)
sudo docker rm pgadmin

# 4. تشغيل الحاوية الجديدة بنفس الإعدادات
sudo docker run -d \
  --name pgadmin \
  --restart unless-stopped \
  -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD='CHANGE_THIS_STRONG_PASSWORD' \
  -v /opt/pgadmin/data:/var/lib/pgadmin \
  dpage/pgadmin4:latest
```

> 💡 **ملاحظة:** سيستخدم pgAdmin نفس المجلد `/opt/pgadmin/data` ويحتفظ بجميع الإعدادات والاتصالات المحفوظة.

---

## 8. ✅ التحقق النهائي

```bash
# التحقق من حالة حاوية pgAdmin
sudo docker inspect pgadmin --format '{{.State.Status}}'

# التحقق من مجلد البيانات
ls -la /opt/pgadmin/data

# التحقق من أن المنفذ 5050 مفتوح
sudo ss -tulnp | grep 5050
```

---

## 7. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: تعذر الوصول إلى لوحة التحكم (http://SERVER-IP:5050)

```bash
# التحقق من أن الحاوية تعمل
sudo docker ps --filter name=pgadmin

# التحقق من أن المنفذ 5050 مفتوح
sudo ss -tulnp | grep :5050

# فحص السجلات لمعرفة الأخطاء
sudo docker logs --tail=50 pgadmin

# إذا كانت الحاوية متوقفة، أعد تشغيلها
sudo docker start pgadmin
```

### ❌ مشكلة: منفذ 5050 مضبوط بالفعل من قبل خدمة أخرى

```bash
# اكتشاف الخدمة التي تستخدم المنفذ
sudo ss -tulnp | grep :5050

# إذا كان المنفذ مستخدماً، يمكنك تغيير المنفذ في أمر التشغيل
# مثال: -p 5051:80 بدلاً من -p 5050:80
```

### ❌ مشكلة: عدم القدرة على الاتصال بـ PostgreSQL من pgAdmin

```bash
# التحقق من أن حاوية PostgreSQL تعمل
sudo docker ps --filter name=db

# التحقق من أن الحاويتان على شبكة مشتركة
sudo docker network ls
sudo docker network inspect <اسم_الشبكة>

# إذا كانت PostgreSQL في حاوية أخرى، استخدم اسم الحاوية بدلاً من localhost
# مثال: Host name/address = odoo17-db
```

### ❌ مشكلة: خطأ في صلاحيات مجلد البيانات

```bash
# إعادة ضبط الصلاحيات للمستخدم 5050
sudo chown -R 5050:5050 /opt/pgadmin/data
sudo chmod -R 700 /opt/pgadmin/data
```

---

## 9. 🗑️ إزالة pgAdmin بالكامل

إذا كنت ترغب في إزالة pgAdmin تمامًا من النظام:

```bash
# 1. إيقاف الحاوية
sudo docker stop pgadmin

# 2. حذف الحاوية
sudo docker rm pgadmin

# 3. حذف الصورة (اختياري)
sudo docker rmi dpage/pgadmin4:latest

# 4. حذف مجلد البيانات (تحذير: سيحذف جميع الإعدادات والاتصالات)
sudo rm -rf /opt/pgadmin/data
```

> 🔴 **تحذير حاسم:** حذف المجلد `/opt/pgadmin/data` سيحذف **جميع** إعدادات pgAdmin، الاتصالات المحفوظة، وبيانات الخوادم المرتبطة بشكل دائم ولا يمكن استعادتها إلا إذا كان لديك نسخة احتياطية.

---

## 10. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| الصورة | `dpage/pgadmin4:latest` |
| اسم الحاوية | `pgadmin` |
| مجلد البيانات على المضيف | `/opt/pgadmin/data` |
| مسار البيانات داخل الحاوية | `/var/lib/pgadmin` |
| منفذ واجهة الويب | `5050` (HTTP) |
| منفذ الحاوية الداخلي | `80` |
| سياسة إعادة التشغيل | `unless-stopped` |
| متغير البريد الإلكتروني | `PGADMIN_DEFAULT_EMAIL` |
| متغير كلمة المرور | `PGADMIN_DEFAULT_PASSWORD` |
| معرف المستخدم (UID) داخل الحاوية | `5050` |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS / 24.04 LTS |
| متطلبات Docker | Docker Engine |

### البنية الداخلية للمجلد

```
deployment/pgadmin/
├── Installing pgAdmin.Command.md    # هذا الدليل الشامل والمفصل
```

---

## 11. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | لا تستخدم كلمة المرور الافتراضية في بيئة الإنتاج. غيّرها فورًا بعد التثبيت الأول. | 🔴 أمني |
| 2 | لا expose المنفذ 5050 مباشرة للإنترنت دون HTTPS وحماية مناسبة (جدار ناري، VPN، أو بروكسي عكسي مثل Traefik). | 🔴 أمني |
| 3 | لا تحذف مجلد البيانات `/opt/pgadmin/data` عند إعادة إنشاء الحاوية، وإلا ستفقد جميع الإعدادات والاتصالات. | 🔴 هام |
| 4 | احتفظ بنسخة احتياطية من مجلد `/opt/pgadmin/data` قبل أي تحديث أو تغيير جوهري. | 🔹 معلومات |
| 5 | إذا كانت PostgreSQL في حاوية Docker أخرى، تأكد من أن الحاويتان على شبكة Docker مشتركة. | 🔹 معلومات |
| 6 | pgAdmin يعمل بمستخدم ذي UID 5050 افتراضيًا. تأكد من ضبط صلاحيات مجلد البيانات بشكل صحيح. | 🔹 معلومات |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق pgAdmin الرسمي:

🔗 https://www.pgadmin.org/docs/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
