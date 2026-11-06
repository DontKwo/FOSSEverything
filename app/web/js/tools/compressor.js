// Centralized File Compressor: compress PDF documents, images, audio, video, and archives.
window.FOSS = window.FOSS || {};

(function () {
  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 B";
    var k = 1024;
    var sizes = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  var pendingPaths = [];

  function renderCompressor(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "compressor-page");

    var queueItems = [];
    var isCompressing = false;

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

    // Left Column: Compression Settings
    var PROFILE_LABELS = {
      light: "Low (Fast)",
      balanced: "Medium (Balanced)",
      aggressive: "High (Maximum)"
    };

    var presetSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "compressor-preset-select",
      "aria-label": "Compression Profile",
      title: "Compression Profile",
      onChange: function () {
        updateRatioEstimate();
        refreshEstimates();
      }
    }, Object.keys(PROFILE_LABELS).map(function (key) {
      return window.FOSS.dom.el("option", { value: key, text: PROFILE_LABELS[key] });
    }));
    presetSelect.value = window.FOSS.toolDefaults.get("compressor", "profile", "balanced");

    var ratioEstimateReadout = window.FOSS.dom.el("div", {
      className: "text-xs font-mono text-muted p-2 rounded bg-neutral",
      "data-testid": "compressor-ratio-estimate",
      text: ""
    });

    var estimateReadout = window.FOSS.dom.el("div", {
      className: "text-xs font-mono p-2 rounded bg-neutral",
      "data-testid": "compressor-estimate-readout",
      text: "Estimated savings: add files to see an estimate"
    });

    function updateRatioEstimate() {
      ratioEstimateReadout.textContent = "Profile: " + (PROFILE_LABELS[presetSelect.value] || presetSelect.value);
    }

    function refreshEstimates() {
      var pending = queueItems.filter(function (it) { return it.status !== "Done"; });
      if (pending.length === 0) {
        estimateReadout.textContent = "Estimated savings: add files to see an estimate";
        return;
      }
      window.FOSS.api("compressor_estimate_savings", {
        items: pending.map(function (it) { return { path: it.path, category: it.category }; }),
        preset: presetSelect.value,
        lossy_png: pngQuantizeCheck.checked
      }).then(function (res) {
        if (!res || !res.results) return;
        var byPath = {};
        res.results.forEach(function (r) { byPath[r.path] = r; });
        pending.forEach(function (it) {
          var est = byPath[it.path];
          it.est_bytes = est ? est.estimated_bytes : 0;
          it.est_pct = est ? est.saved_pct : 0;
        });
        estimateReadout.textContent = "Estimated savings: " + formatBytes(res.total_saved_bytes) + " (" +
          res.total_saved_pct + "%) of " + formatBytes(res.total_original_bytes) + " before compressing";
        renderQueueTable();
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    var defaultQuantize = !!window.FOSS.toolDefaults.get("compressor", "png_quantize", true);
    var pngQuantizeCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      className: "checkbox checkbox-sm",
      "data-testid": "compressor-png-quantize",
      "aria-label": "Quantize PNG Palette",
      title: "Quantize PNG Palette",
      checked: defaultQuantize,
      onChange: function () {
        refreshEstimates();
      }
    });

    var maxDimInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input font-mono text-xs",
      "data-testid": "compressor-max-dim",
      placeholder: "e.g. 1920 (optional)",
      "aria-label": "Max Image Dimension",
      title: "Max Image Dimension"
    });

    var targetMbInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input font-mono text-xs",
      "data-testid": "compressor-target-mb",
      placeholder: "e.g. 25 (optional)",
      "aria-label": "Target Video Size MB",
      title: "Target Video Size MB"
    });

    var pngColorsInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input font-mono text-xs",
      "data-testid": "compressor-png-colors",
      placeholder: "128 (16-256)",
      value: "128",
      min: "16",
      max: "256",
      "aria-label": "PNG Palette Colors",
      title: "PNG Palette Colors"
    });

    var jpegQualityInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input font-mono text-xs",
      "data-testid": "compressor-jpeg-quality",
      placeholder: "75 (10-100)",
      value: "75",
      min: "10",
      max: "100",
      "aria-label": "JPEG / WebP Quality",
      title: "JPEG / WebP Quality"
    });

    var audioBitrateInput = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs font-mono",
      "data-testid": "compressor-audio-bitrate",
      "aria-label": "Audio Bitrate",
      title: "Audio Bitrate"
    }, [
      window.FOSS.dom.el("option", { value: "auto", text: "Default (Auto Profile)" }),
      window.FOSS.dom.el("option", { value: "96k", text: "96 kbps (Voice/Compact)" }),
      window.FOSS.dom.el("option", { value: "128k", text: "128 kbps (Standard)" }),
      window.FOSS.dom.el("option", { value: "192k", text: "192 kbps (High Quality)" })
    ]);

    var advancedDetails = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 pt-2 border-t border-border hidden",
      "data-testid": "compressor-advanced-panel"
    }, [
      window.FOSS.components.field("PNG Palette Colors (16 - 256)", pngColorsInput),
      window.FOSS.components.field("JPEG / WebP Quality %", jpegQualityInput),
      window.FOSS.components.field("Audio Re-encode Bitrate", audioBitrateInput)
    ]);

    var toggleAdvancedBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm text-xs row gap-1 items-center justify-between w-full",
      "data-testid": "compressor-advanced-toggle",
      type: "button",
      onClick: function () {
        var isHidden = advancedDetails.classList.contains("hidden");
        advancedDetails.classList.toggle("hidden", !isHidden);
        toggleAdvancedBtn.textContent = isHidden ? "[-] Hide Advanced Options" : "[+] Show Advanced Options";
      }
    }, [window.FOSS.dom.el("span", { text: "[+] Show Advanced Options" })]);

    var advancedContainer = window.FOSS.dom.el("div", {
      className: "flex-col gap-1",
      "data-testid": "compressor-advanced-group"
    }, [
      toggleAdvancedBtn,
      advancedDetails
    ]);

    var outputDirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono text-xs grow",
      "data-testid": "compressor-out-dir",
      placeholder: "Default: next to source (_compressed)",
      "aria-label": "Output Folder",
      title: "Output Folder"
    });

    var browseDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "compressor-browse-dir-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", { title: "Select Output Folder" }).then(function (res) {
          if (res && res.path) outputDirInput.value = res.path;
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Browse..." })]);

    var runBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "compressor-run-btn",
      type: "button",
      onClick: function () {
        executeCompression();
      }
    }, [window.FOSS.icons.el("download", 16), window.FOSS.dom.el("span", { text: "Compress Items" })]);

    var sidebarCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Compression Settings" }),
      window.FOSS.components.field("Profile", presetSelect),
      ratioEstimateReadout,
      estimateReadout,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
        pngQuantizeCheck,
        window.FOSS.dom.el("label", {
          className: "text-xs font-semibold cursor-pointer",
          text: "Quantize PNG Palette (50-75% smaller)"
        })
      ]),
      window.FOSS.components.field("Max Image Dimension (px)", maxDimInput),
      window.FOSS.components.field("Target Video Size (MB)", targetMbInput),
      advancedContainer,
      window.FOSS.dom.el("div", { className: "flex-col gap-1" }, [
        window.FOSS.dom.el("label", { className: "text-xs font-semibold text-muted", text: "Output Folder" }),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [outputDirInput, browseDirBtn])
      ]),
      runBtn
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "compressor-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [sidebarCard]);

    // Right Column: Queue & Savings Table
    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "compressor-choose-file",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", { title: "Select Files to Compress" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          addPathsToQueue(res.paths);
        });
      }
    }, [window.FOSS.icons.el("file-plus", 14), window.FOSS.dom.el("span", { text: "Add Files..." })]);

    var addFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "compressor-add-folder-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", { title: "Select Folder to Compress" }).then(function (res) {
          if (!res || res.cancelled || !res.path) return;
          addPathsToQueue([res.path]);
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "compressor-clear-btn",
      type: "button",
      onClick: function () {
        queueItems = [];
        renderQueueTable();
        refreshEstimates();
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    function addPathsToQueue(paths) {
      statusBar.textContent = "Scanning input files...";
      window.FOSS.api("compressor_scan_inputs", {
        paths: paths,
        recursive: true
      }).then(function (res) {
        if (!res || !res.items) return;
        res.items.forEach(function (it) {
          var exists = queueItems.some(function (q) { return q.path === it.path; });
          if (!exists) {
            queueItems.push({
              path: it.path,
              name: it.name,
              category: it.category || "General",
              output_ext: it.output_ext || "",
              est_bytes: 0,
              est_pct: 0,
              size_bytes: it.size_bytes || 0,
              compressed_bytes: 0,
              saved_bytes: 0,
              saved_pct: 0,
              status: "Queued",
              output_path: ""
            });
          }
        });
        renderQueueTable();
        refreshEstimates();
        statusBar.textContent = "Queue: " + queueItems.length + " item(s) ready";
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    var tableHost = window.FOSS.dom.el("div", {
      className: "table-wrap grow flex-col gap-2",
      "data-testid": "compressor-queue-table",
      style: "min-width: 0; width: 100%; box-sizing: border-box;"
    });

    var savingsBanner = window.FOSS.dom.el("div", {
      className: "text-xs font-mono text-muted p-2 rounded bg-neutral hidden",
      "data-testid": "compressor-savings-banner",
      text: ""
    });

    function renderQueueTable() {
      tableHost.innerHTML = "";
      if (queueItems.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-8 text-center font-mono",
          text: "Compression queue is empty. Click Add Files or Add Folder above."
        }));
        runBtn.textContent = "Compress Items";
        runBtn.disabled = true;
        savingsBanner.classList.add("hidden");
        return;
      }

      runBtn.textContent = "Compress " + queueItems.length + " Items";
      runBtn.disabled = false;

      var rows = queueItems.map(function (it, idx) {
        var savingsBadge;
        if (it.status === "Done") {
          if (it.saved_bytes > 0) {
            savingsBadge = window.FOSS.dom.el("span", {
              className: "badge badge-success text-xs font-mono",
              style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
              "data-truncate-ok": "true",
              title: "-" + it.saved_pct + "% (" + formatBytes(it.saved_bytes) + ")",
              text: "-" + it.saved_pct + "%"
            });
          } else {
            savingsBadge = window.FOSS.dom.el("span", {
              className: "badge badge-neutral text-xs font-mono",
              style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
              "data-truncate-ok": "true",
              title: "Optimal file size",
              text: "Optimal"
            });
          }
        } else if (it.status === "Failed") {
          savingsBadge = window.FOSS.dom.el("span", {
            className: "badge badge-danger text-xs",
            style: "white-space: nowrap;",
            text: "Failed"
          });
        } else if (it.status === "Compressing...") {
          savingsBadge = window.FOSS.dom.el("span", {
            className: "badge badge-warning text-xs",
            style: "white-space: nowrap;",
            text: "Working..."
          });
        } else {
          savingsBadge = window.FOSS.dom.el("span", {
            className: "badge badge-neutral text-xs font-mono",
            style: "white-space: nowrap;",
            title: "Estimated savings before compressing",
            text: it.est_bytes > 0 ? "~-" + it.est_pct + "%" : "Queued"
          });
        }

        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Remove from queue",
          title: "Remove from queue",
          onClick: function () {
            queueItems.splice(idx, 1);
            renderQueueTable();
            refreshEstimates();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {
            className: "font-semibold text-sm",
            style: "width: 30%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.name,
            "data-truncate-ok": "true",
            title: it.path
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs text-muted",
            style: "width: 15%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.category,
            "data-truncate-ok": "true",
            title: it.category
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono text-muted",
            style: "width: 15%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: formatBytes(it.size_bytes),
            "data-truncate-ok": "true",
            title: formatBytes(it.size_bytes)
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono",
            style: "width: 15%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.compressed_bytes > 0 ? formatBytes(it.compressed_bytes) : (it.est_bytes > 0 ? "~" + formatBytes(it.est_bytes) : "-"),
            "data-truncate-ok": "true",
            title: it.compressed_bytes > 0 ? formatBytes(it.compressed_bytes) : (it.est_bytes > 0 ? "Estimated " + formatBytes(it.est_bytes) : "-")
          }),
          window.FOSS.dom.el("td", {
            style: "width: 25%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: it.status === "Done" ? "-" + it.saved_pct + "%" : "Estimated savings"
          }, [savingsBadge]),
          window.FOSS.dom.el("td", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;" }, [removeBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", {
        className: "table w-full",
        style: "table-layout: fixed; width: 100%; min-width: 0;"
      }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 30%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "File", "data-truncate-ok": "true", title: "File" }),
            window.FOSS.dom.el("th", { style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Type", "data-truncate-ok": "true", title: "Type" }),
            window.FOSS.dom.el("th", { style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Orig", "data-truncate-ok": "true", title: "Original" }),
            window.FOSS.dom.el("th", { style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Comp", "data-truncate-ok": "true", title: "Compressed" }),
            window.FOSS.dom.el("th", { style: "width: 25%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Saved", "data-truncate-ok": "true", title: "Savings" }),
            window.FOSS.dom.el("th", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;", text: "", "data-truncate-ok": "true", title: "Actions" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);

      tableHost.appendChild(table);
    }

    function executeCompression() {
      if (queueItems.length === 0 || isCompressing) return;
      isCompressing = true;
      clearError();
      statusBar.textContent = "Compressing items...";

      queueItems.forEach(function (it) { it.status = "Compressing..."; });
      renderQueueTable();

      var pset = presetSelect.value;
      var qPng = pngQuantizeCheck.checked;
      var maxDim = parseInt(maxDimInput.value, 10) || undefined;
      var targetMb = parseInt(targetMbInput.value, 10) || undefined;
      var pColors = parseInt(pngColorsInput.value, 10) || 128;
      var jQuality = parseInt(jpegQualityInput.value, 10) || undefined;
      var aBitrate = audioBitrateInput.value !== "auto" ? audioBitrateInput.value : undefined;
      var outDir = outputDirInput.value.trim();

      function runBatchWithCustomPath(customPath) {
        window.FOSS.api("compressor_compress_items", {
          items: queueItems.map(function (it) {
            return {
              path: it.path,
              category: it.category,
              output_path: customPath || undefined
            };
          }),
          preset: pset,
          lossy_png: qPng,
          png_colors: pColors,
          quality: jQuality,
          audio_bitrate: aBitrate,
          max_dimension: maxDim,
          target_size_mb: targetMb,
          output_dir: outDir || undefined
        }).then(function (res) {
          isCompressing = false;
          if (res && res.results) {
            res.results.forEach(function (r, i) {
              if (queueItems[i]) {
                queueItems[i].status = r.ok ? "Done" : "Failed";
                queueItems[i].compressed_bytes = r.compressed_bytes || 0;
                queueItems[i].saved_bytes = r.saved_bytes || 0;
                queueItems[i].saved_pct = r.saved_pct || 0;
                queueItems[i].output_path = r.output_path || "";
              }
            });
            statusBar.textContent = "Compression complete (" + (res.succeeded || 0) + " succeeded, " + (res.failed || 0) + " failed)";
            if (res.total_original_bytes > 0) {
              var bannerText = "Total Reduced: " + formatBytes(res.total_original_bytes) + " -> " + formatBytes(res.total_compressed_bytes) +
                " (Saved " + formatBytes(res.total_saved_bytes) + " / " + res.total_saved_pct + "%)";
              savingsBanner.textContent = bannerText;
              savingsBanner.classList.remove("hidden");
            }
            if (res.results.length === 1 && res.results[0].output_path) {
              showResult(res.results[0].output_path, "Item Compressed Successfully");
            }
          } else {
            statusBar.textContent = "Compression complete";
          }
          renderQueueTable();
        }).catch(function (err) {
          isCompressing = false;
          showError((err && err.message) || String(err));
          statusBar.textContent = "Compression error";
        });
      }

      if (queueItems.length === 1) {
        var single = queueItems[0];
        var srcExt = single.name.lastIndexOf(".") !== -1 ? single.name.substring(single.name.lastIndexOf(".")) : "";
        var outExt = (single.output_ext || srcExt).replace(/^\./, "").toLowerCase();
        window.FOSS.api("select_save_path", {
          title: "Save Compressed File",
          default_name: "compressed",
          file_types: outExt ? [{ name: outExt.toUpperCase() + " file (*." + outExt + ")", extensions: [outExt] }] : []
        }).then(function (res) {
          var chosen = (res && res.path) || "";
          if (!chosen) {
            isCompressing = false;
            single.status = "Queued";
            statusBar.textContent = "Save cancelled";
            renderQueueTable();
            return;
          }
          runBatchWithCustomPath(chosen);
        }).catch(function (err) {
          isCompressing = false;
          showError((err && err.message) || String(err));
        });
      } else {
        runBatchWithCustomPath("");
      }
    }

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
          addFilesBtn,
          addFolderBtn
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [clearBtn])
      ]),
      tableHost,
      savingsBanner
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "compressor-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable compressor-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);

    updateRatioEstimate();
    renderQueueTable();

    if (pendingPaths.length) {
      var queuedPaths = pendingPaths;
      pendingPaths = [];
      addPathsToQueue(queuedPaths);
    }
  }

  window.FOSS.router.register({
    id: "compressor",
    title: "File Compressor",
    navName: "Compressor",
    category: "Utilities",
    icon: "compressor",
    workbench: true,
    defaults: [
      {
        key: "profile",
        label: "Default compression profile",
        type: "select",
        options: [
          { value: "light", label: "Low (Fast)" },
          { value: "balanced", label: "Medium (Balanced)" },
          { value: "aggressive", label: "High (Maximum)" }
        ],
        default: "balanced"
      },
      { key: "png_quantize", label: "Quantize PNG palette by default", type: "toggle", default: true }
    ],
    tabs: [
      { id: "main", label: "File Compressor", aliases: ["single"], render: renderCompressor }
    ],
    onFiles: function (paths, ctx) {
      if (!paths || !paths.length) return;
      pendingPaths = paths.slice();
      window.FOSS.router.open("compressor", "main");
    }
  });
})();
