# عقد REST API

هذه هي الواجهة المعتمدة للقالب. المسارات الجديدة تستخدم بادئة `/api/v1/`. المسارات نفسها متاحة غالبًا تحت `/api/` للتوافق، لكن تطبيقات العملاء الجديدة يجب أن تستعمل الإصدار المرقّم.

## الاستجابات

كل الاستجابات تستخدم الغلاف التالي:

```json
{
  "success": true,
  "message": "",
  "data": {},
  "errors": null
}
```

عند الفشل تكون `success` مساوية لـ`false`، ويظهر وصف مختصر في `message` و`error`، وتظهر تفاصيل التحقق في `errors` عند توفرها. لا تعتمد التطبيقات على نص الرسالة لاتخاذ قرار؛ استخدم حالة HTTP وبنية الخطأ.

القائمة المرقّمة تعيد `data.items` و`data.meta`. معاملات القائمة القياسية هي `page` و`page_size`، والحد الأقصى لحجم الصفحة 100. يرسل المثال المحايد معامل البحث `q`.

## المصادقة

| العملية | المسار | المصادقة |
| --- | --- | --- |
| الحصول على زوج JWT | `POST /api/v1/auth/token/` | عامة |
| تجديد JWT | `POST /api/v1/auth/token/refresh/` | refresh token في الجسم |
| التحقق من JWT | `POST /api/v1/auth/token/verify/` | token في الجسم |
| الملف الشخصي | `GET /api/v1/auth/me` | `Authorization: Bearer <access>` |
| تسجيل الخروج وإبطال refresh | `POST /api/v1/auth/logout` | Bearer؛ أرسل `refresh` اختياريًا في الجسم |
| جلسة الويب | `POST /api/v1/auth/login` | CSRF والجلسة |

نجاح تسجيل الدخول يعيد `data.access` و`data.refresh` و`data.user`. وتبقى `access` و`refresh` في المستوى الأعلى لتوافق العملاء الأقدم. يعيد التجديد الغلاف نفسه، ويدوّر refresh token عند تفعيله. تعامل مع الرمز المجدد باعتباره الرمز الوحيد الصالح.

## وحدة المثال المحايدة

تتطلب جميع عمليات العناصر صلاحيات الوحدة المناسبة. مستخدم الإدارة يملك الصلاحيات الافتراضية.

| العملية | المسار | المدخلات |
| --- | --- | --- |
| قائمة وبحث | `GET /api/v1/modules/example/items/?q=...&page=1&page_size=20` | لا شيء |
| إنشاء | `POST /api/v1/modules/example/items/create/` | `name`, `code`, `description?`, `quantity?` |
| تفاصيل | `GET /api/v1/modules/example/items/{id}/` | لا شيء |
| تعديل جزئي | `PATCH /api/v1/modules/example/items/{id}/update/` | أي من حقول العنصر |
| حذف | `DELETE /api/v1/modules/example/items/{id}/delete/` | لا شيء |

`name` و`code` مطلوبان عند الإنشاء؛ `code` فريد، و`quantity` عدد صحيح غير سالب. تعرض القائمة `items` وبيانات الصفحة في `meta`.

## مسارات النواة

- `GET /api/v1/capabilities/` يعرض إصدار العقد والوحدات المركبة.
- `GET /api/v1/dashboard/stats` يعرض ملخص اللوحة.
- `/api/v1/audit-logs` لسجل التدقيق.
- `/api/v1/settings/` لإعدادات النظام والقوائم المرجعية.
- `/api/v1/backup/` لعمليات النسخ الاحتياطي، وهي محمية بصلاحيات الإدارة.

راجع المخطط المنشور في `/api/v1/schema/` للتفاصيل الحالية لكل مسار.

## النسخ الاحتياطي والاستعادة

