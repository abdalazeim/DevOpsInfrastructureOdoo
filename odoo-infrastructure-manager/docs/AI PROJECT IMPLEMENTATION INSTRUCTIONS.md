# AI PROJECT IMPLEMENTATION INSTRUCTIONS
## Build New Project Using the Existing Django Enterprise Template

### 1. قاعدة أساسية
- القالب الحالي **جاهز ومعتمد**.
- لا تعيد بناء الـTemplate.
- لا تغيّر الـCore Architecture إلا عند وجود سبب تقني واضح.
- لا تنشئ Architecture جديدة للمشروع.
- استخدم الـTemplate كنقطة البداية الإلزامية.
- أضف فقط ما يخص المشروع الجديد.

### 2. افهم المشروع أولًا
قبل كتابة أي كود:

1. افهم هدف المشروع.
2. حدد المستخدمين والأدوار.
3. حدد العمليات الرئيسية.
4. حدد الـBusiness Workflow.
5. حدد البيانات المطلوبة.
6. حدد العلاقات بين البيانات.
7. حدد الصلاحيات.
8. حدد التقارير المطلوبة.
9. حدد الـIntegrations المطلوبة.
10. حدد المتطلبات غير الوظيفية:
   - Security
   - Performance
   - Scalability
   - Audit
   - Backup
   - Responsive UI

**لا تبدأ البرمجة قبل فهم المشروع.**

### 3. تحليل المتطلبات
حوّل المتطلبات إلى:

```text
Requirements
    ↓
Modules
    ↓
Features
    ↓
Entities
    ↓
Workflows
    ↓
Permissions
    ↓
UI Pages
    ↓
APIs
    ↓
Tests
```

يجب أن يكون لكل Requirement مكان واضح داخل النظام.

### 4. تحديد Modules
حدد Business Modules المطلوبة فقط.

مثال:

```text
Core
Accounts

Business Modules:
├── Module A
├── Module B
├── Module C
└── Module D
```

- لا تضف Module غير مطلوب.
- لا تضع Business Logic داخل Core.
- اجعل كل Module مسؤولًا عن نطاق محدد.
- قلل الترابط بين Modules.

### 5. تصميم Business Architecture
لكل Module حدد:

- الهدف
- المسؤولية
- Entities
- Models
- Services
- Repositories عند الحاجة
- Views
- Forms
- Serializers
- Permissions
- URLs
- Reports
- Tests

استخدم:

```text
Module
 ├── Models
 ├── Services
 ├── Repositories
 ├── Views
 ├── Forms
 ├── Serializers
 ├── Permissions
 ├── URLs
 └── Tests
```

### 6. تصميم قاعدة البيانات
قبل إنشاء Models:

1. حدد Entities.
2. حدد Attributes.
3. حدد Primary Keys.
4. حدد Foreign Keys.
5. حدد One-to-One.
6. حدد One-to-Many.
7. حدد Many-to-Many.
8. حدد Constraints.
9. حدد Unique Fields.
10. حدد Indexes عند الحاجة.
11. حدد Audit Requirements.
12. حدد Soft Delete عند الحاجة.

ثم حوّل التصميم إلى Django Models.

**لا تنشئ Models عشوائيًا أثناء البرمجة.**

### 7. Business Rules
حدد Business Rules قبل كتابة Services.

لكل عملية حدد:

```text
Input
 ↓
Validation
 ↓
Business Rules
 ↓
Transaction
 ↓
Database Changes
 ↓
Audit
 ↓
Notification
 ↓
Result
```

ضع القواعد داخل **Service Layer** وليس داخل Templates أو JavaScript.

### 8. Workflow
لكل عملية رئيسية ارسم Workflow واضحًا.

مثال:

```text
Draft
 ↓
Submitted
 ↓
Approved
 ↓
Processed
 ↓
Completed
```

حدد:
- من يستطيع تنفيذ كل خطوة.
- ما شروط الانتقال.
- ما الذي يحدث عند الرفض.
- ما الذي يمكن تعديله.
- ما الذي يتم تسجيله في Audit Log.

### 9. Permissions
أنشئ Permission Matrix قبل بناء الواجهات.

مثال:

