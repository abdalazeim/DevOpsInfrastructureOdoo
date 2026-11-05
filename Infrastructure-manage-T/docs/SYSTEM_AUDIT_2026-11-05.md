# دراسة النظام ومراجعة الأخطاء — 2026-11-05

## النتيجة وحدود الفحص

النظام الحالي مدير بنية تحتية عبر Terminal، لكن مسارات النشر والنسخ والاستعادة ليست متكاملة بعد. توجد أعطال تمنع التثبيت، وأخرى تعطي حالة نجاح غير صحيحة، وأخطاء في الاستعادة قد تترك البيانات ناقصة. لا أوصي باعتماد مسارات الاستعادة الحالية على بيانات إنتاجية قبل إصلاحها وتجربة استعادة كاملة.

هذه قائمة بالعيوب التي أمكن إثباتها أو تحديد شروطها من النسخة الحالية، وليست ضماناً باكتشاف كل عيب ممكن. تمت قراءة الكود، تشغيل اختبارات Python، تحليل ملفات Python وYAML، ومحاكاة حالات محددة دون تثبيت برامج أو إيقاف حاويات أو استعادة قواعد بيانات. البيئة Windows/Python 3.14؛ لم يتوفر Bash أو Docker أو Ansible لتجربة نشر Ubuntu كاملة.

- الاختبارات: `python -B -m unittest discover tests -v` — نجح 85 اختباراً.
- تحليل AST: 40 ملف Python داخل app دون أخطاء تركيبية.
- تحليل YAML: 105 ملفات yml دون أخطاء تركيبية أو مفاتيح عادية مكررة؛ هذا لا يشمل قوالب Jinja ولا يثبت صحة معاملات Ansible.
- محاكاة: أثبتت NameError في قائمة Traefik، وتجاوز المكونات غير المثبتة، والتعرف الخاطئ على Odoo، وتكوين أوامر إصلاح بلا docker، والاستمرار إلى أمر تابع بعد فشل سابق.
- لم أعدل ملفات التشغيل. توجد تعديلات كثيرة سابقة في مساحة العمل؛ التقرير يصف محتواها الحالي ولا ينسبها لهذه المراجعة.

## كيف يعمل النظام

1. `app/main.py` يقرأ action/profile/dry-run ويبدأ واجهة نصية أو Textual أو workflow مباشر.
2. `app/models/profile.py` و`app/validators` يعرّفان إعدادات البنية والتحقق منها. أضيفت `app/config/hostname_config.py` كمصدر آخر للنطاقات وأسماء المضيف.
3. `app/ui/app.py` ينسق القوائم، اكتشاف الأدوات، تثبيتها، التشخيص، الإصلاح، وإدارة Odoo وTraefik وJenkins.
4. `app/services` تتضمن فحص البيئة، خطط التثبيت، تشغيل الأوامر، Docker، النسخ الاحتياطية، والمثبت التسلسلي. بعضها يستخدم subprocess مباشرة وبعضها يمر عبر طبقة تنفيذ مشتركة.
5. `app/workflows` يبني خطوات تجهيز الخادم ونشر Traefik وOdoo 17/18/19 والنشر الكامل. المسار القديم يستدعي `automation/scripts`.
6. `deployment` يحتوي عائلات نشر مستقلة: MultiVersion، MultiInstance، ومجلدات odoo17/18/19، ولكل منها بعض مزيج Shell وAnsible وCompose وJenkins.
7. البيانات المستهدفة موزعة بين `/opt/odoo-infrastructure` و`/opt/odooXX` و`/data/odooXX`، مع أسماء حاويات مفردة وأخرى تتضمن instance. لذلك لا يستطيع كل فاحص أو سكريبت نسخ التعامل تلقائياً مع ما ينشئه مسار آخر.

الاعتماد على Terminal تحقق في نقطة الدخول، لكنه لا يعني أن Portainer وpgAdmin بلا واجهة ويب؛ هذه خدمات يديرها البرنامج. المشكلة المعمارية الأهم هي تكرار التنفيذ ومصادر الإعدادات، لا غياب React أو وجوده.

## أخطاء النسخ والاستعادة — أولوية عالية