تتطلب القائمة `backup.view` أو صلاحية عرض البنية التحتية. إنشاء/تعديل/تشغيل
السياسات يتطلب `backup.create` أو `infrastructure_manage`؛ والسياسة المفعلة
تمنح موافقة صريحة على النسخ الحي المجدول. جميع القوائم مرقمة، ولا يعرض
Serializer الأثر مرجع التخزين الداخلي.

| العملية | المسار | المدخلات |
| --- | --- | --- |
| قائمة/إنشاء السياسات | `GET/POST /api/v1/backups/policies/` | `name`, `service`, `template`, `retention_count`, `interval_minutes`, `enabled` |
| تفاصيل/تعديل السياسة | `GET/PATCH /api/v1/backups/policies/{id}/` | أي حقول قابلة للتعديل |
| تشغيل Backup | `POST /api/v1/backups/policies/{id}/run/` | `mode: dry_run|live`, و`confirm: true` للحي، و`variables?` |
| قائمة artifacts | `GET /api/v1/backups/artifacts/` | `status?`, `host?`, `service?`, `policy?`, `page?`, `page_size?` |
| تحديث artifact | `POST /api/v1/backups/artifacts/{id}/refresh/` | لا شيء |
| طلب Restore | `POST /api/v1/backups/artifacts/{id}/restore/` | `template_id`, `mode`, `variables?`; وللحي `confirm: true` و`confirm_restore: "RESTORE"` |

تتطلب الاستعادة `backup.restore` أو `backup_restore` وصلاحيات تنفيذ Automation
ومدير المهام. يبدأ Restore بـdry-run؛ ولا يقبل live إلا بعد نجاح dry-run سابق
لنفس artifact والقالب ومجموعة المتغيرات، ثم يلزم التأكيد وكتابة `RESTORE`.
مرجع artifact يحقنه النظام ولا يقبله من العميل. تعيد طلبات التشغيل `202` عند
إرسالها إلى مدير المهام، و`503` إذا تعذر الإرسال؛ نجاح Semaphore وحده لا يثبت
سلامة محتوى الملف.

## الإشعارات

جميع مسارات الإشعارات تتطلب جلسة أو JWT، وتكون محصورة بالمستخدم الحالي دون
صلاحية إدارية لقراءة سجلات الآخرين. القوائم مرقمة بمعاملات `page` و`page_size`.

| العملية | المسار | المدخلات |
| --- | --- | --- |
| قائمة الإشعارات | `GET /api/v1/notifications/?unread=true|false` | اختياري `unread`; يعاد عدد غير المقروء في `data.meta.unread_count` |
| تعليم إشعار كمقروء | `POST /api/v1/notifications/{id}/read/` | لا شيء |
| تعليم الكل كمقروء | `POST /api/v1/notifications/read-all/` | لا شيء |
| قراءة التفضيلات | `GET /api/v1/notifications/preferences/` | لا شيء |
| تعديل التفضيلات | `PATCH /api/v1/notifications/preferences/` | `{"preferences":[{"category":"alert","in_app_enabled":true,"email_enabled":false}]}` |

الفئات المقبولة هي `alert`, `backup`, `automation`, `task`, و`security`.
التفضيلات الافتراضية داخل التطبيق مفعلة والبريد معطل. يتطلب تفعيل البريد
عنوانًا صالحًا في حساب المستخدم. حالة البريد (`not_enabled`, `pending`,
`sending`, `sent`, `failed`, `suppressed`) لا تعني إلا حالة محاولة backend؛ لا تثبت وصول
البريد إلى صندوق المستلم. يعيد كل عنصر `email_status`، مع عدم إظهار أخطاء
التوصيل الداخلية أو عنوان بريد أي مستخدم آخر.

## سجل الخوادم والبنية التحتية

كل المسارات التالية لها بادئة `/api/v1/servers/`، وتعيد غلاف الاستجابة
الموحد. القائمة مرقمة بمعاملات `page` و`page_size`، ويدعم البحث `q` ومرشحات
`environment`, `connection_status`, `group`, و`tag`.

