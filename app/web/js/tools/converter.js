// File Format Converter: single file, recursive batch queue, and format interoperability.
window.FOSS = window.FOSS || {};

(function () {
  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 B";
    var k = 1024;
    var sizes = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  // TAB 1: Single File Converter
  function renderSingle(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "converter-page");

    var currentFile = "";
    var currentFamily = "Generic";
    var availableTargetsList = [];

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "converter-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "converter-error-banner"
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
      "data-testid": "converter-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "converter-result-card",
        title: titleText || "Conversion Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Left Column: Source Selection and Summary Card
    var fileDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "converter-source-display",
      "data-truncate-ok": "true",
      title: "No file selected",
      text: "No file selected"
    });

    var familyBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral",
      "data-testid": "converter-family-badge",
      text: "Auto-detect"
    });

    var sizeDisplay = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      text: ""
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-choose-file",
      "aria-label": "Choose file",
      title: "Choose file",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", { title: "Select File to Convert" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          loadFile(res.paths[0]);
        });
      }
    }, [window.FOSS.icons.el("file-plus", 14), window.FOSS.dom.el("span", { text: "Choose File..." })]);

    var sourceCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Source File" }),
      window.FOSS.dom.el("div", { className: "flex-col gap-2" }, [
        chooseBtn,
        fileDisplay,
        window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [familyBadge, sizeDisplay])
      ])
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "converter-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [sourceCard]);

    // Right Column: Target Options and Conversion
    var targetSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "converter-target-select",
      "aria-label": "Target Format",
      title: "Target Format",
      onChange: function () {
        updateContextualOptions();
      }
    });

    var outputStemInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono",
      "data-testid": "converter-output-stem",
      placeholder: "Default (source filename)",
      "aria-label": "Output Filename Stem",
      title: "Output Filename Stem"
    });

    var outputDirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono grow",
      "data-testid": "converter-output-dir",
      placeholder: "Same as source directory",
      "aria-label": "Output Folder",
      title: "Output Folder"
    });

    var browseDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-browse-dir-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", { title: "Select Output Folder" }).then(function (res) {
          if (res && res.path) outputDirInput.value = res.path;
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Browse..." })]);

    var qualitySlider = window.FOSS.components.slider({
      label: "Image Quality",
      min: 10,
      max: 100,
      value: 85,
      step: 5,
      unit: "%"
    });

    var dpiInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "converter-pdf-dpi",
      value: "150",
      min: "72",
      max: "600",
      "aria-label": "Render DPI",
      title: "Render DPI"
    });

    var contextualOptionsContainer = window.FOSS.dom.el("div", { className: "flex-col gap-2" });

    function updateContextualOptions() {
      contextualOptionsContainer.innerHTML = "";
      var fmt = (targetSelect.value || "").toUpperCase();
      if (["JPEG", "JPG", "WEBP"].indexOf(fmt) >= 0) {
        contextualOptionsContainer.appendChild(qualitySlider.el);
      }
      if (fmt.indexOf("PDF") >= 0 || fmt === "DOCX") {
        contextualOptionsContainer.appendChild(window.FOSS.components.field("Rendering DPI", dpiInput));
      }
    }

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "converter-convert-btn",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Please select a file to convert.");
          return;
        }
        clearError();
        statusBar.textContent = "Converting file...";
        var tgt = targetSelect.value;
        var stem = outputStemInput.value.trim();
        var outDir = outputDirInput.value.trim();
        var dpi = parseInt(dpiInput.value, 10) || 150;
        var q = qualitySlider.getValue ? qualitySlider.getValue() : 85;

        var baseName = currentFile.split(/[/\\]/).pop().replace(/\.[^/.]+$/, "");
        var defName = (stem || baseName) + "." + tgt.toLowerCase();
        window.FOSS.api("select_save_path", {
          title: "Save Converted File",
          default_name: defName
        }).then(function (res) {
          var outPath = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          window.FOSS.api("converter_convert_file", {
            file_path: currentFile,
            output_path: outPath || undefined,
            target_format: tgt,
            output_stem: stem || undefined,
            output_dir: outDir || undefined,
            dpi: dpi,
            quality: q
          }).then(function (convRes) {
            if (convRes && convRes.output_path) {
              statusBar.textContent = "Conversion complete: " + convRes.output_path;
              showResult(convRes.output_path, "Conversion Complete");
            } else {
              showError("Conversion produced no output file.");
            }
          }).catch(function (err) {
            showError((err && err.message) || String(err));
          });
        }).catch(function () {
          window.FOSS.api("converter_convert_file", {
            file_path: currentFile,
            target_format: tgt,
            output_stem: stem || undefined,
            output_dir: outDir || undefined,
            dpi: dpi,
            quality: q
          }).then(function (convRes) {
            if (convRes && convRes.output_path) {
              statusBar.textContent = "Conversion complete: " + convRes.output_path;
              showResult(convRes.output_path, "Conversion Complete");
            }
          });
        });
      }
    }, [window.FOSS.icons.el("refresh", 16), window.FOSS.dom.el("span", { text: "Convert File" })]);

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Conversion Options" }),
      window.FOSS.components.field("Target Format", targetSelect),
      contextualOptionsContainer,
      window.FOSS.components.field("Custom Output Filename (Optional)", outputStemInput),
      window.FOSS.dom.el("div", { className: "flex-col gap-1" }, [
        window.FOSS.dom.el("label", { className: "text-xs font-semibold text-muted", text: "Output Folder" }),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [outputDirInput, browseDirBtn])
      ]),
      convertBtn
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "converter-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable converter-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    function loadFile(filePath) {
      currentFile = filePath;
      var fileName = filePath.split(/[/\\]/).pop();
      fileDisplay.textContent = fileName;
      fileDisplay.setAttribute("title", filePath);
      statusBar.textContent = "Analyzing " + fileName + "...";

      window.FOSS.api("converter_available_targets", { file_path: filePath }).then(function (res) {
        if (!res) return;
        currentFamily = res.family || "File";
        familyBadge.textContent = currentFamily;
        availableTargetsList = res.targets || [];
        targetSelect.innerHTML = "";
        availableTargetsList.forEach(function (t) {
          targetSelect.appendChild(window.FOSS.dom.el("option", { value: t, text: t }));
        });
        updateContextualOptions();
        statusBar.textContent = "Ready (" + availableTargetsList.length + " compatible target formats)";
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);
  }

  // TAB 2: Batch & Folder Queue
  function renderBatch(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "converter-page");

    var queueItems = [];
    var isProcessing = false;

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "converter-queue-status",
      text: "Queue idle: 0 items"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "converter-batch-error"
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

    // Top Controls Bar
    var recursiveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      className: "checkbox checkbox-sm",
      "data-testid": "converter-batch-recursive",
      "aria-label": "Include Subfolders",
      title: "Include Subfolders",
      checked: true
    });

    var preserveTreeCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      className: "checkbox checkbox-sm",
      "data-testid": "converter-batch-preserve-tree",
      "aria-label": "Preserve Folder Structure",
      title: "Preserve Folder Structure",
      checked: true
    });

    var familyFilterSelect = window.FOSS.dom.el("select", {
      className: "select select-sm",
      "data-testid": "converter-batch-family-filter",
      "aria-label": "Filter Family",
      title: "Filter Family",
      onChange: function () {
        renderQueueTable();
      }
    }, [
      window.FOSS.dom.el("option", { value: "all", text: "All Supported Families" }),
      window.FOSS.dom.el("option", { value: "image", text: "Images" }),
      window.FOSS.dom.el("option", { value: "document", text: "Documents & Office" }),
      window.FOSS.dom.el("option", { value: "media", text: "Audio & Video" }),
      window.FOSS.dom.el("option", { value: "data", text: "Structured Data" }),
      window.FOSS.dom.el("option", { value: "model3d", text: "3D Models" })
    ]);

    var targetAllSelect = window.FOSS.dom.el("select", {
      className: "select select-sm",
      "data-testid": "converter-batch-target-all",
      "aria-label": "Target format for all",
      title: "Target format for all",
      onChange: function () {
        var fmt = targetAllSelect.value;
        if (!fmt) return;
        queueItems.forEach(function (it) {
          if (it.targets && it.targets.indexOf(fmt) !== -1) {
            it.target_format = fmt;
          }
        });
        renderQueueTable();
      }
    }, [window.FOSS.dom.el("option", { value: "", text: "Apply Target to All..." })]);

    function updateTargetAllOptions() {
      var union = [];
      queueItems.forEach(function (it) {
        (it.targets || []).forEach(function (t) {
          if (union.indexOf(t) === -1) union.push(t);
        });
      });
      targetAllSelect.innerHTML = "";
      targetAllSelect.appendChild(window.FOSS.dom.el("option", { value: "", text: "Apply Target to All..." }));
      union.sort().forEach(function (t) {
        targetAllSelect.appendChild(window.FOSS.dom.el("option", { value: t, text: t }));
      });
    }

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-queue-add-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", { title: "Select Files to Convert" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          addPathsToQueue(res.paths);
        });
      }
    }, [window.FOSS.icons.el("file-plus", 14), window.FOSS.dom.el("span", { text: "Add Files..." })]);

    var addFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-batch-add-folder-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", { title: "Select Folder to Convert" }).then(function (res) {
          if (!res || res.cancelled || !res.path) return;
          addPathsToQueue([res.path]);
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var addFolderBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm hidden",
      "data-testid": "converter-queue-add-folder-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", { title: "Select Folder to Convert" }).then(function (res) {
          if (!res || res.cancelled || !res.path) return;
          addPathsToQueue([res.path]);
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var clearCompletedBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "converter-batch-clear-btn",
      type: "button",
      onClick: function () {
        queueItems = queueItems.filter(function (it) { return it.status !== "Done"; });
        renderQueueTable();
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear Completed" })]);

    function addPathsToQueue(paths) {
      statusBar.textContent = "Scanning input files...";
      window.FOSS.api("converter_scan_inputs", {
        paths: paths,
        recursive: recursiveCheck.checked
      }).then(function (res) {
        if (!res || !res.items) return;
        res.items.forEach(function (it) {
          var exists = queueItems.some(function (q) { return q.path === it.path; });
          if (!exists) {
            queueItems.push({
              path: it.path,
              name: it.name,
              rel_dir: it.rel_dir || "",
              size_bytes: it.size_bytes || 0,
              family: it.family || "File",
              targets: it.targets || [],
              target_format: it.default_target || (it.targets && it.targets[0]) || "",
              status: "Queued",
              error: null,
              output_path: ""
            });
          }
        });
        updateTargetAllOptions();
        renderQueueTable();
        statusBar.textContent = "Queue: " + queueItems.length + " item(s) ready";
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    // Center Queue Table
    var tableHost = window.FOSS.dom.el("div", {
      className: "grow flex-col gap-2 overflow-x-auto",
      "data-testid": "converter-queue-table",
      style: "min-width: 0; width: 100%; box-sizing: border-box;"
    });

    function renderQueueTable() {
      tableHost.innerHTML = "";
      var famFilter = familyFilterSelect.value;
      var visibleItems = queueItems.filter(function (it) {
        if (famFilter === "all") return true;
        var fam = (it.family || "").toLowerCase();
        if (famFilter === "image") return fam === "image";
        if (famFilter === "document") return ["document", "office", "pdf"].indexOf(fam) >= 0;
        if (famFilter === "media") return ["audio", "video"].indexOf(fam) >= 0;
        if (famFilter === "data") return fam === "data";
        if (famFilter === "model3d") return fam === "model3d";
        return true;
      });

      if (visibleItems.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-8 text-center font-mono",
          text: queueItems.length === 0 ? "Batch queue is empty. Click Add Files or Add Folder above." : "No queue items match the active family filter."
        }));
        runBtn.textContent = "Convert 0 Files";
        runBtn.disabled = true;
        return;
      }

      runBtn.textContent = "Convert " + visibleItems.length + " Files";
      runBtn.disabled = false;

      var rows = visibleItems.map(function (it, idx) {
        var relHint = it.rel_dir ? it.rel_dir + "/" : "";
        var nameText = relHint + it.name;

        var targetSelectEl = window.FOSS.dom.el("select", {
          className: "select select-sm w-full font-mono text-xs",
          "data-testid": "converter-row-target-" + idx,
          "aria-label": "Row Target Format",
          title: "Select target format for " + it.name,
          onChange: function () {
            it.target_format = targetSelectEl.value;
          }
        }, (it.targets || []).map(function (t) {
          var opt = window.FOSS.dom.el("option", { value: t, text: t });
          if (t === it.target_format) opt.selected = true;
          return opt;
        }));

        var statusEl;
        if (it.status === "Done") {
          statusEl = window.FOSS.dom.el("span", {
            className: "badge badge-success text-xs",
            text: "Done"
          });
        } else if (it.status === "Failed") {
          statusEl = window.FOSS.dom.el("span", {
            className: "badge badge-danger text-xs",
            text: "Failed",
            title: it.error || "Conversion failed"
          });
        } else if (it.status === "Converting...") {
          statusEl = window.FOSS.dom.el("span", {
            className: "badge badge-warning text-xs",
            text: "Converting..."
          });
        } else {
          statusEl = window.FOSS.dom.el("span", {
            className: "badge badge-neutral text-xs",
            text: "Queued"
          });
        }

        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Remove from queue",
          title: "Remove from queue",
          onClick: function () {
            var origIdx = queueItems.indexOf(it);
            if (origIdx !== -1) queueItems.splice(origIdx, 1);
            updateTargetAllOptions();
            renderQueueTable();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {
            className: "font-semibold text-sm",
            style: "width: 35%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: nameText,
            "data-truncate-ok": "true",
            title: it.path
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs text-muted",
            style: "width: 15%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.family,
            "data-truncate-ok": "true",
            title: it.family
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono text-muted",
            style: "width: 15%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: formatBytes(it.size_bytes),
            "data-truncate-ok": "true",
            title: formatBytes(it.size_bytes)
          }),
          window.FOSS.dom.el("td", { style: "width: 20%;" }, [targetSelectEl]),
          window.FOSS.dom.el("td", { style: "width: 15%; text-align: center;" }, [statusEl]),
          window.FOSS.dom.el("td", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;" }, [removeBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", {
        className: "table w-full",
        style: "table-layout: fixed; width: 100%; min-width: 0;"
      }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 35%;", text: "Source File", "data-truncate-ok": "true", title: "Source File" }),
            window.FOSS.dom.el("th", { style: "width: 15%;", text: "Family", "data-truncate-ok": "true", title: "Family" }),
            window.FOSS.dom.el("th", { style: "width: 15%;", text: "Size", "data-truncate-ok": "true", title: "Size" }),
            window.FOSS.dom.el("th", { style: "width: 20%;", text: "Target Format", "data-truncate-ok": "true", title: "Target Format" }),
            window.FOSS.dom.el("th", { style: "width: 15%; text-align: center;", text: "Status", "data-truncate-ok": "true", title: "Status" }),
            window.FOSS.dom.el("th", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;", text: "", "data-truncate-ok": "true", title: "Actions" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);

      tableHost.appendChild(table);
    }

    // Bottom Bar: Output Folder and Primary Run Button
    var outputDirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono grow text-xs",
      "data-testid": "converter-batch-out-dir",
      placeholder: "Default: <common_folder>/converted",
      "aria-label": "Batch Output Folder",
      title: "Batch Output Folder"
    });

    var browseBatchDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-batch-browse-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", { title: "Select Output Folder" }).then(function (res) {
          if (res && res.path) outputDirInput.value = res.path;
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Browse..." })]);

    var runBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "converter-batch-start-btn",
      type: "button",
      onClick: function () {
        executeBatch();
      }
    }, [window.FOSS.icons.el("refresh", 16), window.FOSS.dom.el("span", { text: "Convert Files" })]);

    function executeBatch() {
      if (queueItems.length === 0 || isProcessing) return;
      isProcessing = true;
      clearError();
      statusBar.textContent = "Processing batch conversions...";

      queueItems.forEach(function (it) { it.status = "Converting..."; });
      renderQueueTable();

      var outDir = outputDirInput.value.trim();
      var preserve = preserveTreeCheck.checked;

      window.FOSS.api("converter_batch_convert", {
        items: queueItems.map(function (it) {
          return {
            path: it.path,
            target_format: it.target_format,
            rel_dir: it.rel_dir
          };
        }),
        output_dir: outDir || undefined,
        preserve_tree: preserve
      }).then(function (res) {
        isProcessing = false;
        if (res && res.results) {
          res.results.forEach(function (r, i) {
            if (queueItems[i]) {
              queueItems[i].status = r.ok ? "Done" : "Failed";
              queueItems[i].error = r.error;
              queueItems[i].output_path = r.output_path;
            }
          });
          statusBar.textContent = "Batch complete (" + (res.succeeded || 0) + " succeeded, " + (res.failed || 0) + " failed)";
        } else {
          statusBar.textContent = "Batch complete";
        }
        renderQueueTable();
      }).catch(function (err) {
        isProcessing = false;
        showError((err && err.message) || String(err));
        statusBar.textContent = "Batch stopped with error";
      });
    }

    var card = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
          addFilesBtn,
          addFolderBtn
        ]),
        window.FOSS.dom.el("div", { className: "row gap-3 items-center flex-wrap" }, [
          window.FOSS.dom.el("label", { className: "row gap-1 items-center text-xs text-muted cursor-pointer" }, [
            recursiveCheck,
            window.FOSS.dom.el("span", { text: "Include Subfolders" })
          ]),
          window.FOSS.dom.el("label", { className: "row gap-1 items-center text-xs text-muted cursor-pointer" }, [
            preserveTreeCheck,
            window.FOSS.dom.el("span", { text: "Preserve Structure" })
          ]),
          familyFilterSelect,
          targetAllSelect,
          clearCompletedBtn
        ])
      ]),
      tableHost,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap pt-2 border-t" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 items-center grow", style: "min-width: 16rem;" }, [
          window.FOSS.dom.el("span", { className: "text-xs font-semibold text-muted shrink-0", text: "Output Folder:" }),
          outputDirInput,
          browseBatchDirBtn
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          runBtn
        ])
      ])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(card);

    renderQueueTable();
  }

  window.FOSS.router.register({
    id: "converter",
    title: "File Format Converter",
    navName: "Converter",
    category: "Utilities",
    icon: "refresh",
    workbench: true,
    tabs: [
      { id: "single", label: "Single File", render: renderSingle },
      { id: "batch", label: "Batch & Folder Queue", aliases: ["queue"], render: renderBatch }
    ],
    onFiles: function (paths, ctx) {
      if (!paths || !paths.length) return;
      if (paths.length === 1) {
        window.FOSS.router.open("converter", "single");
      } else {
        window.FOSS.router.open("converter", "batch");
      }
    }
  });
})();
