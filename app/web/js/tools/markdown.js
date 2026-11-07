// Markdown Studio workspace: editing, live preview, formatting, HTML and PDF export.
window.FOSS = window.FOSS || {};

(function () {
  function mdDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("markdown", key, fallback);
  }

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
      "font-size: 15px; line-height: 1.6; color: " + fg + "; background: " + bg + "; padding: 20px; margin: 0; word-break: break-word; } " +
      "a { color: " + linkColor + "; text-decoration: none; } " +
      "a:hover { text-decoration: underline; } " +
      "h1, h2, h3, h4 { margin-top: 20px; margin-bottom: 12px; font-weight: 600; } " +
      "h1 { font-size: 1.8em; padding-bottom: 0.3em; border-bottom: 1px solid " + border + "; } " +
      "h2 { font-size: 1.4em; padding-bottom: 0.3em; border-bottom: 1px solid " + border + "; } " +
      "ul { list-style-type: disc; padding-left: 2em; margin-bottom: 16px; } " +
      "ul ul { list-style-type: circle; } " +
      "ul ul ul { list-style-type: square; } " +
      "ol { list-style-type: decimal; padding-left: 2em; margin-bottom: 16px; } " +
      "ol ol { list-style-type: lower-alpha; } " +
      "ol ol ol { list-style-type: lower-roman; } " +
      "li + li { margin-top: 0.25em; } " +
      ".task-list-item { list-style-type: none; margin-left: -1.25em; } " +
      ".task-list-item input { margin-right: 0.5em; vertical-align: middle; } " +
      "code { background: " + codeBg + "; padding: 2px 6px; border-radius: 4px; font-size: 85%; font-family: monospace; } " +
      "pre { background: " + codeBg + "; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 85%; margin-bottom: 16px; } " +
      "pre code { padding: 0; background: transparent; } " +
      ".code-header { background: " + codeBg + "; border: 1px solid " + border + "; border-bottom: none; padding: 4px 10px; font-size: 12px; font-family: monospace; color: #888; border-top-left-radius: 6px; border-top-right-radius: 6px; } " +
      ".code-header + pre { border-top-left-radius: 0; border-top-right-radius: 0; border: 1px solid " + border + "; } " +
      "blockquote { border-left: 4px solid " + border + "; margin: 0 0 16px 0; padding-left: 14px; color: #888; } " +
      ".markdown-alert { padding: 8px 14px; margin-bottom: 16px; border-left: 4px solid #0969da; background: " + codeBg + "; border-radius: 0 6px 6px 0; } " +
      ".markdown-alert-note { border-left-color: #0969da; } " +
      ".markdown-alert-tip { border-left-color: #1a7f37; } " +
      ".markdown-alert-important { border-left-color: #8250df; } " +
      ".markdown-alert-warning { border-left-color: #9a6700; } " +
      ".markdown-alert-caution { border-left-color: #cf222e; } " +
      ".markdown-alert-title { font-weight: 600; margin: 0 0 4px 0; } " +
      "table { border-collapse: collapse; width: 100%; margin: 16px 0; } " +
      "th, td { border: 1px solid " + border + "; padding: 8px 12px; text-align: left; } " +
      "img { max-width: 100%; height: auto; } " +
      ".footnotes { font-size: 12px; border-top: 1px solid " + border + "; padding-top: 14px; color: #888; margin-top: 24px; } " +
      ".katex-display-math { text-align: center; margin: 16px 0; font-family: 'KaTeX_Math', 'Cambria Math', 'Times New Roman', serif; font-size: 1.15em; } " +
      ".katex-inline-math { font-family: 'KaTeX_Math', 'Cambria Math', 'Times New Roman', serif; font-size: 1.05em; } " +
      ".empty-preview-note { color: #888; font-style: italic; } " +
      "</style></head><body>" + (bodyHtml || "<p class=\"empty-preview-note\">Preview is empty</p>") + "</body></html>";
  }

  function renderMain(panel, ctx) {
    panel.innerHTML = "";

    var activeFlavor = mdDefault("flavor", "gfm");

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "markdown-error"
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

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "markdown-result-host"
    });

    var statsBadge = window.FOSS.dom.el("span", {
      className: "badge badge-neutral",
      "data-testid": "markdown-stats",
      text: "0 words / 0 lines"
    });

    var editor = window.FOSS.components.codeEditor({
      testid: "markdown-editor",
      placeholder: "Type or paste Markdown here...",
      ariaLabel: "Markdown source editor",
      fillHeight: true,
      onChange: function () {
        updateStats();
        schedulePreview();
      }
    });

    function updateStats() {
      var txt = editor.getValue();
      var lines = txt ? txt.split("\n").length : 0;
      var words = txt.trim() ? txt.trim().split(/\s+/).length : 0;
      statsBadge.textContent = words + " words / " + lines + " lines";
    }

    var previewIframe = window.FOSS.dom.el("iframe", {
      className: "markdown-preview-frame grow",
      "data-testid": "markdown-preview-frame",
      sandbox: "allow-same-origin allow-scripts",
      title: "Markdown live preview"
    });

    function toggleTaskAt(index, checked) {
      var lines = editor.getValue().split("\n");
      var inFence = false;
      var seen = 0;
      for (var li = 0; li < lines.length; li++) {
        if (/^\s*(```|~~~)/.test(lines[li])) {
          inFence = !inFence;
          continue;
        }
        if (inFence) continue;
        var m = lines[li].match(/^(\s*(?:[-*+]|\d+[.)])\s+)\[[ xX]\](\s.*|)$/);
        if (!m) continue;
        if (seen === index) {
          lines[li] = m[1] + "[" + (checked ? "x" : " ") + "]" + m[2];
          editor.textarea.value = lines.join("\n");
          updateStats();
          return;
        }
        seen++;
      }
    }

    function wireTaskCheckboxes() {
      var frameDoc = previewIframe.contentDocument;
      if (!frameDoc) return;
      var boxes = frameDoc.querySelectorAll(".task-list-item input[type='checkbox']");
      Array.prototype.forEach.call(boxes, function (box, idx) {
        box.removeAttribute("disabled");
        box.addEventListener("change", function () {
          toggleTaskAt(idx, box.checked);
        });
      });
    }

    previewIframe.addEventListener("load", wireTaskCheckboxes);

    var previewTimer = null;
    function schedulePreview() {
      clearTimeout(previewTimer);
      previewTimer = setTimeout(function () {
        updatePreview();
      }, 120);
    }

    function updatePreview() {
      var mdText = editor.getValue();
      if (!mdText.trim()) {
        previewIframe.srcdoc = calcPreviewDoc("");
        return;
      }
      window.FOSS.api("markdown_to_html", { markdown: mdText, flavor: activeFlavor }).then(function (res) {
        if (res && res.html !== undefined) {
          previewIframe.srcdoc = calcPreviewDoc(res.html);
        }
      });
    }

    if (window.FOSS.store && window.FOSS.store.subscribe) {
      window.FOSS.store.subscribe("theme", function () {
        updatePreview();
      });
    }

    // Top action bar
    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-open",
      title: "Open Markdown File",
      onClick: function () {
        window.FOSS.api("select_file", { title: "Open Markdown File", file_types: ["md", "markdown", "txt"] }).then(function (res) {
          var openPath = res && res.paths && res.paths[0];
          if (openPath) {
            window.FOSS.api("read_text_file", { path: openPath }).then(function (readRes) {
              if (readRes && readRes.content !== undefined) {
                editor.setValue(readRes.content);
                updateStats();
                updatePreview();
              }
            });
          }
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Open" })]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-save",
      title: "Save Document (Ctrl+S)",
      onClick: function () {
        saveDocument("md");
      }
    }, [window.FOSS.icons.el("save", 16), window.FOSS.dom.el("span", { text: "Save..." })]);

    function saveDocument(preferred) {
      var fileTypes = [
        { name: "Markdown (*.md)", extensions: ["md"] },
        { name: "HTML Document (*.html)", extensions: ["html"] }
      ];
      if (preferred === "html") fileTypes.reverse();
      window.FOSS.api("select_save_path", {
        title: "Save Document",
        default_name: "document",
        file_types: fileTypes
      }).then(function (res) {
        var chosenPath = (res && (res.path || res.file_path || res.output_path)) || "";
        if (!chosenPath) return;
        if (chosenPath.toLowerCase().endsWith(".html")) {
          exportHtmlTo(chosenPath);
          return;
        }
        window.FOSS.api("write_text_file", { path: chosenPath, content: editor.getValue() }).then(function () {
          window.FOSS.toast.show("Saved to " + chosenPath, "success");
        }).catch(function (err) {
          showError("Save failed: " + (err.message || err));
        });
      });
    }

    var flavorSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "markdown-flavor-select",
      "aria-label": "Select Markdown flavor parser",
      title: "Markdown parser flavor",
      onChange: function (e) {
        activeFlavor = e.target.value;
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "gfm", text: "GFM", selected: activeFlavor === "gfm" }),
      window.FOSS.dom.el("option", { value: "commonmark", text: "CommonMark", selected: activeFlavor === "commonmark" }),
      window.FOSS.dom.el("option", { value: "strict", text: "Strict", selected: activeFlavor === "strict" })
    ]);

    function exportHtmlTo(chosenPath) {
      clearError();
      var mdText = editor.getValue();
      if (!mdText.trim()) {
        showError("Cannot export empty document");
        return;
      }
      window.FOSS.api("markdown_export_html", { markdown: mdText, output_path: chosenPath, flavor: activeFlavor }).then(function (res) {
        if (res && res.output_path) {
          renderExportSuccess(res.output_path);
        }
      }).catch(function (err) {
        showError("HTML export failed: " + (err.message || err));
      });
    }

    var exportHtmlBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "markdown-export-html",
      title: "Export HTML Document",
      onClick: function () {
        clearError();
        if (!editor.getValue().trim()) {
          showError("Cannot export empty document");
          return;
        }
        saveDocument("html");
      }
    }, [window.FOSS.icons.el("external", 16), window.FOSS.dom.el("span", { text: "Export HTML" })]);

    var defaultExportFormat = mdDefault("export_format", "pdf");

    var exportPdfBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "markdown-export-pdf",
      onClick: function () {
        clearError();
        var mdText = editor.getValue();
        if (!mdText.trim()) {
          showError("Cannot export empty document");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Export PDF Document",
          default_name: "document",
          file_types: [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }]
        }).then(function (dlg) {
          var chosenPath = (dlg && (dlg.path || dlg.file_path || dlg.output_path)) || "";
          if (!chosenPath) return;
          window.FOSS.api("markdown_export_pdf", { markdown: mdText, output_path: chosenPath, flavor: activeFlavor }).then(function (res) {
            if (res && res.output_path) {
              renderExportSuccess(res.output_path);
            }
          }).catch(function (err) {
            showError("PDF export failed: " + (err.message || err));
          });
        });
      }
    }, [window.FOSS.icons.el("download", 16), window.FOSS.dom.el("span", { text: "Export PDF" })]);

    function renderExportSuccess(filePath) {
      resultHost.innerHTML = "";
      resultHost.classList.remove("hidden");
      var card = window.FOSS.components.resultCard({
        testid: "markdown-result",
        title: "Export Complete",
        message: "Saved: " + filePath,
        outputPath: filePath
      });
      resultHost.appendChild(card);
    }

    var wrapSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-dense": "true",
      "data-testid": "markdown-wrap-select",
      "aria-label": "Editor line wrap mode",
      title: "Editor line wrap mode",
      onChange: function (e) {
        applyWrapMode(e.target.value);
      }
    }, [
      window.FOSS.dom.el("option", { value: "soft", text: "Wrap" }),
      window.FOSS.dom.el("option", { value: "off", text: "No wrap" })
    ]);

    function applyWrapMode(mode) {
      var wrapOff = mode === "off";
      editor.textarea.setAttribute("wrap", wrapOff ? "off" : "soft");
      editor.el.classList.toggle("markdown-editor-wrap-off", wrapOff);
      wrapSelect.value = wrapOff ? "off" : "soft";
    }

    var topBar = window.FOSS.dom.el("div", { className: "row markdown-topbar" }, [
      window.FOSS.dom.el("div", { className: "row gap-2" }, [
        openBtn,
        saveBtn,
        flavorSelect,
        wrapSelect
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2" }, [
        statsBadge,
        exportHtmlBtn,
        exportPdfBtn
      ])
    ]);

    applyWrapMode(mdDefault("line_wrap", "soft"));

    // Formatting Toolbar Helpers
    function insertSnippet(type, params) {
      clearError();
      var ta = editor.textarea;
      var selStart = ta.selectionStart;
      var selEnd = ta.selectionEnd;
      var selText = ta.value.substring(selStart, selEnd);

      var p = Object.assign({}, params || {}, { snippet_type: type, text: selText });
      window.FOSS.api("markdown_format_snippet", p).then(function (res) {
        if (res && res.snippet !== undefined) {
          var before = ta.value.substring(0, selStart);
          var after = ta.value.substring(selEnd);
          ta.value = before + res.snippet + after;
          ta.selectionStart = ta.selectionEnd = selStart + res.snippet.length;
          ta.focus();
          updateStats();
          schedulePreview();
        }
      });
    }

    function indentSelection(spaces) {
      var ta = editor.textarea;
      var selStart = ta.selectionStart;
      var selEnd = ta.selectionEnd;
      var val = ta.value;

      var lineStart = val.lastIndexOf("\n", selStart - 1) + 1;
      var lineEnd = val.indexOf("\n", selEnd);
      if (lineEnd === -1) lineEnd = val.length;

      var targetLines = val.substring(lineStart, lineEnd).split("\n");
      var modified;
      if (spaces > 0) {
        var pad = "  ";
        modified = targetLines.map(function (l) { return l.length > 0 ? pad + l : l; }).join("\n");
      } else {
        modified = targetLines.map(function (l) {
          if (l.startsWith("  ")) return l.substring(2);
          if (l.startsWith(" ")) return l.substring(1);
          return l;
        }).join("\n");
      }
      ta.value = val.substring(0, lineStart) + modified + val.substring(lineEnd);
      ta.selectionStart = lineStart;
      ta.selectionEnd = lineStart + modified.length;
      updateStats();
      schedulePreview();
    }

    // Keyboard Shortcuts & Smart List Continuation on textarea
    editor.textarea.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        indentSelection(e.shiftKey ? -2 : 2);
      } else if (e.key === "Enter") {
        var ta = editor.textarea;
        var pos = ta.selectionStart;
        var val = ta.value;
        var lineStart = val.lastIndexOf("\n", pos - 1) + 1;
        var currentLine = val.substring(lineStart, pos);

        var listMatch = currentLine.match(/^(\s*)([-*+]|\d+\.)\s+(\[[ xX]\]\s+)?(.*)$/);
        if (listMatch) {
          e.preventDefault();
          var indent = listMatch[1];
          var marker = listMatch[2];
          var task = listMatch[3];
          var content = listMatch[4];

          if (!content.trim()) {
            // Exit list item if empty
            var cleared = indent.length >= 2 ? indent.substring(2) : "";
            ta.value = val.substring(0, lineStart) + cleared + val.substring(pos);
            ta.selectionStart = ta.selectionEnd = lineStart + cleared.length;
          } else {
            var nextMarker;
            if (/^\d+\./.test(marker)) {
              var num = parseInt(marker, 10);
              nextMarker = (num + 1) + ".";
            } else {
              nextMarker = marker;
            }
            var nextTask = task ? "[ ] " : "";
            var insertStr = "\n" + indent + nextMarker + " " + nextTask;
            ta.value = val.substring(0, pos) + insertStr + val.substring(pos);
            ta.selectionStart = ta.selectionEnd = pos + insertStr.length;
          }
          updateStats();
          schedulePreview();
        }
      } else if ((e.ctrlKey || e.metaKey) && !e.altKey) {
        if (e.key === "b" || e.key === "B") {
          e.preventDefault();
          insertSnippet("wrap", { marker: "**", placeholder: "bold text" });
        } else if (e.key === "i" || e.key === "I") {
          e.preventDefault();
          insertSnippet("wrap", { marker: "*", placeholder: "italic text" });
        } else if (e.key === "k" || e.key === "K") {
          e.preventDefault();
          insertSnippet("link", { label: "link text" });
        } else if (e.key === "s" || e.key === "S") {
          e.preventDefault();
          saveDocument("md");
        }
      }
    });

    // Toolbar Buttons
    var toolbar = window.FOSS.dom.el("div", {
      className: "markdown-toolbar row gap-1",
      "data-testid": "markdown-toolbar"
    }, [
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-h1",
        title: "Heading 1",
        onClick: function () { insertSnippet("heading", { level: 1 }); }
      }, [window.FOSS.dom.el("strong", { text: "H1" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-h2",
        title: "Heading 2",
        onClick: function () { insertSnippet("heading", { level: 2 }); }
      }, [window.FOSS.dom.el("strong", { text: "H2" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-heading",
        title: "Heading 3",
        onClick: function () { insertSnippet("heading", { level: 3 }); }
      }, [window.FOSS.dom.el("strong", { text: "H3" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-bold",
        title: "Bold (Ctrl+B)",
        onClick: function () { insertSnippet("wrap", { marker: "**", placeholder: "bold text" }); }
      }, [window.FOSS.dom.el("strong", { text: "B" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-italic",
        title: "Italic (Ctrl+I)",
        onClick: function () { insertSnippet("wrap", { marker: "*", placeholder: "italic text" }); }
      }, [window.FOSS.dom.el("em", { text: "I" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-strike",
        title: "Strikethrough",
        onClick: function () { insertSnippet("wrap", { marker: "~~", placeholder: "strikethrough text" }); }
      }, [window.FOSS.dom.el("s", { text: "S" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-list",
        title: "Bullet List",
        onClick: function () { insertSnippet("list_item", { ordered: false }); }
      }, [window.FOSS.icons.el("file-text", 16), window.FOSS.dom.el("span", { text: "Bullet" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-numlist",
        title: "Numbered List",
        onClick: function () { insertSnippet("list_item", { ordered: true }); }
      }, [window.FOSS.icons.el("file-text", 16), window.FOSS.dom.el("span", { text: "1. 2." })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-tasklist",
        title: "Task Checkbox",
        onClick: function () {
          var ta = editor.textarea;
          var pos = ta.selectionStart;
          var ins = "- [ ] ";
          ta.value = ta.value.substring(0, pos) + ins + ta.value.substring(pos);
          ta.selectionStart = ta.selectionEnd = pos + ins.length;
          ta.focus();
          updateStats();
          schedulePreview();
        }
      }, [window.FOSS.icons.el("check-square", 16), window.FOSS.dom.el("span", { text: "Task" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-indent",
        title: "Indent (Tab)",
        onClick: function () { indentSelection(2); }
      }, [window.FOSS.icons.el("indent", 16)]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-outdent",
        title: "Outdent (Shift+Tab)",
        onClick: function () { indentSelection(-2); }
      }, [window.FOSS.icons.el("outdent", 16)]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-quote",
        title: "Quote Block",
        onClick: function () { insertSnippet("blockquote", {}); }
      }, [window.FOSS.dom.el("span", { text: "Quote" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-callout",
        title: "GFM Note Alert",
        onClick: function () {
          var ta = editor.textarea;
          var pos = ta.selectionStart;
          var ins = "> [!NOTE]\n> Important details here.\n\n";
          ta.value = ta.value.substring(0, pos) + ins + ta.value.substring(pos);
          ta.selectionStart = ta.selectionEnd = pos + ins.length;
          ta.focus();
          updateStats();
          schedulePreview();
        }
      }, [window.FOSS.icons.el("info", 16), window.FOSS.dom.el("span", { text: "Callout" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-code",
        title: "Inline Code",
        onClick: function () { insertSnippet("wrap", { marker: "`", placeholder: "code" }); }
      }, [window.FOSS.dom.el("code", { text: "<>" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-codeblock",
        title: "Code Block",
        onClick: function () { insertSnippet("code_block", { language: "python" }); }
      }, [window.FOSS.icons.el("code", 16), window.FOSS.dom.el("span", { text: "Block" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-table",
        title: "Insert Table",
        onClick: function () { insertSnippet("markdown_table", { rows: 2, cols: 3 }); }
      }, [window.FOSS.icons.el("columns", 16), window.FOSS.dom.el("span", { text: "Table" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-link",
        title: "Link (Ctrl+K)",
        onClick: function () { insertSnippet("link", { label: "link text" }); }
      }, [window.FOSS.icons.el("external", 16), window.FOSS.dom.el("span", { text: "Link" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-image",
        title: "Image",
        onClick: function () { insertSnippet("image", { alt: "image description" }); }
      }, [window.FOSS.icons.el("image", 16), window.FOSS.dom.el("span", { text: "Image" })]),

      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-footnote",
        title: "Footnote",
        onClick: function () {
          var ta = editor.textarea;
          var pos = ta.selectionStart;
          var ins = "[^1]\n\n[^1]: Footnote details here.\n";
          ta.value = ta.value.substring(0, pos) + ins + ta.value.substring(pos);
          ta.selectionStart = ta.selectionEnd = pos + ins.length;
          ta.focus();
          updateStats();
          schedulePreview();
        }
      }, [window.FOSS.dom.el("span", { text: "[^1]" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "markdown-hr",
        title: "Horizontal Rule",
        onClick: function () { insertSnippet("horizontal_rule", {}); }
      }, [window.FOSS.dom.el("span", { text: "---" })])
    ]);

    // Resizable Split Panes
    var editorCard = window.FOSS.dom.el("div", {
      className: "card stack-sm grow code-editor-fill",
      "data-testid": "markdown-card-editor"
    }, [
      editor.el
    ]);

    var previewCard = window.FOSS.dom.el("div", {
      className: "card stack-sm grow code-editor-fill",
      "data-testid": "markdown-preview"
    }, [
      window.FOSS.dom.el("div", { className: "row-between" }, [
        window.FOSS.dom.el("h3", { className: "card-title", text: "Live Preview" }),
        window.FOSS.dom.el("span", { className: "badge badge-neutral text-xs", text: "Auto-synced" })
      ]),
      previewIframe
    ]);

    var splitArea = window.FOSS.dom.el("div", {
      className: "split resizable even markdown-workbench-split",
      "data-testid": "markdown-split"
    }, [
      editorCard,
      window.FOSS.components.splitDivider({ targetSplit: null, testid: "markdown-split-divider" }),
      previewCard
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack grow markdown-panel-stack"
    }, [
      topBar,
      toolbar,
      errorBanner,
      resultHost,
      splitArea
    ]));

    // Wire onFiles support
    ctx.state = ctx.state || {};
    ctx.state.loadFile = function (filePath) {
      window.FOSS.api("read_text_file", { path: filePath }).then(function (readRes) {
        if (readRes && readRes.content !== undefined) {
          editor.setValue(readRes.content);
          updateStats();
          updatePreview();
        }
      });
    };

    updateStats();
    updatePreview();
  }

  window.FOSS.router.register({
    id: "markdown",
    title: "Markdown Studio",
    navName: "Markdown",
    category: "Documents",
    icon: "markdown",
    workbench: true,
    defaults: [
      {
        key: "flavor",
        label: "Parser flavor",
        type: "select",
        options: [
          { value: "gfm", label: "GFM" },
          { value: "commonmark", label: "CommonMark" },
          { value: "strict", label: "Strict" }
        ],
        default: "gfm"
      },
      {
        key: "line_wrap",
        label: "Editor line wrap",
        type: "select",
        options: [
          { value: "soft", label: "Wrap long lines" },
          { value: "off", label: "No wrap (scroll horizontally)" }
        ],
        default: "soft"
      },
      {
        key: "export_format",
        label: "Default export format",
        type: "select",
        options: [
          { value: "pdf", label: "PDF Document (*.pdf)" },
          { value: "html", label: "HTML Document (*.html)" },
          { value: "md", label: "Markdown Document (*.md)" }
        ],
        default: "pdf"
      }
    ],
    description: "Side-by-side Markdown editor and live renderer with GitHub GFM, CommonMark, and HTML/PDF export.",
    tabs: [
      { id: "main", label: "Markdown Studio", render: renderMain }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0 && ctx.state && ctx.state.loadFile) {
        ctx.state.loadFile(paths[0]);
      }
    }
  });
})();