| العملية | المسار | الصلاحية |
| --- | --- | --- |
| قائمة الخوادم | `GET /` | `server.view` أو `infrastructure_view` |
| تسجيل خادم | `POST /` | `server.create` أو `infrastructure_manage` |
| تفاصيل خادم ولقطته | `GET /{id}/` | `server.view` أو `infrastructure_view` |
| تعديل الجرد | `PATCH /{id}/` | `server.update` أو `infrastructure_manage` |
| قائمة/إنشاء مجموعات | `GET /groups/`, `POST /groups/` | عرض الخوادم / `infrastructure_manage` |
| قائمة/إنشاء وسوم | `GET /tags/`, `POST /tags/` | عرض الخوادم / `infrastructure_manage` |
| تاريخ المزامنة | `GET /{id}/sync-history/` | `server.view` أو `infrastructure_view` |
| إرسال اختبار اتصال | `POST /{id}/test-connection/` | `server.connect` أو `infrastructure_manage`؛ و`task.view` أو `tasks_manage` |
| إرسال اكتشاف | `POST /{id}/discover/` | `server.discover` أو `server.view` أو `infrastructure_view`؛ و`task.view` أو `tasks_manage` |

تقبل عمليات الإنشاء والتعديل معرفات `groups` و`tags` ومؤشر `credential_id`
اختياريًا؛ لا تعيد الاستجابات بيانات الاعتماد أو قيمها المشفرة، بل تعيد
`has_credential` فقط. تتطلب العمليات المرسلة توفر مدير المهام، وتعيد `202`
ومعرف المهمة؛ عند تعطيل الإرسال تعيد `503` ولا تنفذ fallback متزامنًا. اختبار
الاتصال والاكتشاف المباشر المتاحان في لوحة الويب مساران للقراءة محدودان
ومنفصلان عن واجهة API غير المتزامنة.

يحتوي `latest_snapshot` في تفاصيل الخادم على `source`, `status`, `captured_at`,
`is_stale`, `collection_duration_ms`, و`availability` و`data`. يعيد API
حالة حداثة اللقطة صراحةً؛ على المستهلكين عدم عرض لقطة `is_stale=true` على أنها
قياس حالي. يجمع الاكتشاف المحلي معلومات Linux للقراءة فقط تشمل النظام والمعالج
والذاكرة والتخزين والواجهات والمسارات والمنافذ والخدمات والعمليات ومؤشرات
توافر الأدوات. يظهر قياس التخزين المفصل تحت `data.storage`، مع إبقاء
`data.disks` قائمة filesystems للتوافق. كل قسم في `availability` مستقل، وقد
يكون `available` أو `unavailable` أو `unsupported`؛ القيمة الصفرية قياس حقيقي
وليست علامة على غياب القياس.

## مدير المهام

تتطلب جميع المسارات مصادقة جلسة أو Bearer وصلاحية المهام المناسبة. الاستجابات
تستخدم غلاف API الموحد؛ لا تعيد بيانات metadata الداخلية أو بيانات الاعتماد.

| العملية | المسار | الصلاحية |
| --- | --- | --- |
| قائمة مرقمة | `GET /api/v1/tasks/?status=&operation=&target_server=&page=&page_size=` | `task.view` أو `tasks_manage` |
| تفاصيل وسجل | `GET /api/v1/tasks/{uuid}/` | `task.view` أو `tasks_manage` |
| طلب إلغاء | `POST /api/v1/tasks/{uuid}/cancel/` | `task.cancel` أو `tasks_manage` |
| إعادة محاولة مؤهلة | `POST /api/v1/tasks/{uuid}/retry/` | `task.retry` أو `tasks_manage`، إضافة لصلاحية العملية الأصلية |

