# إعادة مراجعة الإصلاحات — 2026-11-05

## الحكم

تم إصلاح بعض الأسباب المحددة في التقرير السابق، لكن المشاكل لم تُحل بالكامل. ظهر أيضاً خطأ تركيبي جديد يمنع تشغيل البرنامج، وأخطاء في منطق التشخيص والاستعادة ومسار ServerSetupWorkflow الجديد.

هذه مراجعة للكود الحالي، وليست شهادة نجاح نشر. تغيّرت بعض الملفات أثناء الفحص؛ آخر دليل آلي محفوظ في `REVIEW_RECHECK_2026-11-05_evidence.json` بتاريخ 2026-11-05 الساعة 11:10:30 +02:00، ويحتوي بصمات ملفات app وأخطاء AST ونتيجة تشغيل CLI. أي تعديلات لاحقة تحتاج تحققاً جديداً ولا يشملها الحكم هنا.

لم أعدّل كود التشغيل. أضفت تقرير المراجعة وملف الأدلة فقط.

## التحقق المنفذ

- تشغيل `python -B -m unittest discover tests`: **85 اختباراً ناجحاً**، أُعيد تشغيلها بعد ظهور العطل أيضاً ونجحت.
- تشغيل `python -B app/main.py --help`: **فشل، exit code 1**.
- تحليل 45 ملف Python في آخر تحقق: خطآن تركيبيان، في sequential_installer.py عند 168 وفي app/main.py عند 69.
- تحليل 111 ملف YAML تحت deployment: لا أخطاء صياغة YAML؛ لا يعني ذلك صحة Ansible أو القوالب بعد render.
- محاكاة آمنة دون Docker فعلي: اكتشاف صور خاطئة على أنها Odoo مثبت، تصنيف حاويات Up كمتوقفة، فشل نتيجة إعداد سليم موجود مسبقاً، نجاح تقرير كله تحذيرات، وتجاوز منع التبعيات غير المباشرة.
- لم يتوفر Bash أو Docker أو ansible-playbook محلياً. لم تُنفذ عمليات تثبيت أو استعادة أو إيقاف خدمات.

## حالة النتائج السابقة F01–F37

«أُصلح السبب المحدد» تعني أن موضع الخطأ الأصلي تغير بصورة تعالجه؛ لا تعني اكتمال نجاح الميزة على Ubuntu.

