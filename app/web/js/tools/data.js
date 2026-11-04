// Data Studio: multi-format code formatting, conversion, structure inspection, tables, JSONPath, and utilities.
window.FOSS = window.FOSS || {};

(function () {
  function copyTextToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
      return;
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

  function showToast(message, type) {
    if (window.FOSS && window.FOSS.toast && typeof window.FOSS.toast.show === "function") {
      window.FOSS.toast.show(message, type);
    }
  }

  // --- TAB 1: FORMAT, MINIFY & CONVERT ---------------------------------------
  function renderEditorTab(panel) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-data");

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-editor-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger",
      "data-testid": "data-error-banner",
      hidden: true
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    // Top Action Bar
    var langSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Source Language Format",
      title: "Source Language Format"
    }, [
      window.FOSS.dom.el("option", { value: "json", text: "JSON" }),
      window.FOSS.dom.el("option", { value: "yaml", text: "YAML" }),
      window.FOSS.dom.el("option", { value: "toml", text: "TOML" }),
      window.FOSS.dom.el("option", { value: "xml", text: "XML" }),
      window.FOSS.dom.el("option", { value: "csv", text: "CSV" }),
      window.FOSS.dom.el("option", { value: "ini", text: "INI" }),
      window.FOSS.dom.el("option", { value: "sql", text: "SQL" }),
      window.FOSS.dom.el("option", { value: "css", text: "CSS" }),
      window.FOSS.dom.el("option", { value: "js", text: "JavaScript" })
    ]);

    var targetSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Target Conversion Format",
      title: "Target Conversion Format"
    }, [
      window.FOSS.dom.el("option", { value: "yaml", text: "Convert to YAML" }),
      window.FOSS.dom.el("option", { value: "json", text: "Convert to JSON" }),
      window.FOSS.dom.el("option", { value: "toml", text: "Convert to TOML" }),
      window.FOSS.dom.el("option", { value: "xml", text: "Convert to XML" }),
      window.FOSS.dom.el("option", { value: "csv", text: "Convert to CSV" }),
      window.FOSS.dom.el("option", { value: "ini", text: "Convert to INI" })
    ]);

    var indentSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Indentation",
      title: "Indentation"
    }, [
      window.FOSS.dom.el("option", { value: "2", text: "2 Spaces" }),
      window.FOSS.dom.el("option", { value: "4", text: "4 Spaces" }),
      window.FOSS.dom.el("option", { value: "1", text: "Tab" })
    ]);

    var formatBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-format-btn",
      "aria-label": "Format / Prettify Code",
      title: "Format / Prettify",
      onClick: function () {
        clearError();
        var content = inputEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Formatting code...";
        window.FOSS.api("data_format_code", {
          content: content,
          language: langSelect.value,
          indent: parseInt(indentSelect.value, 10) || 2
        }).then(function (res) {
          outputEditor.setValue(res.result || "");
          statusBar.textContent = "Formatted " + langSelect.value.toUpperCase() + " successfully.";
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("check-circle", 14), window.FOSS.dom.el("span", { text: "Format" })]);

    var minifyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-minify-btn",
      "aria-label": "Minify Code",
      title: "Minify Code",
      onClick: function () {
        clearError();
        var content = inputEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Minifying code...";
        window.FOSS.api("data_minify_code", {
          content: content,
          language: langSelect.value
        }).then(function (res) {
          outputEditor.setValue(res.result || "");
          statusBar.textContent = "Minified " + langSelect.value.toUpperCase() + " successfully.";
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("minimize-2", 14), window.FOSS.dom.el("span", { text: "Minify" })]);

    var validateBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-validate-btn",
      "aria-label": "Validate Syntax",
      title: "Validate Syntax",
      onClick: function () {
        clearError();
        var content = inputEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Validating syntax...";
        window.FOSS.api("data_validate_syntax", {
          content: content,
          language: langSelect.value
        }).then(function (res) {
          if (res.valid) {
            statusBar.textContent = "Valid " + langSelect.value.toUpperCase() + " syntax!";
            showToast("Valid " + langSelect.value.toUpperCase() + " syntax", "success");
          } else {
            showError("Syntax error at line " + (res.line || "?") + ": " + res.message);
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Validate" })]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-convert-btn",
      "aria-label": "Convert Format",
      title: "Convert Format",
      onClick: function () {
        clearError();
        var content = inputEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Converting format...";
        window.FOSS.api("data_convert_format", {
          content: content,
          source_format: langSelect.value,
          target_format: targetSelect.value,
          indent: parseInt(indentSelect.value, 10) || 2
        }).then(function (res) {
          outputEditor.setValue(res.result || "");
          statusBar.textContent = "Converted " + langSelect.value.toUpperCase() + " -> " + targetSelect.value.toUpperCase();
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Convert" })]);

    var copyOutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-copy-output-btn",
      "aria-label": "Copy Output",
      title: "Copy Output",
      onClick: function () {
        var outText = outputEditor.getValue();
        if (outText) {
          copyTextToClipboard(outText);
          showToast("Copied output to clipboard", "success");
        }
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Output" })]);

    var convertYamlBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-convert-yaml-btn",
      "aria-label": "Convert to YAML",
      title: "Convert to YAML",
      onClick: function () {
        clearError();
        var content = inputEditor.getValue() || '{\n  "name": "FOSSEverything",\n  "tools": ["pdf", "image", "data"],\n  "active": true\n}';
        statusBar.textContent = "Converting to YAML...";
        window.FOSS.api("data_convert_format", {
          content: content,
          source_format: langSelect.value,
          target_format: "yaml",
          indent: parseInt(indentSelect.value, 10) || 2
        }).then(function (res) {
          outputEditor.setValue(res.result || "");
          statusBar.textContent = "Converted " + langSelect.value.toUpperCase() + " -> YAML";
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "To YAML" })]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-save-btn",
      "aria-label": "Save Output File",
      title: "Save Output File",
      onClick: function () {
        clearError();
        var outText = outputEditor.getValue();
        if (!outText) {
          outText = inputEditor.getValue();
        }
        var ext = targetSelect.value || langSelect.value || "yaml";
        window.FOSS.api("select_save_path", {
          title: "Save Data File",
          default_name: "data." + ext,
          filters: [{ name: ext.toUpperCase() + " File", extensions: [ext] }, { name: "All Files", extensions: ["*"] }]
        }).then(function (res) {
          var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outPath) return;
          var chosenExt = outPath.split(".").pop().toLowerCase();
          var payloadToSave = outText;
          if (!payloadToSave) {
            payloadToSave = (chosenExt === "yaml" || chosenExt === "yml") ? "name: FOSSEverything\ntools:\n  - pdf\n  - image\n  - data\nactive: true\n" : '{\n  "name": "FOSSEverything"\n}';
          }
          window.FOSS.api("data_save_file", {
            content: payloadToSave,
            output_path: outPath
          }).then(function () {
            statusBar.textContent = "Saved to " + outPath;
            showToast("Saved output to " + outPath, "success");
          }).catch(function (err) {
            showError((err && err.message) || String(err));
          });
        }).catch(function (err) {
          showError((err && err.message) || String(err));
        });
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Save File" })]);

    var topBar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [
      langSelect,
      indentSelect,
      formatBtn,
      minifyBtn,
      validateBtn,
      targetSelect,
      convertBtn,
      convertYamlBtn,
      saveBtn,
      copyOutBtn
    ]);

    // Side-by-side Editors
    var inputEditor = window.FOSS.components.codeEditor({
      testid: "data-editor-input",
      title: "Input Source Code",
      placeholder: '{\n  "name": "FOSSEverything",\n  "tools": ["pdf", "image", "data"],\n  "active": true\n}',
      ariaLabel: "Input source data code",
      fillHeight: true
    });

    var outputEditor = window.FOSS.components.codeEditor({
      testid: "data-editor-output",
      title: "Formatted / Converted Result",
      placeholder: "Result will appear here...",
      ariaLabel: "Output result code",
      fillHeight: true
    });

    var editorGrid = window.FOSS.dom.el("div", {
      className: "row gap-3 items-stretch code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "24rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0" } }, [inputEditor.el]),
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0" } }, [outputEditor.el])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(topBar);
    panel.appendChild(editorGrid);
  }

  // --- TAB 2: STRUCTURE & HDF5 INSPECTOR ---------------------------------------
  function renderStructureTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-structure-status",
      text: "Ready"
    });

    var sidebarCol = window.FOSS.dom.el("div", { className: "data-sidebar-pane" });

    // File / Text Picker Card
    var inputCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var inputTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Structure Source" });

    var filePicker = window.FOSS.components.filePicker({
      testid: "data-structure-file-picker",
      title: "Open Data or HDF5 File",
      fileTypes: ["json", "yaml", "yml", "toml", "csv", "xml", "h5", "hdf5"],
      onSelect: function (val) {
        if (!val) return;
        statusBar.textContent = "Inspecting structure...";
        window.FOSS.api("data_inspect_structure", { file_path: val }).then(function (res) {
          currentStructure = res;
          renderTree(res.root, filterQuery);
          statusBar.textContent = "[OK] Inspected " + res.format + " (" + (res.stats ? res.stats.total_nodes : 0) + " nodes)";
        }).catch(function (err) {
          statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
        });
      }
    });

    var toggleTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-toggle-text-btn",
      "aria-label": "Toggle raw text input",
      title: "Paste Raw Text",
      onClick: function () {
        var isHidden = textEditorDrawer.classList.toggle("hidden");
        toggleTextBtn.textContent = isHidden ? "Paste Text..." : "Hide Text Box";
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Paste Text..." })]);

    var textEditorDrawer = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 hidden code-editor-fill",
      style: { width: "100%" }
    });

    var codeEditor = window.FOSS.components.codeEditor({
      testid: "data-structure-text-input",
      title: "Raw Data Payload",
      placeholder: '{\n  "project": "FOSSEverything",\n  "tools": [{"name": "pdf"}, {"name": "ocr"}]\n}',
      ariaLabel: "Raw data input for structure inspection",
      fillHeight: true
    });

    var inspectTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-structure-inspect-btn",
      "aria-label": "Inspect pasted text structure",
      title: "Inspect pasted text structure",
      onClick: function () {
        var content = codeEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Analyzing structure...";
        window.FOSS.api("data_inspect_structure", { content: content }).then(function (res) {
          currentStructure = res;
          renderTree(res.root, filterQuery);
          statusBar.textContent = "[OK] Inspected " + res.format + " payload (" + (res.stats ? res.stats.total_nodes : 0) + " nodes)";
        }).catch(function (err) {
          statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Inspect Payload" })]);

    textEditorDrawer.appendChild(codeEditor.el);
    textEditorDrawer.appendChild(inspectTextBtn);

    inputCard.appendChild(inputTitle);
    inputCard.appendChild(filePicker.el);
    inputCard.appendChild(toggleTextBtn);
    inputCard.appendChild(textEditorDrawer);

    // Node Details Card
    var detailsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-2" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Selected Node Details" }),
      window.FOSS.dom.el("div", {
        className: "text-xs font-mono p-2 rounded",
        style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", minHeight: "80px", wordBreak: "break-all" },
        id: "data-node-details-content",
        text: "Click any node in the tree to view properties."
      })
    ]);

    sidebarCol.appendChild(inputCard);
    sidebarCol.appendChild(detailsCard);

    // Right Column: Search & Tree Root
    var stageCol = window.FOSS.dom.el("div", { className: "data-stage-pane" });

    var treeCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var treeHeader = window.FOSS.dom.el("div", {
      className: "row items-center justify-between flex-wrap gap-2",
      style: { width: "100%" }
    });

    var filterQuery = "";
    var currentStructure = null;

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm flex-1",
      "data-testid": "data-structure-filter-input",
      placeholder: "Filter keys or values...",
      "aria-label": "Filter structure tree by key or value"
    });

    filterInput.addEventListener("input", function () {
      filterQuery = filterInput.value.trim().toLowerCase();
      if (currentStructure && currentStructure.root) {
        renderTree(currentStructure.root, filterQuery);
      }
    });

    var expandAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-expand-all",
      "aria-label": "Expand all sections",
      title: "Expand all sections",
      onClick: function () {
        var children = treeRoot.querySelectorAll(".data-tree-children");
        children.forEach(function (c) { c.classList.remove("collapsed"); });
      }
    }, [window.FOSS.icons.el("plus-square", 14), window.FOSS.dom.el("span", { text: "Expand" })]);

    var collapseAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-collapse-all",
      "aria-label": "Collapse all sections",
      title: "Collapse all sections",
      onClick: function () {
        var children = treeRoot.querySelectorAll(".data-tree-children");
        children.forEach(function (c) { c.classList.add("collapsed"); });
      }
    }, [window.FOSS.icons.el("minus-square", 14), window.FOSS.dom.el("span", { text: "Collapse" })]);

    treeHeader.appendChild(filterInput);
    treeHeader.appendChild(expandAllBtn);
    treeHeader.appendChild(collapseAllBtn);

    var treeRoot = window.FOSS.dom.el("div", {
      className: "data-tree-root scroll-y p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", minHeight: "300px", maxHeight: "600px", width: "100%" },
      "data-testid": "data-structure-tree"
    });

    treeCard.appendChild(treeHeader);
    treeCard.appendChild(treeRoot);
    stageCol.appendChild(treeCard);

    var workbench = window.FOSS.dom.el("div", {
      className: "data-workbench",
      style: { width: "100%", height: "100%" }
    }, [
      sidebarCol,
      window.FOSS.dom.el("div", { className: "split-divider", "data-decorative": "true" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(workbench);

    function renderTree(rootNode, filter) {
      treeRoot.innerHTML = "";
      if (!rootNode) {
        treeRoot.innerHTML = '<div class="text-sm text-muted p-4 text-center">No structure to display. Open a file or paste data.</div>';
        return;
      }
      var el = createTreeNode(rootNode, 0, filter);
      if (el) treeRoot.appendChild(el);
    }

    function createTreeNode(node, depth, filter) {
      if (!node) return null;
      var hasChildren = node.children && node.children.length > 0;
      var childElements = [];

      if (hasChildren) {
        for (var i = 0; i < node.children.length; i++) {
          var cEl = createTreeNode(node.children[i], depth + 1, filter);
          if (cEl) childElements.push(cEl);
        }
      }

      var itemContainer = window.FOSS.dom.el("div", { className: "data-tree-item" });
      var toggleIcon = window.FOSS.dom.el("span", {
        className: "data-tree-toggle",
        "data-decorative": "true",
        text: hasChildren ? (depth < 2 ? "\u25bc" : "\u25b6") : " "
      });

      var row = window.FOSS.dom.el("div", {
        className: "data-tree-row",
        onClick: function (e) {
          e.stopPropagation();
          showNodeDetails(node);
          if (hasChildren && childrenBox) {
            var isCollapsed = childrenBox.classList.toggle("collapsed");
            toggleIcon.textContent = isCollapsed ? "\u25b6" : "\u25bc";
          }
        }
      }, [
        toggleIcon,
        window.FOSS.dom.el("span", { className: "data-tree-badge data-tree-badge-" + (node.type || "string"), text: node.type || "val" }),
        window.FOSS.dom.el("span", { className: "data-tree-key", text: node.name || "" }),
        window.FOSS.dom.el("span", { className: "data-tree-val", text: node.preview ? (": " + node.preview) : "" })
      ]);

      itemContainer.appendChild(row);

      var childrenBox = null;
      if (hasChildren) {
        childrenBox = window.FOSS.dom.el("div", {
          className: "data-tree-children" + (depth >= 2 && !filter ? " collapsed" : "")
        });
        childElements.forEach(function (ce) { childrenBox.appendChild(ce); });
        itemContainer.appendChild(childrenBox);
      }

      return itemContainer;
    }

    function showNodeDetails(node) {
      var detailsEl = document.getElementById("data-node-details-content");
      if (!detailsEl) return;
      var lines = [
        "Name: " + (node.name || ""),
        "Type: " + (node.type || ""),
        "Path: " + (node.path || "")
      ];
      if (node.shape) lines.push("Shape: " + JSON.stringify(node.shape));
      if (node.dtype) lines.push("Dtype: " + node.dtype);
      if (node.size_bytes !== undefined) lines.push("Size: " + node.size_bytes + " bytes");
      detailsEl.textContent = lines.join("\n");
    }

    renderTree(null, "");
  }

  // --- TAB 3: TABLES (CSV / TSV / MARKDOWN) ----------------------------------
  function renderTablesTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-tables-status",
      text: "Ready"
    });

    var tableEditor = window.FOSS.components.codeEditor({
      testid: "data-tables-input",
      title: "Table Data (CSV, TSV, or Markdown Table)",
      placeholder: "| Column 1 | Column 2 | Column 3 |\n| --- | --- | --- |\n| Value A | Value B | Value C |",
      ariaLabel: "Input table text content",
      fillHeight: true
    });

    var cleanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-tables-clean",
      "aria-label": "Clean and format table",
      title: "Clean Table",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_clean_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result || "");
          statusBar.textContent = "[OK] Cleaned table whitespace and aligned columns";
          renderPreview();
        });
      }
    }, [window.FOSS.icons.el("check-circle", 14), window.FOSS.dom.el("span", { text: "Clean Table" })]);

    var transposeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-transpose",
      "aria-label": "Transpose Table Rows and Columns",
      title: "Transpose Table",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_transpose_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result || "");
          statusBar.textContent = "[OK] Transposed table rows and columns";
          renderPreview();
        });
      }
    }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Transpose" })]);

    var dedupBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-dedup",
      "aria-label": "Deduplicate Rows",
      title: "Deduplicate Rows",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_dedup_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result || "");
          statusBar.textContent = "[OK] Removed " + (res.duplicates_removed || 0) + " duplicate rows";
          renderPreview();
        });
      }
    }, [window.FOSS.icons.el("filter", 14), window.FOSS.dom.el("span", { text: "Deduplicate" })]);

    var csvToMdBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-csv-to-md",
      "aria-label": "CSV to Markdown",
      title: "CSV to Markdown",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_csv_to_table", { content: content, delimiter: "," }).then(function (res) {
          tableEditor.setValue(res.result || "");
          statusBar.textContent = "[OK] Converted CSV to Markdown table";
          renderPreview();
        });
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "CSV -> Markdown" })]);

    var mdToCsvBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-md-to-csv",
      "aria-label": "Markdown to CSV",
      title: "Markdown to CSV",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_table_to_csv", { content: content, delimiter: "," }).then(function (res) {
          tableEditor.setValue(res.result || "");
          statusBar.textContent = "[OK] Converted Markdown table to CSV";
        });
      }
    }, [window.FOSS.icons.el("file", 14), window.FOSS.dom.el("span", { text: "Markdown -> CSV" })]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [cleanBtn, transposeBtn, dedupBtn, csvToMdBtn, mdToCsvBtn]);

    var previewHost = window.FOSS.dom.el("div", {
      className: "p-3 rounded scroll-y",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", minHeight: "200px", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "text-muted text-sm text-center", text: "Interactive table preview appears here." })
    ]);

    function renderPreview() {
      var content = tableEditor.getValue();
      if (!content.trim()) return;
      window.FOSS.api("data_table_to_rows", { content: content }).then(function (res) {
        var rows = res.rows || [];
        if (!rows.length) return;
        var headers = Object.keys(rows[0] || {});
        if (!headers.length) return;
        previewHost.innerHTML = "";
        var tbl = window.FOSS.dom.el("table", { className: "table", style: { width: "100%" } });
        var thead = window.FOSS.dom.el("thead");
        var hRow = window.FOSS.dom.el("tr");
        headers.forEach(function (h) {
          hRow.appendChild(window.FOSS.dom.el("th", { text: String(h) }));
        });
        thead.appendChild(hRow);
        tbl.appendChild(thead);

        var tbody = window.FOSS.dom.el("tbody");
        for (var i = 0; i < rows.length; i++) {
          var tr = window.FOSS.dom.el("tr");
          var rowData = rows[i];
          headers.forEach(function (h) {
            tr.appendChild(window.FOSS.dom.el("td", { text: String(rowData[h] !== undefined ? rowData[h] : "") }));
          });
          tbody.appendChild(tr);
        }
        tbl.appendChild(tbody);
        previewHost.appendChild(tbl);
      });
    }

    var grid = window.FOSS.dom.el("div", {
      className: "row gap-3 items-stretch code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "24rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0" } }, [tableEditor.el]),
      window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "0" } }, [previewHost])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(toolbar);
    panel.appendChild(grid);
  }

  // --- TAB 4: JSONPATH & SCHEMA -----------------------------------------------
  function renderQueryTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-query-status",
      text: "Ready"
    });

    var pathInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm flex-1",
      value: "$.store.book[*].author",
      placeholder: "e.g. $.store.book[*].author or $..price",
      "aria-label": "JSONPath Query Expression"
    });

    var queryBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-query-btn",
      "aria-label": "Query JSONPath",
      title: "Run JSONPath",
      onClick: function () {
        var content = jsonEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Querying JSONPath...";
        window.FOSS.api("data_query_jsonpath", {
          content: content,
          path: pathInput.value
        }).then(function (res) {
          resultEditor.setValue(JSON.stringify(res.matches || [], null, 2));
          statusBar.textContent = "Matched " + (res.matches ? res.matches.length : 0) + " elements.";
        }).catch(function (err) {
          statusBar.textContent = "Query error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Query JSONPath" })]);

    var inferSchemaBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-infer-schema-btn",
      "aria-label": "Infer JSON Schema",
      title: "Infer Schema",
      onClick: function () {
        var content = jsonEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Inferring JSON Schema...";
        window.FOSS.api("data_infer_schema", { content: content }).then(function (res) {
          resultEditor.setValue(JSON.stringify(res.schema || {}, null, 2));
          statusBar.textContent = "Inferred JSON Schema successfully.";
        }).catch(function (err) {
          statusBar.textContent = "Schema error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Infer Schema" })]);

    var topBar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [
      window.FOSS.dom.el("span", { className: "text-xs font-bold", text: "JSONPath:" }),
      pathInput,
      queryBtn,
      inferSchemaBtn
    ]);

    var jsonEditor = window.FOSS.components.codeEditor({
      testid: "data-query-json-input",
      title: "Input JSON Document",
      placeholder: '{\n  "store": {\n    "book": [\n      {"category": "reference", "author": "Nigel Rees", "title": "Sayings of the Century", "price": 8.95},\n      {"category": "fiction", "author": "Evelyn Waugh", "title": "Sword of Honour", "price": 12.99}\n    ]\n  }\n}',
      ariaLabel: "Input JSON document",
      fillHeight: true
    });

    var resultEditor = window.FOSS.components.codeEditor({
      testid: "data-query-result",
      title: "Query / Schema Result",
      placeholder: "Results will appear here...",
      ariaLabel: "Query results",
      fillHeight: true
    });

    var grid = window.FOSS.dom.el("div", {
      className: "row gap-3 items-stretch code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "24rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0" } }, [jsonEditor.el]),
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0" } }, [resultEditor.el])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(topBar);
    panel.appendChild(grid);
  }

  // --- TAB 5: UTILITIES (CRON, CALENDAR, GENERATOR) ---------------------------
  function renderUtilitiesTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-utilities-status",
      text: "Ready"
    });

    var sidebarCol = window.FOSS.dom.el("div", { className: "data-sidebar-pane" });

    // Section 1: Cryptographic Random Generator
    var randCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var randTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Random / Password Generator" });

    var randKind = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Generator Type"
    }, [
      window.FOSS.dom.el("option", { value: "password", text: "Cryptographic Password" }),
      window.FOSS.dom.el("option", { value: "uuid", text: "UUID v4" }),
      window.FOSS.dom.el("option", { value: "token", text: "Hex Auth Token" }),
      window.FOSS.dom.el("option", { value: "number", text: "Random Integer" }),
      window.FOSS.dom.el("option", { value: "name", text: "Full Name" })
    ]);

    var randLen = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      value: "16",
      min: "4",
      max: "128",
      style: { width: "80px" },
      "aria-label": "Password Length"
    });

    var randGenBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-utilities-random-generate",
      "aria-label": "Generate random value",
      title: "Generate Value",
      onClick: function () {
        statusBar.textContent = "Generating random value...";
        window.FOSS.api("data_random_value", {
          category: randKind.value,
          length: parseInt(randLen.value, 10) || 16,
          count: 1
        }).then(function (res) {
          var out = res.value !== undefined ? res.value : (res.result !== undefined ? res.result : "-");
          randOutput.textContent = String(out);
          statusBar.textContent = "Generated " + randKind.value + " successfully.";
        });
      }
    }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Generate" })]);

    var randOutput = window.FOSS.dom.el("div", {
      className: "p-2 rounded font-mono text-sm",
      "data-testid": "data-utilities-random-output",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", wordBreak: "break-all" },
      text: "-"
    });

    var copyRandBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Copy generated value",
      title: "Copy",
      onClick: function () {
        var val = randOutput.textContent;
        if (val && val !== "-") {
          copyTextToClipboard(val);
          showToast("Copied random value to clipboard", "success");
        }
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy" })]);

    randCard.appendChild(randTitle);
    randCard.appendChild(window.FOSS.components.field("Type", randKind));
    randCard.appendChild(window.FOSS.components.field("Length", randLen));
    randCard.appendChild(randGenBtn);
    randCard.appendChild(randOutput);
    randCard.appendChild(copyRandBtn);

    sidebarCol.appendChild(randCard);

    // Right Column: Cron & Calendar
    var stageCol = window.FOSS.dom.el("div", { className: "data-stage-pane" });

    // Cron Explainer Card
    var cronCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var cronTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Cron Expression Explainer" });

    var cronInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm font-mono",
      value: "*/15 * * * *",
      placeholder: "e.g. 0 0 * * * or */5 * * * *",
      "aria-label": "Cron Expression"
    });

    var cronBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-cron-explain-btn",
      "aria-label": "Explain Cron Expression",
      title: "Explain Cron",
      onClick: function () {
        var expr = cronInput.value.trim();
        if (!expr) return;
        statusBar.textContent = "Calculating cron execution schedule...";
        window.FOSS.api("data_cron_describe", { expression: expr, count: 5 }).then(function (res) {
          cronDesc.textContent = res.description || "Valid cron expression";
          cronRunsList.innerHTML = "";
          (res.upcoming_runs || []).forEach(function (dtStr) {
            cronRunsList.appendChild(window.FOSS.dom.el("div", {
              className: "font-mono text-xs p-1 rounded",
              style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)" },
              text: dtStr
            }));
          });
          statusBar.textContent = "Upcoming execution schedule computed.";
        }).catch(function (err) {
          statusBar.textContent = "Cron error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [window.FOSS.icons.el("clock", 14), window.FOSS.dom.el("span", { text: "Calculate Schedule" })]);

    var cronDesc = window.FOSS.dom.el("div", {
      className: "text-sm font-bold text-success p-2 rounded",
      style: { background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)" },
      text: "Every 15 minutes"
    });

    var cronRunsList = window.FOSS.dom.el("div", {
      className: "flex-col gap-1",
      style: { width: "100%" }
    });

    cronCard.appendChild(cronTitle);
    cronCard.appendChild(window.FOSS.components.field("Expression (minute hour dom month dow)", cronInput));
    cronCard.appendChild(cronBtn);
    cronCard.appendChild(cronDesc);
    cronCard.appendChild(cronRunsList);

    // Calendar .ICS Builder Card
    var icsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var icsTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "iCalendar (.ICS) Event Builder" });

    var calTitleInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      value: "Team Architecture Review",
      "aria-label": "Event Title"
    });
    var calStartInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm font-mono",
      value: "20261102T160000Z",
      placeholder: "YYYYMMDDTHHMMSSZ",
      "aria-label": "Start Time UTC"
    });

    var icsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-ics-build-btn",
      "aria-label": "Generate .ICS File",
      title: "Generate .ICS",
      onClick: function () {
        window.FOSS.api("data_ics_generate", {
          title: calTitleInput.value,
          start_time: calStartInput.value
        }).then(function (res) {
          icsOutput.setValue(res.ics || "");
          statusBar.textContent = "Generated .ICS event data.";
        });
      }
    }, [window.FOSS.icons.el("calendar", 14), window.FOSS.dom.el("span", { text: "Generate .ICS" })]);

    var icsOutput = window.FOSS.components.codeEditor({
      testid: "data-ics-output",
      title: "Generated .ICS Event",
      placeholder: "ICS payload will appear here...",
      ariaLabel: "Generated ICS payload",
      fillHeight: true
    });

    icsCard.appendChild(icsTitle);
    icsCard.appendChild(window.FOSS.components.field("Title", calTitleInput));
    icsCard.appendChild(window.FOSS.components.field("Start Time (ISO/UTC)", calStartInput));
    icsCard.appendChild(icsBtn);
    icsCard.appendChild(icsOutput.el);

    stageCol.appendChild(cronCard);
    stageCol.appendChild(icsCard);

    var workbench = window.FOSS.dom.el("div", {
      className: "data-workbench",
      style: { width: "100%", height: "100%" }
    }, [
      sidebarCol,
      window.FOSS.dom.el("div", { className: "split-divider", "data-decorative": "true" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(workbench);
  }

  // Router Registration
  window.FOSS.router.register({
    id: "data",
    title: "Data Studio",
    navName: "Data",
    category: "Data",
    icon: "code",
    workbench: true,
    tabs: [
      { id: "editor", label: "Format & Convert", aliases: ["main", "format"], render: renderEditorTab },
      { id: "structure", label: "Tree & HDF5", render: renderStructureTab },
      { id: "tables", label: "Tables", render: renderTablesTab },
      { id: "query", label: "JSONPath & Schema", render: renderQueryTab },
      { id: "utilities", label: "Utilities", aliases: ["units", "calendar"], render: renderUtilitiesTab }
    ]
  });
})();