الإلغاء قبل التنفيذ يحول المهمة إلى `cancelled`. أثناء تنفيذ عملية لا تدعم
المقاطعة يسجل كطلب ولا يدعي النظام إيقافها؛ ينفذ العامل الإلغاء إذا وصل الطلب
قبل بدء المحول. إعادة المحاولة متاحة فقط لحالة `failed` أو `timeout` قبل بلوغ
حد المحاولات، وتعاد مراجعة صلاحية العملية والهدف والتأكيد قبل الإرسال. عند
تعطيل الطابور لا يحدث تنفيذ متزامن بديل.

## أتمتة Ansible عبر Semaphore

هذه المرحلة توسع لوحة الويب الحالية ولا تضيف REST API جديدًا؛ كل مسارات
الأفعال تتطلب جلسة مصادقًا عليها وCSRF:

| العملية | المسار | الصلاحية |
| --- | --- | --- |
| عرض الكتالوج | `GET /dashboard/automation/templates/` | `infrastructure_view` أو `server.view` |
| إنشاء قالب معطل | `POST /dashboard/automation/templates/create/` | `automation.playbook.create` أو `infrastructure_manage` |
| اعتماد/تعطيل قالب | `POST /dashboard/automation/templates/{id}/toggle/` | `automation.playbook.create` أو `infrastructure_manage` |
| حفظ جدولة اختبار جاف | `POST /dashboard/automation/templates/{id}/schedule/` | `automation.playbook.create` أو `infrastructure_manage` |
| طلب تشغيل | `POST /dashboard/automation/templates/{id}/run/` | `automation.playbook.execute` و`task.view` |
| تفاصيل/تحديث التشغيل | `GET /dashboard/automation/runs/{id}/`, `POST .../{id}/refresh/` | عرض البنية التحتية |

طلب التشغيل يقبل `mode=dry_run` افتراضيًا، أو `mode=live` مع `confirm=yes`
وقيم `confirm_restore=RESTORE` الإضافية لاستعادة النسخ. يمكن إرسال
`variables_json` ككائن JSON من مفاتيح معلنة في مخطط القالب؛ الأنواع scalar هي
string وinteger وboolean. ترفض المفاتيح غير المعلنة أو الحساسة، وتُحفظ القيم
المشفرة ولا تضاف إلى بيانات المهمة أو السجلات. كل قالب معتمد يقتصر على خادم
واحد مفعل وحد Ansible مطابق صريح من `ManagedHost.ansible_limit`؛ لا تقبل
المسارات `all` أو wildcards.

تُرسل عمليات التشغيل إلى `/api/v1/tasks/` داخليًا عبر Infrastructure Engine؛
استجابة لوحة التشغيل تعيد توجيه المستخدم، بينما تظهر حالة مهمة Semaphore في
`AutomationRun` بعد التحديث. الأمر
`python manage.py dispatch_due_automation_schedules` يطلق الجداول الدورية
بوضع dry-run فقط ويجب جدولتُه من النظام كل دقيقة.

## Docker

تتطلب جميع المسارات مصادقة وصلاحية Docker المناسبة. تسجيل المحرك واكتشافه
والأفعال لا تتصل بالمحرك داخل طلب الويب؛ الأفعال تُرسل إلى Task Manager.

| العملية | المسار | الصلاحية | المدخلات/النتيجة |
| --- | --- | --- | --- |
| قائمة المحركات | `GET /api/v1/docker/engines/` | `docker.container.view` | قائمة مرقمة |
| تسجيل محرك محلي | `POST /api/v1/docker/engines/` | `docker.engine.manage` | `server_id`؛ يعيد `201` |
| تفاصيل وجرد المحرك | `GET /api/v1/docker/engines/{id}/` | `docker.container.view` | الجرد محفوظ ومحدود إلى 500 عنصر لكل نوع |
| إرسال اكتشاف | `POST /api/v1/docker/engines/{id}/discover/` | `docker.container.view` و`task.view` أو `tasks_manage` | جسم فارغ؛ يعيد `202` ومعرف المهمة |
| فعل حاوية | `POST /api/v1/docker/engines/{id}/containers/{container_id}/{action}/` | صلاحية الفعل و`task.view` أو `tasks_manage` | `{"confirmation": true}` فقط؛ يعيد `202` ومعرف المهمة |

