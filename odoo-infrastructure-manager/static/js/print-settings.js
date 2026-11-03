var printSettings = (function () {
  var _settings = {};

  var LAYOUT_FIELDS = [
    { key: 'prt_paper_size', label: 'حجم الورقة', type: 'select', desc: 'حجم الورقة المستخدمة في الطباعة', options: [
      { value: 'a4', label: 'A4 (210 × 297 مم)' },
      { value: 'a5', label: 'A5 (148 × 210 مم)' },
      { value: 'letter', label: 'Letter (216 × 279 مم)' },
      { value: 'legal', label: 'Legal (216 × 356 مم)' },
    ]},
    { key: 'prt_orientation', label: 'اتجاه الصفحة', type: 'select', desc: 'اتجاه الطباعة', options: [
      { value: 'portrait', label: 'عمودي (Portrait)' },
      { value: 'landscape', label: 'أفقي (Landscape)' },
    ]},
    { key: 'prt_margins', label: 'هوامش الصفحة', type: 'select', desc: 'حجم الهوامش حول المحتوى', options: [
      { value: 'narrow', label: 'ضيق' },
      { value: 'normal', label: 'عادي' },
      { value: 'wide', label: 'عريض' },
    ]},
    { key: 'prt_font_size', label: 'حجم الخط الأساسي', type: 'number', placeholder: '12', desc: 'حجم الخط الرئيسي للمطبوعات بالنقاط' },
    { key: 'prt_copies', label: 'عدد النسخ الافتراضي', type: 'number', placeholder: '1', desc: 'عدد النسخ المطبوعة تلقائياً' },
    { key: 'prt_auto_print', label: 'طباعة تلقائية بعد الحفظ', type: 'toggle', desc: 'إرسال للطباعة تلقائياً عند حفظ المستند' },
  ];

  var CONTENT_FIELDS = [
    { key: 'prt_show_header', label: 'إظهار الترويسة', type: 'toggle', desc: 'إظهار شريط الترويسة في أعلى الصفحة' },
    { key: 'prt_show_footer', label: 'إظهار التذييل', type: 'toggle', desc: 'إظهار شريط التذييل في أسفل الصفحة' },
    { key: 'prt_show_logo', label: 'إظهار الشعار', type: 'toggle', desc: 'إظهار شعار الشركة في المطبوعات' },
    { key: 'prt_show_date', label: 'إظهار تاريخ الطباعة', type: 'toggle', desc: 'إظهار تاريخ ووقت الطباعة' },
    { key: 'prt_show_page_num', label: 'إظهار أرقام الصفحات', type: 'toggle', desc: 'ترقيم الصفحات في الأسفل' },
    { key: 'prt_signature_line', label: 'إظهار خطة التوقيع', type: 'toggle', desc: 'إظهار خط التوقيع في أسفل المستند' },
    { key: 'prt_compact_mode', label: 'وضع الطباعة المختصر', type: 'toggle', desc: 'تقليل المسافات والهوامش لزيادة المعلومات في الصفحة' },
    { key: 'prt_header_text', label: 'نص الترويسة المخصص', type: 'text', placeholder: 'النظام العام', desc: 'النص المعروض في ترويسة المطبوعات' },
  ];

  function init() {
    _loadSettings();
  }

  function _loadSettings() {
    apiFetch('/api/settings/system?category=printing').then(function (r) {
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      var list = data.settings || [];
      _settings = {};
      list.forEach(function (s) { _settings[s.key] = s.value; });
      _renderLayoutForm();
      _renderContentForm();
      if (typeof settings !== 'undefined' && settings._renderPrtStats) settings._renderPrtStats();
    }).catch(function () {
      _settings = {};
      _renderLayoutForm();
      _renderContentForm();
    });
  }

  function _renderLayoutForm() {
    var form = document.getElementById('prt-layout-form');
    if (!form) return;
    var html = '';
    LAYOUT_FIELDS.forEach(function (f) {
      var val = _settings[f.key] || '';
      html += '<div class="col-md-6" style="margin-bottom:16px">';
      html += '<label class="form-label" style="font-weight:700;font-size:13px">' + f.label + '</label>';
      if (f.type === 'toggle') {
        var isChecked = val === 'true';
        html += '<div class="form-check form-switch">';
        html += '<input class="form-check-input" type="checkbox" id="cfg_' + f.key + '" ' + (isChecked ? 'checked' : '') + ' style="cursor:pointer">';
        html += '</div>';
      } else if (f.type === 'number') {
        html += '<input type="number" class="form-control" id="cfg_' + f.key + '" value="' + (val || f.placeholder || '0') + '" min="1">';
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

  function _renderContentForm() {
    var form = document.getElementById('prt-content-form');
    if (!form) return;
    var html = '';
    CONTENT_FIELDS.forEach(function (f) {
      var val = _settings[f.key] || '';
      var col = f.key === 'prt_header_text' ? 'col-md-12' : 'col-md-6';
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
    LAYOUT_FIELDS.concat(CONTENT_FIELDS).forEach(function (f) {
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
      body: JSON.stringify({ settings: items, category: 'printing' }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.success) {
        showToast('تم حفظ إعدادات الطباعة بنجاح', 'success');
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
    _renderLayoutForm: _renderLayoutForm,
    _renderContentForm: _renderContentForm,
  };
})();
