// Image Studio: AI Background Removal, Transformations, and Creative Media.
window.FOSS = window.FOSS || {};

(function () {
  function renderBackground(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var currentOriginalDataUrl = "";
    var currentCutoutDataUrl = "";
    var modelsCatalog = [];
    var modelsDir = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "AI Background Removal" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Local segmentation models. Models download once into your unified settings directory."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "images-bg-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "images-bg-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "images-bg-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "images-bg-result-card",
        title: titleText || "Background Removed",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Split container
    var split = window.FOSS.dom.el("div", {
      className: "split resizable images-workbench-split",
      "data-testid": "images-bg-split"
    });

    var sidebar = window.FOSS.dom.el("div", { className: "images-sidebar-pane" });
    var stage = window.FOSS.dom.el("div", { className: "images-stage-pane" });

    // Model Selector
    var modelSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "images-bg-model-select",
      "aria-label": "Background Removal Model",
      title: "Background Removal Model",
      style: "width: 100%;"
    });

    // Model Manager Card
    var modelManagerCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "images-model-manager",
      style: "width: 100%; font-size: var(--text-xs);"
    });

    var modelManagerHeader = window.FOSS.dom.el("div", {
      className: "row items-center justify-between",
      style: "gap: var(--space-2);"
    }, [
      window.FOSS.dom.el("span", { className: "font-semibold", text: "AI Models Storage" }),
      window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "data-testid": "images-open-models-dir-btn",
        text: "Open Folder",
        onClick: function () {
          if (modelsDir) {
            window.FOSS.api("open_path", { path: modelsDir });
          }
        }
      })
    ]);

    var modelListContainer = window.FOSS.dom.el("div", {
      style: "max-height: 12rem; overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-1);"
    });

    modelManagerCard.appendChild(modelManagerHeader);
    modelManagerCard.appendChild(modelListContainer);

    var modelBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral text-xs",
      "data-testid": "images-bg-model-badge",
      text: "Checking..."
    });

    function updateModelBadge() {
      var current = modelsCatalog.find(function (m) { return m.id === modelSelect.value; });
      var isDownloaded = !!(current && current.downloaded);
      modelBadge.className = "badge text-xs " + (isDownloaded ? "success" : "warning");
      modelBadge.textContent = current ? (isDownloaded ? "Downloaded" : "Pending download (" + current.download_size + ")") : "Unknown";
    }

    modelSelect.addEventListener("change", updateModelBadge);

    function refreshModelsList() {
      window.FOSS.api("images_models_status", {}).then(function (res) {
        if (!res || !res.models) return;
        modelsCatalog = res.models;
        modelsDir = res.models_dir || "";

        var previousVal = modelSelect.value;
        modelSelect.innerHTML = "";
        modelsCatalog.forEach(function (m) {
          var statusTag = m.downloaded ? "[Downloaded]" : "[Pending]";
          modelSelect.appendChild(window.FOSS.dom.el("option", {
            value: m.id,
            text: statusTag + " " + m.label + " - " + m.download_size
          }));
        });

        var preferred = window.FOSS.toolDefaults.get("images", "rembg_model", "u2net");
        var hasModel = function (id) { return modelsCatalog.some(function (m) { return m.id === id; }); };
        if (previousVal && hasModel(previousVal)) {
          modelSelect.value = previousVal;
        } else if (hasModel(preferred)) {
          modelSelect.value = preferred;
        }
        updateModelBadge();

        modelListContainer.innerHTML = "";
        modelsCatalog.forEach(function (m) {
          var mId = m.id;
          var mLabel = m.label;
          var mSize = m.download_size;
          var isDownloaded = !!m.downloaded;

          var row = window.FOSS.dom.el("div", {
            className: "row items-center justify-between",
            style: "padding: var(--space-1) 0; border-bottom: 1px solid var(--border);"
          });

          var labelCol = window.FOSS.dom.el("div", { className: "flex-col", style: "min-width: 0; flex: 1 1 0%;" }, [
            window.FOSS.dom.el("span", { className: "font-semibold truncate", text: mLabel }),
            window.FOSS.dom.el("span", { className: "text-muted text-xs", text: mSize })
          ]);

          var actionCol = window.FOSS.dom.el("div", { className: "row items-center gap-1" });
          if (isDownloaded) {
            var badge = window.FOSS.dom.el("span", { className: "badge success text-xs", text: "Downloaded" });
            var delBtn = window.FOSS.dom.el("button", {
              className: "btn btn-sm btn-ghost",
              "data-testid": "images-model-del-" + mId,
              text: "Delete",
              onClick: function () {
                statusBar.textContent = "Deleting model " + mId + "...";
                window.FOSS.api("images_delete_model", { model: mId }).then(function () {
                  statusBar.textContent = "Model " + mId + " deleted.";
                  refreshModelsList();
                }).catch(function (err) {
                  showError(err && err.message ? err.message : String(err));
                });
              }
            });
            actionCol.appendChild(badge);
            actionCol.appendChild(delBtn);
          } else {
            var badge = window.FOSS.dom.el("span", { className: "badge warning text-xs", text: "Pending" });
            var dlBtn = window.FOSS.dom.el("button", {
              className: "btn btn-sm btn-secondary",
              "data-testid": "images-model-dl-" + mId,
              text: "Download",
              onClick: function () {
                statusBar.textContent = "Downloading " + mLabel + "...";
                window.FOSS.api("images_download_model", { model: mId }).then(function () {
                  statusBar.textContent = "Downloaded " + mLabel + " successfully.";
                  refreshModelsList();
                }).catch(function (err) {
                  showError(err && err.message ? err.message : String(err));
                });
              }
            });
            actionCol.appendChild(badge);
            actionCol.appendChild(dlBtn);
          }

          row.appendChild(labelCol);
          row.appendChild(actionCol);
          modelListContainer.appendChild(row);
        });
      }).catch(function (err) {
        showError("Failed to query models: " + (err && err.message ? err.message : String(err)));
      });
    }

    refreshModelsList();

    // Stage elements
    var stageWrapper = window.FOSS.dom.el("div", {
      className: "images-stage-wrapper checkerboard-bg",
      "data-testid": "images-stage-wrapper"
    });

    var previewCutout = window.FOSS.dom.el("img", {
      className: "images-preview-img hidden",
      "data-testid": "images-cutout-preview",
      alt: "Cutout Preview"
    });

    var previewOriginal = window.FOSS.dom.el("img", {
      className: "images-preview-img hidden",
      "data-testid": "images-original-preview",
      alt: "Original Preview"
    });

    var emptyPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center",
      text: "Open an image to preview cutout or compare before/after."
    });

    stageWrapper.appendChild(emptyPlaceholder);
    stageWrapper.appendChild(previewCutout);
    stageWrapper.appendChild(previewOriginal);

    var viewMode = "cutout"; // cutout | original | both
    var viewModeToggle = window.FOSS.components.segmented({
      testid: "images-view-mode-toggle",
      items: [
        { id: "cutout", label: "Cutout" },
        { id: "original", label: "Original" },
        { id: "both", label: "Side-by-Side" }
      ],
      value: "cutout",
      onChange: function (val) {
        viewMode = val;
        updateStageView();
      }
    });

    function updateStageView() {
      if (!currentFile) {
        emptyPlaceholder.classList.remove("hidden");
        previewCutout.classList.add("hidden");
        previewOriginal.classList.add("hidden");
        return;
      }
      emptyPlaceholder.classList.add("hidden");
      if (viewMode === "original") {
        previewOriginal.classList.remove("hidden");
        previewCutout.classList.add("hidden");
      } else if (viewMode === "cutout") {
        previewOriginal.classList.add("hidden");
        if (currentCutoutDataUrl) {
          previewCutout.src = currentCutoutDataUrl;
          previewCutout.classList.remove("hidden");
        } else {
          previewOriginal.classList.remove("hidden");
        }
      } else {
        // Both
        previewOriginal.classList.remove("hidden");
        if (currentCutoutDataUrl) {
          previewCutout.src = currentCutoutDataUrl;
          previewCutout.classList.remove("hidden");
        }
      }
    }

    // File Picker
    var filePicker = window.FOSS.components.filePicker({
      testid: "images-bg-picker",
      title: "Select Image for Background Removal",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
        currentCutoutDataUrl = "";
        window.FOSS.api("images_load_data", { file_path: currentFile }).then(function (res) {
          if (res && res.data_url) {
            currentOriginalDataUrl = res.data_url;
            previewOriginal.src = currentOriginalDataUrl;
            updateStageView();
          }
        });
      },
      onClear: function () {
        currentFile = "";
        currentOriginalDataUrl = "";
        currentCutoutDataUrl = "";
        updateStageView();
      }
    });

    // Backdrop controls
    var backdropSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "images-backdrop-select",
      "aria-label": "Backdrop Type",
      title: "Backdrop Type",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("option", { value: "transparent", text: "Transparent (PNG)" }),
      window.FOSS.dom.el("option", { value: "solid", text: "Solid Color" }),
      window.FOSS.dom.el("option", { value: "blur", text: "Blurred Original Backdrop" })
    ]);

    var colorPicker = window.FOSS.dom.el("input", {
      type: "color",
      value: "#ffffff",
      className: "input",
      "data-testid": "images-backdrop-color",
      "aria-label": "Backdrop Color",
      title: "Backdrop Color",
      style: "width: 3rem; height: 2.2rem; padding: 0.1rem;"
    });

    var blurSlider = window.FOSS.dom.el("input", {
      type: "range",
      min: "5",
      max: "50",
      value: "25",
      className: "input",
      "data-testid": "images-backdrop-blur",
      "aria-label": "Backdrop Blur Radius",
      title: "Backdrop Blur Radius"
    });

    var backdropOptionsRow = window.FOSS.dom.el("div", {
      className: "row items-center gap-2 flex-wrap",
      style: "margin-top: var(--space-1);"
    }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Color:" }),
      colorPicker,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Blur:" }),
      blurSlider
    ]);

    function cutoutFileTypes() {
      var types = [{ name: "PNG Image (*.png)", extensions: ["png"] }];
      if (backdropSelect.value !== "transparent") {
        types.push({ name: "WebP Image (*.webp)", extensions: ["webp"] });
        types.push({ name: "JPEG Image (*.jpg)", extensions: ["jpg", "jpeg"] });
      }
      return types;
    }

    function promptCutoutPath() {
      return window.FOSS.api("select_save_path", {
        title: "Save Cutout",
        default_name: "cutout",
        file_types: cutoutFileTypes()
      }).then(function (res) {
        if (!res || res.cancelled) return "";
        return (res.path || (res.paths && res.paths[0]) || "").trim();
      });
    }

    // Primary action button
    var removeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "images-remove-bg-btn",
      "aria-label": "Remove Background",
      title: "Remove Background",
      onClick: function () {
        if (!currentFile) return showError("Select an image first.");
        clearError();
        promptCutoutPath().then(function (chosenPath) {
          if (!chosenPath) return;
          statusBar.textContent = "Removing background with " + modelSelect.value + "...";
          removeBtn.disabled = true;

          window.FOSS.api("images_remove_background", {
            file_path: currentFile,
            model: modelSelect.value,
            backdrop: backdropSelect.value,
            color: colorPicker.value,
            blur_radius: parseInt(blurSlider.value, 10) || 25,
            quality: window.FOSS.toolDefaults.get("images", "jpeg_quality", 85),
            output_path: chosenPath
          }).then(function (res) {
            removeBtn.disabled = false;
            if (res && res.data_url) {
              currentCutoutDataUrl = res.data_url;
              viewMode = "cutout";
              viewModeToggle.setValue("cutout");
              updateStageView();
              statusBar.textContent = "Background removed and saved to " + chosenPath;
              saveCutoutBtn.classList.remove("hidden");
              showResult(chosenPath, "Cutout Saved Successfully");
              refreshModelsList();
            }
          }).catch(function (err) {
            removeBtn.disabled = false;
            showError(err && err.message ? err.message : String(err));
          });
        });
      }
    }, [
      window.FOSS.icons.el("sparkles", 16),
      window.FOSS.dom.el("span", { text: "Remove Background" })
    ]);

    var saveCutoutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "images-save-cutout-btn",
      text: "Save Cutout...",
      onClick: function () {
        if (!currentCutoutDataUrl || !currentFile) return showError("Generate a cutout first.");
        promptCutoutPath().then(function (outP) {
          if (!outP) return;
          window.FOSS.api("images_save_preview", {
            data_url: currentCutoutDataUrl,
            output_path: outP,
            quality: window.FOSS.toolDefaults.get("images", "jpeg_quality", 85)
          }).then(function () {
            showResult(outP, "Cutout Saved");
            statusBar.textContent = "Saved to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        });
      }
    });

    var batchBgBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "images-batch-bg-btn",
      text: "Batch Removal...",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Select Images for Batch Background Removal",
          file_types: ["png", "jpg", "jpeg"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            window.FOSS.api("select_directory", { title: "Select Output Folder" }).then(function (dRes) {
              var outD = dRes && dRes.paths && dRes.paths.length > 0 ? dRes.paths[0] : "";
              if (!outD) return;
              statusBar.textContent = "Processing " + res.paths.length + " files...";
              window.FOSS.api("images_batch_process", {
                file_paths: res.paths,
                output_dir: outD,
                remove_background: true,
                bg_model: modelSelect.value
              }).then(function () {
                showResult(outD, "Batch Background Removal Complete");
                statusBar.textContent = "Batch processing complete.";
              }).catch(function (err) {
                showError(err && err.message ? err.message : String(err));
              });
            });
          }
        });
      }
    });

    var actionsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: "width: 100%;"
    }, [
      window.FOSS.components.field("AI Model", modelSelect),
      window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Model status:" }),
        modelBadge
      ]),
      window.FOSS.components.field("Backdrop", backdropSelect),
      backdropOptionsRow,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap", style: "margin-top: var(--space-2);" }, [
        removeBtn,
        saveCutoutBtn,
        batchBgBtn
      ])
    ]);

    sidebar.appendChild(filePicker.el);
    sidebar.appendChild(actionsCard);
    sidebar.appendChild(modelManagerCard);

    var stageHeader = window.FOSS.dom.el("div", {
      className: "row items-center justify-between flex-wrap gap-2",
      style: "margin-bottom: var(--space-1);"
    }, [
      window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: "Interactive Preview" }),
      viewModeToggle
    ]);

    stage.appendChild(stageHeader);
    stage.appendChild(stageWrapper);

    split.appendChild(sidebar);
    split.appendChild(window.FOSS.components.splitDivider({ vertical: true }));
    split.appendChild(stage);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);
  }

  function renderTransform(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var previewDataUrl = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Crop, Resize & Adjust" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Non-destructive image transformations. Saves as a new file without modifying originals."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "images-tf-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "images-tf-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var split = window.FOSS.dom.el("div", {
      className: "split resizable images-workbench-split",
      "data-testid": "images-tf-split"
    });

    var sidebar = window.FOSS.dom.el("div", { className: "images-sidebar-pane" });
    var stage = window.FOSS.dom.el("div", { className: "images-stage-pane" });

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "images-stage-wrapper checkerboard-bg",
      "data-testid": "images-tf-stage-wrapper"
    });

    var previewImg = window.FOSS.dom.el("img", {
      className: "images-preview-img hidden",
      "data-testid": "images-tf-preview",
      alt: "Transform Preview"
    });

    var emptyPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm",
      text: "Open an image to start transforming."
    });

    stageWrapper.appendChild(emptyPlaceholder);
    stageWrapper.appendChild(previewImg);

    function updatePreview(url) {
      if (url) {
        previewDataUrl = url;
        previewImg.src = url;
        previewImg.classList.remove("hidden");
        emptyPlaceholder.classList.add("hidden");
      }
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-tf-picker",
      title: "Select Image",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
        window.FOSS.api("images_load_data", { file_path: currentFile }).then(function (res) {
          if (res && res.data_url) {
            updatePreview(res.data_url);
            if (widthInput && res.width) widthInput.value = res.width;
            if (heightInput && res.height) heightInput.value = res.height;
          }
        });
      },
      onClear: function () {
        currentFile = "";
        previewDataUrl = "";
        previewImg.classList.add("hidden");
        emptyPlaceholder.classList.remove("hidden");
      }
    });

    // Transforms Card
    var transformsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: "width: 100%;"
    });

    // Rotation / Flip Buttons
    var rotFlipRow = window.FOSS.dom.el("div", { className: "row gap-1 items-center flex-wrap" }, [
      window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "data-testid": "images-rotate-ccw",
        text: "Rotate 90 CCW",
        onClick: function () {
          if (!currentFile) return showError("Open an image first.");
          window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 270 }).then(function (res) {
            if (res && res.data_url) updatePreview(res.data_url);
          });
        }
      }),
      window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "data-testid": "images-rotate-cw",
        text: "Rotate 90 CW",
        onClick: function () {
          if (!currentFile) return showError("Open an image first.");
          window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 90 }).then(function (res) {
            if (res && res.data_url) updatePreview(res.data_url);
          });
        }
      }),
      window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "data-testid": "images-flip-h",
        text: "Flip H",
        onClick: function () {
          if (!currentFile) return showError("Open an image first.");
          window.FOSS.api("images_flip", { file_path: currentFile, direction: "horizontal" }).then(function (res) {
            if (res && res.data_url) updatePreview(res.data_url);
          });
        }
      }),
      window.FOSS.dom.el("button", {
        className: "btn btn-sm",
        "data-testid": "images-flip-v",
        text: "Flip V",
        onClick: function () {
          if (!currentFile) return showError("Open an image first.");
          window.FOSS.api("images_flip", { file_path: currentFile, direction: "vertical" }).then(function (res) {
            if (res && res.data_url) updatePreview(res.data_url);
          });
        }
      })
    ]);

    // Resize controls
    var widthInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      placeholder: "Width",
      "aria-label": "Width",
      title: "Width",
      style: "width: 5rem;"
    });
    var heightInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      placeholder: "Height",
      "aria-label": "Height",
      title: "Height",
      style: "width: 5rem;"
    });
    var resizeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "images-resize-btn",
      text: "Resize",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        var w = parseInt(widthInput.value, 10);
        var h = parseInt(heightInput.value, 10);
        if (!w || !h) return showError("Enter valid dimensions.");
        window.FOSS.api("images_resize", { file_path: currentFile, width: w, height: h }).then(function (res) {
          if (res && res.data_url) updatePreview(res.data_url);
        });
      }
    });

    var circleCropBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "images-circle-crop",
      text: "Circle Crop",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_circle_crop", { file_path: currentFile }).then(function (res) {
          if (res && res.data_url) updatePreview(res.data_url);
        });
      }
    });

    var resizeRow = window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
      widthInput,
      window.FOSS.dom.el("span", { text: "x" }),
      heightInput,
      resizeBtn,
      circleCropBtn
    ]);

    // Adjustment sliders
    var brightSlider = window.FOSS.dom.el("input", {
      type: "range",
      min: "20",
      max: "200",
      value: "100",
      className: "input",
      "aria-label": "Brightness",
      title: "Brightness"
    });
    var contrastSlider = window.FOSS.dom.el("input", {
      type: "range",
      min: "20",
      max: "200",
      value: "100",
      className: "input",
      "aria-label": "Contrast",
      title: "Contrast"
    });
    var satSlider = window.FOSS.dom.el("input", {
      type: "range",
      min: "0",
      max: "200",
      value: "100",
      className: "input",
      "aria-label": "Saturation",
      title: "Saturation"
    });

    function applyAdjustments() {
      if (!currentFile) return;
      window.FOSS.api("images_adjust", {
        file_path: currentFile,
        brightness: parseInt(brightSlider.value, 10),
        contrast: parseInt(contrastSlider.value, 10),
        saturation: parseInt(satSlider.value, 10)
      }).then(function (res) {
        if (res && res.data_url) updatePreview(res.data_url);
      });
    }

    brightSlider.addEventListener("change", applyAdjustments);
    contrastSlider.addEventListener("change", applyAdjustments);
    satSlider.addEventListener("change", applyAdjustments);

    var autoEnhanceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "images-auto-enhance",
      text: "Auto Enhance",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_auto_enhance", { file_path: currentFile }).then(function (res) {
          if (res && res.data_url) updatePreview(res.data_url);
        });
      }
    });

    // Filter presets
    var filterSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "images-filter-select",
      "aria-label": "Filter Preset",
      title: "Filter Preset",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("option", { value: "Auto Enhance", text: "Auto Enhance" }),
      window.FOSS.dom.el("option", { value: "Vivid", text: "Vivid" }),
      window.FOSS.dom.el("option", { value: "Warm Tone", text: "Warm Tone" }),
      window.FOSS.dom.el("option", { value: "Cool Tone", text: "Cool Tone" }),
      window.FOSS.dom.el("option", { value: "Grayscale", text: "Grayscale" })
    ]);

    var applyFilterBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      text: "Apply Filter",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_apply_filter", { file_path: currentFile, filter_name: filterSelect.value }).then(function (res) {
          if (res && res.data_url) updatePreview(res.data_url);
        });
      }
    });

    var SAVE_TYPES = {
      png: { name: "PNG Image (*.png)", extensions: ["png"] },
      webp: { name: "WebP Image (*.webp)", extensions: ["webp"] },
      jpeg: { name: "JPEG Image (*.jpg)", extensions: ["jpg", "jpeg"] }
    };

    var qualityInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      min: "1",
      max: "100",
      value: String(window.FOSS.toolDefaults.get("images", "jpeg_quality", 85)),
      "data-testid": "images-tf-quality",
      "aria-label": "JPEG and WebP quality",
      title: "JPEG and WebP quality",
      style: "width: 5rem;"
    });

    // Save the preview shown on stage as a new file in the chosen format
    var saveCopyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "images-tf-save",
      text: "Save Copy As...",
      onClick: function () {
        if (!currentFile || !previewDataUrl) return showError("Open an image first.");
        var preferred = String(window.FOSS.toolDefaults.get("images", "export_format", "webp"));
        var order = [preferred].concat(Object.keys(SAVE_TYPES).filter(function (key) { return key !== preferred; }));
        window.FOSS.api("select_save_path", {
          title: "Save Transformed Image",
          default_name: "transformed",
          file_types: order.map(function (key) { return SAVE_TYPES[key]; })
        }).then(function (res) {
          if (!res || res.cancelled) return;
          var outP = (res && res.path) || (res && res.paths && res.paths.length > 0 ? res.paths[0] : "");
          if (!outP) return;
          window.FOSS.api("images_save_preview", {
            data_url: previewDataUrl,
            output_path: outP,
            quality: parseInt(qualityInput.value, 10) || 85
          }).then(function () {
            statusBar.textContent = "Saved to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        });
      }
    });

    transformsCard.appendChild(window.FOSS.dom.el("span", { className: "font-semibold text-xs", text: "Transformations" }));
    transformsCard.appendChild(rotFlipRow);
    transformsCard.appendChild(resizeRow);
    transformsCard.appendChild(window.FOSS.dom.el("span", { className: "font-semibold text-xs", text: "Adjustments" }));
    transformsCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Brightness:" }),
      brightSlider,
      autoEnhanceBtn
    ]));
    transformsCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Contrast:" }),
      contrastSlider
    ]));
    transformsCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Saturation:" }),
      satSlider
    ]));
    transformsCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2", style: "margin-top: var(--space-1);" }, [
      filterSelect,
      applyFilterBtn
    ]));
    transformsCard.appendChild(window.FOSS.dom.el("div", { className: "row items-center gap-2", style: "margin-top: var(--space-2);" }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Quality:" }),
      qualityInput,
      saveCopyBtn
    ]));

    sidebar.appendChild(filePicker.el);
    sidebar.appendChild(transformsCard);

    stage.appendChild(stageWrapper);

    split.appendChild(sidebar);
    split.appendChild(window.FOSS.components.splitDivider({ vertical: true }));
    split.appendChild(stage);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(split);
  }

  function renderCreative(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "GIF & ASCII Art" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Create and extract animated GIFs, or generate ASCII art text from photos."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "images-cr-status",
      text: "Ready"
    });

    var asciiPre = window.FOSS.dom.el("pre", {
      className: "code-block",
      "data-testid": "images-ascii-preview",
      style: "font-family: monospace; white-space: pre; overflow: auto; max-height: 24rem; font-size: 0.5rem; line-height: 1;"
    });

    var charsetSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "images-ascii-charset",
      "aria-label": "ASCII Character Set",
      title: "ASCII Character Set",
      style: "width: 10rem;"
    }, [
      window.FOSS.dom.el("option", { value: "standard", text: "Standard" }),
      window.FOSS.dom.el("option", { value: "detailed", text: "Detailed" }),
      window.FOSS.dom.el("option", { value: "blocks", text: "Blocks" }),
      window.FOSS.dom.el("option", { value: "minimal", text: "Minimal" })
    ]);

    var widthInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      value: "80",
      "aria-label": "ASCII Columns Width",
      title: "ASCII Columns Width",
      style: "width: 5rem;"
    });

    var generateAsciiBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "images-ascii-gen-btn",
      text: "Generate ASCII Art",
      onClick: function () {
        if (!currentFile) return;
        statusBar.textContent = "Rendering ASCII art...";
        window.FOSS.api("images_to_ascii", {
          file_path: currentFile,
          columns: parseInt(widthInput.value, 10) || 80,
          charset: charsetSelect.value
        }).then(function (res) {
          if (res && res.ascii) {
            asciiPre.textContent = res.ascii;
            statusBar.textContent = "ASCII art rendered.";
          }
        });
      }
    });

    var saveAsciiBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "images-ascii-save-btn",
      text: "Save .txt...",
      onClick: function () {
        if (!asciiPre.textContent) return;
        window.FOSS.api("select_save_path", {
          title: "Save ASCII Art",
          default_name: "ascii_art",
          file_types: [{ name: "Text File (*.txt)", extensions: ["txt"] }]
        }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          window.FOSS.api("write_text_file", { path: outP, content: asciiPre.textContent }).then(function () {
            statusBar.textContent = "Saved to " + outP;
          });
        });
      }
    });

    var asciiCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: "ASCII Art Generator" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Preset:" }),
        charsetSelect,
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Width:" }),
        widthInput,
        generateAsciiBtn,
        saveAsciiBtn
      ]),
      asciiPre
    ]);

    // GIF tools card
    var gifCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: "width: 100%; margin-top: var(--space-3);"
    }, [
      window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: "GIF Studio" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        window.FOSS.dom.el("button", {
          className: "btn",
          "data-testid": "images-gif-extract-btn",
          text: "Extract GIF Frames...",
          onClick: function () {
            window.FOSS.api("select_files", {
              title: "Select Animated GIF",
              file_types: ["gif"]
            }).then(function (fRes) {
              if (!fRes || !fRes.paths || fRes.paths.length === 0) return;
              var gifP = fRes.paths[0];
              window.FOSS.api("select_directory", { title: "Select Destination Directory for Frames" }).then(function (dRes) {
                var outD = dRes && dRes.paths && dRes.paths.length > 0 ? dRes.paths[0] : "";
                if (!outD) return;
                statusBar.textContent = "Extracting frames...";
                window.FOSS.api("images_gif_ops", {
                  action: "extract",
                  file_path: gifP,
                  output_dir: outD
                }).then(function (res) {
                  statusBar.textContent = "Extracted " + (res && res.count ? res.count : "all") + " frames to " + outD;
                });
              });
            });
          }
        }),
        window.FOSS.dom.el("button", {
          className: "btn",
          "data-testid": "images-gif-create-btn",
          text: "Create GIF from Images...",
          onClick: function () {
            window.FOSS.api("select_files", {
              title: "Select Ordered Frame Images",
              file_types: ["png", "jpg", "jpeg"]
            }).then(function (fRes) {
              if (!fRes || !fRes.paths || fRes.paths.length === 0) return;
              var framePaths = fRes.paths;
              window.FOSS.api("select_save_path", {
                title: "Save Animated GIF",
                default_name: "animation",
                file_types: [{ name: "GIF Animation (*.gif)", extensions: ["gif"] }]
              }).then(function (sRes) {
                var outP = sRes && sRes.paths && sRes.paths.length > 0 ? sRes.paths[0] : "";
                if (!outP) return;
                statusBar.textContent = "Assembling GIF...";
                window.FOSS.api("images_gif_ops", {
                  action: "create",
                  frame_paths: framePaths,
                  output_path: outP,
                  fps: 10
                }).then(function () {
                  statusBar.textContent = "Created animated GIF at " + outP;
                });
              });
            });
          }
        })
      ])
    ]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-cr-picker",
      title: "Select Image for ASCII Art",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
      },
      onClear: function () {
        currentFile = "";
        asciiPre.textContent = "";
      }
    });

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(filePicker.el);
    panel.appendChild(asciiCard);
    panel.appendChild(gifCard);
  }

  window.FOSS.router.register({
    id: "images",
    title: "Image Studio",
    navName: "Images",
    category: "Visuals",
    icon: "images",
    workbench: true,
    defaults: [
      {
        key: "rembg_model",
        label: "Default background removal model",
        type: "select",
        options: ["u2net", "u2netp", "silueta", "isnet-general-use", "u2net_human_seg", "birefnet-general-lite", "bria-rmbg"],
        default: "u2net"
      },
      { key: "export_format", label: "Default export format", type: "select", options: ["png", "webp", "jpeg"], default: "webp" },
      { key: "jpeg_quality", label: "Default JPEG quality", type: "number", min: 1, max: 100, step: 1, default: 85 }
    ],
    tabs: [
      { id: "background", label: "Background", render: renderBackground },
      { id: "transform", label: "Transform", render: renderTransform },
      { id: "creative", label: "Creative", render: renderCreative }
    ]
  });
})();