| Role | View | Create | Edit | Delete | Approve |
|---|---|---|---|---|---|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ |
| Manager | ✓ | ✓ | ✓ | ✗ | ✓ |
| User | ✓ | ✓ | ✗ | ✗ | ✗ |

لا تعتمد على إخفاء الزر فقط.

**الصلاحيات يجب أن تُطبق Backend أيضًا.**

### 10. Services
لكل عملية Business مهمة أنشئ Service مناسبًا.

مثال:

```text
CreateService
UpdateService
ApproveService
RejectService
DeleteService
ProcessService
```

لا تضع Business Logic الكبير داخل:
- Views
- Forms
- Serializers
- Templates

### 11. Transactions
استخدم Transactions عندما تحتوي العملية على أكثر من تغيير مترابط.

مثال:

```text
Create Document
+
Update Related Data
+
Create Audit Log
+
Create Notification
```

يجب أن تكون العملية Atomic عند الحاجة.

### 12. API
إذا كان المشروع يحتاج API:

- استخدم DRF الموجود في القالب.
- استخدم `/api/v1/`.
- حافظ على Response Format الموحد.
- طبق Authentication.
- طبق Permissions.
- طبق Validation.
- طبق Pagination.
- أضف API Tests.

لا تنشئ API مختلفًا عن Standard القالب.

### 13. Frontend
استخدم Django Templates الموجودة في القالب.

لا تنشئ Frontend Architecture جديدة إلا إذا كان هناك سبب واضح.

استخدم:

```text
Base
 ↓
Layout
 ↓
Page
 ↓
Components
 ↓
Partials
```

أعد استخدام Components الموجودة قبل إنشاء Components جديدة.

### 14. Responsive UI
كل Page جديدة يجب أن تكون:

- Responsive
- Mobile First
- Touch Friendly
- RTL/LTR
- Accessible

اختبر على الأقل:

```text
320px
360px
390px
414px
768px
1024px
1366px
1920px
```

يمنع:
- Horizontal Overflow
- Broken Tables
- Overlapping Elements
- Hidden Actions
- Unusable Forms

### 15. RTL / LTR
المشروع يجب أن يعمل بشكل صحيح مع:

```text
Arabic → RTL
English → LTR
```

استخدم Logical CSS Properties.

لا تضع `left/right` بشكل يؤدي إلى كسر الاتجاه الآخر.

### 16. UI/UX
قبل إنشاء كل Page حدد:

```text
Page Purpose
↓
User Role
↓
Data
↓
Actions
↓
Permissions
↓
States
↓
Validation
↓
Error Handling
```

كل Page يجب أن تحتوي على حالات واضحة مثل:

- Loading
- Empty
- Success
- Error
- Permission Denied

### 17. Search / Filter / Pagination
للقوائم الكبيرة استخدم:

- Search
- Filters
- Sorting
- Pagination

لا تحمل جميع البيانات إلى المتصفح بدون حاجة.

### 18. Reports
لكل Report حدد:

- البيانات
- Filters
- Permissions
- Sorting
- Export
- Print
- PDF عند الحاجة

اجعل Reports متوافقة مع Desktop وMobile وPrint.

### 19. Notifications
حدد متى يحتاج النظام إلى:

- In-App Notification
- Email
- Alert
- System Message

ولا تضف Notifications بدون Business Requirement.

### 20. Audit
كل عملية حساسة يجب أن تكون قابلة للتتبع.

مثل:

```text
CREATE
UPDATE
DELETE
APPROVE
REJECT
LOGIN
LOGOUT
STATUS CHANGE
```

ويجب معرفة:
- المستخدم
- الوقت
- العملية
- العنصر
- القيم القديمة والجديدة عند الحاجة

### 21. Security
أثناء التطوير يجب الالتزام بـ:

- Authentication
- Authorization
- CSRF
- XSS Protection
- SQL Injection Protection
- Secure Cookies
- Input Validation
- Permission Checks
- Secrets خارج Git
- Secure File Uploads
- Audit Logging

لا تؤجل Security إلى نهاية المشروع.

### 22. Development Sequence
اتبع هذا الترتيب:

