/**
 * LEAP2 shared footer + admin badge — injected via <script src="/static/footer.js"></script>.
 *
 * - Renders the site footer with health/experiment status
 * - Loads admin-modal.js for login/change-password modals
 * - Adds an admin badge to the navbar when logged in
 * - Swaps footer links based on auth state (Login vs Change Password + Logout)
 */
(function () {
  // Load admin-modal.js (provides window.LEAP.showLogin / showChangePassword)
  var modalScript = document.createElement("script");
  modalScript.src = "/static/admin-modal.js";
  document.head.appendChild(modalScript);

  // ── Inject admin badge style ──
  var badgeStyle = document.createElement("style");
  badgeStyle.textContent =
    ".admin-badge{display:inline-flex;align-items:center;gap:0.3rem;font-size:0.6875rem;font-weight:500;" +
    "color:var(--color-accent);padding:0.125rem 0.5rem;border:1px solid var(--color-accent);" +
    "border-radius:99px;cursor:default;opacity:0;transition:opacity .3s;margin-left:0.25rem;}" +
    ".admin-badge.visible{opacity:1;}" +
    ".admin-badge svg{opacity:0.7;}";
  document.head.appendChild(badgeStyle);

  // ── Build footer ──
  var footer = document.createElement("footer");
  footer.className = "site-footer";
  footer.innerHTML =
    '<a href="/docs">API Docs</a> <span class="footer-sep">&middot;</span> ' +
    '<a href="#" class="footer-admin" id="ft-login">Admin</a>' +
    '<span class="footer-sep" id="ft-login-sep">&middot;</span> ' +
    '<a href="#" class="footer-admin" id="ft-chpw" style="display:none">Change Password</a>' +
    '<span class="footer-sep" id="ft-chpw-sep" style="display:none">&middot;</span> ' +
    '<a href="#" class="footer-admin" id="ft-reload" style="display:none">Reload Experiment</a>' +
    '<span class="footer-sep" id="ft-reload-sep" style="display:none">&middot;</span> ' +
    '<a href="#" class="footer-admin" id="ft-rediscover" style="display:none">Rediscover</a>' +
    '<span class="footer-sep" id="ft-rediscover-sep" style="display:none">&middot;</span> ' +
    '<a href="#" class="footer-admin" id="ft-logout" style="display:none">Logout</a>' +
    '<span class="footer-sep" id="ft-logout-sep" style="display:none">&middot;</span> ' +
    '<a href="https://github.com/leaplive/LEAP2" target="_blank" rel="noopener">GitHub</a>' +
    "<br>" +
    '<span class="footer-meta">' +
    '<span class="footer-status"><span class="footer-dot offline" id="ft-dot"></span> <span id="ft-status">...</span></span>' +
    ' <span class="footer-sep">&middot;</span> ' +
    '<span id="ft-info"></span>' +
    "</span>";

  document.body.appendChild(footer);

  // ── Wire footer links ──
  document.getElementById("ft-login").addEventListener("click", function (e) {
    e.preventDefault();
    if (window.LEAP && window.LEAP.showLogin) {
      window.LEAP.showLogin(function () { window.location.reload(); });
    }
  });
  document.getElementById("ft-chpw").addEventListener("click", function (e) {
    e.preventDefault();
    if (window.LEAP && window.LEAP.showChangePassword) window.LEAP.showChangePassword();
  });
  document.getElementById("ft-logout").addEventListener("click", async function (e) {
    e.preventDefault();
    try {
      await fetch("/logout", { method: "POST", credentials: "same-origin" });
    } catch (_) {}
    window.location.reload();
  });

  // ── Detect experiment name from URL ──
  var expMatch = window.location.pathname.match(/\/exp\/([^/]+)/);
  var expName = expMatch ? expMatch[1] : new URLSearchParams(window.location.search).get("exp");

  document.getElementById("ft-reload").addEventListener("click", async function (e) {
    e.preventDefault();
    if (!expName) return;
    var link = this;
    var orig = link.textContent;
    try {
      var res = await fetch("/exp/" + encodeURIComponent(expName) + "/admin/reload", {
        method: "POST", credentials: "same-origin",
      });
      if (res.ok) { window.location.reload(); return; }
      link.textContent = "Error";
    } catch (_) {
      link.textContent = "Error";
    }
    setTimeout(function () { link.textContent = orig; }, 1500);
  });
  document.getElementById("ft-rediscover").addEventListener("click", async function (e) {
    e.preventDefault();
    var link = this;
    try {
      var res = await fetch("/api/admin/rediscover", {
        method: "POST", credentials: "same-origin",
      });
      if (res.ok) { window.location.reload(); return; }
      link.textContent = "Error";
    } catch (_) {
      link.textContent = "Error";
    }
    var orig = "Rediscover";
    setTimeout(function () { link.textContent = orig; }, 1500);
  });

  // ── Health check ──
  fetch("/api/health")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("ft-dot").classList.remove("offline");
      document.getElementById("ft-status").textContent = "Healthy";
      var v = d.version ? "v" + d.version : "";
      document.getElementById("ft-info").textContent = v;
    })
    .catch(function () {
      document.getElementById("ft-status").textContent = "Offline";
    });

  // ── Experiment count ──
  fetch("/api/experiments")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var n = (d.experiments || []).length;
      var info = document.getElementById("ft-info");
      if (n > 0) {
        info.textContent =
          (info.textContent ? info.textContent + " \u00b7 " : "") +
          "Serving " + n + " experiment" + (n !== 1 ? "s" : "");
      }
    })
    .catch(function () {});

  // ── Admin auth — badge + footer state ──
  fetch("/api/auth-status", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.admin) {
        // Hide login link, show admin actions
        document.getElementById("ft-login").style.display = "none";
        document.getElementById("ft-login-sep").style.display = "none";
        var adminIds = ["ft-chpw", "ft-chpw-sep", "ft-logout", "ft-logout-sep"];
        if (!expName) adminIds.push("ft-rediscover", "ft-rediscover-sep");
        if (expName) adminIds.push("ft-reload", "ft-reload-sep");
        adminIds.forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.style.display = "";
        });

        // Add admin badge to navbar
        var navLinks = document.querySelector(".navbar-links");
        if (navLinks) {
          var badge = document.createElement("span");
          badge.className = "admin-badge";
          badge.innerHTML =
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
            "Admin";
          navLinks.insertBefore(badge, navLinks.querySelector(".theme-toggle"));
          // Animate in
          requestAnimationFrame(function () { badge.classList.add("visible"); });
        }
      }
    })
    .catch(function () {});
})();
