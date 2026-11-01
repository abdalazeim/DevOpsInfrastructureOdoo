# ODOO INFRASTRUCTURE
## TECHNICAL DEPLOYMENT & OPERATIONS RUNBOOK

**Project:** DevOps Odoo Infrastructure  
**Domain:** devops-odoo.com  
**Platform:** Ubuntu Server  
**Containerization:** Docker & Docker Compose  
**Reverse Proxy:** Traefik v3.7  
**Deployment Status:** Operational

---

# 01. INFRASTRUCTURE OVERVIEW
## نظرة عامة على البنية التحتية

تم إعداد بيئة تشغيل تستضيف إصدارين مستقلين من Odoo على خادم Ubuntu واحد.

| Component | Technology | Purpose |
|---|---|---|
| Operating System | Ubuntu | Server OS |
| Container Engine | Docker | Container Runtime |
| Orchestration | Docker Compose | Service Management |
| Reverse Proxy | Traefik v3.7 | Domain Routing |
| Network | Docker Bridge | Container Communication |
| Database 01 | PostgreSQL 16 | Odoo 17 Database |
| Database 02 | PostgreSQL 18 | Odoo 19 Database |
| Application 01 | Odoo 17 | ERP Application |
| Application 02 | Odoo 19 | ERP Application |

### Infrastructure Architecture

```text
                         INTERNET
                            |
                            |
                     PUBLIC IP ADDRESS
                            |
                            |
                      UBUNTU SERVER
                     devops-odoo
                            |
                            |
                     DOCKER ENGINE
                            |
                            |
                     TRAEFIK v3.7
                      Reverse Proxy
                            |
                     Docker Network
                         proxy
                            |
             +--------------+--------------+
             |                             |
             |                             |
        ODOO STACK 17                 ODOO STACK 19
             |                             |
         Odoo 17                        Odoo 19
         Port 8069                     Port 8069
             |                             |
       PostgreSQL 16                 PostgreSQL 18
             |                             |
       Persistent Data               Persistent Data
```

---

# 02. SERVER ENVIRONMENT
## تجهيز الخادم

### 2.1 تحديث Ubuntu

```bash
sudo apt update
sudo apt upgrade -y
```

### 2.2 تثبيت الأدوات الأساسية

```bash
sudo apt install -y \
curl \
wget \
git \
nano \
vim \
htop \
net-tools \
ca-certificates \
gnupg \
lsb-release \
unzip \
jq \
dnsutils \
ufw
```

### 2.3 معرفة مواصفات الخادم

```bash
hostnamectl
```

```bash
lsb_release -a
```

```bash
free -h
```

```bash
df -h
```

```bash
lscpu
```

### 2.4 معرفة عنوان IP

```bash
hostname -I
```

```bash
ip addr
```

### 2.5 فحص المنافذ

```bash
sudo ss -tulpn
```

---

# 03. DOCKER ENGINE INSTALLATION
## تثبيت Docker

### 3.1 إزالة الحزم المتعارضة عند الحاجة

لا تنفذ هذا القسم إذا كانت بيئة Docker الحالية مستقرة ولا توجد حاجة لإزالة الحزم.

```bash
sudo apt remove -y \
docker.io \
docker-doc \
docker-compose \
podman-docker \
containerd \
runc
```

### 3.2 إعداد مستودع Docker الرسمي

```bash
sudo apt update
sudo apt install -y ca-certificates curl
```

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
-o /etc/apt/keyrings/docker.asc
```

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

### 3.3 إضافة المستودع

```bash
echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 3.4 تثبيت Docker Compose Plugin

```bash
sudo apt update
```

```bash
sudo apt install -y \
docker-ce \
docker-ce-cli \
containerd.io \
docker-buildx-plugin \
docker-compose-plugin
```

### 3.5 تشغيل Docker

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### 3.6 التحقق من التثبيت

```bash
sudo docker version
```

```bash
sudo docker compose version
```

```bash
sudo systemctl status docker
```

---

# 04. DOCKER NETWORK ARCHITECTURE
## إنشاء الشبكة المشتركة

تم استخدام شبكة Docker خارجية باسم:

