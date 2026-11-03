// ============================================================
//  DATA & STATE
// ============================================================
const API_BASE = '/api';

function getApiKey() { return localStorage.getItem('API_KEY') || 'admin'; }

function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

async function logout() {
  if (!confirm('هل أنت متأكد من تسجيل الخروج؟')) return;
  try { await fetch('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  window.location.href = '/login';
}

let currentUserPermissions = [];

function hasPermission(perm) {
  if (!currentUserPermissions || !currentUserPermissions.length) return false;
  if (currentUserPermissions[0] === '*') return true;
  return currentUserPermissions.indexOf(perm) !== -1;
}

function applyNavPermissionFilter() {
  if (!window._isLoggedIn) return;
  var navPermMap = {
    'nav-dashboard': 'nav_dashboard',
    'nav-reports': 'nav_reports',
    'nav-settings': 'nav_settings',
    'nav-backup': 'nav_backup',
    'nav-users': 'nav_users',
  };
  document.querySelectorAll('.nav-item-link').forEach(function(el) {
    var perm = navPermMap[el.id];
    if (perm === undefined) return;
    if (perm === null) { el.style.display = 'none'; return; }
    el.style.display = hasPermission(perm) ? '' : 'none';
  });
}

const NAV_ITEMS = [
  { section: 'القوائم الرئيسية' },
  { id: 'dashboard', label: 'لوحة التحكم', icon: 'fa-th-large', perm: 'nav_dashboard' },
  { id: 'example', label: 'العناصر التجريبية', icon: 'fa-cubes', perm: 'nav_example' },
  { id: 'reports', label: 'التقارير', icon: 'fa-chart-pie', perm: 'nav_reports' },
  { section: 'الإعدادات العامة' },
  { id: 'settings', label: 'الإعدادات العامة', icon: 'fa-cog', perm: 'nav_settings' },
  { id: 'backup', label: 'النسخ الاحتياطية', icon: 'fa-database', perm: 'nav_backup' },
  { id: 'users', label: 'إدارة المستخدمين', icon: 'fa-users', perm: 'nav_users' },
];

const PAGE_TITLES = {
  dashboard: 'لوحة التحكم',
  example: 'العناصر التجريبية',
  reports: 'التقارير',
  settings: 'الإعدادات العامة',
  backup: 'النسخ الاحتياطية',
  users: 'إدارة المستخدمين',
};

// ============================================================
//  SIDEBAR / NAVIGATION
// ============================================================
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main-content');
  const navbar = document.querySelector('.top-navbar');
  const icon = document.getElementById('sidebar-toggle-icon');
  sidebar.classList.toggle('collapsed');
  main.classList.toggle('expanded');
  navbar.classList.toggle('collapsed');
  icon.classList.toggle('fa-angles-right');
  icon.classList.toggle('fa-angles-left');
}

function openMobileSidebar() {
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  if (!sidebar || !overlay) return;
  sidebar.classList.add('mobile-open');
  overlay.classList.add('show');
  document.body.classList.add('sidebar-open');
}

function closeMobileSidebar() {
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.remove('mobile-open');
  if (overlay) overlay.classList.remove('show');
  document.body.classList.remove('sidebar-open');
}

function showPage(page) {
  document.querySelectorAll('.modal-backdrop').forEach(function(b) { b.remove(); });
  document.querySelectorAll('.modal').forEach(function(m) { m.classList.remove('show'); });
  document.body.classList.remove('modal-open');
  document.body.style.overflow = '';

  // Permission check only for logged-in users with loaded permissions
  if (window._authCompleted && window._isLoggedIn) {
    var navItem = NAV_ITEMS.find(function(n) { return n.id === page || n.id === (page.indexOf('/') !== -1 ? page.split('/')[0] : page); });
    if (navItem && navItem.perm && !hasPermission(navItem.perm)) {
      showToast('لا تملك صلاحية الوصول إلى هذه الصفحة', 'error');
      return;
    }
  }

  document.querySelectorAll('.page-content').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item-link').forEach(n => n.classList.remove('active'));

  var basePage = page.indexOf('/') !== -1 ? page.split('/')[0] : page;
  var pageEl = document.getElementById('page-' + basePage);
  if (pageEl) pageEl.classList.add('active');
  var navEl = document.getElementById('nav-' + basePage);
  if (navEl) navEl.classList.add('active');
  var subNavEl = document.getElementById('nav-' + page);
  if (subNavEl) subNavEl.classList.add('active');

  var titleEl = document.getElementById('topbar-page-title');
  if (titleEl) titleEl.textContent = PAGE_TITLES[basePage] || (page.indexOf('/') !== -1 ? page.split('/')[1] : page);

  updateTopbarActions(page);

  if (page === 'dashboard') loadDashboardStats();
  else if (page === 'backup') loadBackupPage();
  else if (page === 'settings') settings.init();
  else if (page === 'users') { reloadUsers(); loadGroups(); }
  else if (page === 'reports' && typeof auditReports !== 'undefined') { auditReports.init(); }
  else if (typeof window['moduleInit_' + basePage] === 'function') { window['moduleInit_' + basePage](); }
  else if (typeof window['moduleInit_' + basePage] === 'function') { window['moduleInit_' + basePage](); }

  closeMobileSidebar();
}

function updateTopbarActions(page) {
  const container = document.getElementById('topbar-actions');
  if (!container) return;
  container.innerHTML = '<button class="topbar-btn" onclick="refreshData()" title="تحديث"><i class="fas fa-rotate-right"></i></button>';
}

function refreshData() {
  const active = document.querySelector('.page-content.active');
  if (!active) return;
  const id = active.id.replace('page-', '');
  showPage(id);
}

// ============================================================
//  AUTH
// ============================================================
async function checkAuthStatus() {
  try {
    const res = await fetch('/api/auth/status', { credentials: 'same-origin' });
    const data = await res.json();
    if (data.logged_in) {
      const u = data.user;
      currentUserPermissions = u.permissions || [];
      window._currentUser = u;
      window._isLoggedIn = true;
      document.getElementById('sidebar-user-name').textContent = u.name;
      document.getElementById('sidebar-user-role').textContent = u.system_role_name || '';
      document.getElementById('nav-user-name').textContent = u.name;
      document.getElementById('nav-user-role').textContent = u.system_role_name || '';
      const initials = (u.name || u.username || '??').split(' ').filter(Boolean).slice(0, 2).map(s => s[0]).join('');
      document.getElementById('nav-user-initials').textContent = initials;
      document.getElementById('dropdown-user-initials').textContent = initials;
      document.getElementById('dropdown-user-name').textContent = u.name;
      document.getElementById('dropdown-user-job').textContent = u.job_title || '';
      document.getElementById('dropdown-user-dept').textContent = u.department || '';
      window._authCompleted = true;
      applyNavPermissionFilter();
    }
  } catch (e) { console.log('Auth check failed'); }
  window._authCompleted = true;
}

// ============================================================
//  API HELPER
// ============================================================
function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}), 'X-API-KEY': getApiKey() };
  const csrfToken = getCsrfToken();
  if (csrfToken) headers['X-CSRFToken'] = csrfToken;
  const controller = new AbortController();
  const timeout = setTimeout(function() { controller.abort(); }, 30000);
  return fetch(path, { ...options, headers, credentials: 'same-origin', signal: controller.signal }).finally(function() { clearTimeout(timeout); });
}

