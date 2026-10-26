// Universal Office tool: text extraction, metadata reading/stripping, and format conversions (DOCX/PPTX/XLSX/ODT).
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-office");

    var currentFile = "";
    var currentExt = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Office Document Studio" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Extract structured text and metadata, export DOCX to PDF/Markdown, PPTX to outlines, and XLSX to CSV."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "office-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "office-error-banner"
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
      "data-testid": "office-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "office-result-card",
        title: titleText || "Conversion Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Card 1: File selection & Conversion
    var convertCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    convertCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Document Conversion" }));

    var fileDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "office-file-display",
      "data-truncate-ok": "true",
      title: "No office document selected",
      text: "No office document selected"
    });

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "office-choose-file",
      "aria-label": "Choose office document",
      title: "Choose office document",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentFile = res.paths[0];
          fileDisplay.textContent = currentFile;
          fileDisplay.title = currentFile;
          var dotIdx = currentFile.lastIndexOf(".");
          currentExt = dotIdx > 0 ? currentFile.substring(dotIdx).toLowerCase() : "";
          updateTargetOptions();
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Document" })
    ]);

    convertCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [
      fileDisplay,
      window.FOSS.dom.el("div", { className: "row" }, [chooseBtn])
    ]));

    var targetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "office-target-select",
      "aria-label": "Target format",
      title: "Target format"
    });

    function updateTargetOptions() {
      targetSelect.innerHTML = "";
      if (currentExt === ".docx" || currentExt === ".odt" || currentExt === ".docm") {
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "pdf", text: "PDF (.pdf)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "md", text: "Markdown (.md)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }));
      } else if (currentExt === ".pptx" || currentExt === ".odp" || currentExt === ".pptm") {
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "md", text: "Markdown Outline (.md)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }));
      } else if (currentExt === ".xlsx" || currentExt === ".ods" || currentExt === ".xlsm") {
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "csv", text: "CSV (.csv)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }));
      } else {
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "pdf", text: "PDF (.pdf)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "md", text: "Markdown (.md)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "csv", text: "CSV (.csv)" }));
        targetSelect.appendChild(window.FOSS.dom.el("option", { value: "txt", text: "Plain Text (.txt)" }));
      }
    }

    updateTargetOptions();

    var targetRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Target Format" }),
      targetSelect
    ]);
    convertCard.appendChild(targetRow);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "office-convert-btn",
      "aria-label": "Convert Document",
      title: "Convert Document",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Please choose an Office document to convert.");
          return;
        }
        clearError();
        statusBar.textContent = "Converting document...";

        var target = targetSelect.value;
        if (target === "pdf") {
          window.FOSS.api("office_docx_to_pdf", { input_path: currentFile }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "PDF export ready: " + res.output_path;
              showResult(res.output_path, "PDF Document Exported");
            } else {
              showError("Failed to convert document to PDF.");
            }
          });
        } else if (target === "md") {
          if (currentExt.indexOf("ppt") !== -1) {
            window.FOSS.api("office_pptx_to_markdown", { input_path: currentFile }).then(function (res) {
              if (res && res.output_path) {
                statusBar.textContent = "Markdown outline ready: " + res.output_path;
                showResult(res.output_path, "Markdown Outline Exported");
              } else {
                showError("Failed to convert presentation to Markdown.");
              }
            });
          } else {
            window.FOSS.api("office_docx_to_markdown", { input_path: currentFile }).then(function (res) {
              if (res && res.output_path) {
                statusBar.textContent = "Markdown export ready: " + res.output_path;
                showResult(res.output_path, "Markdown Document Exported");
              } else {
                showError("Failed to convert document to Markdown.");
              }
            });
          }
        } else if (target === "csv") {
          window.FOSS.api("office_xlsx_to_csv", { input_path: currentFile }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "CSV export ready: " + res.output_path;
              showResult(res.output_path, "Spreadsheet Sheet Exported to CSV");
            } else {
              showError("Failed to convert spreadsheet to CSV.");
            }
          });
        } else {
          // Plain text fallback
          window.FOSS.api("office_extract", { file_path: currentFile }).then(function (res) {
            if (res && res.text) {
              var txtPath = currentFile.replace(/\.[^.]+$/, ".txt");
              window.FOSS.api("write_text_file", { path: txtPath, text: res.text }).then(function () {
                statusBar.textContent = "Text extracted: " + txtPath;
                showResult(txtPath, "Plain Text Extracted");
              });
            } else {
              showError("Failed to extract plain text.");
            }
          });
        }
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Convert Document" })
    ]);

    convertCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [convertBtn]));

    // Card 2: Text Extraction & Metadata Inspection
    var extractCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    extractCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Text Extraction & Metadata" }));

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "office-extract-btn",
      "aria-label": "Extract Text and Metadata",
      title: "Extract Text and Metadata",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Please choose an Office document first.");
          return;
        }
        clearError();
        statusBar.textContent = "Extracting text and metadata...";
        window.FOSS.api("office_extract", { file_path: currentFile }).then(function (res) {
          if (!res) {
            showError("Extraction failed.");
            return;
          }
          statusBar.textContent = "Extracted " + (res.text ? res.text.length : 0) + " characters.";
          textOutput.value = res.text || "";
          renderMetaTable(res.metadata || {});
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "Extract Text & Metadata" })
    ]);

    var stripBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "office-strip-btn",
      "aria-label": "Strip Document Metadata",
      title: "Strip Document Metadata",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Please choose an Office document first.");
          return;
        }
        clearError();
        statusBar.textContent = "Stripping metadata...";
        window.FOSS.api("office_metadata", { file_path: currentFile, action: "strip" }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Stripped document saved: " + res.output_path;
            showResult(res.output_path, "Cleaned Document Ready");
          } else {
            showError("Failed to strip metadata.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Strip Metadata" })
    ]);

    extractCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [extractBtn, stripBtn]));

    var textOutput = window.FOSS.dom.el("textarea", {
      className: "input font-mono text-sm w-full",
      "data-testid": "office-text-output",
      "aria-label": "Extracted text content",
      title: "Extracted text content",
      rows: 8,
      readOnly: true,
      placeholder: "Extracted document text will appear here..."
    });
    extractCard.appendChild(textOutput);

    var metaTableWrap = window.FOSS.dom.el("div", {
      className: "table-wrap scroll-x",
      "data-testid": "office-meta-table"
    });
    extractCard.appendChild(metaTableWrap);

    function renderMetaTable(meta) {
      metaTableWrap.innerHTML = "";
      var keys = Object.keys(meta);
      if (!keys.length) {
        metaTableWrap.innerHTML = '<div class="text-xs text-muted p-2">No metadata properties found.</div>';
        return;
      }
      var tbl = window.FOSS.dom.el("table", { className: "table w-full" });
      var tbody = window.FOSS.dom.el("tbody", {});
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "font-semibold text-xs w-48 text-muted", text: k }),
          window.FOSS.dom.el("td", { className: "font-mono text-sm", style: "word-break: break-all;", text: String(meta[k]) })
        ]);
        tbody.appendChild(tr);
      }
      tbl.appendChild(tbody);
      metaTableWrap.appendChild(tbl);
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(convertCard);
    panel.appendChild(extractCard);
  }

  window.FOSS.router.register({
    id: "office",
    title: "Office Document Studio",
    navName: "Office",
    category: "system",
    icon: "file-text",
    tabs: [
      { id: "main", label: "Office Studio", render: renderMain }
    ]
  });
})();
