# 🔧 دليل تثبيت Jenkins على Ubuntu Server باستخدام Docker

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الأداة:** Jenkins CI/CD Server (LTS - JDK 21)  
> **التخزين:** Docker Volume مستقل (`jenkins_home`) لحفظ الإعدادات والمستخدمين والمهام والإضافات  
> **المنفذ:** 8080 (واجهة الويب)  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [مقدمة عن Jenkins](#-مقدمة-عن-Jenkins)
2. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
3. [الطريقة الأولى: التثبيت اليدوي خطوة بخطوة](#-الطريقة-الأولى-التثبيت-اليدوي-خطوة-بخطوة)
4. [التحقق من تشغيل Jenkins](#-التحقق-من-تشغيل-Jenkins)
5. [الوصول إلى لوحة التحكم](#-الوصول-إلى-لوحة-التحكم)
6. [إدارة Jenkins (تشغيل، إيقاف، إعادة تشغيل، تحديث)](#-إدارة-Jenkins)
7. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
8. [إزالة Jenkins بالكامل](#-إزالة-Jenkins-بشكل-كامل)
9. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
10. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🎯 مقدمة عن Jenkins

**Jenkins** هو خادم أتمتة مفتوح المصدر يستخدم للتكامل المستمر والنشر المستمر (CI/CD). يسمح بتنظيم عمليات البناء والاختبار والنشر تلقائياً عبر الإضافات (Plugins) والمكتبات المشتركة (Shared Libraries).

### ✅ ما يمكن إدارةه عبر Jenkins في هذا النظام:

| المكون | الغرض |
|--------|-------|
| Docker | بناء ونشر صور Docker وحاويات |
| Traefik | إدارة البروكسي العكسي والنشر عبر HTTPS |
| Odoo 17/18/19 | نشر نسخ Odoo متعددة تلقائياً |
| PostgreSQL | إدارة نسخ احتياطية لقواعد البيانات |
| Ansible | تشغيل أنابيب الأتمتة عبر أنsible Playbooks |

---

## 2. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | Docker Engine | `docker --version` | راجع دليل تثبيت Docker |
| 2 | Docker Compose | `docker compose version` | يُثبّت مع Docker Engine |
| 3 | صلاحيات جذر (sudo) | `id` | — |
| 4 | منفذ 8080 فارغ | `ss -tulnp | grep :8080` | — |
| 5 | مساحة قرصية حرة | `df -h /var` | 10 جيجابايت على الأقل لـ `jenkins_home` |

---

## 3. 🚀 الطريقة الأولى: التثبيت اليدوي خطوة بخطوة

اتبع هذه التترتيب exactement لتثبيت Jenkins على نظام Ubuntu Server باستخدام Docker.

### الخطوة 1: إنشاء Docker Volume لحفظ بيانات Jenkins

```bash
sudo docker volume create jenkins_home
```

هذا الحجم سيحفظ جميع إعدادات Jenkins، المستخدمين، المهام (Jobs)، والإضافات (Plugins) حتى إذا تم حذف الحاوية وإعادة إنشائها.

### الخطوة 2: تحميل صورة Jenkins الرسمية (LTS - JDK 21)

```bash
sudo docker pull jenkins/jenkins:lts-jdk21
```

### الخطوة 3: إنشاء وتشغيل حاوية Jenkins

```bash
sudo docker run -d \
  --name jenkins \
  --restart unless-stopped \
  -p 8080:8080 \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
```

#### جدول خيارات التشغيل (Run Options)

| الخيار | القيمة | الغرض |
|--------|--------|-------|
| `-d` | — | تشغيل الحاوية في الخلفية (Detached mode) |
| `--name` | `jenkins` | naming الحاوية لسهولة الإدارة |
| `--restart` | `unless-stopped` | إعادة التشغيل التلقائي إلا إذا تم إيقافها يدوياً |
| `-p` | `8080:8080` | منفذ واجهة Jenkins الويب |
| `-v` | `jenkins_home:/var/jenkins_home` | تخزين إعدادات وبيانات Jenkins في حجم Docker مستقل |

> ⚠️ **ملاحظة:** لم نفتح منفذ الوكلاء (50000) لأنه غير مطلوب في التشغيل الأساسي. يمكن إضافته لاحقاً إذا لزم الأمر (`-p 50000:50000`).

---

## 4. ✅ التحقق من تشغيل Jenkins

```bash
sudo docker ps --filter name=jenkins
```

### الخطوة 5: عرض سجلات Jenkins

```bash
sudo docker logs --tail=100 jenkins
```

### الخطوة 6: استخراج كلمة المرور الأولية للمدير

```bash
sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

> 🔑 **احتفظ بكلمة المرور** لاستخدامها عند الدخول الأول إلى لوحة التحكم.

---

## 3. 🌐 الوصول إلى لوحة التحكم

افتح متصفح الويب وانتقل إلى:

```
http://SERVER-IP:8080
```

استبدل `SERVER-IP` بعنوان IP الفعلي للسيرفر الخاص بك.

### 🔐 الإعداد الأول (First Login)

عند الدخول الأول إلى لوحة Jenkins:

1. أدخل **كلمة المرور الأولية** التي استخرجتها في الخطوة 6.
2. اختر **Install suggested plugins** (تثبيت الإضافات المقترحة).
3. أنشئ حساب **Administrator** (اسم مستخدم وكلمة مرور قوية).
4. أكمل إعداد Jenkins (رابط الجسر URL، إلخ).

---

## 6. ⚙️ إدارة Jenkins

### إعادة تشغيل Jenkins

```bash
sudo docker restart jenkins
```

### إيقاف Jenkins

```bash
sudo docker stop jenkins
```

### تشغيل Jenkins (بعد الإيقاف)

```bash
sudo docker start jenkins
```

### متابعة السجلات في الوقت الفعلي

```bash
sudo docker logs -f jenkins
```

### الدخول إلى Terminal داخل الحاوية

```bash
sudo docker exec -it jenkins bash
```

### تحديث Jenkins إلى أحدث إصدار

```bash
# 1. تحميل أحدث صورة LTS
sudo docker pull jenkins/jenkins:lts-jdk21

# 2. إيقاف الحاوية الحالية
sudo docker stop jenkins

# 3. حذف الحاوية الحالية (البيانات محفوظة في الحجم jenkins_home)
sudo docker rm jenkins

# 4. تشغيل الحاوية الجديدة بنفس الإعدادات
sudo docker run -d \
  --name jenkins \
  --restart unless-stopped \
  -p 8080:8080 \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
```

> 💡 **ملاحظة:** سيستخدم Jenkins نفس الحجم `jenkins_home` ويحتفظ بجميع البيانات والإعدادات والمستخدمين والمهام والإضافات.

---

## 7. ✅ التحقق النهائي

```bash
# التحقق من حالة حاوية Jenkins
sudo docker inspect jenkins --format '{{.State.Status}}'

# التحقق من حجم البيانات
sudo docker volume inspect jenkins_home

# التحقق من أن المنفذ 8080 مفتوح
sudo ss -tulnp | grep 8080
```

---

## 8. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: تعذر الوصول إلى لوحة التحكم (http://SERVER-IP:8080)

```bash
# التحقق من أن الحاوية تعمل
sudo docker ps --filter name=jenkins

# التحقق من أن المنفذ 8080 مفتوح
sudo ss -tulnp | grep :8080

# فحص السجلات لمعرفة الأخطاء
sudo docker logs --tail=50 jenkins

# إذا كانت الحاوية متوقفة، أعد تشغيلها
sudo docker start jenkins
```

### ❌ مشكلة: منفذ 8080 مضبوط بالفعل من قبل خدمة أخرى

```bash
# اكتشاف الخدمة التي تستخدم المنفذ
sudo ss -tulnp | grep :8080

# إذا كان المنفذ مستخدماً، يمكنك تغيير المنفذ في أمر التشغيل
# مثال: -p 8081:8080 بدلاً من -p 8080:8080
```

### ❌ مشكلة: forgot كلمة مرور المسؤول

```bash
# إعادة تعيين كلمة مرور المسؤول عبر سطر الأوامر داخل الحاوية
sudo docker exec -it jenkins bash

# داخل الحاوية، نفذ:
# java -jar jenkins-cli.jar -s http://localhost:8080/ who-am-i --auth admin:your_password
```

---

## 9. 🗑️ إزالة Jenkins بالكامل

إذا كنت ترغب في إزالة Jenkins تمامًا من النظام:

```bash
# 1. إيقاف الحاوية
sudo docker stop jenkins

# 2. حذف الحاوية
sudo docker rm jenkins

# 3. حذف الصورة (اختياري)
sudo docker rmi jenkins/jenkins:lts-jdk21

# 4. حذف حجم البيانات (تحذير: سيحذف جميع إعدادات ومستخدمين ومهام Jenkins)
sudo docker volume rm jenkins_home
```

> 🔴 **تحذير حاسم:** حذف حجم `jenkins_home` سيحذف **جميع** إعدادات Jenkins، المستخدمين، المهام، والإضافات بشكل دائم ولا يمكن استعادتها إلا إذا كان لديك نسخة احتياطية.

---

## 10. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| الصورة | `jenkins/jenkins:lts-jdk21` |
| اسم الحاوية | `jenkins` |
| اسم الحجم (Volume) | `jenkins_home` |
| منفذ واجهة الويب | `8080` (HTTP) |
| سياسة إعادة التشغيل | `unless-stopped` |
| مسار البيانات داخل الحاوية | `/var/jenkins_home` |
| مسار ملف كلمة المرور الأولية | `/var/jenkins_home/secrets/initialAdminPassword` |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS / 24.04 LTS |
| متطلبات Docker | Docker Engine |

### البنية الداخلية للمجلد

```
deployment/jenkins/
├── Installing Jenkins.Command.md    # هذا الدليل الشامل والمفصل
```

---

## 11. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | لا تعرض المنفذ 8080 مباشرة للإنترنت دون HTTPS وحماية مناسبة (جدار ناري، VPN، أو بروكسي عكسي مثل Traefik). | 🔴 أمني |
| 2 | لا تربط Docker Socket (`/var/run/docker.sock`) مع Jenkins إلا بعد تصميم صلاحيات آمنة؛ لأنه يمنح صلاحيات واسعة على الخادم. | 🔴 أمني |
| 3 | حجم `jenkins_home` يحفظ جميع إعدادات ومستخدمين ومهام وإضافات Jenkins. لا تحذفه إلا إذا كنت تريد إعادة الضبط الكامل. | 🔴 هام |
| 4 | احتفظ بنسخة احتياطية من `jenkins_home` قبل أي تحديث أو تغيير جوهري. | 🔹 معلومات |
| 5 | كلمة مرور المسؤول يجب أن تكون قوية وتحتوي على أحرف كبيرة وصغيرة وأرقام ورموز. | 🔴 أمني |
| 6 | منفذ الوكلاء (50000) غير مفتوح افتراضياً. افتحه فقط إذا كنت ستستخدم وكلاء Jenkins بعيدين. | 🔹 معلومات |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Jenkins الرسمي:

🔗 https://www.jenkins.io/doc/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
