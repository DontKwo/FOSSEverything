// Archive Studio: package, extract, inspect, and protect archives with offline security.
window.FOSS = window.FOSS || {};

(function () {
  var globalQueuedSources = [];
  var globalInspectPath = "";
  var globalInspectMembers = [];
  var globalMemberHashes = {};

  var FORMAT_LABELS = [
    { fmt: "zip", name: "ZIP Archive (*.zip)", ext: "zip" },
    { fmt: "tar", name: "TAR Archive (*.tar)", ext: "tar" },
    { fmt: "tar.gz", name: "TAR.GZ Archive (*.tar.gz)", ext: "tar.gz" },
    { fmt: "tar.xz", name: "TAR.XZ Archive (*.tar.xz)", ext: "tar.xz" },
    { fmt: "tar.bz2", name: "TAR.BZ2 Archive (*.tar.bz2)", ext: "tar.bz2" }
  ];

  function archiveFileTypes(selectedFmt) {
    var ordered = FORMAT_LABELS.slice().sort(function (a, b) {
      return (a.fmt === selectedFmt ? 0 : 1) - (b.fmt === selectedFmt ? 0 : 1);
    });
    return ordered.map(function (f) { return { name: f.name, extensions: [f.ext] }; });
  }

  function formatFromPath(path, fallback) {
    var lower = String(path || "").toLowerCase();
    if (/\.(tar\.gz|tgz)$/.test(lower)) return "tar.gz";
    if (/\.(tar\.xz|txz)$/.test(lower)) return "tar.xz";
    if (/\.(tar\.bz2|tbz2)$/.test(lower)) return "tar.bz2";
    if (/\.tar$/.test(lower)) return "tar";
    if (/\.zip$/.test(lower)) return "zip";
    return fallback;
  }

  function levelOptions() {
    var labels = { 0: "Store Only (Level 0 - Fastest)", 1: "Fastest (Level 1)", 6: "Balanced (Level 6)", 9: "Maximum (Level 9 - Smallest)" };
    var opts = [];
    for (var lvl = 0; lvl <= 9; lvl++) {
      opts.push(window.FOSS.dom.el("option", { value: String(lvl), text: labels[lvl] || "Level " + lvl }));
    }
    return opts;
  }

  function shortHash(hex) {
    return hex ? hex.slice(0, 12) + "..." : "-";
  }

  function formatBytes(bytes) {
    if (bytes === 0 || !bytes) return "0 B";
    var units = ["B", "KB", "MB", "GB", "TB"];
    var idx = Math.floor(Math.log(bytes) / Math.log(1024));
    idx = Math.min(idx, units.length - 1);
    var val = (bytes / Math.pow(1024, idx)).toFixed(idx === 0 ? 0 : 1);
    return val + " " + units[idx];
  }

  // TAB 1: Create Archive
  function renderCreate(panel, ctx) {
    panel.innerHTML = "";

    var currentSources = globalQueuedSources.slice();

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "archive-create-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "archive-create-error"
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
      "data-testid": "archive-create-result"
    });

    function showResult(path, titleText, details) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-create-result-card",
        title: titleText || "Archive Created",
        outputPath: path,
        details: details || []
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var sourceDisplay = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "archive-source-display",
      "data-truncate-ok": "true",
      title: "No sources selected",
      text: "No sources selected"
    });

    function updateSourceDisplay() {
      if (currentSources.length === 0) {
        sourceDisplay.textContent = "No sources selected";
        sourceDisplay.setAttribute("title", "No sources selected");
      } else {
        var count = currentSources.length;
        var txt = count + " item" + (count === 1 ? "" : "s") + " selected";
        sourceDisplay.textContent = txt;
        sourceDisplay.setAttribute("title", txt);
      }
      globalQueuedSources = currentSources.slice();
      renderQueueTable();
    }

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "archive-format-select",
      "aria-label": "Archive Format",
      title: "Archive Format"
    }, [
      window.FOSS.dom.el("option", { value: "zip", text: "ZIP (.zip)" }),
      window.FOSS.dom.el("option", { value: "tar.gz", text: "TAR.GZ (.tar.gz)" }),
      window.FOSS.dom.el("option", { value: "tar.xz", text: "TAR.XZ (.tar.xz)" }),
      window.FOSS.dom.el("option", { value: "tar.bz2", text: "TAR.BZ2 (.tar.bz2)" }),
      window.FOSS.dom.el("option", { value: "tar", text: "TAR (.tar)" })
    ]);
    formatSelect.value = window.FOSS.toolDefaults.get("archive", "format", "zip");

    var compSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "archive-compression-select",
      "aria-label": "Compression Level",
      title: "Compression Level"
    }, levelOptions());
    compSelect.value = String(window.FOSS.toolDefaults.get("archive", "level", 6));

    var handleAddFiles = function () {
      clearError();
      window.FOSS.api("select_files", { title: "Select Files to Archive" }).then(function (res) {
        if (!res || res.cancelled || !res.paths || !res.paths.length) return;
        res.paths.forEach(function (p) {
          if (currentSources.indexOf(p) === -1) currentSources.push(p);
        });
        updateSourceDisplay();
      });
    };

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "archive-add-files-btn",
      type: "button",
      onClick: handleAddFiles
    }, [window.FOSS.icons.el("file-plus", 16), window.FOSS.dom.el("span", { text: "Add Files..." })]);

    var chooseSourceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "archive-choose-source",
      type: "button",
      onClick: handleAddFiles
    }, [window.FOSS.icons.el("file-plus", 16), window.FOSS.dom.el("span", { text: "Add Files..." })]);

    var addFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "archive-add-folder-btn",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", { title: "Select Folder to Archive" }).then(function (res) {
          if (!res || res.cancelled || !res.path) return;
          if (currentSources.indexOf(res.path) === -1) {
            currentSources.push(res.path);
            updateSourceDisplay();
          }
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var clearQueueBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "archive-clear-queue-btn",
      type: "button",
      onClick: function () {
        currentSources = [];
        updateSourceDisplay();
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear Queue" })]);

    var createBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "archive-create-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (currentSources.length === 0) {
          showError("Please select at least one file or folder to package.");
          return;
        }
        var fmt = formatSelect.value;
        var comp = parseInt(compSelect.value, 10);
        if (isNaN(comp)) comp = 6;

        window.FOSS.api("select_save_path", {
          title: "Save Archive",
          default_name: "archive",
          file_types: archiveFileTypes(fmt)
        }).then(function (res) {
          var destPath = (res && res.path) || "";
          if (!destPath) {
            statusBar.textContent = "Save cancelled";
            return null;
          }
          statusBar.textContent = "Creating archive...";
          return window.FOSS.api("archive_create", {
            sources: currentSources,
            format: formatFromPath(destPath, fmt),
            compression_level: comp,
            output_path: destPath
          }).then(function (created) {
            if (created && created.output_path) {
              statusBar.textContent = "Archive created successfully.";
              showResult(created.output_path, "Archive Created", [
                { label: "Size", value: formatBytes(created.size_bytes) },
                { label: "SHA-256", value: created.sha256 || "" }
              ]);
            }
          });
        }).catch(function (err) {
          showError((err && err.message) || String(err));
        });
      }
    }, [window.FOSS.icons.el("archive", 16), window.FOSS.dom.el("span", { text: "Create Archive" })]);

    // Left controls pane
    var leftSettingsCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Packaging Options" }),
      window.FOSS.components.field("Archive Format", formatSelect),
      window.FOSS.components.field("Compression Level", compSelect),
      createBtn
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "archive-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [
      leftSettingsCard
    ]);

    // Right Queue Table Pane
    var queueTableHost = window.FOSS.dom.el("div", {
      className: "grow flex-col gap-2 overflow-x-auto",
      "data-testid": "archive-sources-table",
      style: "min-width: 0; width: 100%; box-sizing: border-box;"
    });

    function renderQueueTable() {
      queueTableHost.innerHTML = "";
      if (currentSources.length === 0) {
        queueTableHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-8 text-center font-mono",
          text: "Staging queue is empty. Click Add Files or Add Folder on the toolbar above."
        }));
        return;
      }
      var rows = currentSources.map(function (srcPath, idx) {
        var baseName = srcPath.split(/[/\\]/).pop() || srcPath;
        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Remove source item",
          title: "Remove from queue",
          onClick: function () {
            currentSources.splice(idx, 1);
            updateSourceDisplay();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {
            className: "font-semibold text-sm",
            style: "width: 35%; max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: baseName,
            "data-truncate-ok": "true",
            title: baseName
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs text-muted font-mono",
            style: "max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: srcPath,
            "data-truncate-ok": "true",
            title: srcPath
          }),
          window.FOSS.dom.el("td", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;" }, [removeBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", {
        className: "table w-full",
        style: "table-layout: fixed; width: 100%; min-width: 0;"
      }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 35%;", text: "Name", "data-truncate-ok": "true", title: "Name" }),
            window.FOSS.dom.el("th", { style: "width: auto;", text: "Path", "data-truncate-ok": "true", title: "Path" }),
            window.FOSS.dom.el("th", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;", text: "", "data-truncate-ok": "true", title: "Action" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);
      queueTableHost.appendChild(table);
    }

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          addFilesBtn,
          chooseSourceBtn,
          addFolderBtn
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          sourceDisplay,
          clearQueueBtn
        ])
      ]),
      queueTableHost
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "archive-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [
      stageCard
    ]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable archive-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);

    updateSourceDisplay();
  }

  // TAB 2: Extract Archive
  function renderExtract(panel, ctx) {
    panel.innerHTML = "";

    var currentArchivePath = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "archive-extract-status",
      text: "Select an archive file to extract."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "archive-extract-error"
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
      "data-testid": "archive-extract-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-extract-result-card",
        title: titleText || "Extraction Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var targetDirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono",
      "data-testid": "archive-extract-target",
      placeholder: "Destination directory",
      "aria-label": "Extraction Target Folder",
      title: "Extraction Target Folder"
    });

    var expectedShaInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono text-xs",
      "data-testid": "archive-extract-expected-sha",
      placeholder: "64-character hex digest (optional)",
      "aria-label": "Expected SHA-256",
      title: "Expected SHA-256"
    });

    var summaryText = window.FOSS.dom.el("div", {
      className: "text-sm text-muted font-mono",
      text: "No archive loaded. Choose an archive file on the left."
    });

    function loadArchiveInfo(archPath) {
      currentArchivePath = archPath;
      clearError();
      statusBar.textContent = "Inspecting archive contents...";
      window.FOSS.api("archive_list", { archive_path: archPath }).then(function (res) {
        if (res) {
          statusBar.textContent = "Archive loaded: " + (res.count || 0) + " files.";
          var fmt = res.format || "unknown";
          var sizeStr = formatBytes(res.total_size_bytes || 0);
          summaryText.innerHTML = "";
          summaryText.appendChild(window.FOSS.dom.el("div", { className: "stack-sm" }, [
            window.FOSS.dom.el("div", { text: "Archive: " + archPath.split(/[/\\]/).pop() }),
            window.FOSS.dom.el("div", { text: "Format: " + fmt.toUpperCase() }),
            window.FOSS.dom.el("div", { text: "Member Count: " + (res.count || 0) + " items" }),
            window.FOSS.dom.el("div", { text: "Uncompressed Size: " + sizeStr })
          ]));
          if (!targetDirInput.value) {
            var base = archPath.replace(/\.(tar\.gz|tar\.xz|tar\.bz2|tgz|txz|tbz2|zip|tar)$/i, "");
            targetDirInput.value = base + "_extracted";
          }
        }
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    var chooseArchiveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "archive-extract-choose",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", { title: "Select Archive File to Extract" }).then(function (res) {
          var p = (res && res.paths && res.paths[0]) || (res && res.path);
          if (p) loadArchiveInfo(p);
        });
      }
    }, [window.FOSS.icons.el("archive", 16), window.FOSS.dom.el("span", { text: "Choose Archive..." })]);

    var browseTargetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-extract-browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", { title: "Select Destination Directory" }).then(function (res) {
          if (res && res.path) targetDirInput.value = res.path;
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Browse Folder..." })]);

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "archive-extract-run-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (!currentArchivePath) {
          showError("Please choose an archive file first.");
          return;
        }
        var targetDir = targetDirInput.value.trim();
        statusBar.textContent = "Extracting archive safely...";
        window.FOSS.job("archive_extract", {
          archive_path: currentArchivePath,
          target_dir: targetDir,
          expected_sha256: expectedShaInput.value.trim() || undefined
        }).then(function (res) {
          if (res && res.target_dir) {
            statusBar.textContent = "Extraction complete: " + res.target_dir;
            showResult(res.target_dir, "Extraction Complete");
          }
        }).catch(function (err) {
          showError((err && err.message) || String(err));
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Extract All Files" })]);

    var leftCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Extraction Controls" }),
      chooseArchiveBtn,
      window.FOSS.dom.el("div", { className: "flex-col gap-1" }, [
        window.FOSS.components.field("Destination Folder", targetDirInput),
        browseTargetBtn
      ]),
      window.FOSS.components.field("Expected SHA-256 (Optional)", expectedShaInput),
      extractBtn
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "archive-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [leftCard]);

    var securityBadge = window.FOSS.dom.el("div", {
      className: "row gap-2 items-center text-xs text-muted mb-sm p-2",
      style: "background: var(--bg-surface-sunken); border-radius: var(--radius-sm); border: 1px solid var(--border);"
    }, [
      window.FOSS.icons.el("shield", 16),
      window.FOSS.dom.el("span", { text: "Path traversal (Zip-Slip/Tar-Slip) protection active: entries escaping destination root are rejected." })
    ]);

    var summaryCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Archive Pre-Extraction Summary" }),
      securityBadge,
      summaryText
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "archive-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [summaryCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable archive-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);
  }

  // TAB 3: Inspect & Convert
  function renderInspect(panel, ctx) {
    panel.innerHTML = "";

    var selectedMemberNames = new Set();
    var filterQuery = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "archive-inspect-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "archive-inspect-error"
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
      "data-testid": "archive-inspect-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-inspect-result-card",
        title: titleText || "Operation Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var tableHost = window.FOSS.dom.el("div", {
      className: "grow flex-col",
      "data-testid": "archive-member-table"
    });

    function renderMembersTable() {
      tableHost.innerHTML = "";
      if (globalInspectMembers.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-8 text-center font-mono",
          text: "No archive loaded. Click Choose Archive above to inspect member entries."
        }));
        return;
      }

      var filtered = globalInspectMembers.filter(function (m) {
        if (!filterQuery) return true;
        return m.path.toLowerCase().indexOf(filterQuery.toLowerCase()) !== -1;
      });

      var rows = filtered.map(function (m) {
        var isChecked = selectedMemberNames.has(m.path);
        var chk = window.FOSS.dom.el("input", {
          type: "checkbox",
          checked: isChecked,
          "aria-label": "Select member " + m.path,
          title: "Select member " + m.path,
          onChange: function (e) {
            if (e.target.checked) selectedMemberNames.add(m.path);
            else selectedMemberNames.delete(m.path);
          }
        });

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { style: "width: 2rem;" }, [chk]),
          window.FOSS.dom.el("td", { className: "font-mono text-xs", text: m.path, "data-truncate-ok": "true", title: m.path }),
          window.FOSS.dom.el("td", { className: "text-right font-mono text-xs", text: formatBytes(m.size_bytes) }),
          window.FOSS.dom.el("td", { className: "text-right font-mono text-xs text-muted", text: formatBytes(m.compressed_bytes) }),
          window.FOSS.dom.el("td", { className: "text-right font-mono text-xs", text: m.ratio_pct + "%" }),
          window.FOSS.dom.el("td", { className: "text-right font-mono text-xs text-muted", text: m.modified_iso ? m.modified_iso.slice(0, 19).replace("T", " ") : "-" }),
          window.FOSS.dom.el("td", {
            className: "font-mono text-xs text-muted",
            text: shortHash(globalMemberHashes[m.path]),
            "data-truncate-ok": "true",
            title: globalMemberHashes[m.path] || "Run Test Integrity to compute"
          })
        ]);
      });

      var table = window.FOSS.dom.el("table", { className: "table w-full" }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 2rem;" }),
            window.FOSS.dom.el("th", { text: "Path" }),
            window.FOSS.dom.el("th", { className: "text-right", text: "Size" }),
            window.FOSS.dom.el("th", { className: "text-right", text: "Compressed" }),
            window.FOSS.dom.el("th", { className: "text-right", text: "Ratio" }),
            window.FOSS.dom.el("th", { className: "text-right", text: "Modified (UTC)" }),
            window.FOSS.dom.el("th", { text: "SHA-256" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);
      tableHost.appendChild(table);
    }

    function loadInspectArchive(archPath) {
      globalInspectPath = archPath;
      clearError();
      statusBar.textContent = "Loading archive members...";
      window.FOSS.api("archive_list", { archive_path: archPath }).then(function (res) {
        if (res && res.members) {
          globalInspectMembers = res.members;
          globalMemberHashes = {};
          digestReadout.textContent = "SHA-256: not computed";
          selectedMemberNames.clear();
          statusBar.textContent = "Archive loaded: " + globalInspectMembers.length + " members.";
          renderMembersTable();
        }
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "archive-inspect-choose",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", { title: "Select Archive File to Inspect" }).then(function (res) {
          var p = (res && res.paths && res.paths[0]) || (res && res.path);
          if (p) {
            loadInspectArchive(p);
          }
        });
      }
    }, [window.FOSS.icons.el("archive", 16), window.FOSS.dom.el("span", { text: "Choose Archive..." })]);

    var testIntegrityBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-test-integrity-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (!globalInspectPath) {
          showError("Select an archive first.");
          return;
        }
        statusBar.textContent = "Testing archive integrity...";
        window.FOSS.api("archive_test", { archive_path: globalInspectPath }).then(function (res) {
          if (!(res && res.valid)) {
            showError((res && res.message) || "Integrity check failed.");
            return null;
          }
          var entryCount = res.details && res.details.count !== undefined ? res.details.count : 0;
          statusBar.textContent = "Integrity check passed: all " + entryCount + " entries valid.";
          return window.FOSS.api("archive_checksums", { archive_path: globalInspectPath }).then(function (sums) {
            if (!sums) return;
            globalMemberHashes = {};
            (sums.members || []).forEach(function (entry) { globalMemberHashes[entry.path] = entry.sha256; });
            digestReadout.textContent = "SHA-256: " + sums.archive_sha256;
            digestReadout.setAttribute("title", sums.archive_sha256);
            renderMembersTable();
          });
        }).catch(function (err) {
          showError((err && err.message) || String(err));
        });
      }
    }, [window.FOSS.icons.el("check", 14), window.FOSS.dom.el("span", { text: "Test Integrity" })]);

    var digestReadout = window.FOSS.dom.el("div", {
      className: "font-mono text-xs text-muted",
      "data-testid": "archive-sha256-readout",
      "data-truncate-ok": "true",
      title: "SHA-256 digest of the archive file",
      text: "SHA-256: not computed"
    });

    var expectedHashInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm font-mono",
      "data-testid": "archive-inspect-expected-sha",
      placeholder: "Expected SHA-256 digest...",
      "aria-label": "Expected SHA-256",
      title: "Expected SHA-256"
    });

    var verifyHashBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-verify-sha-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (!globalInspectPath) {
          showError("Select an archive first.");
          return;
        }
        var expected = expectedHashInput.value.trim();
        if (!expected) {
          showError("Enter an expected SHA-256 digest to compare.");
          return;
        }
        window.FOSS.api("archive_verify_sha256", {
          archive_path: globalInspectPath,
          expected_sha256: expected
        }).then(function (res) {
          digestReadout.textContent = "SHA-256: " + res.actual;
          digestReadout.setAttribute("title", res.actual);
          if (res.valid) {
            statusBar.textContent = "SHA-256 match: archive digest equals the expected value.";
          } else {
            showError("SHA-256 mismatch: archive digest differs from the expected value.");
          }
        }).catch(function (err) {
          showError((err && err.message) || String(err));
        });
      }
    }, [window.FOSS.icons.el("shield", 14), window.FOSS.dom.el("span", { text: "Verify SHA-256" })]);

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm font-mono",
      "data-testid": "archive-inspect-filter",
      placeholder: "Filter members...",
      "aria-label": "Filter members",
      title: "Filter members",
      onInput: function (e) {
        filterQuery = e.target.value.trim();
        renderMembersTable();
      }
    });

    var extractSelectedBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-extract-selected-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (!globalInspectPath) {
          showError("Select an archive first.");
          return;
        }
        var membersList = Array.from(selectedMemberNames);
        if (membersList.length === 0) {
          showError("Select at least one member checkbox to extract.");
          return;
        }
        window.FOSS.api("select_folder", {
          title: "Select Destination Directory for Selected Members"
        }).then(function (res) {
          var targetDir = res && res.path;
          if (!targetDir) return;
          statusBar.textContent = "Extracting " + membersList.length + " selected members...";
          window.FOSS.job("archive_extract_selected", {
            archive_path: globalInspectPath,
            members: membersList,
            target_dir: targetDir
          }).then(function (res) {
            if (res && res.target_dir) {
              statusBar.textContent = "Extracted " + membersList.length + " members: " + res.target_dir;
              showResult(res.target_dir, "Selected Members Extracted");
            }
          }).catch(function (err) {
            showError((err && err.message) || String(err));
          });
        });
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Extract Selected..." })]);

    var convertTargetSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "archive-convert-fmt-select",
      "aria-label": "Convert Target Format",
      title: "Convert Target Format"
    }, [
      window.FOSS.dom.el("option", { value: "zip", text: "To ZIP (.zip)" }),
      window.FOSS.dom.el("option", { value: "tar.gz", text: "To TAR.GZ (.tar.gz)" }),
      window.FOSS.dom.el("option", { value: "tar.xz", text: "To TAR.XZ (.tar.xz)" }),
      window.FOSS.dom.el("option", { value: "tar.bz2", text: "To TAR.BZ2 (.tar.bz2)" })
    ]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-convert-btn",
      type: "button",
      onClick: function () {
        clearError();
        if (!globalInspectPath) {
          showError("Select an archive first.");
          return;
        }
        var targetFmt = convertTargetSelect.value;
        window.FOSS.api("select_save_path", {
          title: "Select Converted Archive Location",
          default_name: "converted",
          file_types: archiveFileTypes(targetFmt)
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Converting archive format...";
            window.FOSS.job("archive_convert", {
              archive_path: globalInspectPath,
              output_path: res.path
            }).then(function (convRes) {
              if (convRes && convRes.output_path) {
                statusBar.textContent = "Archive converted: " + convRes.output_path;
                showResult(convRes.output_path, "Archive Converted");
              }
            }).catch(function (err) {
              showError((err && err.message) || String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("refresh-cw", 14), window.FOSS.dom.el("span", { text: "Convert Archive..." })]);

    var inspectCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          chooseBtn,
          testIntegrityBtn,
          extractSelectedBtn
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          filterInput,
          convertTargetSelect,
          convertBtn
        ])
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        expectedHashInput,
        verifyHashBtn
      ]),
      digestReadout,
      tableHost
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(inspectCard);

    if (globalInspectMembers.length > 0) {
      renderMembersTable();
    }
  }

  // Register Router
  window.FOSS.router.register({
    id: "archive",
    title: "Archive Studio",
    navName: "Archive",
    category: "Utilities",
    icon: "archive",
    workbench: true,
    defaults: [
      { key: "format", label: "Default archive format", type: "select", options: ["zip", "tar.gz"], default: "zip" },
      { key: "level", label: "Default compression level", type: "number", min: 0, max: 9, step: 1, default: 6 }
    ],
    onFiles: function (paths) {
      if (!paths || paths.length === 0) return;
      var first = paths[0];
      var lower = first.toLowerCase();
      var isArchive = lower.endsWith(".zip") || lower.endsWith(".tar") || lower.endsWith(".tar.gz") ||
        lower.endsWith(".tgz") || lower.endsWith(".tar.xz") || lower.endsWith(".txz") ||
        lower.endsWith(".tar.bz2") || lower.endsWith(".tbz2") || lower.endsWith(".fossbundle") ||
        lower.endsWith(".enc");
      if (isArchive) {
        window.FOSS.router.open("archive", "inspect");
      } else {
        globalQueuedSources = paths.slice();
        window.FOSS.router.open("archive", "create");
      }
    },
    tabs: [
      { id: "create", label: "Create Archive", render: renderCreate },
      { id: "extract", label: "Extract Archive", render: renderExtract },
      { id: "inspect", label: "Inspect Contents", render: renderInspect }
    ]
  });
})();