```text
proxy
```

وظيفتها ربط Traefik بمشاريع Odoo المختلفة.

### 4.1 التحقق من الشبكة

```bash
sudo docker network ls
```

### 4.2 إنشاء الشبكة إذا لم تكن موجودة

```bash
sudo docker network create proxy
```

**تنبيه:** إذا ظهرت رسالة بأن الشبكة موجودة مسبقاً، لا تنشئها مجدداً.

### 4.3 فحص الشبكة

```bash
sudo docker network inspect proxy
```

### 4.4 عرض الحاويات المتصلة بالشبكة

```bash
sudo docker network inspect proxy \
--format '{{range .Containers}}{{.Name}}{{println}}{{end}}'
```

---

# 05. TRAEFIK REVERSE PROXY
## إعداد نظام التوجيه المركزي

تم اعتماد Traefik v3.7 كوسيط عكسي لاستقبال طلبات HTTP وتوجيهها إلى خدمات Odoo.

### 5.1 الوظائف

- استقبال طلبات النطاقات.
- تحديد الخدمة بناءً على Host Header.
- توجيه الطلب إلى منفذ Odoo الداخلي.
- الاتصال بحاويات Docker عبر شبكة proxy.
- إدارة قواعد التوجيه مركزياً.

### 5.2 المنافذ

| Port | Description |
|---|---|
| 80 | HTTP EntryPoint |
| 443 | HTTPS EntryPoint إذا تم تفعيله |
| 10090 | لوحة التحكم المنشورة |
| 8080 | لوحة التحكم داخل الحاوية |

### 5.3 فحص حاوية Traefik

