// Markdown Studio workspace: editing, live preview, formatting, HTML and PDF export.
window.FOSS = window.FOSS || {};

(function () {
  function calcPreviewDoc(bodyHtml) {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    var bg = isDark ? "#0d1322" : "#ffffff";
    var fg = isDark ? "#e6edf3" : "#1f2328";
    var border = isDark ? "#30363d" : "#d0d7de";
    var codeBg = isDark ? "#161b22" : "#f6f8fa";
    var linkColor = isDark ? "#58a6ff" : "#0969da";

    return "<!DOCTYPE html><html><head><meta charset=\"utf-8\">" +
      "<style>" +
      "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; " +
      "line-height: 1.6; color: " + fg + "; background: " + bg + "; padding: 16px; margin: 0; word-break: break-word; } " +
      "a { color: " + linkColor + "; } " +
      "code { background: " + codeBg + "; padding: 2px 5px; border-radius: 4px; font-size: 85%; } " +
      "pre code { display: block; padding: 12px; overflow-x: auto; } " +
      "blockquote { border-left: 4px solid " + border + "; margin: 0; padding-left: 16px; color: #888; } " +
      "table { border-collapse: collapse; width: 100%; margin: 16px 0; } " +
      "th, td { border: 1px solid " + border + "; padding: 8px 12px; text-align: left; } " +
      "img { max-width: 100%; height: auto; } " +
      "</style></head><body>" + (bodyHtml || "<p style=\"color:#888;font-style:italic;\">Preview is empty</p>") + "</body></html>";
  }

  function renderMain(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Interactive Markdown editor with live preview, syntax formatting, and export to HTML and PDF."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "markdown-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "markdown-status",
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
      "data-testid": "markdown-result-host"
    });

    var editor = window.FOSS.components.codeEditor({
      testid: "markdown-editor",
      title: "Markdown Source",
      placeholder: "type or paste markdown here",
      ariaLabel: "Markdown source editor",
      onChange: function () {
        schedulePreview();
      }
    });

    var previewIframe = window.FOSS.dom.el("iframe", {
      className: "markdown-preview-frame",
      "data-testid": "markdown-preview-frame",
      sandbox: "allow-same-origin allow-scripts",
      title: "Markdown preview"
    });

    var previewTimer = null;
    function schedulePreview() {
      clearTimeout(previewTimer);
      previewTimer = setTimeout(function () {
        updatePreview();
      }, 150);
    }

    function updatePreview() {
      var mdText = editor.getValue();
      if (!mdText.trim()) {
        previewIframe.srcdoc = calcPreviewDoc("");
        statusBar.textContent = "Preview ready";
        return;
      }
      window.FOSS.api("markdown_to_html", { markdown: mdText }).then(function (res) {
        if (res && res.html !== undefined) {
          previewIframe.srcdoc = calcPreviewDoc(res.html);
          statusBar.textContent = "Preview updated";
        }
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function wrapSelection(prefix, suffix, defaultPlaceholder) {
      var el = editor.textarea;
      var start = el.selectionStart;
      var end = el.selectionEnd;
      var val = el.value;
      var sel = val.substring(start, end);
      var insertVal = sel ? sel : defaultPlaceholder;
      var replacement = prefix + insertVal + suffix;
      el.value = val.substring(0, start) + replacement + val.substring(end);
      el.selectionStart = start + prefix.length;
      el.selectionEnd = start + prefix.length + insertVal.length;
      el.focus();
      schedulePreview();
    }

    function prefixLine(prefix, defaultText) {
      var el = editor.textarea;
      var start = el.selectionStart;
      var val = el.value;
      if (!val) {
        el.value = prefix + defaultText + "\n";
        el.selectionStart = el.selectionEnd = el.value.length;
        el.focus();
        schedulePreview();
        return;
      }
      var lineStart = val.lastIndexOf("\n", start - 1);
      lineStart = lineStart === -1 ? 0 : lineStart + 1;
      el.value = val.substring(0, lineStart) + prefix + val.substring(lineStart);
      el.selectionStart = el.selectionEnd = start + prefix.length;
      el.focus();
      schedulePreview();
    }

    function insertBlock(snippet) {
      var el = editor.textarea;
      var start = el.selectionStart;
      var val = el.value;
      var before = val.substring(0, start);
      var after = val.substring(start);
      var needsNlBefore = before.length > 0 && !before.endsWith("\n");
      var textToInsert = (needsNlBefore ? "\n\n" : "") + snippet + "\n\n";
      el.value = before + textToInsert + after;
      el.selectionStart = el.selectionEnd = start + textToInsert.length;
      el.focus();
      schedulePreview();
    }

    function makeToolbarBtn(testid, title, label, onClick) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": testid,
        "aria-label": title,
        title: title,
        type: "button",
        onClick: onClick
      }, [
        window.FOSS.dom.el("span", { text: label })
      ]);
    }

    var toolbarRow = window.FOSS.dom.el("div", {
      className: "markdown-toolbar row scroll-x",
      gap: "xs"
    }, [
      makeToolbarBtn("markdown-bold", "Bold", "Bold", function () {
        wrapSelection("**", "**", "bold text");
      }),
      makeToolbarBtn("markdown-italic", "Italic", "Italic", function () {
        wrapSelection("*", "*", "italic text");
      }),
      makeToolbarBtn("markdown-heading", "Heading", "Heading", function () {
        prefixLine("### ", "Heading");
      }),
      makeToolbarBtn("markdown-list", "Bullet List", "List", function () {
        prefixLine("- ", "List item");
      }),
      makeToolbarBtn("markdown-numlist", "Numbered List", "1. List", function () {
        prefixLine("1. ", "List item");
      }),
      makeToolbarBtn("markdown-link", "Insert Link", "Link", function () {
        wrapSelection("[", "](https://example.com)", "link text");
      }),
      makeToolbarBtn("markdown-code", "Inline Code", "Code", function () {
        wrapSelection("`", "`", "code");
      }),
      makeToolbarBtn("markdown-quote", "Blockquote", "Quote", function () {
        prefixLine("> ", "Blockquote");
      }),
      makeToolbarBtn("markdown-table", "Insert Table", "Table", function () {
        insertBlock("| Column 1 | Column 2 |\n| :--- | :--- |\n| Item 1 | Item 2 |");
      }),
      makeToolbarBtn("markdown-hr", "Horizontal Rule", "HR", function () {
        insertBlock("---");
      })
    ]);

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-open",
      "aria-label": "Open Markdown file",
      title: "Open Markdown file",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var filePath = res.paths[0];
          window.FOSS.api("read_text_file", { file_path: filePath }).then(function (readRes) {
            editor.setValue(readRes.content || "");
            schedulePreview();
            clearError();
            statusBar.textContent = "[OK] Loaded " + filePath;
          }).catch(function (err) {
            showError("Failed to read file: " + (err && err.message ? err.message : String(err)));
          });
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Open" })
    ]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-save",
      "aria-label": "Save Markdown file",
      title: "Save Markdown file",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        window.FOSS.api("select_save_path", { default_name: "document.md" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var savePath = res.paths[0];
          window.FOSS.api("write_text_file", { file_path: savePath, content: content }).then(function () {
            clearError();
            statusBar.textContent = "[OK] Saved to " + savePath;
          }).catch(function (err) {
            showError("Failed to save: " + (err && err.message ? err.message : String(err)));
          });
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Save" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "markdown-clear",
      "aria-label": "Clear editor content",
      title: "Clear editor content",
      type: "button",
      onClick: function () {
        editor.setValue("");
        updatePreview();
        clearError();
        statusBar.textContent = "Editor cleared";
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var editorFooter = window.FOSS.dom.el("div", {
      className: "row",
      gap: "sm"
    }, [openBtn, saveBtn, clearBtn]);

    var editorCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm",
      "data-testid": "markdown-card-editor"
    }, [
      window.FOSS.dom.el("h3", { className: "card-title", text: "Markdown Source" }),
      toolbarRow,
      editor.el,
      editorFooter
    ]);

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "markdown-result",
        title: titleText,
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var exportHtmlBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "markdown-export-html",
      "aria-label": "Export to HTML",
      title: "Export to HTML",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        if (!content.trim()) {
          showError("Cannot export empty Markdown document.");
          return;
        }
        window.FOSS.api("select_save_path", { default_name: "document.html" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var savePath = res.paths[0];
          window.FOSS.api("markdown_export_html", { markdown: content, output_path: savePath }).then(function () {
            clearError();
            showResult(savePath, "HTML Document Exported");
            statusBar.textContent = "[OK] Exported HTML to " + savePath;
          }).catch(function (err) {
            showError("HTML export failed: " + (err && err.message ? err.message : String(err)));
          });
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Export HTML" })
    ]);

    var exportPdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-export-pdf",
      "aria-label": "Export to PDF",
      title: "Export to PDF",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        if (!content.trim()) {
          showError("Cannot export empty Markdown document.");
          return;
        }
        window.FOSS.api("select_save_path", { default_name: "document.pdf" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var savePath = res.paths[0];
          window.FOSS.api("markdown_export_pdf", { markdown: content, output_path: savePath }).then(function () {
            clearError();
            showResult(savePath, "PDF Document Exported");
            statusBar.textContent = "[OK] Exported PDF to " + savePath;
          }).catch(function (err) {
            showError("PDF export failed: " + (err && err.message ? err.message : String(err)));
          });
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Export PDF" })
    ]);

    var previewHeader = window.FOSS.dom.el("div", {
      className: "row",
      style: "justify-content: space-between; align-items: center;"
    }, [
      window.FOSS.dom.el("h3", { className: "card-title", text: "Preview" }),
      window.FOSS.dom.el("div", { className: "row", gap: "xs" }, [exportHtmlBtn, exportPdfBtn])
    ]);

    var previewCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm",
      "data-testid": "markdown-card-preview"
    }, [
      previewHeader,
      previewIframe
    ]);

    var viewModeSegmented = window.FOSS.components.segmented({
      testid: "markdown-view-toggle",
      items: [
        { id: "both", label: "Side-by-side" },
        { id: "edit", label: "Editor" },
        { id: "preview", label: "Preview" }
      ],
      value: "both",
      onChange: function (val) {
        if (val === "both") {
          editorCard.classList.remove("hidden");
          previewCard.classList.remove("hidden");
        } else if (val === "edit") {
          editorCard.classList.remove("hidden");
          previewCard.classList.add("hidden");
        } else if (val === "preview") {
          editorCard.classList.add("hidden");
          previewCard.classList.remove("hidden");
        }
      }
    });

    var topRow = window.FOSS.dom.el("div", {
      className: "row",
      style: "justify-content: space-between; align-items: center;"
    }, [
      statusBar,
      viewModeSegmented.el
    ]);

    var splitArea = window.FOSS.dom.el("div", {
      className: "split even",
      "data-testid": "markdown-split"
    }, [
      editorCard,
      previewCard
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [
      desc,
      topRow,
      errorBanner,
      resultHost,
      splitArea
    ]));

    updatePreview();
  }

  window.FOSS.router.register({
    id: "markdown",
    title: "Markdown Studio",
    navName: "Markdown",
    category: "Documents",
    icon: "file",
    workbench: false,
    tabs: [
      { id: "main", label: "Markdown Studio", render: renderMain }
    ]
  });
})();
