// Theme and UI scale management.
window.FOSS = window.FOSS || {};

(function () {
  function init() {
    var theme = window.FOSS.store.get("theme", "dark");
    var scale = window.FOSS.store.get("ui_scale", 1.0);
    setTheme(theme, false);
    setScale(scale, false);

    var customColors = window.FOSS.store.get("custom_colors", {});
    if (customColors && typeof customColors === "object") {
      applyCustomColors(customColors, false);
    }
  }

  function setTheme(themeName, persist) {
    document.documentElement.setAttribute("data-theme", themeName);
    if (persist !== false) {
      window.FOSS.store.set("theme", themeName);
    }
  }

  function setScale(scaleVal, persist) {
    var clamped = Math.max(0.85, Math.min(1.5, parseFloat(scaleVal) || 1.0));
    document.documentElement.style.setProperty("--ui-scale", String(clamped));
    if (persist !== false) {
      window.FOSS.store.set("ui_scale", clamped);
    }
  }

  function applyCustomColors(colorsMap, persist) {
    if (!colorsMap) return;
    for (var k in colorsMap) {
      if (Object.prototype.hasOwnProperty.call(colorsMap, k)) {
        document.documentElement.style.setProperty(k, colorsMap[k]);
      }
    }
    if (persist !== false) {
      window.FOSS.store.set("custom_colors", colorsMap);
    }
  }

  window.FOSS.theme = {
    init: init,
    setTheme: setTheme,
    setScale: setScale,
    applyCustomColors: applyCustomColors
  };
})();