```bash
sudo docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

### 5.4 فحص سجلات Traefik

```bash
sudo docker logs --tail=100 traefik
```

إذا كان اسم الحاوية مختلفاً، استخرجه من `docker ps`.

### 5.5 اختبار الوصول إلى Traefik

```bash
curl -I http://127.0.0.1
```

---

# 06. DNS CONFIGURATION
## إعداد سجلات DNS

يجب أن تكون سجلات النطاقات موجهة إلى عنوان IP العام للخادم.

| Record Type | Host | Value |
|---|---|---|
| A | odoo17 | SERVER_PUBLIC_IP |
| A | odoo19 | SERVER_PUBLIC_IP |

استبدل `SERVER_PUBLIC_IP` بعنوان IP العام للخادم.

### 6.1 اختبار DNS

```bash
dig odoo17.devops-odoo.com
```

```bash
dig odoo19.devops-odoo.com
```

### 6.2 اختبار بديل

```bash
nslookup odoo17.devops-odoo.com
```

```bash
nslookup odoo19.devops-odoo.com
```

### 6.3 اختبار الوصول إلى HTTP

```bash
curl -I http://odoo17.devops-odoo.com
```

```bash
curl -I http://odoo19.devops-odoo.com
```

---

# 07. ODOO 17 DEPLOYMENT
## إعداد وتشغيل Odoo 17

### 7.1 مسار المشروع

```bash
cd /opt/odoo-17-docker
```

### 7.2 بنية المشروع

```text
/opt/odoo-17-docker/
│
├── addons/
├── custom_addons/
├── etc/
├── postgresql/
├── docker-compose.yml
└── entrypoint.sh
```

### 7.3 الخدمات

| Service | Function |
|---|---|
| odoo17 | Odoo Application |
| db | PostgreSQL Database |

### 7.4 المنافذ

| Host Port | Container Port | Function |
|---|---|---|
| 10017 | 8069 | Odoo Web |
| 20017 | 8072 | Longpolling |

### 7.5 إعداد الاتصال بقاعدة البيانات

```text
HOST=db
PORT=5432
USER=odoo
PASSWORD=<SECURE_PASSWORD>
```

يجب أن تكون بيانات الدخول متطابقة بين إعدادات PostgreSQL وOdoo.

### 7.6 إعدادات الشبكة

يجب أن تكون خدمة Odoo 17 مرتبطة بالشبكة:

```text
proxy
```

ويجب أن يحتوي إعداد Traefik على قاعدة توجيه:

```text
Host(`odoo17.devops-odoo.com`)
```

والمنفذ الداخلي:

```text
8069
```

### 7.7 تشغيل الخدمات

```bash
cd /opt/odoo-17-docker
sudo docker compose up -d
```

### 7.8 إعادة إنشاء خدمة Odoo فقط

```bash
sudo docker compose up -d --no-deps --force-recreate odoo17
```

### 7.9 التحقق من التشغيل

```bash
sudo docker compose ps
```

```bash
sudo docker compose logs --tail=100 odoo17
```

---

# 08. ODOO 19 DEPLOYMENT
## إعداد وتشغيل Odoo 19

### 8.1 مسار المشروع

```bash
cd /opt/odoo19-enterprise
```

### 8.2 الخدمات

| Service | Function |
|---|---|
| odoo19 | Odoo Application |
| db | PostgreSQL Database |

### 8.3 المنافذ

| Host Port | Container Port | Function |
|---|---|---|
| 10019 | 8069 | Odoo Web |
| 20019 | 8072 | Longpolling |

### 8.4 إعداد قاعدة البيانات

```text
HOST=db
PORT=5432
USER=<DATABASE_USER>
PASSWORD=<SECURE_PASSWORD>
```

### 8.5 إعداد Traefik

قاعدة التوجيه:

```text
Host(`odoo19.devops-odoo.com`)
```

المنفذ الداخلي:

```text
8069
```

الشبكة:

```text
proxy
```

يجب أن يعمل Odoo باستخدام Proxy Mode عند وجود Traefik أمامه.

### 8.6 تشغيل النظام

```bash
cd /opt/odoo19-enterprise
sudo docker compose up -d
```

### 8.7 إعادة إنشاء خدمة Odoo فقط

```bash
sudo docker compose up -d --no-deps --force-recreate odoo19
```

### 8.8 فحص الحالة

```bash
sudo docker compose ps
```

```bash
sudo docker compose logs --tail=100 odoo19
```

---

# 09. POSTGRESQL MANAGEMENT
## إدارة قواعد البيانات

تم تخصيص قاعدة بيانات مستقلة لكل إصدار.

| Version | PostgreSQL |
|---|---|
| Odoo 17 | PostgreSQL 16 |
| Odoo 19 | PostgreSQL 18 |

### 9.1 فحص قواعد البيانات

لـ Odoo 17:

```bash
cd /opt/odoo-17-docker
sudo docker compose exec db psql -U odoo -l
```

لـ Odoo 19:

```bash
cd /opt/odoo19-enterprise
sudo docker compose exec db psql -U <DATABASE_USER> -l
```

استبدل اسم المستخدم بالقيمة الموجودة في إعداد Compose.

### 9.2 الدخول إلى PostgreSQL

```bash
sudo docker compose exec db psql -U odoo
```

### 9.3 عرض قواعد البيانات

```sql
\l
```

### 9.4 عرض المستخدمين

```sql
\du
```

### 9.5 الخروج

```sql
\q
```

---

# 10. DATABASE CONNECTIVITY TEST
## اختبار اتصال Odoo بقاعدة البيانات

تم استخدام مكتبة psycopg2 للتحقق من الاتصال من داخل حاوية Odoo 17.

```bash
sudo docker exec odoo-17-docker-odoo17-1 \
python3 -c "import psycopg2; c=psycopg2.connect(host='db',port=5432,user='odoo',password='YOUR_PASSWORD',dbname='postgres'); print('DATABASE CONNECTION SUCCESS'); c.close()"
```

النتيجة المتوقعة:

```text
DATABASE CONNECTION SUCCESS
```

إذا ظهر Authentication Failed:

1. افحص كلمة مرور PostgreSQL.
2. افحص متغيرات بيئة Odoo.
3. افحص ملف الإعدادات.
4. تأكد أن اسم المستخدم صحيح.
5. أعد إنشاء خدمة Odoo بعد تصحيح الإعدادات.

---

# 11. ENTRYPOINT & DEPENDENCIES
## إدارة تشغيل Odoo والمتطلبات

ملف التشغيل الخاص بـ Odoo 17:

```text
/opt/odoo-17-docker/entrypoint.sh
```

### تسلسل التنفيذ

```text
Container Start
      |
      v
