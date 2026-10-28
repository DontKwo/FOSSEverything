// Centralized File Compressor: compress PDF documents, images, audio, video, and archives in one place.
window.FOSS = window.FOSS || {};

(function () {
  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 B";
    var k = 1024;
    var sizes = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function detectCategory(path) {
    if (!path) return "Unknown";
    var ext = path.split(".").pop().toLowerCase();
    if (ext === "pdf") return "PDF";
    if (["png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif", "avif"].indexOf(ext) >= 0) return "Image";
    if (["mp4", "mkv", "mov", "avi", "webm", "mp3", "wav", "aac", "ogg", "flac", "m4a"].indexOf(ext) >= 0) return "Media";
    if (["zip", "tar", "gz", "bz2", "7z"].indexOf(ext) >= 0) return "Archive";
    return "Other";
  }

  function renderSingle(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "compressor-page");

    var currentFile = "";
    var currentCat = "Unknown";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Universal File Compressor" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Compress any PDF, image, video, audio file, or archive locally with optimal compression engines."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "compressor-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "compressor-error-banner"
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
      className: "hidden mb-sm",
      "data-testid": "compressor-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "compressor-result-card",
        title: titleText || "Compression Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var fileDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "compressor-file-display",
      "data-truncate-ok": "true",
      title: "No file selected",
      text: "No file selected"
    });

    var typeBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral",
      "data-testid": "compressor-type-badge",
      text: "Auto-detect"
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "compressor-choose-file",
      "aria-label": "Choose file",
      title: "Choose file",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          loadFile(res.paths[0]);
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose File" })
    ]);

    var fileCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [
        fileDisplay,
        window.FOSS.dom.el("div", { className: "row gap-sm items-center" }, [typeBadge, chooseBtn])
      ])
    ]);

    // Compression settings options
    var pdfLevelSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "compressor-pdf-level",
      "aria-label": "PDF Compression level"
    }, [
      window.FOSS.dom.el("option", { value: "lossless", text: "Lossless (remove duplicate metadata & objects)" }),
      window.FOSS.dom.el("option", { value: "medium", text: "Balanced (downscale images to 150 DPI)" }),
      window.FOSS.dom.el("option", { value: "max", text: "Maximum (downscale images to 72 DPI)" })
    ]);

    var imageQualitySlider = window.FOSS.components.slider({
      testid: "compressor-image-quality",
      label: "Image Quality (JPEG / WebP)",
      min: 10,
      max: 100,
      step: 5,
      value: 80,
      unit: "%"
    });

    var mediaTargetInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "compressor-media-target-mb",
      "aria-label": "Target size in MB",
      value: "25",
      style: "width: 6rem;"
    });

    var mediaPresetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "compressor-media-preset",
      "aria-label": "Media compression speed"
    }, [
      window.FOSS.dom.el("option", { value: "medium", text: "Balanced (medium speed & size)" }),
      window.FOSS.dom.el("option", { value: "fast", text: "Fast Encoding" }),
      window.FOSS.dom.el("option", { value: "veryslow", text: "Maximum Compression (smaller size)" })
    ]);

    var optionsContainer = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "compressor-options-card"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Compression Settings" }),
      window.FOSS.dom.el("div", {
        className: "text-xs text-muted",
        "data-testid": "compressor-options-hint",
        text: "Select a file above to configure compression settings."
      })
    ]);

    function loadFile(path) {
      currentFile = path;
      fileDisplay.textContent = path;
      fileDisplay.title = path;
      currentCat = detectCategory(path);
      typeBadge.textContent = currentCat;
      clearError();
      updateOptionsView();
    }

    function updateOptionsView() {
      optionsContainer.innerHTML = "";
      optionsContainer.appendChild(window.FOSS.dom.el("span", { className: "card-title", text: currentCat + " Compression Settings" }));

      if (currentCat === "PDF") {
        optionsContainer.appendChild(window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Compression Level" }));
        optionsContainer.appendChild(pdfLevelSelect);
      } else if (currentCat === "Image") {
        optionsContainer.appendChild(imageQualitySlider.el);
      } else if (currentCat === "Media") {
        optionsContainer.appendChild(window.FOSS.dom.el("div", { className: "row gap-sm items-center" }, [
          window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Target File Size:" }),
          mediaTargetInput,
          window.FOSS.dom.el("span", { className: "text-sm text-muted", text: "MB (for Discord, Email, or Slack)" })
        ]));
        optionsContainer.appendChild(window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Encoding Speed / Effort" }));
        optionsContainer.appendChild(mediaPresetSelect);
      } else {
        optionsContainer.appendChild(window.FOSS.dom.el("p", {
          className: "text-xs text-muted",
          text: "Standard compression will be applied using local ZIP/archive deflate algorithms."
        }));
      }

      var compressBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary btn-sm",
        "data-testid": "compressor-run-btn",
        "aria-label": "Compress file",
        title: "Compress file",
        type: "button",
        onClick: runCompression
      }, [
        window.FOSS.icons.el("download", 16),
        window.FOSS.dom.el("span", { text: "Compress File" })
      ]);

      optionsContainer.appendChild(window.FOSS.dom.el("div", { className: "row mt-sm" }, [compressBtn]));
    }

    function runCompression() {
      if (!currentFile) {
        showError("Please select a file to compress.");
        return;
      }
      clearError();
      statusBar.textContent = "Compressing " + currentCat.toLowerCase() + " file...";

      var ext = currentFile.split(".").pop();
      var defaultOut = currentFile.replace(/\.[^/.]+$/, "") + "_compressed." + ext;

      if (currentCat === "PDF") {
        var lvl = pdfLevelSelect.value;
        window.FOSS.api("pdf_compress", {
          input_path: currentFile,
          output_path: defaultOut,
          level: lvl
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Compressed PDF successfully: " + res.output_path;
            showResult(res.output_path, "PDF Compressed Successfully");
          } else {
            showError("Failed to compress PDF.");
          }
        }).catch(function (err) {
          showError(err.message || "Compression error.");
        });
      } else if (currentCat === "Image") {
        var q = imageQualitySlider.getValue ? imageQualitySlider.getValue() : 80;
        window.FOSS.api("images_compress", {
          file_path: currentFile,
          output_path: defaultOut,
          quality: q
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Compressed image successfully: " + res.output_path;
            showResult(res.output_path, "Image Compressed Successfully");
          } else {
            showError("Failed to compress image.");
          }
        }).catch(function (err) {
          showError(err.message || "Compression error.");
        });
      } else if (currentCat === "Media") {
        var mb = parseInt(mediaTargetInput.value, 10) || 25;
        var pset = mediaPresetSelect.value || "medium";
        window.FOSS.api("media_compress", {
          file_path: currentFile,
          output_path: defaultOut,
          target_size_mb: mb,
          preset: pset
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Compressed media successfully: " + res.output_path;
            showResult(res.output_path, "Media Compressed Successfully");
          } else {
            showError("Failed to compress media.");
          }
        }).catch(function (err) {
          showError(err.message || "Compression error.");
        });
      } else {
        // Fallback to archive compression
        var archiveOut = currentFile + ".zip";
        window.FOSS.api("archive_create", {
          file_paths: [currentFile],
          output_path: archiveOut,
          format: "zip"
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Compressed archive created: " + res.output_path;
            showResult(res.output_path, "Archive Compressed Successfully");
          } else {
            showError("Failed to create compressed archive.");
          }
        }).catch(function (err) {
          showError(err.message || "Compression error.");
        });
      }
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(fileCard);
    panel.appendChild(optionsContainer);
  }

  window.FOSS.router.register({
    id: "compressor",
    title: "File Compressor",
    navName: "Compressor",
    category: "Utilities",
    icon: "download",
    workbench: false,
    tabs: [
      { id: "single", label: "File Compressor", render: renderSingle }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        var inEl = document.querySelector("[data-testid='compressor-file-display']");
        if (inEl) {
          renderSingle(document.querySelector("[data-testid='compressor-page']") || document.body, ctx);
        }
      }
    }
  });
})();
