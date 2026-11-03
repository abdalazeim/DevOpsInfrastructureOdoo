# STANDARD PROJECT BUILD RULES
## Fixed Django Enterprise Architecture

### 1. القاعدة الأساسية

كل مشروع جديد يجب أن يبدأ من **نفس الـEnterprise Template والـArchitecture الثابتة**.

ممنوع إنشاء Architecture مختلفة لمشروع جديد.

الاختلاف بين المشاريع يكون فقط في:

```text
Business Requirements
        ↓
Business Modules
        ↓
Models
        ↓
Services
        ↓
Views / APIs
        ↓
Pages / Reports
```

أما الـCore Architecture فتبقى ثابتة.

---

# 2. Supported Deployment Modes

يجب أن يدعم المشروع وضعين رئيسيين:

### Desktop / Local

```text
Windows
   ↓
EXE
   ↓
Django
   ↓
SQLite
   ↓
db.sqlite3
```

الاستخدام:
- Local
- Offline
- Desktop
- Windows
- Small installations

### Server / Production

```text
Internet / LAN
      ↓
    Nginx
      ↓
   Gunicorn
      ↓
    Django
      ↓
 PostgreSQL 16
```

الاستخدام:
- Production
- Server
- Cloud
- Multiple Users
- LAN / Internet

---

# 3. Database Strategy

استخدم قاعدة البيانات حسب البيئة:

| Environment | Database |
|---|---|
| Development | SQLite |
| Testing | SQLite |
| Desktop | SQLite |
| Production | PostgreSQL 16+ |

يجب أن يعمل المشروع بنفس Django Codebase مع تغيير Configuration فقط.

لا تنشئ نسخة Django مختلفة للـDesktop وServer.

---

# 4. Fixed Project Structure

كل مشروع جديد يجب أن يبدأ بهذا الهيكل:

```text
Project/
│
├── manage.py
├── requirements.txt
├── requirements-desktop.txt
├── .env
├── .env.example
├── README.md
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── desktop.py
│   │
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   │
│   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   ├── validators/
│   │   ├── permissions/
│   │   ├── exceptions/
│   │   ├── utils/
│   │   └── signals.py
│   │
│   ├── accounts/
│   │   ├── models/
│   │   ├── views/
│   │   ├── services/
│   │   ├── selectors/
│   │   ├── permissions/
│   │   ├── forms/
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   └── modules/
│       ├── module_a/
│       ├── module_b/
│       └── module_c/
│
├── templates/
│   ├── base.html
│   ├── layouts/
│   ├── components/
│   ├── partials/
│   └── pages/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── vendor/
│
├── media/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│   ├── backup/
│   ├── restore/
│   └── feature_three/
│
├── desktop/
│   ├── launcher.py
│   ├── build.py
│   └── icon.ico
│
├── deployment/
│   ├── docker/
│   ├── nginx/
│   └── gunicorn/
│
└── docs/
```

**هذا الهيكل Standard ولا يتم تغييره إلا لسبب تقني حقيقي.**

---

# 5. Core Architecture

`apps/core/` يحتوي فقط على الوظائف المشتركة بين جميع المشاريع.

مثل:

```text
Core
├── Base Models
├── Common Services
├── Validators
├── Permissions
├── Exceptions
├── Utilities
├── Signals
├── Audit
├── Notifications
├── Common Helpers
└── Shared Infrastructure
```

### ممنوع

وضع Business Logic خاص بالمشروع داخل Core.

مثال ممنوع:

```text
core/
└── feature_one/
```

أو:

```text
core/
└── feature_two/
```

---

# 6. Accounts Architecture

`apps/accounts/` مسؤول عن كل ما يتعلق بالمستخدمين:

```text
Authentication
Authorization
Users
Roles
Groups
Permissions
Profiles
Sessions
Password Management
```

يجب أن يكون Accounts قابلًا لإعادة الاستخدام في جميع المشاريع.

---

# 7. Business Modules

كل وظيفة Business جديدة يجب أن تكون داخل:

```text
apps/modules/
```

مثال:

```text
apps/modules/
├── feature_three/
├── feature_two/
├── feature_one/
└── feature_four/
```

لكن لا تضف Module إلا إذا كان المشروع يحتاجه.

---

# 8. Standard Module Structure

أي Business Module جديد يجب أن يتبع نفس البنية:

```text
module/
│
├── models/
├── services/
├── selectors/
├── repositories/
├── views/
├── serializers/
├── forms/
├── permissions/
├── urls.py
├── admin.py
└── tests/
```

### المسؤوليات

**Models**
- Database structure
- Relationships
- Constraints

**Selectors**
- READ operations
- Query logic
- Data retrieval

**Services**
- Business Logic
- CREATE
- UPDATE
- DELETE
- Workflow
- Transactions

