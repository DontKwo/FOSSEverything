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
    var presetSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "compressor-preset-select",
      "aria-label": "Compression Preset",
      title: "Compression Preset",
      onChange: function () {
        updateRatioEstimate();
      }
    }, [
      window.FOSS.dom.el("option", { value: "light", text: "Low (~15-30%)" }),
      window.FOSS.dom.el("option", { value: "balanced", text: "Medium (~30-50%)", selected: "selected" }),
      window.FOSS.dom.el("option", { value: "aggressive", text: "High (~50-75%)" })
    ]);

    var ratioEstimateReadout = window.FOSS.dom.el("div", {
      className: "text-xs font-mono text-muted p-2 rounded bg-neutral",
      "data-testid": "compressor-ratio-estimate",
      text: "Estimated ratio: ~30-50% reduction (Medium)"
    });

    function updateRatioEstimate() {
      var val = presetSelect.value;
      if (val === "light") {
        ratioEstimateReadout.textContent = "Estimated ratio: ~15-30% reduction (Low)";
      } else if (val === "aggressive") {
        ratioEstimateReadout.textContent = "Estimated ratio: ~50-75% reduction (High)";
      } else {
        ratioEstimateReadout.textContent = "Estimated ratio: ~30-50% reduction (Medium)";
      }
    }

    var pngQuantizeCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      className: "checkbox checkbox-sm",
      "data-testid": "compressor-png-quantize",
      "aria-label": "Quantize PNG Palette",
      title: "Quantize PNG Palette",
      checked: true
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
      window.FOSS.components.field("Preset", presetSelect),
      ratioEstimateReadout,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
        pngQuantizeCheck,
        window.FOSS.dom.el("label", {
          className: "text-xs font-semibold cursor-pointer",
          text: "Quantize PNG Palette (50-75% smaller)"
        })
      ]),
      window.FOSS.components.field("Max Image Dimension (px)", maxDimInput),
      window.FOSS.components.field("Target Video Size (MB)", targetMbInput),
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
            className: "badge badge-neutral text-xs",
            style: "white-space: nowrap;",
            text: "Queued"
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
            text: it.compressed_bytes > 0 ? formatBytes(it.compressed_bytes) : "-",
            "data-truncate-ok": "true",
            title: it.compressed_bytes > 0 ? formatBytes(it.compressed_bytes) : "-"
          }),
          window.FOSS.dom.el("td", {
            style: "width: 25%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: "-" + it.saved_pct + "%"
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
        var baseName = queueItems[0].name;
        var ext = baseName.lastIndexOf(".") !== -1 ? baseName.substring(baseName.lastIndexOf(".")) : "";
        var stem = ext ? baseName.substring(0, baseName.lastIndexOf(".")) : baseName;
        window.FOSS.api("select_save_path", {
          title: "Save Compressed File",
          default_name: stem + "_compressed" + ext
        }).then(function (res) {
          var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          runBatchWithCustomPath(p);
        }).catch(function () {
          runBatchWithCustomPath("");
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

    renderQueueTable();
  }

  window.FOSS.router.register({
    id: "compressor",
    title: "File Compressor",
    navName: "Compressor",
    category: "Utilities",
    icon: "download",
    workbench: true,
    tabs: [
      { id: "main", label: "File Compressor", aliases: ["single"], render: renderCompressor }
    ],
    onFiles: function (paths, ctx) {
      if (!paths || !paths.length) return;
      window.FOSS.router.open("compressor", "main");
    }
  });
})();