async function apiFetchJSON(path, options = {}) {
  const res = await apiFetch(path, options);
  if (res.status === 401) {
    window._isLoggedIn = false;
    window.location.href = '/login';
    throw new Error('يجب تسجيل الدخول أولاً');
  }
  if (!res.ok) throw new Error(await res.text().catch(() => 'HTTP ' + res.status));
  return res.json();
}

// ============================================================
//  DATE / TIME
// ============================================================
function updateDateTime() {
  const now = new Date();
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const el = document.getElementById('topNavDateText');
  if (el) el.textContent = now.toLocaleDateString('ar-SA', options);
}

// ============================================================
//  PROFILE DROPDOWN
// ============================================================
function toggleProfileDropdown() {
  document.getElementById('profileDropdown').classList.toggle('show');
}

document.addEventListener('click', function(e) {
  const dropdown = document.getElementById('profileDropdown');
  const profile = document.querySelector('.top-nav-profile');
  if (dropdown && profile && !profile.contains(e.target)) {
    dropdown.classList.remove('show');
  }
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar && sidebar.classList.contains('mobile-open') && !sidebar.contains(e.target)) {
    closeMobileSidebar();
  }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeMobileSidebar();
    const dropdown = document.getElementById('profileDropdown');
    if (dropdown) dropdown.classList.remove('show');
  }
});

window.addEventListener('resize', debounce(function() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar || !sidebar.classList.contains('mobile-open')) return;
  if (window.innerWidth >= 992) closeMobileSidebar();
}, 150));

// ============================================================
//  NOTIFICATIONS
// ============================================================
function showNotifications() {
  showToast('لا توجد إشعارات حالياً', 'info');
}

function handleGlobalSearch(val) {}