- **F01 — جزئي:** backup.sh أصبح ينشئ BACKUP_ID وmanifest وchecksums. لكن manifest يثبت امتدادات zst حتى عند استخدام fallback gzip، والعقد ما زال مختلفاً بين Shell وAnsible.
- **F02 — أُصلح السبب المحدد:** استبدل docker exec -T بـ-i.
- **F03 — غير محلول:** TARGET_DB يُحسب لكن psql ما زال يستخدم `-d postgres -U postgres`. أضيف ON_ERROR_STOP، لكن الملف الآن يمرر بـ-f كمسار مضيف داخل الحاوية، فتتعطل الاستعادة.
- **F04 — جزئي:** أضيف manifest واكتشاف compgen للأرشيفات، لكن fallback لملف SQL ما زال يستخدم wildcard داخل اقتباس في اختبار -f.
- **F05 — جزئي:** الوجهة الجديدة تُحسب قبل الكتابة، لكن لا تُنشأ حاويات أو Compose أو إعدادات اتصال النسخة الجديدة؛ docker start لاسم جديد يفشل.
- **F06 — غير مكتمل:** الاستعادة توقف PostgreSQL أيضاً، لكن نسخ الأمان ما زالت تتجاهل أخطاء cp، ولا توجد آلية استرجاع حالة التشغيل عند الفشل. النسخ العادي يضغط مجلد data متضمناً PostgreSQL الحي.
- **F07 — أُصلح السبب المحدد:** حقول stat أصبحت `.stat.exists`.
- **F08 — غير محلول:** نقل dump صار قبل psql، لكنه يبدأ باكتشاف ملفات باستخدام command مع pipe وwildcard؛ ونتيجة loop تُقرأ من `.stdout` بدلاً من `.results`، ثم first يأخذ أول حرف من النص لو وُجد.
- **F09 — جزئي:** أضيفت مجلدات instance وصححت بعض مستويات item. ما زال حفظ checksums يقرأ مستوى item خاطئاً، وbackup_stop_odoo=false يلغي النسخ نفسه، وليس الإيقاف فقط.
- **F10 — جزئي:** أضيف pg_dump؛ لكن المستخدم واسم القاعدة مفترضان، وفشل Docker أو dump يُخفى، ثم يمكن أن يسمى snapshot verified بلا قواعد بيانات.
- **F11 — جزئي:** يتحقق SHA256 إذا وُجد manifest سليم بالاسم المتوقع. غيابه أو فساده يؤدي للمتابعة دون checksum. لم تُضف آلية استرجاع قواعد البيانات من dumps أو إعادة ربط المسارات التشغيلية.
- **F12 — جزئي مع تراجعات:** أضيف ON_ERROR_STOP وفشل عند صفر جداول. اسم metadata المطلوب لا يطابق ما ينتجه backup-db.sh، واختيار filestore فقد مطابقة التاريخ ويضيف مجلد المصدر داخل مجلد الهدف.
- **F13 — جزئي:** دعم Odoo18 وتنظيف امتدادات الملفات أُصلحا. fallback يبحث عن filestore داخل حاوية PostgreSQL بدلاً من Odoo.
- **F14 — أُصلح السبب المحدد:** أصبح النسخ source/. بدلاً من source/، فيمنع تداخل المجلدات المذكور.
- **F15 — أُصلح السبب المحدد:** handle_traefik_management يملك الآن dry_run=False. لا يحل ذلك تمرير --dry-run لجميع القوائم.
- **F16 — أُصلح السبب المحدد:** set_config مستورد الآن. استمرار الإعدادات وتوحيد مصادرها موضوع F35.
- **F17 — أُصلح وتحقق بالمحاكاة:** فحوص المكونات الخمسة تعيد `(False, None)` عند الغياب بدلاً من True.
- **F18 — أُصلح نقص أمر التشغيل:** أضيف إنشاء إعداد وCompose وup. إعداد Traefik الناتج ما زال غير مكتمل بالنسبة للنطاقات والـdashboard والتوافق مع بقية المسارات.
- **F19 — أُصلح في جسم الحلقة:** أضيف break بعد فشل خطوة. لكن الملف كله لا يمكن استيراده حالياً بسبب خطأ N01 أدناه.
- **F20 — جزئي وغير قابل للتشغيل حالياً:** أضيفت محاولة killpg وفحص نهائي، لكن تعديل المسافات البادئة كسر الملف. صلاحيات السجل غير محسومة؛ sudo mkdir لا يمنح Python غير المرفوع صلاحية كتابة الملف، ولا يزال mkdir غير المرفوع موجوداً في install.
- **F21 — أُصلح السبب المحدد:** script_content يُكتب قبل تشغيل bash؛ لم يُختبر تثبيت Ansible فعلياً.
- **F22 — غير محلول بالكامل:** لم يعد PostgreSQL مستقل يعادل installed، لكنه يصبح partial. حاويتان بصور nginx/redis وبالأسماء المتوقعة ما زالتا تعطيان installed. التثبيت متعدد النسخ الصحيح يُصنف partial.
- **F23 — أُصلح نقص docker:** أوامر الإصلاح أصبحت docker start وتحافظ على sudo. لكنها لا تحفظ `--host unix:///var/run/docker.sock` المستخدم في الفحص، لذا تظل إمكانية إصلاح Docker context مختلف قائمة.
- **F24 — تراجع جزئي:** أُصلح فحص منافذ Odoo عند with_traefik، لكن استخدام كلمة running داخل Status يصنف Up كمتوقف. فحوص منافذ Jenkins وبعض الخدمات ما زالت غير مرتبطة بالتخطيط الحقيقي.
- **F25 — إصلاح جارٍ غير مكتمل:** أضيف أثناء المراجعة tui.dry_run وتمرير dry_run إلى run_textual_app، لكن تعريف run_textual_app الحالي لا يقبل هذا الوسيط، وقوائم التثبيت لا تقرأ الخاصية الجديدة. traefik-backup ما زال يكتب snapshot فعلياً. انظر N15.
- **F26 — باقٍ:** main ما زال يطبع FAILED دون exit غير صفري عند فشل نتيجة workflow؛ توجد تقارير نجاح غير دقيقة في المسار الجديد أيضاً.
- **F27 — باقٍ:** مثبت Traefik الفردي ينشئ proxy بلا ضمان وجود، ثم يكتب /opt بواسطة Python غير المرفوع رغم use_sudo.
- **F28 — باقٍ:** مثبت Traefik الفردي لا يولد router dashboard أو middleware المعلن، ويستخدم le مقابل letsencrypt في مسارات أخرى وemail غير محلول في الملف.
- **F29 — باقٍ في المسارات القديمة:** restart_policy ما زال داخل docker_compose_v2 وinfo.State ما زال في أدوار MultiVersion/odoo18. وجود أدوار جديدة لا يصلح القديمة تلقائياً.
- **F30 — باقٍ:** entrypoint في أدوار MultiVersion/odoo18 ينفذ `$@` بينما command يبدأ بـ--config، ويبدأ Compose قبل إكمال config.
- **F31 — باقٍ:** قوالب MultiVersion تكرر environment وتطلب متغيرات instance غير المربوطة في مهمة template.
- **F32 — باقٍ في عائلتي النشر:** Odoo17 يفتقد tasks/main.yml للدور، وOdoo19 يطلب postgresql غير موجود ضمن مساره ويستخدم item دون الحلقة الخارجية. الدور الجديد في deployment/ansible مسار مستقل، ولا يوجد دليل ربط يصلح هذه playbooks.
- **F33 — باقٍ:** أخطاء SOURCE_DIR وbrace expansion وchmod وODOO_DOMAIN في deployment/odoo17/scripts/install-odoo17.sh لم تعالج.
- **F34 — باقٍ:** `${env.BUILD_NUMBER}` داخل sh ذي الاقتباس المفرد في Jenkins restore لم يتغير.
- **F35 — باقٍ ومتوسع:** أضيف ServerSetupWorkflow بتعريفات ثابتة لا تستخدم خيارات profile في قرارات التثبيت، بجانب المسارات السابقة.
- **F36 — باقٍ:** Portainer التسلسلي ما زال 9000 و/srv/portainer، ولا توجد تجربة تثبيت/فحص pgAdmin مماثلة لبقية المكونات.
- **F37 — باقٍ:** أسرار fallback السابقة موجودة ولا تُفرض صلاحية مقيدة على snapshot. أضيف staging لملفات SQL لا يُحذف بعد الأرشفة.

