// Keyboard shortcuts manager and global keybindings router.
window.FOSS = window.FOSS || {};

(function () {
  function init() {
    document.addEventListener("keydown", handleKeyDown);
  }

  function handleKeyDown(e) {
    var isCtrl = e.ctrlKey || e.metaKey;

    // Palette open: Ctrl+K or Ctrl+P
    if (isCtrl && (e.key === "k" || e.key === "K" || e.key === "p" || e.key === "P")) {
      e.preventDefault();
      if (window.FOSS.palette) window.FOSS.palette.open();
      return;
    }

    // Fullscreen: F11
    if (e.key === "F11") {
      e.preventDefault();
      window.FOSS.api("toggle_fullscreen", {});
      return;
    }

    // Zoom scale: Ctrl+=, Ctrl+-, Ctrl+0
    if (isCtrl && (e.key === "=" || e.key === "+")) {
      e.preventDefault();
      var sUp = window.FOSS.store.get("ui_scale", 1.0) + 0.1;
      window.FOSS.theme.setScale(sUp);
      return;
    }
    if (isCtrl && e.key === "-") {
      e.preventDefault();
      var sDown = window.FOSS.store.get("ui_scale", 1.0) - 0.1;
      window.FOSS.theme.setScale(sDown);
      return;
    }
    if (isCtrl && e.key === "0") {
      e.preventDefault();
      window.FOSS.theme.setScale(1.0);
      return;
    }

    // Navigation shortcuts: Alt+Home or Alt+H -> Home
    if (e.altKey && (e.key === "Home" || e.key === "h" || e.key === "H")) {
      e.preventDefault();
      window.FOSS.router.open("home");
      return;
    }

    // Settings: Alt+S
    if (e.altKey && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      window.FOSS.router.open("settings");
      return;
    }
  }

  window.FOSS.shortcuts = {
    init: init
  };
})();