// ============================================================
//  TOAST
// ============================================================
function showToast(message, type) {
  const colors = { success: '#059669', error: '#dc2626', warning: '#d97706', info: '#2563eb' };
  const bg = colors[type] || '#374151';
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:' + bg + ';color:#fff;padding:12px 24px;border-radius:10px;font-size:14px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.2);font-family:Cairo,sans-serif;';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// ============================================================
//  DASHBOARD
// ============================================================


async function loadDashboardStats() {
  try {
    const data = await apiFetchJSON(API_BASE + '/dashboard/stats');
    function setStat(id, val) {
      var el = document.getElementById(id);
      if (el) el.textContent = val || 0;
    }
    setStat('stat-total-users', data.total_users);
    setStat('stat-active-users', data.active_users);
    setStat('stat-audit-today', data.audit_events_today);
    setStat('stat-audit-total', data.total_audit_events);

    // Latest audit activity
    var auditTbody = document.getElementById('dash-audit-tbody');
    if (auditTbody && data.latest_audit) {
      auditTbody.innerHTML = data.latest_audit.map(function(log) {
        var ts = log.created_at ? new Date(log.created_at).toLocaleString('ar') : '—';
        return '<tr><td>' + escapeHtml(log.user_name || '—') + '</td><td>' + escapeHtml(log.action_label || log.action || '—') + '</td><td>' + escapeHtml(log.module || '—') + '</td><td>' + escapeHtml(log.object_repr || '—') + '</td><td style="font-size:12px;color:#6b7280;">' + ts + '</td></tr>';
      }).join('');
    }
  } catch (e) {
    showToast('فشل تحميل بيانات لوحة التحكم', 'error');
  }
}

// ============================================================
//  BACKUP
// ============================================================
async function createBackup() {
  try {
    const res = await apiFetchJSON(API_BASE + '/backup/create', { method: 'POST' });
    showToast(res.message || 'تم حفظ النسخ الاحتياطية', 'success');
    loadBackupPage();
  } catch (e) { showToast('فشل حفظ النسخ الاحتياطية', 'error'); }
}

async function loadBackupPage() {
  try {
    const backups = await apiFetchJSON(API_BASE + '/backup/list');
    document.getElementById('backup-count').textContent = backups.length;
    const tbody = document.getElementById('backupTableBody');
    const empty = document.getElementById('backup-empty');
    if (backups.length === 0) {
      if (tbody) tbody.innerHTML = '';
      if (empty) empty.style.display = 'block';
      document.getElementById('last-backup-date').textContent = '--';
      document.getElementById('total-backup-size').textContent = '--';
      return;
    }
    if (empty) empty.style.display = 'none';
    document.getElementById('last-backup-date').textContent = backups[0].created_at.split('T')[0];
    const totalSize = backups.reduce((sum, b) => sum + (b.size || 0), 0);
    document.getElementById('total-backup-size').textContent = formatFileSize(totalSize);

    if (tbody) {
      tbody.innerHTML = backups.map((b, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(b.filename)}</td>
          <td>${b.created_at.split('T')[0]}</td>
          <td>${b.size_display || formatFileSize(b.size)}</td>
          <td>
            <button class="btn-action btn-edit" onclick="restoreBackup('${b.filename}')" title="استعادة"><i class="fas fa-undo"></i></button>
            <button class="btn-action btn-delete" onclick="deleteBackup('${b.filename}')" title="حذف"><i class="fas fa-trash"></i></button>
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {}
}

async function restoreBackup(filename) {
  if (!confirm('هل أنت متأكد من استعادة النسخة الاحتياطية؟')) return;
  try {
    const res = await apiFetchJSON(API_BASE + '/backup/restore', {
      method: 'POST',
      body: JSON.stringify({ filename })
    });
    showToast(res.message || 'تم استعادة النسخة', 'success');
  } catch (e) { showToast('فشل استعادة النسخة', 'error'); }
}

async function deleteBackup(filename) {
  if (!confirm('هل أنت متأكد من حذف النسخة الاحتياطية؟')) return;
  try {
    await apiFetchJSON(API_BASE + '/backup/' + filename, { method: 'DELETE' });
    showToast('تم حذف النسخة', 'success');
    loadBackupPage();
  } catch (e) { showToast('فشل حذف النسخة', 'error'); }
}

function formatFileSize(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  for (const unit of units) {
    if (size < 1024) return size.toFixed(1) + ' ' + unit;
    size /= 1024;
  }
  return size.toFixed(1) + ' TB';
}

// ============================================================
//  SETTINGS - Modules (التقارير, الحسابات, الطباعة)
// ============================================================
const settings = {
  currentModule: 'reporting',

  MODULES: {
    reporting: { label: 'إعداد التقارير', icon: 'fa-chart-bar' },
    accounting: { label: 'إعداد الحسابات', icon: 'fa-calculator' },
    printing: { label: 'إعداد الطباعة', icon: 'fa-print' },
  },

  async init() {
    this.switchModule('reporting');
  },

  switchModule(module) {
    this.currentModule = module;
    document.querySelectorAll('#settingsTabs .set-tab').forEach(function (t) { t.classList.remove('active'); });
    var tab = document.querySelector('.set-tab[data-module="' + module + '"]');
    if (tab) tab.classList.add('active');

    var rptPanel = document.getElementById('settingsReportingPanel');
    var accPanel = document.getElementById('settingsAccountingPanel');
    var prtPanel = document.getElementById('settingsPrintingPanel');
    var actionsEl = document.getElementById('settingsHeaderActions');

    if (rptPanel) rptPanel.style.display = module === 'reporting' ? '' : 'none';
    if (accPanel) accPanel.style.display = module === 'accounting' ? '' : 'none';
    if (prtPanel) prtPanel.style.display = module === 'printing' ? '' : 'none';

    if (actionsEl) actionsEl.innerHTML = '';

    if (module === 'reporting') {
      if (typeof reportSettings !== 'undefined') reportSettings.init();
      this._renderRptStats();
    } else if (module === 'accounting') {
      if (typeof accountingSettings !== 'undefined') accountingSettings.init();
      this._renderAccStats();
    } else if (module === 'printing') {
      if (typeof printSettings !== 'undefined') printSettings.init();
      this._renderPrtStats();
    }
  },

  _renderRptStats() {
    var statsEl = document.getElementById('settingsStats');
    if (!statsEl) return;
    statsEl.innerHTML =
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e8f0fe,#c6d9f7)"><i class="fas fa-file-pdf" style="color:#1967d2"></i></div><div class="set-stat-info"><div class="set-stat-value">14</div><div class="set-stat-label">إعداد التقارير</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e6f7ee,#b8e6cc)"><i class="fas fa-file-excel" style="color:#1e8e3e"></i></div><div class="set-stat-info"><div class="set-stat-value">PDF</div><div class="set-stat-label">الصيغة الافتراضية</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fef7e0,#fde9b3)"><i class="fas fa-list-ol" style="color:#e37400"></i></div><div class="set-stat-info"><div class="set-stat-value">20</div><div class="set-stat-label">عناصر/صفحة</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fce8e6,#f5c6c2)"><i class="fas fa-sync-alt" style="color:#d93025"></i></div><div class="set-stat-info"><div class="set-stat-value">300</div><div class="set-stat-label">ثانية تحديث</div></div></div>';
  },

  _renderAccStats() {
    var statsEl = document.getElementById('settingsStats');
    if (!statsEl) return;
    statsEl.innerHTML =
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e8f0fe,#c6d9f7)"><i class="fas fa-building" style="color:#1967d2"></i></div><div class="set-stat-info"><div class="set-stat-value">12</div><div class="set-stat-label">إعداد الحسابات</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e6f7ee,#b8e6cc)"><i class="fas fa-coins" style="color:#1e8e3e"></i></div><div class="set-stat-info"><div class="set-stat-value">د.ل</div><div class="set-stat-label">العملة الافتراضية</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fef7e0,#fde9b3)"><i class="fas fa-percent" style="color:#e37400"></i></div><div class="set-stat-info"><div class="set-stat-value">0%</div><div class="set-stat-label">نسبة الضريبة</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fce8e6,#f5c6c2)"><i class="fas fa-calendar-alt" style="color:#d93025"></i></div><div class="set-stat-info"><div class="set-stat-value">1</div><div class="set-stat-label">بداية السنة المالية</div></div></div>';
  },

  _renderPrtStats() {
    var statsEl = document.getElementById('settingsStats');
    if (!statsEl) return;
    statsEl.innerHTML =
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e8f0fe,#c6d9f7)"><i class="fas fa-file" style="color:#1967d2"></i></div><div class="set-stat-info"><div class="set-stat-value">14</div><div class="set-stat-label">إعداد الطباعة</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#e6f7ee,#b8e6cc)"><i class="fas fa-ruler-combined" style="color:#1e8e3e"></i></div><div class="set-stat-info"><div class="set-stat-value">A4</div><div class="set-stat-label">حجم الورقة</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fef7e0,#fde9b3)"><i class="fas fa-text-height" style="color:#e37400"></i></div><div class="set-stat-info"><div class="set-stat-value">12</div><div class="set-stat-label">حجم الخط</div></div></div>' +
      '<div class="set-stat-card"><div class="set-stat-icon" style="background:linear-gradient(135deg,#fce8e6,#f5c6c2)"><i class="fas fa-copy" style="color:#d93025"></i></div><div class="set-stat-info"><div class="set-stat-value">1</div><div class="set-stat-label">عدد النسخ</div></div></div>';
  },

  _rptTab(tab) {
    document.querySelectorAll('#settingsReportingPanel .set-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-rpttab') === tab);
    });
    var configPanel = document.getElementById('rpt-config-panel');
    var appearancePanel = document.getElementById('rpt-appearance-panel');
    if (tab === 'general') {
      configPanel.style.display = '';
      appearancePanel.style.display = 'none';
      if (typeof reportSettings !== 'undefined') reportSettings._renderConfigForm();
    } else {
      configPanel.style.display = 'none';
      appearancePanel.style.display = '';
      if (typeof reportSettings !== 'undefined') reportSettings._renderAppearanceForm();
    }
    this._renderRptStats();
  },

  _accTab(tab) {
    document.querySelectorAll('#settingsAccountingPanel .set-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-acctab') === tab);
    });
    var companyPanel = document.getElementById('acc-company-panel');
    var financePanel = document.getElementById('acc-finance-panel');
    if (tab === 'company') {
      companyPanel.style.display = '';
      financePanel.style.display = 'none';
      if (typeof accountingSettings !== 'undefined') accountingSettings._renderCompanyForm();
    } else {
      companyPanel.style.display = 'none';
      financePanel.style.display = '';
      if (typeof accountingSettings !== 'undefined') accountingSettings._renderFinanceForm();
    }
    this._renderAccStats();
  },

  _prtTab(tab) {
    document.querySelectorAll('#settingsPrintingPanel .set-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-prttab') === tab);
    });
    var layoutPanel = document.getElementById('prt-layout-panel');
    var contentPanel = document.getElementById('prt-content-panel');
    if (tab === 'layout') {
      layoutPanel.style.display = '';
      contentPanel.style.display = 'none';
      if (typeof printSettings !== 'undefined') printSettings._renderLayoutForm();
    } else {
      layoutPanel.style.display = 'none';
      contentPanel.style.display = '';
      if (typeof printSettings !== 'undefined') printSettings._renderContentForm();
    }
    this._renderPrtStats();
  },
};

