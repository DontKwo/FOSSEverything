// OCR Studio: offline text extraction from images and PDFs, searchable PDF creation, and batch OCR.
window.FOSS = window.FOSS || {};

(function () {
  var LANGUAGES = {
    eng: "English",
    spa: "Spanish",
    fra: "French",
    deu: "German",
    ita: "Italian",
    por: "Portuguese",
    chi_sim: "Chinese (Simplified)",
    chi_tra: "Chinese (Traditional)",
    jpn: "Japanese",
    kor: "Korean",
    rus: "Russian",
    ara: "Arabic",
    hin: "Hindi",
    nld: "Dutch",
    pol: "Polish",
    tur: "Turkish",
    ukr: "Ukrainian",
    vie: "Vietnamese"
  };
  var INPUT_TYPES = ["pdf", "png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp"];

  function ocrDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("ocr", key, fallback);
  }

  function languageOptions(catalog, selected) {
    return Object.keys(catalog).map(function (code) {
      return window.FOSS.dom.el("option", {
        value: code,
        text: catalog[code] + " (" + code + ")",
        selected: code === selected
      });
    });
  }

  function fillLanguages(select, catalog) {
    var keep = select.value;
    select.innerHTML = "";
    languageOptions(catalog, keep).forEach(function (opt) {
      select.appendChild(opt);
    });
    select.value = keep;
  }

  function languageDefaultOptions() {
    return Object.keys(LANGUAGES).map(function (code) {
      return { value: code, label: LANGUAGES[code] + " (" + code + ")" };
    });
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.setProperty("position", "fixed");
    ta.style.setProperty("opacity", "0");
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  // TAB 1: Document OCR
  function renderDocumentOcr(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var currentPage = 0;
    var totalPages = 1;
    var fileInspection = null;

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "ocr-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "ocr-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
      leftCol.scrollTop = 0;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "ocr-result-host"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "ocr-result-card",
        title: titleText || "OCR Completed",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
      leftCol.scrollTop = 0;
    }

    // Searchable PDF status banner
    var searchableBanner = window.FOSS.dom.el("div", {
      className: "banner info hidden",
      "data-testid": "ocr-searchable-banner"
    }, [
      window.FOSS.icons.el("info", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function updateSearchableBanner(insp) {
      if (!insp || !insp.searchable_pages || insp.searchable_pages.length === 0) {
        searchableBanner.classList.add("hidden");
        return;
      }
      var msg;
      if (insp.is_fully_searchable) {
        msg = "All " + insp.page_count + " pages are already searchable and will be preserved automatically.";
      } else {
        msg = insp.searchable_pages.length + " of " + insp.page_count + " pages already contain searchable text and will be preserved automatically.";
      }
      searchableBanner.querySelector(".banner-msg").textContent = msg;
      searchableBanner.classList.remove("hidden");
    }

    // Page preview element with zoom controls and expanded viewport
    var previewZoom = 1.0;
    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "ocr-preview-img",
      alt: "Open a document to see preview",
      className: "ocr-preview-img hidden"
    });

    var previewPlaceholder = window.FOSS.dom.el("div", {
      className: "ocr-preview-placeholder text-muted text-sm text-center",
      text: "No document loaded"
    });

    var previewCanvas = window.FOSS.dom.el("div", {
      className: "ocr-preview-canvas",
      "data-testid": "ocr-preview-canvas"
    }, [
      window.FOSS.dom.el("div", { className: "ocr-preview-scroll" }, [previewImg, previewPlaceholder])
    ]);

    var zoomLevelLabel = window.FOSS.dom.el("span", {
      className: "text-xs font-mono",
      "data-testid": "ocr-zoom-level",
      text: "100%"
    });

    function applyZoom(delta, reset) {
      if (reset) previewZoom = 1.0;
      else previewZoom = Math.min(3.0, Math.max(0.4, Math.round((previewZoom + delta) * 10) / 10));
      previewImg.style.setProperty("width", Math.round(previewZoom * 100) + "%");
      zoomLevelLabel.textContent = Math.round(previewZoom * 100) + "%";
    }

    var zoomOutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-xs btn-icon",
      title: "Zoom Out",
      "data-testid": "ocr-zoom-out",
      "aria-label": "Zoom Out",
      onclick: function () { applyZoom(-0.2, false); }
    }, [window.FOSS.icons.el("minus", 12)]);

    var zoomResetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-xs",
      title: "Reset Zoom",
      "data-testid": "ocr-zoom-reset",
      "aria-label": "Reset Zoom",
      onclick: function () { applyZoom(0, true); }
    }, [zoomLevelLabel]);

    var zoomInBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-xs btn-icon",
      title: "Zoom In",
      "data-testid": "ocr-zoom-in",
      "aria-label": "Zoom In",
      onclick: function () { applyZoom(0.2, false); }
    }, [window.FOSS.icons.el("plus", 12)]);

    var zoomControls = window.FOSS.dom.el("div", { className: "row gap-1 items-center" }, [
      zoomOutBtn,
      zoomResetBtn,
      zoomInBtn
    ]);

    var pageIndicator = window.FOSS.dom.el("span", {
      className: "text-xs font-semibold",
      "data-testid": "ocr-page-indicator",
      text: "Page 1 of 1"
    });

    var pageTypeBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral text-xs",
      "data-testid": "ocr-page-type-badge",
      text: "Scanned"
    });

    function updatePageBadge() {
      if (!fileInspection) {
        pageTypeBadge.textContent = "Scanned";
        return;
      }
      var pNum = currentPage + 1;
      if (fileInspection.searchable_pages && fileInspection.searchable_pages.indexOf(pNum) !== -1) {
        pageTypeBadge.textContent = "Searchable";
        pageTypeBadge.className = "badge badge-success text-xs";
      } else if (fileInspection.hybrid_pages && fileInspection.hybrid_pages.indexOf(pNum) !== -1) {
        pageTypeBadge.textContent = "Hybrid";
        pageTypeBadge.className = "badge badge-warning text-xs";
      } else {
        pageTypeBadge.textContent = "Scanned";
        pageTypeBadge.className = "badge badge-neutral text-xs";
      }
    }

    var prevBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-prev-btn",
      "aria-label": "Previous Page",
      title: "Previous Page",
      disabled: true,
      onclick: function () {
        if (currentPage > 0) {
          currentPage--;
          loadPagePreview();
        }
      }
    }, [window.FOSS.icons.el("arrow-left", 16), window.FOSS.dom.el("span", { text: "Previous" })]);

    var nextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-next-btn",
      "aria-label": "Next Page",
      title: "Next Page",
      disabled: true,
      onclick: function () {
        if (currentPage < totalPages - 1) {
          currentPage++;
          loadPagePreview();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "Next" }), window.FOSS.icons.el("arrow-right", 16)]);

    function loadPagePreview() {
      if (!currentFile) return;
      pageIndicator.textContent = "Page " + (currentPage + 1) + " of " + totalPages;
      prevBtn.disabled = currentPage <= 0;
      nextBtn.disabled = currentPage >= totalPages - 1;
      updatePageBadge();

      if (currentFile.toLowerCase().endsWith(".pdf")) {
        window.FOSS.api("pdf_render_page", { file_path: currentFile, page_number: currentPage }).then(function (res) {
          if (res && res.data_url) {
            previewImg.src = res.data_url;
            previewImg.classList.remove("hidden");
            previewPlaceholder.classList.add("hidden");
          }
        }).catch(function (err) {
          showError("Preview failed: " + (err.message || err));
        });
      } else {
        window.FOSS.api("ocr_preview_image", { file_path: currentFile }).then(function (res) {
          if (res && res.data_url) {
            previewImg.src = res.data_url;
            previewImg.classList.remove("hidden");
            previewPlaceholder.classList.add("hidden");
          }
        }).catch(function (err) {
          showError("Preview failed: " + (err.message || err));
        });
      }
    }

    var previewCard = window.FOSS.dom.el("div", { className: "card card-compact stack-sm ocr-preview-card" }, [
      window.FOSS.dom.el("div", { className: "row-between items-center" }, [
        window.FOSS.dom.el("h3", { className: "card-title text-base", text: "OCR Preview" }),
        window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          zoomControls,
          pageTypeBadge
        ])
      ]),
      previewCanvas,
      window.FOSS.dom.el("div", { className: "row-between" }, [
        prevBtn,
        pageIndicator,
        nextBtn
      ])
    ]);

    // OCR Settings Card
    var langSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "ocr-language",
      "aria-label": "OCR Language"
    }, languageOptions(LANGUAGES, ocrDefault("language", "eng")));
    langSelect.value = ocrDefault("language", "eng");

    window.FOSS.api("ocr_languages", {}).then(function (res) {
      if (res && res.catalog) fillLanguages(langSelect, res.catalog);
    });

    var dpiSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "ocr-dpi",
      "aria-label": "OCR DPI Resolution"
    }, [
      window.FOSS.dom.el("option", { value: "150", text: "150 DPI (Fast)" }),
      window.FOSS.dom.el("option", { value: "200", text: "200 DPI (Recommended)" }),
      window.FOSS.dom.el("option", { value: "300", text: "300 DPI (Fine Print)" })
    ]);
    dpiSelect.value = String(ocrDefault("dpi", "200"));

    var pageRangeInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      placeholder: "All (or e.g. 1-4, 7, 10-12)",
      "data-testid": "ocr-page-range",
      "aria-label": "Page selection ranges"
    });

    var forceOverwriteCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: !!ocrDefault("force_reocr", false),
      "data-testid": "ocr-force-reocr-check",
      "aria-label": "Force re-OCR on pages with existing searchable text"
    });
    var forceOverwriteLabel = window.FOSS.dom.el("label", { className: "row gap-2 text-xs" }, [
      forceOverwriteCheck,
      window.FOSS.dom.el("span", { text: "Force re-OCR on existing searchable text" })
    ]);

    var progressBar = window.FOSS.components.progress({ testid: "ocr-progress" });
    progressBar.el.classList.add("hidden");

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-extract-btn",
      disabled: true,
      onclick: function () {
        runTextExtraction();
      }
    }, [window.FOSS.icons.el("file-text", 16), window.FOSS.dom.el("span", { text: "Extract Text" })]);

    var makePdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "ocr-make-pdf-btn",
      disabled: true,
      onclick: function () {
        runMakeSearchablePdf();
      }
    }, [window.FOSS.icons.el("pdf", 16), window.FOSS.dom.el("span", { text: "Save Searchable PDF..." })]);

    var settingsCard = window.FOSS.dom.el("div", { className: "card card-compact stack-sm ocr-settings-card" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "OCR Settings" }),
      window.FOSS.dom.el("div", { className: "field" }, [
        window.FOSS.dom.el("label", { text: "Language" }),
        langSelect
      ]),
      window.FOSS.dom.el("div", { className: "field" }, [
        window.FOSS.dom.el("label", { text: "Resolution" }),
        dpiSelect
      ]),
      window.FOSS.dom.el("div", { className: "field" }, [
        window.FOSS.dom.el("label", { text: "Page Range" }),
        pageRangeInput
      ]),
      forceOverwriteLabel,
      progressBar.el,
      window.FOSS.dom.el("div", { className: "row gap-2 mt-2" }, [extractBtn, makePdfBtn])
    ]);

    // File picker
    var filePicker = window.FOSS.components.filePicker({
      testid: "ocr-file-picker",
      label: "Choose PDF or Image File",
      fileTypes: INPUT_TYPES,
      onSelect: function (file) {
        var p = typeof file === "string" ? file : (file ? file.path : "");
        if (!p) return;
        loadFile(p);
      }
    });

    function loadFile(filePath) {
      clearError();
      currentFile = filePath;
      currentPage = 0;
      extractBtn.disabled = false;
      makePdfBtn.disabled = false;
      statusBar.textContent = "Loaded: " + filePath;

      if (filePath.toLowerCase().endsWith(".pdf")) {
        window.FOSS.api("ocr_inspect_file", { file_path: filePath }).then(function (res) {
          if (res && res.page_count) {
            fileInspection = res;
            totalPages = res.page_count;
            updateSearchableBanner(res);
            loadPagePreview();
          }
        });
      } else {
        fileInspection = null;
        totalPages = 1;
        searchableBanner.classList.add("hidden");
        loadPagePreview();
      }
    }

    // Right Column: Extracted Text
    var statsBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral text-xs",
      "data-testid": "ocr-char-word-count",
      text: "0 characters / 0 words"
    });

    var textArea = window.FOSS.dom.el("textarea", {
      className: "code-editor ocr-text-area",
      "data-testid": "ocr-text-result",
      placeholder: "Extracted text appears here. Existing searchable text is preserved unless Force re-OCR is checked.",
      "aria-label": "Extracted OCR text",
      onInput: function () {
        updateTextStats();
      }
    });

    function updateTextStats() {
      var txt = textArea.value;
      var chars = txt.length;
      var words = txt.trim() ? txt.trim().split(/\s+/).length : 0;
      statsBadge.textContent = chars + " characters / " + words + " words";
    }

    var formatSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "ocr-output-format",
      "aria-label": "Output text format"
    }, [
      window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }),
      window.FOSS.dom.el("option", { value: "md", text: "Markdown (.md)" })
    ]);
    formatSelect.value = ocrDefault("output_format", "txt");

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-copy-btn",
      title: "Copy Extracted Text",
      onclick: function () {
        copyToClipboard(textArea.value);
        window.FOSS.toast.show("Copied extracted text to clipboard", "success");
      }
    }, [window.FOSS.icons.el("clipboard", 16), window.FOSS.dom.el("span", { text: "Copy" })]);

    var saveTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-save-text-btn",
      title: "Save Extracted Text File",
      onclick: function () {
        if (!textArea.value.trim()) {
          showError("No extracted text to save");
          return;
        }
        var fileTypes = [
          { name: "Plain Text (*.txt)", extensions: ["txt"] },
          { name: "Markdown (*.md)", extensions: ["md"] },
          { name: "PDF Document (*.pdf)", extensions: ["pdf"] }
        ];
        if (formatSelect.value === "md") fileTypes.unshift(fileTypes.splice(1, 1)[0]);
        window.FOSS.api("select_save_path", {
          title: "Save Extracted Text",
          default_name: "extracted_text",
          file_types: fileTypes
        }).then(function (dlg) {
          var chosenPath = (dlg && (dlg.path || dlg.file_path || dlg.output_path)) || "";
          if (!chosenPath) return;
          if (chosenPath.toLowerCase().endsWith(".pdf")) {
            runMakeSearchablePdf(chosenPath);
            return;
          }
          window.FOSS.api("write_text_file", { path: chosenPath, content: textArea.value }).then(function () {
            window.FOSS.toast.show("Saved text to " + chosenPath, "success");
          }).catch(function (err) {
            showError("Save failed: " + (err.message || err));
          });
        });
      }
    }, [window.FOSS.icons.el("save", 16), window.FOSS.dom.el("span", { text: "Save Text..." })]);

    var textCard = window.FOSS.dom.el("div", {
      className: "card card-compact stack-sm ocr-text-card"
    }, [
      window.FOSS.dom.el("div", { className: "row-between" }, [
        window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Extracted Text" }),
        statsBadge
      ]),
      textArea,
      window.FOSS.dom.el("div", { className: "row-between mt-2" }, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Format:" }),
          formatSelect
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          copyBtn,
          saveTextBtn
        ])
      ])
    ]);

    function runTextExtraction() {
      if (!currentFile) return;
      clearError();
      progressBar.el.classList.remove("hidden");
      progressBar.setIndeterminate(true);
      statusBar.textContent = "Extracting text with OCR...";

      var params = {
        file_path: currentFile,
        language: langSelect.value,
        dpi: parseInt(dpiSelect.value, 10),
        force_reocr: forceOverwriteCheck.checked,
        page_range: pageRangeInput.value.trim()
      };

      window.FOSS.api("ocr_recognize_file", params).then(function (res) {
        progressBar.el.classList.add("hidden");
        if (res && res.text !== undefined) {
          textArea.value = res.text;
          updateTextStats();
          statusBar.textContent = "Extraction complete (" + res.text.length + " chars)";
        } else {
          showError((res && res.error) || "OCR extraction failed");
        }
      }).catch(function (err) {
        progressBar.el.classList.add("hidden");
        showError(String(err));
      });
    }

    function startSearchablePdf(chosenPath) {
      progressBar.el.classList.remove("hidden");
      progressBar.setIndeterminate(true);
      statusBar.textContent = "Generating searchable PDF...";

      var params = {
        input_path: currentFile,
        output_path: chosenPath,
        language: langSelect.value,
        dpi: parseInt(dpiSelect.value, 10),
        force_reocr: forceOverwriteCheck.checked,
        page_range: pageRangeInput.value.trim()
      };

      window.FOSS.api("ocr_create_searchable_pdf", params).then(function (res) {
        progressBar.el.classList.add("hidden");
        if (res && res.output_path) {
          showResult(res.output_path, "Searchable PDF Created");
          statusBar.textContent = "Searchable PDF generated: " + res.output_path;
        } else {
          showError((res && res.error) || "Failed to create searchable PDF");
        }
      }).catch(function (err) {
        progressBar.el.classList.add("hidden");
        showError(String(err));
      });
    }

    function runMakeSearchablePdf(presetPath) {
      if (!currentFile) return;
      clearError();
      if (presetPath) {
        startSearchablePdf(presetPath);
        return;
      }
      window.FOSS.api("select_save_path", {
        title: "Save Searchable PDF",
        default_name: "searchable",
        file_types: [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }]
      }).then(function (dlg) {
        var chosenPath = (dlg && (dlg.path || dlg.file_path || dlg.output_path)) || "";
        if (chosenPath) startSearchablePdf(chosenPath);
      });
    }

    var leftCol = window.FOSS.dom.el("div", {
      className: "ocr-left-col stack-sm"
    }, [
      errorBanner,
      resultHost,
      filePicker.el,
      searchableBanner,
      previewCard,
      settingsCard
    ]);

    var splitArea = window.FOSS.dom.el("div", {
      className: "split resizable ocr-workbench-split grow",
      "data-testid": "ocr-split"
    }, [
      leftCol,
      window.FOSS.components.splitDivider({ testid: "ocr-split-divider" }),
      textCard
    ]);

    panel.appendChild(window.FOSS.dom.el("div", { className: "stack grow ocr-panel-stack" }, [splitArea]));

    ctx.state = ctx.state || {};
    ctx.state.loadFile = loadFile;
  }

  // TAB 2: Batch OCR
  function renderBatchOcr(panel, ctx) {
    panel.innerHTML = "";
    var queue = [];

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "ocr-batch-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      errorBanner.querySelector(".banner-msg").textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "ocr-batch-result"
    });

    // Top action bar
    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-add-btn",
      onclick: function () {
        window.FOSS.api("select_files", { title: "Select Files for Batch OCR", file_types: INPUT_TYPES }).then(function (res) {
          if (res && res.paths) {
            addPathsToQueue(res.paths);
          }
        });
      }
    }, [window.FOSS.icons.el("file", 16), window.FOSS.dom.el("span", { text: "Add Files" })]);

    var recursiveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "ocr-batch-recursive",
      "aria-label": "Include subfolders when scanning folders"
    });
    var recursiveLabel = window.FOSS.dom.el("label", { className: "row gap-1 text-xs text-muted" }, [
      recursiveCheck,
      window.FOSS.dom.el("span", { text: "Include Subfolders" })
    ]);

    var addFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-add-folder-btn",
      onclick: function () {
        window.FOSS.api("select_folder", { title: "Select Folder for Batch OCR" }).then(function (res) {
          var folderP = (res && (res.path || res.folder_path || res.output_dir)) || "";
          if (folderP) {
            window.FOSS.api("ocr_scan_inputs", { paths: [folderP], recursive: recursiveCheck.checked }).then(function (scanRes) {
              if (scanRes && scanRes.paths && scanRes.paths.length > 0) {
                addPathsToQueue(scanRes.paths);
              } else {
                window.FOSS.toast.show("No supported OCR documents found.", "info");
              }
            });
          }
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "ocr-batch-clear-btn",
      onclick: function () {
        queue = [];
        renderQueueTable();
      }
    }, [window.FOSS.icons.el("trash", 16), window.FOSS.dom.el("span", { text: "Clear Queue" })]);

    var topBar = window.FOSS.dom.el("div", { className: "row-between" }, [
      window.FOSS.dom.el("div", { className: "row gap-2" }, [
        addFilesBtn,
        addFolderBtn,
        recursiveLabel
      ]),
      clearBtn
    ]);

    function addPathsToQueue(paths) {
      clearError();
      paths.forEach(function (p) {
        if (queue.indexOf(p) === -1) {
          queue.push(p);
        }
      });
      renderQueueTable();
    }

    // Options Bar
    var langSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "ocr-batch-language",
      "aria-label": "Batch OCR Language"
    }, languageOptions(LANGUAGES, ocrDefault("language", "eng")));
    langSelect.value = ocrDefault("language", "eng");

    window.FOSS.api("ocr_languages", {}).then(function (res) {
      if (res && res.catalog) fillLanguages(langSelect, res.catalog);
    });

    var dpiSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "ocr-batch-dpi",
      "aria-label": "Batch OCR Resolution"
    }, [
      window.FOSS.dom.el("option", { value: "150", text: "150 DPI" }),
      window.FOSS.dom.el("option", { value: "200", text: "200 DPI" }),
      window.FOSS.dom.el("option", { value: "300", text: "300 DPI" })
    ]);
    dpiSelect.value = String(ocrDefault("dpi", "200"));

    var formatSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "ocr-batch-format",
      "aria-label": "Batch Output Format"
    }, [
      window.FOSS.dom.el("option", { value: "pdf", text: "Searchable PDF (.pdf)", selected: true }),
      window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }),
      window.FOSS.dom.el("option", { value: "md", text: "Markdown (.md)" })
    ]);

    var outFolderInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      placeholder: "Same folder as each source file",
      "data-testid": "ocr-batch-out-folder",
      "data-truncate-ok": "true",
      title: "Batch destination folder",
      "aria-label": "Batch destination folder"
    });

    var browseFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-browse-folder",
      "aria-label": "Browse destination folder",
      title: "Browse destination folder",
      onclick: function () {
        window.FOSS.api("select_folder", { title: "Select Destination Folder" }).then(function (res) {
          var p = (res && (res.path || res.folder_path || res.output_dir)) || "";
          if (p) outFolderInput.value = p;
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse..." })]);

    var forceOverwriteCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: !!ocrDefault("force_reocr", false),
      "data-testid": "ocr-batch-force-reocr-check",
      "aria-label": "Force re-OCR existing searchable text in batch",
      title: "Force re-OCR existing searchable text in batch"
    });
    var forceOverwriteLabel = window.FOSS.dom.el("label", { className: "row gap-1 text-xs text-muted" }, [
      forceOverwriteCheck,
      window.FOSS.dom.el("span", { text: "Force re-OCR" })
    ]);

    var runBatchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-run-batch-btn",
      onclick: function () {
        executeBatch();
      }
    }, [window.FOSS.icons.el("play", 16), window.FOSS.dom.el("span", { text: "Run Batch OCR" })]);

    var optionsBar = window.FOSS.dom.el("div", { className: "card card-compact stack-sm" }, [
      window.FOSS.dom.el("div", { className: "row gap-3 wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-1 text-xs text-muted" }, [
          window.FOSS.dom.el("span", { text: "Language:" }),
          langSelect
        ]),
        window.FOSS.dom.el("div", { className: "row gap-1 text-xs text-muted" }, [
          window.FOSS.dom.el("span", { text: "DPI:" }),
          dpiSelect
        ]),
        window.FOSS.dom.el("div", { className: "row gap-1 text-xs text-muted" }, [
          window.FOSS.dom.el("span", { text: "Format:" }),
          formatSelect
        ]),
        forceOverwriteLabel
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Destination:" }),
        outFolderInput,
        browseFolderBtn,
        runBatchBtn
      ])
    ]);

    // Queue Table
    var tableHost = window.FOSS.dom.el("div", { className: "grow ocr-batch-host", "data-testid": "ocr-batch-list" });

    function renderQueueTable() {
      tableHost.innerHTML = "";
      if (queue.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", { className: "empty" }, [
          window.FOSS.icons.el("file-text", 32),
          window.FOSS.dom.el("p", { className: "empty-title", text: "Queue is empty" }),
          window.FOSS.dom.el("p", { className: "empty-desc", text: "Add files or entire folders to process with Batch OCR." })
        ]));
        return;
      }

      var rows = queue.map(function (filePath, idx) {
        var parts = filePath.replace(/\\/g, "/").split("/");
        var fileName = parts[parts.length - 1];
        var parentDir = parts.slice(0, -1).join("/");

        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "ocr-batch-remove-" + idx,
          "aria-label": "Remove file " + fileName,
          title: "Remove file " + fileName,
          onclick: function () {
            queue.splice(idx, 1);
            renderQueueTable();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { text: String(idx + 1) }),
          window.FOSS.dom.el("td", { text: fileName }),
          window.FOSS.dom.el("td", { className: "text-muted text-xs", text: parentDir }),
          window.FOSS.dom.el("td", { className: "text-muted text-xs", text: "Queued" }),
          window.FOSS.dom.el("td", {}, [removeBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", { className: "table" }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "#", style: "width: 2.5rem;" }),
            window.FOSS.dom.el("th", { text: "File / Folder" }),
            window.FOSS.dom.el("th", { text: "Location" }),
            window.FOSS.dom.el("th", { text: "Status" }),
            window.FOSS.dom.el("th", { text: "", style: "width: 3.5rem;" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);

      tableHost.appendChild(window.FOSS.dom.el("div", { className: "ocr-batch-scroll scroll-x" }, [table]));
    }

    function executeBatch() {
      if (queue.length === 0) {
        showError("Batch queue is empty. Add files or folders first.");
        return;
      }
      clearError();

      var params = {
        paths: queue.slice(),
        recursive: recursiveCheck.checked,
        language: langSelect.value,
        dpi: parseInt(dpiSelect.value, 10),
        format: formatSelect.value,
        force_reocr: forceOverwriteCheck.checked,
        output_dir: outFolderInput.value.trim() || undefined
      };

      runBatchBtn.disabled = true;
      runBatchBtn.textContent = "Processing...";

      window.FOSS.api("ocr_batch", params).then(function (res) {
        runBatchBtn.disabled = false;
        runBatchBtn.innerHTML = window.FOSS.icons.svg("play", 16) + " <span>Run Batch OCR</span>";
        if (res && res.results) {
          resultHost.innerHTML = "";
          var card = window.FOSS.components.resultCard({
            testid: "ocr-batch-result-card",
            title: "Batch OCR Completed",
            message: "Processed " + (res.count || res.results.length) + " files successfully."
          });
          resultHost.appendChild(card);
          resultHost.classList.remove("hidden");
        }
      }).catch(function (err) {
        runBatchBtn.disabled = false;
        runBatchBtn.innerHTML = window.FOSS.icons.svg("play", 16) + " <span>Run Batch OCR</span>";
        showError(String(err));
      });
    }

    panel.appendChild(window.FOSS.dom.el("div", { className: "stack grow ocr-panel-stack" }, [
      topBar,
      optionsBar,
      errorBanner,
      resultHost,
      tableHost
    ]));

    renderQueueTable();

    ctx.state = ctx.state || {};
    ctx.state.addBatchPaths = addPathsToQueue;
  }

  window.FOSS.router.register({
    id: "ocr",
    title: "OCR Studio",
    navName: "OCR",
    category: "Documents",
    icon: "ocr",
    workbench: true,
    defaults: [
      { key: "language", label: "Language", type: "select", options: languageDefaultOptions(), default: "eng" },
      {
        key: "dpi",
        label: "Resolution",
        type: "select",
        options: [
          { value: "150", label: "150 DPI" },
          { value: "200", label: "200 DPI" },
          { value: "300", label: "300 DPI" }
        ],
        default: "200"
      },
      {
        key: "output_format",
        label: "Output format",
        type: "select",
        options: [
          { value: "txt", label: "Plain Text (.txt)" },
          { value: "md", label: "Markdown (.md)" }
        ],
        default: "txt"
      },
      { key: "force_reocr", label: "Force re-OCR existing text", type: "toggle", default: false }
    ],
    description: "Extract text from scans and images; create searchable PDFs completely offline.",
    tabs: [
      { id: "document", label: "Document OCR", render: renderDocumentOcr },
      { id: "batch", label: "Batch OCR", render: renderBatchOcr }
    ],
    onFiles: function (paths, ctx) {
      if (!paths || paths.length === 0) return;
      if (paths.length === 1 && !paths[0].endsWith("/") && !paths[0].endsWith("\\")) {
        window.FOSS.router.open("ocr", "document");
        if (ctx.state && ctx.state.loadFile) {
          ctx.state.loadFile(paths[0]);
        }
      } else {
        window.FOSS.router.open("ocr", "batch");
        if (ctx.state && ctx.state.addBatchPaths) {
          ctx.state.addBatchPaths(paths);
        }
      }
    }
  });
})();
