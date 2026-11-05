# 🌐 دليل تثبيت Traefik v3.7 على Ubuntu باستخدام Docker Compose

> **النظام المدعوم:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS  
> **الأداة:** Traefik v3.7 - Reverse Proxy و Load Balancer  
> **الوظيفة:** إدارة الوصول إلى Odoo، Jenkins، Portainer، pgAdmin عبر HTTPS وشهادات SSL تلقائية من Let's Encrypt  
> **الشبكة:** شبكة Docker مشتركة باسم `proxy`  
> **المنافذ:** 80 (HTTP)، 443 (HTTPS)  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [مقدمة عن Traefik](#-مقدمة-عن-Traefik)
2. [المتطلبات الأساسية](#-المتطلبات-الأساسية)
3. [الطريقة الأولى: التثبيت باستخدام Docker Compose](#-الطريقة-الأولى-التثبيت-باستخدام-Docker-Compose)
4. [إنشاء مجلدات Traefik](#-إنشاء-مجلدات-Traefik)
5. [إنشاء ملف شهادة SSL](#-إنشاء-ملف-شهادة-SSL)
6. [إنشاء شبكة Docker مشتركة](#-إنشاء-شبكة-Docker-مشتركة)
7. [إنشاء ملف Docker Compose](#-إنشاء-ملف-Docker-Compose)
8. [التحقق من ملف Compose](#-التحقق-من-ملف-Compose)
9. [تحميل صورة Traefik](#-تحميل-صورة-Traefik)
10. [تشغيل Traefik](#-تشغيل-Traefik)
11. [التحقق من التشغيل](#-التحقق-من-التشغيل)
12. [إعداد جدار الحماية UFW](#-إعداد-جدار-الحماية-UFW)
13. [التحقق من DNS](#-التحقق-من-DNS)
14. [إدارة Traefik (إعادة تشغيل، إيقاف، تشغيل، تحديث)](#-إدارة-Traefik)
15. [استكشاف الأخطاء وإصلاحها](#-استكشاف-الأخطاء-وإصلاحها)
16. [إزالة Traefik بالكامل](#-إزالة-Traefik-بشكل-كامل)
17. [المعلومات التقنية والبنية الداخلية](#-المعلومات-التقنية-والبنية-الداخلية)
18. [ملاحظات هامة وتحذيرات أمنية](#-ملاحظات-هامة-وتحذيرات-أمنية)

---

## 1. 🎯 مقدمة عن Traefik

**Traefik** هو بروكسي عكسي (Reverse Proxy) وموزع أحمال (Load Balancer) حديث مصمم للبنى التحتية القائمة على الحاويات (Docker، Kubernetes). يكتشف الخدمات تلقائياً عبر ملصقات Docker (Labels) ويدير توجيه الطلبات وشهادات SSL عبر Let's Encrypt.

### ✅ ما يمكن إدارةه عبر Traefik في هذا النظام:

| المكون | الغرض |
|--------|-------|
| Odoo 17/18/19 | توجيه الطلبات عبر HTTPS مع شهادات SSL |
| Jenkins | الوصول الآمن لواجهة Jenkins عبر HTTPS |
| Portainer | إدارة حاويات Docker عبر واجهة آمنة |
| pgAdmin | إدارة قواعد بيانات PostgreSQL عبر واجهة آمنة |
| شهادات SSL | إصدار وتجديد تلقائي لشهادات Let's Encrypt |

---

## 2. 🔧 المتطلبات الأساسية

تأكد من توفر المتطلبات التالية قبل بدء التثبيت:

| # | المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|---|----------|--------------|------------------------|
| 1 | Docker Engine | `docker --version` | راجع دليل تثبيت Docker |
| 2 | Docker Compose | `docker compose version` | يُثبّت مع Docker Engine |
| 3 | صلاحيات جذر (sudo) | `id` | — |
| 4 | منفذ 80 فارغ | `ss -tulnp | grep :80` | — |
| 5 | منفذ 443 فارغ | `ss -tulnp | grep :443` | — |
| 6 | اسم نطاق (Domain) | `dig +short your-domain.com` | نطاق مُشار إلى IP السيرفر |

---

## 3. 🚀 الطريقة الأولى: التثبيت باستخدام Docker Compose

سنثبت Traefik v3.7 باستخدام Docker Compose، مع حفظ الإعدادات وشهادات SSL بشكل دائم.

---

## 4. 📁 إنشاء مجلدات Traefik

```bash
sudo mkdir -p /opt/traefik
sudo mkdir -p /opt/traefik/letsencrypt
```

### الغرض من المجلدات:

| المجلد | الغرض |
|--------|-------|
| `/opt/traefik` | مجلد الإعدادات الرئيسي وملف docker-compose.yml |
| `/opt/traefik/letsencrypt` | مجلد حفظ شهادات SSL وقبول التحديات (ACME) |

---

## 5. 🔐 إنشاء ملف حفظ شهادات SSL

```bash
sudo touch /opt/traefik/letsencrypt/acme.json
sudo chmod 600 /opt/traefik/letsencrypt/acme.json
```

> ⚠️ **ملاحظة:** ملف `acme.json` يخزن شهادات SSL ومفاتيحها. الصلاحية `600` تضمن أن فقط مالك الملف يمكنه قراءته وكتابته للأمان.

---

## 6. 🌐 إنشاء شبكة Docker مشتركة

هذه الشبكة ستُستخدم من قبل Traefik وجميع الخدمات التي تريد عرضها عبر البروكسي (Odoo، Jenkins، Portainer، pgAdmin).

```bash
sudo docker network inspect proxy >/dev/null 2>&1 || \
sudo docker network create proxy
```

> 💡 **ملاحظة:** الأمر يتحقق من وجود الشبكة قبل إنشائها لتجنب الأخطاء إذا كانت موجودة مسبقاً.

---

## 7. 📝 إنشاء ملف Docker Compose

```bash
sudo nano /opt/traefik/docker-compose.yml
```

### محتوى الملف:

```yaml
services:
  traefik:
    image: traefik:v3.7
    container_name: traefik
    restart: unless-stopped

    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=proxy"

      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"

      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"

      - "--certificatesresolvers.letsencrypt.acme.email=YOUR_EMAIL"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"

      - "--log.level=INFO"
      - "--accesslog=true"

    ports:
      - "80:80"
      - "443:443"

    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"

    networks:
      - proxy

networks:
  proxy:
    external: true
```

### ⚠️ استبدل `YOUR_EMAIL` ببريدك الإلكتروني الحقيقي قبل حفظ الملف.

### شرح الأوامر (Command Options):

| الخيار | القيمة | الغرض |
|--------|--------|-------|
| `--api.dashboard=true` | — | تفعيل لوحة التحكم الخاصة بـ Traefik |
| `--providers.docker=true` | — | تفعيل مزود Docker لاكتشاف الخدمات تلقائياً |
| `--providers.docker.exposedbydefault=false` | — | عدم عرض الحاويات افتراضياً (يتطلب ملصقات يدوية) |
| `--providers.docker.network=proxy` | — | الشبكة التي يستخدمها Traefik لاكتشاف الحاويات |
| `--entrypoints.web.address=:80` | — | نقطة نهاية HTTP على المنفذ 80 |
| `--entrypoints.websecure.address=:443` | — | نقطة نهاية HTTPS على المنفذ 443 |
| `--entrypoints.web.http.redirections.entrypoint.to=websecure` | — | إعادة توجيه HTTP إلى HTTPS |
| `--entrypoints.web.http.redirections.entrypoint.scheme=https` | — | استخدام مخطط HTTPS في إعادة التوجيه |
| `--certificatesresolvers.letsencrypt.acme.email` | بريدك الإلكتروني | بريد التسجيل في Let's Encrypt |
| `--certificatesresolvers.letsencrypt.acme.storage` | `/letsencrypt/acme.json` | مسار حفظ شهادات SSL |
| `--certificatesresolvers.letsencrypt.acme.httpchallenge=true` | — | تفعيل التحقق عبر HTTP Challenge |
| `--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint` | `web` | نقطة نهاية للتحقق عبر HTTP |
| `--log.level=INFO` | — | مستوى السجلات (INFO) |
| `--accesslog=true` | — | تفعيل سجلات الوصول |

---

## 8. ✅ التحقق من ملف Compose

```bash
cd /opt/traefik
sudo docker compose config
```

إذا ظهر محتوى الملف بدون أخطاء، فالملف سليم وجاهز للتشغيل.

---

## 9. 📥 تحميل صورة Traefik

```bash
sudo docker pull traefik:v3.7
```

---

## 10. 🚀 تشغيل Traefik

```bash
cd /opt/traefik
sudo docker compose up -d
```

---

## 11. ✅ التحقق من التشغيل

### التحقق من تشغيل الحاوية:

```bash
sudo docker ps --filter name=traefik
```

### عرض السجلات:

```bash
sudo docker logs --tail=100 traefik
```

### متابعة السجلات مباشرة:

```bash
sudo docker logs -f traefik
```

### التحقق من المنافذ:

```bash
sudo ss -tulnp | grep -E ':80|:443'
```

### التحقق من شبكة Docker:

```bash
sudo docker network inspect proxy
```

---

## 12. 🔥 إعداد جدار الحماية UFW

إذا كنت تستخدم UFW على السيرفر:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

> 💡 **ملاحظة:** تأكد من أن المنافذ 80 و443 مفتوحة للسماح بالحركة الواردة والصادرة عبر HTTP وHTTPS.

---

## 13. 🌍 التحقق من DNS

يجب أن يكون نطاقك موجّهاً إلى عنوان IP العام للسيرفر، وأن تكون المنافذ 80 و443 متاحة من الإنترنت.

```bash
dig +short devops-odoo.com
```

استبدل `devops-odoo.com` بنطاقك الخاص إذا كنت تستخدم نطاقاً آخر.

### ✅ النتيجة المتوقعة:

يجب أن يظهر عنوان IP العام للسيرفر ك resultado للأمر `dig`.

---

## 14. ⚙️ إدارة Traefik

### إعادة تشغيل Traefik:

```bash
cd /opt/traefik
sudo docker compose restart
```

### إيقاف Traefik:

```bash
cd /opt/traefik
sudo docker compose stop
```

### تشغيل Traefik (بعد الإيقاف):

```bash
cd /opt/traefik
sudo docker compose start
```

### تحديث الصورة وإعادة إنشاء الحاوية:

```bash
cd /opt/traefik
sudo docker compose pull
sudo docker compose up -d
```

### التحقق من حالة الحاوية:

```bash
sudo docker inspect traefik --format '{{.State.Status}}'
```

---

## 8. 🐛 استكشاف الأخطاء وإصلاحها

### ❌ مشكلة: تعذر الوصول إلى لوحة تحكم Traefik

```bash
# التحقق من أن الحاوية تعمل
sudo docker ps --filter name=traefik

# التحقق من المنافذ
sudo ss -tulnp | grep -E ':80|:443'

# فحص السجلات
sudo docker logs --tail=50 traefik

# إذا كانت الحاوية متوقفة
sudo docker compose -f /opt/traefik/docker-compose.yml up -d
```

### ❌ مشكلة: عدم إصدار شهادات SSL من Let's Encrypt

```bash
# التحقق من أن البريد الإلكتروني صحيح في ملف docker-compose.yml
grep "acme.email" /opt/traefik/docker-compose.yml

# التحقق من أن المنفذ 80 مفتوح للتحدي (HTTP Challenge)
sudo ss -tulnp | grep :80

# التحقق من DNS
dig +short your-domain.com

# فحص السجلات للحصول على تفاصيل الخطأ
sudo docker logs traefik | grep -i "acme\|letsencrypt\|certificate"
```

### ❌ مشكلة: عدم اكتشاف الحاويات الأخرى (Odoo، Jenkins، إلخ)

```bash
# التحقق من أن الحاويات على شبكة proxy
sudo docker network inspect proxy

# التحقق من أن الحاويات تحتوي على ملصقات Traefik
sudo docker inspect <اسم_الحاوية> | grep -i traefik

# مثال على ملصقات يجب إضافتها لحاوية Odoo:
# labels:
#   - "traefik.enable=true"
#   - "traefik.http.routers.odoo.rule=Host(`odoo.your-domain.com`)"
#   - "traefik.http.routers.odoo.entrypoints=websecure"
#   - "traefik.http.routers.odoo.tls.certresolver=letsencrypt"
```

---

## 9. 🗑️ إزالة Traefik بالكامل

إذا كنت ترغب في إزالة Traefik تمامًا من النظام:

```bash
# 1. إيقاف الحاويات
cd /opt/traefik
sudo docker compose down

# 2. حذف الصورة (اختياري)
sudo docker rmi traefik:v3.7

# 3. حذف مجلد الإعدادات (اختياري - سيحذف شهادات SSL)
sudo rm -rf /opt/traefik

# 4. حذف الشبكة (إذا لم تستخدمها خدمات أخرى)
sudo docker network rm proxy
```

> 🔴 **تحذير حاسم:** حذف المجلد `/opt/traefik` سيحذف **جميع** شهادات SSL والإعدادات بشكل دائم ولا يمكن استعادتها إلا إذا كان لديك نسخة احتياطية.

---

## 10. ℹ️ المعلومات التقنية والبنية الداخلية

### الجدول التقني

| العنصر | القيمة |
|--------|--------|
| الصورة | `traefik:v3.7` |
| اسم الحاوية | `traefik` |
| اسم الشبكة | `proxy` |
| منفذ HTTP | `80` |
| منفذ HTTPS | `443` |
| مسار شهادات SSL | `/opt/traefik/letsencrypt/acme.json` |
| مسار Docker Socket | `/var/run/docker.sock` |
| سياسة إعادة التشغيل | `unless-stopped` |
| مزود الشهادات | Let's Encrypt (HTTP Challenge) |
| نظام التشغيل المدعوم | Ubuntu 22.04 LTS / 24.04 LTS |
| متطلبات Docker | Docker Engine + Docker Compose |

### شكل البنية بعد التثبيت:

```
Internet / HTTPS
     ↓
Ports 80 / 443
     ↓
Traefik Reverse Proxy
  (SSL · Routing · Let's Encrypt)
     ↓
Docker Network: proxy
     ↓
├── Odoo 17 / 18 / 19
├── Jenkins
├── Portainer
└── pgAdmin
```

### البنية الداخلية للمجلد:

```
deployment/traefik/
├── Installing Traefik.Command.md    # هذا الدليل الشامل والمفصل
```

---

## 11. ⚠️ ملاحظات هامة وتحذيرات أمنية

| # | الملاحظة | نوع التحذير |
|---|----------|-------------|
| 1 | استبدل `YOUR_EMAIL` ببريدك الإلكتروني الحقيقي في ملف docker-compose.yml قبل التشغيل. | 🔴 أمني |
| 2 | لا expose المنافذ 80 و443 مباشرة للإنترنت دون جدار ناري مناسب (UFW). | 🔴 أمني |
| 3 | يجب أن يكون النطاق موجّهاً إلى IP السيرفر قبل إصدار شهادات SSL من Let's Encrypt. | 🔴 هام |
| 4 | ملف `acme.json` يحتوي على مفاتيح خاصة للشهادات. احتفظ بنسخة احتياطية منه. | 🔴 أمني |
| 5 | الحاويات التي تريد عرضها عبر Traefik يجب أن تكون على شبكة `proxy` وتحتوي على ملصقات Traefik. | 🔹 معلومات |
| 6 | إعادة توجيه HTTP إلى HTTPS مفعلة افتراضياً في هذا الإعداد. | 🔹 معلومات |
| 7 | لوحة تحكم Traefik متاحة عبر المنفذ 8080 افتراضياً إذا تم تفعيل `--api.dashboard=true`. | 🔹 معلومات |

---

## 📞 الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع توثيق Traefik الرسمي:

🔗 https://doc.traefik.io/traefik/

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