// ============================================================
//  USERS MANAGEMENT
// ============================================================
let users = [];
let groups = [];
let roles = [];
let masterPermissions = [];
let permissionGroups = [];
let pendingDeleteUserId = null;

async function reloadUsers() {
  try {
    users = await apiFetchJSON(API_BASE + '/users');
    updateUserStats();
    renderUsersTable();
  } catch (e) { showToast('فشل تحميل المستخدمين', 'error'); }
}

function updateUserStats() {
  const total = users.length;
  const active = users.filter(u => u.is_active !== false).length;
  const inactive = total - active;
  const admins = users.filter(u => u.is_superuser).length;
  document.getElementById('users-stat-total').textContent = total;
  document.getElementById('users-stat-active').textContent = active;
  document.getElementById('users-stat-inactive').textContent = inactive;
  document.getElementById('users-stat-admins').textContent = admins;
}

function renderUsersTable() {
  const tbody = document.getElementById('usersTableBody');
  const badge = document.getElementById('users-count-badge');
  if (badge) badge.textContent = users.length;
  if (!tbody) return;

  const q = (document.getElementById('usersSearchInput')?.value || '').trim().toLowerCase();
  const filtered = q ? users.filter(u =>
    (u.full_name || '').toLowerCase().includes(q) ||
    (u.username || '').toLowerCase().includes(q) ||
    (u.job_title || '').toLowerCase().includes(q) ||
    (u.department || '').toLowerCase().includes(q) ||
    (u.employee_number || '').toLowerCase().includes(q)
  ) : users;

  tbody.innerHTML = filtered.map((u, i) => {
    const statusHtml = u.is_superuser
      ? '<span class="status-badge" style="background:#d97706;color:#fff;font-size:11px">مدير النظام</span>'
      : u.is_active !== false
        ? '<span class="status-badge" style="background:#059669;color:#fff;font-size:11px">نشط</span>'
        : '<span class="status-badge" style="background:#6b7280;color:#fff;font-size:11px">غير نشط</span>';
    return `<tr>
      <td>${i + 1}</td>
      <td><strong>${escapeHtml(u.full_name)}</strong></td>
      <td>${escapeHtml(u.username)}</td>
      <td>${escapeHtml(u.job_title || '-')}</td>
      <td>${escapeHtml(u.department || '-')}</td>
      <td>${escapeHtml(u.employee_number || '-')}</td>
      <td>${escapeHtml(u.group_name || '-')}</td>
      <td>${escapeHtml(u.system_role_name || '-')}</td>
      <td>${statusHtml}</td>
      <td>
        <button class="btn-action btn-edit" onclick="openUserModal(${u.id})" title="تعديل"><i class="fas fa-pen"></i></button>
        <button class="btn-action btn-delete" onclick="openDeleteUserModal(${u.id})" title="حذف"><i class="fas fa-trash"></i></button>
      </td>
    </tr>`;
  }).join('');
}

