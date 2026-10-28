// OCR Studio: offline text extraction from images and PDFs, searchable PDF creation, and batch OCR.
window.FOSS = window.FOSS || {};

(function () {
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

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "OCR Studio" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Extract copyable text from scanned documents and images, or generate searchable PDFs offline." })
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
    var previewHeading = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Document Preview" });

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
      text: "No document loaded"
    });

    var pageIndicator = window.FOSS.dom.el("span", {
      className: "text-xs font-semibold",
      "data-testid": "ocr-page-indicator",
      text: "Page 1 of 1"
    });

    var prevBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-prev-btn",
      "aria-label": "< prev",
      title: "< prev",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px" },
      onClick: function () {
        if (currentPage > 0) {
          currentPage--;
          updatePreview();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "< prev" })]);

    var nextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-next-btn",
      "aria-label": "Next >",
      title: "Next >",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px" },
      onClick: function () {
        if (currentPage < totalPages - 1) {
          currentPage++;
          updatePreview();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "Next >" })]);

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
        previewPlaceholder.style.setProperty("display", "block");
        previewImg.style.setProperty("display", "none");
        previewPlaceholder.textContent = "open a document to see preview";
        return;
      }
      previewPlaceholder.style.setProperty("display", "none");
      previewImg.style.setProperty("display", "block");
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
        previewPlaceholder.style.setProperty("display", "block");
        previewImg.style.setProperty("display", "none");
        previewPlaceholder.textContent = "no document loaded";
        pageIndicator.textContent = "Page 1 of 1";
      }
    });

    // Configuration Group
    var configCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", flex: "1 1 320px", minWidth: "280px" }
    });
    var configHeading = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "OCR Configuration" });

    var langSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-language",
      "aria-label": "Language",
      title: "Language",
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
      "aria-label": "Resolution",
      title: "Resolution",
      style: { minHeight: "36px", minWidth: "180px" }
    }, [
      window.FOSS.dom.el("option", { value: "150", text: "Standard (150 DPI) - Fast" }),
      window.FOSS.dom.el("option", { value: "200", selected: true, text: "High Quality (200 DPI) - Recommended" }),
      window.FOSS.dom.el("option", { value: "300", text: "Ultra (300 DPI) - Fine text / Receipts" })
    ]);

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-format",
      "aria-label": "Output Format",
      title: "Output Format",
      style: { minHeight: "36px", minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }),
      window.FOSS.dom.el("option", { value: "md", text: "Markdown (.md)" }),
      window.FOSS.dom.el("option", { value: "pdf", text: "Searchable PDF (.pdf)" })
    ]);

    var pageRangeInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      "data-testid": "ocr-page-range",
      placeholder: "All pages (or e.g. 1-3, 5)",
      "aria-label": "Pages",
      title: "Pages",
      style: { minHeight: "36px", minWidth: "160px" }
    });

    var ocrProgress = window.FOSS.components.progress({
      testid: "ocr-progress",
      percent: 0,
      message: "Ready"
    });
    ocrProgress.el.classList.add("hidden");

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-extract-btn",
      "aria-label": "Extract Text (OCR)",
      title: "Extract Text (OCR)",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a document first.");
          return;
        }
        clearError();
        statusBar.textContent = "Running OCR recognition...";
        ocrProgress.el.classList.remove("hidden");
        ocrProgress.update(25, "Analyzing document structure and layout...");
        var progTimer = setInterval(function () {
          var cur = parseInt(ocrProgress.el.getAttribute("aria-valuenow") || "25", 10);
          if (cur < 85) ocrProgress.update(cur + 15, "Recognizing characters...");
        }, 300);
        var dpiVal = parseInt(dpiSelect.value, 10) || 200;
        ctx.api("ocr_recognize_file", { file_path: currentFile, language: langSelect.value, dpi: dpiVal }).then(function (res) {
          clearInterval(progTimer);
          if (res && res.ok) {
            ocrProgress.update(100, "OCR extraction complete.");
            var txt = res.text || "";
            textArea.value = txt;
            updateCount(txt);
            statusBar.textContent = "OCR recognition completed.";
          } else {
            ocrProgress.el.classList.add("hidden");
            showError((res && res.error) || "OCR extraction failed.");
          }
        }).catch(function (err) {
          clearInterval(progTimer);
          ocrProgress.el.classList.add("hidden");
          showError(err.message || "OCR extraction failed.");
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 18),
      window.FOSS.dom.el("span", { text: "Extract Text (OCR)" })
    ]);

    var makePdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "ocr-make-pdf-btn",
      "aria-label": "Make Searchable PDF",
      title: "Make Searchable PDF",
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
          ocrProgress.el.classList.remove("hidden");
          ocrProgress.update(20, "Rasterizing document pages...");
          var pdfTimer = setInterval(function () {
            var cur = parseInt(ocrProgress.el.getAttribute("aria-valuenow") || "20", 10);
            if (cur < 85) ocrProgress.update(cur + 15, "Synthesizing searchable text layer...");
          }, 350);
          var dpiVal = parseInt(dpiSelect.value, 10) || 200;
          ctx.api("ocr_create_searchable_pdf", { input_path: currentFile, output_path: saveP, language: langSelect.value, dpi: dpiVal }).then(function (pres) {
            clearInterval(pdfTimer);
            if (pres && pres.ok && pres.output_path) {
              ocrProgress.update(100, "Searchable PDF synthesized.");
              statusBar.textContent = "Searchable PDF created.";
              showResult(pres.output_path, "Searchable PDF Created");
            } else {
              ocrProgress.el.classList.add("hidden");
              showError((pres && pres.error) || "Failed to create searchable PDF.");
            }
          }).catch(function (err) {
            clearInterval(pdfTimer);
            ocrProgress.el.classList.add("hidden");
            showError(err.message || "Failed to create searchable PDF.");
          });
        });
      }
    }, [
      window.FOSS.icons.el("layers", 18),
      window.FOSS.dom.el("span", { text: "Make Searchable PDF" })
    ]);

    var controlsRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("Language", langSelect),
      window.FOSS.components.field("Resolution", dpiSelect),
      window.FOSS.components.field("Output Format", formatSelect),
      window.FOSS.components.field("Pages", pageRangeInput),
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
    panel.appendChild(ocrProgress.el);
    panel.appendChild(filePicker.el);
    panel.appendChild(splitTop);
    panel.appendChild(textCard);
  }

  // TAB 2: Batch OCR
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
      window.FOSS.dom.el("span", { text: "Open File" })
    ]);

    var folderInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      "data-testid": "ocr-batch-out-folder",
      placeholder: "Save in source file folder",
      "aria-label": "Output Folder",
      title: "Output Folder",
      style: { minHeight: "36px", minWidth: "200px" }
    });

    var browseFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "ocr-batch-browse-folder",
      "aria-label": "Output Folder",
      title: "Output Folder",
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
      window.FOSS.dom.el("span", { text: "Output Folder" })
    ]);

    var batchFormatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "ocr-batch-format",
      "aria-label": "Format",
      title: "Format",
      style: { minHeight: "36px", minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "pdf", text: "Searchable PDF (.pdf)" }),
      window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" })
    ]);

    var batchProgress = window.FOSS.components.progress({
      testid: "ocr-batch-progress",
      percent: 0,
      message: "Ready"
    });
    batchProgress.el.classList.add("hidden");

    var runBatchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "ocr-run-batch-btn",
      "aria-label": "Run Batch OCR",
      title: "Run Batch OCR",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (batchFiles.length === 0) {
          showError("Add at least one document to batch.");
          return;
        }
        clearError();
        statusBar.textContent = "Processing batch OCR (" + batchFiles.length + " files)...";
        batchProgress.el.classList.remove("hidden");
        batchProgress.update(15, "Starting batch OCR on " + batchFiles.length + " files...");
        var bTimer = setInterval(function () {
          var cur = parseInt(batchProgress.el.getAttribute("aria-valuenow") || "15", 10);
          if (cur < 85) batchProgress.update(cur + 15, "Processing batch OCR queue...");
        }, 400);
        var makePdf = batchFormatSelect.value === "pdf";
        ctx.api("ocr_batch", {
          file_paths: batchFiles,
          searchable_pdf: makePdf,
          output_dir: folderInput.value.trim() || undefined
        }).then(function (bres) {
          clearInterval(bTimer);
          if (bres && bres.ok) {
            batchProgress.update(100, "Batch OCR completed for " + bres.count + " items.");
            statusBar.textContent = "Batch OCR completed for " + bres.count + " items.";
            showResult(folderInput.value || batchFiles[0], "Batch OCR Completed");
          } else {
            batchProgress.el.classList.add("hidden");
            showError((bres && bres.error) || "Batch OCR failed.");
          }
        }).catch(function (err) {
          clearInterval(bTimer);
          batchProgress.el.classList.add("hidden");
          showError(err.message || "Batch OCR failed.");
        });
      }
    }, [
      window.FOSS.icons.el("layers", 18),
      window.FOSS.dom.el("span", { text: "Run Batch OCR" })
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
    panel.appendChild(batchProgress.el);
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

