// Theme and UI scale management.
window.FOSS = window.FOSS || {};

(function () {
  var MIN_UI_SCALE = 0.50;
  var MAX_UI_SCALE = 2.50;
  var STEP_UI_SCALE = 0.05;
  var saveScaleTimer = null;

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
    if (themeName === "ut") themeName = "ut_austin";
    document.documentElement.setAttribute("data-theme", themeName);
    if (persist !== false) {
      window.FOSS.store.set("theme", themeName);
    }
  }

  function applyScale(scaleVal) {
    var parsed = parseFloat(scaleVal);
    if (isNaN(parsed)) parsed = 1.0;
    var rounded = Math.round(parsed * 20) / 20;
    var clamped = Math.max(MIN_UI_SCALE, Math.min(MAX_UI_SCALE, rounded));
    document.documentElement.style.setProperty("--ui-scale", String(clamped));
    return clamped;
  }

  function setScale(scaleVal, persist) {
    var clamped = applyScale(scaleVal);
    if (persist !== false) {
      window.FOSS.store.set("ui_scale", clamped);
    }
    updateSettingsUi(clamped);
    return clamped;
  }

  function stepScale(deltaSteps) {
    var current = parseFloat(document.documentElement.style.getPropertyValue("--ui-scale"));
    if (isNaN(current) || current <= 0) current = 1.0;
    var next = Math.round((current + deltaSteps * STEP_UI_SCALE) * 20) / 20;
    var clamped = applyScale(next);

    if (saveScaleTimer) clearTimeout(saveScaleTimer);
    saveScaleTimer = setTimeout(function () {
      window.FOSS.store.set("ui_scale", clamped);
    }, 180);

    updateSettingsUi(clamped);
    return clamped;
  }

  function updateSettingsUi(val) {
    var slider = document.getElementById("settings-scale-slider");
    if (slider) slider.value = String(val);
    var label = document.getElementById("settings-scale-value");
    if (label) label.textContent = Math.round(val * 100) + "%";
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
    applyScale: applyScale,
    stepScale: stepScale,
    applyCustomColors: applyCustomColors,
    MIN_SCALE: MIN_UI_SCALE,
    MAX_SCALE: MAX_UI_SCALE,
    STEP_SCALE: STEP_UI_SCALE
  };
})();