```text
1. Requirements
       ↓
2. Business Analysis
       ↓
3. Modules
       ↓
4. Database Design
       ↓
5. Business Rules
       ↓
6. Workflows
       ↓
7. Permissions
       ↓
8. Models
       ↓
9. Services
       ↓
10. Forms / Serializers
       ↓
11. Views / APIs
       ↓
12. Templates / UI
       ↓
13. Reports
       ↓
14. Notifications
       ↓
15. Tests
       ↓
16. Security Review
       ↓
17. Responsive Review
       ↓
18. Documentation
       ↓
19. Deployment
```

### 23. Development by Module
لا تبنِ النظام كاملًا دفعة واحدة.

ابنِ:

```text
Module
 ↓
Database
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
Review
```

ثم انتقل إلى Module التالي.

### 24. Testing
كل Feature جديدة يجب أن تحتوي على Tests مناسبة.

اختبر:

- Models
- Services
- Permissions
- Forms
- APIs
- Views
- Business Rules
- Workflows

ثم اختبر التكامل بين Modules.

### 25. Migration
بعد تعديل Models:

```bash
python manage.py makemigrations
python manage.py makemigrations --check
python manage.py migrate
```

لا تحذف Migrations مستخدمة.

### 26. Code Review
بعد كل Module راجع:

- Clean Code
- SOLID
- DRY
- KISS
- Security
- Performance
- Naming
- Dependencies
- Transactions
- Permissions
- Tests
- Documentation

### 27. لا تقم بـ Overengineering
استخدم أبسط Architecture تحقق المطلوب.

لا تضف:
- Microservices
- Repository
- Abstraction
- Design Pattern
- Service
- Package

إلا عندما يكون له سبب حقيقي.

**Reuse existing Template architecture first.**

### 28. عدم كسر القالب
قبل تعديل أي جزء من Core:

1. تحقق هل يمكن تنفيذ المطلوب داخل Module.
2. تحقق هل يوجد Component أو Service جاهز.
3. تحقق هل يمكن Extension بدل Modification.
4. لا تعدل Core إلا عند الضرورة.

الأولوية:

```text
Reuse
 ↓
Extend
 ↓
Customize Module
 ↓
Modify Core فقط عند الضرورة
```

### 29. Performance
من البداية راعِ:

- Database Indexes
- Query Optimization
- `select_related`
- `prefetch_related`
- Pagination
- Caching عند الحاجة
- Lazy Loading
- Optimized Images
- Efficient JavaScript

تجنب N+1 Queries.

### 30. Documentation
وثّق المشروع أثناء البناء وليس بعد الانتهاء فقط.

وثّق:

- Project Overview
- Modules
- Architecture
- Database
- Workflows
- Permissions
- API
- Installation
- Configuration
- Deployment
- Backup
- Troubleshooting

### 31. Final Validation
قبل اعتبار المشروع مكتملًا تحقق من:

```text
✓ Requirements
✓ Modules
✓ Database
✓ Business Rules
✓ Workflows
✓ Permissions
✓ Services
✓ API
✓ UI/UX
✓ Responsive
✓ RTL/LTR
✓ Security
✓ Audit
✓ Notifications
✓ Reports
✓ Testing
✓ Performance
✓ Documentation
✓ Deployment
✓ Backup/Recovery
```

### 32. قاعدة العمل مع AI
عند إعطاء AI أي Feature جديدة:

1. افهم المطلوب.
2. حدد الـModule المناسب.
3. افحص Architecture الحالية.
4. أعد استخدام الموجود.
5. حدد Database Changes.
6. حدد Business Rules.
7. حدد Permissions.
8. نفذ Service Layer.
9. نفذ API/View.
10. نفذ UI.
11. أضف Tests.
12. اختبر Security.
13. اختبر Responsive.
14. حدّث Documentation.
15. لا تنتقل للميزة التالية قبل نجاح الاختبارات.

### FINAL RULE

**استخدم القالب الجاهز كما هو، ولا تعيد بناءه.**

المشروع الجديد =

```text
Existing Enterprise Template
            +
     Project Requirements
            +
     Business Modules
            +
      Project Features
```

وليس:

```text
Existing Template
        ↓
Rebuild Architecture
        ↓
Create New Framework
```

الهدف النهائي:

**Build the new business system on top of the existing enterprise template while preserving its architecture, security, coding standards, reusable components, testing strategy, deployment structure, and maintainability.**