### F01 — ناتج backup.sh لا يطابق ما يتطلبه restore.sh

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh` و`restore.sh`.
الأول يكتب ملفات بتاريخ داخل مجلد instance؛ الثاني يطلب مجلد BACKUP_ID يحتوي manifest.json وchecksums.sha256. لا ينتج الأول هذا العقد. النتيجة: لا يمكن تمرير ناتج النسخ مباشرة إلى الاستعادة. المطلوب صيغة موحدة وإثبات دورة backup→restore.

### F02 — أمر النسخ يستخدم خيار Docker غير صالح

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh:78`.
`docker exec -T` غير صالح؛ الخيار -T يخص docker compose exec، وليس docker exec. يتوقف dump قبل تكوين نسخة صالحة. المصدر: [Docker exec](https://docs.docker.com/reference/cli/docker/container/exec/).

### F03 — استعادة Shell تخفي الفشل وتختار قاعدة غير مستهدفة

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/restore.sh`، قسم PostgreSQL.
يشغل psql على قاعدة postgres وبالمستخدم postgres، ثم `|| true` ويطبع النجاح. لا يختار قاعدة Odoo من manifest ولا يعالج dump بصيغته الصحيحة. كذلك لا يكون المستخدم postgres موجوداً بالضرورة عندما أنشئت الحاوية بـPOSTGRES_USER مختلف. المطلوب استهداف القاعدة/المستخدم الصحيحين، ON_ERROR_STOP، وعدم إصدار النجاح بعد فشل.

### F04 — فحص ملفات الاستعادة يعامل النجمة كحرف

الموضع: السكريبت السابق، فحوص database/filestore/addons/config.
التعبير `[ -f "${BACKUP_PATH}/filestore_*.tar.gz" ]` لا يوسع wildcard. تُتجاوز الملفات الموجودة بأسماء فعلية، وكذلك SQL المؤرخ ما لم يوجد database.dump. المطلوب اكتشاف أسماء الملفات صراحة والتحقق من العدد والصيغة.

### F05 — خيار new-instance يستعيد على النسخة الأصلية

الموضع: السكريبت السابق، قسم new-instance.
NEW_INSTANCE_NAME يستخدم للطباعة فقط؛ المسارات وأسماء الحاويات بقيت مشتقة من INSTANCE الأصلي، والاستعادة حدثت قبل هذا القسم. المطلوب بناء وجهة جديدة كاملة قبل أي كتابة وعدم لمس المصدر.

### F06 — نسخة الأمان ليست ضماناً قبل الاستبدال

الموضع: السكريبت السابق، safety backup وإيقاف/تشغيل الحاويات.
ينسخ مجلد البيانات الحي قبل إيقاف Odoo، دون إيقاف PostgreSQL أو آلية نسخ متسقة، ويتجاهل أخطاء cp وstop/start. قد يواصل الاستعادة دون نسخة أمان صالحة. المطلوب فشل صريح عند تعذر نسخة الأمان وإثبات اتساقها.

### F07 — قراءة خاطئة لنتائج Ansible stat

الموضع: `deployment/Odoo-MultiVersion-Deployment/ansible/roles/restore/tasks/main.yml:18` وما بعده.
يستخدم backup_stat.exists وmanifest_stat.exists وchecksums_stat.exists؛ النتيجة داخل `.stat.exists`. يفشل بوابة التحقق قبل الاستعادة. المصدر: [Ansible stat](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/stat_module.html).

### F08 — ترتيب ونقل ملف dump في Ansible مكسوران

الموضع: الدور السابق، مهام Restore PostgreSQL وCopy database dump.
ينفذ psql قبل نقل الملف. النقل نفسه cp داخل الحاوية لمسار مضيف، وليس docker cp أو mount؛ والمتغير _db_file معرف لمهمة سابقة فقط. كما أن unarchive يأخذ مساراً بنجمة دون اكتشاف الملف. يجب إصلاح المسار كاملاً، لا تبديل ترتيب المهمتين فقط.

### F09 — دور Ansible للنسخ لا يبني المسارات ونتائج الحلقات بصورة صحيحة

الموضع: `deployment/Odoo-MultiVersion-Deployment/ansible/roles/backup/tasks/main.yml`.
إنشاء المجلدات لا يغطي كل وجهات instance/timestamp المستخدمة لاحقاً. نتائج register المتداخلة تُقرأ بمستوى item غير صحيح، منها item.name بدلاً من item.item.name عند استهلاك نتائج dump. كذلك يوجد اختلاف بين تمثيل الإصدار الرقمي وتمثيل odoo17 في المسارات. المطلوب نموذج manifest موحد واختبار الدور ببيانات instance واحدة ثم اثنتين.

### F10 — full_snapshot لا يحتوي فعلياً قواعد البيانات

الموضع: `app/services/system_backup.py:28`.
include_db_dumps غير مستخدم. الأرشيف يجمع مجلدات المشروع و.env وملف ACME محدداً، ولا ينفذ pg_dump ولا يجمع بيانات Odoo الحية. تسمية full snapshot ووصفه الحاليان يوحيان بتغطية لا يقدمها. إما تنفيذها أو توضيح أنه أرشيف إعدادات فقط.

### F11 — استعادة snapshot لا تتحقق من SHA256 المحفوظ

الموضع: `app/services/system_backup.py:142`.
verify_archive يدعم expected_sha256، لكن restore_snapshot يستدعيه دون القيمة؛ لذلك يقبل أرشيفاً قابلاً للقراءة ولو لم يطابق manifest. كما أن مسار ACME المطلق المخزن في tar يستخرج نسبياً تحت target_dir ولا يعاد تلقائياً إلى موقعه التشغيلي. المطلوب تحقق manifest وخريطة استعادة واضحة.

### F12 — استعادة قاعدة البيانات القديمة قد تنجح جزئياً وتعلن النجاح

الموضع: `automation/scripts/restore-db.sh`.
لا يتحقق checksum قبل حذف القاعدة المستهدفة؛ psql يعمل دون ON_ERROR_STOP؛ ووجود أي جداول ليس دليلاً على اكتمال الاستعادة. وعند تغيير اسم القاعدة يُنشأ مجلد filestore بالاسم الجديد لكن tar يعيد الاسم القديم. المطلوب تحقق مسبق، إيقاف عند SQL error، وربط filestore باسم الوجهة.

### F13 — فجوة حفظ filestore ودعم Odoo18

الموضع: `automation/scripts/backup-db.sh` وقوالب Compose ومنها `deployment/Odoo-MultiVersion-Deployment/docker/odoo17-compose.yml.j2`.
السكريبت القديم يقبل 17/19 فقط. بعض القوالب لا تربط /var/lib/odoo بمجلد مضيف معروف، بينما النسخ يبحث عن filestore على المضيف. البيانات قد تبقى في volume تلقائي للصورة لكن لا يلتقطها النسخ الحالي. كما أن اسم ملف filestore المستخدم في تنظيف النسخ القديمة لا يطابق امتداد الأرشيف. المطلوب ربط تخزين صريح واختبار استعادة مرفق فعلي.

### F14 — استعادة إعدادات النظام تنشئ مجلدات متداخلة

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/restore-system-config.sh:121` وما بعده.
`cp -a source/netplan/ /etc/netplan/` عند وجود الوجهة ينسخ مجلد netplan داخلها. يتكرر مع ssh/docker/opt/systemd. لا يعيد المحتويات إلى مواقعها المقصودة. المطلوب نسخ المحتويات مع خطة تحقق وتراجع قبل تفعيل إعدادات الشبكة وSSH.

## أخطاء التثبيت والتشخيص — أولوية عالية

### F15 — قائمة Traefik تتعطل بمتغير غير معرف

الموضع: `app/ui/app.py:694` و`:723` داخل handle_traefik_management.
dry_run ليس وسيطاً ولا متغيراً محلياً. محاكاة فرع التثبيت أعادت NameError. المطلوب تمرير وضع التنفيذ صراحة من نقطة الدخول.

### F16 — تعديل النطاق يفشل عند حفظ الإعداد

الموضع: `app/ui/app.py:1289`.
set_config غير مستورد. يتغير self.hostname_config قبل الفشل، بينما المصدر المشترك لا يتحدث. المطلوب تحديث ذري للمصدرين وحفظ دائم إذا كان المقصود استمرار التعديل بعد إعادة التشغيل.

### F17 — المثبت التسلسلي يتجاوز الأدوات غير الموجودة

الموضع: `app/ui/app.py:1145,1168,1182,1197,1215`.
صياغة lambda تعيد `(True, (False, None))` عند غياب المكون؛ True هو العنصر الأول دائماً. أثبتت المحاكاة ذلك لكل الفحوص الخمسة. النتيجة SKIPPED بدل التثبيت. المطلوب أن يشمل الشرط tuple كاملاً.

### F18 — خطوة Traefik التسلسلية لا تثبت Traefik

الموضع: `app/ui/app.py`، تعريف مكون Traefik داخل handle_sequential_installation.
الأوامر تنشئ شبكة ومجلدات وacme.json فقط؛ لا تنشئ إعداداً كاملاً ولا تشغل container. بعد إصلاح F17 يمكن أن تعلن اكتمال مكون لم يُثبت. المطلوب إعادة استخدام مثبت واحد مع تحقق نهائي.

### F19 — فشل خطوة لا يوقف الخطوات التابعة داخل المكون

الموضع: `app/services/sequential_installer.py`، ComponentInstaller.install.
تسجل الحلقة الفشل ثم تكمل الخطوة التالية. أثبتت المحاكاة تنفيذ أمر ثانٍ بعد فشل الأول. الاستمرار إلى مكون مستقل يختلف عن تشغيل خطوات تعتمد على تثبيت فاشل. المطلوب تعريف التبعيات وإيقاف سلسلة المكون الفاشلة.

### F20 — صلاحيات التسجيل والتحقق النهائي غير مكتملين

الموضع: `app/services/sequential_installer.py`.
إنشاء /var/log/odoo-installer يتم من Python دون رفع صلاحيات رغم use_sudo للأوامر؛ قد يتوقف المستخدم العادي قبل التقرير. بعد نجاح الأوامر تُهمل القيمة المنطقية لفحص التثبيت النهائي. وعند timeout يُقتل process المباشر دون ضمان إنهاء أبنائه. المطلوب مسار log قابل للكتابة، تحقق نهائي ملزم، وإدارة process group.

### F21 — مثبت Ansible لا يكتب السكريبت الذي بناه

الموضع: `app/services/ansible_service.py:86,187`.
يبني script_content ثم يعيد أوامر tee/chmod/bash فقط دون تمرير المحتوى إلى tee. يتوقف tee انتظاراً للمدخل أو يترك ملفاً فارغاً؛ ثم قد ينتهي bash بنجاح دون تثبيت. المطلوب كتابة المحتوى فعلياً والتحقق من ansible-playbook بعده.

### F22 — اكتشاف Odoo يخلط قاعدة مستقلة بتثبيت Odoo

الموضع: `app/services/odoo_service.py:43`.
أي صورة postgres مطابقة تكفي لتقرير installed، حتى دون Odoo. واسم odoo17 مع صورة غير صحيحة يُقبل، بينما حساب collision داخل الفرع نفسه لا يمكن أن يصبح True. أثبتت المحاكاة الحالتين. المطلوب ربط حاويتي التطبيق والقاعدة بهوية المشروع والتحقق من الصورة والحالة.

### F23 — أوامر الإصلاح تحاول تشغيل start بدل docker start

الموضع: `app/services/odoo_service.py:128,143,205` و`app/services/jenkins_service.py:301,312`.
fix_command يبدأ بـstart، والإصلاح يضيف sudo فقط. الناتج المجرب `sudo -n start ...`. المطلوب منشئ أوامر Docker موحد يحافظ أيضاً على host/context والصلاحيات.

### F24 — بعض فحوص الحالة والمنافذ تعطي إنذارات غير صحيحة

الموضع: `app/services/odoo_service.py` و`jenkins_service.py`.
تصنيف بعض حالات الحاوية يعتمد على استبعاد Exited/Created وليس اشتراط running؛ وفحص المنافذ قد يعتبر منفذ الخدمة القائمة تعارضاً معها. مثبت Odoo يفحص منافذ المضيف حتى عند استخدام Traefik دون نشرها، وJenkins يفحص منافذ لا ينشرها Compose. المطلوب مطابقة الحالة والشبكة الفعلية للخطة.

### F25 — dry-run لا يشمل جميع نقاط الدخول

الموضع: `app/main.py:39` وما بعده.
--dry-run لا يمرر إلى القوائم الافتراضية وTextual، وtraefik-backup ينشئ snapshot فعلياً. المستخدم لا يحصل على الوعد المعلن «دون تعديل النظام» لكل action. المطلوب سياق تنفيذ واحد أو رفض هذا الجمع بوضوح.

### F26 — فشل العمليات لا ينعكس دائماً على حالة CLI

الموضع: `app/main.py` و`app/ui/app.py`، أوامر workflows والتحكم بالحاويات.
main لا يحول نتيجة فشل العمليات إلى exit غير صفري، وبعض أوامر lifecycle تستخدم check=False ثم تطبع النجاح. هذا يجعل Jenkins أو shell يعتمد نتيجة ظاهرية غير صحيحة. المطلوب نتيجة موحدة ومخرجات مرتبطة بـreturncode.

## Traefik وAnsible وقوالب النشر

### F27 — مثبت Traefik لا يتحمل شبكة موجودة ولا يكمل صلاحيات sudo

الموضع: `app/services/traefik_manager.py:845`.
ينشئ proxy بلا فحص وجودها؛ وهذا يفشل بعد تجهيز الخادم مسبقاً. ثم يكتب ملفات /opt بواسطة open في Python، رغم رفع صلاحيات mkdir فقط. النتيجة PermissionError مع مستخدم عادي. المطلوب ensure-network وكتابة ملفات بصلاحيات متسقة.

### F28 — إعداد Traefik الجديد لا يحقق لوحة التحكم المعلنة

الموضع: `app/services/traefik_manager.py:753` وما بعده.
dashboard مفعل مع insecure=false، لكن Compose لا يحدد router إلى api@internal أو middleware للمصادقة، مع طباعة رابط Dashboard محمي. resolver الجديد اسمه le بينما مسارات أخرى تستخدم letsencrypt. كذلك email مكتوب كـ`${ACME_EMAIL}` داخل YAML المركب وليس قيمة محلولة من مولد الملف. المطلوب توليد إعداد مكتمل واختبار TLS والـrouter؛ مجرد running لا يثبت ذلك.

### F29 — معاملات Ansible وحقول النتائج غير صحيحة

الموضع: `deployment/Odoo-MultiVersion-Deployment/ansible/roles/docker/tasks/main.yml:28` ومثيله odoo18؛ وأدوار odoo/traefik/restore.
docker_compose_v2 لا يقبل restart_policy كمعامل للموديول. وdocker_container_info يعيد container لا info، لذلك `.info.State.Status` تفشل. المصادر: [Compose v2 module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_compose_v2_module.html)، [container info](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_info_module.html).

### F30 — entrypoint المولد لا يستطيع تشغيل أمر Odoo

الموضع: دور docker في MultiVersion وodoo18 مع قوالب Compose.
entrypoint محتواه `exec "$@"`، لكن command يبدأ بـ`--config=...`. لا يضيف اسم executable، وبالتالي لا يشغل odoo. كذلك يبدأ Compose قبل دور إنشاء إعداد Odoo. المطلوب المحافظة على entrypoint الصورة أو استدعاء odoo صراحة وتجهيز config قبل التشغيل.

### F31 — قوالب MultiVersion لا تتلقى متغيرات instance وتكرر environment

الموضع: `deployment/Odoo-MultiVersion-Deployment/ansible/roles/docker/tasks/main.yml` و`docker/odoo17-compose.yml.j2` و`docker/odoo19-compose.yml.j2`.
الحلقة تمرر item، بينما القالب يطلب container_name/db_user/data_path كمتغيرات مستقلة دون mapping في المهمة. وفي خدمة Odoo يوجد environment مرتين؛ إما يرفضه المحلل أو تضيع HOST/USER/PASSWORD عند اعتماد القيمة الثانية. المطلوب render باستخدام instance صريح ثم docker compose config لكل فرع Traefik.

### F32 — أدوار Odoo17/19 غير مكتملة الربط

الموضع: `deployment/odoo17/ansible/roles/odoo/tasks` و`deployment/odoo19/ansible/playbooks/install.yml` و`roles/odoo/tasks/main.yml`.
Odoo17 يحتوي deploy_instance.yml دون tasks/main.yml لاستدعائه. Odoo19 يطلب دور postgresql غير موجود محلياً، ودور odoo يستخدم item دون حلقة خارجية على instances، مع حلقة داخلية تعيد استخدام item ومسارات قوالب غير مطابقة للملفات المتاحة. النشر لا يمكن اعتباره مكتملاً من checkout وحده. المطلوب تجميع الأدوار وتشغيل syntax-check ثم نشر تجريبي.

### F33 — سكريبت Odoo17 الخاص يجمع عدة أعطال مستقلة

الموضع: `deployment/odoo17/scripts/install-odoo17.sh:20` وما بعده.
PROJECT_ROOT يصل إلى deployment ثم SOURCE_DIR يضيف deployment مرة ثانية. mkdir يضع brace expansion داخل اقتباس فينشئ اسماً حرفياً. chmod لجميع الملفات 644 يلغي تنفيذ entrypoint بعد chmod +x. وفرع Traefik يطبع ODOO_DOMAIN غير معرف مع set -u. يلزم إصلاح الأربعة حتى يعمل المسار.

### F34 — Jenkins restore يحتوي توسعة shell غير صالحة

الموضع: `deployment/Odoo-MultiVersion-Deployment/Jenkins/restore.Jenkinsfile:50`.
داخل sh بثلاث علامات اقتباس مفردة تظل `${env.BUILD_NUMBER}` نصاً لـshell، وتؤدي إلى bad substitution. المطلوب `$BUILD_NUMBER` داخل shell أو interpolation مضبوط في Groovy. يجب فحص المواضع المشابهة في pipelines الأخرى أيضاً.

## فجوات المتطلبات والإعدادات

### F35 — إعدادات الهوية والمسارات ليست مصدراً واحداً

الموضع: `app/config/hostname_config.py` و`profiles` و`templates/env.template` وخدمات/سكريبتات النشر.
يوجد اكتشاف تلقائي للhostname إضافة إلى YAML و.env وقيم ثابتة في السكريبتات. كما تختلف جذور Traefik بين /opt/traefik و/opt/odoo-infrastructure/traefik. قد يدير الفاحص أو النسخ موقعاً مختلفاً عما نشره المثبت. المطلوب إعداد محسوم واحد يمر إلى جميع الخطط، مع manifest للموارد المنشأة.

### F36 — Portainer وpgAdmin لا يطابقان تماماً الطلب السابق

الموضع: `app/ui/app.py`، مكون Portainer التسلسلي، وخدمات التثبيت الحالية.
المسار التسلسلي ما زال يستخدم 9000 وربط /srv/portainer بدلاً من الطلب الأخير 9443 وportainer_data. ولا توجد خدمة تثبيت/فحص pgAdmin مماثلة لخدمات Python/PostgreSQL/Portainer؛ وجود Compose وحده لا يحقق نفس تجربة القائمة. هذه فجوة متطلبات، وليست خطأ تركيبياً. بيانات دخول pgAdmin ينبغي أن تكون مدخلاً وقت التثبيت لا كلمة ثابتة منشورة.

### F37 — أسرار افتراضية وصلاحيات أرشيف غير مفروضة

الموضع: `deployment/odoo17/scripts/install-odoo17.sh` و`deployment/odoo19/ansible/roles/odoo/tasks/main.yml` و`app/services/system_backup.py`.
توجد fallbacks لكلمات مرور مثل odoo17/odoo19، كما لا تفرض خدمة snapshot صلاحية مقيدة على أرشيف يجمع .env؛ تحت umask شائع 022 يمكن أن يكون مقروءاً لمستخدمين آخرين. المطلوب رفض الأسرار الافتراضية في الإنتاج وفرض 0600 على النسخ المحتوية عليها.

## ترتيب المعالجة والتحقق المطلوب

1. إصلاح عقد النسخ والاستعادة F01–F14 أولاً، ثم تجربة استعادة إلى قاعدة مستقلة مع سجل ومرفق Odoo وفحصهما بعد الاستعادة، وتجربة أرشيف تالف وفشل SQL ومساحة غير كافية.
2. إصلاح أعطال القوائم والمثبت F15–F26 وإضافة اختبارات تمنع SKIPPED/نجاح كاذب، مع exit code صحيح.
3. اعتماد مسار نشر واحد وبناء باقي الواجهات فوقه، ثم معالجة F27–F35. تشغيل Ansible syntax-check وrender/compose config لكل إصدار وفرع شبكة، ثم تجربة Ubuntu نظيفة وتجربة إعادة التنفيذ على تثبيت قائم.
4. استكمال Portainer/pgAdmin وتأمين الأسرار، ثم اختبار مستخدم عادي مع sudo وDocker daemon متوقف واسم حاوية محجوز ومنفذ مستخدم.

نجاح الاختبارات الحالية مفيد لكنه لا يثبت نجاح هذه المسارات الجديدة. لا بد من اختبار end-to-end على Ubuntu قبل وصف النظام بأنه جاهز للإنتاج.
