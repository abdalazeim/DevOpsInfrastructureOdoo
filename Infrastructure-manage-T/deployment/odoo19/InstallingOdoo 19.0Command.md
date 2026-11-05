# دليل تثبيت Odoo 19 بالطريقة التقليدية (اليدوية)

هذا الدليل مخصص للحالة التي يتم فيها **تحميل مجلد `deployment/odoo19` من الإنترنت** أو **نقله من جهاز إلى آخر** وتريد تثبيته محلياً دون الاعتماد على استنساخ من GitHub عبر أمر curl.

---

## المتطلبات الأساسية

قبل بدء التثبيت، تأكد من توفر ما يلي على نظامك (يوصى باستخدام Ubuntu 22.04+):

| المتطلب | الأمر للتحقق | الأمر للتثبيت (Ubuntu) |
|----------|--------------|------------------------|
| Docker Engine | `docker --version` | `sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin` |
| Docker Compose | `docker compose version` | يُثبّت مع Docker Engine كإضافة (`docker-compose-plugin`) |
| sudo / صلاحيات جذر | `id` | — |
| مساحة قرصية حرة | `df -h /` | — |

للتحقق من أن Docker يعمل بشكل صحيح:
```bash
sudo docker run hello-world
```

---

## الطريقة الأولى: التثبيت التقليدي المحلي (بدون Git Clone)

استخدم هذه الطريقة عند تحميل المجلد كملف مضغوط (ZIP) أو نسخه من جهاز آخر إلى الجهاز الحالي.

### الخطوة 1: تحضير المجلد

افتح المحطة وانتقل إلى مكان المجلد:

```bash
# إذا قمت بتنزيل المجلد كمجلد مضغوط، فك الضغط أولاً
unzip odoo19.zip
cd deployment/odoo19

# أو إذا كان المجلد موجوداً بالفعل
cd deployment/odoo19
```

### الخطوة 2: تعيين الصلاحيات

```bash
# منح الصلاحية للتنفيذ لملف التشغيل
chmod +x run.sh
chmod +x entrypoint.sh

# تعيين صلاحيات المجلداتfr
sudo chmod -R 700 postgresql
sudo chmod -R 755 addons etc
sudo chown -R $USER:$USER .
```

### الخطوة 3: إنشاء مجلد PostgreSQL

```bash
mkdir -p postgresql
```

### الخطوة 4: تشغيل الحاويات

```bash
# تشغيل في الخلفية (detached mode)
sudo docker compose up -d

# أو chạy في واجهة المح terminal لرؤية السجلات مباشرة
sudo docker compose up
```

### الخطوة 5: الوصول إلى Odoo

افتح المتصفح وانتقل إلى:

```
http://localhost:10019
```

للمحادثة المباشرة (Live Chat):
```
http://localhost:20019
```

---

## الطريقة الثانية: استخدام ملف run.sh مع引数 مخصصة

إذا كنت تفضل استخدام السكربت المرفق مع تحديد وجهة مخصصة وموانئ مخصصة:

```bash
# تثبيت نسخة أولى
sudo bash run.sh --destination /opt/odoo-one --port 10019 --chat 20019

# تثبيت نسخة ثانية على منفذ مختلف
sudo bash run.sh --destination /opt/odoo-two --port 11019 --chat 21019

# مع تحديد كلمات مرور مخصصة
sudo bash run.sh --destination /opt/odoo-one --port 10019 --chat 20019 --password admin123 --db-password dbpass123
```

**وسائط السكربت:**
- `--destination`: مسار التثبيت (مثال: `odoo-one` أو `/opt/odoo-one`)
- `--port`: منفذ HTTP (الافتراضي: `10019`)
- `--chat`: منفذ الدردشة الحية (الافتراضي: `20019`)
- `--password`: كلمة مرور الماستر لـ Odoo (اختياري)
- `--db-password`: كلمة مرور قاعدة بيانات PostgreSQL (اختياري)

---

## الطريقة الثالثة: التثبيت اليدوي الكامل (خطوة بخطوة)

إذا كنت تريد التحكم الكامل في كل خطوة:

### 1. نسخ ملفات التكوين
```bash
cp etc/odoo.conf etc/odoo.conf.bak
cp docker-compose.yml docker-compose.yml.bak
```

### 2. تعديل المنافذ (اختياري)
افتح ملف `docker-compose.yml` وقم بتعديل المنافذ:

```yaml
ports:
  - "10019:8069"      # المنفذ الأول: المضيف:pContainer
  - "20019:8072"      # منفذ الدردشة الحية
```

### 3. تعديل إعدادات Odoo
افتح ملف `etc/odoo.conf` وقم بتعديل الإعدادات حسب الحاجة:

```ini
[options]
admin_passwd = admin
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo19
addons_path = /mnt/extra-addons
```

### 4. بناء وتشغيل الحاويات
```bash
sudo docker compose build
sudo docker compose up -d
```

### 5. التحقق من حالة الحاويات
```bash
sudo docker compose ps
sudo docker logs -f odoo19
sudo docker logs -f odoo19-db
```

---

## إدارة الحاويات

