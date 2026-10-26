// ArtCraft Hub: launcher and installer manager for external ArtCraft creative desktop applications.
window.FOSS = window.FOSS || {};

(function () {
  var APPS = [
    {
      key: "photocraft",
      name: "PhotoCraft",
      desc: "Deep multi-layer photo editing, non-destructive layer masks, RAW processing, and advanced brush tools.",
      icon: "image"
    },
    {
      key: "pdfcraft",
      name: "PDFCraft",
      desc: "Advanced PDF form designer, AcroForm field inspection, vector markup annotations, and bookmarks manager.",
      icon: "file-text"
    },
    {
      key: "filmcraft",
      name: "FilmCraft",
      desc: "Multi-track non-linear video editing (NLE), audio mastering, transitions, and timeline compositing.",
      icon: "film"
    },
    {
      key: "vectorcraft",
      name: "VectorCraft",
      desc: "Scalable vector graphics (SVG) illustration, bezier paths, boolean operations, and typography layout.",
      icon: "edit-3"
    },
    {
      key: "cadcraft",
      name: "CADCraft",
      desc: "2D drafting and 3D parametric engineering design with precise geometric dimensioning.",
      icon: "box"
    }
  ];

  function renderSuite(panel, ctx) {
    panel.innerHTML = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "ArtCraft Creative Suite" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Dedicated external desktop applications for deep editing, audio/video NLE, vector graphics, and CAD." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "artcraft-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "artcraft-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var appsGrid = window.FOSS.dom.el("div", {
      className: "grid-auto",
      "data-testid": "artcraft-grid",
      style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)", width: "100%", marginTop: "var(--space-3)" }
    });

    ctx.api("get_artcraft_status", {}).then(function (res) {
      var statusMap = (res && res.status) || {};
      appsGrid.innerHTML = "";

      APPS.forEach(function (appDef) {
        var stat = statusMap[appDef.key] || { installed: false, path: "" };
        var card = window.FOSS.dom.el("div", {
          className: "card flex-col justify-between",
          "data-testid": "artcraft-card-" + appDef.key,
          style: { border: "1px solid var(--border)", padding: "var(--space-4)", display: "flex", flexDirection: "column", justifyContent: "space-between", minHeight: "200px" }
        });

        var top = window.FOSS.dom.el("div", { className: "stack-sm" }, [
          window.FOSS.dom.el("div", { className: "row items-center justify-between", style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, [
            window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", alignItems: "center", gap: "var(--space-2)" } }, [
              window.FOSS.icons.el(appDef.icon || "box", 20),
              window.FOSS.dom.el("h3", { className: "card-title text-base", text: appDef.name })
            ]),
            window.FOSS.dom.el("span", {
              className: "badge " + (stat.installed ? "badge-success" : "badge-neutral"),
              text: stat.installed ? "Installed" : "External"
            })
          ]),
          window.FOSS.dom.el("p", { className: "text-xs text-muted", style: { marginTop: "var(--space-2)", lineHeight: "1.5" }, text: appDef.desc })
        ]);

        var launchBtn = window.FOSS.dom.el("button", {
          className: "btn " + (stat.installed ? "btn-primary" : "btn-secondary") + " btn-sm",
          "data-testid": "artcraft-hub-launch-" + appDef.key,
          "aria-label": "Launch " + appDef.name,
          title: "Launch " + appDef.name,
          type: "button",
          style: { minHeight: "36px", marginTop: "var(--space-3)", width: "100%" },
          onClick: function () {
            clearError();
            statusBar.textContent = "Launching " + appDef.name + "...";
            ctx.api("launch_artcraft_app", { app_name: appDef.key }).then(function (lres) {
              if (lres && lres.ok) {
                statusBar.textContent = appDef.name + " launched successfully.";
              } else {
                showError((lres && lres.error) || (appDef.name + " not found on PATH. Install ArtCraft or add to PATH."));
              }
            });
          }
        }, [
          window.FOSS.icons.el("external-link", 16),
          window.FOSS.dom.el("span", { text: stat.installed ? "Launch Application" : "Launch or Locate" })
        ]);

        card.appendChild(top);
        card.appendChild(launchBtn);
        appsGrid.appendChild(card);
      });
    });

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(appsGrid);
  }

  function renderInstall(panel, ctx) {
    panel.innerHTML = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "ArtCraft Setup & Installation" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Configure environment paths and download standalone ArtCraft creative tools." })
    ]);

    var infoCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-4)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "System PATH Integration" }),
      window.FOSS.dom.el("p", { className: "text-sm text-muted", text: "ArtCraft desktop applications are detected automatically when their executable files are placed in your system PATH or installed in standard application directories." }),
      window.FOSS.dom.el("div", {
        className: "card text-xs font-mono",
        style: { backgroundColor: "var(--bg-raised)", padding: "var(--space-3)", borderRadius: "var(--radius-sm)" },
        text: "winget install ArtCraft.Suite\n# or place executables in %LOCALAPPDATA%\\Programs\\ArtCraft\\"
      })
    ]);

    panel.appendChild(header);
    panel.appendChild(infoCard);
  }

  window.FOSS.router.register({
    id: "artcraft",
    title: "ArtCraft Hub",
    navName: "ArtCraft",
    category: "Visuals",
    icon: "palette",
    tabs: [
      { id: "suite", label: "Creative Suite", render: renderSuite },
      { id: "install", label: "Install & Setup", render: renderInstall }
    ]
  });
})();