الأفعال هي `start`, `stop`, `restart`, `pause`, `resume`, و`remove`. يتطلب
`remove` صلاحية `docker.container.delete`، ولكل فعل آخر صلاحية
`docker.container.{action}`. `INFRA_DOCKER_WRITE_ENABLED` معطل افتراضيًا؛
تظل عمليات التغيير خلف Engine والعامل ولا تعمل عند غياب الإرسال.
يعيد مسار الاكتشاف `503` إذا كان `INFRA_DOCKER_READ_ENABLED` معطلًا.

يقتصر endpoint على Unix socket المحلي. واجهة الويب تعرض بيانات آخر اكتشاف
ناجح وتصرح بتقادمها؛ سجلات الحاويات تقرأ عبر Docker SDK، وتقبل `tail` من 1
إلى 200، وتعيد محتوى منقحًا ومحدود الحجم. لا توجد API لتنفيذ أوامر داخل
الحاويات أو إدارة ملفاتها.

## المزامنة دون اتصال

يستخدم Android عنوانًا موحدًا للمزامنة: `POST /api/v1/sync/` لإرسال العمليات و`GET /api/v1/sync/` لسحب البيانات. يحمل كل عنصر دفع `operation_id` ثابتًا من UUID و`kind` و`payload`. يحتفظ الخادم بالنتيجة في المعاملة نفسها التي تنفذ التغيير؛ إعادة UUID من المستخدم نفسه تعيد النتيجة المحفوظة من دون تكرار الأثر. لا تُعاد نتيجة عملية مستخدم إلى حساب آخر.

يدعم قالب المثال الأنواع `example.item.create` و`example.item.update` و`example.item.delete`، مع صلاحية `example_manage`. يرسل التعديل `id` و`data`، ويمكنه تضمين `base_updated_at` الذي أعاده الخادم. التعديل القديم يُرفض كـ`conflict` ويُحفظ مع بيانات التعارض للمراجعة. يكتب الحذف سجل tombstone ضمن معاملة العملية.

يرسل السحب `since` (المؤشر السابق الذي أعاده الخادم) و`models` اختيارية مفصولة بفواصل، مثل `example.item`. تعيد الاستجابة `rows` حسب المجموعة، و`tombstones`، ومؤشرًا جديدًا. الوحدات تسجل مجموعات السحب ومعالجات العمليات في ملف `sync.py` الخاص بها؛ لا تفترض النواة نماذج مجال بعينها. التسجيل يقبل `queryset(user=...)` و`scope_key(user=...)` لعزل صفوف وعمليات حذف المؤسسات. تظهر المجموعات وأنماط المزامنة في `/api/v1/capabilities/`.

السحب الحالي يعيد كل تغييرات المجموعات المطلوبة ضمن المؤشر في استجابة واحدة. أضف paging token قبل استخدامه لمجموعة كبيرة أو تطبيق عالي الحجم.

## التوافق مع Flutter

يستخدم تطبيق Flutter `AuthApi` و`SessionManager` و`ApiInterceptor` للمصادقة والتجديد، و`ExampleItemsApi` للمثال نفسه. تغطي اختبارات Django عمليات CRUD عبر JWT، وتغطي اختبارات Flutter صيغة القائمة والمسارات والطلبات والاستجابات المغلفة. لا توجد تهيئة لخادم إنتاج حي ضمن اختبار الوحدة.

يحفظ Android طابورًا محليًا مع UUID ثابت، ومحاولات مؤجلة بتراجع زمني، ويستخدم المنسق المشترك لإرسال النتائج وتطبيق الصفوف والحذف ثم تثبيت المؤشر. يحدد البناء المجموعات المدعومة عبر `SYNC_MODELS`؛ القيمة الافتراضية `example.item`.

## المراقبة والتنبيهات