function filterUsers() {
  renderUsersTable();
}

async function openUserModal(id) {
  const isEdit = !!id;
  document.getElementById('userEditId').value = id || '';
  document.getElementById('userModalLabel').textContent = isEdit ? 'تعديل المستخدم' : 'إضافة مستخدم جديد';

  if (isEdit) {
    const u = users.find(x => x.id === id);
    if (u) {
      document.getElementById('userFullName').value = u.full_name || '';
      document.getElementById('userUsername').value = u.username || '';
      document.getElementById('userPassword').value = '';
      document.getElementById('userEmail').value = u.email || '';
      document.getElementById('userPhone').value = u.phone || '';
      document.getElementById('userEmployeeNumber').value = u.employee_number || '';
      document.getElementById('userIsActive').checked = u.is_active !== false;
    }
  } else {
    document.getElementById('userFullName').value = '';
    document.getElementById('userUsername').value = '';
    document.getElementById('userPassword').value = '';
    document.getElementById('userEmail').value = '';
    document.getElementById('userPhone').value = '';
    document.getElementById('userEmployeeNumber').value = '';
    document.getElementById('userIsActive').checked = true;
  }

  try {
    await populateGroupDropdown(id);
  } catch (e) {}

  try {
    await populateUserRoleItems(id);
  } catch (e) {}

  try {
    await populateLookupSelect('userJobTitle', 'job_title', id ? (users.find(x => x.id === id)?.job_title || '') : '');
  } catch (e) {}

  try {
    await populateLookupSelect('userDepartment', 'department', id ? (users.find(x => x.id === id)?.department || '') : '');
  } catch (e) {}

  new bootstrap.Modal(document.getElementById('userModal')).show();
}

async function populateLookupSelect(selectId, category, selectedValue) {
  try {
    const data = await apiFetchJSON(API_BASE + '/settings/lookups');
    const items = data.lookups || [];
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const label = category === 'job_title' ? 'اختر الوظيفة' : 'اختر القسم';
    sel.innerHTML = '<option value="">— ' + label + ' —</option>' +
      items
        .filter(l => l.category === category)
        .map(l => `<option value="${l.name}" ${l.name === selectedValue ? 'selected' : ''}>${escapeHtml(l.name)}</option>`)
        .join('');
  } catch (e) {}
}

async function populateGroupDropdown(userId) {
  try {
    groups = await apiFetchJSON(API_BASE + '/users/groups');
    const groupSel = document.getElementById('userGroup');
    if (groupSel) {
      const u = userId ? users.find(x => x.id === userId) : null;
      groupSel.innerHTML = '<option value="">— بدون مجموعة —</option>' +
        groups.map(g => `<option value="${g.id}" ${u && u.group_id === g.id ? 'selected' : ''}>${escapeHtml(g.name)}</option>`).join('');
    }
  } catch (e) {}
}

async function populateUserRoleItems(userId) {
  try {
    roles = await apiFetchJSON(API_BASE + '/users/roles');
    const tagWrap = document.getElementById('selectedRoleTag');
    const menu = document.getElementById('roleDropdownMenu');
    const hiddenInput = document.getElementById('userSystemRole');
    if (!tagWrap || !menu) return;
    const u = userId ? users.find(x => x.id === userId) : null;
    const selectedId = u ? u.system_role_id : null;
    const selectedRole = selectedId ? roles.find(r => r.id === selectedId) : null;

    // --- Render selected role tag ---
    if (selectedRole) {
      tagWrap.innerHTML = `<span class="selected-role-tag">
        <span>${escapeHtml(selectedRole.name)}</span>
        <span class="tag-count">(${Array.isArray(selectedRole.permissions) ? selectedRole.permissions.length : 0})</span>
        <span class="tag-close" onclick="event.stopPropagation();clearSelectedRole()" title="إزالة">&times;</span>
      </span>`;
    } else {
      tagWrap.innerHTML = `<span class="selected-role-tag" style="background:#e4eaf2;color:#6b7280;font-weight:400">
        بدون صلاحية
      </span>`;
    }

    // --- Render role options dropdown ---
    if (!roles.length) {
      menu.innerHTML = '<div class="role-no-option">لا توجد صلاحيات متاحة</div>';
    } else {
      menu.innerHTML = roles.map(r => {
        const isSelected = selectedId === r.id;
        return `<div class="role-option-card${isSelected ? ' selected' : ''}" data-role-id="${r.id}" onclick="selectRoleOption(this)">
          <span class="role-option-name">${escapeHtml(r.name)}</span>
          <span class="role-option-desc">${escapeHtml(r.description || '-')}</span>
          <span class="role-option-badge">${Array.isArray(r.permissions) ? r.permissions.length : 0}</span>
        </div>`;
      }).join('');
    }

    if (hiddenInput) hiddenInput.value = selectedId || '';
  } catch (e) {}
}

