/**
 * LEAP2 Shared UI — theme toggle + mobile nav hamburger.
 *
 * Usage (every page):
 *   1. FOUC-prevention in <head> (before CSS):
 *        <script>
 *          (function(){var t=localStorage.getItem("leap-theme");
 *          if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme:dark)").matches))
 *          document.documentElement.classList.add("dark")})();
 *        </script>
 *
 *   2. Include this file (can be deferred):
 *        <script src="/static/theme-toggle.js" defer></script>
 *
 *   3. Theme toggle button (anywhere in navbar):
 *        <button class="theme-toggle" id="theme-toggle" aria-label="Toggle theme">
 *          <svg class="icon-sun" ...></svg>
 *          <svg class="icon-moon" ...></svg>
 *        </button>
 *
 *   4. Hamburger button (in navbar, before .navbar-links):
 *        <button class="nav-hamburger" id="nav-hamburger" aria-label="Menu">
 *          <svg ...></svg>
 *        </button>
 */
(function () {
  /* ── Theme toggle ── */
  var STORAGE_KEY = "leap-theme";

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function applyTheme(dark) {
    document.documentElement.classList.toggle("dark", dark);
  }

  function toggleTheme() {
    var next = !isDark();
    applyTheme(next);
    try { localStorage.setItem(STORAGE_KEY, next ? "dark" : "light"); } catch (_) {}
  }

  window.leapToggleTheme = toggleTheme;

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
    if (!localStorage.getItem(STORAGE_KEY)) {
      applyTheme(e.matches);
    }
  });

  /* ── Mobile nav hamburger ── */
  function toggleNav() {
    var links = document.querySelector(".navbar-links");
    if (links) links.classList.toggle("open");
  }

  function closeNav() {
    var links = document.querySelector(".navbar-links");
    if (links) links.classList.remove("open");
  }

  /* ── Bind on ready ── */
  function bind() {
    var themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

    var hamburger = document.getElementById("nav-hamburger");
    if (hamburger) hamburger.addEventListener("click", toggleNav);

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".navbar")) closeNav();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) closeNav();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