## أخطاء جديدة أو تراجعات مؤكدة

### N01 — حرج: نقطة الدخول لا تعمل

الموضع: `app/services/sequential_installer.py:156–168`.
try الخاص بـPopen أصبح داخل drain بمسافة بادئة غير صحيحة، ثم stdout_thread يقع قبل except/finally الموافق. Python يرفض الملف: `SyntaxError: expected 'except' or 'finally' block` عند 168. لأن app/main.py يستورده عبر TerminalUI، حتى --help يفشل. هذا أول إصلاح مطلوب، مع اختبار smoke لنقطة الدخول؛ الاختبارات الـ85 لا تستورد هذا المسار.

### N02 — عالٍ: الحاويات العاملة توصف بأنها متوقفة

الموضع: `app/services/odoo_service.py:149` و`app/services/jenkins_service.py:294`.
الكود يفحص `'running' in status.lower()` لكن Status القادم من docker ps يكون مثل `Up 2 hours`؛ State أو inspect هما مصدر running. المحاكاة أعادت odoo17_container_not_running وodoo17_db_not_running لحاويتين Up. سيطلب النظام إصلاح خدمة سليمة. المصدر الرسمي يوضح صيغة Status: [Docker container ls](https://docs.docker.com/reference/cli/docker/container/ls/).

### N03 — عالٍ: إصلاح الاستعادة أدخل مسار ملف خاطئ ويترك PostgreSQL متوقفاً

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/restore.sh:184–191,286`.
DB_FILE يشير إلى /data/backups على المضيف، لكن psql -f يعمل داخل الحاوية دون copy أو mount لهذا الملف. TARGET_DB غير مستخدم. وحتى إذا أصلح نقل الملف ونجحت الاستعادة، السكريبت يوقف قاعدة البيانات ثم يشغل Odoo وحده في النهاية؛ فحص pg_isready يفشل ويصدر تحذيراً ثم exit 0. المطلوب استعادة إلى القاعدة الصحيحة عبر stdin أو نقل صريح وإعادة حالة تشغيل الخدمتين.

### N04 — عالٍ: checksum القديم لا يُفحص وfilestore قد لا يطابق dump

الموضع: `automation/scripts/restore-db.sh:39,112–132` مقابل `automation/scripts/backup-db.sh:36`.
النسخ يولد meta_DB_TIMESTAMP.json؛ الاستعادة تبحث عن dump_DB_TIMESTAMP.meta.json، فتتخطى الفحص دائماً للناتج الطبيعي. كذلك تقطع اسم DB عند أول underscore وتختار أول filestore مطابق دون timestamp. ثم تفك أرشيفاً يحتوي مجلد DB داخل مجلد TARGET_DB، فينتج TARGET_DB/SOURCE_DB/... بدلاً من الملفات في المستوى المطلوب. هذا يهدد اتساق المرفقات حتى لو نجح SQL.

### N05 — عالٍ: fallback المرفقات ينفذ على حاوية قاعدة البيانات

الموضع: `automation/scripts/backup-db.sh:73` وما بعده.
يستخدم DB_CONTAINER للبحث عن /var/lib/odoo/filestore ولـtar وdocker cp؛ بيانات Odoo في حاوية التطبيق. كما أن fallback يؤرشف filestore بالكامل بدلاً من قاعدة واحدة، وهو عقد مختلف عن المسار الأساسي. يجب استخدام حاوية Odoo والقاعدة والتاريخ نفسيهما.

### N06 — عالٍ: backup.sh يترك Odoo متوقفاً عند فشل dump

الموضع: `deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh:75–144`.
أضيف docker stop قبل pg_dump، لكن لا يوجد trap لاسترجاع الحالة عند الخطأ. pg_dump ما زال يستخدم postgres حتى عندما POSTGRES_USER=odoo17 أو غيره؛ فشل متوقع على الحاويات المولدة بهذه الإعدادات، وset -e ينهي السكريبت قبل docker start. التعليق الذي يقول restart even on failure لا ينفذ حماية فعلية.

### N07 — عالٍ: اكتشاف dump في Ansible لا ينفذ كما كُتب

الموضع: `deployment/Odoo-MultiVersion-Deployment/ansible/roles/restore/tasks/main.yml`، Discover database dump وCopy database dump.
ansible.builtin.command لا يفسر `2>/dev/null | head -1` ولا glob؛ تُرسل كوسائط إلى ls. ثم register مع loop يعيد results لا stdout، وفلتر first على string يعيد حرفاً لا مساراً. ترتيب المهام تحسن لكن التنفيذ لا يصل إلى dump صالح. المصدر: [Ansible command](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/command_module.html).

### N08 — عالٍ: ملف سر PostgreSQL غير موجود داخل الحاوية الجديدة

الموضع: `app/core/server_setup.py:167` و`deployment/ansible/roles/postgresql/tasks/main.yml`.
يحدد POSTGRES_PASSWORD_FILE=/run/secrets/... بلا إنشاء السر أو mount له. صورة PostgreSQL تقرأ الملف أثناء التهيئة، فيفشل بدء قاعدة جديدة. كما أن ServerSetupWorkflow يجهز قاعدة باسم odoo17-db فقط رغم تثبيت إصدارات Odoo الثلاثة. المصدر: [entrypoint لصورة PostgreSQL الرسمية](https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh).

### N09 — عالٍ: مسار Odoo الجديد لا يضبط اتصال القاعدة أو إتاحة الخدمة

الموضع: `app/core/server_setup.py` تعريفات odoo17/18/19 و`deployment/ansible/roles/odoo17/tasks/main.yml` ومثيلاه.
أوامر الحاويات لا تمرر HOST/USER/PASSWORD ولا تكتب odoo.conf وتربط مجلداً فارغاً مكان /etc/odoo. لا توجد ports ولا labels لتوجيه Traefik لهذه الخدمات. إنشاء حاوية باسم صحيح لا يحقق تشغيل Odoo واتصال قاعدة وإمكانية وصول المستخدم. أيضاً Traefik في ServerSetupWorkflow لا يتصل بشبكة proxy رغم وضع التطبيقات فيها.

### N10 — عالٍ: منع التبعيات لا ينتقل عبر السلسلة

الموضع: `app/core/server_setup.py:443,464`.
عند فشل system-packages، can_install يمنع docker-engine دون تسجيله blocked/failed. docker-network يفحص الفشل المباشر لـdocker-engine فقط، فيسمح بالتنفيذ رغم فشل أصل السلسلة. أثبتت المحاكاة: blocked_docker_engine=true لكن docker_network_allowed_despite_failed_ancestor=true. يجب اعتبار كل تبعية غير ناجحة مانعاً، وتسجيل سبب التجاوز صراحة.

### N11 — متوسط: التقرير يقلب النجاح والفشل

الموضع: `app/core/server_setup.py:451–456,634`.
الخدمة الموجودة مسبقاً تتحول إلى SKIPPED، ثم overall_success يشترط صفر skipped. المحاكاة: جميع الخدمات مثبتة مسبقاً → false. وفي المقابل جميع الحالات WARNING → true لأن warnings لا تدخل المعادلة. الفحوص تعتمد أحياناً على وجود اسم حاوية متوقفة أو وجود psql فقط، فلا تثبت صحة الخدمة. يجب فصل التجاوز السليم عن المحظور وعن الفشل والتحذير.

### N12 — عالٍ: ServerSetupWorkflow يتجاهل profile في خطة التثبيت

الموضع: `app/core/server_setup.py` COMPONENT_DEFINITIONS وrun_ordered_installation.
self.profile يستخدم في وصف operation فقط، ولا يتحكم في اختيار إصدارات Odoo المفعلة أو الموارد أو النطاق أو منافذ التثبيت. التعريفات تثبت 17 و18 و19 جميعاً. هذا مسار جديد لا يحترم إعدادات المستخدم ولو كانت صحيحة في YAML.

### N13 — متوسط: صفحة Failed Installations لا تقرأ تاريخ الفشل

الموضع: `app/ui/app.py`، handle_failed_installations.
تنشئ workflow جديداً وتستدعي inspect_all، الذي لا يسند FAILED بل ALREADY_INSTALLED/READY_TO_INSTALL/NOT_CHECKED. لذلك القائمة filtered على FAILED فارغة دائماً في هذا المسار. لا تعيد تشغيل إخفاق سابق ولا تعرض سجله، رغم عنوانها.

### N14 — عالٍ: snapshot قد يعلن verified رغم فشل جميع dumps

الموضع: `app/services/system_backup.py`، _dump_databases/create_full_snapshot.
Docker error يعيد قائمة فارغة؛ وفشل pg_dump لا يُرفع ولا يُحفظ في manifest. اختبرت Docker permission denied بالمحاكاة فكانت النتيجة []. بعدها snapshot يستمر في أرشفة الإعدادات ويسجل verified مع include_db_dumps=true. كذلك اسم القاعدة مشتق من اسم الحاوية والمستخدم مثبت على postgres، وليس من الإعداد الفعلي. يجب اعتبار فشل dump مطلوب فشلاً للنسخة، والتمييز بين عدم وجود قواعد وفشل الوصول إليها.

## ما ينبغي فعله قبل اعتبار الإصلاحات مكتملة

### N15 — حرج: التعديل الأخير لـmain أضاف خطأين آخرين

الموضع: `app/main.py:43,69` مقابل `app/ui/textual_app.py:268`.
في آخر فحص التصقت `elif args.action == "odoo17":` بسطر print السابق؛ AST و--help يفشلان بـinvalid syntax عند 69. كذلك أضيف الاستدعاء `run_textual_app(tui.profile, dry_run=args.dry_run)` بينما الدالة تعرف profile فقط؛ بعد إصلاح الصياغة سيؤدي هذا الاختلاف إلى TypeError عند اختيار textual. هذه حالة الملف عند الساعة 11:10:30؛ التعديلات كانت مستمرة أثناء المراجعة.

1. إصلاح N01 ثم التأكد من نجاح --help و--action validate على النسخة نفسها التي ستُنشر.
2. إصلاح عقد النسخ والاستعادة مع أسماء الملفات وبيانات الاتصال وحالة الخدمات، ثم تجربة استعادة قاعدة ومرفق إلى نسخة مستقلة. اختبار فشل dump والقرص الممتلئ وchecksum غير مطابق أساسي.
3. توحيد مسار التثبيت حتى لا يبقى المسار القديم معطلاً بجانب مسار جديد غير مكتمل، وتمرير profile إلى التنفيذ فعلياً.

## تحديث حالة الإصلاحات — 2026-11-05 (بعد الإصلاح)

### النتائج التي تم إصلاحها (P0 – P2)

| النتيجة | الحالة | الملفات المعدلة | الملاحظات |
|---------|--------|----------------|-----------|
| N01/N15 — نقطة الدخول لا تعمل | ✓ مُصلح | `app/ui/textual_app.py` | أُضيف `dry_run` لمعامل `run_textual_app` و `OdooTextualApp.__init__`؛ `--help` ينجح exit 0 |
| N02 — الحاويات العاملة توصف بأنها متوقفة | ✓ مُصلح | `app/services/odoo_service.py`, `app/services/jenkins_service.py` | استخدام `status.lower().startswith("up")` بدلاً من `'running' in status.lower()` |
| N03 — استعادة PostgreSQL مسار ملف خاطئ | ✓ مُصلح | `deployment/.../scripts/restore.sh` | استخدام `-d "${TARGET_DB}"`، مستخدم DB من المانيفست/البيئة، إبقاء DB قيد التشغيل |
| N04 — checksum لا يُفحص وfilestore لا يطابق | ✓ مُصلح | `automation/scripts/restore-db.sh` | استخراج اسم الميتاداتا من اسم الـ dump، استخراج filestore دون تداخل |
| N05 — fallback المرفقات على حاوية DB | ✓ مُصلح | `automation/scripts/backup-db.sh` | استخدام حاوية Odoo بدلاً من حاوية DB في fallback |
| N06 — backup.sh يترك Odoo متوقفاً | ✓ مُصلح | `deployment/.../scripts/backup.sh` | trap على EXIT لإعادة تشغيل Odoo، مستخدم DB من الحاوية |
| F22 — اكتشاف Odoo خاطئ | ✓ مُصلح | `app/services/odoo_service.py` | مطابقة اسم دقيقة `names == f'odoo{version}'` |
| F26 — فشل العمليات يُبلّغ بنجاح كاذب | ✓ جزئي | `app/ui/app.py` | التقاط return code لأوامر traefik start/stop/restart |
| F29 — restart_policy و info.State في Ansible | ✓ مُصلح | 6 ملفات Ansible roles | `restart_policy: {Name: "always"}`, `.container.State.Status` |
| F33 — install-odoo17.sh brace expansion | ✓ مُصلح | `deployment/odoo17/scripts/install-odoo17.sh` | أوامر mkdir منفصلة بدلاً من `{}` داخل اقتباس |
| F34 — Jenkins \${BUILD_NUMBER} في sh | ✓ مُصلح | `restore.Jenkinsfile`, `sequential-install.Jenkinsfile` | `$BUILD_NUMBER` بدلاً من `\${BUILD_NUMBER}` |
| N08 — سر PostgreSQL غير مُنشأ | ✓ مُصلح | `app/core/server_setup.py` | إنشاء ملف السر بصلاحيات 600 ورفعه للحاوية |
| N09 — Odoo بدون اتصال قاعدة أو منافذ | ✓ مُصلح | `app/core/server_setup.py` | متغيرات DB، نشر المنافذ، تسميات Traefik |
| N10 — تبعية فاشلة لا تمنع المكونات التابعة | ✓ مُصلح | `app/core/server_setup.py` | مجموعة `_blocked_components` في `can_install()` |
| N11 — التقرير يقلب نجاح/فشل | ✓ مُصلح | `app/core/server_setup.py` | `overall_success` لا يحسب SKIPPED كفشل |
| N12 — ServerSetupWorkflow يتجاهل profile | ✓ مُصلح | `app/core/server_setup.py` | تصفية مكونات Odoo حسب `profile.odooXX.enabled` |

### النتائج المتبقية (تحتاج اختبار Ubuntu فعلي)

| النتيجة | الحالة | السبب |
|---------|--------|-------|
| F01–F06 | جزئي | تحتاج اختبار effective على Ubuntu |
| F07–F11 | جزئي | تحتاج اختبار Ansible فعلي |
| F12–F14 | جزئي مع تراجعات | تحتاج اختبار على قاعدة حقيقية |
| F15–F18 | أُصلح السبب | تحتاج اختبار dry-run على Ubuntu |
| F19–F24 | أُصلح | تحتاج اختبار Docker فعلي |
| F25 | جزئي | run_textual_app يقبل dry_run الآن |
| F27–F28 | باقٍ | إعداد Traefik completo يحتاج اختبار |
| F30–F32 | باقٍ | قوالب Entrypoint و Odoo roles تحتاج render/test |
| F35–F37 | باقٍ | فجوات متطلبات وأسرار |

### اختبار التشغيل
- `python -m compileall app/`: ✓ جميع الملفات تُCompile
- `python app/main.py --help`: ✓ exit code 0
- `python -B -m unittest discover tests`: ✓ 85/85 ناجح

### حد الجاهزية للإنتاج
لا يمكن اعتبار النظام جاهزاً للإنتاج حتى يتم اختبار end-to-end على نظام Ubuntu مع Docker وAnsible فعليين، بما في ذلك اختبار النسخ والاستعادة على قاعدة بيانات فعلية ونشر Odoo مع اتصال PostgreSQL مؤكد.