Python Dependencies
      |
      v
System Dependencies
      |
      v
Logrotate Configuration
      |
      v
Cron Service
      |
      v
Wait For PostgreSQL
      |
      v
Start Odoo Server
```

### فحص العمليات

```bash
sudo docker exec odoo-17-docker-odoo17-1 \
sh -c 'ps aux | grep -E "apt-get|apt |odoo" | grep -v grep'
```

### فحص logrotate

```bash
sudo docker exec odoo-17-docker-odoo17-1 \
dpkg -s logrotate 2>/dev/null | grep Status
```

النتيجة المتوقعة:

```text
Status: install ok installed
```

### تحسين وقت التشغيل

تم اقتراح التحقق من تثبيت logrotate قبل تنفيذ apt-get update، حتى لا تتكرر عملية التثبيت عند كل تشغيل.

قبل تعديل الملف:

```bash
sudo cp /opt/odoo-17-docker/entrypoint.sh \
/opt/odoo-17-docker/entrypoint.sh.backup
```

المقطع المقترح:

```bash
if ! dpkg-query -W -f='${Status}' logrotate 2>/dev/null | grep -q "install ok installed"; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y logrotate
fi

pip3 install -r /etc/odoo/requirements.txt
```

هذا تحسين مقترح، ويجب مقارنة المقطع بالملف الفعلي قبل تطبيقه.

---

# 12. REVERSE PROXY TESTING
## اختبار التوجيه عبر Traefik

### اختبار Odoo 17 محلياً

```bash
curl -I --max-time 20 \
http://127.0.0.1:10017/web/database/selector
```

### اختبار Odoo 19 محلياً

```bash
curl -I --max-time 20 \
http://127.0.0.1:10019/web/database/selector
```

### اختبار Odoo 17 عبر النطاق

```bash
curl -I --max-time 20 \
http://odoo17.devops-odoo.com/
```

### اختبار Odoo 19 عبر النطاق

```bash
curl -I --max-time 20 \
http://odoo19.devops-odoo.com/
```

### فحص نتيجة HTTP

| Status | Meaning |
|---|---|
| 200 | Request Successful |
| 301 | Redirect |
| 302 | Temporary Redirect |
| 400 | Bad Request |
| 401 | Authentication Required |
| 403 | Forbidden |
| 404 | Not Found |
| 502 | Bad Gateway |
| 503 | Service Unavailable |
| 504 | Gateway Timeout |

ملاحظة: قد تختلف استجابة الصفحة الرئيسية عن صفحة اختيار قاعدة البيانات حسب إعدادات Odoo. لا تعتبر كل استجابة Redirect دليلاً على وجود عطل.

---

# 13. TROUBLESHOOTING
## معالجة الأخطاء التقنية

### المشكلة الأولى: 502 Bad Gateway

الأسباب المحتملة:

- حاوية Odoo متوقفة.
- Traefik لا يستطيع الوصول إلى الحاوية.
- إعداد المنفذ الداخلي غير صحيح.
- الشبكة المشتركة غير مضبوطة.
- Odoo لم ينجح في الاتصال بقاعدة البيانات.

الفحص:

```bash
sudo docker ps -a
```

```bash
sudo docker network inspect proxy
```

```bash
sudo docker logs --tail=100 traefik
```

```bash
sudo docker compose logs --tail=100 odoo17
```

أو افحص خدمة Odoo 19 من مجلد مشروعها.

### المشكلة الثانية: Connection Reset by Peer

الأسباب المحتملة:

- Odoo لم يبدأ بعد.
- Entrypoint ما زال ينفذ التثبيت.
- PostgreSQL غير متاح.
- خدمة Odoo توقفت بسبب خطأ.

الفحص:

```bash
sudo docker compose ps
```

```bash
sudo docker compose logs --tail=200 odoo17
```

### المشكلة الثالثة: PostgreSQL Authentication Failed

افحص:

```bash
sudo docker compose logs --tail=100 db
```

ثم راجع:

```text
Database Host
Database User
Database Password
Database Port
```

يجب تحديث إعدادات Odoo وPostgreSQL بصورة متوافقة.

### المشكلة الرابعة: Address Already in Use

افحص المنفذ:

```bash
sudo ss -lntp | grep ':10017'
```

أو:

```bash
sudo ss -lntp | grep ':10019'
```

لا تغيّر المنافذ قبل تحديد الخدمة التي تستخدمها.

### المشكلة الخامسة: Docker Container Exited

افحص:

```bash
sudo docker ps -a
```

ثم:

```bash
sudo docker logs --tail=200 CONTAINER_NAME
```

استبدل `CONTAINER_NAME` بالاسم الفعلي للحاوية.

### المشكلة السادسة: DNS Resolution Failure

```bash
dig odoo17.devops-odoo.com
dig odoo19.devops-odoo.com
```

تحقق من سجلات DNS وعنوان IP العام.

---

# 14. BACKUP & RESTORE STRATEGY
## النسخ الاحتياطي والاستعادة

النسخ الاحتياطي عنصر أساسي في بيئة الإنتاج.

### 14.1 إنشاء مجلد النسخ الاحتياطي

```bash
sudo mkdir -p /opt/backups/odoo
```

### 14.2 نسخ ملفات إعداد Odoo 17

```bash
sudo tar -czf /opt/backups/odoo/odoo17-config.tar.gz \
-C /opt/odoo-17-docker \
docker-compose.yml entrypoint.sh etc
```

### 14.3 نسخ ملفات إعداد Odoo 19

```bash
sudo tar -czf /opt/backups/odoo/odoo19-config.tar.gz \
-C /opt/odoo19-enterprise \
docker-compose.yml
```

### 14.4 نسخ قواعد البيانات

يجب أولاً معرفة أسماء قواعد البيانات الفعلية.

مثال لـ Odoo 17:

```bash
cd /opt/odoo-17-docker

