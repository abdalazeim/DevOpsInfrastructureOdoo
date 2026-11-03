var reportSettings = (function () {
  var _settings = {};

  var CONFIG_FIELDS = [
    { key: 'rpt_default_format', label: 'صيغة التصدير الافتراضية', type: 'select', desc: 'الصيغة المستخدمة عند تصدير التقارير', options: [
      { value: 'pdf', label: 'PDF' },
      { value: 'excel', label: 'Excel' },
      { value: 'csv', label: 'CSV' },
    ]},
    { key: 'rpt_date_range', label: 'النطاق الزمني الافتراضي', type: 'select', desc: 'الفترة الزمنية الافتراضية عند فتح التقارير', options: [
      { value: 'today', label: 'اليوم' },
      { value: 'this_week', label: 'هذا الأسبوع' },
      { value: 'this_month', label: 'هذا الشهر' },
      { value: 'this_quarter', label: 'هذا الربع' },
      { value: 'this_year', label: 'هذا العام' },
      { value: 'last_30', label: 'آخر 30 يوم' },
    ]},
    { key: 'rpt_items_per_page', label: 'عدد العناصر في كل صفحة', type: 'number', placeholder: '20', desc: 'عدد الصفوف المعروضة في كل صفحة تقرير' },
    { key: 'rpt_refresh_interval', label: 'فترات التحديث بالثواني', type: 'number', placeholder: '300', desc: 'مدة التحديث التلقائي بالثواني (0 = بدون تحديث)' },
    { key: 'rpt_auto_refresh', label: 'تحديث تلقائي للبيانات', type: 'toggle', desc: 'تحديث بيانات التقارير تلقائياً' },
    { key: 'rpt_show_totals', label: 'إظهار صف الإجماليات', type: 'toggle', desc: 'إظهار صف الإجماليات في نهاية التقارير' },
    { key: 'rpt_currency_format', label: 'تنسيق عرض العملة', type: 'select', desc: 'شكل عرض العملة في التقارير', options: [
      { value: 'symbol', label: 'الرمز (د.ل)' },
      { value: 'code', label: 'الكود (LYD)' },
      { value: 'name', label: 'الاسم (دينار ليبي)' },
    ]},
  ];

  var APPEARANCE_FIELDS = [
    { key: 'rpt_logo_on_report', label: 'عرض الشعار على التقارير', type: 'toggle', desc: 'إظهار شعار الشركة في أعلى التقارير المطبوعة' },
    { key: 'rpt_company_header', label: 'عرض معلومات الشركة في التقرير', type: 'toggle', desc: 'إظهار اسم وعنوان الشركة في ترويسة التقرير' },
    { key: 'rpt_show_date', label: 'إظهار تاريخ التقرير التلقائي', type: 'toggle', desc: 'إظهار تاريخ ووقت إنشاء التقرير' },
    { key: 'rpt_show_user', label: 'إظهار اسم المستخدم', type: 'toggle', desc: 'إظهار اسم المستخدم الذي أنشأ التقرير' },
    { key: 'rpt_footer_text', label: 'نص التذييل', type: 'text', placeholder: 'النظام العام', desc: 'النص المعروض في أسفل التقارير' },
  ];

  function init() {
    _loadSettings();
  }

  function _loadSettings() {
    apiFetch('/api/settings/system?category=reporting').then(function (r) {
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      var list = data.settings || [];
      _settings = {};
      list.forEach(function (s) { _settings[s.key] = s.value; });
      _renderConfigForm();
      _renderAppearanceForm();
      if (typeof settings !== 'undefined' && settings._renderRptStats) settings._renderRptStats();
    }).catch(function () {
      _settings = {};
      _renderConfigForm();
      _renderAppearanceForm();
    });
  }

  function _renderConfigForm() {
    var form = document.getElementById('rpt-config-form');
    if (!form) return;
    var html = '';
    CONFIG_FIELDS.forEach(function (f) {
      var val = _settings[f.key] || '';
      html += '<div class="col-md-6" style="margin-bottom:16px">';
      html += '<label class="form-label" style="font-weight:700;font-size:13px">' + f.label + '</label>';
      if (f.type === 'toggle') {
        var isChecked = val === 'true';
        html += '<div class="form-check form-switch">';
        html += '<input class="form-check-input" type="checkbox" id="cfg_' + f.key + '" ' + (isChecked ? 'checked' : '') + ' style="cursor:pointer">';
        html += '</div>';
      } else if (f.type === 'number') {
        html += '<input type="number" class="form-control" id="cfg_' + f.key + '" value="' + (val || f.placeholder || '0') + '" min="0">';
      } else if (f.type === 'select') {
        html += '<select class="form-select" id="cfg_' + f.key + '">';
        if (f.options) {
          f.options.forEach(function (o) {
            html += '<option value="' + o.value + '" ' + (val === o.value ? 'selected' : '') + '>' + o.label + '</option>';
          });
        }
        html += '</select>';
      } else {
        html += '<input type="text" class="form-control" id="cfg_' + f.key + '" value="' + (val || '') + '" placeholder="' + (f.placeholder || '') + '">';
      }
      if (f.desc) {
        html += '<small class="text-muted" style="font-size:11px">' + f.desc + '</small>';
      }
      html += '</div>';
    });
    form.innerHTML = html;
  }

  function _renderAppearanceForm() {
    var form = document.getElementById('rpt-appearance-form');
    if (!form) return;
    var html = '';
    APPEARANCE_FIELDS.forEach(function (f) {
      var val = _settings[f.key] || '';
      var col = f.key === 'rpt_footer_text' ? 'col-md-12' : 'col-md-6';
      html += '<div class="' + col + '" style="margin-bottom:16px">';
      html += '<label class="form-label" style="font-weight:700;font-size:13px">' + f.label + '</label>';
      if (f.type === 'toggle') {
        var isChecked = val === 'true';
        html += '<div class="form-check form-switch">';
        html += '<input class="form-check-input" type="checkbox" id="cfg_' + f.key + '" ' + (isChecked ? 'checked' : '') + ' style="cursor:pointer">';
        html += '</div>';
      } else {
        html += '<input type="text" class="form-control" id="cfg_' + f.key + '" value="' + (val || '') + '" placeholder="' + (f.placeholder || '') + '">';
      }
      if (f.desc) {
        html += '<small class="text-muted" style="font-size:11px">' + f.desc + '</small>';
      }
      html += '</div>';
    });
    form.innerHTML = html;
  }

  function _collectAllFields() {
    var items = [];
    CONFIG_FIELDS.concat(APPEARANCE_FIELDS).forEach(function (f) {
      var el = document.getElementById('cfg_' + f.key);
      if (!el) return;
      var val = f.type === 'toggle' ? (el.checked ? 'true' : 'false') : el.value;
      items.push({ key: f.key, value: val, description: f.desc });
    });
    return items;
  }

  function saveAll() {
    var items = _collectAllFields();
    apiFetch('/api/settings/bulk-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings: items, category: 'reporting' }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.success) {
        showToast('تم حفظ إعدادات التقارير بنجاح', 'success');
        _loadSettings();
      } else {
        showToast(d.error || 'خطأ في الحفظ', 'error');
      }
    }).catch(function () {
      showToast('حدث خطأ أثناء الحفظ', 'error');
    });
  }

  function seedDefaults() {
    apiFetch('/api/settings/seed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.success) {
        showToast(d.message || 'تم الإعداد الافتراضي', 'success');
      } else {
        showToast(d.error || 'الإعدادات موجودة مسبقاً', 'info');
      }
      _loadSettings();
    }).catch(function () {
      showToast('حدث خطأ', 'error');
    });
  }

  return {
    init: init,
    saveAll: saveAll,
    seedDefaults: seedDefaults,
    _renderConfigForm: _renderConfigForm,
    _renderAppearanceForm: _renderAppearanceForm,
  };
})();
