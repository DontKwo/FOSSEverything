// Metadata Tools workspace: inspect, edit, strip, GPS extraction, diffing, and batch cleanup.
window.FOSS = window.FOSS || {};

(function () {
  var globalCurrentFile = "";

  var TYPE_LABELS = {
    jpg: "JPEG Image", jpeg: "JPEG Image", png: "PNG Image", webp: "WebP Image", gif: "GIF Image",
    bmp: "Bitmap Image", tif: "TIFF Image", tiff: "TIFF Image", pdf: "PDF Document",
    docx: "Microsoft Word Document", docm: "Microsoft Word Macro Document",
    xlsx: "Microsoft Excel Workbook", xlsm: "Microsoft Excel Macro Workbook",
    pptx: "Microsoft PowerPoint Presentation", pptm: "Microsoft PowerPoint Macro Presentation",
    odt: "OpenDocument Text", ods: "OpenDocument Spreadsheet", odp: "OpenDocument Presentation",
    mp3: "MP3 Audio", wav: "WAV Audio", flac: "FLAC Audio", m4a: "M4A Audio", ogg: "Ogg Audio",
    mp4: "MP4 Video", mov: "QuickTime Video", mkv: "Matroska Video", webm: "WebM Video"
  };

  function matchedFileTypes(filePath) {
    var base = String(filePath || "").split(/[/\\]/).pop();
    var dot = base.lastIndexOf(".");
    var ext = dot !== -1 ? base.substring(dot + 1).toLowerCase() : "";
    if (!ext) return [];
    var label = TYPE_LABELS[ext] || (ext.toUpperCase() + " File");
    return [{ name: label + " (*." + ext + ")", extensions: [ext] }];
  }

  function savePathFor(filePath, title, baseName) {
    return window.FOSS.api("select_save_path", {
      title: title,
      default_name: baseName,
      file_types: matchedFileTypes(filePath)
    }).then(function (res) {
      if (!res || res.cancelled) return "";
      return res.path || (res.paths && res.paths[0]) || "";
    });
  }

  function renderInspectTab(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "metadata-inspect-page");

    var currentFilePath = globalCurrentFile || "";
    var currentMetadata = {};
    var currentGps = null;

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "metadata-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "metadata-error"
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
      "data-testid": "metadata-result-host"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "metadata-result",
        title: titleText,
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var warningBanner = window.FOSS.dom.el("div", {
      className: "banner info",
      "data-testid": "metadata-warning-banner"
    }, [
      window.FOSS.icons.el("info", 18),
      window.FOSS.dom.el("span", {
        className: "banner-msg",
        text: "Notice: Metadata removal strips headers and tags, but does not remove visible page content or annotations."
      })
    ]);

    // Left Column: Dropzone, Privacy Assessment, Editable Form, Actions
    var pathDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-xs text-muted grow",
      style: "min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      "data-testid": "metadata-file-display",
      "data-truncate-ok": "true",
      title: "No file selected",
      text: "No file selected"
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "metadata-choose-file",
      "aria-label": "Choose file",
      title: "Choose file",
      type: "button",
      onClick: function () {
        browseAction();
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose File" })
    ]);

    var fileCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Target File" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [chooseBtn, pathDisplay])
    ]);

    // Privacy Assessment Card
    var privacyBadge = window.FOSS.dom.el("div", {
      className: "badge badge-neutral text-xs",
      "data-testid": "metadata-privacy-badge",
      text: "No file inspected"
    });

    var gpsBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden flex-col gap-2",
      "data-testid": "metadata-gps-warning"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center font-semibold text-xs" }, [
        window.FOSS.icons.el("alert", 16),
        window.FOSS.dom.el("span", { text: "EXIF GPS Coordinates Found!" })
      ]),
      window.FOSS.dom.el("div", { className: "text-xs font-mono", id: "metadata-gps-coords", text: "" })
    ]);

    var openMapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-open-map-btn",
      type: "button",
      onClick: function () {
        if (currentGps && currentGps.maps_url) {
          window.open(currentGps.maps_url, "_blank");
        }
      }
    }, [
      window.FOSS.icons.el("link", 14),
      window.FOSS.dom.el("span", { text: "Open Exact Location in Map" })
    ]);

    var privacyCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
        window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: "Privacy Assessment" }),
        privacyBadge
      ]),
      gpsBanner
    ]);

    // Editable Metadata Form
    var titleInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs",
      "data-testid": "metadata-input-title",
      "aria-label": "Document Title",
      placeholder: "Document title..."
    });

    var authorInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs",
      "data-testid": "metadata-input-author",
      "aria-label": "Author or Creator",
      placeholder: "Author name..."
    });

    var subjectInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs",
      "data-testid": "metadata-input-subject",
      "aria-label": "Subject",
      placeholder: "Subject description..."
    });

    var keywordsInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs",
      "data-testid": "metadata-input-keywords",
      "aria-label": "Keywords",
      placeholder: "Keywords (comma separated)..."
    });

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-save-btn",
      type: "button",
      onClick: function () {
        saveEditsAction();
      }
    }, [
      window.FOSS.icons.el("check", 14),
      window.FOSS.dom.el("span", { text: "Save Metadata Changes" })
    ]);

    var editCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Edit Document Properties" }),
      window.FOSS.components.field("Title", titleInput),
      window.FOSS.components.field("Author / Creator", authorInput),
      window.FOSS.components.field("Subject", subjectInput),
      window.FOSS.components.field("Keywords", keywordsInput),
      saveBtn
    ]);

    var backupSwitch = window.FOSS.components.switch({
      testid: "metadata-backup-toggle",
      label: "Create a backup copy of the original file",
      checked: !!window.FOSS.toolDefaults.get("metadata", "create_backup", false)
    });

    // Primary Strip Button
    var stripBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary w-full",
      "data-testid": "metadata-strip-btn",
      type: "button",
      onClick: function () {
        stripAction();
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Save Clean Copy (Strip All Metadata)..." })
    ]);

    // Safety and capability details host (kept for scenario compatibility)
    var diffTableHost = window.FOSS.dom.el("div", {
      className: "text-xs",
      "data-testid": "metadata-diff-table"
    });

    editCard.classList.add("hidden");

    var sidebar = window.FOSS.dom.el("div", {
      className: "metadata-sidebar-pane"
    }, [
      fileCard,
      privacyCard,
      warningBanner,
      backupSwitch.el,
      stripBtn,
      editCard,
      diffTableHost
    ]);

    // Right Column: Filterable grouped Metadata Table
    var tableFilterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs grow",
      "data-testid": "metadata-table-filter",
      placeholder: "Filter metadata tags or values...",
      "aria-label": "Filter metadata tags"
    });

    var inspectTableHost = window.FOSS.dom.el("div", {
      className: "table-wrap grow",
      style: "min-height: 12rem;",
      "data-testid": "metadata-table"
    });

    var filterQuery = "";
    tableFilterInput.addEventListener("input", function () {
      filterQuery = tableFilterInput.value.trim().toLowerCase();
      renderInspectTable(currentMetadata);
    });

    var saveTableEditsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-save-table-btn",
      type: "button",
      onClick: function () {
        saveEditsAction();
      }
    }, [window.FOSS.icons.el("save", 14), window.FOSS.dom.el("span", { text: "Save All Changes" })]);

    var addTagBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-add-tag-btn",
      type: "button",
      onClick: function () {
        var key = window.prompt("Enter new metadata tag name:");
        if (!key || !key.trim()) return;
        currentMetadata[key.trim()] = "";
        renderInspectTable(currentMetadata);
      }
    }, [window.FOSS.icons.el("plus", 14), window.FOSS.dom.el("span", { text: "Add Tag" })]);

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "box-sizing: border-box; min-width: 0;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: "Editable Metadata Fields" }),
        window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          tableFilterInput,
          addTagBtn,
          saveTableEditsBtn
        ])
      ]),
      inspectTableHost
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "metadata-stage-pane grow"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable metadata-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);

    panel._loadFile = loadFile;

    function browseAction() {
      clearError();
      window.FOSS.api("select_file", {}).then(function (res) {
        if (!res || res.cancelled || !res.paths || !res.paths.length) return;
        loadFile(res.paths[0]);
      });
    }

    function loadFile(filePath) {
      if (!filePath) return;
      currentFilePath = filePath;
      globalCurrentFile = filePath;
      pathDisplay.textContent = filePath;
      pathDisplay.title = filePath;
      statusBar.textContent = "Inspecting metadata: " + filePath;
      clearError();
      resultHost.classList.add("hidden");

      window.FOSS.api("metadata_inspect", { file_path: filePath }).then(function (res) {
        if (res.ok === false) {
          showError(res.error || "Inspect failed");
          return;
        }
        currentMetadata = res.metadata || {};
        renderInspectTable(currentMetadata);
        populateEditForm(currentMetadata);
        checkGps(filePath, currentMetadata);
        renderDiffTable(currentMetadata);
        statusBar.textContent = "[OK] Inspected: " + filePath;
      }).catch(function (err) {
        showError("Inspect failed: " + (err && err.message ? err.message : String(err)));
      });
    }

    function renderInspectTable(meta) {
      inspectTableHost.innerHTML = "";
      var entries = Object.entries(meta || {});
      if (filterQuery) {
        entries = entries.filter(function (e) {
          return e[0].toLowerCase().indexOf(filterQuery) !== -1 || String(e[1]).toLowerCase().indexOf(filterQuery) !== -1;
        });
      }

      if (!entries.length) {
        inspectTableHost.innerHTML = "<div class='text-xs text-muted p-3'>No matching metadata tags found.</div>";
        return;
      }

      var rows = entries.map(function (e) {
        var key = e[0];
        var valInput = window.FOSS.dom.el("input", {
          type: "text",
          className: "input input-sm text-xs font-mono w-full",
          value: String(e[1]),
          "aria-label": "Value for " + key,
          onInput: function () {
            currentMetadata[key] = valInput.value;
            syncInputsFromMetadata(currentMetadata);
          }
        });

        var deleteBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm text-danger",
          type: "button",
          title: "Delete Tag",
          "aria-label": "Delete tag " + key,
          onClick: function () {
            delete currentMetadata[key];
            renderInspectTable(currentMetadata);
            syncInputsFromMetadata(currentMetadata);
          }
        }, [window.FOSS.icons.el("trash", 12)]);

        var copyBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          type: "button",
          title: "Copy Value",
          "aria-label": "Copy tag value",
          onClick: function () {
            if (navigator.clipboard) {
              navigator.clipboard.writeText(String(currentMetadata[key] || "")).then(function () {
                if (window.FOSS.toast) window.FOSS.toast.show("Copied value", "info");
              });
            }
          }
        }, [window.FOSS.icons.el("copy", 12)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {
            className: "font-mono text-xs font-semibold",
            "data-truncate-ok": "true",
            title: String(key),
            text: String(key)
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono",
            style: "padding: 0.25rem 0.5rem;"
          }, [valInput]),
          window.FOSS.dom.el("td", { style: "width: 5rem; text-align: right; white-space: nowrap;" }, [copyBtn, deleteBtn])
        ]);
      });

      var tbl = window.FOSS.dom.el("table", { className: "table" }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "Tag Name", style: "width: 35%;" }),
            window.FOSS.dom.el("th", { text: "Value" }),
            window.FOSS.dom.el("th", { text: "", style: "width: 2.5rem;" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);
      inspectTableHost.appendChild(tbl);
    }

    function populateEditForm(meta) {
      syncInputsFromMetadata(meta);
    }

    function syncInputsFromMetadata(meta) {
      titleInput.value = meta.Title || meta.title || meta["PDF:Title"] || "";
      authorInput.value = meta["Author / Creator"] || meta.Author || meta.author || meta.Artist || "";
      subjectInput.value = meta.Subject || meta.subject || meta["PDF:Subject"] || "";
      keywordsInput.value = meta.Keywords || meta.keywords || meta["PDF:Keywords"] || "";
    }

    function checkGps(filePath, meta) {
      window.FOSS.api("metadata_gps_preview", { file_path: filePath, metadata: meta }).then(function (res) {
        var gps = res && res.gps;
        currentGps = gps;
        var coordsEl = document.getElementById("metadata-gps-coords");
        if (gps && gps.has_gps) {
          if (coordsEl) coordsEl.textContent = "Lat: " + gps.lat + ", Lon: " + gps.lon + " (" + gps.formatted + ")";
          gpsBanner.classList.remove("hidden");
          if (!gpsBanner.contains(openMapBtn)) {
            gpsBanner.appendChild(openMapBtn);
          }
          privacyBadge.className = "badge badge-danger text-xs";
          privacyBadge.textContent = "GPS Location Tags Found";
        } else {
          gpsBanner.classList.add("hidden");
          var tagCount = Object.keys(meta || {}).length;
          if (tagCount === 0) {
            privacyBadge.className = "badge badge-success text-xs";
            privacyBadge.textContent = "Clean (Zero Tags)";
          } else {
            privacyBadge.className = "badge badge-neutral text-xs";
            privacyBadge.textContent = tagCount + " Metadata Tags Found";
          }
        }
      });
    }

    function renderDiffTable(meta) {
      diffTableHost.innerHTML = "";
      var keys = Object.keys(meta || {});
      if (keys.length === 0) {
        diffTableHost.innerHTML = "<div class='text-xs text-muted p-3'>No metadata detected.</div>";
        return;
      }
      var rows = keys.map(function (k) {
        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "font-mono text-xs", text: k }),
          window.FOSS.dom.el("td", { className: "text-xs", style: "word-break: break-all;", text: String(meta[k]) }),
          window.FOSS.dom.el("td", { className: "text-xs text-success font-mono", text: "[Stripped]" })
        ]);
      });
      var tbl = window.FOSS.dom.el("table", { className: "table" }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "Field" }),
            window.FOSS.dom.el("th", { text: "Detected" }),
            window.FOSS.dom.el("th", { text: "Sanitized Output" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);
      var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
      diffTableHost.appendChild(wrap);
    }

    function saveEditsAction() {
      if (!currentFilePath) {
        statusBar.textContent = "Ready";
        return;
      }
      clearError();
      var edits = {};
      if (titleInput.value.trim()) edits.title = titleInput.value.trim();
      if (authorInput.value.trim()) edits.author = authorInput.value.trim();
      if (subjectInput.value.trim()) edits.subject = subjectInput.value.trim();
      if (keywordsInput.value.trim()) edits.keywords = keywordsInput.value.trim();

      savePathFor(currentFilePath, "Save Edited File", "edited").then(function (destPath) {
        if (!destPath) {
          statusBar.textContent = "Save cancelled";
          return;
        }
        statusBar.textContent = "Saving metadata edits...";
        return window.FOSS.api("metadata_save", { file_path: currentFilePath, updates: edits, output_path: destPath }).then(function (res) {
          if (res.ok === false) {
            showError(res.error || "Save edits failed");
            return;
          }
          showResult(res.output_path, "Saved Edited File");
          statusBar.textContent = "[OK] Saved edits to: " + res.output_path;
        });
      }).catch(function (err) {
        showError("Save edits failed: " + (err && err.message ? err.message : String(err)));
      });
    }

    function stripAction() {
      if (!currentFilePath) {
        showError("Please choose a file to strip metadata from.");
        return;
      }
      clearError();

      function doStrip(destPath) {
        statusBar.textContent = "Stripping all metadata...";
        return window.FOSS.api("metadata_strip_any", {
          file_path: currentFilePath,
          output_path: destPath,
          backup: backupSwitch.isChecked()
        }).then(function (res) {
          if (res.ok === false) {
            showError(res.error || "Stripping metadata failed");
            return;
          }
          showResult(res.output_path, "Clean Copy Saved (All Metadata Stripped)");
          var backupNote = res.backup_path ? " Backup: " + res.backup_path : "";
          statusBar.textContent = "[OK] Clean copy written: " + res.output_path + "." + backupNote;
          return window.FOSS.api("metadata_inspect", { file_path: res.output_path }).then(function (after) {
            var cleaned = (after && after.metadata) || {};
            renderInspectTable(Object.keys(cleaned).length ? cleaned : { "Status": "Sanitized (no metadata fields remain)" });
          });
        });
      }

      savePathFor(currentFilePath, "Save Clean Copy (Metadata Stripped)", "clean").then(function (destPath) {
        if (!destPath) {
          statusBar.textContent = "Save cancelled";
          return;
        }
        return doStrip(destPath);
      }).catch(function (err) {
        showError("Stripping failed: " + (err && err.message ? err.message : String(err)));
      });
    }

    if (currentFilePath) {
      loadFile(currentFilePath);
    }
  }

  // TAB 2: Batch Folder Scrub
  function renderBatchTab(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "metadata-batch-page");

    var selectedFolder = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "metadata-batch-status",
      text: "Select a folder to batch strip metadata"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "metadata-batch-error"
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

    var folderDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-xs text-muted grow",
      style: "min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      "data-testid": "metadata-batch-folder-display",
      "data-truncate-ok": "true",
      title: "No folder selected",
      text: "No folder selected"
    });

    var folderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "metadata-batch-folder-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var path = res.paths[0];
          selectedFolder = path;
          folderDisplay.textContent = path;
          folderDisplay.title = path;
          statusBar.textContent = "Selected folder: " + path;
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Folder" })
    ]);

    var recursiveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "metadata-batch-recursive",
      checked: true,
      id: "metadata-batch-rec-check"
    });

    var scanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-batch-scan-btn",
      type: "button",
      onClick: function () {
        runBatch(true);
      }
    }, [
      window.FOSS.icons.el("search", 14),
      window.FOSS.dom.el("span", { text: "Scan Folder (Dry Run)" })
    ]);

    var scrubBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "metadata-batch-scrub-btn",
      type: "button",
      onClick: function () {
        runBatch(false);
      }
    }, [
      window.FOSS.icons.el("trash", 14),
      window.FOSS.dom.el("span", { text: "Scrub Metadata" })
    ]);

    var leftCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Batch Scrub Settings" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [folderBtn, folderDisplay]),
      window.FOSS.dom.el("label", { className: "row gap-2 items-center text-xs" }, [
        recursiveCheck,
        window.FOSS.dom.el("span", { text: "Include Subfolders" })
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2 pt-sm" }, [scanBtn, scrubBtn])
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "metadata-sidebar-pane"
    }, [leftCard]);

    var tableHost = window.FOSS.dom.el("div", {
      className: "table-wrap grow",
      style: "min-height: 12rem;",
      "data-testid": "metadata-batch-table"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs text-muted p-3", text: "No scan or scrub results yet." })
    ]);

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "box-sizing: border-box; min-width: 0;"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Batch Scan & Scrub Results" }),
      tableHost
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "metadata-stage-pane grow"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable metadata-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(split);

    function runBatch(preview) {
      if (!selectedFolder) {
        showError("Please choose a folder to batch scrub.");
        return;
      }
      clearError();
      statusBar.textContent = (preview ? "Scanning folder: " : "Scrubbing folder: ") + selectedFolder + "...";
      window.FOSS.api("metadata_batch_cleanup", {
        input_dir: selectedFolder,
        recursive: recursiveCheck.checked,
        preview: preview
      }).then(function (res) {
        if (res.ok === false) {
          showError(res.error || "Batch operation failed");
          return;
        }
        var results = res.results || {};
        var fileList = results.files || [];
        statusBar.textContent = "[OK] Processed " + (results.processed || 0) + ", skipped " + (results.skipped || 0) + ", errors " + (results.errors || 0);

        tableHost.innerHTML = "";
        if (!fileList.length) {
          tableHost.innerHTML = "<div class='text-xs text-muted p-3'>No files processed in selected folder.</div>";
          return;
        }

        var rows = fileList.map(function (f) {
          var fPath = typeof f === "string" ? f : f.path;
          var fCount = typeof f === "object" ? f.metadata_fields : "-";
          return window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", {
              className: "font-mono text-xs",
              "data-truncate-ok": "true",
              title: fPath,
              text: fPath
            }),
            window.FOSS.dom.el("td", { className: "text-xs font-mono", text: String(fCount) }),
            window.FOSS.dom.el("td", { className: "text-xs font-semibold text-success", text: preview ? "Detected" : "Cleaned" })
          ]);
        });

        var tbl = window.FOSS.dom.el("table", { className: "table" }, [
          window.FOSS.dom.el("thead", {}, [
            window.FOSS.dom.el("tr", {}, [
              window.FOSS.dom.el("th", { text: "File" }),
              window.FOSS.dom.el("th", { text: "Metadata Fields", style: "width: 8rem;" }),
              window.FOSS.dom.el("th", { text: "Status", style: "width: 6rem;" })
            ])
          ]),
          window.FOSS.dom.el("tbody", {}, rows)
        ]);
        tableHost.appendChild(tbl);
      }).catch(function (err) {
        showError("Batch failed: " + (err && err.message ? err.message : String(err)));
      });
    }
  }

  window.FOSS.router.register({
    id: "metadata",
    title: "Metadata Tools",
    navName: "Metadata",
    category: "Utilities",
    icon: "metadata",
    workbench: true,
    defaults: [
      { key: "create_backup", label: "Create backup of original file when stripping", type: "toggle", default: false }
    ],
    onFiles: function (paths) {
      if (!paths || !paths.length) return;
      window.FOSS.router.open("metadata", "inspect");
      var inspectPanel = document.querySelector("[data-testid='metadata-inspect-page']");
      if (inspectPanel && inspectPanel._loadFile) {
        inspectPanel._loadFile(paths[0]);
      }
    },
    tabs: [
      { id: "inspect", label: "Inspect, Edit & Strip", aliases: ["main", "strip"], render: renderInspectTab },
      { id: "batch", label: "Batch Folder Scrub", render: renderBatchTab }
    ]
  });
})();
