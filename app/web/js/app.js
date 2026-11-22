// Main application bootstrapper and testing harness hooks.
window.FOSS = window.FOSS || {};

(function () {
  function boot() {
    window.FOSS.theme.init();
    window.FOSS.shortcuts.init();
    window.FOSS.dropzone.init();
    window.FOSS.tooltips.init();
    if (window.FOSS.resizer) window.FOSS.resizer.init();

    // Check collapsed sidebar setting
    if (window.FOSS.store.get("sidebar_collapsed", false)) {
      var appEl = document.querySelector(".app");
      if (appEl) appEl.classList.add("sidebar-rail");
    }

    // Initial route: render configured startup workspace immediately on DOM ready
    var initialView = window.FOSS.store.get("startup_view", "home") || "home";
    window.FOSS.router.open(initialView);

    // Asynchronously synchronize settings from Python backend
    window.FOSS.store.loadAll().then(function () {
      window.FOSS.theme.init();
      var rootEl = document.querySelector(".app");
      if (rootEl) {
        rootEl.classList.toggle("sidebar-rail", Boolean(window.FOSS.store.get("sidebar_collapsed", false)));
      }
      var loadedStartup = window.FOSS.store.get("startup_view", "home") || "home";
      if (loadedStartup !== "home" && window.FOSS.router.getActiveView() === "home") {
        window.FOSS.router.open(loadedStartup);
      }
      window.FOSS.ready = true;
    }).catch(function () {
      window.FOSS.ready = true;
    });
  }

  function listStates() {
    var states = [
      { view: "home", state: "default" },
      { view: "home", state: "empty-search" },
      { view: "palette", state: "open" },
      { view: "settings", state: "appearance" },
      { view: "settings", state: "home" },
      { view: "settings", state: "keybindings" },
      { view: "settings", state: "shell" },
      { view: "settings", state: "privacy" },
      { view: "settings", state: "about" },
      { view: "modal", state: "confirm" },
      { view: "toast", state: "stack" },
      { view: "sidebar", state: "rail" }
    ];

    var tools = window.FOSS.router.getRegisteredTools();
    tools.forEach(function (t) {
      var tabs = t.tabs || [];
      if (tabs.length === 0) {
        states.push({ view: t.id, state: "default" });
      } else {
        tabs.forEach(function (tb) {
          states.push({ view: t.id, state: tb.id });
        });
      }
    });

    return states;
  }

  function openState(view, state) {
    if (view === "home") {
      window.FOSS.router.open("home");
      if (state === "empty-search") {
        var input = document.querySelector(".home-search-input");
        if (input) {
          input.value = "xyznonexistentquery";
          input.dispatchEvent(new Event("input"));
        }
      }
    } else if (view === "palette") {
      window.FOSS.palette.open();
    } else if (view === "settings") {
      window.FOSS.router.open("settings", state);
    } else if (view === "modal") {
      window.FOSS.confirm({
        title: "Test Confirmation",
        message: "Verifying modal dialog presentation.",
        persistent: true
      });
    } else if (view === "toast") {
      window.FOSS.toast.show("Sample info toast notification", "info");
      window.FOSS.toast.show("Sample success message", "success");
      window.FOSS.toast.show("Sample error message", "error");
    } else if (view === "sidebar" && state === "rail") {
      var appEl = document.querySelector(".app");
      if (appEl) appEl.classList.add("sidebar-rail");
    } else {
      window.FOSS.router.open(view, state);
    }
  }

  function selfTest() {
    var findings = typeof window.__audit === "function" ? window.__audit() : [];
    var missingApi = [];

    var requiredApis = [
      "ping", "get_apps", "get_tooltips", "get_setting", "set_setting",
      "get_settings_all", "reset_settings", "reset_settings_defaults",
      "select_file", "select_files", "select_folder", "select_save_path",
      "read_text_file", "write_text_file", "open_path", "open_folder",
      "copy_to_clipboard", "toggle_fullscreen", "route_file", "get_recents",
      "clear_recents", "get_version", "job_start", "job_poll", "job_cancel"
    ];

    if (window.pywebview && window.pywebview.api) {
      requiredApis.forEach(function (name) {
        if (typeof window.pywebview.api[name] !== "function") {
          missingApi.push(name);
        }
      });
    }

    return {
      ready: Boolean(window.FOSS.ready),
      findings: findings,
      missing_api: missingApi
    };
  }

  function openPaths(paths, mode) {
    if (paths && paths.length > 0) {
      if (mode === "ocr") {
        window.FOSS.router.open("ocr").then(function () {
          var tool = window.FOSS.router.getTool ? window.FOSS.router.getTool("ocr") : null;
          if (tool && tool.onFiles) {
            tool.onFiles(paths, window.FOSS.router.createContext("ocr"));
          }
        });
      } else {
        window.FOSS.router.routeFiles(paths);
      }
    }
  }

  window.FOSS.ready = false;
  window.FOSS.listStates = listStates;
  window.FOSS.openState = openState;
  window.FOSS.selfTest = selfTest;
  window.FOSS.openPaths = openPaths;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
