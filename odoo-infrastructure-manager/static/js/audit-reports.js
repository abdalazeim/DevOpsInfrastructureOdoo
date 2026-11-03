// ============================================================
//  AUDIT REPORTS (سجل التدقيق)
//  Generic system audit-log reports (domain-agnostic).
// ============================================================
var auditReports = (function () {
  var _currentPage = 1;
  var _pageSize = 25;
  var _totalPages = 1;
  var _allRows = [];

  var ACTION_LABELS = {
    create: 'إنشاء',
    update: 'تحديث',
    delete: 'حذف',
    login: 'دخول',
    logout: 'خروج',
    approve: 'اعتماد',
    reject: 'رفض',
    other: 'أخرى',
  };

  var ACTION_COLORS = {
    create: '#059669',
    update: '#1967d2',
    delete: '#dc2626',
    login: '#7c3aed',
    logout: '#6b7280',
    approve: '#059669',
    reject: '#dc2626',
    other: '#9ca3af',
  };

  function init() {
    _currentPage = 1;
    _renderActionFilter();
    load();
  }

  function _renderActionFilter() {
    var sel = document.getElementById('rpt-action');
    if (!sel) return;
    var html = '<option value="">الكل</option>';
    Object.keys(ACTION_LABELS).forEach(function (k) {
      html += '<option value="' + k + '">' + ACTION_LABELS[k] + '</option>';
    });
    sel.innerHTML = html;
  }

  function load() {
    var params = new URLSearchParams();
    params.set('page', _currentPage);
    params.set('page_size', _pageSize);

    var search = (document.getElementById('rpt-search') || {}).value || '';
    if (search) params.set('search', search);

    var action = (document.getElementById('rpt-action') || {}).value || '';
    if (action) params.set('action', action);

    var dateFrom = (document.getElementById('rpt-date-from') || {}).value || '';
    if (dateFrom) params.set('date_from', dateFrom);

    var dateTo = (document.getElementById('rpt-date-to') || {}).value || '';
    if (dateTo) params.set('date_to', dateTo);

    apiFetch(API_BASE + '/audit-logs?' + params.toString())
      .then(function (r) {
        if (r.status === 401) { window.location.href = '/login'; throw new Error('unauthorized'); }
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (d) {
        var payload = (d && d.data) || {};
        var items = payload.items || [];
        var meta = payload.meta || {};
        _allRows = items;
        _totalPages = meta.pages || 1;
        _renderStats(items.length, meta.total || 0);
        _renderTable(items);
        _renderPagination(meta);
      })
      .catch(function () {
        _allRows = [];
        _renderStats(0, 0);
        _renderTable([]);
        _renderPagination({ page: 1, pages: 1 });
        showToast('فشل تحميل سجل التدقيق', 'error');
      });
  }

  function _renderStats(count, total) {
    var statsEl = document.getElementById('reportStats');
    if (!statsEl) return;
    statsEl.style.display = '';
    statsEl.innerHTML =
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e8f0fe,#c6d9f7)"><i class="fas fa-list" style="color:#1967d2"></i></div><div class="set-stat-info"><div class="set-stat-value">' + total + '</div><div class="set-stat-label">إجمالي السجلات</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e6f7ee,#b8e6cc)"><i class="fas fa-clipboard-list" style="color:#1e8e3e"></i></div><div class="set-stat-info"><div class="set-stat-value">' + count + '</div><div class="set-stat-label">سجل في هذه الصفحة</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fef7e0,#fde9b3)"><i class="fas fa-shield-alt" style="color:#e37400"></i></div><div class="set-stat-info"><div class="set-stat-value">تدقيق</div><div class="set-stat-label">سجل النشاطات</div></div></div>';
  }

  function _actionBadge(action) {
    var label = ACTION_LABELS[action] || action;
    var color = ACTION_COLORS[action] || '#9ca3af';
    return '<span class="badge" style="background:' + color + ';color:#fff;padding:3px 10px;border-radius:4px;font-size:11px;">' + label + '</span>';
  }

  function _renderTable(items) {
    var head = document.getElementById('reportTableHead');
    var body = document.getElementById('reportTableBody');
    var title = document.getElementById('reportTitle');
    if (title) title.innerHTML = '<i class="fas fa-history"></i> سجل التدقيق';
    if (head) {
      head.innerHTML = '<tr>' +
        '<th style="width:50px">#</th>' +
        '<th>المستخدم</th>' +
        '<th>الإجراء</th>' +
        '<th>الوحدة</th>' +
        '<th>الوصف</th>' +
        '<th>IP</th>' +
        '<th>التاريخ</th>' +
        '</tr>';
    }
    if (!body) return;
    if (items.length === 0) {
      body.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#9ca3af"><i class="fas fa-inbox" style="display:block;font-size:32px;margin-bottom:8px"></i>لا توجد سجلات</td></tr>';
      return;
    }
    body.innerHTML = items.map(function (e, i) {
      var offset = (_currentPage - 1) * _pageSize;
      var date = e.created_at ? new Date(e.created_at) : null;
      var dateStr = date ? date.toLocaleDateString('ar') + ' ' + date.toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' }) : '—';
      return '<tr>' +
        '<td>' + (offset + i + 1) + '</td>' +
        '<td><strong>' + escapeHtml(e.user_name || '—') + '</strong></td>' +
        '<td>' + _actionBadge(e.action) + '</td>' +
        '<td>' + escapeHtml(e.module || '—') + '</td>' +
        '<td>' + escapeHtml(e.object_repr || '—') + '</td>' +
        '<td style="direction:ltr;font-size:12px;color:#6b7280;">' + escapeHtml(e.ip_address || '—') + '</td>' +
        '<td style="font-size:12px;color:#6b7280;">' + dateStr + '</td>' +
        '</tr>';
    }).join('');
  }

  function _renderPagination(meta) {
    var infoEl = document.getElementById('rpt-pagination-info');
    var btnsEl = document.getElementById('rpt-pagination-btns');
    if (infoEl) {
      var from = _allRows.length === 0 ? 0 : ((meta.page || 1) - 1) * (meta.page_size || _pageSize) + 1;
      var to = from === 0 ? 0 : from + _allRows.length - 1;
      infoEl.textContent = 'عرض ' + from + ' إلى ' + to + ' من ' + (meta.total || 0) + ' سجل';
    }
    if (!btnsEl) return;
    var pages = meta.pages || 1;
    var current = meta.page || 1;
    var html = '';
    html += '<button class="pagination-btn" onclick="auditReports.goTo(' + (current - 1) + ')" ' + (current <= 1 ? 'disabled' : '') + '><i class="fas fa-chevron-right"></i></button>';
    var start = Math.max(1, current - 2);
    var end = Math.min(pages, start + 4);
    start = Math.max(1, end - 4);
    for (var p = start; p <= end; p++) {
      html += '<button class="pagination-btn' + (p === current ? ' active' : '') + '" onclick="auditReports.goTo(' + p + ')">' + p + '</button>';
    }
    html += '<button class="pagination-btn" onclick="auditReports.goTo(' + (current + 1) + ')" ' + (current >= pages ? 'disabled' : '') + '><i class="fas fa-chevron-left"></i></button>';
    btnsEl.innerHTML = html;
  }

  function goTo(page) {
    if (page < 1 || page > _totalPages) return;
    _currentPage = page;
    load();
  }

  function filterLocal() {
    _currentPage = 1;
    debounce(load, 300)();
  }

  function printReport() {
    var rows = _allRows;
    if (rows.length === 0) { showToast('لا توجد بيانات للطباعة', 'error'); return; }
    var html = '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8"><title>سجل التدقيق</title><style>' +
      'body{font-family:"Traditional Arabic","Arial",sans-serif;font-size:13px;direction:rtl;padding:16px}' +
      'h2{text-align:center;margin:0 0 4px}' +
      'p.meta{text-align:center;color:#555;margin:0 0 14px}' +
      'table{width:100%;border-collapse:collapse}' +
      'th,td{border:1px solid #000;padding:5px 8px;text-align:center}' +
      'th{background:#000;color:#fff}' +
      '</style></head><body>' +
      '<h2>سجل التدقيق</h2>' +
      '<p class="meta">' + new Date().toLocaleDateString('ar') + ' — ' + new Date().toLocaleTimeString('ar') + '</p>' +
      '<table><thead><tr><th>#</th><th>المستخدم</th><th>الإجراء</th><th>الوحدة</th><th>الوصف</th><th>IP</th><th>التاريخ</th></tr></thead><tbody>';
    rows.forEach(function (e, i) {
      var date = e.created_at ? new Date(e.created_at) : null;
      var dateStr = date ? date.toLocaleDateString('ar') + ' ' + date.toLocaleTimeString('ar') : '—';
      html += '<tr><td>' + (i + 1) + '</td><td>' + escapeHtml(e.user_name || '—') + '</td><td>' + escapeHtml(ACTION_LABELS[e.action] || e.action) + '</td><td>' + escapeHtml(e.module || '—') + '</td><td>' + escapeHtml(e.object_repr || '—') + '</td><td>' + escapeHtml(e.ip_address || '—') + '</td><td>' + dateStr + '</td></tr>';
    });
    html += '</tbody></table></body></html>';
    var win = window.open('', '_blank', 'width=900,height=650');
    if (!win) { showToast('الرجاء السماح بالنوافذ المنبثقة', 'error'); return; }
    win.document.write(html);
    win.document.close();
    win.print();
  }

  function exportCSV() {
    if (_allRows.length === 0) { showToast('لا توجد بيانات للتصدير', 'error'); return; }
    var cols = ['المستخدم', 'الإجراء', 'الوحدة', 'الوصف', 'IP', 'التاريخ'];
    var lines = [cols.join(',')];
    _allRows.forEach(function (e) {
      var date = e.created_at ? new Date(e.created_at) : null;
      var dateStr = date ? date.toLocaleDateString('ar') + ' ' + date.toLocaleTimeString('ar') : '';
      var row = [e.user_name || '', ACTION_LABELS[e.action] || e.action, e.module || '', e.object_repr || '', e.ip_address || '', dateStr];
      lines.push(row.map(function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(','));
    });
    var blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'audit-log-' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  return {
    init: init,
    load: load,
    goTo: goTo,
    filterLocal: filterLocal,
    printReport: printReport,
    exportCSV: exportCSV,
  };
})();