**Repositories**
- Database abstraction عند الحاجة فقط.

**Views**
- HTTP handling
- Request/Response orchestration

**Serializers**
- API validation
- Data transformation

**Forms**
- Django form validation/UI handling

**Permissions**
- Access control

---

# 9. Fixed Data Flow

يجب اتباع هذا التدفق:

```text
Request
   ↓
URL
   ↓
View
   ↓
Serializer / Form
   ↓
Service
   ↓
Selector ──────→ READ
   │
   └────────────→ Model → WRITE
                       ↓
                    Database
```

### القاعدة

**READ**

```text
View
 ↓
Selector
 ↓
Database
```

**WRITE**

```text
View
 ↓
Form/Serializer
 ↓
Service
 ↓
Model
 ↓
Database
```

ولا تضع Business Logic داخل View.

---

# 10. Service Layer Rule

أي Business Operation معقدة يجب أن تكون داخل Service.

مثال:

```text
CreateDocumentService
ApproveDocumentService
RejectDocumentService
UpdateDocumentService
DeleteDocumentService
ProcessDocumentService
```

الـService مسؤول عن:

```text
Validation
+
Business Rules
+
Transaction
+
Database Changes
+
Audit
+
Notifications
```

---

# 11. Selector Rule

استخدم Selectors لعمليات القراءة المعقدة.

مثال:

```text
get_active_records()
get_by_status()
get_user_records()
get_dashboard_statistics()
```

لا تضع Query Logic المعقد داخل Views.

---

# 12. Transaction Rule

عند وجود أكثر من عملية مترابطة:

```text
Service
   ↓
transaction.atomic()
   ↓
Operation A
   ↓
Operation B
   ↓
Audit
   ↓
Notification
```

إما نجاح العملية كاملة أو Rollback.

---

# 13. API Standard

إذا كان المشروع يحتاج API:

```text
/api/v1/
```

مثال:

```text
/api/v1/auth/
/api/v1/users/
/api/v1/<module>/
```

يجب استخدام نفس API Architecture الموجودة في Template.

لا تنشئ API Architecture مختلفة.

---

# 14. Frontend Standard

استخدم Django Templates الموجودة في القالب.

التسلسل:

```text
base.html
    ↓
layouts
    ↓
pages
    ↓
components
    ↓
partials
```

أعد استخدام Components الموجودة قبل إنشاء Components جديدة.

---

# 15. Responsive Standard

كل مشروع جديد يجب أن يكون:

```text
Mobile First
Responsive
Touch Friendly
RTL/LTR
Accessible
Desktop Optimized
```

ويعمل على:

```text
Mobile
Tablet
Laptop
Desktop
Ultra-Wide
```

بدون إنشاء نسخة منفصلة.

---

# 16. RTL / LTR

يجب دعم:

```text
Arabic → RTL
English → LTR
```

كل Component يجب أن يعمل في الاتجاهين.

استخدم CSS Logical Properties.

لا تجعل التصميم يعتمد بشكل صلب على:

```text
left
right
```

---

# 17. Security Standard

كل مشروع جديد يجب أن يرث Security Architecture من Template.

يجب تطبيق:

```text
Authentication
Authorization
Permissions
CSRF
XSS Protection
SQL Injection Protection
Secure Cookies
HTTPS
Secure Headers
Environment Secrets
Audit Logging
File Upload Security
```

لا تؤجل Security إلى نهاية المشروع.

---

# 18. Testing Standard

كل Module يجب أن يحتوي على Tests.

يجب توفير:

```text
tests/
├── unit/
├── integration/
└── e2e/
```

واختبار:

```text
Models
Services
Selectors
Permissions
Forms
Views
APIs
Business Rules
Workflows
```

---

# 19. Documentation Standard

كل مشروع يجب أن يحتوي على:

```text
docs/
├── architecture/
├── development/
├── deployment/
├── database/
├── api/
└── security/
```

ويجب توثيق:

- Architecture
- Modules
- Database
- Workflows
- Permissions
- API
- Installation
- Configuration
- Deployment
- Backup
- Security

---

# 20. Desktop Standard

عند الحاجة إلى نسخة Windows:

```text
desktop/
├── launcher.py
├── build.py
└── icon.ico
```

استخدم:

```text
PyInstaller
```

والـDesktop يستخدم:

```text
config.settings.desktop
```

وقاعدة البيانات:

```text
SQLite
```

ويجب أن يكون:

```text
Offline Capable
```

ولا يؤثر Desktop Configuration على Production.

---

# 21. Server Standard

Production يجب أن يعمل:

```text
Client
 ↓
Nginx
 ↓
Gunicorn
 ↓
Django
 ↓
PostgreSQL 16
```

ولا يستخدم:

```text
python manage.py runserver
```

في Production.

