# 📦 دليل تثبيت Portainer CE على Ubuntu

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الإصدار:** Portainer CE LTS  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **المنافذ:** 8000 (Edge Agent) و 9443 (لوحة التحكم عبر HTTPS)  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
2. [الطريقة الأولى: التثبيت اليدوي خطوة بخطوة](#-الطريقة-الأولى-التثبيت-اليدوي-خطوة-بخطوة)
3. [التحقق من تشغيل Portainer](#-التحقق-من-تشغيل-Portainer)
4. [الوصول إلى لوحة التحكم](#-الوصول-إلى-لوحة-التحكم)
5. [إدارة Portainer (تشغيل، إيقاف، إعادة تشغيل، تحديث)](#-إدارة-Portainer)
6. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
7. [إزالة Portainer بالكامل](#-إزالة-Portainer-بشكل-كامل)
8. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
9. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | Docker Engine | `docker --version` | راجع دليل تثبيت Docker |
| 2 | Docker Compose | `docker compose version` | يُثبّت مع Docker Engine |
| 3 | صلاحيات جذر (sudo) | `id` | — |
| 4 | منفذ 9443 فارغ | `ss -tulnp | grep :9443` | — |
| 5 | منفذ 8000 فارغ | `ss -tulnp | grep :8000` | — |

---

## 2. 🚀 الطريقة الأولى: التثبيت اليدوي خطوة بخطوة

اتبع هذه التترتيب exactement لتثبيت Portainer CE بشكل آمن.

### الخطوة 1: إنشاء Docker Volume لحفظ بيانات Portainer

```bash
sudo docker volume create portainer_data
```

هذا الحجم سيحفظ جميع إعدادات Portainer، المستخدمين، والبيانات حتى إذا تم حذف الحاوية وإعادة إنشائها.

### الخطوة 2: تحميل صورة Portainer CE (الإصدار طويل الأمد LTS)

```bash
sudo docker pull portainer/portainer-ce:lts
```

### الخطوة 3: إنشاء وتشغيل حاوية Portainer

```bash
sudo docker run -d \
  --name portainer \
  --restart=always \
  -p 8000:8000 \
  -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts
```

#### جدول خيارات التشغيل (Run Options)

| الخيار | القيمة | الغرض |
|--------|--------|-------|
| `-d` | — | تشغيل الحاوية في الخلفية (Detached mode) |
| `--name` | `portainer` | naming الحاوية لسهولة الإدارة |
| `--restart` | `always` | إعادة التشغيل التلقائي عند توقف الحاوية أو إعادة تشغيل النظام |
| `-p` | `8000:8000` | منفذ Edge Agent للاتصال بالعوامل البعيدة |
| `-p` | `9443:9443` | منفذ لوحة التحكم عبر HTTPS (أمين) |
| `-v` | `/var/run/docker.sock:/var/run/docker.sock` | مشاركة م socket Docker مع الحاوية لإدارة الحاويات الأخرى |
| `-v` | `portainer_data:/data` | تخزين إعدادات وبيانات Portainer في حجم Docker |

### الخطوة 4: التحقق من تشغيل Portainer

```bash
sudo docker ps --filter name=portainer
```

### الخطوة 5: فحص سجلات Portainer

```bash
sudo docker logs --tail=100 portainer
```

### الخطوة 6: التحقق من المنافذ

```bash
sudo ss -tulnp | grep -E ':9443|:8000'
```

---

## 3. 🌐 الوصول إلى لوحة التحكم

افتح متصفح الويب وانتقل إلى:

```
https://SERVER-IP:9443
```

استبدل `SERVER-IP` بعنوان IP الفعلي للسيرفر الخاص بك.

### 🔐 الإعداد الأول (First Login)

عند أول دخول إلى لوحة التحكم:

1. سيُطلب منك إنشاء حساب **المدير (Admin)** وكلمة مرور قوية.
2. اختر **Docker** كبيئة إدارة محلية.
3. احفظ بيانات الدخول في مكان آمن.

---

## 4. ⚙️ إدارة Portainer

### إعادة تشغيل Portainer

```bash
sudo docker restart portainer
```

### إيقاف Portainer

```bash
sudo docker stop portainer
```

### تشغيل Portainer (بعد الإيقاف)

```bash
sudo docker start portainer
```

### عرض السجلات في الوقت الفعلي

```bash
sudo docker logs -f portainer
```

### تحديث Portainer إلى أحدث إصدار

```bash
# 1. تحميل أحدث صورة
sudo docker pull portainer/portainer-ce:lts

# 2. إيقاف الحاوية الحالية
sudo docker stop portainer

# 3. حذف الحاوية الحالية (البيانات محفوظة في الحجم portainer_data)
sudo docker rm portainer

# 4. تشغيل الحاوية الجديدة بنفس الإعدادات
sudo docker run -d \
  --name portainer \
  --restart=always \
  -p 8000:8000 \
  -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts
```

---

## 5. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: تعذر الوصول إلى لوحة التحكم (https://SERVER-IP:9443)

```bash
# التحقق من أن الحاوية تعمل
sudo docker ps --filter name=portainer

# التحقق من أن المنفذ 9443 مفتوح
sudo ss -tulnp | grep :9443

# فحص السجلات لمعرفة الأخطاء
sudo docker logs --tail=50 portainer

# إذا كانت الحاوية متوقفة، أعد تشغيلها
sudo docker start portainer
```

### ❌ مشكلة: منفذ 9443 أو 8000 مضبوط بالفعل من قبل خدمة أخرى

```bash
# اكتشاف الخدمة التي تستخدم المنفذ
sudo ss -tulnp | grep -E ':9443|:8000'

# إذا كان المنفذ مستخدماً، يمكنك تغيير المنفذ في أمر التشغيل
# مثال: -p 9444:9443 بدلاً من -p 9443:9443
```

### ❌ مشكلة: عدم القدرة على الاتصال بـ Docker Socket

```bash
# التحقق من وجود ملف Socket Docker
ls -la /var/run/docker.sock

# التحقق من صلاحيات المستخدم
ls -la /var/run/docker.sock | awk '{print $1}'

# إذا لم يكن الملف موجوداً، تأكد من أن Docker Engine يعمل
sudo systemctl start docker
sudo systemctl status docker
```

### ❌ مشكلة: فقدان البيانات بعد إعادة إنشاء الحاوية

تأكد من استخدام الحجم `portainer_data` في الأمر `-v portainer_data:/data`. البيانات تُخزّن في هذا الحجم وليس داخل الحاوية نفسها.

---

## 6. 🗑️ إزالة Portainer بالكامل

إذا كنت ترغب في إزالة Portainer تمامًا من النظام:

```bash
# 1. إيقاف الحاوية
sudo docker stop portainer

# 2. حذف الحاوية
sudo docker rm portainer

# 3. حذف الصورة (اختياري)
sudo docker rmi portainer/portainer-ce:lts

# 4. حذف حجم البيانات (تحذير: سيحذف جميع إعدادات ومستخدمي Portainer)
sudo docker volume rm portainer_data
```

> 🔴 **تحذير حاسم:** حذف حجم `portainer_data` سيحذف **جميع** إعدادات Portainer، المستخدمين، والبيانات بشكل دائم ولا يمكن استعادتها إلا إذا كان لديك نسخة احتياطية.

---

## 7. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| الصورة | `portainer/portainer-ce:lts` |
| اسم الحاوية | `portainer` |
| اسم الحجم (Volume) | `portainer_data` |
| منفذ لوحة التحكم | `9443` (HTTPS) |
| منفذ Edge Agent | `8000` |
| سياسة إعادة التشغيل | `always` |
| مسار Docker Socket | `/var/run/docker.sock` |
| مسار البيانات داخل الحاوية | `/data` |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS / 24.04 LTS |
| متطلبات Docker | Docker Engine + Docker Compose |

### البنية الداخلية للمجلد

```
deployment/portainer/
├── Installing Portainer.Command.md    # هذا الدليل الشامل والمفصل
```

---

## 8. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | حجم `portainer_data` يحفظ جميع إعدادات ومستخدمي Portainer. لا تحذفه إلا إذا كنت تريد إعادة الضبط الكامل. | 🔴 هام |
| 2 | منفذ 9443 يستخدم HTTPS. تأكد من فتح جدار الحماية (UFW) لهذا المنفذ إذا كنت تصل عن بعد. | 🔹 معلومات |
| 3 | منفذ 8000 يستخدم لـ Edge Agent لإدارةustos Docker البعيدة. أغلقه إذا لم تحتاجه. | 🔹 معلومات |
| 4 | 참여 Docker Socket (`/var/run/docker.sock`) يمنح Portainer صلاحيات واسعة على Docker. تأكد من أن فقط المستخدمين الموثوقين يمكنهم الوصول إلى Portainer. | 🔴 أمني |
| 5 | عند تحديث Portainer، البيانات محفوظة في الحجم `portainer_data` ولن تُفقد. | 🔹 معلومات |
| 6 | كلمة مرور المدير يجب أن تكون قوية وتحتوي على أحرف كبيرة وصغيرة وأرقام ورموز. | 🔴 أمني |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Portainer الرسمي:

🔗 https://docs.portainer.io/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