| العملية | الأمر |
|---------|-------|
| تشغيل | `sudo docker compose up -d` |
| إعادة تشغيل | `sudo docker compose restart` |
| إيقاف | `sudo docker compose stop` |
| إيقاف وحذف الحاويات | `sudo docker compose down` |
| إيقاف وحذف الحاويات والأحجام | `sudo docker compose down -v` ⚠️ (يحذف بيانات قاعدة البيانات) |
| عرض السجلات | `sudo docker compose logs -f` |
| عرض السجلات لخدمة محددة | `sudo docker compose logs -f odoo19` |

---

## تشغيل نسخ متعددة من Odoo 19 على نفس الجهاز

يمكنك تشغيل نسخ متعددة مع تحديد مجلدات ومنافذ مختلفة لكل نسخة:

```bash
# النسخة الأولى
mkdir -p /opt/odoo19-instance1
cp -r deployment/odoo19/* /opt/odoo19-instance1/
cd /opt/odoo19-instance1
sudo sed -i 's/10019:8069/10019:8069/g' docker-compose.yml
sudo sed -i 's/20019:8072/20019:8072/g' docker-compose.yml
sudo docker compose up -d

# النسخة الثانية (على منافذ مختلفة)
mkdir -p /opt/odoo19-instance2
cp -r deployment/odoo19/* /opt/odoo19-instance2/
cd /opt/odoo19-instance2
sudo sed -i 's/10019:8069/11019:8069/g' docker-compose.yml
sudo sed -i 's/20019:8072/21019:8072/g' docker-compose.yml
sudo docker compose up -d
```

---

## حفظ واستعادة النسخة الاحتياطية

### نسخ احتياطي لقاعدة البيانات
```bash
sudo docker exec odoo19-db pg_dump -U odoo postgres > backup_odoo19_$(date +%Y%m%d).sql
```

### استعادة قاعدة البيانات
```bash
sudo docker exec -i odoo19-db psql -U odoo postgres < backup_odoo19.sql
```

### نسخ احتياطي للمجلدات (Filestore)
```bash
sudo tar -czvf odoo19_filestore_backup.tar.gz addons etc postgresql
```

---

## استكشاف الأخطاء وإصلاحها

### مشكلة الصلاحيات (Permission Denied)
```bash
sudo chmod -R 777 addons
sudo chmod -R 777 etc
sudo chmod -R 777 postgresql
sudo chown -R $USER:$USER .
```

### مشكلة في عدد مراقبات الملفات (inotify)
```bash
if grep -qF "fs.inotify.max_user_watches" /etc/sysctl.conf; then
  echo $(grep -F "fs.inotify.max_user_watches" /etc/sysctl.conf)
else
  echo "fs.inotify.max_user_watches = 524288" | sudo tee -a /etc/sysctl.conf
fi
sudo sysctl -p
```

### порт مضبوط بالفعل (Port Already in Use)
```bash
sudo ss -tuln | grep 10019
# إذا كان المنفذ مستخدماً، غير المنفذ في docker-compose.yml ثم أعد التشغيل
sudo docker compose down
sudo docker compose up -d
```

### التحقق من أن PostgreSQL يعمل
```bash
sudo docker exec odoo19-db pg_isready -U odoo
```

---

## البنية الداخلية للمجلد

```
deployment/odoo19/
├── docker-compose.yml          # تعريف خدمات Docker (Odoo + PostgreSQL)
├── docker-compose.traefik.yml  # تكوين ترافيك (اختياري)
├── run.sh                      # سكربت التشغيل السريع
├── entrypoint.sh               # نقطة دخول الحاوية
├── etc/
│   ├── odoo.conf               # إعدادات Odoo
│   ├── logrotate               # تدوير السجلات
│   └── requirements.txt        # متطلبات بايثون
├── addons/                     # الإضافات المخصصة
├── postgresql/                 # بيانات قاعدة البيانات (يتم إنشاؤه تلقائياً)
├── instances/                  # إعدادات النسخ المتعددة
├── scripts/
│   ├── install-odoo19.sh       # سكربت التثبيت عبر Ansible
│   ├── backup.sh               # سكربت النسخ الاحتياطي
│   └── health-check.sh         # فحص صحة الخدمة
├── ansible/                    # ملفات أنسابيل للنشر التلقائي
├── config/
│   ├── odoo.conf               # تكوين Odoo مستقل
│   └── odoo.standalone.conf    # تكوين Standalone
├── README.md
├── LICENSE
└── Jenkinsfile                 # مسار النشر عبر Jenkins
```

---

## ملاحظات هامة

1. **لا تستخدم `sudo docker compose down -v` إلا إذا كنت تريد حذف جميع بيانات قاعدة البيانات permanently.**
2. **احتفظ بنسخة احتياطية من مجلد `postgresql` قبل أي عملية تحديث أو حذف.**
3. **إذا كنت تنقل المجلد بين أجهزة، تأكد من أن جميع الأجهزة لديها نفس إصدار Docker.**
4. **لتغيير كلمة مرور الماستر، عدل ملف `etc/odoo.conf` ثم أعد تشغيل الحاوية.**
5. **هذا الدليل مخصص للتثبيت المحلي اليدوي. للنشر عبر أنابيب النشر (CI/CD) استخدم ملف `Jenkinsfile` أو ملفات أنسبيل في مجلد `ansible/`.**

---

## الدعم

للاستفسارات أو الإبلاغ عن مشاكل، راجع ملف `README.md` أو افتح قضية (Issue) في المستودع على GitHub.
