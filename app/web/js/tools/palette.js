// Color Palette Extractor and Eyedropper workspace.
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

  function calcContrastRatio(r, g, b, r2, g2, b2) {
    function lum(ch) {
      var v = ch / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
    var l1 = 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b);
    var l2 = 0.2126 * lum(r2) + 0.7152 * lum(g2) + 0.0722 * lum(b2);
    var lighter = Math.max(l1, l2);
    var darker = Math.min(l1, l2);
    return ((lighter + 0.05) / (darker + 0.05)).toFixed(2);
  }

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

    var activeTab = "dominant";
    var currentImagePath = "";
    var currentImageDataUrl = "";
    var extractedSwatches = [];
    var sampledSwatches = [];

    // Header
    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", {
        className: "card-title",
        text: "Color Palette Extractor & Eyedropper"
      }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Extract dominant colors automatically or click anywhere on the image with the eyedropper cursor."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "palette-status",
      text: "Open an image to extract palettes or sample colors with the mouse."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger",
      "data-testid": "palette-error-banner",
      hidden: true
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", {
      "data-testid": "palette-result",
      hidden: true
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "palette-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Top Card: File selection and Extraction controls
    var controlCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var pickerField = window.FOSS.components.filePicker({
      testid: "palette-file-picker",
      title: "Select image file to extract colors...",
      fileTypes: ["png", "jpg", "jpeg", "webp", "bmp", "gif"],
      onSelect: function (val) {
        currentImagePath = val;
        clearError();
        if (val) {
          loadImageAndExtract();
        }
      },
      onClear: function () {
        currentImagePath = "";
        extractedSwatches = [];
        sampledSwatches = [];
        renderDominantSwatches();
        updateSamplesUI();
      }
    });

    var numColorsInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "palette-num-colors",
      "aria-label": "Colors to extract",
      title: "Colors to extract",
      min: "2",
      max: "32",
      value: "8",
      style: { width: "80px" }
    });

    var numColorsField = window.FOSS.components.field(
      "Colors to Extract",
      numColorsInput
    );

    var methodSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "palette-method-select",
      "aria-label": "Extraction Method",
      title: "Extraction Method",
      style: { minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "median-cut", text: "Median-Cut" }),
      window.FOSS.dom.el("option", { value: "kmeans", text: "K-Means Clustering" })
    ]);

    var methodField = window.FOSS.components.field(
      "Extraction Method",
      methodSelect
    );

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "palette-extract-btn",
      "aria-label": "Extract dominant colors",
      title: "Extract dominant colors",
      onClick: function () {
        if (!currentImagePath) {
          showError("Select an image file first.");
          return;
        }
        loadImageAndExtract();
      }
    }, [
      window.FOSS.icons.el("palette", 16),
      window.FOSS.dom.el("span", { text: "Extract Dominant Colors" })
    ]);

    var multiAggregateBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "palette-multi-aggregate-btn",
      "aria-label": "Multi-image aggregation",
      title: "Multi-image aggregation",
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
    }, [
      window.FOSS.icons.el("layers", 16),
      window.FOSS.dom.el("span", { text: "Multi-image aggregation" })
    ]);

    var controlsRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-3)",
        width: "100%"
      }
    }, [
      numColorsField,
      methodField,
      extractBtn,
      multiAggregateBtn
    ]);

    controlCard.appendChild(pickerField.el);
    controlCard.appendChild(controlsRow);

    // Main workspace: Left side Eyedropper Canvas & HUD, Right side Swatch Tabs
    var workspaceCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });

    // Group: eyedropper tool (hover / click to sample)
    var eyedropperGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { flex: "1 1 260px", minWidth: "0", maxWidth: "100%", width: "100%" }
    });

    var eyedropperHeader = window.FOSS.dom.el("h3", {
      className: "card-title text-base",
      text: "Eyedropper Tool (Hover / Click to sample)"
    });

    var canvasContainer = window.FOSS.dom.el("div", {
      style: {
        position: "relative",
        background: "var(--color-bg-base)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        minHeight: "220px",
        width: "100%",
        maxWidth: "100%",
        minWidth: "0",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden"
      }
    });

    var previewCanvas = window.FOSS.dom.el("canvas", {
      "data-testid": "palette-preview-canvas",
      style: {
        display: "none",
        cursor: "crosshair",
        width: "100%",
        maxWidth: "100%",
        height: "auto",
        maxHeight: "360px",
        objectFit: "contain"
      }
    });

    var emptyPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm p-4 text-center",
      text: "Open an image to preview and sample colors."
    });

    canvasContainer.appendChild(previewCanvas);
    canvasContainer.appendChild(emptyPlaceholder);

    // Live HUD Box
    var hudBox = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "palette-hud-box",
      style: {
        background: "var(--color-bg-muted)",
        border: "1px solid var(--color-border)",
        padding: "var(--space-3)"
      }
    });

    var hudColorSwatch = window.FOSS.dom.el("div", {
      style: {
        width: "36px",
        height: "36px",
        borderRadius: "var(--radius-sm)",
        border: "2px solid var(--color-border)",
        background: "var(--color-bg-muted)",
        flexShrink: "0"
      }
    });

    var hudHexLabel = window.FOSS.dom.el("div", {
      className: "font-mono font-bold text-sm",
      "data-testid": "palette-hud-hex",
      text: "#------"
    });

    var hudRgbLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "palette-hud-rgb",
      text: "rgb(---, ---, ---)"
    });

    var hudPosLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "palette-hud-pos",
      text: "position: (-, -)"
    });

    var hudContrastLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "palette-contrast-info",
      text: "contrast: - vs white, - vs black"
    });

    var hudInfoCol = window.FOSS.dom.el("div", { className: "flex-col gap-1 flex-1" }, [
      hudHexLabel,
      hudRgbLabel,
      hudPosLabel,
      hudContrastLabel
    ]);

    var hudRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-3)" }
    }, [
      hudColorSwatch,
      hudInfoCol
    ]);

    hudBox.appendChild(hudRow);
    eyedropperGroup.appendChild(eyedropperHeader);
    eyedropperGroup.appendChild(canvasContainer);
    eyedropperGroup.appendChild(hudBox);

    // Right Column: Palette Tabs (Dominant Colors & Eyedropper Samples)
    var tabsGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { flex: "1 1 260px", minWidth: "0", maxWidth: "100%", width: "100%" }
    });

    var tabDominantBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "palette-tab-dominant",
      "aria-label": "Dominant Colors",
      title: "Dominant Colors",
      onClick: function () {
        switchTab("dominant");
      }
    }, [
      window.FOSS.icons.el("palette", 16),
      window.FOSS.dom.el("span", { text: "Dominant Colors" })
    ]);

    var tabSamplesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "palette-tab-samples",
      "aria-label": "Eyedropper Samples (0)",
      title: "Eyedropper Samples (0)",
      onClick: function () {
        switchTab("samples");
      }
    }, [
      window.FOSS.icons.el("eyedropper", 16),
      window.FOSS.dom.el("span", { text: "Eyedropper Samples (0)" })
    ]);

    var tabNav = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)", borderBottom: "1px solid var(--color-border)", paddingBottom: "var(--space-2)" }
    }, [
      tabDominantBtn,
      tabSamplesBtn
    ]);

    // Dominant Pane
    var dominantPane = window.FOSS.dom.el("div", { className: "flex-col gap-3" });

    // Toolbar actions for Dominant
    var copyAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-copy-all-btn",
      "aria-label": "copy hex",
      title: "copy hex",
      onClick: function () {
        if (extractedSwatches.length === 0) {
          showError("No swatches to copy.");
          return;
        }
        var hexList = extractedSwatches.map(function (s) { return s.hex; }).join(", ");
        copyToClipboard(hexList);
        statusBar.textContent = "Copied " + extractedSwatches.length + " hex codes to clipboard.";
      }
    }, [
      window.FOSS.icons.el("copy", 14),
      window.FOSS.dom.el("span", { text: "Copy Hex" })
    ]);

    var exportStripBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-export-strip-btn",
      "aria-label": "Export visual strip image",
      title: "Export visual strip image",
      onClick: function () {
        exportPalette("strip");
      }
    }, [
      window.FOSS.icons.el("image", 14),
      window.FOSS.dom.el("span", { text: "Export Strip" })
    ]);

    var exportGplBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-export-gpl-btn",
      "aria-label": "Export GIMP Palette (.gpl)",
      title: "Export GIMP Palette (.gpl)",
      onClick: function () {
        exportPalette("gpl");
      }
    }, [
      window.FOSS.icons.el("file", 14),
      window.FOSS.dom.el("span", { text: "Export GPL" })
    ]);

    var exportCssBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-export-css-btn",
      "aria-label": "Export CSS custom properties",
      title: "Export CSS custom properties",
      onClick: function () {
        exportPalette("css");
      }
    }, [
      window.FOSS.icons.el("code", 14),
      window.FOSS.dom.el("span", { text: "Export CSS" })
    ]);

    var exportJsonBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-export-json-btn",
      "aria-label": "Export JSON palette",
      title: "Export JSON palette",
      onClick: function () {
        exportPalette("json");
      }
    }, [
      window.FOSS.icons.el("file-text", 14),
      window.FOSS.dom.el("span", { text: "Export JSON" })
    ]);

    var exportAcoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-export-aco-btn",
      "aria-label": "Export Adobe Color Swatch (.aco)",
      title: "Export Adobe Color Swatch (.aco)",
      onClick: function () {
        exportPalette("aco");
      }
    }, [
      window.FOSS.icons.el("palette", 14),
      window.FOSS.dom.el("span", { text: "Export ACO" })
    ]);

    var dominantActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-2)",
        width: "100%"
      }
    }, [
      copyAllBtn,
      exportStripBtn,
      exportGplBtn,
      exportCssBtn,
      exportJsonBtn,
      exportAcoBtn
    ]);

    var swatchList = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 scroll-y",
      "data-testid": "palette-swatch-list",
      style: { maxHeight: "420px", paddingRight: "var(--space-1)" }
    });
    swatchList.innerHTML = '<div class="text-sm text-muted p-4 text-center">No palette extracted yet. Open an image above.</div>';

    dominantPane.appendChild(dominantActionsRow);
    dominantPane.appendChild(swatchList);

    // Samples Pane
    var samplesPane = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      hidden: true
    });

    var clearSamplesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "palette-clear-samples-btn",
      "aria-label": "clear sampled colors",
      title: "clear sampled colors",
      onClick: function () {
        sampledSwatches = [];
        updateSamplesUI();
        statusBar.textContent = "Cleared sampled colors.";
      }
    }, [
      window.FOSS.icons.el("trash-2", 14),
      window.FOSS.dom.el("span", { text: "Clear Sampled Colors" })
    ]);

    var samplesActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)" }
    }, [
      clearSamplesBtn
    ]);

    var samplesList = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 scroll-y",
      "data-testid": "palette-samples-list",
      style: { maxHeight: "420px", paddingRight: "var(--space-1)" }
    });
    samplesList.innerHTML = '<div class="text-sm text-muted p-4 text-center">Click on pixels in the image preview to sample colors.</div>';

    samplesPane.appendChild(samplesActionsRow);
    samplesPane.appendChild(samplesList);

    tabsGroup.appendChild(tabNav);
    tabsGroup.appendChild(dominantPane);
    tabsGroup.appendChild(samplesPane);

    var columnsRow = window.FOSS.dom.el("div", {
      className: "row items-start",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-4)",
        width: "100%"
      }
    }, [
      eyedropperGroup,
      tabsGroup
    ]);

    workspaceCard.appendChild(columnsRow);

    // Assembly
    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(controlCard);
    panel.appendChild(workspaceCard);

    // Logic Functions
    function switchTab(tabId) {
      activeTab = tabId;
      if (tabId === "dominant") {
        dominantPane.removeAttribute("hidden");
        samplesPane.setAttribute("hidden", "true");
        tabDominantBtn.className = "btn btn-primary";
        tabSamplesBtn.className = "btn";
      } else {
        dominantPane.setAttribute("hidden", "true");
        samplesPane.removeAttribute("hidden");
        tabDominantBtn.className = "btn";
        tabSamplesBtn.className = "btn btn-primary";
      }
    }

    function createSwatchRow(swatch, showPercentage) {
      var hexCode = swatch.hex || "#000000";
      var rgbArr = swatch.rgb || [0, 0, 0];
      var name = swatch.name || findNearestCssColor(rgbArr[0], rgbArr[1], rgbArr[2]);
      var rgbStr = "rgb(" + rgbArr[0] + ", " + rgbArr[1] + ", " + rgbArr[2] + ")";

      var swatchBtn = window.FOSS.dom.el("button", {
        className: "btn",
        "aria-label": "Color " + hexCode,
        title: "Click to copy " + hexCode,
        style: {
          width: "40px",
          height: "40px",
          minWidth: "40px",
          borderRadius: "var(--radius-sm)",
          border: "2px solid var(--color-border)",
          background: hexCode,
          padding: "0",
          flexShrink: "0"
        },
        onClick: function () {
          copyToClipboard(hexCode);
          statusBar.textContent = "Copied " + hexCode + " to clipboard.";
        }
      });

      var infoCol = window.FOSS.dom.el("div", {
        className: "flex-col flex-1",
        style: { gap: "2px", minWidth: "120px" }
      }, [
        window.FOSS.dom.el("span", {
          className: "font-mono font-bold text-sm",
          text: hexCode + " - " + name
        }),
        window.FOSS.dom.el("span", {
          className: "font-mono text-xs text-muted",
          text: rgbStr + (showPercentage && swatch.percentage != null ? " (" + swatch.percentage + "% of pixels)" : "")
        })
      ]);

      var copyHexBtn = window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "aria-label": "copy hex " + hexCode,
        title: "Copy Hex",
        onClick: function () {
          copyToClipboard(hexCode);
          statusBar.textContent = "Copied " + hexCode + " to clipboard.";
        }
      }, [
        window.FOSS.dom.el("span", { text: "HEX" })
      ]);

      var copyRgbBtn = window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "aria-label": "Copy RGB " + rgbStr,
        title: "Copy RGB",
        onClick: function () {
          copyToClipboard(rgbStr);
          statusBar.textContent = "Copied " + rgbStr + " to clipboard.";
        }
      }, [
        window.FOSS.dom.el("span", { text: "RGB" })
      ]);

      var btnRow = window.FOSS.dom.el("div", {
        className: "row items-center",
        style: { gap: "var(--space-2)" }
      }, [
        copyHexBtn,
        copyRgbBtn
      ]);

      return window.FOSS.dom.el("div", {
        className: "row items-center justify-between p-2 rounded",
        style: {
          display: "flex",
          flexWrap: "wrap",
          background: "var(--color-bg-muted)",
          border: "1px solid var(--color-border)",
          gap: "var(--space-2)",
          width: "100%"
        }
      }, [
        swatchBtn,
        infoCol,
        btnRow
      ]);
    }

    function renderDominantSwatches() {
      swatchList.innerHTML = "";
      if (extractedSwatches.length === 0) {
        swatchList.innerHTML = '<div class="text-sm text-muted p-4 text-center">No dominant colors extracted yet.</div>';
        return;
      }
      for (var i = 0; i < extractedSwatches.length; i++) {
        var row = createSwatchRow(extractedSwatches[i], true);
        swatchList.appendChild(row);
      }
      statusBar.textContent = "Extracted " + extractedSwatches.length + " dominant colors.";
    }

    function updateSamplesUI() {
      var count = sampledSwatches.length;
      var labelSpan = tabSamplesBtn.querySelector("span");
      if (labelSpan) {
        labelSpan.textContent = "eyedropper samples (" + count + ")";
      }
      tabSamplesBtn.setAttribute("aria-label", "eyedropper samples (" + count + ")");
      tabSamplesBtn.setAttribute("title", "eyedropper samples (" + count + ")");

      samplesList.innerHTML = "";
      if (count === 0) {
        samplesList.innerHTML = '<div class="text-sm text-muted p-4 text-center">Click on pixels in the image preview to sample colors.</div>';
        return;
      }
      for (var i = 0; i < count; i++) {
        var row = createSwatchRow(sampledSwatches[i], false);
        samplesList.appendChild(row);
      }
    }

    function drawImageToCanvas(dataUrl) {
      var img = new Image();
      img.onload = function () {
        previewCanvas.width = img.width;
        previewCanvas.height = img.height;
        var ctx2d = previewCanvas.getContext("2d");
        ctx2d.drawImage(img, 0, 0);
        previewCanvas.style.setProperty("display", "block");
        emptyPlaceholder.style.setProperty("display", "none");
      };
      img.src = dataUrl;
    }

    // Canvas Mouse Events
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
      var r = px[0];
      var g = px[1];
      var b = px[2];
      var hexCode = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
      var cssName = findNearestCssColor(r, g, b);
      var cWhite = calcContrastRatio(r, g, b, 255, 255, 255);
      var cBlack = calcContrastRatio(r, g, b, 0, 0, 0);

      hudColorSwatch.style.setProperty("background", hexCode);
      hudHexLabel.textContent = hexCode + " - " + cssName;
      hudRgbLabel.textContent = "rgb(" + r + ", " + g + ", " + b + ")";
      hudPosLabel.textContent = "position: (" + x + ", " + y + ")";
      hudContrastLabel.textContent = "contrast: " + cWhite + ":1 vs white, " + cBlack + ":1 vs black";
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
      var r = px[0];
      var g = px[1];
      var b = px[2];
      var hexCode = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
      var cssName = findNearestCssColor(r, g, b);

      var newSwatch = {
        hex: hexCode,
        rgb: [r, g, b],
        name: cssName
      };
      sampledSwatches.unshift(newSwatch);
      updateSamplesUI();
      copyToClipboard(hexCode);
      statusBar.textContent = "Sampled pixel (" + x + ", " + y + "): " + hexCode + " (" + cssName + ") (Copied to clipboard)";
    });

    function loadImageAndExtract() {
      clearError();
      statusBar.textContent = "Extracting color palette...";
      var nColors = parseInt(numColorsInput.value, 10) || 8;
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
        renderDominantSwatches();
        if (res.data_url) {
          currentImageDataUrl = res.data_url;
          drawImageToCanvas(res.data_url);
        }
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function aggregateMultipleImages(paths) {
      clearError();
      statusBar.textContent = "Aggregating palettes across " + paths.length + " images...";
      var nColors = parseInt(numColorsInput.value, 10) || 8;
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
        renderDominantSwatches();
        statusBar.textContent = "Aggregated " + extractedSwatches.length + " colors from " + paths.length + " images.";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function exportPalette(format) {
      clearError();
      var swatchesToExport = activeTab === "samples" && sampledSwatches.length > 0 ? sampledSwatches : extractedSwatches;
      if (swatchesToExport.length === 0) {
        showError("No colors to export. Extract or sample colors first.");
        return;
      }
      var colorList = swatchesToExport.map(function (s) { return s.hex; });

      var defaultName = "palette." + (format === "strip" ? "png" : format);
      var filters = [];
      if (format === "strip") {
        filters.push({ name: "PNG Image", extensions: ["png"] });
      } else if (format === "gpl") {
        filters.push({ name: "GIMP Palette", extensions: ["gpl"] });
      } else if (format === "css") {
        filters.push({ name: "CSS Stylesheet", extensions: ["css"] });
      } else if (format === "json") {
        filters.push({ name: "JSON File", extensions: ["json"] });
      } else if (format === "aco") {
        filters.push({ name: "Adobe Swatch File", extensions: ["aco"] });
      }

      window.FOSS.api("select_save_path", {
        title: "Export Palette (" + format.toUpperCase() + ")",
        default_name: defaultName,
        filters: filters
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        var apiMethod = "palette_export_" + format;
        window.FOSS.api(apiMethod, {
          colors: colorList,
          output_path: outPath
        }).then(function (saveRes) {
          var savedPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(savedPath, "Palette Exported (" + format.toUpperCase() + ")");
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
    title: "Color Palette Extractor",
    navName: "Palette",
    category: "Visuals",
    icon: "palette",
    tabs: [
      { id: "main", label: "Dominant Colors", render: renderPalette }
    ]
  });
})();
