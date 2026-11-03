var accountingSettings = (function () {
  var _settings = {};

  var COMPANY_FIELDS = [
    { key: 'acc_company_name', label: 'اسم الشركة', type: 'text', placeholder: 'اسم الشركة', desc: 'الاسم الرسمي للشركة (يظهر في التقارير والمستندات)' },
    { key: 'acc_company_address', label: 'عنوان الشركة', type: 'text', placeholder: 'المدينة، الدولة', desc: 'العنوان الكامل للشركة' },
    { key: 'acc_company_phone', label: 'هاتف الشركة', type: 'text', placeholder: '+218...', desc: 'رقم هاتف الشركة الرئيسي' },
    { key: 'acc_company_email', label: 'البريد الإلكتروني', type: 'text', placeholder: 'info@company.ly', desc: 'البريد الإلكتروني الرسمي للشركة' },
    { key: 'acc_tax_number', label: 'رقم التسجيل الضريبي', type: 'text', placeholder: '123456789', desc: 'رقم السجل الضريبي للشركة' },
  ];

  var FINANCE_FIELDS = [
    { key: 'acc_tax_rate', label: 'نسبة الضريبة (%)', type: 'number', placeholder: '0', desc: 'نسبة ضريبة القيمة المضافة الافتراضية' },
    { key: 'acc_default_currency', label: 'العملة الافتراضية', type: 'text', placeholder: 'د.ل', desc: 'العملة المستخدمة في المستندات والتقارير' },
    { key: 'acc_fiscal_year_start', label: 'بداية السنة المالية', type: 'select', desc: 'الشهر الذي تبدأ فيه السنة المالية', options: [
      { value: '1', label: 'يناير' },
      { value: '2', label: 'فبراير' },
      { value: '3', label: 'مارس' },
      { value: '4', label: 'أبريل' },
      { value: '5', label: 'مايو' },
      { value: '6', label: 'يونيو' },
      { value: '7', label: 'يوليو' },
      { value: '8', label: 'أغسطس' },
      { value: '9', label: 'سبتمبر' },
      { value: '10', label: 'أكتوبر' },
      { value: '11', label: 'نوفمبر' },
      { value: '12', label: 'ديسمبر' },
    ]},
    { key: 'acc_cost_center', label: 'تفعيل مراكز التكلفة', type: 'toggle', desc: 'إظهار حقل مركز التكلفة في المستندات' },
    { key: 'acc_budget_tracking', label: 'تتبع الميزانية', type: 'toggle', desc: 'تفعيل متابعة الميزانية ومراقبة الإنفاق' },
    { key: 'acc_receipt_prefix', label: 'بادئ رقم الإيصال', type: 'text', placeholder: 'REC-', desc: 'البادئ المستخدم في ترقيم الإيصالات' },
    { key: 'acc_expense_prefix', label: 'بادئ رقم المصروفات', type: 'text', placeholder: 'EXP-', desc: 'البادئ المستخدم في ترقيم المستندات المالية' },
  ];

  function init() {
    _loadSettings();
  }

  function _loadSettings() {
    apiFetch('/api/settings/system?category=accounting').then(function (r) {
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      var list = data.settings || [];
      _settings = {};
      list.forEach(function (s) { _settings[s.key] = s.value; });
      _renderCompanyForm();
      _renderFinanceForm();
      if (typeof settings !== 'undefined' && settings._renderAccStats) settings._renderAccStats();
    }).catch(function () {
      _settings = {};
      _renderCompanyForm();
      _renderFinanceForm();
    });
  }

  function _renderConfigForm() {
    _renderCompanyForm();
  }

  function _renderCompanyForm() {
    var form = document.getElementById('acc-company-form');
    if (!form) return;
    var html = '';
    COMPANY_FIELDS.forEach(function (f) {
      var val = _settings[f.key] || '';
      var col = f.key === 'acc_company_name' || f.key === 'acc_company_address' ? 'col-md-12' : 'col-md-6';
      html += '<div class="' + col + '" style="margin-bottom:16px">';
      html += '<label class="form-label" style="font-weight:700;font-size:13px">' + f.label + '</label>';
      html += '<input type="text" class="form-control" id="cfg_' + f.key + '" value="' + (val || '') + '" placeholder="' + (f.placeholder || '') + '">';
      if (f.desc) {
        html += '<small class="text-muted" style="font-size:11px">' + f.desc + '</small>';
      }
      html += '</div>';
    });
    form.innerHTML = html;
  }

  function _renderFinanceForm() {
    var form = document.getElementById('acc-finance-form');
    if (!form) return;
    var html = '';
    FINANCE_FIELDS.forEach(function (f) {
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

  function _collectAllFields() {
    var items = [];
    COMPANY_FIELDS.concat(FINANCE_FIELDS).forEach(function (f) {
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
      body: JSON.stringify({ settings: items, category: 'accounting' }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.success) {
        showToast('تم حفظ إعدادات الحسابات بنجاح', 'success');
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
    _renderCompanyForm: _renderCompanyForm,
    _renderFinanceForm: _renderFinanceForm,
  };
})();