function toggleRoleDropdown(e) {
  e.stopPropagation();
  const toggle = document.getElementById('roleDropdownToggle');
  const menu = document.getElementById('roleDropdownMenu');
  if (!toggle || !menu) return;
  const isOpen = menu.classList.contains('show');
  closeAllRoleDropdowns();
  if (!isOpen) {
    menu.classList.add('show');
    toggle.classList.add('open');
  }
}

function closeAllRoleDropdowns() {
  document.querySelectorAll('.role-dropdown-menu').forEach(m => m.classList.remove('show'));
  document.querySelectorAll('.role-dropdown-toggle').forEach(t => t.classList.remove('open'));
}

function selectRoleOption(el) {
  const roleId = parseInt(el.dataset.roleId);
  const hiddenInput = document.getElementById('userSystemRole');
  const menu = document.getElementById('roleDropdownMenu');
  if (hiddenInput) hiddenInput.value = roleId || '';
  menu.querySelectorAll('.role-option-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  closeAllRoleDropdowns();
  // Update tag
  const tagWrap = document.getElementById('selectedRoleTag');
  const role = roles.find(r => r.id === roleId);
  if (role) {
    tagWrap.innerHTML = `<span class="selected-role-tag">
      <span>${escapeHtml(role.name)}</span>
      <span class="tag-count">(${Array.isArray(role.permissions) ? role.permissions.length : 0})</span>
      <span class="tag-close" onclick="event.stopPropagation();clearSelectedRole()" title="إزالة">&times;</span>
    </span>`;
  }
}

function clearSelectedRole() {
  const hiddenInput = document.getElementById('userSystemRole');
  const tagWrap = document.getElementById('selectedRoleTag');
  const menu = document.getElementById('roleDropdownMenu');
  if (hiddenInput) hiddenInput.value = '';
  tagWrap.innerHTML = '<span class="selected-role-tag" style="background:#e4eaf2;color:#6b7280;font-weight:400">بدون صلاحية</span>';
  menu.querySelectorAll('.role-option-card').forEach(c => c.classList.remove('selected'));
}

function addNewRoleFromUser() {
  openRoleModal();
}

function addNewGroupFromUser() {
  openGroupModal();
}

async function saveUser() {
  const id = document.getElementById('userEditId').value;
  const data = {
    full_name: document.getElementById('userFullName').value.trim(),
    username: document.getElementById('userUsername').value.trim(),
    email: document.getElementById('userEmail').value.trim(),
    phone: document.getElementById('userPhone').value.trim(),
    job_title: document.getElementById('userJobTitle').value.trim(),
    department: document.getElementById('userDepartment').value.trim(),
    employee_number: document.getElementById('userEmployeeNumber').value.trim(),
    is_active: document.getElementById('userIsActive').checked,
    group_id: parseInt(document.getElementById('userGroup').value) || null,
    system_role_id: parseInt(document.getElementById('userSystemRole').value) ? parseInt(document.getElementById('userSystemRole').value) : null,
  };

  const pwd = document.getElementById('userPassword').value;
  if (pwd) data.password = pwd;

  try {
    let res;
    if (id) {
      res = await apiFetch(API_BASE + '/users/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } else {
      if (!data.username) { showToast('اسم المستخدم مطلوب', 'error'); return; }
      res = await apiFetch(API_BASE + '/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    }
    const result = await res.json();
    if (res.ok && result.success) {
      showToast(result.message || 'تم الحفظ بنجاح', 'success');
      bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
      await reloadUsers();
    } else {
      showToast(result.error || 'خطأ في الحفظ', 'error');
    }
  } catch (e) {
    showToast('حدث خطأ أثناء الحفظ', 'error');
  }
}

function openDeleteUserModal(id) {
  pendingDeleteUserId = id;
  const u = users.find(x => x.id === id);
  const preview = document.getElementById('deleteUserNamePreview');
  if (preview) preview.textContent = u ? u.full_name || u.username : '';
  new bootstrap.Modal(document.getElementById('deleteUserModal')).show();
}

async function confirmDeleteUser() {
  if (!pendingDeleteUserId) return;
  const id = pendingDeleteUserId;
  pendingDeleteUserId = null;
  try {
    const res = await apiFetch(API_BASE + '/users/' + id, { method: 'DELETE' });
    const data = await res.json();
    bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'))?.hide();
    if (res.ok && data.success) {
      showToast(data.message || 'تم الحذف', 'success');
      await reloadUsers();
    } else {
      showToast(data.error || 'خطأ في الحذف', 'error');
    }
  } catch (e) {
    showToast('حدث خطأ أثناء الحذف', 'error');
  }
}

// ============================================================
//  USER TABS
// ============================================================
function switchUserTab(tab) {
  document.querySelectorAll('#page-users .set-tab').forEach(t => t.classList.remove('active'));
  const tabEl = document.querySelector('#page-users .set-tab[data-module="' + tab + '"]');
  if (tabEl) tabEl.classList.add('active');
  document.getElementById('userTabUsers').style.display = tab === 'users' ? '' : 'none';
  document.getElementById('userTabGroups').style.display = tab === 'groups' ? '' : 'none';
  document.getElementById('userTabRoles').style.display = tab === 'roles' ? '' : 'none';
  if (tab === 'groups') loadGroups();
  if (tab === 'roles') loadRoles();
}

// ============================================================
//  GROUPS
// ============================================================
async function loadGroups() {
  try {
    groups = await apiFetchJSON(API_BASE + '/users/groups');
    const tbody = document.getElementById('groupsTableBody');
    const badge = document.getElementById('groups-count-badge');
    if (badge) badge.textContent = groups.length;
    if (!tbody) return;
    tbody.innerHTML = groups.map((g, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${escapeHtml(g.name)}</strong></td>
        <td>${g.description ? escapeHtml(g.description) : '-'}</td>
        <td>${g.created_at ? g.created_at.split('T')[0] : '-'}</td>
        <td>
          <button class="btn-action btn-edit" onclick="openGroupModal(${g.id})" title="تعديل"><i class="fas fa-pen"></i></button>
          <button class="btn-action btn-delete" onclick="deleteGroup(${g.id})" title="حذف"><i class="fas fa-trash"></i></button>
        </td>
      </tr>
    `).join('');
  } catch (e) {}
}

async function openGroupModal(id) {
  document.getElementById('groupEditId').value = id || '';
  document.getElementById('groupModalTitle').textContent = id ? 'تعديل المجموعة' : 'إضافة مجموعة';
  document.getElementById('groupName').value = '';
  document.getElementById('groupDesc').value = '';
  if (id) {
    try {
      groups = await apiFetchJSON(API_BASE + '/users/groups');
      const g = groups.find(x => x.id === id);
      if (g) {
        document.getElementById('groupName').value = g.name;
        document.getElementById('groupDesc').value = g.description || '';
      }
    } catch (e) {}
  }
  new bootstrap.Modal(document.getElementById('groupModal')).show();
}

async function saveGroup() {
  const id = document.getElementById('groupEditId').value;
  const name = document.getElementById('groupName').value.trim();
  const description = document.getElementById('groupDesc').value.trim();
  if (!name) { showToast('اسم المجموعة مطلوب', 'error'); return; }

  try {
    let res;
    if (id) {
      res = await apiFetch(API_BASE + '/users/groups/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
    } else {
      res = await apiFetch(API_BASE + '/users/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
    }
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'تم الحفظ', 'success');
      bootstrap.Modal.getInstance(document.getElementById('groupModal')).hide();
      await loadGroups();
      const userModal = document.getElementById('userModal');
      if (userModal.classList.contains('show')) {
        const uId = parseInt(document.getElementById('userEditId').value) || null;
        await populateGroupDropdown(uId);
      }
    } else {
      showToast(data.error || 'خطأ في الحفظ', 'error');
    }
  } catch (e) { showToast('حدث خطأ في الحفظ', 'error'); }
}

async function deleteGroup(id) {
  if (!confirm('هل أنت متأكد من حذف هذه المجموعة؟')) return;
  try {
    const res = await apiFetch(API_BASE + '/users/groups/' + id, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'تم الحذف', 'success');
      await loadGroups();
    } else {
      showToast(data.error || 'خطأ في الحذف', 'error');
    }
  } catch (e) { showToast('حدث خطأ في الحذف', 'error'); }
}

// ============================================================
//  PERMISSIONS MATRIX
// ============================================================
async function loadMasterPermissions() {
  try {
    const data = await apiFetchJSON(API_BASE + '/users/permissions');
    masterPermissions = data.permissions || [];
    permissionGroups = data.groups || [];
  } catch (e) {
    masterPermissions = [];
    permissionGroups = [];
    console.error('loadMasterPermissions error:', e);
  }
}

function renderPermissionsMatrix(selectedPermissions) {
  const container = document.getElementById('permissionsMatrix');
  if (!container) return;

  if (!masterPermissions.length) {
    container.innerHTML = '<div class="text-muted text-center py-3">لا توجد صلاحيات متاحة. قم بإنشاء صلاحية جديدة من الأعلى.</div>';
    return;
  }

  if (!selectedPermissions) selectedPermissions = [];
  const isAll = selectedPermissions.length === 1 && selectedPermissions[0] === '*';
  const perms = isAll ? [] : (Array.isArray(selectedPermissions) ? selectedPermissions : []);

  let usedGroups = permissionGroups.length > 0 ? permissionGroups : [];

  if (!usedGroups.length) {
    const seen = {};
    masterPermissions.forEach(p => {
      const g = p.group || 'other';
      if (!seen[g]) {
        seen[g] = { key: g, label: g === 'nav' ? 'قوائم النظام' : g === 'windows' ? 'نوافذ' : g === 'actions' ? 'الأزرار والإجراءات' : g === 'reports' ? 'التقارير' : g === 'print' ? 'طباعة' : 'أخرى', icon: '' };
        usedGroups.push(seen[g]);
      }
    });
  }

  const grouped = {};
  masterPermissions.forEach(p => {
    if (!grouped[p.group]) grouped[p.group] = [];
    grouped[p.group].push(p);
  });

  let html = '';
  usedGroups.forEach(group => {
    const groupPerms = grouped[group.key] || [];
    if (!groupPerms.length) return;

    html += '<div class="perm-group">' +
      '<div class="perm-group-header">' +
        '<i class="fas ' + (group.icon || 'fa-tag') + ' perm-group-icon"></i> ' +
        '<span class="perm-group-title">' + escapeHtml(group.label) + '</span>' +
        '<span class="perm-group-count">' + groupPerms.length + '</span>' +
      '</div>' +
      '<div class="perm-group-body">';

    groupPerms.forEach(p => {
      const checked = isAll || perms.indexOf(p.code) !== -1;
      html +=
        '<label class="perm-item">' +
        '<input class="perm-checkbox" type="checkbox" value="' + p.code + '" id="perm_' + p.code + '"' + (checked ? ' checked' : '') + '>' +
        '<span class="perm-label">' + escapeHtml(p.label) + '</span>' +
        '<span class="perm-code">' + p.code + '</span>' +
        '</label>';
    });

    html += '</div></div>';
  });

  container.innerHTML = html;
}

function checkAllPermissions(checked) {
  document.querySelectorAll('.perm-checkbox').forEach(cb => { cb.checked = checked; });
}

function getSelectedPermissions() {
  const checked = [];
  document.querySelectorAll('.perm-checkbox:checked').forEach(cb => checked.push(cb.value));
  return checked;
}

// ============================================================
//  ROLES
// ============================================================
async function loadRoles() {
  try {
    roles = await apiFetchJSON(API_BASE + '/users/roles');
    const tbody = document.getElementById('rolesTableBody');
    const badge = document.getElementById('roles-count-badge');
    if (badge) badge.textContent = roles.length;
    if (!tbody) return;
    tbody.innerHTML = roles.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${escapeHtml(r.name)}</strong></td>
        <td>${escapeHtml(r.description || '-')}</td>
        <td><span class="badge-count" style="background:#0F2D5C">${(r.permissions || []).length}</span></td>
        <td>${r.created_at ? r.created_at.split('T')[0] : '-'}</td>
        <td>
          <button class="btn-action btn-edit" onclick="openRoleModal(${r.id})" title="تعديل"><i class="fas fa-pen"></i></button>
          <button class="btn-action btn-delete" onclick="deleteRole(${r.id})" title="حذف"><i class="fas fa-trash"></i></button>
        </td>
      </tr>
    `).join('');
  } catch (e) {}
}

async function openRoleModal(id) {
  await loadMasterPermissions();
  const isEdit = !!id;
  document.getElementById('roleEditId').value = id || '';
  document.getElementById('roleModalTitle').textContent = isEdit ? 'تعديل صلاحية' : 'إضافة صلاحية جديدة';

  if (isEdit) {
    try {
      roles = await apiFetchJSON(API_BASE + '/users/roles');
      const r = roles.find(x => x.id === id);
      if (r) {
        document.getElementById('roleName').value = r.name;
        document.getElementById('roleDescription').value = r.description || '';
        renderPermissionsMatrix(r.permissions || []);
      }
    } catch (e) {}
  } else {
    document.getElementById('roleName').value = '';
    document.getElementById('roleDescription').value = '';
    renderPermissionsMatrix([]);
  }

  new bootstrap.Modal(document.getElementById('roleModal')).show();
}

async function saveRole() {
  const id = document.getElementById('roleEditId').value;
  const name = document.getElementById('roleName').value.trim();
  const description = document.getElementById('roleDescription').value.trim();
  const permissions = getSelectedPermissions();

  if (!name) { showToast('الرجاء إدخال الاسم', 'error'); return; }

  try {
    let res;
    if (id) {
      res = await apiFetch(API_BASE + '/users/roles/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, permissions }),
      });
    } else {
      res = await apiFetch(API_BASE + '/users/roles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, permissions }),
      });
    }
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'تم الحفظ', 'success');
      bootstrap.Modal.getInstance(document.getElementById('roleModal')).hide();
      await loadRoles();
      const userModal = document.getElementById('userModal');
      if (userModal.classList.contains('show')) {
        const uId = parseInt(document.getElementById('userEditId').value) || null;
        await populateUserRoleItems(uId);
      }
    } else {
      showToast(data.error || 'خطأ في الحفظ', 'error');
    }
  } catch (e) { showToast('حدث خطأ في الحفظ', 'error'); }
}

async function deleteRole(id) {
  if (!confirm('هل أنت متأكد من حذف هذه الصلاحية؟')) return;
  try {
    const res = await apiFetch(API_BASE + '/users/roles/' + id, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'تم الحذف', 'success');
      await loadRoles();
    } else {
      showToast(data.error || 'خطأ في الحذف', 'error');
    }
  } catch (e) { showToast('حدث خطأ في الحذف', 'error'); }
}

