// Color Palette Studio: Dominant extraction, live 9x9 loupe eyedropper, and WCAG contrast.
window.FOSS = window.FOSS || {};

(function () {
  var CSS_NAMED_COLORS = {
    black: [0, 0, 0], white: [255, 255, 255], red: [255, 0, 0], green: [0, 128, 0],
    blue: [0, 0, 255], yellow: [255, 255, 0], cyan: [0, 255, 255], magenta: [255, 0, 255],
    orange: [255, 165, 0], purple: [128, 0, 128], pink: [255, 192, 203], brown: [165, 42, 42],
    gray: [128, 128, 128], silver: [192, 192, 192], maroon: [128, 0, 0], navy: [0, 0, 128],
    teal: [0, 128, 128], olive: [128, 128, 0], lime: [0, 255, 0], aqua: [0, 255, 255],
    fuchsia: [255, 0, 255], gold: [255, 215, 0], indigo: [75, 0, 130], violet: [238, 130, 238],
    coral: [255, 127, 80], tomato: [255, 99, 71], salmon: [250, 128, 114], beige: [245, 245, 220],
    tan: [210, 180, 140], khaki: [240, 230, 140], azure: [240, 255, 255], aliceblue: [240, 248, 255],
    lavender: [230, 230, 250], mintcream: [245, 255, 250], honeydew: [240, 255, 240], snow: [255, 250, 250]
  };

  function findNearestCssColor(r, g, b) {
    var bestName = "black";
    var bestDist = Infinity;
    var keys = Object.keys(CSS_NAMED_COLORS);
    for (var i = 0; i < keys.length; i++) {
      var name = keys[i];
      var base = CSS_NAMED_COLORS[name];
      var dr = r - base[0];
      var dg = g - base[1];
      var db = b - base[2];
      var dist = dr * dr + dg * dg + db * db;
      if (dist < bestDist) {
        bestDist = dist;
        bestName = name;
      }
    }
    return bestName;
  }

  function rgbToHsl(r, g, b) {
    var rn = r / 255, gn = g / 255, bn = b / 255;
    var max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
    var d = max - min;
    var l = (max + min) / 2;
    var h = 0, s = 0;
    if (d !== 0) {
      s = l < 0.5 ? d / (max + min) : d / (2 - max - min);
      if (max === rn) h = ((gn - bn) / d) % 6;
      else if (max === gn) h = (bn - rn) / d + 2;
      else h = (rn - gn) / d + 4;
      h = Math.round(h * 60);
      if (h < 0) h += 360;
    }
    return [h, Math.round(s * 100), Math.round(l * 100)];
  }

  function parseHex(hex) {
    var clean = (hex || "").replace("#", "").trim();
    if (clean.length === 3) {
      clean = clean[0] + clean[0] + clean[1] + clean[1] + clean[2] + clean[2];
    }
    if (clean.length === 6) {
      return [parseInt(clean.slice(0, 2), 16), parseInt(clean.slice(2, 4), 16), parseInt(clean.slice(4, 6), 16)];
    }
    return [0, 0, 0];
  }

  function calcLuminance(r, g, b) {
    function lum(ch) {
      var v = ch / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
    return 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b);
  }

  function calcContrastRatio(r1, g1, b1, r2, g2, b2) {
    var l1 = calcLuminance(r1, g1, b1);
    var l2 = calcLuminance(r2, g2, b2);
    var lighter = Math.max(l1, l2);
    var darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function wcagGrade(ratio) {
    if (ratio >= 7.0) return "AAA";
    if (ratio >= 4.5) return "AA";
    if (ratio >= 3.0) return "AA Large";
    return "Fail";
  }

  function formatColor(rgbArr, hslArr, fmt) {
    if (fmt === "rgb") return "rgb(" + rgbArr[0] + ", " + rgbArr[1] + ", " + rgbArr[2] + ")";
    if (fmt === "hsl") return "hsl(" + hslArr[0] + ", " + hslArr[1] + "%, " + hslArr[2] + "%)";
    var hexParts = rgbArr.map(function (ch) { return ("0" + ch.toString(16)).slice(-2); });
    return "#" + hexParts.join("").toUpperCase();
  }

  var EXPORT_TYPES = {
    json: { name: "JSON File (*.json)", extensions: ["json"], api: "palette_export_json" },
    css: { name: "CSS Variables (*.css)", extensions: ["css"], api: "palette_export_css" },
    ase: { name: "Adobe Swatch Exchange (*.ase)", extensions: ["ase"], api: "palette_export_ase" },
    png: { name: "PNG Swatch Strip (*.png)", extensions: ["png"], api: "palette_export_strip" },
    gpl: { name: "GIMP Palette (*.gpl)", extensions: ["gpl"], api: "palette_export_gpl" },
    aco: { name: "Adobe Swatch (*.aco)", extensions: ["aco"], api: "palette_export_aco" }
  };
  var applyDefaultsHook = null;

  window.addEventListener("foss:tool-defaults-changed", function (evt) {
    if (evt.detail && evt.detail.toolId === "palette" && applyDefaultsHook) applyDefaultsHook();
  });

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.setProperty("position", "fixed");
    ta.style.setProperty("opacity", "0");
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  function renderPalette(panel, ctx) {
    panel.innerHTML = "";
    var toolDefaults = window.FOSS.toolDefaults.all("palette");
    var copyFormat = String(toolDefaults.copy_format);

    var activeTab = "dominant";
    var currentImagePath = "";
    var currentImageObj = null;
    var extractedSwatches = [];
    var sampledSwatches = [];
    var fgColor = "#000000";
    var bgColor = "#FFFFFF";

    // Status bar & Error banner
    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "palette-status",
      text: "Open an image to extract palettes or sample colors with the mouse."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "palette-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      "data-testid": "palette-result",
      className: "hidden"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "palette-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // --- LEFT COLUMN CONTROLS ---

    // Source Bar
    var fileNameBadge = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted truncate",
      "data-truncate-ok": "true",
      title: "No image loaded",
      text: "No image loaded"
    });

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "palette-open-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {
          title: "Select Image File",
          file_types: ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            currentImagePath = res.paths[0];
            clearError();
            loadImageAndExtract();
          }
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Open Image" })]);
    openBtn.setAttribute("data-testid", "palette-file-picker-browse");

    var multiBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "palette-multi-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Select Multiple Images for Aggregation",
          file_types: ["png", "jpg", "jpeg", "webp"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            aggregateMultipleImages(res.paths);
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("layers", 14), window.FOSS.dom.el("span", { text: "Multi-Image Palette" })]);

    var sourceCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "palette-source-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Image Source" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        openBtn,
        multiBtn
      ]),
      fileNameBadge
    ]);

    // Extraction Controls
    var countInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "palette-count-input",
      "aria-label": "Swatches count",
      title: "Swatches count (2 to 24)",
      min: "2",
      max: "24",
      value: String(toolDefaults.swatch_count)
    });
    countInput.setAttribute("data-testid", "palette-num-colors");

    applyDefaultsHook = function () {
      var fresh = window.FOSS.toolDefaults.all("palette");
      copyFormat = String(fresh.copy_format);
      countInput.value = String(fresh.swatch_count);
      renderActiveSwatches();
    };

    var defaultMethod = String(toolDefaults.extraction_method || "kmeans");
    var methodSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "palette-method-select",
      "aria-label": "Extraction Method",
      title: "Extraction Method"
    }, [
      window.FOSS.dom.el("option", { value: "median-cut", text: "Median-Cut" }),
      window.FOSS.dom.el("option", { value: "kmeans", text: "K-Means Clustering" })
    ]);
    methodSelect.value = defaultMethod;

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "palette-extract-btn",
      type: "button",
      onClick: function () {
        if (!currentImagePath) {
          showError("Select an image file first.");
          return;
        }
        loadImageAndExtract();
      }
    }, [window.FOSS.icons.el("palette", 16), window.FOSS.dom.el("span", { text: "Extract Palette" })]);

    var extractionCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "palette-extraction-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Image Extraction" }),
      window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
        window.FOSS.components.field("Swatches", countInput),
        window.FOSS.components.field("Algorithm", methodSelect)
      ]),
      extractBtn
    ]);

    // Live Eyedropper Magnifier & HUD
    var loupeCanvas = window.FOSS.dom.el("canvas", {
      width: 80,
      height: 80,
      "data-testid": "palette-loupe-canvas",
      style: "width: 5rem; height: 5rem; border-radius: var(--radius-sm); border: 1px solid var(--border); image-rendering: pixelated; flex-shrink: 0;"
    });

    var hudColorSwatch = window.FOSS.dom.el("div", {
      style: "width: 2.25rem; height: 2.25rem; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface-sunken); flex-shrink: 0;"
    });

    var hudHexLabel = window.FOSS.dom.el("span", {
      className: "font-mono font-bold text-sm",
      "data-testid": "palette-hud-hex",
      text: "#------"
    });

    var hudRgbLabel = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "palette-hud-rgb",
      text: "RGB(---, ---, ---)"
    });

    var hudHslLabel = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "palette-hud-hsl",
      text: "HSL(---, --%, --%)"
    });

    var hudNameBadge = window.FOSS.dom.el("span", {
      className: "badge neutral text-xs",
      text: "--"
    });

    var hudPosLabel = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "palette-hud-pos",
      text: "Position: (-, -)"
    });

    var hudContrastLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "palette-contrast-info",
      text: "Contrast: -- vs white, -- vs black"
    });

    var eyedropperHud = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "palette-eyedropper-hud"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Eyedropper Loupe (Hover to Inspect)" }),
      window.FOSS.dom.el("div", { className: "row gap-3 items-center" }, [
        loupeCanvas,
        window.FOSS.dom.el("div", { className: "flex-col gap-1", style: "flex: 1 1 0%; min-width: 0;" }, [
          window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
            hudColorSwatch,
            hudHexLabel,
            hudNameBadge
          ]),
          hudRgbLabel,
          hudHslLabel,
          hudPosLabel
        ])
      ]),
      hudContrastLabel
    ]);

    // WCAG Contrast Checker Card
    var fgInput = window.FOSS.dom.el("input", {
      type: "color",
      value: fgColor,
      className: "input",
      "aria-label": "Foreground Color",
      title: "Foreground Color",
      style: "width: 3rem; height: 2rem; padding: 0; cursor: pointer;"
    });

    var bgInput = window.FOSS.dom.el("input", {
      type: "color",
      value: bgColor,
      className: "input",
      "aria-label": "Background Color",
      title: "Background Color",
      style: "width: 3rem; height: 2rem; padding: 0; cursor: pointer;"
    });

    var contrastRatioDisplay = window.FOSS.dom.el("div", {
      className: "font-mono font-bold text-lg",
      "data-testid": "palette-contrast-ratio",
      text: "21.00 : 1"
    });

    var contrastBadgesRow = window.FOSS.dom.el("div", {
      className: "row gap-1 items-center flex-wrap",
      "data-testid": "palette-contrast-badges"
    });

    function updateContrastCard() {
      var rgb1 = parseHex(fgInput.value);
      var rgb2 = parseHex(bgInput.value);
      var ratio = calcContrastRatio(rgb1[0], rgb1[1], rgb1[2], rgb2[0], rgb2[1], rgb2[2]);
      contrastRatioDisplay.textContent = ratio.toFixed(2) + " : 1";

      contrastBadgesRow.innerHTML = "";
      var normalAA = ratio >= 4.5;
      var normalAAA = ratio >= 7.0;
      var largeAA = ratio >= 3.0;
      var largeAAA = ratio >= 4.5;

      contrastBadgesRow.appendChild(window.FOSS.dom.el("span", {
        className: "badge " + (normalAA ? "success" : "neutral") + " text-xs",
        text: "Normal AA: " + (normalAA ? "Pass" : "Fail")
      }));
      contrastBadgesRow.appendChild(window.FOSS.dom.el("span", {
        className: "badge " + (normalAAA ? "success" : "neutral") + " text-xs",
        text: "Normal AAA: " + (normalAAA ? "Pass" : "Fail")
      }));
      contrastBadgesRow.appendChild(window.FOSS.dom.el("span", {
        className: "badge " + (largeAA ? "success" : "neutral") + " text-xs",
        text: "Large AA: " + (largeAA ? "Pass" : "Fail")
      }));
      contrastBadgesRow.appendChild(window.FOSS.dom.el("span", {
        className: "badge " + (largeAAA ? "success" : "neutral") + " text-xs",
        text: "Large AAA: " + (largeAAA ? "Pass" : "Fail")
      }));
    }

    fgInput.addEventListener("input", updateContrastCard);
    bgInput.addEventListener("input", updateContrastCard);
    updateContrastCard();

    var contrastCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "palette-contrast-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "WCAG Contrast Checker" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
        window.FOSS.dom.el("label", { className: "row gap-1 items-center text-xs font-semibold" }, [
          window.FOSS.dom.el("span", { text: "FG" }),
          fgInput
        ]),
        window.FOSS.dom.el("label", { className: "row gap-1 items-center text-xs font-semibold" }, [
          window.FOSS.dom.el("span", { text: "BG" }),
          bgInput
        ]),
        contrastRatioDisplay
      ]),
      contrastBadgesRow
    ]);

    function generateHarmonies(hex) {
      var rgb = parseHex(hex);
      var hsl = rgbToHsl(rgb[0], rgb[1], rgb[2]);
      var h = hsl[0], s = hsl[1], l = hsl[2];
      function hslToHex(hDeg, sPct, lPct) {
        var sNorm = sPct / 100, lNorm = lPct / 100;
        var c = (1 - Math.abs(2 * lNorm - 1)) * sNorm;
        var x = c * (1 - Math.abs(((hDeg / 60) % 2) - 1));
        var m = lNorm - c / 2;
        var rNorm = 0, gNorm = 0, bNorm = 0;
        if (hDeg < 60) { rNorm = c; gNorm = x; }
        else if (hDeg < 120) { rNorm = x; gNorm = c; }
        else if (hDeg < 180) { gNorm = c; bNorm = x; }
        else if (hDeg < 240) { gNorm = x; bNorm = c; }
        else if (hDeg < 300) { rNorm = x; bNorm = c; }
        else { rNorm = c; bNorm = x; }
        var rInt = Math.round((rNorm + m) * 255);
        var gInt = Math.round((gNorm + m) * 255);
        var bInt = Math.round((bNorm + m) * 255);
        var toHexPart = function (n) { var sVal = Math.max(0, Math.min(255, n)).toString(16); return sVal.length === 1 ? "0" + sVal : sVal; };
        return "#" + toHexPart(rInt) + toHexPart(gInt) + toHexPart(bInt);
      }
      return [
        { label: "Base", hex: hex },
        { label: "Complementary", hex: hslToHex((h + 180) % 360, s, l) },
        { label: "Analogous +", hex: hslToHex((h + 30) % 360, s, l) },
        { label: "Analogous -", hex: hslToHex((h + 330) % 360, s, l) },
        { label: "Triadic 1", hex: hslToHex((h + 120) % 360, s, l) },
        { label: "Triadic 2", hex: hslToHex((h + 240) % 360, s, l) }
      ];
    }

    var harmonizerSwatchesRow = window.FOSS.dom.el("div", {
      className: "row gap-1 items-center flex-wrap",
      "data-testid": "palette-harmonizer-swatches"
    });

    function updateHarmonizerCard(baseHex) {
      harmonizerSwatchesRow.innerHTML = "";
      var list = generateHarmonies(baseHex || fgColor || "#3b82f6");
      list.forEach(function (item) {
        var chip = window.FOSS.dom.el("div", {
          className: "row items-center gap-1 p-1 rounded border border-border cursor-pointer",
          title: item.label + ": " + item.hex + " (Click to copy)",
          style: "font-size: 0.75rem;",
          onClick: function () {
            copyToClipboard(item.hex);
            statusBar.textContent = "Copied " + item.label + " (" + item.hex + ") to clipboard.";
          }
        }, [
          window.FOSS.dom.el("div", {
            style: "width: 1rem; height: 1rem; border-radius: 2px; background-color: " + item.hex + "; border: 1px solid var(--border);"
          }),
          window.FOSS.dom.el("span", { className: "font-mono font-semibold", text: item.hex })
        ]);
        harmonizerSwatchesRow.appendChild(chip);
      });
    }

    var harmonizerCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "palette-harmonizer-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Color Harmonizer" }),
      harmonizerSwatchesRow
    ]);
    updateHarmonizerCard("#3b82f6");

    var sidebar = window.FOSS.dom.el("div", {
      className: "palette-sidebar",
      "data-testid": "palette-sidebar"
    }, [
      sourceCard,
      extractionCard,
      eyedropperHud,
      harmonizerCard,
      contrastCard
    ]);

    // --- RIGHT COLUMN WORKSPACE ---

    // Interactive Stage Canvas
    var previewCanvas = window.FOSS.dom.el("canvas", {
      "data-testid": "palette-preview-canvas",
      style: "max-width: 100%; max-height: 20rem; width: auto; height: auto; display: none; cursor: crosshair; border-radius: var(--radius-md); border: 1px solid var(--border);"
    });

    var emptyPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm p-4 text-center",
      text: "Open an image to preview and sample colors."
    });

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "card card-compact items-center justify-center",
      style: "min-height: 14rem; overflow: hidden; display: flex; background: var(--bg-surface-sunken);"
    }, [
      previewCanvas,
      emptyPlaceholder
    ]);

    // Segmented Tabs & Clear Button
    var sourceTabs = window.FOSS.components.segmented({
      testid: "palette-source-tabs",
      items: [
        { id: "dominant", label: "Dominant Colors (0)" },
        { id: "samples", label: "Eyedropper Samples (0)" }
      ],
      value: "dominant",
      onChange: function (val) {
        switchTab(val);
      }
    });

    var domTabBtn = sourceTabs.el.querySelector('[data-testid="palette-source-tabs-dominant"]');
    if (domTabBtn) domTabBtn.setAttribute("data-testid", "palette-tab-dominant");

    var samTabBtn = sourceTabs.el.querySelector('[data-testid="palette-source-tabs-samples"]');
    if (samTabBtn) samTabBtn.setAttribute("data-testid", "palette-tab-samples");

    var clearSamplesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm hidden",
      "data-testid": "palette-clear-samples-btn",
      type: "button",
      onClick: function () {
        sampledSwatches = [];
        updateTabsLabels();
        renderActiveSwatches();
        redrawImagePins();
        statusBar.textContent = "Cleared sampled colors.";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear Samples" })]);

    // Proportional Color Strip Bar
    var stripBar = window.FOSS.dom.el("div", {
      className: "palette-strip-bar",
      "data-testid": "palette-strip-bar"
    });

    // Unified Export Toolbar
    var copyAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "palette-copy-hex-btn",
      type: "button",
      onClick: function () {
        var swatches = getActiveSwatches();
        if (swatches.length === 0) {
          showError("No swatches to copy.");
          return;
        }
        var colorList = swatches.map(function (s) {
          var rgbArr = s.rgb || parseHex(s.hex);
          return formatColor(rgbArr, s.hsl || rgbToHsl(rgbArr[0], rgbArr[1], rgbArr[2]), copyFormat);
        }).join(", ");
        copyToClipboard(colorList);
        statusBar.textContent = "Copied " + swatches.length + " " + copyFormat.toUpperCase() + " colors to clipboard.";
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy All" })]);
    copyAllBtn.setAttribute("data-testid", "palette-copy-all-btn");

    var defaultExportFormat = String(toolDefaults.export_format || "json");
    var formatSelect = window.FOSS.dom.el("select", {
      className: "input btn-sm",
      "data-testid": "palette-export-format-select",
      "aria-label": "Export Format",
      title: "Export Format",
      style: "min-width: 10rem;"
    }, [
      window.FOSS.dom.el("option", { value: "json", text: "JSON (.json)" }),
      window.FOSS.dom.el("option", { value: "css", text: "CSS Variables (.css)" }),
      window.FOSS.dom.el("option", { value: "ase", text: "Adobe Swatch Exchange (.ase)" }),
      window.FOSS.dom.el("option", { value: "png", text: "PNG Swatch Strip (.png)" }),
      window.FOSS.dom.el("option", { value: "gpl", text: "GIMP Palette (.gpl)" }),
      window.FOSS.dom.el("option", { value: "aco", text: "Adobe Swatch (.aco)" })
    ]);
    formatSelect.value = defaultExportFormat;

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "palette-export-btn",
      type: "button",
      onClick: function () {
        exportPalette(formatSelect.value);
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Export Palette..." })]);
    exportBtn.setAttribute("data-testid", "palette-export-strip-btn");

    var exportToolbar = window.FOSS.dom.el("div", {
      className: "row gap-2 items-center justify-between flex-wrap",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        sourceTabs.el,
        clearSamplesBtn
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        copyAllBtn,
        formatSelect,
        exportBtn
      ])
    ]);

    // Swatch Cards Grid
    var swatchGrid = window.FOSS.dom.el("div", {
      className: "row gap-2 flex-wrap",
      "data-testid": "palette-swatch-list"
    });
    swatchGrid.setAttribute("data-testalias", "palette-dominant-list");

    var swatchContainer = window.FOSS.dom.el("div", {
      className: "palette-swatch-container",
      "data-testid": "palette-swatch-grid",
      style: "width: 100%;"
    }, [swatchGrid]);

    var stagePane = window.FOSS.dom.el("div", {
      className: "palette-stage-pane",
      "data-testid": "palette-stage-pane"
    }, [
      stageWrapper,
      stripBar,
      exportToolbar,
      swatchContainer
    ]);

    // Split Assembly
    var split = window.FOSS.dom.el("div", {
      className: "split resizable palette-workbench",
      "data-testid": "palette-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true, testid: "palette-split-divider" }),
      stagePane
    ]);

    var header = window.FOSS.dom.el("div", { className: "card-header pb-2" }, [
      window.FOSS.dom.el("h2", { className: "card-title text-lg font-bold", text: "Dominant Color Palette" }),
      window.FOSS.dom.el("p", { className: "text-muted text-xs", text: "Extract dominant color swatches, sample live pixel colors, and verify WCAG contrast compliance." })
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);

    renderActiveSwatches();
    renderStripBar();

    // --- LOGIC FUNCTIONS ---

    function getActiveSwatches() {
      return activeTab === "dominant" ? extractedSwatches : sampledSwatches;
    }

    function switchTab(tabId) {
      if (activeTab === tabId && sourceTabs.getValue() === tabId) return;
      activeTab = tabId;
      if (sourceTabs.getValue() !== tabId) {
        sourceTabs.setValue(tabId);
      }
      if (tabId === "dominant") {
        clearSamplesBtn.classList.add("hidden");
        swatchGrid.setAttribute("data-testid", "palette-swatch-list");
      } else {
        clearSamplesBtn.classList.remove("hidden");
        swatchGrid.setAttribute("data-testid", "palette-samples-list");
      }
      renderActiveSwatches();
      renderStripBar();
    }

    function updateTabsLabels() {
      var domCount = extractedSwatches.length;
      var samCount = sampledSwatches.length;
      var domBtn = sourceTabs.el.querySelector('[data-testid="palette-tab-dominant"]') || sourceTabs.el.querySelector('[data-testid="palette-source-tabs-dominant"]');
      if (domBtn) {
        var sp1 = domBtn.querySelector("span");
        if (sp1) sp1.textContent = "Dominant Colors (" + domCount + ")";
      }
      var samBtn = sourceTabs.el.querySelector('[data-testid="palette-tab-samples"]') || sourceTabs.el.querySelector('[data-testid="palette-source-tabs-samples"]');
      if (samBtn) {
        var sp2 = samBtn.querySelector("span");
        if (sp2) sp2.textContent = "Eyedropper Samples (" + samCount + ")";
      }
    }

    function renderStripBar() {
      stripBar.innerHTML = "";
      var swatches = getActiveSwatches();
      if (!swatches || swatches.length === 0) {
        stripBar.style.setProperty("display", "none");
        return;
      }
      stripBar.style.setProperty("display", "flex");

      var hasPercentages = swatches.some(function (s) { return s.percentage && s.percentage > 0; });
      var totalPct = swatches.reduce(function (acc, s) { return acc + (s.percentage || 0); }, 0) || 100;

      swatches.forEach(function (s) {
        var pct = hasPercentages ? (s.percentage / totalPct) * 100 : (100 / swatches.length);
        var seg = window.FOSS.dom.el("div", {
          className: "palette-strip-segment",
          style: "width: " + pct + "%; background-color: " + s.hex + ";",
          title: s.hex + " (" + (s.percentage ? s.percentage + "%" : Math.round(pct) + "%") + ")"
        });
        stripBar.appendChild(seg);
      });
    }

    function createSwatchCard(swatch) {
      var hexCode = swatch.hex || "#000000";
      var rgbArr = swatch.rgb || [0, 0, 0];
      var hslArr = swatch.hsl || rgbToHsl(rgbArr[0], rgbArr[1], rgbArr[2]);
      var colorName = swatch.name || findNearestCssColor(rgbArr[0], rgbArr[1], rgbArr[2]);

      function copyAs(fmt) {
        var text = formatColor(rgbArr, hslArr, fmt);
        copyToClipboard(text);
        statusBar.textContent = "Copied " + text + " to clipboard.";
      }

      var colorBlock = window.FOSS.dom.el("div", {
        className: "palette-swatch-color",
        style: "background-color: " + hexCode + ";",
        title: "Click to copy " + formatColor(rgbArr, hslArr, copyFormat),
        onClick: function () { copyAs(copyFormat); }
      });

      var row1 = window.FOSS.dom.el("div", { className: "row justify-between items-center" }, [
        window.FOSS.dom.el("span", { className: "font-mono font-bold text-sm", text: hexCode }),
        window.FOSS.dom.el("span", { className: "badge neutral text-xs", text: colorName }),
        swatch.percentage != null && swatch.percentage > 0
          ? window.FOSS.dom.el("span", { className: "badge success text-xs", text: swatch.percentage + "%" })
          : window.FOSS.dom.el("span")
      ]);

      var row2 = window.FOSS.dom.el("div", { className: "flex-col gap-0 text-xs text-muted font-mono" }, [
        window.FOSS.dom.el("span", { text: formatColor(rgbArr, hslArr, "rgb") }),
        window.FOSS.dom.el("span", { text: formatColor(rgbArr, hslArr, "hsl") })
      ]);

      function copyButton(fmt) {
        return window.FOSS.dom.el("button", {
          className: "btn btn-sm row gap-1 items-center " + (fmt === copyFormat ? "btn-secondary" : "btn-ghost"),
          "data-dense": "true",
          "data-testid": "palette-copy-" + fmt + "-btn",
          title: { hex: "Copy HEX", rgb: "Copy RGB", hsl: "Copy HSL" }[fmt],
          onClick: function () { copyAs(fmt); }
        }, [
          window.FOSS.icons.el("copy", 14),
          window.FOSS.dom.el("span", { text: fmt.toUpperCase() })
        ]);
      }

      var setFgBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-dense": "true",
        text: "Set FG",
        title: "Set Contrast Checker Foreground",
        onClick: function () {
          fgInput.value = hexCode;
          updateContrastCard();
          updateHarmonizerCard(hexCode);
          statusBar.textContent = "Foreground set to " + hexCode;
        }
      });

      var setBgBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-dense": "true",
        text: "Set BG",
        title: "Set Contrast Checker Background",
        onClick: function () {
          bgInput.value = hexCode;
          updateContrastCard();
          statusBar.textContent = "Background set to " + hexCode;
        }
      });

      var row3 = window.FOSS.dom.el("div", { className: "row gap-1 items-center flex-wrap" }, [
        copyButton("hex"),
        copyButton("rgb"),
        copyButton("hsl"),
        setFgBtn,
        setBgBtn
      ]);

      function contrastBadge(label, ratio, testid) {
        var level = ratio >= 4.5 ? "success" : (ratio >= 3.0 ? "warning" : "danger");
        return window.FOSS.dom.el("span", {
          className: "badge " + level + " text-xs",
          "data-testid": testid,
          title: "WCAG contrast " + label.toLowerCase() + ": " + ratio.toFixed(2) + ":1 (" + wcagGrade(ratio) + ")",
          text: label + " " + ratio.toFixed(2) + ":1 " + wcagGrade(ratio)
        });
      }

      var contrastWhite = calcContrastRatio(rgbArr[0], rgbArr[1], rgbArr[2], 255, 255, 255);
      var contrastBlack = calcContrastRatio(rgbArr[0], rgbArr[1], rgbArr[2], 0, 0, 0);

      var accessibilityRow = window.FOSS.dom.el("div", {
        className: "palette-swatch-accessibility row gap-1 items-center flex-wrap text-muted",
        "data-testid": "palette-swatch-accessibility"
      }, [
        contrastBadge("White", contrastWhite, "palette-contrast-white"),
        contrastBadge("Black", contrastBlack, "palette-contrast-black")
      ]);

      return window.FOSS.dom.el("div", {
        className: "palette-swatch-card",
        "data-testid": "palette-swatch-card"
      }, [
        colorBlock,
        row1,
        row2,
        row3,
        accessibilityRow
      ]);
    }

    function renderActiveSwatches() {
      swatchGrid.innerHTML = "";
      var swatches = getActiveSwatches();
      if (swatches.length === 0) {
        swatchGrid.innerHTML = '<div class="text-sm text-muted p-4 text-center font-mono">No palette extracted yet. Open an image above.</div>';
        return;
      }
      swatches.forEach(function (s) {
        swatchGrid.appendChild(createSwatchCard(s));
      });
    }

    function redrawImagePins() {
      if (!currentImageObj) return;
      var ctx2d = previewCanvas.getContext("2d");
      ctx2d.drawImage(currentImageObj, 0, 0);

      // Draw numbered pin markers on sampled coordinates
      sampledSwatches.forEach(function (sw, idx) {
        if (sw.pin) {
          var px = sw.pin[0], py = sw.pin[1];
          ctx2d.beginPath();
          ctx2d.arc(px, py, 6, 0, Math.PI * 2);
          ctx2d.fillStyle = sw.hex;
          ctx2d.fill();
          ctx2d.lineWidth = 2;
          ctx2d.strokeStyle = "#FFFFFF";
          ctx2d.stroke();
          ctx2d.fillStyle = "#000000";
          ctx2d.font = "bold 9px sans-serif";
          ctx2d.textAlign = "center";
          ctx2d.textBaseline = "middle";
          ctx2d.fillText(String(idx + 1), px, py - 10);
        }
      });
    }

    function drawImageToCanvas(dataUrl) {
      var img = new Image();
      img.onload = function () {
        currentImageObj = img;
        previewCanvas.width = img.width;
        previewCanvas.height = img.height;
        redrawImagePins();
        previewCanvas.style.setProperty("display", "block");
        emptyPlaceholder.style.setProperty("display", "none");
        stageWrapper.classList.add("checkerboard-bg");
        fileNameBadge.textContent = currentImagePath.split(/[/\\]/).pop() + " (" + img.width + "x" + img.height + ")";
        fileNameBadge.title = fileNameBadge.textContent;
      };
      img.src = dataUrl;
    }

    // 9x9 Pixel Loupe Renderer
    function updateLoupe(cx, cy) {
      if (!currentImageObj || !previewCanvas.width) return;
      var ctx2d = previewCanvas.getContext("2d");
      var lCtx = loupeCanvas.getContext("2d");
      lCtx.clearRect(0, 0, loupeCanvas.width, loupeCanvas.height);

      var half = 4; // 9x9 grid: -4 to +4
      var pixelSize = loupeCanvas.width / 9;

      for (var dy = -half; dy <= half; dy++) {
        for (var dx = -half; dx <= half; dx++) {
          var sx = cx + dx;
          var sy = cy + dy;
          if (sx >= 0 && sx < previewCanvas.width && sy >= 0 && sy < previewCanvas.height) {
            var pData = ctx2d.getImageData(sx, sy, 1, 1).data;
            lCtx.fillStyle = "rgb(" + pData[0] + "," + pData[1] + "," + pData[2] + ")";
          } else {
            lCtx.fillStyle = "#222222";
          }
          lCtx.fillRect((dx + half) * pixelSize, (dy + half) * pixelSize, pixelSize, pixelSize);
        }
      }

      // Draw center crosshair over (4, 4)
      lCtx.strokeStyle = "#FFFFFF";
      lCtx.lineWidth = 1.5;
      lCtx.strokeRect(half * pixelSize, half * pixelSize, pixelSize, pixelSize);
    }

    // Canvas Mouse Interactions
    previewCanvas.addEventListener("mousemove", function (e) {
      if (!previewCanvas.width || !previewCanvas.height) return;
      var rect = previewCanvas.getBoundingClientRect();
      var scaleX = previewCanvas.width / rect.width;
      var scaleY = previewCanvas.height / rect.height;
      var x = Math.floor((e.clientX - rect.left) * scaleX);
      var y = Math.floor((e.clientY - rect.top) * scaleY);
      x = Math.max(0, Math.min(previewCanvas.width - 1, x));
      y = Math.max(0, Math.min(previewCanvas.height - 1, y));

      var ctx2d = previewCanvas.getContext("2d");
      var px = ctx2d.getImageData(x, y, 1, 1).data;
      var r = px[0], g = px[1], b = px[2];
      var hexCode = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
      var colorName = findNearestCssColor(r, g, b);
      var hsl = rgbToHsl(r, g, b);

      var cWhite = calcContrastRatio(r, g, b, 255, 255, 255).toFixed(2);
      var cBlack = calcContrastRatio(r, g, b, 0, 0, 0).toFixed(2);

      hudColorSwatch.style.setProperty("background", hexCode);
      hudHexLabel.textContent = hexCode;
      hudNameBadge.textContent = colorName;
      hudRgbLabel.textContent = "RGB(" + r + ", " + g + ", " + b + ")";
      hudHslLabel.textContent = "HSL(" + hsl[0] + ", " + hsl[1] + "%, " + hsl[2] + "%)";
      hudPosLabel.textContent = "Position: (" + x + ", " + y + ")";
      hudContrastLabel.textContent = "Contrast: " + cWhite + ":1 vs white, " + cBlack + ":1 vs black";

      updateLoupe(x, y);
    });

    previewCanvas.addEventListener("click", function (e) {
      if (!previewCanvas.width || !previewCanvas.height) return;
      var rect = previewCanvas.getBoundingClientRect();
      var scaleX = previewCanvas.width / rect.width;
      var scaleY = previewCanvas.height / rect.height;
      var x = Math.floor((e.clientX - rect.left) * scaleX);
      var y = Math.floor((e.clientY - rect.top) * scaleY);
      x = Math.max(0, Math.min(previewCanvas.width - 1, x));
      y = Math.max(0, Math.min(previewCanvas.height - 1, y));

      var ctx2d = previewCanvas.getContext("2d");
      var px = ctx2d.getImageData(x, y, 1, 1).data;
      var r = px[0], g = px[1], b = px[2];
      var hexCode = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
      var colorName = findNearestCssColor(r, g, b);
      var hsl = rgbToHsl(r, g, b);

      var newSwatch = {
        hex: hexCode,
        rgb: [r, g, b],
        hsl: hsl,
        name: colorName,
        percentage: 0.0,
        pin: [x, y]
      };

      sampledSwatches.unshift(newSwatch);
      updateTabsLabels();
      redrawImagePins();
      if (activeTab === "samples") {
        renderActiveSwatches();
        renderStripBar();
      }
      var sampledText = formatColor([r, g, b], hsl, copyFormat);
      copyToClipboard(sampledText);
      statusBar.textContent = "Sampled pixel (" + x + ", " + y + "): " + sampledText + " (" + colorName + ") copied to clipboard.";
    });

    function loadImageAndExtract() {
      clearError();
      statusBar.textContent = "Extracting color palette...";
      var nColors = parseInt(countInput.value, 10) || 8;
      var method = methodSelect.value || "median-cut";

      window.FOSS.api("palette_extract", {
        image_path: currentImagePath,
        num_colors: nColors,
        method: method
      }).then(function (res) {
        if (!res || !res.palette) {
          showError("Failed to extract color palette.");
          return;
        }
        extractedSwatches = res.palette;
        updateTabsLabels();
        renderActiveSwatches();
        renderStripBar();
        if (res.data_url) {
          drawImageToCanvas(res.data_url);
        }
        statusBar.textContent = "Extracted " + extractedSwatches.length + " dominant colors.";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function aggregateMultipleImages(paths) {
      clearError();
      statusBar.textContent = "Aggregating palettes across " + paths.length + " images...";
      var nColors = parseInt(countInput.value, 10) || 8;
      var method = methodSelect.value || "median-cut";

      window.FOSS.api("palette_aggregate", {
        image_paths: paths,
        num_colors: nColors,
        method: method
      }).then(function (res) {
        if (!res || !res.palette) {
          showError("Failed to aggregate color palettes.");
          return;
        }
        extractedSwatches = res.palette;
        updateTabsLabels();
        renderActiveSwatches();
        renderStripBar();
        statusBar.textContent = "Aggregated " + extractedSwatches.length + " colors from " + paths.length + " images.";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function exportPalette(preferredFormat) {
      clearError();
      var swatchesToExport = getActiveSwatches();
      if (swatchesToExport.length === 0) {
        showError("No colors to export. Extract or sample colors first.");
        return;
      }
      var colorList = swatchesToExport.map(function (s) { return s.hex; });
      var order = [preferredFormat].concat(Object.keys(EXPORT_TYPES).filter(function (key) { return key !== preferredFormat; }));

      window.FOSS.api("select_save_path", {
        title: "Export Palette",
        default_name: "palette",
        file_types: order.map(function (key) {
          return { name: EXPORT_TYPES[key].name, extensions: EXPORT_TYPES[key].extensions };
        })
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        var chosenExt = outPath.split(".").pop().toLowerCase();
        var chosenFormat = EXPORT_TYPES[chosenExt] ? chosenExt : preferredFormat;
        window.FOSS.api(EXPORT_TYPES[chosenFormat].api, {
          colors: colorList,
          output_path: outPath
        }).then(function (saveRes) {
          var savedPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(savedPath, "Palette Exported (" + chosenFormat.toUpperCase() + ")");
          statusBar.textContent = "Exported to " + savedPath;
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }
  }

  window.FOSS.router.register({
    id: "palette",
    title: "Color Palette Studio",
    navName: "Palette",
    category: "Visuals",
    icon: "palette",
    workbench: true,
    defaults: [
      { key: "swatch_count", label: "Default swatch count", type: "number", min: 2, max: 24, step: 1, default: 6 },
      { key: "copy_format", label: "Primary copy format", type: "select", options: ["hex", "rgb", "hsl"], default: "hex" },
      { key: "extraction_method", label: "Default extraction algorithm", type: "select", options: [
        { value: "kmeans", label: "K-Means Clustering" },
        { value: "median-cut", label: "Median-Cut" }
      ], default: "kmeans" },
      { key: "export_format", label: "Default palette export format", type: "select", options: ["json", "css", "ase", "png", "gpl", "aco"], default: "json" }
    ],
    onFiles: function (files) {
      if (files && files.length > 0) {
        window.FOSS.router.open("palette", "main");
      }
    },
    tabs: [
      { id: "main", label: "Dominant Color Palette", render: renderPalette }
    ]
  });
})();
