# 🐋 دليل تثبيت Docker Engine و Docker Compose على Ubuntu

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **المكونات:** Docker Engine CE + Docker Compose V2 + Docker Buildx  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
2. [الطريقة الأولى: التثبيت اليدوي خطوة بخطوة](#-الطريقة-الأولى-التثبيت-اليدوي-خطوة-بخطوة)
3. [التحقق النهائي من التثبيت](#-التحقق-النهائي-من-التثبيت)
4. [إدارة خدمة Docker](#-إدارة-خدمة-Docker)
5. [إدارة الموارد (حاويات، صور، شبكات، أحجام)](#-إدارة-الموارد)
6. [تنظيف Docker من الموارد غير المستخدمة](#-تنظيف-Docker-من-الموارد-غير-المستخدمة)
7. [إزالة Docker بالكامل من النظام](#-إزالة-Docker-بشكل-كامل-من-النظام)
8. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
9. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
10. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | نظام تشغيل مدعوم | `cat /etc/os-release` | Ubuntu 22.04 LTS / 24.04 LTS |
| 2 | صلاحيات جذر (sudo) | `id` | — |
| 3 | مساحة قرصية حرة | `df -h /` | 5 جيجابايت على الأقل |
| 4 | اتصال إنترنت | `ping -c 4 google.com` | — |

### ✅ اختبار أن Docker يعمل بعد التثبيت

```bash
sudo docker run hello-world
```

---

## 2. 🚀 الطريقة الأولى: التثبيت اليدوي خطوة بخطوة

اتبع هذه التترتيب exactamente لتثبيت Docker Engine بشكل آمن ورسمي من المستودع الرسمي.

### الخطوة 1: تحديث النظام وتثبيت المتطلبات الأساسية

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
```

### الخطوة 2: إنشاء مجلد مفاتيح Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

### الخطوة 3: إضافة مفتاح GPG الرسمي الخاص بـ Docker

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc
```

### الخطوة 4: إضافة مستودع Docker الرسمي إلى النظام

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" |
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### الخطوة 5: تحديث قائمة الحزم

```bash
sudo apt update
```

### الخطوة 6: تثبيت Docker Engine والمكونات الأساسية

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### جدول المكونات المثبتة

| المكون | الغرض |
|--------|-------|
| `docker-ce` | محرك Docker الأساسي (Community Edition) |
| `docker-ce-cli` | واجهة سطر الأوامر (CLI) للتفاعل مع Docker |
| `containerd.io` | تشغيل وإدارة دورة حياة الحاويات |
| `docker-buildx-plugin` | بناء صور Docker متقدمة ودعم multiple architectures |
| `docker-compose-plugin` | إدارة تطبيقات Docker متعددة الحاويات عبر ملف compose |

### الخطوة 7: تشغيل Docker وتفعيله تلقائيًا عند إقلاع النظام

```bash
sudo systemctl enable --now docker
```

### الخطوة 8: التحقق من حالة خدمة Docker

```bash
sudo systemctl status docker --no-pager
```

**النتيجة المتوقعة:** حالة الخدمة يجب أن تكون `active (running)` باللون الأخضر.

### الخطوة 9: التحقق من إصدار Docker

```bash
sudo docker version
```

### الخطوة 10: التحقق من Docker Compose

```bash
sudo docker compose version
```

### الخطوة 11: اختبار تشغيل حاوية Docker

```bash
sudo docker run hello-world
```

إذا ظهرت رسالة ترحيب من Docker، فالتركيب ناجح.

### الخطوة 12: السماح للمستخدم بتشغيل Docker دون sudo (اختياري)

```bash
sudo usermod -aG docker "$USER"
```

> ⚠️ **تنبيه أمني:** مجموعة `docker` تمنح المستخدم صلاحيات واسعة تقارب صلاحيات Root. يجب تسجيل الخروج ثم الدخول مجددًا لتفعيل العضوية، أو تنفيذ الأمر `newgrp docker` لتفعيلها فورًا.

---

## 3. ✅ التحقق النهائي من التثبيت

نفذ الأوامر التالية للتحقق من أن كل شيء يعمل بشكل صحيح:

```bash
# التحقق من الإصدارات
docker --version
docker compose version

# التحقق من حالة الخدمة
sudo systemctl is-active docker

# معلومات Docker المفصلة
sudo docker info

# عرض جميع الحاويات
sudo docker ps -a
```

---

## 4. ⚙️ إدارة خدمة Docker

| العملية | الأمر | الوصف |
|---------|-------|-------|
| تشغيل الخدمة | `sudo systemctl start docker` | بدء خدمة Docker فورًا |
| إيقاف الخدمة | `sudo systemctl stop docker` | إيقاف خدمة Docker |
| إعادة تشغيل الخدمة | `sudo systemctl restart docker` | إعادة تشغيل الخدمة |
| تفعيل التشغيل التلقائي | `sudo systemctl enable docker` | تشغيل Docker عند إقلاع النظام |
| تعطيل التشغيل التلقائي | `sudo systemctl disable docker` | منع Docker من التشغيل التلقائي |
| فحص الحالة | `sudo systemctl status docker` | عرض حالة الخدمة الحالية |
| عرض السجلات المباشرة | `sudo journalctl -u docker -f` | مراقبة سجلات Docker في الوقت الفعلي |

---

## 5. 📦 إدارة الموارد (حاويات، صور، شبكات، أحجام)

### 🔹 الحاويات (Containers)

```bash
# عرض جميع الحاويات (تشغيل ومتوقف)
sudo docker ps -a

# تشغيل حاوية متوقفة
sudo docker start <اسم_الحاوية>

# إيقاف حاملة عاملة
sudo docker stop <اسم_الحاوية>

# إعادة تشغيل حاوية
sudo docker restart <اسم_الحاوية>

# حذف حاوية متوقفة
sudo docker rm <اسم_الحاوية>

# حذف حاوية قسراً (حتى إذا كانت تعمل)
sudo docker rm -f <اسم_الحاوية>

# عرض سجلات حاوية في الوقت الفعلي
sudo docker logs -f <اسم_الحاوية>

# عرض سجلات آخر 50 سطر
sudo docker logs --tail 50 <اسم_الحاوية>
```

### 🔹 الصور (Images)

```bash
# عرض جميع الصور المحملة محليًا
sudo docker images

# حذف صورة غير مستخدمة
sudo docker rmi <اسم_الصورة>

# حذف صورة قسراً
sudo docker rmi -f <اسم_الصورة>

# سحب صورة من Docker Hub
sudo docker pull <اسم_الصورة>:<الوسم>

# فحص تفاصيل صورة
sudo docker inspect <اسم_الصورة>
```

### 🔹 الشبكات (Networks)

```bash
# عرض جميع الشبكات
sudo docker network ls

# إنشاء شبكة جديدة من نوع bridge
sudo docker network create --driver bridge <اسم_الشبكة>

# فحص تفاصيل شبكة
sudo docker network inspect <اسم_الشبكة>

# حذف شبكة غير مستخدمة
sudo docker network rm <اسم_الشبكة>
```

### 🔹 الأحجام (Volumes)

```bash
# عرض جميع أحجام Docker
sudo docker volume ls

# فحص تفاصيل حجم
sudo docker volume inspect <اسم_الحجم>

# إنشاء حجم جديد
sudo docker volume create <اسم_الحجم>

# حذف حجم غير مستخدم
sudo docker volume rm <اسم_الحجم>

# حذف جميع الأحجام غير المرتبطة بأي حاوية
sudo docker volume prune
```

---

## 6. 🧹 تنظيف Docker من الموارد غير المستخدمة

```bash
# تنظيف جميع الموارد غير المستخدمة (حاويات متوقفة، صور غير مرتبطة، شبكات غير مستخدمة)
sudo docker system prune

# تنظيف شامل بما في ذلك جميع الصور غير المستخدمة
sudo docker system prune -a

# تنظيف شامل incluyendo الأحجام غير المستخدمة
sudo docker system prune -a --volumes

# عرض استخدام القرص من قبل Docker
sudo docker system df
```

> ⚠️ **تحذير:** الأمر `docker system prune -a --volumes` سيحذف جميع الصور غير المستخدمة والأحجام، بما في ذلك قواعد بيانات Odoo إذا كانت مخزنة في أحجام Docker وغير مرتبطة بحاوية تعمل.

---

## 7. 🗑️ إزالة Docker بالكامل من النظام

إذا كنت ترغب في إزالة Docker تمامًا من النظام:

```bash
# 1. إيقاف وتعطيل خدمة Docker
sudo systemctl stop docker
sudo systemctl disable docker

# 2. إزالة حزم Docker
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3. إزالة التبعيات غير المستخدمة
sudo apt-get autoremove -y

# 4. إزالة ملفات التكوين والبيانات
sudo rm -rf /var/lib/docker
sudo rm -rf /etc/docker
sudo rm -rf /etc/apt/sources.list.d/docker.list
sudo rm -rf /etc/apt/keyrings/docker.asc

# 5. إزالة مجموعة docker من النظام (اختياري)
sudo groupdel docker
```

> 🔴 **تحذير حاسم:** إزالة المجلد `/var/lib/docker` ستحذف **جميع** الصور والحاويات والأحجام والشبكات بشكل دائم ولا يمكن استعادتها إلا إذا كان لديك نسخ احتياطية.

---

## 8. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: أمر docker غير موجود بعد التثبيت

```bash
# تأكد من أن المسار مضاف لمتغيرات البيئة
export PATH=$PATH:/usr/bin/docker

# أو أعد تشغيل المحطة
exec $SHELL
```

### ❌ مشكلة: إذن مرفوض (Permission Denied) عند تشغيل docker بدون sudo

```bash
# أضف المستخدم الحالي لمجموعة docker
sudo usermod -aG docker "$USER"

# تفعيل المجموعة فورًا دون تسجيل خروج
newgrp docker
```

### ❌ مشكلة: Docker daemon غير قيد التشغيل

```bash
# تشغيل خدمة Docker
sudo systemctl start docker

# التحقق من السجلات لمعرفة سبب التوقف
sudo journalctl -u docker -n 50 --no-pager
```

### ❌ مشكلة: عدم القدرة على سحب الصور من Docker Hub

```bash
# التحقق من اتصال الإنترنت
ping -c 4 hub.docker.com

# التحقق من إعدادات DNS
cat /etc/resolv.conf

# إذا كنت خلف جدار ناري أو بروكسي، قم بتعيين البروكسي في Docker
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://proxy.server:port/"
Environment="HTTPS_PROXY=http://proxy.server:port/"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

### ❌ مشكلة: نفاد مساحة القرص بسبب صور وأوامر Docker غير مستخدمة

```bash
# عرض استخدام القرص من قبل Docker
sudo docker system df

# تنظيف الموارد غير المستخدمة
sudo docker system prune -a --volumes
```

---

## 9. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| محرك Docker | Docker Engine CE |
| واجهة سطر الأوامر | Docker CLI |
| إدارة الحاويات | containerd |
| بناء الصور | Docker Buildx |
| إدارة التطبيقات المتعددة | Docker Compose V2 (Plugin) |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS، Ubuntu 24.04 LTS |
| مفتاح GPG | `/etc/apt/keyrings/docker.asc` |
| مستودع apt | `/etc/apt/sources.list.d/docker.list` |
| بيانات Docker | `/var/lib/docker` |
| إعدادات Docker | `/etc/docker` |
| منفذ Docker daemon الافتراضي | unix:///var/run/docker.sock |

### البنية الداخلية للمجلد

```
deployment/docker/
├── docker_installation_commands.txt    # أوامر التثبيت السريعة (الملف الأصلي)
└── Installing Docker.Command.md        # هذا الدليل الشامل والمفصل
```

---

## 10. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | لا تستخدم `sudo apt remove docker` فقط، استخدم `purge` لإزالة ملفات التكوين أيضاً. | 🔹 معلومات |
| 2 | احتفظ بنسخة احتياطية من مجلد `/var/lib/docker` إذا كان يحتوي على صور أو أحجام مهمة قبل الإزالة. | 🔴 هاما |
| 3 | إضافة المستخدم لمجموعة `docker` تمنحه صلاحيات واسعة تقارب Root، لا تفعل ذلك لمستخدمين غير موثوقين. | 🔴 أمني |
| 4 | إذا كنت تنقل التثبيت بين أجهزة، تأكد من أن جميع الأجهزة لديها نفس إصدار Ubuntu. | 🔹 معلومات |
| 5 | للتحديث إلى إصدار أحدث من Docker، نفذ `sudo apt update && sudo apt upgrade -y`. | 🔹 معلومات |
| 6 | الأمر `docker system prune -a --volumes` يحذف جميع الصور والأحجام غير المستخدمة بشكل دائم. | 🔴 خطير |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Docker الرسمي:

🔗 https://docs.docker.com/engine/install/ubuntu/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
