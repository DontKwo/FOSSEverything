// File Format Converter: single file, batch queue, all-in-one compressor, and format interoperability.
window.FOSS = window.FOSS || {};

(function () {
  function renderSingle(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-converter");

    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "File Format Converter" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Convert documents, images, and data formats locally with explicit engine checks."
      }),
      window.FOSS.dom.el("p", {
        className: "text-xs text-muted",
        text: "Image, PDF, JSON, YAML, and CSV conversions run 100% locally on your machine."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "converter-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
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
      className: "hidden",
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

    // Card 1: Source File Selection
    var fileCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var fileDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "converter-source-display",
      "data-truncate-ok": "true",
      title: "No file selected",
      text: "No file selected"
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-choose-file",
      "aria-label": "Choose file",
      title: "Choose file",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentFile = res.paths[0];
          fileDisplay.textContent = currentFile;
          fileDisplay.title = currentFile;
          loadTargets(currentFile);
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose File" })
    ]);

    fileCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [
      fileDisplay,
      window.FOSS.dom.el("div", { className: "row" }, [chooseBtn])
    ]));

    var selectHint = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      text: "Select a file to see its detected type and current size."
    });
    fileCard.appendChild(selectHint);

    // Badges & Capability notices
    var badgesRow = window.FOSS.dom.el("div", { className: "row text-xs text-muted" }, [
      window.FOSS.dom.el("span", { className: "badge badge-neutral", "data-testid": "converter-raw-badge", text: "RAW, HEIC/AVIF, SVG, and PSD recognition" }),
      window.FOSS.dom.el("span", { className: "badge badge-neutral", "data-testid": "converter-media-info", text: "FFmpeg-backed audio/video conversion and extraction" }),
      window.FOSS.dom.el("span", { className: "badge badge-neutral", "data-testid": "converter-font-notice", text: "Font outline preservation (TTF/OTF/WOFF/WOFF2)" }),
      window.FOSS.dom.el("span", { className: "badge badge-neutral", "data-testid": "converter-ebook-notice", text: "E-book conversion (EPUB, MOBI, AZW3, FB2)" }),
      window.FOSS.dom.el("span", { className: "badge badge-neutral", "data-testid": "converter-ics-notice", text: "Calendar .ics import and parsing" })
    ]);
    fileCard.appendChild(badgesRow);

    // Card 2: Conversion Target & Execution
    var targetCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var targetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "converter-target-select",
      "aria-label": "Target format",
      title: "Target format",
      onChange: function () {
        updateSummary();
      }
    }, [
      window.FOSS.dom.el("option", { value: "png", text: "png" }),
      window.FOSS.dom.el("option", { value: "jpeg", text: "jpeg" }),
      window.FOSS.dom.el("option", { value: "webp", text: "webp" }),
      window.FOSS.dom.el("option", { value: "pdf", text: "pdf" }),
      window.FOSS.dom.el("option", { value: "json", text: "json" }),
      window.FOSS.dom.el("option", { value: "yaml", text: "yaml" }),
      window.FOSS.dom.el("option", { value: "csv", text: "csv" })
    ]);

    var targetRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Target format" }),
      targetSelect
    ]);
    targetCard.appendChild(targetRow);

    var summaryText = window.FOSS.dom.el("div", {
      className: "text-xs text-muted p-2 rounded bg-neutral-surface",
      "data-testid": "converter-summary-text",
      text: "Select a source file and target format to preview conversion shape."
    });
    targetCard.appendChild(summaryText);

    var filenameInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "converter-output-filename",
      "aria-label": "Output filename (without extension)",
      "data-truncate-ok": "true",
      title: "Output filename (without extension)",
      placeholder: "output filename (without extension)"
    });

    var filenameRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Output Name" }),
      filenameInput
    ]);
    targetCard.appendChild(filenameRow);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-convert-btn",
      "aria-label": "Convert locally",
      title: "Convert locally",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Please select a file to convert.");
          return;
        }
        clearError();
        statusBar.textContent = "Converting file locally...";
        var outStem = filenameInput.value.trim() || undefined;
        window.FOSS.api("converter_convert_file", {
          file_path: currentFile,
          target_format: targetSelect.value,
          output_stem: outStem
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Converted successfully: " + res.output_path;
            showResult(res.output_path, "File Converted Locally");
          } else {
            showError("Conversion failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Convert Locally" })
    ]);

    var exportEnexBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-export-enex-btn",
      "aria-label": "Export notes folder to enex",
      title: "Export notes folder to enex",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var folder = res.paths[0];
          var outEnex = folder + "/notes_export.enex";
          statusBar.textContent = "Exporting notes to ENEX...";
          window.FOSS.api("converter_export_enex", {
            notes: [{ title: "Exported Notes", content: "Notes from " + folder }],
            output_path: outEnex
          }).then(function (eRes) {
            if (eRes && eRes.output_path) {
              statusBar.textContent = "Notes exported: " + eRes.output_path;
              showResult(eRes.output_path, "Notes Exported to ENEX");
            } else {
              showError("Failed to export notes to ENEX.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "Export Notes Folder to ENEX" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", { className: "row" }, [convertBtn, exportEnexBtn]);
    targetCard.appendChild(actionsRow);

    function loadTargets(filePath) {
      window.FOSS.api("converter_available_targets", { file_path: filePath }).then(function (res) {
        if (!res || !res.targets) return;
        targetSelect.innerHTML = "";
        for (var i = 0; i < res.targets.length; i++) {
          var t = res.targets[i];
          var opt = window.FOSS.dom.el("option", { value: t.toLowerCase(), text: t.toLowerCase() });
          targetSelect.appendChild(opt);
        }
        updateSummary();
      });
    }

    function updateSummary() {
      if (!currentFile) {
        summaryText.textContent = "Select a file to see its detected type and current size.";
        return;
      }
      window.FOSS.api("converter_summary", {
        file_path: currentFile,
        target_format: targetSelect.value
      }).then(function (res) {
        if (res && res.summary) {
          summaryText.textContent = res.summary;
        }
      });
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(fileCard);
    panel.appendChild(targetCard);
  }

  function renderQueue(panel, ctx) {
    panel.innerHTML = "";

    var queueItems = [];

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Batch Conversion Queue" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Add multiple files to a queue, assign a target format globally or per-file, and process sequentially."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "converter-queue-status",
      text: "Queue idle: 0 items"
    });

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var targetAllSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "converter-batch-target-all",
      "aria-label": "Target format for all",
      title: "Target format for all",
      onChange: function () {
        var fmt = targetAllSelect.value;
        for (var i = 0; i < queueItems.length; i++) {
          queueItems[i].target_format = fmt;
        }
        renderQueueTable();
      }
    }, [
      window.FOSS.dom.el("option", { value: "png", text: "png" }),
      window.FOSS.dom.el("option", { value: "jpeg", text: "jpeg" }),
      window.FOSS.dom.el("option", { value: "webp", text: "webp" }),
      window.FOSS.dom.el("option", { value: "pdf", text: "pdf" }),
      window.FOSS.dom.el("option", { value: "json", text: "json" }),
      window.FOSS.dom.el("option", { value: "yaml", text: "yaml" }),
      window.FOSS.dom.el("option", { value: "csv", text: "csv" })
    ]);

    var globalRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Target format for all" }),
      targetAllSelect
    ]);
    card.appendChild(globalRow);

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-queue-add-btn",
      "aria-label": "Choose file",
      title: "Add files to batch queue",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_files", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var fmt = targetAllSelect.value;
          for (var i = 0; i < res.paths.length; i++) {
            queueItems.push({
              input_path: res.paths[i],
              target_format: fmt,
              status: "Pending"
            });
          }
          statusBar.textContent = "Queue: " + queueItems.length + " files ready.";
          renderQueueTable();
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose File" })
    ]);

    var startBatchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-batch-start-btn",
      "aria-label": "Start batch conversion",
      title: "Start batch conversion",
      type: "button",
      onClick: function () {
        if (!queueItems.length) return;
        statusBar.textContent = "Processing batch queue...";
        window.FOSS.api("converter_batch_convert", { items: queueItems }).then(function (res) {
          if (res && res.results) {
            statusBar.textContent = "Batch complete: " + res.results.length + " files processed.";
            for (var i = 0; i < queueItems.length; i++) {
              queueItems[i].status = "Done";
            }
            renderQueueTable();
          }
        });
      }
    }, [
      window.FOSS.icons.el("play", 16),
      window.FOSS.dom.el("span", { text: "Start Batch Conversion" })
    ]);

    var clearQueueBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "converter-queue-clear-btn",
      "aria-label": "Clear queue",
      title: "Clear queue",
      type: "button",
      onClick: function () {
        queueItems = [];
        statusBar.textContent = "Queue idle: 0 items";
        renderQueueTable();
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var toolbar = window.FOSS.dom.el("div", { className: "row" }, [addFilesBtn, startBatchBtn, clearQueueBtn]);
    card.appendChild(toolbar);

    var tableWrap = window.FOSS.dom.el("div", {
      className: "table-wrap scroll-x",
      "data-testid": "converter-queue-table"
    });
    tableWrap.innerHTML = '<div class="text-sm text-muted p-4 text-center">No files in queue. Click Choose File to add files.</div>';
    card.appendChild(tableWrap);

    function renderQueueTable() {
      if (!queueItems.length) {
        tableWrap.innerHTML = '<div class="text-sm text-muted p-4 text-center">No files in queue. Click Choose File to add files.</div>';
        return;
      }
      tableWrap.innerHTML = "";
      var tbl = window.FOSS.dom.el("table", { className: "table w-full" });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { className: "w-12 text-left", text: "#" }),
          window.FOSS.dom.el("th", { className: "text-left", text: "Source File" }),
          window.FOSS.dom.el("th", { className: "w-28 text-left", text: "Target" }),
          window.FOSS.dom.el("th", { className: "w-24 text-left", text: "Status" })
        ])
      ]);
      tbl.appendChild(thead);

      var tbody = window.FOSS.dom.el("tbody", {});
      for (var i = 0; i < queueItems.length; i++) {
        var it = queueItems[i];
        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "text-xs text-muted", text: String(i + 1) }),
          window.FOSS.dom.el("td", { className: "font-mono text-sm", style: "word-break: break-all;", text: it.input_path }),
          window.FOSS.dom.el("td", { className: "font-mono text-xs uppercase", text: it.target_format }),
          window.FOSS.dom.el("td", { className: "text-xs", text: it.status })
        ]);
        tbody.appendChild(tr);
      }
      tbl.appendChild(tbody);
      tableWrap.appendChild(tbl);
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(card);
  }

  function renderCompressor(panel, ctx) {
    panel.innerHTML = "";

    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "All-in-One Compressor" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Shrink any image, audio, or video file locally with one preset - no need to know which studio handles which format."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "converter-compress-status",
      text: "Ready"
    });

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "converter-compress-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "converter-compress-card",
        title: titleText || "Compression Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var fileDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "converter-compress-display",
      "data-truncate-ok": "true",
      title: "No file selected",
      text: "No file selected"
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-compress-choose",
      "aria-label": "Choose file",
      title: "Choose file",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentFile = res.paths[0];
          fileDisplay.textContent = currentFile;
          fileDisplay.title = currentFile;
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose File" })
    ]);

    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [
      fileDisplay,
      window.FOSS.dom.el("div", { className: "row" }, [chooseBtn])
    ]));

    var presetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "converter-compress-preset",
      "aria-label": "Compression Preset",
      title: "Compression Preset"
    }, [
      window.FOSS.dom.el("option", { value: "small", text: "Small File Size (High Compression)" }),
      window.FOSS.dom.el("option", { value: "balanced", text: "Balanced Quality & Size" }),
      window.FOSS.dom.el("option", { value: "high", text: "High Quality (Light Compression)" })
    ]);

    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Preset" }),
      presetSelect
    ]));

    var targetSizeInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-28",
      "data-testid": "converter-compress-target-size",
      "aria-label": "Target size limit (MB)",
      title: "Target size limit (MB)",
      value: 25,
      min: 1
    });

    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Target Size (MB)" }),
      targetSizeInput
    ]));

    var compressBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "converter-compress-btn",
      "aria-label": "Compress locally",
      title: "Compress locally",
      type: "button",
      onClick: function () {
        if (!currentFile) return;
        statusBar.textContent = "Compressing locally...";
        var outP = currentFile.replace(/\.[^.]+$/, "_compressed$&");
        var sizeMb = parseInt(targetSizeInput.value, 10) || 25;
        window.FOSS.api("converter_compress_media_helper", {
          file_path: currentFile,
          output_path: outP,
          target_size_mb: sizeMb
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Compressed successfully: " + res.output_path;
            showResult(res.output_path, "Compressed Media Ready");
          }
        });
      }
    }, [
      window.FOSS.icons.el("minimize", 16),
      window.FOSS.dom.el("span", { text: "Compress Locally" })
    ]);

    card.appendChild(window.FOSS.dom.el("div", { className: "row" }, [compressBtn]));

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(resultHost);
    panel.appendChild(card);
  }

  window.FOSS.router.register({
    id: "converter",
    title: "File Format Converter",
    navName: "Converter",
    category: "system",
    icon: "refresh",
    tabs: [
      { id: "single", label: "Single File Converter", render: renderSingle },
      { id: "queue", label: "Batch Conversion Queue", render: renderQueue },
      { id: "compress", label: "Compressor", render: renderCompressor }
    ]
  });
})();
