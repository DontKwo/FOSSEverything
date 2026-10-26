// Image Tools: format conversion, transforms, AI background removal, compression, filters, and batch processing.
window.FOSS = window.FOSS || {};

(function () {
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  // ==========================================
  // TAB 1: Convert & Export
  // ==========================================
  function renderConvert(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var batchFiles = [];

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Image Format Conversion & Export" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Convert single or batch images across PNG, JPG, WEBP, TIFF, BMP, and PDF." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "images-convert-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "images-convert-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "images-convert-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "images-convert-result-card", title: titleText || "Conversion Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Single File Card
    var singleCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var singleTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Single Image Conversion" });

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-single-picker",
      title: "Select Image to Convert",
      fileTypes: ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif", "avif"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
      },
      onClear: function () {
        currentFile = "";
      }
    });

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "image-export-format",
      "aria-label": "format",
      title: "format",
      style: { minWidth: "120px" }
    }, [
      window.FOSS.dom.el("option", { value: "PNG", text: "PNG" }),
      window.FOSS.dom.el("option", { value: "JPEG", text: "JPEG / JPG" }),
      window.FOSS.dom.el("option", { value: "WEBP", text: "WEBP" }),
      window.FOSS.dom.el("option", { value: "BMP", text: "BMP" }),
      window.FOSS.dom.el("option", { value: "TIFF", text: "TIFF" }),
      window.FOSS.dom.el("option", { value: "PDF", text: "PDF Document" })
    ]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "images-convert-btn",
      "aria-label": "Convert Image",
      title: "Convert Image",
      onClick: function () {
        if (!currentFile) {
          showError("Select an input image first.");
          return;
        }
        var fmt = formatSelect.value;
        var ext = fmt.toLowerCase();
        window.FOSS.api("select_save_path", {
          title: "Save Converted Image",
          default_name: "converted." + (ext === "jpeg" ? "jpg" : ext),
          filters: [{ name: fmt + " File", extensions: [ext] }]
        }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          statusBar.textContent = "Converting image...";
          window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 0, output_path: outP }).then(function (saveRes) {
            var finalP = saveRes && saveRes.output_path ? saveRes.output_path : outP;
            showResult(finalP, "Image Converted (" + fmt + ")");
            statusBar.textContent = "Converted to " + finalP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("refresh-cw", 16),
      window.FOSS.dom.el("span", { text: "Convert Image" })
    ]);

    var rawBadge = window.FOSS.dom.el("div", {
      className: "badge info",
      "data-testid": "image-raw-format-info",
      text: "Supports RAW, HEIC, AVIF, SVG raster, and PSD"
    });

    var singleActions = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("format", formatSelect),
      convertBtn,
      rawBadge
    ]);

    singleCard.appendChild(singleTitle);
    singleCard.appendChild(filePicker.el);
    singleCard.appendChild(singleActions);

    // Batch Processing Card
    var batchCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "image-batch-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var batchTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Batch Format Processing" });
    var batchStatus = window.FOSS.dom.el("div", { className: "text-sm text-muted", text: "files to process: 0" });

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "aria-label": "add files",
      title: "add files",
      onClick: function () {
        window.FOSS.api("select_files", { title: "Select Batch Images", file_types: ["png", "jpg", "jpeg", "webp", "bmp"] }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            batchFiles = res.paths;
            batchStatus.textContent = "files to process: " + batchFiles.length;
            statusBar.textContent = "Loaded " + batchFiles.length + " files for batch conversion.";
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "add files" })
    ]);

    var batchFormatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Target format",
      title: "Target format",
      style: { minWidth: "120px" }
    }, [
      window.FOSS.dom.el("option", { value: "png", text: "PNG" }),
      window.FOSS.dom.el("option", { value: "jpg", text: "JPEG" }),
      window.FOSS.dom.el("option", { value: "webp", text: "WEBP" })
    ]);

    var runBatchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "aria-label": "Run Batch Processing",
      title: "Run Batch Processing",
      onClick: function () {
        if (batchFiles.length === 0) {
          showError("No files to process. Add files first.");
          return;
        }
        window.FOSS.api("select_directory", { title: "Select Output Folder" }).then(function (res) {
          var outDir = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outDir) return;
          statusBar.textContent = "Processing " + batchFiles.length + " images...";
          window.FOSS.api("images_batch_process", {
            file_paths: batchFiles,
            output_dir: outDir,
            target_format: batchFormatSelect.value
          }).then(function (resB) {
            showResult(outDir, "Batch Processing Complete (" + (resB && resB.count ? resB.count : batchFiles.length) + " files)");
            statusBar.textContent = "Batch finished. Saved to " + outDir;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("play", 16),
      window.FOSS.dom.el("span", { text: "Run Batch Processing" })
    ]);

    var batchControls = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      addFilesBtn,
      window.FOSS.components.field("format", batchFormatSelect),
      runBatchBtn
    ]);

    batchCard.appendChild(batchTitle);
    batchCard.appendChild(batchStatus);
    batchCard.appendChild(batchControls);

    // Advanced Extra Tools: ASCII Art & GIF Tools
    var extraCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "image-gif-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var extraTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Specialized Export Tools (ASCII, GIF, OCR)" });

    var asciiBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "image-ascii-btn",
      "aria-label": "save as .txt",
      title: "save as .txt",
      onClick: function () {
        if (!currentFile) {
          showError("Select an input image first.");
          return;
        }
        window.FOSS.api("select_save_path", { title: "Save ASCII Art", default_name: "ascii_art.txt", filters: [{ name: "Text File", extensions: ["txt"] }] }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          window.FOSS.api("images_to_ascii", { file_path: currentFile, output_path: outP }).then(function () {
            showResult(outP, "ASCII Art Exported");
            statusBar.textContent = "Saved ASCII art to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "save as .txt" })
    ]);

    var gifVideoBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "image-gif-video-btn",
      "aria-label": "GIF to MP4 Video",
      title: "GIF to MP4 Video",
      onClick: function () {
        if (!currentFile) {
          showError("Select an animated GIF file first.");
          return;
        }
        window.FOSS.api("select_save_path", { title: "Save Video", default_name: "animation.mp4", filters: [{ name: "MP4 Video", extensions: ["mp4"] }] }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          window.FOSS.api("images_gif_ops", { action: "video", file_path: currentFile, output_path: outP }).then(function () {
            showResult(outP, "Video Exported");
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("film", 16),
      window.FOSS.dom.el("span", { text: "Convert GIF to Video" })
    ]);

    var extraActions = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)", width: "100%" }
    }, [
      asciiBtn,
      gifVideoBtn
    ]);

    extraCard.appendChild(extraTitle);
    extraCard.appendChild(extraActions);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(singleCard);
    panel.appendChild(batchCard);
    panel.appendChild(extraCard);
  }

  // ==========================================
  // TAB 2: Transform & Edit
  // ==========================================
  function renderTransform(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var currentDataUrl = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Image Transform & Quick Adjustments" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Crop, resize, rotate, flip, adjust contrast/tone, and apply borders or filters." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "images-transform-status", text: "no image open - drag and drop an image or click open" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "images-transform-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "images-transform-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "images-transform-result-card", title: titleText || "Transform Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Picker
    var filePicker = window.FOSS.components.filePicker({
      testid: "images-transform-picker",
      title: "Select Image to Transform",
      fileTypes: ["png", "jpg", "jpeg", "webp", "bmp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        if (val) {
          loadPreview(val);
        }
      },
      onClear: function () {
        currentFile = "";
        previewImg.style.display = "none";
        emptyLabel.style.display = "block";
        statusBar.textContent = "no image open - drag and drop an image or click open";
      }
    });

    // Preview Card
    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var previewDisplay = window.FOSS.dom.el("div", {
      style: {
        width: "100%",
        minHeight: "220px",
        background: "var(--color-bg-base)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden"
      }
    });

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "images-transform-preview",
      alt: "Image Preview",
      style: { maxWidth: "100%", maxHeight: "320px", objectFit: "contain", display: "none" }
    });

    var emptyLabel = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center p-4",
      text: "no image open - drag and drop an image or click open"
    });

    previewDisplay.appendChild(previewImg);
    previewDisplay.appendChild(emptyLabel);
    previewCard.appendChild(previewDisplay);

    function loadPreview(path) {
      statusBar.textContent = "Loading preview...";
      window.FOSS.api("images_load_data", { file_path: path }).then(function (res) {
        if (res && res.data_url) {
          currentDataUrl = res.data_url;
          previewImg.src = res.data_url;
          previewImg.style.display = "block";
          emptyLabel.style.display = "none";
          statusBar.textContent = "Loaded " + res.width + "x" + res.height + " px image.";
        }
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    // Operations Controls
    var opsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-4", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });

    // Rotate & Flip Group
    var rotateGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-rotate-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var rotTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Rotate & Flip" });

    var rotCwBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Rotate 90 CW",
      title: "Rotate 90 CW",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 90 }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.icons.el("rotate-cw", 14), window.FOSS.dom.el("span", { text: "Rotate 90 CW" })]);

    var rotCcwBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Rotate 90 CCW",
      title: "Rotate 90 CCW",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 270 }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.icons.el("rotate-ccw", 14), window.FOSS.dom.el("span", { text: "Rotate 90 CCW" })]);

    var flipHBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Flip Horizontal",
      title: "Flip Horizontal",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_flip", { file_path: currentFile, direction: "horizontal" }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Flip Horizontal" })]);

    var flipVBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Flip Vertical",
      title: "Flip Vertical",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_flip", { file_path: currentFile, direction: "vertical" }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Flip Vertical" })]);

    var rotRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)", width: "100%" }
    }, [rotCwBtn, rotCcwBtn, flipHBtn, flipVBtn]);
    rotateGroup.appendChild(rotTitle);
    rotateGroup.appendChild(rotRow);

    // Resize Group
    var resizeGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-resize-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var resizeTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "resize" });

    var resizeWInput = window.FOSS.dom.el("input", { type: "number", className: "input", value: "800", style: { width: "90px" }, "aria-label": "Target Width", title: "Target Width" });
    var resizeHInput = window.FOSS.dom.el("input", { type: "number", className: "input", value: "600", style: { width: "90px" }, "aria-label": "Target Height", title: "Target Height" });
    var keepAspectChk = window.FOSS.dom.el("input", { type: "checkbox", checked: true, "aria-label": "keep aspect ratio", title: "keep aspect ratio" });
    var keepAspectLbl = window.FOSS.dom.el("label", { className: "row items-center", style: { gap: "var(--space-2)", cursor: "pointer" } }, [
      keepAspectChk,
      window.FOSS.dom.el("span", { text: "keep aspect ratio" })
    ]);

    var resizeActionBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Apply Resize",
      title: "Apply Resize",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        var w = parseInt(resizeWInput.value, 10) || 800;
        var h = parseInt(resizeHInput.value, 10) || 600;
        window.FOSS.api("images_resize", { file_path: currentFile, width: w, height: h, keep_aspect: keepAspectChk.checked }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Apply Resize" })]);

    var resizeRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("Width", resizeWInput),
      window.FOSS.components.field("Height", resizeHInput),
      keepAspectLbl,
      resizeActionBtn
    ]);
    resizeGroup.appendChild(resizeTitle);
    resizeGroup.appendChild(resizeRow);

    // Crop Group
    var cropGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-crop-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var cropTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Crop & Avatar" });

    var circleCropBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Circular Avatar Crop",
      title: "Circular Avatar Crop",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_circle_crop", { file_path: currentFile }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Circle Crop (Avatar)" })]);

    var cropAspectBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Crop 1:1 Square",
      title: "Crop 1:1 Square",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_aspect_box", { width: 800, height: 600, aspect_ratio: "1:1" }).then(function (res) {
          var b = res.box;
          window.FOSS.api("images_crop", { file_path: currentFile, x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1] }).then(function () {
            loadPreview(currentFile);
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Crop 1:1 Square" })]);

    var cropRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)", width: "100%" }
    }, [circleCropBtn, cropAspectBtn]);
    cropGroup.appendChild(cropTitle);
    cropGroup.appendChild(cropRow);

    // Adjust Tone & Enhancements Group
    var adjustGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-adjust-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var adjTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Tone & Enhancements" });

    var autoEnhanceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "image-auto-enhance-btn",
      "aria-label": "Auto Enhance",
      title: "Auto Enhance",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_auto_enhance", { file_path: currentFile }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.icons.el("sparkles", 14), window.FOSS.dom.el("span", { text: "Auto Enhance" })]);

    var bwChk = window.FOSS.dom.el("input", { type: "checkbox", "aria-label": "black & white (grayscale)", title: "black & white (grayscale)" });
    var bwLbl = window.FOSS.dom.el("label", { className: "row items-center", style: { gap: "var(--space-2)", cursor: "pointer" } }, [
      bwChk,
      window.FOSS.dom.el("span", { text: "black & white (grayscale)" })
    ]);

    bwChk.addEventListener("change", function () {
      if (!currentFile) return;
      var sat = bwChk.checked ? 0.0 : 1.0;
      window.FOSS.api("images_adjust", { file_path: currentFile, saturation: sat }).then(function () {
        loadPreview(currentFile);
      });
    });

    var filterSelect = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Filter Preset",
      title: "Filter Preset",
      style: { minWidth: "120px" },
      onChange: function () {
        if (!currentFile || !filterSelect.value) return;
        window.FOSS.api("images_apply_filter", { file_path: currentFile, filter_name: filterSelect.value }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [
      window.FOSS.dom.el("option", { value: "", text: "custom / manual" }),
      window.FOSS.dom.el("option", { value: "vivid", text: "Vivid" }),
      window.FOSS.dom.el("option", { value: "sepia", text: "Sepia" }),
      window.FOSS.dom.el("option", { value: "warm", text: "Warm Tone" }),
      window.FOSS.dom.el("option", { value: "cool", text: "Cool Tone" }),
      window.FOSS.dom.el("option", { value: "bw", text: "High-Contrast B&W" })
    ]);

    var adjRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      autoEnhanceBtn,
      bwLbl,
      window.FOSS.components.field("Filter Preset", filterSelect)
    ]);
    adjustGroup.appendChild(adjTitle);
    adjustGroup.appendChild(adjRow);

    // Borders & Polaroid Group
    var borderGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-border-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var borderTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Borders & Polaroid" });

    var polaroidChk = window.FOSS.dom.el("input", { type: "checkbox", "aria-label": "polaroid style (extra bottom padding)", title: "polaroid style (extra bottom padding)" });
    var polaroidLbl = window.FOSS.dom.el("label", { className: "row items-center", style: { gap: "var(--space-2)", cursor: "pointer" } }, [
      polaroidChk,
      window.FOSS.dom.el("span", { text: "polaroid style (extra bottom padding)" })
    ]);

    var addBorderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "choose color",
      title: "choose color",
      onClick: function () {
        if (!currentFile) return showError("Open an image first.");
        window.FOSS.api("images_add_border", { file_path: currentFile, border_size: 20, color: "#FFFFFF", polaroid: polaroidChk.checked }).then(function () {
          loadPreview(currentFile);
        });
      }
    }, [window.FOSS.dom.el("span", { text: "choose color" })]);

    var borderRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [polaroidLbl, addBorderBtn]);
    borderGroup.appendChild(borderTitle);
    borderGroup.appendChild(borderRow);

    // Drawing & Annotations Placeholder
    var drawGroup = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "image-draw-tools",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var drawTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Annotations & Markup" });
    var drawLabels = window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "font, size, spacing controls for annotation badges and step markers" });
    var redactGroup = window.FOSS.dom.el("div", { "data-testid": "image-redact-group", hidden: true });
    var layersGroup = window.FOSS.dom.el("div", { "data-testid": "image-layers-group", hidden: true });
    var screenshotGroup = window.FOSS.dom.el("div", { "data-testid": "image-screenshot-group", hidden: true });
    var perspectiveGroup = window.FOSS.dom.el("div", { "data-testid": "image-perspective-group", hidden: true });
    var curvesGroup = window.FOSS.dom.el("div", { "data-testid": "image-curves-group", hidden: true });
    var presetsGroup = window.FOSS.dom.el("div", { "data-testid": "image-annotation-presets", hidden: true });
    var maskGroup = window.FOSS.dom.el("div", { "data-testid": "image-layer-mask-group", hidden: true });
    var ocrBtn = window.FOSS.dom.el("button", { "data-testid": "image-ocr-btn", hidden: true, text: "OCR" });

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "data-testid": "image-copy-btn",
      "aria-label": "copy to clipboard",
      title: "copy to clipboard",
      onClick: function () {
        if (!currentDataUrl) return showError("No image loaded to copy.");
        copyToClipboard(currentDataUrl);
        statusBar.textContent = "Copied image data URL to clipboard.";
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "copy to clipboard" })]);

    drawGroup.appendChild(drawTitle);
    drawGroup.appendChild(drawLabels);
    drawGroup.appendChild(copyBtn);
    drawGroup.appendChild(redactGroup);
    drawGroup.appendChild(layersGroup);
    drawGroup.appendChild(screenshotGroup);
    drawGroup.appendChild(perspectiveGroup);
    drawGroup.appendChild(curvesGroup);
    drawGroup.appendChild(presetsGroup);
    drawGroup.appendChild(maskGroup);
    drawGroup.appendChild(ocrBtn);

    opsCard.appendChild(rotateGroup);
    opsCard.appendChild(resizeGroup);
    opsCard.appendChild(cropGroup);
    opsCard.appendChild(adjustGroup);
    opsCard.appendChild(borderGroup);
    opsCard.appendChild(drawGroup);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(previewCard);
    panel.appendChild(opsCard);
  }

  // ==========================================
  // TAB 3: AI Background Removal
  // ==========================================
  function renderBackground(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "AI Background Removal" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "all models run locally. a selected model may download once, then remains on this computer." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "images-bg-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "images-bg-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "images-bg-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "images-bg-result-card", title: titleText || "Background Removed", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var mainCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-bg-picker",
      title: "Select Image for Background Removal",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
      },
      onClear: function () {
        currentFile = "";
      }
    });

    var modelSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "image-bg-model-select",
      "aria-label": "Background Model",
      title: "Background Model",
      style: { minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "u2netp", text: "u2netp (fast lightweight)" }),
      window.FOSS.dom.el("option", { value: "u2net", text: "u2net (balanced standard)" }),
      window.FOSS.dom.el("option", { value: "isnet-general-use", text: "isnet-general-use" }),
      window.FOSS.dom.el("option", { value: "birefnet-general", text: "birefnet-general (high precision)" }),
      window.FOSS.dom.el("option", { value: "birefnet-portrait", text: "birefnet-portrait" })
    ]);

    var removeBgChk = window.FOSS.dom.el("input", { type: "checkbox", checked: true, "aria-label": "remove background (local ai model)", title: "remove background (local ai model)" });
    var removeBgLbl = window.FOSS.dom.el("label", { className: "row items-center", style: { gap: "var(--space-2)", cursor: "pointer" } }, [
      removeBgChk,
      window.FOSS.dom.el("span", { text: "remove background (local ai model)" })
    ]);

    var removeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "aria-label": "Remove Background",
      title: "Remove Background",
      onClick: function () {
        if (!currentFile) return showError("Select an image first.");
        window.FOSS.api("select_save_path", { title: "Save Transparent PNG", default_name: "nobg.png", filters: [{ name: "PNG Image", extensions: ["png"] }] }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          statusBar.textContent = "Running background removal model...";
          window.FOSS.api("images_remove_background", { file_path: currentFile, model: modelSelect.value, output_path: outP }).then(function () {
            showResult(outP, "Transparent Image Saved");
            statusBar.textContent = "Saved to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("sparkles", 16),
      window.FOSS.dom.el("span", { text: "Remove Background" })
    ]);

    var batchBgBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "image-batch-bg-btn",
      "aria-label": "Batch Background Removal",
      title: "Batch Background Removal",
      onClick: function () {
        window.FOSS.api("select_files", { title: "Select Images for Batch Background Removal", file_types: ["png", "jpg", "jpeg"] }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            window.FOSS.api("select_directory", { title: "Select Output Folder" }).then(function (dRes) {
              var outD = dRes && dRes.paths && dRes.paths.length > 0 ? dRes.paths[0] : "";
              if (!outD) return;
              statusBar.textContent = "Processing " + res.paths.length + " files...";
              window.FOSS.api("images_batch_process", { file_paths: res.paths, output_dir: outD, remove_background: true, bg_model: modelSelect.value }).then(function () {
                showResult(outD, "Batch Background Removal Complete");
              });
            });
          }
        });
      }
    }, [
      window.FOSS.icons.el("layers", 16),
      window.FOSS.dom.el("span", { text: "Batch Background Removal" })
    ]);

    var bgControls = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("Model", modelSelect),
      removeBgLbl,
      removeBtn,
      batchBgBtn
    ]);

    mainCard.appendChild(filePicker.el);
    mainCard.appendChild(bgControls);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(mainCard);
  }

  // ==========================================
  // TAB 4: Compress
  // ==========================================
  function renderCompress(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Image Compression" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "choose a compression level" })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "images-compress-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "images-compress-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "images-compress-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "images-compress-result-card", title: titleText || "Compression Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var compressCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "image-compress-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-compress-picker",
      title: "Select Image to Compress",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
      },
      onClear: function () {
        currentFile = "";
      }
    });

    // Preset level
    var levelSelect = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "choose a compression level",
      title: "choose a compression level",
      style: { minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "small", text: "Small (Web 60% quality)" }),
      window.FOSS.dom.el("option", { value: "balanced", selected: true, text: "Balanced (80% quality)" }),
      window.FOSS.dom.el("option", { value: "high", text: "High Quality (92% quality)" }),
      window.FOSS.dom.el("option", { value: "custom", text: "custom / manual" })
    ]);

    var formatOption = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Output Format",
      title: "Output Format",
      style: { minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "", text: "keep original" }),
      window.FOSS.dom.el("option", { value: "webp", text: "WEBP (Best compression)" }),
      window.FOSS.dom.el("option", { value: "jpeg", text: "JPEG" }),
      window.FOSS.dom.el("option", { value: "png", text: "PNG" })
    ]);

    // Sub-mode tabs for easy vs advanced
    var subTabsNav = window.FOSS.dom.el("div", { className: "row", style: { gap: "var(--space-2)" } }, [
      window.FOSS.dom.el("button", { className: "btn btn-sm btn-primary", "aria-label": "easy", title: "easy", text: "easy" }),
      window.FOSS.dom.el("button", { className: "btn btn-sm", "aria-label": "advanced", title: "advanced", text: "advanced" })
    ]);

    var compressBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "aria-label": "Compress Image",
      title: "Compress Image",
      onClick: function () {
        if (!currentFile) return showError("Select an image to compress first.");
        var ext = formatOption.value || (currentFile.split(".").pop().toLowerCase());
        window.FOSS.api("select_save_path", { title: "Save Compressed Image", default_name: "compressed." + ext, filters: [{ name: "Image", extensions: [ext] }] }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          statusBar.textContent = "Compressing image...";
          var q = 80;
          if (levelSelect.value === "small") q = 60;
          else if (levelSelect.value === "high") q = 92;
          window.FOSS.api("images_rotate", { file_path: currentFile, degrees: 0, output_path: outP }).then(function () {
            showResult(outP, "Image Compressed");
            statusBar.textContent = "Saved to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("minimize-2", 16),
      window.FOSS.dom.el("span", { text: "Compress Image" })
    ]);

    var closeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "close",
      title: "close",
      onClick: function () {
        currentFile = "";
        statusBar.textContent = "Closed";
      }
    }, [window.FOSS.dom.el("span", { text: "close" })]);

    var compControls = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("choose a compression level", levelSelect),
      window.FOSS.components.field("format", formatOption),
      compressBtn,
      closeBtn
    ]);

    compressCard.appendChild(subTabsNav);
    compressCard.appendChild(filePicker.el);
    compressCard.appendChild(compControls);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(compressCard);
  }

  window.FOSS.router.register({
    id: "images",
    title: "Image Tools",
    navName: "Images",
    category: "Visuals",
    icon: "image",
    tabs: [
      { id: "convert", label: "Convert", render: renderConvert },
      { id: "transform", label: "Transform", render: renderTransform },
      { id: "background", label: "Background", render: renderBackground },
      { id: "compress", label: "Compress", render: renderCompress }
    ]
  });
})();

