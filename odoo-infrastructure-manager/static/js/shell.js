(function () {
  const sidebarKey = "infra.sidebar.collapsed";

  function setCollapsed(collapsed) {
    const sidebar = document.getElementById("sidebar");
    const main = document.getElementById("main-content");
    const navbar = document.querySelector(".top-navbar");
    if (!sidebar || !main || !navbar) return;
    sidebar.classList.toggle("collapsed", collapsed);
    main.classList.toggle("expanded", collapsed);
    navbar.classList.toggle("collapsed", collapsed);
    const icon = document.getElementById("sidebar-toggle-icon");
    if (icon) {
      icon.classList.toggle("fa-angles-right", !collapsed);
      icon.classList.toggle("fa-angles-left", collapsed);
    }
    document.querySelectorAll(".nav-item-link").forEach((link) => {
      if (collapsed) link.title = link.querySelector(".nav-label")?.textContent.trim() || "";
      else link.removeAttribute("title");
    });
    try { localStorage.setItem(sidebarKey, collapsed ? "1" : "0"); } catch (_) {}
  }

  window.toggleSidebar = function () {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) setCollapsed(!sidebar.classList.contains("collapsed"));
  };
  window.openMobileSidebar = function () {
    document.getElementById("sidebar")?.classList.add("mobile-open");
    document.getElementById("sidebar-overlay")?.classList.add("show");
    document.body.classList.add("sidebar-open");
  };
  window.closeMobileSidebar = function () {
    document.getElementById("sidebar")?.classList.remove("mobile-open");
    document.getElementById("sidebar-overlay")?.classList.remove("show");
    document.body.classList.remove("sidebar-open");
  };
  window.toggleProfileDropdown = function () {
    document.getElementById("profileDropdown")?.classList.toggle("show");
  };
  window.handleGlobalSearch = function (value) {
    const query = String(value || "").trim().toLowerCase();
    const rows = document.querySelectorAll(".infra-table tbody tr, .service-row, .automation-row, .run-row, .inventory-record");
    rows.forEach((row) => { row.hidden = Boolean(query) && !row.textContent.toLowerCase().includes(query); });
  };

  document.addEventListener("click", (event) => {
    const dropdown = document.getElementById("profileDropdown");
    const profile = document.querySelector(".top-nav-profile");
    if (dropdown && profile && !profile.contains(event.target)) dropdown.classList.remove("show");
    const sidebar = document.getElementById("sidebar");
    if (sidebar?.classList.contains("mobile-open") && !sidebar.contains(event.target)) window.closeMobileSidebar();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      window.closeMobileSidebar();
      document.getElementById("profileDropdown")?.classList.remove("show");
    }
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 992) window.closeMobileSidebar();
  });
  document.addEventListener("DOMContentLoaded", () => {
    let collapsed = false;
    try { collapsed = localStorage.getItem(sidebarKey) === "1"; } catch (_) {}
    if (collapsed) setCollapsed(true);
    const date = document.getElementById("topNavDateText");
    const updateDate = () => { if (date) date.textContent = new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }); };
    updateDate();
    window.setInterval(updateDate, 60_000);
  });
})();
