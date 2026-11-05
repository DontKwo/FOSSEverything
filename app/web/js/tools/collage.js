// Image Collage and Freeform Layers Studio.
// Supports multi-layer composition, Z-ordering, transforms, grid collages, and layered export.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-collage");

    var activeMode = "grid"; // "grid" or "freeform"
    var exportMode = "flattened"; // "flattened" or "layered"
    var layers = []; // array of layer objects
    var selectedLayerId = null;
    var canvasWidth = 1920;
    var canvasHeight = 1080;
    var isTransparent = false;
    var bgColor = "#f0f0f0";
    var loadedBitmaps = {}; // source_path -> HTMLImageElement

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "collage-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "collage-error-banner"
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
      className: "hidden",
      "data-testid": "collage-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "collage-result-card",
        title: titleText || "Collage Saved",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Top Mode and Canvas Setup Bar
    var topBar = window.FOSS.dom.el("div", {
      className: "flex flex-wrap items-center gap-2 p-2 rounded border border-border bg-surface collage-topbar"
    });

    // Mode Toggle via Segmented Control
    var modeSegmented = window.FOSS.components.segmented({
      testid: "collage-mode-toggle",
      items: [
        { id: "grid", label: "Grid Collage" },
        { id: "freeform", label: "Freeform Layers" }
      ],
      value: "grid",
      onChange: function (val) {
        setMode(val);
      }
    });

    // Canvas Size Preset
    var presetCanvasSelect = window.FOSS.dom.el("select", {
      className: "select text-xs w-36",
      "data-testid": "collage-canvas-preset",
      "aria-label": "Canvas preset size",
      title: "Canvas preset size",
      onChange: function () {
        var val = presetCanvasSelect.value;
        if (val === "1080x1080") {
          canvasWInput.value = 1080;
          canvasHInput.value = 1080;
        } else if (val === "1920x1080") {
          canvasWInput.value = 1920;
          canvasHInput.value = 1080;
        } else if (val === "1080x1350") {
          canvasWInput.value = 1080;
          canvasHInput.value = 1350;
        } else if (val === "2000x2000") {
          canvasWInput.value = 2000;
          canvasHInput.value = 2000;
        }
        applyCanvasDimensions();
      }
    }, [
      window.FOSS.dom.el("option", { value: "1920x1080", selected: true, text: "1920 x 1080 (16:9)" }),
      window.FOSS.dom.el("option", { value: "1080x1080", text: "1080 x 1080 (Square)" }),
      window.FOSS.dom.el("option", { value: "1080x1350", text: "1080 x 1350 (4:5)" }),
      window.FOSS.dom.el("option", { value: "2000x2000", text: "2000 x 2000 (Hi-Res)" }),
      window.FOSS.dom.el("option", { value: "custom", text: "Custom Dimensions" })
    ]);

    var canvasWInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "data-testid": "collage-canvas-w",
      "aria-label": "Canvas width in pixels",
      title: "Canvas width in pixels",
      value: 1920,
      min: 100,
      max: 8000,
      onInput: applyCanvasDimensions
    });

    var canvasHInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "data-testid": "collage-canvas-h",
      "aria-label": "Canvas height in pixels",
      title: "Canvas height in pixels",
      value: 1080,
      min: 100,
      max: 8000,
      onInput: applyCanvasDimensions
    });

    function applyCanvasDimensions() {
      var w = parseInt(canvasWInput.value, 10);
      var h = parseInt(canvasHInput.value, 10);
      if (w > 0 && h > 0) {
        canvasWidth = w;
        canvasHeight = h;
        renderCanvas();
      }
    }

    // Transparent Background Checkbox
    var transparentChk = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "collage-transparent-chk-id",
      className: "checkbox",
      "data-testid": "collage-transparent-chk",
      "aria-label": "Transparent background",
      title: "Transparent background",
      onChange: function () {
        isTransparent = transparentChk.checked;
        renderCanvas();
        if (activeMode === "grid") updateGridPreview();
      }
    });

    // Background Color Picker
    var hiddenColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      hidden: true,
      value: "#f0f0f0",
      "aria-label": "Pick background color",
      title: "Pick background color",
      onChange: function () {
        bgColorInput.value = hiddenColorPicker.value;
        bgColor = hiddenColorPicker.value;
        renderCanvas();
        if (activeMode === "grid") updateGridPreview();
      }
    });

    var bgColorInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input text-xs font-mono w-20",
      "data-testid": "collage-bg-color",
      "aria-label": "Background color hex",
      title: "Background color hex",
      value: "#f0f0f0",
      onInput: function () {
        bgColor = bgColorInput.value;
        renderCanvas();
        if (activeMode === "grid") updateGridPreview();
      }
    });

    var pickColorBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm p-1",
      type: "button",
      "aria-label": "Choose background color",
      title: "Choose background color",
      onClick: function () {
        hiddenColorPicker.click();
      }
    }, [window.FOSS.icons.el("palette", 14)]);

    // Convert Grid to Layers button
    var gridToLayersBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-grid-to-layers-btn",
      "aria-label": "Convert Grid to Layers",
      title: "Convert Grid to Layers",
      type: "button",
      text: "Convert Grid to Layers",
      onClick: convertGridToLayers
    });

    topBar.appendChild(modeSegmented.el);
    topBar.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-1" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Canvas:" }),
      presetCanvasSelect,
      canvasWInput,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "x" }),
      canvasHInput
    ]));
    topBar.appendChild(window.FOSS.dom.el("label", {
      htmlFor: "collage-transparent-chk-id",
      className: "flex items-center gap-1 text-xs cursor-pointer"
    }, [
      transparentChk,
      window.FOSS.dom.el("span", { text: "Transparent BG" })
    ]));
    topBar.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-1" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "BG Color:" }),
      bgColorInput,
      pickColorBtn,
      hiddenColorPicker
    ]));
    topBar.appendChild(gridToLayersBtn);

    // Main Stage Pane
    var stagePane = window.FOSS.dom.el("div", { className: "collage-stage-pane" });

    // Z-Order and Action Bar for Freeform
    var zOrderBar = window.FOSS.dom.el("div", {
      className: "flex flex-wrap items-center gap-2 p-2 rounded bg-surface border border-border hidden"
    });

    var bringFrontBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-bring-front-btn",
      "aria-label": "Bring to Front",
      title: "Bring to Front",
      type: "button",
      onClick: function () {
        moveSelectedLayerZ("front");
      }
    }, [window.FOSS.icons.el("chevron-up", 14), window.FOSS.dom.el("span", { text: "Front" })]);
    bringFrontBtn.setAttribute("data-testalias", "collage-layer-front");

    var bringForwardBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-bring-forward-btn",
      "aria-label": "Bring Forward",
      title: "Bring Forward",
      type: "button",
      onClick: function () {
        moveSelectedLayerZ("forward");
      }
    }, [window.FOSS.icons.el("chevron-up", 14), window.FOSS.dom.el("span", { text: "Forward" })]);
    bringForwardBtn.setAttribute("data-testalias", "collage-layer-up");

    var sendBackwardBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-send-backward-btn",
      "aria-label": "Send Backward",
      title: "Send Backward",
      type: "button",
      onClick: function () {
        moveSelectedLayerZ("backward");
      }
    }, [window.FOSS.icons.el("chevron-down", 14), window.FOSS.dom.el("span", { text: "Backward" })]);
    sendBackwardBtn.setAttribute("data-testalias", "collage-layer-down");

    var sendBackBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-send-back-btn",
      "aria-label": "Send to Back",
      title: "Send to Back",
      type: "button",
      onClick: function () {
        moveSelectedLayerZ("back");
      }
    }, [window.FOSS.icons.el("chevron-down", 14), window.FOSS.dom.el("span", { text: "Back" })]);
    sendBackBtn.setAttribute("data-testalias", "collage-layer-back");

    var dupLayerBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-dup-layer-btn",
      "aria-label": "Duplicate Layer",
      title: "Duplicate Layer",
      type: "button",
      onClick: duplicateSelectedLayer
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Duplicate" })]);

    var delLayerBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm text-danger",
      "data-testid": "collage-del-layer-btn",
      "aria-label": "Delete Layer",
      title: "Delete Layer",
      type: "button",
      onClick: deleteSelectedLayer
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Delete" })]);

    zOrderBar.appendChild(bringFrontBtn);
    zOrderBar.appendChild(bringForwardBtn);
    zOrderBar.appendChild(sendBackwardBtn);
    zOrderBar.appendChild(sendBackBtn);
    zOrderBar.appendChild(dupLayerBtn);
    zOrderBar.appendChild(delLayerBtn);

    // Interactive Stage Viewport
    var stageWrapper = window.FOSS.dom.el("div", {
      className: "collage-stage-wrapper checkerboard-bg",
      "data-testid": "collage-stage"
    });

    // Freeform Canvas element
    var freeformCanvas = window.FOSS.dom.el("canvas", {
      className: "collage-freeform-canvas hidden",
      "data-testid": "collage-freeform-canvas",
      width: 1920,
      height: 1080
    });

    // Grid Preview Container
    var gridPreviewContainer = window.FOSS.dom.el("div", {
      className: "collage-preview-display p-4 min-h-48",
      "data-testid": "collage-preview-display"
    });
    gridPreviewContainer.innerHTML = '<div class="text-sm text-center">No collage preview yet. Add images to generate preview.</div>';

    stageWrapper.appendChild(freeformCanvas);
    stageWrapper.appendChild(gridPreviewContainer);

    stagePane.appendChild(zOrderBar);
    stagePane.appendChild(stageWrapper);

    // Right Sidebar Pane
    var sidebarPane = window.FOSS.dom.el("div", { className: "collage-sidebar-pane" });

    // Card 1: Import and Layer Stack
    var importCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "collage-images-card"
    });
    importCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Images & Layers" }));

    var addImagesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "collage-add-images",
      "aria-label": "Add images",
      title: "Add images",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          addSourceImages(res.paths);
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Add Images" })]);

    var clearImagesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-clear-images",
      "aria-label": "Clear all images",
      title: "Clear all images",
      type: "button",
      onClick: function () {
        layers = [];
        selectedLayerId = null;
        renderLayerList();
        renderCanvas();
        updateGridPreview();
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 16), window.FOSS.dom.el("span", { text: "Clear" })]);

    importCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [addImagesBtn, clearImagesBtn]));

    // Draggable Layers List
    var layersCard = window.FOSS.dom.el("div", {
      className: "flex flex-col gap-1 overflow-y-auto max-h-60",
      "data-testid": "collage-layers-list"
    });
    var layersList = window.FOSS.dom.el("div", {
      className: "flex flex-col gap-1",
      "data-testid": "collage-images-list"
    });
    layersCard.appendChild(layersList);
    importCard.appendChild(layersCard);

    // Card 2: Inspector / Grid Settings
    var controlsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var controlsTitle = window.FOSS.dom.el("h3", {
      className: "card-title text-base",
      text: "Grid Collage Settings"
    });
    controlsCard.appendChild(controlsTitle);

    // Inspector form fields (for Freeform mode)
    var inspectorHost = window.FOSS.dom.el("div", { className: "flex-col gap-2 hidden" });

    var inspXInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "aria-label": "Layer X coordinate",
      title: "Layer X coordinate",
      onInput: updateSelectedFromInspector
    });
    var inspYInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "aria-label": "Layer Y coordinate",
      title: "Layer Y coordinate",
      onInput: updateSelectedFromInspector
    });
    var inspWInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "aria-label": "Layer width",
      title: "Layer width",
      onInput: updateSelectedFromInspector
    });
    var inspHInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "aria-label": "Layer height",
      title: "Layer height",
      onInput: updateSelectedFromInspector
    });
    var inspRotInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input text-xs w-20",
      "aria-label": "Layer rotation angle",
      title: "Layer rotation angle",
      onInput: updateSelectedFromInspector
    });
    var inspOpacityInput = window.FOSS.dom.el("input", {
      type: "range",
      min: 0,
      max: 100,
      value: 100,
      className: "slider grow",
      "aria-label": "Layer opacity slider",
      title: "Layer opacity slider",
      style: "min-height: 2rem;",
      onInput: function() {
        inspOpacityNumber.value = inspOpacityInput.value;
        updateSelectedFromInspector();
      }
    });
    var inspOpacityNumber = window.FOSS.dom.el("input", {
      type: "number",
      min: 0,
      max: 100,
      value: 100,
      className: "input text-xs w-16",
      "aria-label": "Layer opacity percentage",
      title: "Layer opacity percentage",
      onInput: function() {
        var val = Math.min(100, Math.max(0, parseInt(inspOpacityNumber.value, 10) || 0));
        inspOpacityInput.value = val;
        updateSelectedFromInspector();
      }
    });

    var centerLayerBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm text-xs",
      "aria-label": "Center on Canvas",
      title: "Center on Canvas",
      type: "button",
      text: "Center on Canvas",
      onClick: function () {
        var l = getSelectedLayer();
        if (!l) return;
        l.x = Math.round((canvasWidth - l.width) / 2);
        l.y = Math.round((canvasHeight - l.height) / 2);
        syncInspectorFromSelected();
        renderCanvas();
      }
    });

    var fitLayerBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm text-xs",
      "aria-label": "Fit to Canvas",
      title: "Fit to Canvas",
      type: "button",
      text: "Fit to Canvas",
      onClick: function () {
        var l = getSelectedLayer();
        if (!l) return;
        var scale = Math.min(canvasWidth / l.width, canvasHeight / l.height);
        l.width = Math.round(l.width * scale);
        l.height = Math.round(l.height * scale);
        l.x = Math.round((canvasWidth - l.width) / 2);
        l.y = Math.round((canvasHeight - l.height) / 2);
        syncInspectorFromSelected();
        renderCanvas();
      }
    });

    inspectorHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-8", text: "X:" }),
      inspXInput,
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-8 ml-2", text: "Y:" }),
      inspYInput
    ]));
    inspectorHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-8", text: "W:" }),
      inspWInput,
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-8 ml-2", text: "H:" }),
      inspHInput
    ]));
    inspectorHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-8", text: "Rot:" }),
      inspRotInput,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "deg" })
    ]));
    inspectorHost.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-14", text: "Opacity:" }),
      inspOpacityInput,
      inspOpacityNumber,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "%" })
    ]));
    inspectorHost.appendChild(window.FOSS.dom.el("div", { className: "row mt-1" }, [centerLayerBtn, fitLayerBtn]));

    // Grid controls host (for Grid mode)
    var gridHost = window.FOSS.dom.el("div", { className: "flex-col gap-2" });

    var presetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "collage-preset-select",
      "aria-label": "Preset layout",
      title: "Preset layout",
      onChange: function () {
        var val = presetSelect.value;
        if (val === "2col-side" || val === "2x2-quad" || val === "2x1-wide") colsSelect.value = "2";
        else if (val === "3col-trip" || val === "3x3-insta") colsSelect.value = "3";
        else if (val === "1col-story") colsSelect.value = "1";
        updateGridPreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "2col-side", text: "Side-by-side 2-up (2 columns)" }),
      window.FOSS.dom.el("option", { value: "3col-trip", text: "Triptych (3 columns)" }),
      window.FOSS.dom.el("option", { value: "3x3-insta", text: "Instagram grid (3x3)" }),
      window.FOSS.dom.el("option", { value: "2x2-quad", text: "Product grid (2x2)" }),
      window.FOSS.dom.el("option", { value: "1col-story", text: "Story strip (1 column)" }),
      window.FOSS.dom.el("option", { value: "2x1-wide", text: "Wide panel (2x1)" })
    ]);

    var colsSelect = window.FOSS.dom.el("select", {
      className: "select w-24",
      "data-testid": "collage-columns-select",
      "aria-label": "Columns count",
      title: "Columns count",
      onChange: updateGridPreview
    }, [
      window.FOSS.dom.el("option", { value: "1", text: "1" }),
      window.FOSS.dom.el("option", { value: "2", selected: true, text: "2" }),
      window.FOSS.dom.el("option", { value: "3", text: "3" }),
      window.FOSS.dom.el("option", { value: "4", text: "4" }),
      window.FOSS.dom.el("option", { value: "5", text: "5" })
    ]);

    var fitSelect = window.FOSS.dom.el("select", {
      className: "select w-28",
      "data-testid": "collage-fit-select",
      "aria-label": "Fit mode",
      title: "Fit mode",
      onChange: updateGridPreview
    }, [
      window.FOSS.dom.el("option", { value: "cover", text: "Cover" }),
      window.FOSS.dom.el("option", { value: "contain", text: "Contain" }),
      window.FOSS.dom.el("option", { value: "stretch", text: "Stretch" })
    ]);

    var paddingInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-20",
      "data-testid": "collage-padding-input",
      "aria-label": "Cell padding",
      title: "Cell padding",
      value: 12,
      min: 0,
      max: 60,
      onInput: updateGridPreview
    });

    var cornerRadiusInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-20",
      "data-testid": "collage-corner-radius",
      "aria-label": "Corner radius",
      title: "Corner radius",
      value: 0,
      min: 0,
      max: 100,
      onInput: updateGridPreview
    });

    var captionsCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "collage-captions-check-id",
      className: "checkbox",
      "data-testid": "collage-captions-check",
      "aria-label": "Add filenames as captions",
      title: "Add filenames as captions",
      onChange: updateGridPreview
    });

    var watermarkInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow text-xs font-mono",
      "data-testid": "collage-watermark-input",
      "aria-label": "Watermark text",
      title: "Watermark text",
      placeholder: "Optional watermark text",
      onInput: updateGridPreview
    });

    var previewBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-preview-btn",
      "aria-label": "Generate collage preview",
      title: "Generate collage preview",
      type: "button",
      onClick: updateGridPreview
    }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Generate Collage Preview" })]);

    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-16", text: "Preset:" }),
      presetSelect
    ]));
    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-16", text: "Columns:" }),
      colsSelect,
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-10 ml-2", text: "Fit:" }),
      fitSelect
    ]));
    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-16", text: "Padding:" }),
      paddingInput,
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-16 ml-2", text: "Radius:" }),
      cornerRadiusInput
    ]));
    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", {
        htmlFor: "collage-captions-check-id",
        className: "flex items-center gap-2 text-xs cursor-pointer"
      }, [captionsCheck, window.FOSS.dom.el("span", { text: "Add Filenames as Captions" })])
    ]));
    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted w-16", text: "Watermark:" }),
      watermarkInput
    ]));
    gridHost.appendChild(window.FOSS.dom.el("div", { className: "row mt-1" }, [previewBtn]));

    controlsCard.appendChild(inspectorHost);
    controlsCard.appendChild(gridHost);

    // Card 3: Export Card
    var exportCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    exportCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export Collage" }));

    var exportSegmented = window.FOSS.components.segmented({
      testid: "collage-export-kind",
      items: [
        { id: "flattened", label: "Export Flattened" },
        { id: "layered", label: "Export in Layers" }
      ],
      value: "flattened",
      onChange: function (val) {
        setExportKind(val);
      }
    });

    var flatFormatSelect = window.FOSS.dom.el("select", {
      className: "select text-xs",
      "data-testid": "collage-flat-format-select",
      "aria-label": "Flattened format",
      title: "Flattened format"
    }, [
      window.FOSS.dom.el("option", { value: "png", text: "PNG (Lossless)" }),
      window.FOSS.dom.el("option", { value: "jpeg", text: "JPEG (Compressed)" }),
      window.FOSS.dom.el("option", { value: "webp", text: "WEBP (Modern Web)" })
    ]);

    var layeredFormatSelect = window.FOSS.dom.el("select", {
      className: "select text-xs hidden",
      "data-testid": "collage-layered-format-select",
      "aria-label": "Layered format",
      title: "Layered format"
    }, [
      window.FOSS.dom.el("option", { value: "psd", text: "Photoshop Layered (.psd)" }),
      window.FOSS.dom.el("option", { value: "ora", text: "OpenRaster Layered (.ora)" }),
      window.FOSS.dom.el("option", { value: "zip", text: "Transparent PNG Stack (.zip)" }),
      window.FOSS.dom.el("option", { value: "tiff", text: "Multi-Layer TIFF (.tiff)" })
    ]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "collage-save-btn",
      "aria-label": "Save collage",
      title: "Save collage",
      type: "button",
      onClick: handleExport
    }, [window.FOSS.icons.el("save", 16), window.FOSS.dom.el("span", { text: "Save Collage" })]);

    var exportLayersBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm hidden",
      "data-testid": "collage-export-layers-btn",
      "aria-label": "Export Layers",
      title: "Export Layers",
      type: "button",
      onClick: handleExport
    }, [window.FOSS.icons.el("archive", 16), window.FOSS.dom.el("span", { text: "Export Layers..." })]);

    exportCard.appendChild(exportSegmented.el);
    exportCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
      window.FOSS.dom.el("label", { className: "text-xs text-muted", text: "Format:" }),
      flatFormatSelect,
      layeredFormatSelect
    ]));
    exportCard.appendChild(window.FOSS.dom.el("div", { className: "row mt-1" }, [saveBtn, exportLayersBtn]));

    sidebarPane.appendChild(importCard);
    sidebarPane.appendChild(controlsCard);
    sidebarPane.appendChild(exportCard);

    // Split Container
    var split = window.FOSS.dom.el("div", {
      className: "split resizable split-main-first collage-workbench-split",
      "data-testid": "collage-split"
    }, [
      stagePane,
      window.FOSS.components.splitDivider({ vertical: true }),
      sidebarPane
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(topBar);
    panel.appendChild(split);

    // Helper Functions
    function setMode(mode) {
      activeMode = mode;
      if (mode === "freeform") {
        freeformCanvas.classList.remove("hidden");
        gridPreviewContainer.classList.add("hidden");
        zOrderBar.classList.remove("hidden");
        gridToLayersBtn.classList.add("hidden");
        controlsTitle.textContent = "Layer Inspector";
        inspectorHost.classList.remove("hidden");
        gridHost.classList.add("hidden");
        renderCanvas();
      } else {
        freeformCanvas.classList.add("hidden");
        gridPreviewContainer.classList.remove("hidden");
        zOrderBar.classList.add("hidden");
        gridToLayersBtn.classList.remove("hidden");
        controlsTitle.textContent = "Grid Collage Settings";
        inspectorHost.classList.add("hidden");
        gridHost.classList.remove("hidden");
        updateGridPreview();
      }
    }

    function setExportKind(kind) {
      exportMode = kind;
      if (kind === "flattened") {
        flatFormatSelect.classList.remove("hidden");
        layeredFormatSelect.classList.add("hidden");
        saveBtn.classList.remove("hidden");
        exportLayersBtn.classList.add("hidden");
      } else {
        flatFormatSelect.classList.add("hidden");
        layeredFormatSelect.classList.remove("hidden");
        saveBtn.classList.add("hidden");
        exportLayersBtn.classList.remove("hidden");
      }
    }

    function addSourceImages(paths) {
      if (!paths || !paths.length) return;
      var loadPromises = [];
      paths.forEach(function (p) {
        var prm = window.FOSS.api("collage_load_layer_asset", { file_path: p }).then(function (res) {
          if (res && res.data_url) {
            var img = new Image();
            img.src = res.data_url;
            loadedBitmaps[p] = img;

            var fileName = p.split(/[/\\]/).pop();
            var layerW = res.width || 400;
            var layerH = res.height || 400;

            // Scale layer to fit within 60% of canvas if larger
            var maxDim = Math.min(canvasWidth, canvasHeight) * 0.6;
            if (layerW > maxDim || layerH > maxDim) {
              var s = maxDim / Math.max(layerW, layerH);
              layerW = Math.round(layerW * s);
              layerH = Math.round(layerH * s);
            }

            var lObj = {
              id: "l_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
              name: fileName,
              source_path: p,
              x: Math.round((canvasWidth - layerW) / 2 + (layers.length * 20)),
              y: Math.round((canvasHeight - layerH) / 2 + (layers.length * 20)),
              width: layerW,
              height: layerH,
              rotation_deg: 0.0,
              opacity: 1.0,
              visible: true,
              locked: false
            };
            layers.push(lObj);
            selectedLayerId = lObj.id;
          }
        });
        loadPromises.push(prm);
      });

      Promise.all(loadPromises).then(function () {
        renderLayerList();
        syncInspectorFromSelected();
        renderCanvas();
        updateGridPreview();
        statusBar.textContent = "Loaded " + layers.length + " layer(s).";
      });
    }

    function renderLayerList() {
      layersList.innerHTML = "";
      if (!layers.length) {
        layersList.innerHTML = '<div class="text-xs text-muted p-2">No images added. Click Add Images to select photos.</div>';
        return;
      }
      // Top layers rendered at top of list (Photoshop style)
      for (var i = layers.length - 1; i >= 0; i--) {
        (function (idx) {
          var layer = layers[idx];
          var isSel = (layer.id === selectedLayerId);
          var item = window.FOSS.dom.el("div", {
            className: "collage-layer-item collage-layer-card card card-compact flex-col gap-1 p-2 text-xs" + (isSel ? " active" : ""),
            "data-testid": "collage-layer-card",
            draggable: true,
            onClick: function (e) {
              if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON" || e.target.closest("button")) return;
              selectedLayerId = layer.id;
              renderLayerList();
              syncInspectorFromSelected();
              renderCanvas();
            }
          });

          item.addEventListener("dragstart", function (e) {
            e.dataTransfer.setData("text/plain", String(idx));
          });
          item.addEventListener("dragover", function (e) {
            e.preventDefault();
          });
          item.addEventListener("drop", function (e) {
            e.preventDefault();
            var srcIdx = parseInt(e.dataTransfer.getData("text/plain"), 10);
            if (!isNaN(srcIdx) && srcIdx !== idx) {
              var moved = layers.splice(srcIdx, 1)[0];
              layers.splice(idx, 0, moved);
              renderLayerList();
              renderCanvas();
            }
          });

          // Visibility toggle
          var visBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-sm p-0",
            type: "button",
            "data-testid": "collage-layer-visibility",
            "aria-label": layer.visible ? "Hide layer" : "Show layer",
            title: layer.visible ? "Hide layer" : "Show layer",
            onClick: function () {
              layer.visible = !layer.visible;
              renderLayerList();
              renderCanvas();
            }
          }, [window.FOSS.icons.el(layer.visible ? "eye" : "eye-off", 14)]);

          // Lock toggle
          var lockBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-sm p-0",
            type: "button",
            "data-testid": "collage-layer-lock",
            "aria-label": layer.locked ? "Unlock layer" : "Lock layer",
            title: layer.locked ? "Unlock layer" : "Lock layer",
            onClick: function () {
              layer.locked = !layer.locked;
              renderLayerList();
              renderCanvas();
            }
          }, [window.FOSS.icons.el(layer.locked ? "lock" : "unlock", 14)]);

          // Name
          var nameSpan = window.FOSS.dom.el("span", {
            className: "grow truncate font-semibold",
            text: layer.name,
            title: layer.name
          });

          // Delete button
          var delBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-sm p-0 text-danger",
            type: "button",
            "data-testid": "collage-layer-delete",
            "aria-label": "Remove layer",
            title: "Remove layer",
            onClick: function () {
              layers.splice(idx, 1);
              if (selectedLayerId === layer.id) {
                selectedLayerId = layers.length ? layers[layers.length - 1].id : null;
              }
              renderLayerList();
              syncInspectorFromSelected();
              renderCanvas();
              updateGridPreview();
            }
          }, [window.FOSS.icons.el("trash", 14)]);

          var topRow = window.FOSS.dom.el("div", {
            className: "row items-center gap-1 justify-between",
            style: "width: 100%;"
          }, [visBtn, lockBtn, nameSpan, delBtn]);

          // Layer Z-controls
          var frontBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-xs",
            type: "button",
            "data-testid": "collage-layer-front",
            title: "Bring to Front",
            "aria-label": "Bring to Front",
            onClick: function () {
              selectedLayerId = layer.id;
              moveSelectedLayerZ("front");
            }
          }, [window.FOSS.icons.el("chevrons-up", 12), window.FOSS.dom.el("span", { text: "Front" })]);

          var upBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-xs",
            type: "button",
            "data-testid": "collage-layer-up",
            title: "Move Up",
            "aria-label": "Move Up",
            onClick: function () {
              selectedLayerId = layer.id;
              moveSelectedLayerZ("forward");
            }
          }, [window.FOSS.icons.el("chevron-up", 12), window.FOSS.dom.el("span", { text: "Up" })]);

          var downBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-xs",
            type: "button",
            "data-testid": "collage-layer-down",
            title: "Move Down",
            "aria-label": "Move Down",
            onClick: function () {
              selectedLayerId = layer.id;
              moveSelectedLayerZ("backward");
            }
          }, [window.FOSS.icons.el("chevron-down", 12), window.FOSS.dom.el("span", { text: "Down" })]);

          var backBtn = window.FOSS.dom.el("button", {
            className: "btn btn-ghost btn-xs",
            type: "button",
            "data-testid": "collage-layer-back",
            title: "Send to Back",
            "aria-label": "Send to Back",
            onClick: function () {
              selectedLayerId = layer.id;
              moveSelectedLayerZ("back");
            }
          }, [window.FOSS.icons.el("chevrons-down", 12), window.FOSS.dom.el("span", { text: "Back" })]);

          var zOrderRow = window.FOSS.dom.el("div", {
            className: "row gap-1 items-center flex-wrap"
          }, [frontBtn, upBtn, downBtn, backBtn]);

          // Opacity slider per layer
          var opacityPct = Math.round((layer.opacity !== undefined ? layer.opacity : 1.0) * 100);
          var opacityNumInput = window.FOSS.dom.el("input", {
            type: "number",
            min: "0",
            max: "100",
            value: String(opacityPct),
            className: "input input-sm w-16 text-xs",
            "aria-label": "Layer Opacity Percentage",
            title: "Opacity Percentage"
          });
          var opacitySlider = window.FOSS.dom.el("input", {
            type: "range",
            min: "0",
            max: "100",
            value: String(opacityPct),
            className: "input input-sm",
            "data-testid": "collage-layer-opacity",
            "aria-label": "Layer Opacity",
            title: "Opacity",
            style: "flex: 1 1 0%; min-width: 0;"
          });

          opacitySlider.addEventListener("input", function () {
            var val = parseInt(opacitySlider.value, 10);
            layer.opacity = val / 100.0;
            opacityNumInput.value = val;
            if (selectedLayerId === layer.id && inspOpacityInput) {
              inspOpacityInput.value = val;
              inspOpacityNumber.value = val;
            }
            renderCanvas();
          });
          opacityNumInput.addEventListener("input", function () {
            var val = Math.min(100, Math.max(0, parseInt(opacityNumInput.value, 10) || 0));
            opacitySlider.value = val;
            layer.opacity = val / 100.0;
            if (selectedLayerId === layer.id && inspOpacityInput) {
              inspOpacityInput.value = val;
              inspOpacityNumber.value = val;
            }
            renderCanvas();
          });

          var opacityRow = window.FOSS.dom.el("div", {
            className: "row items-center gap-2",
            style: "width: 100%;"
          }, [
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Opacity:" }),
            opacitySlider,
            opacityNumInput,
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "%" })
          ]);

          item.appendChild(topRow);
          item.appendChild(zOrderRow);
          item.appendChild(opacityRow);
          layersList.appendChild(item);
        })(i);
      }
    }

    function getSelectedLayer() {
      for (var i = 0; i < layers.length; i++) {
        if (layers[i].id === selectedLayerId) return layers[i];
      }
      return null;
    }

    function syncInspectorFromSelected() {
      var l = getSelectedLayer();
      if (!l) {
        inspXInput.value = 0;
        inspYInput.value = 0;
        inspWInput.value = 0;
        inspHInput.value = 0;
        inspRotInput.value = 0;
        inspOpacityInput.value = 100;
        inspOpacityNumber.value = 100;
        return;
      }
      inspXInput.value = l.x;
      inspYInput.value = l.y;
      inspWInput.value = l.width;
      inspHInput.value = l.height;
      inspRotInput.value = l.rotation_deg;
      inspOpacityInput.value = Math.round(l.opacity * 100);
      inspOpacityNumber.value = Math.round(l.opacity * 100);
    }

    function updateSelectedFromInspector() {
      var l = getSelectedLayer();
      if (!l) return;
      l.x = parseInt(inspXInput.value, 10) || 0;
      l.y = parseInt(inspYInput.value, 10) || 0;
      l.width = Math.max(1, parseInt(inspWInput.value, 10) || 1);
      l.height = Math.max(1, parseInt(inspHInput.value, 10) || 1);
      l.rotation_deg = parseFloat(inspRotInput.value) || 0;
      l.opacity = (parseInt(inspOpacityInput.value, 10) || 0) / 100.0;
      renderCanvas();
    }

    function moveSelectedLayerZ(dir) {
      var idx = -1;
      for (var i = 0; i < layers.length; i++) {
        if (layers[i].id === selectedLayerId) {
          idx = i;
          break;
        }
      }
      if (idx === -1) return;
      var item = layers.splice(idx, 1)[0];
      if (dir === "front") {
        layers.push(item);
      } else if (dir === "back") {
        layers.unshift(item);
      } else if (dir === "forward") {
        var newIdx = Math.min(layers.length, idx + 1);
        layers.splice(newIdx, 0, item);
      } else if (dir === "backward") {
        var backIdx = Math.max(0, idx - 1);
        layers.splice(backIdx, 0, item);
      }
      renderLayerList();
      renderCanvas();
    }

    function duplicateSelectedLayer() {
      var l = getSelectedLayer();
      if (!l) return;
      var dup = JSON.parse(JSON.stringify(l));
      dup.id = "l_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
      dup.name = l.name + " (Copy)";
      dup.x += 30;
      dup.y += 30;
      layers.push(dup);
      selectedLayerId = dup.id;
      renderLayerList();
      syncInspectorFromSelected();
      renderCanvas();
    }

    function deleteSelectedLayer() {
      var l = getSelectedLayer();
      if (!l) return;
      var idx = layers.indexOf(l);
      if (idx !== -1) {
        layers.splice(idx, 1);
        selectedLayerId = layers.length ? layers[layers.length - 1].id : null;
        renderLayerList();
        syncInspectorFromSelected();
        renderCanvas();
        updateGridPreview();
      }
    }

    // Convert Grid positions to Freeform Layers
    function convertGridToLayers() {
      if (!layers.length) return;
      var cols = parseInt(colsSelect.value, 10) || 2;
      var pad = parseInt(paddingInput.value, 10) || 12;
      var rows = Math.ceil(layers.length / cols);
      var cellW = Math.floor((canvasWidth - (pad * (cols + 1))) / cols);
      var cellH = Math.floor((canvasHeight - (pad * (rows + 1))) / rows);

      for (var i = 0; i < layers.length; i++) {
        var r = Math.floor(i / cols);
        var c = i % cols;
        layers[i].x = pad + c * (cellW + pad);
        layers[i].y = pad + r * (cellH + pad);
        layers[i].width = cellW;
        layers[i].height = cellH;
        layers[i].rotation_deg = 0;
      }
      modeSegmented.setValue("freeform");
      setMode("freeform");
      syncInspectorFromSelected();
      renderCanvas();
    }

    // Canvas Rendering & Interactions
    var ctx2d = freeformCanvas.getContext("2d");

    function renderCanvas() {
      freeformCanvas.width = canvasWidth;
      freeformCanvas.height = canvasHeight;
      ctx2d.clearRect(0, 0, canvasWidth, canvasHeight);

      // Render background if not transparent
      if (!isTransparent) {
        ctx2d.fillStyle = bgColor;
        ctx2d.fillRect(0, 0, canvasWidth, canvasHeight);
      }

      // Draw layers bottom-to-top
      for (var i = 0; i < layers.length; i++) {
        var l = layers[i];
        if (!l.visible) continue;
        var bmp = loadedBitmaps[l.source_path];
        if (!bmp) continue;

        ctx2d.save();
        ctx2d.globalAlpha = Math.max(0, Math.min(1, l.opacity));

        // Translation to center of layer for rotation
        var cx = l.x + l.width / 2;
        var cy = l.y + l.height / 2;
        ctx2d.translate(cx, cy);
        if (l.rotation_deg) {
          ctx2d.rotate((l.rotation_deg * Math.PI) / 180);
        }
        ctx2d.drawImage(bmp, -l.width / 2, -l.height / 2, l.width, l.height);
        ctx2d.restore();
      }

      // Draw active selection box and handles
      var sel = getSelectedLayer();
      if (sel && sel.visible) {
        drawSelectionBox(sel);
      }
    }

    function drawSelectionBox(layer) {
      ctx2d.save();
      var cx = layer.x + layer.width / 2;
      var cy = layer.y + layer.height / 2;
      ctx2d.translate(cx, cy);
      if (layer.rotation_deg) {
        ctx2d.rotate((layer.rotation_deg * Math.PI) / 180);
      }

      var hw = layer.width / 2;
      var hh = layer.height / 2;

      ctx2d.strokeStyle = "#3b82f6";
      ctx2d.lineWidth = 2;
      ctx2d.strokeRect(-hw, -hh, layer.width, layer.height);

      // Draw 8 resize handles
      var handleSize = 8;
      ctx2d.fillStyle = "#ffffff";
      ctx2d.strokeStyle = "#3b82f6";
      ctx2d.lineWidth = 1.5;

      var pts = [
        [-hw, -hh], [0, -hh], [hw, -hh],
        [hw, 0], [hw, hh], [0, hh],
        [-hw, hh], [-hw, 0]
      ];
      pts.forEach(function (pt) {
        ctx2d.fillRect(pt[0] - handleSize / 2, pt[1] - handleSize / 2, handleSize, handleSize);
        ctx2d.strokeRect(pt[0] - handleSize / 2, pt[1] - handleSize / 2, handleSize, handleSize);
      });

      // Rotation handle above top-center
      var rotY = -hh - 20;
      ctx2d.beginPath();
      ctx2d.moveTo(0, -hh);
      ctx2d.lineTo(0, rotY);
      ctx2d.stroke();
      ctx2d.beginPath();
      ctx2d.arc(0, rotY, handleSize / 2, 0, Math.PI * 2);
      ctx2d.fill();
      ctx2d.stroke();

      ctx2d.restore();
    }

    // Canvas Mouse / Drag Handling
    var isDragging = false;
    var dragMode = null;
    var dragHandleIdx = -1;
    var dragStartX = 0;
    var dragStartY = 0;
    var origLayerSpec = null;

    freeformCanvas.addEventListener("mousedown", function (e) {
      var rect = freeformCanvas.getBoundingClientRect();
      var scaleX = canvasWidth / rect.width;
      var scaleY = canvasHeight / rect.height;
      var mx = (e.clientX - rect.left) * scaleX;
      var my = (e.clientY - rect.top) * scaleY;

      // Hit-test handles of selected layer first
      var sel = getSelectedLayer();
      if (sel && sel.visible && !sel.locked) {
        var hHit = hitTestHandles(sel, mx, my);
        if (hHit !== null) {
          isDragging = true;
          dragMode = (hHit === "rotate") ? "rotate" : "resize";
          dragHandleIdx = hHit;
          dragStartX = mx;
          dragStartY = my;
          origLayerSpec = JSON.parse(JSON.stringify(sel));
          return;
        }
      }

      // Hit-test layers top-to-bottom
      var hitLayer = null;
      for (var i = layers.length - 1; i >= 0; i--) {
        var l = layers[i];
        if (!l.visible) continue;
        if (pointInLayer(l, mx, my)) {
          hitLayer = l;
          break;
        }
      }

      if (hitLayer) {
        selectedLayerId = hitLayer.id;
        renderLayerList();
        syncInspectorFromSelected();
        renderCanvas();
        if (!hitLayer.locked) {
          isDragging = true;
          dragMode = "move";
          dragStartX = mx;
          dragStartY = my;
          origLayerSpec = JSON.parse(JSON.stringify(hitLayer));
        }
      } else {
        selectedLayerId = null;
        renderLayerList();
        syncInspectorFromSelected();
        renderCanvas();
      }
    });

    window.addEventListener("mousemove", function (e) {
      if (!isDragging || !origLayerSpec) return;
      var rect = freeformCanvas.getBoundingClientRect();
      var scaleX = canvasWidth / rect.width;
      var scaleY = canvasHeight / rect.height;
      var mx = (e.clientX - rect.left) * scaleX;
      var my = (e.clientY - rect.top) * scaleY;
      var dx = mx - dragStartX;
      var dy = my - dragStartY;

      var sel = getSelectedLayer();
      if (!sel) return;

      if (dragMode === "move") {
        sel.x = Math.round(origLayerSpec.x + dx);
        sel.y = Math.round(origLayerSpec.y + dy);
      } else if (dragMode === "resize") {
        applyResizeHandle(sel, origLayerSpec, dragHandleIdx, dx, dy, e.shiftKey);
      } else if (dragMode === "rotate") {
        var cx = origLayerSpec.x + origLayerSpec.width / 2;
        var cy = origLayerSpec.y + origLayerSpec.height / 2;
        var angle = Math.atan2(my - cy, mx - cx) * (180 / Math.PI) + 90;
        if (e.shiftKey) {
          angle = Math.round(angle / 15) * 15;
        }
        sel.rotation_deg = Math.round(angle);
      }

      syncInspectorFromSelected();
      renderCanvas();
    });

    window.addEventListener("mouseup", function () {
      if (isDragging) {
        isDragging = false;
        dragMode = null;
        origLayerSpec = null;
      }
    });

    function pointInLayer(layer, px, py) {
      var cx = layer.x + layer.width / 2;
      var cy = layer.y + layer.height / 2;
      var rad = (-layer.rotation_deg * Math.PI) / 180;
      var cos = Math.cos(rad);
      var sin = Math.sin(rad);
      var dx = px - cx;
      var dy = py - cy;
      var localX = cos * dx - sin * dy;
      var localY = sin * dx + cos * dy;
      return (
        localX >= -layer.width / 2 &&
        localX <= layer.width / 2 &&
        localY >= -layer.height / 2 &&
        localY <= layer.height / 2
      );
    }

    function hitTestHandles(layer, px, py) {
      var cx = layer.x + layer.width / 2;
      var cy = layer.y + layer.height / 2;
      var rad = (-layer.rotation_deg * Math.PI) / 180;
      var cos = Math.cos(rad);
      var sin = Math.sin(rad);
      var dx = px - cx;
      var dy = py - cy;
      var lx = cos * dx - sin * dy;
      var ly = sin * dx + cos * dy;

      var hw = layer.width / 2;
      var hh = layer.height / 2;
      var threshold = 12;

      // Rotation handle check
      if (Math.abs(lx) <= threshold && Math.abs(ly - (-hh - 20)) <= threshold) {
        return "rotate";
      }

      var handles = [
        [-hw, -hh], [0, -hh], [hw, -hh],
        [hw, 0], [hw, hh], [0, hh],
        [-hw, hh], [-hw, 0]
      ];
      for (var i = 0; i < handles.length; i++) {
        if (Math.abs(lx - handles[i][0]) <= threshold && Math.abs(ly - handles[i][1]) <= threshold) {
          return i;
        }
      }
      return null;
    }

    function applyResizeHandle(layer, orig, handleIdx, dx, dy, lockAspect) {
      var w = orig.width;
      var h = orig.height;
      var x = orig.x;
      var y = orig.y;

      if (handleIdx === 2 || handleIdx === 3 || handleIdx === 4) {
        w += dx;
      }
      if (handleIdx === 0 || handleIdx === 6 || handleIdx === 7) {
        w -= dx;
        x += dx;
      }
      if (handleIdx === 4 || handleIdx === 5 || handleIdx === 6) {
        h += dy;
      }
      if (handleIdx === 0 || handleIdx === 1 || handleIdx === 2) {
        h -= dy;
        y += dy;
      }

      layer.width = Math.max(10, Math.round(w));
      layer.height = Math.max(10, Math.round(h));
      layer.x = Math.round(x);
      layer.y = Math.round(y);
    }

    // Grid Preview Generator
    function updateGridPreview() {
      var imagePaths = layers.map(function (l) { return l.source_path; });
      if (!imagePaths.length) {
        gridPreviewContainer.innerHTML = '<div class="text-sm text-center text-muted">No collage preview yet. Add images to generate preview.</div>';
        return;
      }
      statusBar.textContent = "Rendering grid preview...";
      window.FOSS.api("collage_preview", {
        image_paths: imagePaths,
        columns: parseInt(colsSelect.value, 10) || 2,
        fit_mode: fitSelect.value,
        padding: parseInt(paddingInput.value, 10) || 12,
        corner_radius: parseInt(cornerRadiusInput.value, 10) || 0,
        bg_color: bgColor,
        transparent_bg: isTransparent,
        add_captions: captionsCheck.checked,
        watermark_text: watermarkInput.value.trim() || undefined
      }).then(function (res) {
        if (res && res.data_url) {
          gridPreviewContainer.innerHTML = "";
          var img = window.FOSS.dom.el("img", {
            src: res.data_url,
            alt: "Collage preview",
            className: "max-w-full h-auto rounded border border-border"
          });
          gridPreviewContainer.appendChild(img);
          statusBar.textContent = "Preview updated (" + imagePaths.length + " photos).";
        }
      });
    }

    // Export Logic
    function handleSave() {
      if (!layers.length) {
        showError("Please add images before saving collage.");
        return;
      }
      clearError();

      if (exportMode === "layered") {
        var fmt = layeredFormatSelect.value || "psd";
        var ext = "." + fmt;
        window.FOSS.api("select_save_path", {
          title: "Save Layered Composition",
          default_name: "layers_composition" + ext,
          file_types: [
            { name: fmt.toUpperCase() + " Project", extensions: [fmt] }
          ]
        }).then(function (res) {
          if (!res || res.cancelled || !(res.path || (res.paths && res.paths[0]))) return;
          var chosenPath = res.path || (res.paths && res.paths[0]);
          if (!chosenPath.toLowerCase().endsWith(ext)) {
            chosenPath = chosenPath + ext;
          }

          statusBar.textContent = "Exporting layered project...";
          window.FOSS.api("collage_export_freeform", {
            canvas_width: canvasWidth,
            canvas_height: canvasHeight,
            mode: "layered",
            format: fmt,
            output_path: chosenPath,
            transparent_bg: isTransparent,
            bg_color: bgColor,
            layers: layers.map(function (l) {
              return {
                layer_id: l.id,
                name: l.name,
                source_path: l.source_path,
                x: l.x,
                y: l.y,
                width: l.width,
                height: l.height,
                rotation_deg: l.rotation_deg,
                opacity: l.opacity,
                visible: l.visible,
                locked: l.locked
              };
            })
          }).then(function (createRes) {
            if (createRes && createRes.output_path) {
              statusBar.textContent = "Layers exported: " + createRes.output_path;
              showResult(createRes.output_path, "Layered Project Exported");
            } else {
              showError("Failed to export layered project.");
            }
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        });
        return;
      }

      var activeExportFormat = flatFormatSelect.value || "png";
      var defaultExt = activeExportFormat === "jpeg" ? ".jpg" : ".png";
      window.FOSS.api("select_save_path", {
        title: "Save Collage",
        default_name: "collage" + defaultExt,
        file_types: [
          { name: "Image (" + defaultExt + ")", extensions: [defaultExt.replace(".", "")] }
        ]
      }).then(function (res) {
        if (!res || res.cancelled || !res.path) return;
        var chosenPath = res.path;
        if (!chosenPath.toLowerCase().endsWith(defaultExt)) {
          chosenPath = chosenPath + defaultExt;
        }

        statusBar.textContent = "Exporting collage...";
        if (activeMode === "freeform") {
          window.FOSS.api("collage_export_freeform", {
            canvas_width: canvasWidth,
            canvas_height: canvasHeight,
            mode: "flattened",
            output_path: chosenPath,
            transparent_bg: isTransparent,
            bg_color: bgColor,
            layers: layers.map(function (l) {
              return {
                layer_id: l.id,
                name: l.name,
                source_path: l.source_path,
                x: l.x,
                y: l.y,
                width: l.width,
                height: l.height,
                rotation_deg: l.rotation_deg,
                opacity: l.opacity,
                visible: l.visible,
                locked: l.locked
              };
            })
          }).then(function (createRes) {
            if (createRes && createRes.output_path) {
              statusBar.textContent = "Collage saved: " + createRes.output_path;
              showResult(createRes.output_path, "Collage Saved Successfully");
            } else {
              showError("Failed to save collage.");
            }
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
          return;
        }

        var params = {
          image_paths: layers.map(function (l) { return l.source_path; }),
          output_path: chosenPath,
          columns: parseInt(colsSelect.value, 10) || 2,
          fit_mode: fitSelect.value,
          padding: parseInt(paddingInput.value, 10) || 12,
          corner_radius: parseInt(cornerRadiusInput.value, 10) || 0,
          bg_color: bgColor,
          transparent_bg: isTransparent,
          add_captions: captionsCheck.checked,
          watermark_text: watermarkInput.value.trim() || undefined
        };

        window.FOSS.api("collage_create", params).then(function (createRes) {
          if (createRes && createRes.output_path) {
            statusBar.textContent = "Collage saved: " + createRes.output_path;
            showResult(createRes.output_path, "Collage Saved Successfully");
          } else {
            showError("Failed to save collage.");
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      });
    }

    function handleExport() {
      handleSave();
    }

    renderLayerList();
    renderCanvas();
  }

  window.FOSS.router.register({
    id: "collage",
    title: "Collage & Layers Studio",
    navName: "Collage",
    category: "Visuals",
    icon: "grid",
    workbench: true,
    description: "Freeform multi-layer canvas with Z-ordering, transforms, grid collages, and layered PSD/ORA/ZIP export.",
    onFiles: function (paths) {
      if (!paths || !paths.length) return;
    },
    tabs: [
      { id: "main", label: "Collage Builder", render: renderMain }
    ]
  });
})();
