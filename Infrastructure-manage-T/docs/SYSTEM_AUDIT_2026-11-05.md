# 🔍 دراسة النظام ومراجعة الأخطاء — 2026-11-05

> **التاريخ:** 2026-11-05  
> **المشروع:** Infrastructure-manage-T  
> **النوع:** دراسة نظام ومراجعة أخطاء  
> **البيئة:** Windows / Python 3.14  
> **الحالة:** غير مكتمل (يتطلب اختبار end-to-end على Ubuntu)

---

## 📋 جدول المحتويات

1. [النتيجة وحدود الفحص](#-النتيجة-وحدود-الفحص)
2. [كيف يعمل النظام](#-كيف-يعمل-النظام)
3. [أخطاء النسخ والاستعادة — أولوية عالية](#-أخطاء-النسخ-والاستعادة—أولوية-عالية)
4. [أخطاء التثبيت والتشخيص — أولوية عالية](#-أخطاء-التثبيت-والتشخيص—أولوية-عالية)
5. [Traefik وAnsible وقوالب النشر](#-Traefik-وAnsible-وقوالب-النشر)
6. [فجوات المتطلبات والإعدادات](#-فجوات-المتطلبات-والإعدادات)
7. [ترتيب المعالجة والتحقق المطلوب](#-ترتيب-المعالجة-والتحقق-المطلوب)
8. [تحديث حالة الإصلاح — 2026-11-05](#-تحديث-حالة-الإصلاح—2026-11-05)

---

## 1. 📝 النتيجة وحدود الفحص

النظام الحالي مدير بنية تحتية عبر Terminal، لكن مسارات النشر والنسخ والاستعادة ليست متكاملة بعد. توجد أعطال تمنع التثبيت، وأخرى تعطي حالة نجاح غير صحيحة، وأخطاء في الاستعادة قد تترك البيانات ناقصة. لا أوصي باعتماد مسارات الاستعادة الحالية على بيانات إنتاجية قبل إصلاحها وتجربة استعادة كاملة.

هذه قائمة بالعيوب التي أمكن إثباتها أو تحديد شروطها من النسخة الحالية، وليست ضماناً باكتشاف كل عيب ممكن. تمت قراءة الكود، تشغيل اختبارات Python، تحليل ملفات Python وYAML، ومحاكاة حالات محددة دون تثبيت برامج أو إيقاف حاويات أو استعادة قواعد بيانات. البيئة Windows/Python 3.14؛ لم يتوفر Bash أو Docker أو Ansible لتجربة نشر Ubuntu كاملة.

| # | الأسلوب | النتيجة |
|---|---------|--------|
| 1 | الاختبارات | `python -B -m unittest discover tests -v` — نجح 85 اختباراً. |
| 2 | تحليل AST | 40 ملف Python داخل app دون أخطاء تركيبية. |
| 3 | تحليل YAML | 105 ملفات yml دون أخطاء تركيبية أو مفاتيح عادية مكررة؛ هذا لا يشمل قوالب Jinja ولا يثبت صحة معاملات Ansible. |
| 4 | محاكاة | أثبتت NameError في قائمة Traefik، وتجاوز المكونات غير المثبتة، والتعرف الخاطئ على Odoo، وتكوين أوامر إصلاح بلا docker، والاستمرار إلى أمر تابع بعد فشل سابق. |

لم أعدل ملفات التشغيل. توجد تعديلات كثيرة سابقة في مساحة العمل؛ التقرير يصف محتواها الحالي ولا ينسبها لهذه المراجعة.

---

## 2. ⚙️ كيف يعمل النظام

1. `app/main.py` يقرأ action/profile/dry-run ويبدأ واجهة نصية أو Textual أو workflow مباشر.
2. `app/models/profile.py` و`app/validators` يعرّفان إعدادات البنية والتحقق منها. أضيفت `app/config/hostname_config.py` كمصدر آخر للنطاقات وأسماء المضيف.
3. `app/ui/app.py` ينسق القوائم، اكتشاف الأدوات، تثبيتها، التشخيص، الإصلاح، وإدارة Odoo وTraefik وJenkins.
4. `app/services` تتضمن فحص البيئة، خطط التثبيت، تشغيل الأوامر، Docker، النسخ الاحتياطية، والمثبت التسلسلي. بعضها يستخدم subprocess مباشرة وبعضها يمر عبر طبقة تنفيذ مشتركة.
5. `app/workflows` يبني خطوات تجهيز الخادم ونشر Traefik وOdoo 17/18/19 والنشر الكامل. المسار القديم يستدعي `automation/scripts`.
6. `deployment` يحتوي عائلات نشر مستقلة: MultiVersion، MultiInstance، ومجلدات odoo17/18/19، ولكل منها بعض مزيج Shell وAnsible وCompose وJenkins.
7. البيانات المستهدفة موزعة بين `/opt/odoo-infrastructure` و`/opt/odooXX` و`/data/odooXX`، مع أسماء حاويات مفردة وأخرى تتضمن instance. لذلك لا يستطيع كل فاحص أو سكريبت نسخ التعامل تلقائياً مع ما ينشئه مسار آخر.

الاعتماد على Terminal تحقق في نقطة الدخول، لكنه لا يعني أن Portainer وpgAdmin بلا واجهة ويب؛ هذه خدمات يديرها البرنامج. المشكلة المعمارية الأهم هي تكرار التنفيذ ومصادر الإعدادات، لا غياب React أو وجوده.

---

## 3. ⚠️ أخطاء النسخ والاستعادة — أولوية عالية

| # | الكود | الموقع | المشكلة |
|---|-------|--------|---------|
| F01 | `backup.sh` و `restore.sh` | `deployment/Odoo-MultiVersion-Deployment/scripts/` | ناتج backup.sh لا يطابق ما يتطلبه restore.sh. الأول يكتب ملفات بتاريخ داخل مجلد instance؛ الثاني يطلب مجلد BACKUP_ID يحتوي manifest.json وchecksums.sha256. |
| F02 | `backup.sh:78` | `deployment/Odoo-MultiVersion-Deployment/scripts/` | أمر النسخ يستخدم خيار Docker غير صالح: `docker exec -T` غير صالح؛ الخيار -T يخص docker compose exec، وليس docker exec. |
| F03 | `restore.sh` | `deployment/Odoo-MultiVersion-Deployment/scripts/` | استعادة Shell تخفي الفشل وتختار قاعدة غير مستهدفة. يشغل psql على قاعدة postgres وبالمستخدم postgres، ثم `|| true` ويطبع النجاح. |
| F04 | السكريبت السابق | `deployment/Odoo-MultiVersion-Deployment/scripts/` | فحص ملفات الاستعادة يعامل النجمة كحرف. التعبير `[ -f "${BACKUP_PATH}/filestore_*.tar.gz" ]` لا يوسع wildcard. |
| F05 | السكريبت السابق | `deployment/Odoo-MultiVersion-Deployment/scripts/` | خيار new-instance يستعيد على النسخة الأصلية. NEW_INSTANCE_NAME يستخدم للطباعة فقط؛ المسارات وأسماء الحاويات بقيت مشتقة من INSTANCE الأصلي. |
| F06 | السكريبت السابق | `deployment/Odoo-MultiVersion-Deployment/scripts/` | نسخة الأمان ليست ضماناً قبل الاستبدال. ينسخ مجلد البيانات الحي قبل إيقاف Odoo، دون إيقاف PostgreSQL أو آلية نسخ متسقة. |
| F07 | `restore/tasks/main.yml:18` | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/restore/` | قراءة خاطئة لنتائج Ansible stat. يستخدم backup_stat.exists وmanifest_stat.exists وchecksums_stat.exists؛ النتيجة داخل `.stat.exists`. |
| F08 | `restore/tasks/main.yml` | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/restore/` | ترتيب ونقل ملف dump في Ansible مكسوران. ينفذ psql قبل نقل الملف. |
| F09 | `backup/tasks/main.yml` | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/backup/` | دور Ansible للنسخ لا يبني المسارات ونتائج الحلقات بصورة صحيحة. |
| F10 | `system_backup.py:28` | `app/services/` | full_snapshot لا يحتوي فعلياً قواعد البيانات. include_db_dumps غير مستخدم. |
| F11 | `system_backup.py:142` | `app/services/` | استعادة snapshot لا تتحقق من SHA256 المحفوظ. |
| F12 | `automation/scripts/restore-db.sh` | `automation/scripts/` | استعادة قاعدة البيانات القديمة قد تنجح جزئياً وتعلن النجاح. لا يتحقق checksum قبل حذف القاعدة المستهدفة. |
| F13 | `automation/scripts/backup-db.sh` و `deployment/Odoo-MultiVersion-Deployment/docker/odoo17-compose.yml.j2` | `automation/scripts/` و `deployment/` | فجوة حفظ filestore ودعم Odoo18. السكريبت القديم يقبل 17/19 فقط. |
| F14 | `restore-system-config.sh:121` | `deployment/Odoo-MultiVersion-Deployment/scripts/` | استعادة إعدادات النظام تنشئ مجلدات متداخلة. `cp -a source/netplan/ /etc/netplan/` عند وجود الوجهة ينسخ مجلد netplan داخلها. |

---

## 4. 🚨 أخطاء التثبيت والتشخيص — أولوية عالية

| # | الكود | الموقع | المشكلة |
|---|-------|--------|---------|
| F15 | `app/ui/app.py:694,723` | `app/ui/app.py` | قائمة Traefik تتعطل بمتغير غير معرف. dry_run ليس وسيطاً ولا متغيراً محلياً. |
| F16 | `app/ui/app.py:1289` | `app/ui/app.py` | تعديل النطاق يفشل عند حفظ الإعداد. set_config غير مستورد. |
| F17 | `app/ui/app.py:1145,1168,1182,1197,1215` | `app/ui/app.py` | المثبت التسلسلي يتجاوز الأدوات غير الموجودة. صياغة lambda تعيد `(True, (False, None))` عند غياب المكون. |
| F18 | `app/ui/app.py` | `app/ui/app.py` | خطوة Traefik التسلسلية لا تثبت Traefik. الأوامر تنشئ شبكة ومجلدات وacme.json فقط. |
| F19 | `sequential_installer.py` | `app/services/` | فشل خطوة لا يوقف الخطوات التابعة داخل المكون. تسجل الحلقة الفشل ثم تكمل الخطوة التالية. |
| F20 | `sequential_installer.py` | `app/services/` | صلاحيات التسجيل والتحقق النهائي غير مكتملين. إنشاء /var/log/odoo-installer يتم من Python دون رفع صلاحيات. |
| F21 | `ansible_service.py:86,187` | `app/services/` | مثبت Ansible لا يكتب السكريبت الذي بناه. يبني script_content ثم يعيد أوامر tee/chmod/bash فقط دون تمرير المحتوى إلى tee. |
| F22 | `odoo_service.py:43` | `app/services/` | اكتشاف Odoo يخلط قاعدة مستقلة بتثبيت Odoo. أي صورة postgres مطابقة تكفي لتقرير installed، حتى دون Odoo. |
| F23 | `odoo_service.py:128,143,205` و `jenkins_service.py:301,312` | `app/services/` | أوامر الإصلاح تحاول تشغيل start بدل docker start. fix_command يبدأ بـstart، والإصلاح يضيف sudo فقط. |
| F24 | `odoo_service.py` و `jenkins_service.py` | `app/services/` | بعض فحوص الحالة والمنافذ تعطي إنذارات غير صحيحة. تصنيف بعض حالات الحاوية يعتمد على استبعاد Exited/Created وليس اشتراط running. |
| F25 | `app/main.py:39` وما بعده | `app/main.py` | dry-run لا يشمل جميع نقاط الدخول. --dry-run لا يمرر إلى القوائم الافتراضية وTextual. |
| F26 | `app/main.py` و `app/ui/app.py` | `app/main.py` و `app/ui/app.py` | فشل العمليات لا ينعكس دائماً على حالة CLI. main لا يحول نتيجة فشل العمليات إلى exit غير صفري. |

---

## 5. 🌐 Traefik وAnsible وقوالب النشر

| # | الكود | الموقع | المشكلة |
|---|-------|--------|---------|
| F27 | `traefik_manager.py:845` | `app/services/` | مثبت Traefik لا يتحمل شبكة موجودة ولا يكمل صلاحيات sudo. ينشئ proxy بلا فحص وجودها؛ وهذا يفشل بعد تجهيز الخادم مسبقاً. |
| F28 | `traefik_manager.py:753` وما بعده | `app/services/` | إعداد Traefik الجديد لا يحقق لوحة التحكم المعلنة. dashboard مفعل مع insecure=false، لكن Compose لا يحدد router إلى api@internal. |
| F29 | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/docker/tasks/main.yml:28` ومثيله odoo18 | `deployment/` | معاملات Ansible وحقول النتائج غير صحيحة. docker_compose_v2 لا يقبل restart_policy كمعامل للموديول. |
| F30 | دور docker في MultiVersion وodoo18 | `deployment/` | entrypoint المولد لا يستطيع تشغيل أمر Odoo. entrypoint محتواه `exec "$@"`، لكن command يبدأ بـ`--config=...`. |
| F31 | `deployment/Odoo-MultiVersion-Deployment/ansible/roles/docker/tasks/main.yml` و `docker/odoo17-compose.yml.j2` و `docker/odoo19-compose.yml.j2` | `deployment/` | قوالب MultiVersion لا تتلقى متغيرات instance وتكرر environment. الحلقة تمرر item، بينما القالب يطلب container_name/db_user/data_path كمتغيرات مستقلة دون mapping في المهمة. |
| F32 | `deployment/odoo17/ansible/roles/odoo/tasks` و `deployment/odoo19/ansible/playbooks/install.yml` و `roles/odoo/tasks/main.yml` | `deployment/` | أدوار Odoo17/19 غير مكتملة الربط. Odoo17 يحتوي deploy_instance.yml دون tasks/main.yml لاستدعائه. |
| F33 | `deployment/odoo17/scripts/install-odoo17.sh:20` وما بعده | `deployment/odoo17/scripts/` | سكريبت Odoo17 الخاص يجمع عدة أعطال مستقلة. PROJECT_ROOT يصل إلى deployment ثم SOURCE_DIR يضيف deployment مرة ثانية. |
| F34 | `deployment/Odoo-MultiVersion-Deployment/Jenkins/restore.Jenkinsfile:50` | `deployment/` | Jenkins restore يحتوي توسعة shell غير صالحة. داخل sh بثلاث علامات اقتباس مفردة تظل `${env.BUILD_NUMBER}` نصاً لـshell. |

---

## 6. 📋 فجوات المتطلبات والإعدادات

| # | الكود | الموقع | الفجوة |
|---|-------|--------|--------|
| F35 | `app/config/hostname_config.py` و `profiles` و `templates/env.template` و خدمات/سكريبتات النشر | `app/config/` و `profiles/` | إعدادات الهوية والمسارات ليست مصدراً واحداً. يوجد اكتشاف تلقائي للhostname إضافة إلى YAML و.env وقيم ثابتة في السكريبتات. |
| F36 | `app/ui/app.py`، مكون Portainer التسلسلي، وخدمات التثبيت الحالية | `app/ui/app.py` | Portainer وpgAdmin لا يطابقان تماماً الطلب السابق. المسار التسلسلي ما زال يستخدم 9000 وربط /srv/portainer بدلاً من الطلب الأخير 9443 وportainer_data. |
| F37 | `deployment/odoo17/scripts/install-odoo17.sh` و `deployment/odoo19/ansible/roles/odoo/tasks/main.yml` و `app/services/system_backup.py` | `deployment/` و `app/services/` | أسرار افتراضية وصلاحيات أرشيف غير مفروضة. توجد fallbacks لكلمات مرور مثل odoo17/odoo19، كما لا تفرض خدمة snapshot صلاحية مقيدة على أرشيف يجمع .env. |

---

## 7. 🔢 ترتيب المعالجة والتحقق المطلوب

1. إصلاح عقد النسخ والاستعادة F01–F14 أولاً، ثم تجربة استعادة إلى قاعدة مستقلة مع سجل ومرفق Odoo وفحصهما بعد الاستعادة، وتجربة أرشيف تالف وفشل SQL ومساحة غير كافية.
2. إصلاح أعطال القوائم والمثبت F15–F26 وإضافة اختبارات تمنع SKIPPED/نجاح كاذب، مع exit code صحيح.
3. اعتماد مسار نشر واحد وبناء باقي الواجهات فوقه، ثم معالجة F27–F35. تشغيل Ansible syntax-check وrender/compose config لكل إصدار وفرع شبكة، ثم تجربة Ubuntu نظيفة وتجربة إعادة التنفيذ على تثبيت قائم.
4. استكمال Portainer/pgAdmin وتأمين الأسرار، ثم اختبار مستخدم عادي مع sudo وDocker daemon متوقف واسم حاوية محجوز ومنفذ مستخدم.

نجاح الاختبارات الحالية مفيد لكنه لا يثبت نجاح هذه المسارات الجديدة. لا بد من اختبار end-to-end على Ubuntu قبل وصف النظام بأنه جاهز للإنتاج.

---

## 8. 📊 تحديث حالة الإصلاح — 2026-11-05

### النتائج التي تم إصلاحها (P0 – P2)

| النتيجة | الحالة | الجذر | الإصلاح |
|---------|--------|-------|--------|
| N01/N15 — نقطة الدخول لا تعمل | ✓ مُصلح | `run_textual_app` لا يقبل `dry_run` | أُضيف معامل `dry_run` إلى `OdooTextualApp.__init__` و `run_textual_app` |
| N02 — الحاويات العاملة توصف بأنها متوقفة | ✓ مُصلح | `'running' in status.lower()` يفشل مع "Up X hours" | استخدام `status.lower().startswith("up")` |
| N03 — استعادة PostgreSQL مسار ملف خاطئ | ✓ مُصلح | `psql -d postgres` بدلاً من TARGET_DB | استخدام `-d "${TARGET_DB}"`، مستخدم DB من المانيفست |
| N04 — checksum لا يُفحص وfilestore لا يطابق | ✓ مُصلح | اسم ملف الميتاداتا خاطئ | استخراج الاسم من اسم الـ dump بالاستبدال النصي |
| N05 — fallback المرفقات على حاوية DB | ✓ مُصلح | البحث في حاوية PostgreSQL بدلاً من Odoo | استخدام حاوية Odoo في fallback |
| N06 — backup.sh يترك Odoo متوقفاً | ✓ مُصلح | لا يوجد trap لإعادة التشغيل | trap على EXIT يعيد تشغيل Odoo |
| F22 — اكتشاف Odoo خاطئ | ✓ مُصلح | `in` يطابق substring | مطابقة اسم دقيقة `names == f'odoo{version}'` |
| F26 — فشل العمليات يُبلّغ بنجاح | ✓ جزئي | `check=False` مع طباعة نجاح | التقاط return code للتقرير الدقيق |
| F29 — restart_policy و info.State | ✓ مُصلح | معامل غير صحيح، حقل نتيجة خاطئ | `restart_policy: {Name: "always"}`, `.container.State.Status` |
| F33 — install-odoo17.sh brace expansion | ✓ مُصلح | أقواس داخل اقتباس مزدوج | أوامر mkdir منفصلة |
| F34 — Jenkins \${BUILD_NUMBER} في sh | ✓ مُصلح | نص غير مضمن في shell | `$BUILD_NUMBER` بدلاً من `\${BUILD_NUMBER}` |
| N08 — سر PostgreSQL غير مُنشأ | ✓ مُصلح | ملف السر غير موجود | إنشاء ملف السر بصلاحيات 600 ورفعه للحاوية |
| N09 — Odoo بدون اتصال قاعدة أو منافذ | ✓ مُصلح | نقص متغيرات بيئة ومنافذ Traefik | إضافة متغيرات DB، نشر المنافذ، تسميات Traefik |
| N10 — تبعية فاشلة لا تمنع التابعة | ✓ مُصلح | `_failed_components` لا يُحدّث للمتجاوز | إضافة `_blocked_components` في `can_install()` |
| N11 — التقرير يقلب نجاح/فشل | ✓ مُصلح | SKIPPED يُحسب كفشل | `overall_success` لا يحسب SKIPPED |
| N12 — ServerSetupWorkflow يتجاهل profile | ✓ مُصلح | تعريفات مكونات ثابتة | تصفية مكونات Odoo حسب `profile.odooXX.enabled` |

### نتائج الاختبار (الحالية)

| الاختبار | الحالة | النتيجة |
|---------|--------|--------|
| Python syntax check (`compileall app/`) | ✓ ناجح | جميع الملفات تُCompile |
| Import core modules | ✓ ناجح | جميع الاستيرادات تعمل |
| `python app/main.py --help` | ✓ ناجح | exit code 0 |
| 85 unit tests | ✓ ناجح | 85/85 ناجح |
| Docker/Ansible integration | ⏸ متأخر | يحتاج Ubuntu + Docker + Ansible |

### حد الجاهزية للإنتاج (غير متحقق)

لا يمكن اعتبار النظام جاهزاً للإنتاج حتى تتوفر:
- [ ] اختبار end-to-end على نظام Ubuntu نظيف
- [ ] اختبار النسخ والاستعادة على قاعدة بيانات فعلية
- [ ] اختبار نشر Odoo مع اتصال PostgreSQL مؤكد
- [ ] اختبار Traefik مع TLS وشهادات فعلية

---

*تم إعداد هذا التقرير كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