تتطلب جميع المسارات مصادقة وصلاحية المراقبة المناسبة، وتستخدم غلاف الاستجابة
الموحد. القوائم مرقمة بمعاملات `page` و`page_size` (بحد أقصى 100).

| العملية | المسار | الصلاحية |
| --- | --- | --- |
| أهداف القياس وحالة آخر محاولة | `GET /api/v1/monitoring/targets/` | `monitoring.view` أو `infrastructure_view` أو `server.view` |
| عينات القياس | `GET /api/v1/monitoring/samples/?host={id}&since={ISO-8601}` | صلاحية القراءة |
| تاريخ محاولات الجمع | `GET /api/v1/monitoring/collections/?host={id}&status=success\|failed` | صلاحية القراءة |
| قائمة/إنشاء قواعد | `GET/POST /api/v1/monitoring/rules/` | قراءة / `monitoring.alert.manage` أو `infrastructure_manage` |
| تفاصيل/تعديل قاعدة | `GET/PATCH/PUT /api/v1/monitoring/rules/{id}/` | قراءة / صلاحية إدارة القواعد |
| الأحداث | `GET /api/v1/monitoring/alerts/?host={id}&state=open\|acknowledged\|resolved\|all` | صلاحية القراءة |
| إقرار حدث مفتوح | `POST /api/v1/monitoring/alerts/{id}/acknowledge/` | `monitoring.alert.acknowledge` أو إدارة التنبيهات/البنية التحتية |

تقبل النسب حدودًا من 0 إلى 100، وفترة التهدئة من 1 إلى 1440 دقيقة. القياس
المفقود لا يتحول إلى صفر ولا يحل حدثًا قائمًا. يعرض الهدف حالة آخر محاولة؛
تظهر تفاصيل محاولات الجمع الفاشلة في `/collections/`. تشغيل
`python manage.py collect_infra_metrics` من cron/systemd timer يجمع القياسات،
ويقيم القواعد وينشئ إشعارات المستلمين المؤهلين ثم يطبق الاحتفاظ. البريد لا
يرسل داخل الجامع؛ يشغّل `python manage.py dispatch_pending_notifications` من
جدولة منفصلة لمعالجة outbox وإعادة المحاولات. يعيد أمر الجمع حالة فشل غير
صفرية إذا تعذر موفر القياس.

## التقارير

تحتاج كل معاينة إلى `reports.view` وصلاحية قراءة المجال المقابل. يتطلب كل
تصدير الصلاحيتين `reports.view` و`reports.export` وصلاحية المصدر أيضًا.
الكتالوج لا يعرض أنواع التقارير غير المسموح بها. التقارير للقراءة فقط وتعتمد
سجلات المصدر الحالية؛ لا تعرض مراجع التخزين أو بيانات الاعتماد أو سجلات
المهام الخام.

| العملية | المسار | الصلاحية |
| --- | --- | --- |
| كتالوج الأنواع المصرح بها | `GET /api/v1/reports/` | `reports.view` |
| معاينة مرقمة | `GET /api/v1/reports/{slug}/?from=&to=&host=&page=&page_size=` | `reports.view` وصلاحية المصدر |
| تصدير CSV أو PDF | `GET /api/v1/reports/{slug}/export/?format=csv\|pdf&from=&to=&host=` | `reports.view`, `reports.export`, وصلاحية المصدر |

الأنواع هي `servers` (`server.view`)، و`alerts` (`monitoring.view`)،
و`tasks` (`task.view`)، و`backups` (`backup.view`). تقبل `from` و`to`
تاريخ ISO-8601 أو timestamp، مع مدى أقصى 365 يومًا، و`host` معرفًا موجبًا.
حجم المعاينة الأقصى 100 صف للصفحة؛ التصدير يرفض أكثر من 5000 صف CSV أو
300 صف PDF. لا يسجل AuditLog محتوى الصفوف؛ يسجل المستخدم والنوع والصيغة
والمرشحات وعدد الصفوف لكل تنزيل ناجح.