sudo docker compose exec -T db \
pg_dump -U odoo -Fc DATABASE_NAME \
> /opt/backups/odoo/odoo17-DATABASE_NAME.dump
```

مثال لـ Odoo 19:

```bash
cd /opt/odoo19-enterprise

sudo docker compose exec -T db \
pg_dump -U DATABASE_USER -Fc DATABASE_NAME \
> /opt/backups/odoo/odoo19-DATABASE_NAME.dump
```

استبدل أسماء قواعد البيانات والمستخدمين بالقيم الفعلية.

### 14.5 التحقق من ملفات النسخ

```bash
sudo ls -lh /opt/backups/odoo
```

**مهم:** قواعد البيانات وحدها لا تكفي لاستعادة Odoo بالكامل. يجب الاحتفاظ أيضاً بملفات filestore الخاصة بكل قاعدة بيانات، وملفات الإضافات المخصصة والإعدادات. كما ينبغي اختبار الاستعادة دورياً على بيئة منفصلة.

---

# 15. SECURITY HARDENING
## تأمين الخادم

### 15.1 فحص جدار الحماية

```bash
sudo ufw status verbose
```

### 15.2 المنافذ الأساسية

| Port | Purpose |
|---|---|
| 22 | SSH |
| 80 | HTTP |
| 443 | HTTPS |

لا تفتح منافذ PostgreSQL أو منافذ Odoo المباشرة للإنترنت دون ضرورة واضحة.

### 15.3 تفعيل HTTPS

يوصى بإعداد شهادات TLS عبر Traefik باستخدام Let's Encrypt.

المتطلبات:

1. توجيه النطاقات إلى IP الخادم.
2. فتح المنفذين 80 و443.
3. إعداد ACME Certificate Resolver.
4. إنشاء ملف تخزين الشهادات مع صلاحيات مناسبة.
5. تفعيل HTTPS Routers.
6. اختبار تجديد الشهادات.

### 15.4 حماية بيانات الدخول

- استخدام كلمات مرور قوية وفريدة.
- عدم حفظ كلمات المرور في مستودعات Git.
- عدم نشر ملفات `.env`.
- تقييد الوصول إلى لوحة Traefik.
- استخدام SSH Keys.
- الاحتفاظ بنسخ احتياطية آمنة.

---

# 16. MAINTENANCE & MONITORING
## الصيانة والمراقبة

### فحص استهلاك الموارد

```bash
sudo docker stats
```

### فحص مساحة القرص

```bash
df -h
```

### فحص الذاكرة

```bash
free -h
```

### فحص الحاويات

```bash
sudo docker ps
```

### فحص الخدمات

```bash
sudo systemctl status docker
```

### فحص السجلات

```bash
sudo journalctl -u docker --since today
```

### تنظيف Docker

عرض المساحة المستخدمة:

```bash
sudo docker system df
```

**تحذير:** لا تستخدم `docker system prune -a --volumes` بصورة عشوائية، لأنه قد يحذف موارد تحتاج إليها الخدمات.

---

# 17. OPERATIONAL COMMANDS
## أوامر التشغيل اليومية

### تشغيل Odoo 17

```bash
cd /opt/odoo-17-docker
sudo docker compose up -d
```

### إيقاف Odoo 17

```bash
cd /opt/odoo-17-docker
sudo docker compose stop
```

### إعادة تشغيل Odoo 17

```bash
cd /opt/odoo-17-docker
sudo docker compose restart
```

### تشغيل Odoo 19

```bash
cd /opt/odoo19-enterprise
sudo docker compose up -d
```

### إيقاف Odoo 19

```bash
cd /opt/odoo19-enterprise
sudo docker compose stop
```

### إعادة تشغيل Odoo 19

```bash
cd /opt/odoo19-enterprise
sudo docker compose restart
```

### عرض الحاويات

```bash
sudo docker ps -a
```

### عرض الشبكات

```bash
sudo docker network ls
```

### عرض الصور

```bash
sudo docker images
```

---

# 18. FINAL DEPLOYMENT VERIFICATION
## قائمة التحقق النهائية

| No. | Verification | Expected Result |
|---|---|---|
| 01 | Ubuntu Server | Running |
| 02 | Docker Engine | Active |
| 03 | Docker Compose | Available |
| 04 | Docker Network proxy | Available |
| 05 | Traefik v3.7 | Running |
| 06 | PostgreSQL 16 | Running |
| 07 | PostgreSQL 18 | Running |
| 08 | Odoo 17 Container | Running |
| 09 | Odoo 19 Container | Running |
| 10 | Odoo 17 Database Connection | Successful |
| 11 | Odoo 19 Database Connection | Successful |
| 12 | DNS Resolution | Successful |
| 13 | Reverse Proxy Routing | Successful |
| 14 | Odoo 17 HTTP Test | HTTP 200 OK |
| 15 | Odoo 19 HTTP Test | Successful |
| 16 | Backup Strategy | Documented |
| 17 | Security Review | Required |

---

# 19. PRODUCTION ENDPOINTS
## روابط الأنظمة

**ODOO 17**

http://odoo17.devops-odoo.com/

**ODOO 19**

http://odoo19.devops-odoo.com/

---

# 20. TECHNICAL COMPLETION SUMMARY

تم إعداد بيئة تشغيل متعددة الإصدارات على خادم Ubuntu واحد.

تم فصل التطبيقات وقواعد البيانات، وربط الخدمات عبر شبكة Docker مشتركة، واستخدام Traefik لتوجيه النطاقات.

كما تمت معالجة مشكلات اتصال PostgreSQL، وأخطاء HTTP 502، ومشكلة تأخر بدء Odoo 17 بسبب عمليات التهيئة داخل Entrypoint.

**Final Architecture:**

```text
Ubuntu Server
    |
    +-- Docker Engine
    |
    +-- Traefik v3.7
    |      |
    |      +-- odoo17.devops-odoo.com
    |      |       |
    |      |       +-- Odoo 17
    |      |       +-- PostgreSQL 16
    |      |
    |      +-- odoo19.devops-odoo.com
    |              |
    |              +-- Odoo 19
    |              +-- PostgreSQL 18
    |
    +-- Docker Network: proxy
```

**DOCUMENT STATUS: OPERATIONAL**

**DOCUMENT TYPE: TECHNICAL DEPLOYMENT & OPERATIONS RUNBOOK**
