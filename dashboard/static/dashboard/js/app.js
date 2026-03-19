(function () {
  const root = document.documentElement;
  const app = document.querySelector(".app");
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const sidebarCollapse = document.getElementById("sidebarCollapse");
  const year = document.getElementById("year");

  if (year) year.textContent = new Date().getFullYear();

  function updateThemeIcon(theme) {
    if (!themeIcon) return;
    // Light -> lua | Dark -> sol
    themeIcon.className = theme === "dark"
      ? "bi bi-sun-fill"
      : "bi bi-moon-stars-fill";
  }

  function setTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);
    updateThemeIcon(theme);
  }

  // ✅ inicializa (tema salvo ou light)
  const savedTheme = localStorage.getItem("theme") || "light";
  setTheme(savedTheme);

  function toggleTheme() {
    const current = root.getAttribute("data-bs-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    setTheme(next);
  }

  themeToggle?.addEventListener("click", toggleTheme);

  // Sidebar
  const savedSidebar = localStorage.getItem("sidebarCollapsed");
  if (savedSidebar === "true") app?.classList.add("sidebar-collapsed");

  function toggleSidebar() {
    app?.classList.toggle("sidebar-collapsed");
    const isCollapsed = app?.classList.contains("sidebar-collapsed");
    localStorage.setItem("sidebarCollapsed", String(isCollapsed));
  }

  sidebarCollapse?.addEventListener("click", toggleSidebar);
})();