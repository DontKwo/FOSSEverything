// Metadata Tools workspace: inspect, edit, strip, GPS extraction, diffing, and batch cleanup.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";

    var currentFilePath = "";
    var currentMetadata = {};

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Inspect a file before sharing it. Edit supported fields or write a clean copy."
    });

    var formatBadge = window.FOSS.dom.el("div", {
      className: "badge badge-neutral",
      "data-testid": "metadata-format-badge",
      text: "PDF, image, audio, and video files are supported locally."
    });

    var warningBanner = window.FOSS.dom.el("div", {
      className: "banner info",
      "data-testid": "metadata-warning-banner"
    }, [
      window.FOSS.icons.el("info", 18),
      window.FOSS.dom.el("span", {
        className: "banner-msg",
        text: "Notice: Metadata removal strips headers and tags, but does not remove visible PDF page content, annotations, or attachments."
      })
    ]);

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "metadata-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "metadata-status",
      text: "Ready"
    });

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

    var pathDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
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

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-browse-btn",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        browseAction();
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    function browseAction() {
      window.FOSS.api("select_file", {}).then(function (res) {
        if (!res || res.cancelled || !res.paths || !res.paths.length) return;
        loadFile(res.paths[0]);
      });
    }

    var pickerCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Select File to Inspect" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm", style: "align-items: center;" }, [
        pathDisplay,
        chooseBtn,
        browseBtn
      ])
    ]);

    var inspectTableHost = window.FOSS.dom.el("div", {
      className: "table-wrap",
      "data-testid": "metadata-inspect-table"
    });

    var titleInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "metadata-pdf-title-input",
      placeholder: "Document Title",
      "aria-label": "Document Title"
    });

    var authorInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "metadata-author-input",
      placeholder: "Author",
      "aria-label": "Author"
    });

    var subjectInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "metadata-subject-input",
      placeholder: "Subject",
      "aria-label": "Subject"
    });

    var keywordsInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "metadata-keywords-input",
      placeholder: "Keywords (comma separated)",
      "aria-label": "Keywords"
    });

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "metadata-save-btn",
      "aria-label": "Save edited metadata",
      title: "Save edited metadata",
      type: "button",
      onClick: function () {
        if (!currentFilePath) return;
        var updates = {};
        if (titleInput.value) updates.Title = titleInput.value;
        if (authorInput.value) updates.Author = authorInput.value;
        if (subjectInput.value) updates.Subject = subjectInput.value;
        if (keywordsInput.value) updates.Keywords = keywordsInput.value;

        window.FOSS.api("metadata_save", { file_path: currentFilePath, updates: updates }).then(function (res) {
          clearError();
          showResult(res.output_path, "Metadata Saved to New File");
          statusBar.textContent = "[OK] Saved edits to " + res.output_path;
        }).catch(function (err) {
          showError("Save error: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Save Edits" })
    ]);

    var stripBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-strip-btn",
      "aria-label": "Strip image EXIF metadata",
      title: "Strip image EXIF metadata",
      type: "button",
      onClick: function () {
        executeStrip("Clean Image Copy Created");
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Strip Image Metadata" })
    ]);

    var stripPdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-strip-pdf-btn",
      "aria-label": "Strip PDF Info/XMP metadata",
      title: "Strip PDF Info/XMP metadata",
      type: "button",
      onClick: function () {
        executeStrip("Clean PDF Copy Created");
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Strip PDF Metadata" })
    ]);

    function executeStrip(titleText) {
      if (!currentFilePath) return;
      window.FOSS.api("metadata_strip", { file_path: currentFilePath }).then(function (res) {
        clearError();
        showResult(res.output_path, titleText);
        statusBar.textContent = "[OK] Clean file written to " + res.output_path;
      }).catch(function (err) {
        showError("Strip error: " + (err && err.message ? err.message : String(err)));
      });
    }

    var editForm = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm",
      "data-testid": "metadata-edit-form"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Edit Standard Metadata Fields" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [titleInput, authorInput]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [subjectInput, keywordsInput]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [saveBtn, stripBtn, stripPdfBtn])
    ]);

    var gpsDetails = window.FOSS.dom.el("div", {
      className: "text-sm font-mono",
      "data-testid": "metadata-gps-details",
      text: "No GPS coordinates present in inspected file."
    });

    var openMapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "metadata-open-map",
      "aria-label": "Open in browser map",
      title: "Open in browser map",
      type: "button",
      onClick: function () {
        window.FOSS.api("open_path", { path: "https://www.openstreetmap.org" });
      }
    }, [
      window.FOSS.icons.el("external", 16),
      window.FOSS.dom.el("span", { text: "Open in Browser Map" })
    ]);

    var gpsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm",
      "data-testid": "metadata-gps-card"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "GPS Location & Geodata" }),
      gpsDetails,
      openMapBtn
    ]);

    var diffTableHost = window.FOSS.dom.el("div", {
      className: "table-wrap",
      "data-testid": "metadata-diff-table"
    });

    var diffCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Metadata Diff & Backend Safety Report" }),
      diffTableHost
    ]);

    var recursiveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "metadata-recursive-check",
      "aria-label": "include subfolders"
    });

    var batchStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "metadata-batch-status",
      text: "Ready for folder cleanup"
    });

    var batchCleanupBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "metadata-batch-cleanup-btn",
      "aria-label": "Browse folder and clean metadata",
      title: "Browse folder and clean metadata",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (r) {
          if (!r || r.cancelled || !r.paths || !r.paths.length) return;
          var inDir = r.paths[0];
          window.FOSS.api("metadata_batch_cleanup", {
            input_dir: inDir,
            recursive: recursiveCheck.checked,
            preview: false
          }).then(function (res) {
            batchStatus.textContent = "[OK] Cleaned folder: " + inDir;
          });
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Batch Folder Cleanup" })
    ]);

    var batchCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Batch Folder Metadata Cleanup" }),
      window.FOSS.dom.el("p", {
        className: "text-xs text-muted",
        text: "Strips metadata from every supported file in a folder. Outputs are written to a separate folder; originals are untouched."
      }),
      window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [
        recursiveCheck,
        window.FOSS.dom.el("span", { className: "text-sm", text: "Include Subfolders" })
      ]),
      batchCleanupBtn,
      batchStatus
    ]);

    function loadFile(filePath) {
      currentFilePath = filePath;
      pathDisplay.textContent = filePath;
      pathDisplay.title = filePath;

      window.FOSS.api("metadata_inspect", { file_path: filePath }).then(function (res) {
        currentMetadata = res.metadata || {};
        renderInspectTable(currentMetadata);
        renderSafetyReport(filePath);
        checkGps(currentMetadata);
        populateEditForm(currentMetadata);
        statusBar.textContent = "[OK] Inspected: " + filePath;
      }).catch(function (err) {
        showError("Inspect failed: " + (err && err.message ? err.message : String(err)));
      });
    }

    function renderInspectTable(meta) {
      inspectTableHost.innerHTML = "";
      var entries = Object.entries(meta);
      if (!entries.length) {
        inspectTableHost.innerHTML = "<div class='text-xs text-muted p-3'>No metadata tags found.</div>";
        return;
      }
      var rows = entries.map(function (e) {
        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "font-mono text-xs", text: String(e[0]) }),
          window.FOSS.dom.el("td", { className: "text-sm", text: String(e[1]), style: "word-break: break-all;" })
        ]);
      });
      var tbl = window.FOSS.dom.el("table", { className: "table" }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "Tag" }),
            window.FOSS.dom.el("th", { text: "Value" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);
      inspectTableHost.appendChild(tbl);
    }

    function populateEditForm(meta) {
      titleInput.value = meta.Title || meta["PDF:Title"] || meta["Exif.Image.DocumentName"] || "";
      authorInput.value = meta.Author || meta["PDF:Author"] || meta["Exif.Image.Artist"] || "";
      subjectInput.value = meta.Subject || meta["PDF:Subject"] || "";
      keywordsInput.value = meta.Keywords || meta["PDF:Keywords"] || "";
    }

    function checkGps(meta) {
      window.FOSS.api("metadata_gps_preview", { metadata: meta }).then(function (res) {
        if (res && res.gps) {
          gpsDetails.textContent = "Coordinates: " + res.gps.latitude + ", " + res.gps.longitude + " (" + (res.gps.formatted || "GPS Tag Present") + ")";
        } else {
          gpsDetails.textContent = "No GPS coordinates present in inspected file.";
        }
      });
    }

    function renderSafetyReport(filePath) {
      window.FOSS.api("metadata_support_report", { file_path: filePath }).then(function (res) {
        diffTableHost.innerHTML = "";
        var rows = [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", { text: "File Kind" }),
            window.FOSS.dom.el("td", { className: "font-mono text-sm", text: res.kind || "Standard" })
          ]),
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", { text: "Backend Safety" }),
            window.FOSS.dom.el("td", { className: "text-sm", text: res.safe_to_strip ? "Safe for in-place or copy stripping" : "Review fields before stripping" })
          ])
        ];
        var tbl = window.FOSS.dom.el("table", { className: "table" }, [
          window.FOSS.dom.el("thead", {}, [
            window.FOSS.dom.el("tr", {}, [
              window.FOSS.dom.el("th", { text: "Capability" }),
              window.FOSS.dom.el("th", { text: "Safety Status" })
            ])
          ]),
          window.FOSS.dom.el("tbody", {}, rows)
        ]);
        diffTableHost.appendChild(tbl);
      });
    }

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [
      desc,
      formatBadge,
      warningBanner,
      errorBanner,
      resultHost,
      pickerCard,
      inspectTableHost,
      editForm,
      gpsCard,
      diffCard,
      batchCard,
      statusBar
    ]));
  }

  window.FOSS.router.register({
    id: "metadata",
    title: "Metadata Tools",
    navName: "Metadata",
    category: "Utilities",
    icon: "file",
    workbench: false,
    tabs: [
      { id: "main", label: "Inspect & Edit", render: renderMain }
    ]
  });
})();
