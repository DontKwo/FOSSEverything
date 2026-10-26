// OCR Studio: offline text extraction from images and PDFs, searchable PDF creation, and batch OCR.
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
  // TAB 1: Document OCR
  // ==========================================
  function renderDocumentOcr(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var currentPage = 0;
    var totalPages = 1;

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "OCR Studio" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "extract copyable text from scanned documents and images, or generate searchable pdfs offline." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "ocr-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "ocr-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "ocr-result-host", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "ocr-result-card", title: titleText || "OCR Completed", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Document Preview Element
    var previewCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", flex: "1 1 320px", minWidth: "280px" }
    });
    var previewHeading = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "document preview" });

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "ocr-preview-img",
      alt: "open a document to see preview",
      style: {
        maxWidth: "100%",
        maxHeight: "280px",
        objectFit: "contain",
        display: "none",
        margin: "0 auto",
        backgroundColor: "var(--bg-raised)",
        borderRadius: "var(--radius-md)"
      }
    });

    var previewPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center",
      style: { padding: "var(--space-8) var(--space-4)", backgroundColor: "var(--bg-raised)", borderRadius: "var(--radius-md)" },
      text: "no document loaded"
    });

    var pageIndicator = window.FOSS.dom.el("span", {
      className: "text-xs font-semibold",
      "data-testid": "ocr-page-indicator",
      text: "Page 1 of 1"
    });

    var prevBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-prev-btn",
      "aria-label": "◀ prev",
      title: "◀ prev",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px" },
      onClick: function () {
        if (currentPage > 0) {
          currentPage--;
          updatePreview();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "◀ prev" })]);

    var nextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-next-btn",
      "aria-label": "next ▶",
      title: "next ▶",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px" },
      onClick: function () {
        if (currentPage < totalPages - 1) {
          currentPage++;
          updatePreview();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "next ▶" })]);

    var navRow = window.FOSS.dom.el("div", {
      className: "row items-center justify-between",
      style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", marginTop: "var(--space-2)" }
    }, [prevBtn, pageIndicator, nextBtn]);

    previewCard.appendChild(previewHeading);
    previewCard.appendChild(previewPlaceholder);
    previewCard.appendChild(previewImg);
    previewCard.appendChild(navRow);

    function updatePreview() {
      if (!currentFile) {
        previewPlaceholder.style.display = "block";
        previewImg.style.display = "none";
        previewPlaceholder.textContent = "open a document to see preview";
        return;
      }
      previewPlaceholder.style.display = "none";
      previewImg.style.display = "block";
      pageIndicator.textContent = "Page " + (currentPage + 1) + " of " + totalPages;

      if (currentFile.toLowerCase().endsWith(".pdf")) {
        ctx.api("pdf_render_page", { file_path: currentFile, page_number: currentPage, dpi: 100 }).then(function (res) {
          if (res && res.ok && res.data_url) {
            previewImg.src = res.data_url;
          }
        });
      } else {
        ctx.api("images_load_data", { file_path: currentFile }).then(function (res) {
          if (res && res.ok && res.data_url) {
            previewImg.src = res.data_url;
          }
        });
      }
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "ocr-file-picker",
      title: "select a pdf or image file (png, jpg, tiff, webp, bmp, etc)",
      fileTypes: ["pdf", "png", "jpg", "jpeg", "webp", "tiff", "bmp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        currentPage = 0;
        totalPages = 1;
        statusBar.textContent = "Loaded: " + val.split(/[/\\]/).pop();

        if (val.toLowerCase().endsWith(".pdf")) {
          ctx.api("pdf_open_doc", { file_path: val }).then(function (res) {
            if (res && res.ok) {
              totalPages = res.page_count || 1;
              updatePreview();
            }
          });
        } else {
          updatePreview();
        }
      },
      onClear: function () {
        currentFile = "";
        previewImg.src = "";
        previewPlaceholder.style.display = "block";
        previewImg.style.display = "none";
        previewPlaceholder.textContent = "no document loaded";
        pageIndicator.textContent = "Page 1 of 1";
      }
    });

    // Configuration Group
    var configCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", flex: "1 1 320px", minWidth: "280px" }
    });
    var configHeading = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "ocr configuration" });

    var langSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-language",
      "aria-label": "language",
      title: "language",
      style: { minHeight: "36px", minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "eng", text: "English (eng)" }),
      window.FOSS.dom.el("option", { value: "spa", text: "Spanish (spa)" }),
      window.FOSS.dom.el("option", { value: "fra", text: "French (fra)" }),
      window.FOSS.dom.el("option", { value: "deu", text: "German (deu)" }),
      window.FOSS.dom.el("option", { value: "ita", text: "Italian (ita)" }),
      window.FOSS.dom.el("option", { value: "por", text: "Portuguese (por)" })
    ]);

    var dpiSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-dpi",
      "aria-label": "resolution",
      title: "resolution",
      style: { minHeight: "36px", minWidth: "180px" }
    }, [
      window.FOSS.dom.el("option", { value: "150", text: "standard (150 dpi) - fast" }),
      window.FOSS.dom.el("option", { value: "200", selected: true, text: "high quality (200 dpi) - recommended" }),
      window.FOSS.dom.el("option", { value: "300", text: "ultra (300 dpi) - fine text / receipts" })
    ]);

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-format",
      "aria-label": "output format",
      title: "output format",
      style: { minHeight: "36px", minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "txt", text: "plain text (.txt)" }),
      window.FOSS.dom.el("option", { value: "md", text: "markdown (.md)" }),
      window.FOSS.dom.el("option", { value: "pdf", text: "searchable pdf (.pdf)" })
    ]);

    var pageRangeInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      "data-testid": "ocr-page-range",
      placeholder: "all pages (or e.g. 1-3, 5)",
      "aria-label": "pages",
      title: "pages",
      style: { minHeight: "36px", minWidth: "160px" }
    });

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-extract-btn",
      "aria-label": "extract text (ocr)",
      title: "extract text (ocr)",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a document first.");
          return;
        }
        clearError();
        statusBar.textContent = "Running OCR recognition...";
        var dpiVal = parseInt(dpiSelect.value, 10) || 200;
        ctx.api("ocr_recognize_file", { file_path: currentFile, language: langSelect.value, dpi: dpiVal }).then(function (res) {
          if (res && res.ok) {
            var txt = res.text || "";
            textArea.value = txt;
            updateCount(txt);
            statusBar.textContent = "OCR recognition completed.";
          } else {
            showError((res && res.error) || "OCR extraction failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 18),
      window.FOSS.dom.el("span", { text: "extract text (ocr)" })
    ]);

    var makePdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "ocr-make-pdf-btn",
      "aria-label": "make searchable pdf",
      title: "make searchable pdf",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a document first.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Searchable PDF", default_name: "searchable.pdf", file_types: ["pdf"] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Synthesizing searchable PDF...";
          var dpiVal = parseInt(dpiSelect.value, 10) || 200;
          ctx.api("ocr_create_searchable_pdf", { input_path: currentFile, output_path: saveP, language: langSelect.value, dpi: dpiVal }).then(function (pres) {
            if (pres && pres.ok && pres.output_path) {
              statusBar.textContent = "Searchable PDF created.";
              showResult(pres.output_path, "Searchable PDF Created");
            } else {
              showError((pres && pres.error) || "Failed to create searchable PDF.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("layers", 18),
      window.FOSS.dom.el("span", { text: "make searchable pdf" })
    ]);

    var controlsRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("language", langSelect),
      window.FOSS.components.field("resolution", dpiSelect),
      window.FOSS.components.field("output format", formatSelect),
      window.FOSS.components.field("pages", pageRangeInput),
      extractBtn,
      makePdfBtn
    ]);

    configCard.appendChild(configHeading);
    configCard.appendChild(controlsRow);

    // Text Display & Counter Area
    var textCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { width: "100%", border: "1px solid var(--border)", padding: "var(--space-3)" }
    });

    var countLabel = window.FOSS.dom.el("span", {
      className: "text-xs text-muted font-mono",
      "data-testid": "ocr-char-word-count",
      text: "0 characters | 0 words"
    });

    function updateCount(txt) {
      var str = (txt && typeof txt === "string") ? txt : "";
      var chars = str.length;
      var words = str.trim() ? str.trim().split(/\s+/).length : 0;
      countLabel.textContent = chars + " characters | " + words + " words";
    }

    var textHeadingRow = window.FOSS.dom.el("div", {
      className: "row items-center justify-between",
      style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "extracted text" }),
      countLabel
    ]);

    var textArea = window.FOSS.dom.el("textarea", {
      className: "input scroll-y",
      "data-testid": "ocr-text-result",
      placeholder: "extracted ocr text will appear here. you can edit and format the text directly.",
      "aria-label": "extracted text",
      title: "extracted text",
      rows: 8,
      style: { width: "100%", minHeight: "160px", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", lineHeight: "1.5" },
      onInput: function () {
        updateCount(textArea.value);
      }
    });

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-copy-btn",
      "aria-label": "Copy Extracted Text",
      title: "Copy Extracted Text",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!textArea.value) return;
        copyToClipboard(textArea.value);
        statusBar.textContent = "Copied text to clipboard.";
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Copy" })
    ]);

    var saveTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-save-text-btn",
      "aria-label": "Save Extracted Text",
      title: "Save Extracted Text",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!textArea.value) {
          showError("No text to save.");
          return;
        }
        var ext = formatSelect.value === "md" ? ".md" : ".txt";
        ctx.api("select_save_path", { title: "Save OCR Text", default_name: "ocr_text" + ext, file_types: [ext.slice(1)] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          ctx.api("save_file_text", { path: saveP, content: textArea.value }).then(function (sres) {
            statusBar.textContent = "Saved extracted text to " + saveP;
            showResult(saveP, "Text File Saved");
          });
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save File" })
    ]);

    var textActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }
    }, [copyBtn, saveTextBtn]);

    textCard.appendChild(textHeadingRow);
    textCard.appendChild(textArea);
    textCard.appendChild(textActionsRow);

    var splitTop = window.FOSS.dom.el("div", {
      className: "row",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [configCard, previewCard]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(splitTop);
    panel.appendChild(textCard);
  }

  // ==========================================
  // TAB 2: Batch OCR
  // ==========================================
  function renderBatchOcr(panel, ctx) {
    panel.innerHTML = "";
    var batchFiles = [];
    var outFolder = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Batch OCR" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Queue multiple documents and images for bulk offline optical character recognition." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "ocr-batch-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "ocr-batch-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "ocr-batch-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "ocr-batch-result-card", title: titleText || "Batch Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var filesList = window.FOSS.dom.el("div", {
      className: "card flex-col gap-1 scroll-y",
      "data-testid": "ocr-batch-list",
      style: { maxHeight: "200px", minHeight: "80px", overflowY: "auto", border: "1px solid var(--border)", padding: "var(--space-2)" }
    });

    function renderBatchFiles() {
      filesList.innerHTML = "";
      if (batchFiles.length === 0) {
        filesList.appendChild(window.FOSS.dom.el("div", { className: "text-muted text-sm", text: "No files added to batch." }));
        return;
      }
      batchFiles.forEach(function (f, idx) {
        var row = window.FOSS.dom.el("div", {
          className: "row items-center justify-between",
          style: { display: "flex", justifyContent: "space-between", padding: "var(--space-1) var(--space-2)" }
        }, [
          window.FOSS.dom.el("span", { className: "text-sm", text: (idx + 1) + ". " + f.split(/[/\\]/).pop() }),
          window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Queued" })
        ]);
        filesList.appendChild(row);
      });
    }

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-add-btn",
      "aria-label": "open file",
      title: "open file",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        ctx.api("select_files", { title: "Select Documents for Batch OCR", file_types: ["pdf", "png", "jpg", "jpeg", "webp", "tiff", "bmp"] }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            batchFiles = batchFiles.concat(res.paths);
            renderBatchFiles();
            statusBar.textContent = "Added " + res.paths.length + " files. Total: " + batchFiles.length;
          }
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "open file" })
    ]);

    var folderInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      "data-testid": "ocr-batch-out-folder",
      placeholder: "save in source file folder",
      "aria-label": "output folder",
      title: "output folder",
      style: { minHeight: "36px", minWidth: "200px" }
    });

    var browseFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-browse-folder",
      "aria-label": "output folder",
      title: "output folder",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        ctx.api("select_folder", { title: "Select Output Folder" }).then(function (res) {
          var p = (res && res.paths && res.paths[0]) || "";
          if (p) {
            outFolder = p;
            folderInput.value = p;
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "output folder" })
    ]);

    var batchFormatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-batch-format",
      "aria-label": "format",
      title: "format",
      style: { minHeight: "36px", minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "pdf", text: "searchable pdf (.pdf)" }),
      window.FOSS.dom.el("option", { value: "txt", text: "plain text (.txt)" })
    ]);

    var runBatchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-run-batch-btn",
      "aria-label": "run batch ocr",
      title: "run batch ocr",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (batchFiles.length === 0) {
          showError("Add at least one document to batch.");
          return;
        }
        clearError();
        statusBar.textContent = "Processing batch OCR (" + batchFiles.length + " files)...";
        var makePdf = batchFormatSelect.value === "pdf";
        ctx.api("ocr_batch", {
          file_paths: batchFiles,
          searchable_pdf: makePdf,
          output_dir: folderInput.value.trim() || undefined
        }).then(function (bres) {
          if (bres && bres.ok) {
            statusBar.textContent = "Batch OCR completed for " + bres.count + " items.";
            showResult(folderInput.value || batchFiles[0], "Batch OCR Completed");
          } else {
            showError((bres && bres.error) || "Batch OCR failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("layers", 18),
      window.FOSS.dom.el("span", { text: "run batch ocr" })
    ]);

    var batchCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      addFilesBtn,
      window.FOSS.components.field("destination", folderInput),
      browseFolderBtn,
      window.FOSS.components.field("format", batchFormatSelect),
      runBatchBtn
    ]);

    batchCard.appendChild(toolbar);
    batchCard.appendChild(filesList);

    renderBatchFiles();

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(batchCard);
  }

  // Register OCR Tool
  window.FOSS.router.register({
    id: "ocr",
    title: "OCR Studio",
    navName: "OCR",
    category: "Documents",
    icon: "file-text",
    tabs: [
      { id: "document", label: "document ocr", render: renderDocumentOcr },
      { id: "batch", label: "batch ocr", render: renderBatchOcr }
    ]
  });
})();