---

# 22. Docker Standard

إذا تم استخدام Docker:

```text
Docker
├── Django
├── PostgreSQL
└── Nginx
```

ويجب أن يكون المشروع قابلًا للتشغيل بواسطة:

```bash
docker compose up -d
```

---

# 23. Environment Configuration

استخدم:

```text
.env
.env.example
```

ولا تضع:

```text
Passwords
API Keys
Secret Keys
Database Credentials
Tokens
```

داخل Git.

---

# 24. Development Workflow

عند بناء أي مشروع جديد اتبع هذا التسلسل الإجباري:

```text
1. Requirements
       ↓
2. Business Analysis
       ↓
3. Modules Definition
       ↓
4. Database Design
       ↓
5. Entity Relationships
       ↓
6. Business Rules
       ↓
7. Workflows
       ↓
8. Permissions
       ↓
9. Models
       ↓
10. Selectors
       ↓
11. Services
       ↓
12. Forms / Serializers
       ↓
13. Views / APIs
       ↓
14. Templates / UI
       ↓
15. Reports
       ↓
16. Notifications
       ↓
17. Tests
       ↓
18. Security Review
       ↓
19. Responsive Review
       ↓
20. Documentation
       ↓
21. Deployment
```

---

# 25. Module Development Workflow

لا تبنِ كل النظام دفعة واحدة.

لكل Module:

```text
Requirements
 ↓
Database
 ↓
Models
 ↓
Selectors
 ↓
Services
 ↓
Permissions
 ↓
Views/API
 ↓
UI
 ↓
Tests
 ↓
Security Review
 ↓
Documentation
```

بعد اكتمال Module وانتقاله إلى حالة مستقرة، ابدأ Module التالي.

---

# 26. AI Development Rule

عند إعطاء AI Feature جديدة، يجب عليه اتباع:

```text
Understand
   ↓
Identify Module
   ↓
Check Existing Components
   ↓
Design
   ↓
Implement
   ↓
Test
   ↓
Security Review
   ↓
Responsive Review
   ↓
Document
```

ويجب على AI **فحص الـTemplate الحالي وإعادة استخدام الموجود** قبل إنشاء أي شيء جديد.

---

# 27. ممنوعات أساسية

AI ممنوع من:

- إعادة بناء الـTemplate.
- تغيير Architecture بدون سبب.
- إنشاء Core جديد.
- وضع Business Logic داخل Core.
- وضع Business Logic داخل Templates.
- وضع Business Logic كبير داخل Views.
- تكرار Components الموجودة.
- تكرار Services الموجودة.
- Hard-Coded Configuration.
- Secrets داخل Git.
- إنشاء Microservices بدون حاجة حقيقية.
- إنشاء Frontend منفصل بدون Requirement.
- إنشاء Desktop Code منفصل عن Business Logic.
- كسر توافق SQLite/PostgreSQL.
- حذف Migrations مستخدمة.
- تجاهل Tests.
- تجاهل Security.
- تجاهل Responsive Design.

---

# 28. Database Compatibility Rule

أي Model أو Query أو Feature جديد يجب اختباره بحيث يعمل مع:

```text
SQLite
        +
PostgreSQL 16
```

قدر الإمكان.

لا تستخدم Database-specific functionality إلا إذا كانت هناك حاجة واضحة.

---

# 29. Final Quality Gate

قبل اعتماد أي Module:

```text
✓ Architecture
✓ Database
✓ Models
✓ Selectors
✓ Services
✓ Permissions
✓ Forms
✓ API
✓ Views
✓ UI
✓ Responsive
✓ RTL/LTR
✓ Security
✓ Audit
✓ Tests
✓ Performance
✓ Documentation
```

---

# 30. FINAL PROJECT PRINCIPLE

كل مشروع جديد يجب أن يكون:

```text
                EXISTING TEMPLATE
                       │
          ┌────────────┴────────────┐
          │                         │
        CORE                    ACCOUNTS
          │                         │
          └────────────┬────────────┘
                       │
                BUSINESS MODULES
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Module A     Module B     Module C
```

والـCore Architecture تبقى ثابتة.

---

# FINAL RULE

**Build Every New Project Using the Same Architecture.**

المشروع الجديد لا يعيد اختراع Architecture.

بل:

```text
Existing Enterprise Template
            +
Project Requirements
            +
Business Modules
            =
New Enterprise Application
```

### قاعدة ثابتة:

**Architecture ثابتة — Modules متغيرة — Business Logic معزولة — Database قابلة للتبديل — Deployment متعدد — Codebase واحد.**

الهدف:

**نفس المشروع ونفس الـCodebase يعمل على Windows/EXE/SQLite محليًا، وعلى Server/Nginx/Gunicorn/PostgreSQL 16 في الإنتاج.**