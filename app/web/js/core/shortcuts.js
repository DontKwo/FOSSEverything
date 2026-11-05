// Keyboard shortcuts manager and global keybindings router.
window.FOSS = window.FOSS || {};

(function () {
  var DEFAULT_KEYMAP = {
    "open_palette": { label: "Command Palette", key: "k", ctrl: true, alt: false, shift: false, display: "Ctrl+K" },
    "go_home": { label: "Navigate to Home", key: "Home", ctrl: false, alt: true, shift: false, display: "Alt+Home" },
    "open_settings": { label: "Open Settings", key: "s", ctrl: false, alt: true, shift: false, display: "Alt+S" },
    "toggle_fullscreen": { label: "Toggle Fullscreen", key: "F11", ctrl: false, alt: false, shift: false, display: "F11" },
    "zoom_in": { label: "Zoom In", key: "=", ctrl: true, alt: false, shift: false, display: "Ctrl+=" },
    "zoom_out": { label: "Zoom Out", key: "-", ctrl: true, alt: false, shift: false, display: "Ctrl+-" },
    "zoom_reset": { label: "Reset Zoom", key: "0", ctrl: true, alt: false, shift: false, display: "Ctrl+0" }
  };

  function getKeymap() {
    return window.FOSS.store.get("custom_keybindings", DEFAULT_KEYMAP);
  }

  function dispatchShortcutAction(action) {
    if (action === "open_palette") {
      if (window.FOSS.palette) window.FOSS.palette.open();
    } else if (action === "go_home") {
      if (window.FOSS.router) window.FOSS.router.open("home");
    } else if (action === "open_settings") {
      if (window.FOSS.router) window.FOSS.router.open("settings");
    } else if (action === "toggle_fullscreen") {
      if (window.FOSS.api) window.FOSS.api("toggle_fullscreen", {});
    } else if (action === "zoom_in") {
      if (window.FOSS.theme && window.FOSS.theme.stepScale) {
        window.FOSS.theme.stepScale(1);
      }
    } else if (action === "zoom_out") {
      if (window.FOSS.theme && window.FOSS.theme.stepScale) {
        window.FOSS.theme.stepScale(-1);
      }
    } else if (action === "zoom_reset") {
      if (window.FOSS.theme && window.FOSS.theme.setScale) {
        window.FOSS.theme.setScale(1.0);
      }
    }
  }

  function handleKeyDown(e) {
    var map = getKeymap();
    for (var action in map) {
      var b = map[action];
      if (b && b.key &&
          b.key.toLowerCase() === e.key.toLowerCase() &&
          !!b.ctrl === (e.ctrlKey || e.metaKey) &&
          !!b.alt === e.altKey &&
          !!b.shift === e.shiftKey) {
        e.preventDefault();
        dispatchShortcutAction(action);
        return;
      }
    }
  }

  function init() {
    document.addEventListener("keydown", handleKeyDown);

    var wheelRAF = null;
    window.addEventListener("wheel", function (e) {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        e.stopPropagation();
        if (e.deltaY !== 0 && window.FOSS.theme && window.FOSS.theme.stepScale) {
          if (wheelRAF) cancelAnimationFrame(wheelRAF);
          wheelRAF = requestAnimationFrame(function () {
            window.FOSS.theme.stepScale(e.deltaY < 0 ? 1 : -1);
            wheelRAF = null;
          });
        }
      }
    }, { passive: false });
  }

  window.FOSS.shortcuts = {
    init: init,
    DEFAULT_KEYMAP: DEFAULT_KEYMAP,
    getKeymap: getKeymap,
    dispatchShortcutAction: dispatchShortcutAction
  };
})();