// ============================================================
//  UTILITY
// ============================================================

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Close role dropdown when clicking outside
document.addEventListener('click', function(e) {
  const dropdown = document.getElementById('roleDropdown');
  if (dropdown && !dropdown.contains(e.target)) {
    closeAllRoleDropdowns();
  }
});

// ============================================================
//  GLOBAL LOADING OVERLAY
// ============================================================
var _loadingCount = 0;
function showGlobalLoading() {
  _loadingCount++;
  var el = document.getElementById('globalLoading');
  if (el) el.classList.add('active');
}
function hideGlobalLoading() {
  _loadingCount = Math.max(0, _loadingCount - 1);
  if (_loadingCount === 0) {
    var el = document.getElementById('globalLoading');
    if (el) el.classList.remove('active');
  }
}

// ============================================================
//  DEBOUNCE UTILITY
// ============================================================
function debounce(fn, delay) {
  var timer;
  return function() {
    var ctx = this, args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function() { fn.apply(ctx, args); }, delay || 300);
  };
}

// ============================================================
//  SCROLL-TO-TOP BUTTON
// ============================================================
function initScrollToTop() {
  var btn = document.getElementById('scrollToTopBtn');
  if (!btn) return;
  window.addEventListener('scroll', debounce(function() {
    if (window.scrollY > 300) btn.classList.add('visible');
    else btn.classList.remove('visible');
  }, 100));
  btn.addEventListener('click', function() { window.scrollTo({ top: 0, behavior: 'smooth' }); });
}

// ============================================================
//  UNSAVED CHANGES GUARD
// ============================================================
window._hasUnsavedChanges = false;
function markUnsaved() { window._hasUnsavedChanges = true; }
function clearUnsaved() { window._hasUnsavedChanges = false; }
window.addEventListener('beforeunload', function(e) {
  if (window._hasUnsavedChanges) { e.preventDefault(); e.returnValue = ''; }
});

// ============================================================
//  INIT
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
  checkAuthStatus();
  updateDateTime();
  setInterval(updateDateTime, 60000);
  loadDashboardStats();
  initScrollToTop();
});


