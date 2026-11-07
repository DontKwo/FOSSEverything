// Data Studio: multi-format code formatting, conversion, structure inspection, tables, JSONPath, and utilities.
window.FOSS = window.FOSS || {};

(function () {
  var TARGET_FORMATS = ["yaml", "json", "toml", "xml", "csv", "ini"];
  var CONVERT_FORMATS = ["json", "yaml", "toml", "xml", "csv", "ini"];
  var HDF5_EXTENSIONS = ["h5", "hdf5", "he5"];
  var SAVE_TYPE_NAMES = {
    json: "JSON Document (*.json)",
    yaml: "YAML Document (*.yaml)",
    toml: "TOML Document (*.toml)",
    csv: "CSV Table (*.csv)",
    sql: "SQL Script (*.sql)"
  };

  function toolDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("data", key, fallback);
  }

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

  function normalizeExt(path) {
    var dot = path.lastIndexOf(".");
    var ext = dot >= 0 ? path.slice(dot + 1).toLowerCase() : "";
    return ext === "yml" ? "yaml" : ext;
  }

  function buildSaveTypes(firstExt) {
    var order = Object.keys(SAVE_TYPE_NAMES);
    var first = order.indexOf(firstExt) >= 0 ? firstExt : "json";
    var sorted = [first].concat(order.filter(function (ext) { return ext !== first; }));
    return sorted.map(function (ext) {
      return { name: SAVE_TYPE_NAMES[ext], extensions: [ext] };
    });
  }

  function errorText(err) {
    return err && err.message ? err.message : String(err);
  }

  function renderEditorTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "data-editor-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "data-error-banner"
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

    var outputFormat = "";

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
    }, TARGET_FORMATS.map(function (fmt) {
      return window.FOSS.dom.el("option", { value: fmt, text: "Convert to " + fmt.toUpperCase() });
    }));
    targetSelect.value = String(toolDefault("target_format", "yaml"));

    var indentSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Indentation",
      title: "Indentation"
    }, [
      window.FOSS.dom.el("option", { value: "2", text: "2 Spaces" }),
      window.FOSS.dom.el("option", { value: "4", text: "4 Spaces" }),
      window.FOSS.dom.el("option", { value: "8", text: "8 Spaces" })
    ]);
    indentSelect.value = String(toolDefault("indent", "2"));

    function indentValue() {
      return parseInt(indentSelect.value, 10) || 2;
    }

    function runConvert(targetFormat) {
      clearError();
      var content = inputEditor.getValue();
      if (!content.trim()) return;
      statusBar.textContent = "Converting format...";
      window.FOSS.api("data_convert_format", {
        content: content,
        source_format: langSelect.value,
        target_format: targetFormat,
        indent: indentValue()
      }).then(function (res) {
        outputEditor.setValue(res.result || "");
        outputFormat = targetFormat;
        statusBar.textContent = "Converted " + langSelect.value.toUpperCase() + " -> " + targetFormat.toUpperCase();
      }).catch(function (err) {
        showError(errorText(err));
      });
    }

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
          indent: indentValue()
        }).then(function (res) {
          outputEditor.setValue(res.result || "");
          outputFormat = langSelect.value;
          statusBar.textContent = "Formatted " + langSelect.value.toUpperCase() + " successfully.";
        }).catch(function (err) {
          showError(errorText(err));
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
          outputFormat = langSelect.value;
          statusBar.textContent = "Minified " + langSelect.value.toUpperCase() + " successfully.";
        }).catch(function (err) {
          showError(errorText(err));
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
          showError(errorText(err));
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Validate" })]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-convert-btn",
      "aria-label": "Convert Format",
      title: "Convert Format",
      onClick: function () { runConvert(targetSelect.value); }
    }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Convert" })]);

    var convertYamlBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-convert-yaml-btn",
      "aria-label": "Convert to YAML",
      title: "Convert to YAML",
      onClick: function () { runConvert("yaml"); }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "To YAML" })]);

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

    function writeSaveFile(content, outPath) {
      return window.FOSS.api("data_save_file", {
        content: content,
        output_path: outPath
      }).then(function () {
        statusBar.textContent = "Saved to " + outPath;
        showToast("Saved output to " + outPath, "success");
      });
    }

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-save-btn",
      "aria-label": "Save Output File",
      title: "Save Output File",
      onClick: function () {
        clearError();
        var outText = outputEditor.getValue();
        var textFormat = outputFormat || targetSelect.value;
        if (!outText) {
          outText = inputEditor.getValue();
          textFormat = langSelect.value;
        }
        if (!outText) {
          showError("Nothing to save. Enter or generate data first.");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Data File",
          default_name: "data",
          file_types: buildSaveTypes(textFormat)
        }).then(function (res) {
          var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outPath) return null;
          var chosenExt = normalizeExt(outPath);
          var needsConvert = chosenExt !== textFormat
            && CONVERT_FORMATS.indexOf(chosenExt) >= 0
            && CONVERT_FORMATS.indexOf(textFormat) >= 0;
          if (!needsConvert) return writeSaveFile(outText, outPath);
          statusBar.textContent = "Converting to " + chosenExt.toUpperCase() + " for saving...";
          return window.FOSS.api("data_convert_format", {
            content: outText,
            source_format: textFormat,
            target_format: chosenExt,
            indent: indentValue()
          }).then(function (conv) {
            return writeSaveFile(conv.result || "", outPath);
          });
        }).catch(function (err) {
          showError(errorText(err));
        });
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Save File" })]);

    var topBar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [
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

    var editorGrid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [inputEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [outputEditor])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(topBar);
    panel.appendChild(editorGrid);
  }

  function isHdf5Path(path) {
    var dot = path.lastIndexOf(".");
    return dot >= 0 && HDF5_EXTENSIONS.indexOf(path.slice(dot + 1).toLowerCase()) >= 0;
  }

  function formatBytes(count) {
    if (count < 1024) return count + " B";
    var units = ["KB", "MB", "GB", "TB"];
    var value = count / 1024;
    var idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx += 1;
    }
    return value.toFixed(value < 10 ? 2 : 1) + " " + units[idx];
  }

  function cellText(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function keyValueTable(rows) {
    var body = window.FOSS.dom.el("tbody");
    rows.forEach(function (row) {
      if (row[1] === null || row[1] === undefined || row[1] === "") return;
      body.appendChild(window.FOSS.dom.el("tr", {}, [
        window.FOSS.dom.el("th", { className: "wb-kv-key", text: row[0] }),
        window.FOSS.dom.el("td", { className: "font-mono", text: cellText(row[1]) })
      ]));
    });
    return window.FOSS.dom.el("table", { className: "table wb-table" }, [body]);
  }

  function gridTable(columns, rows, rowOffset) {
    var head = window.FOSS.dom.el("tr");
    if (rowOffset !== undefined) head.appendChild(window.FOSS.dom.el("th", { text: "#" }));
    columns.forEach(function (name) {
      head.appendChild(window.FOSS.dom.el("th", { text: String(name) }));
    });
    var body = window.FOSS.dom.el("tbody");
    rows.forEach(function (row, rowIdx) {
      var tr = window.FOSS.dom.el("tr");
      if (rowOffset !== undefined) {
        tr.appendChild(window.FOSS.dom.el("td", { className: "text-muted font-mono", text: String(rowOffset + rowIdx) }));
      }
      row.forEach(function (cell) {
        tr.appendChild(window.FOSS.dom.el("td", { className: "font-mono", text: cellText(cell) }));
      });
      body.appendChild(tr);
    });
    return window.FOSS.dom.el("table", { className: "table wb-table" }, [
      window.FOSS.dom.el("thead", {}, [head]),
      body
    ]);
  }

  function framedScroll(inner) {
    return window.FOSS.dom.el("div", { className: "wb-frame" }, [
      window.FOSS.dom.el("div", { className: "wb-scroll-host" }, [inner])
    ]);
  }

  function sectionTitle(text) {
    return window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: text });
  }

  function createHdf5Explorer(setStatus) {
    var filePath = "";
    var searchTimer = null;
    var selectedRow = null;

    var searchInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "data-hdf5-search",
      placeholder: "Filter members by path...",
      "aria-label": "Filter HDF5 members by path"
    });

    var summaryEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-field-full",
      "data-testid": "data-hdf5-summary",
      text: "No HDF5 file open."
    });

    var treeRoot = window.FOSS.dom.el("div", {
      className: "data-tree-root wb-tree",
      "data-testid": "data-hdf5-tree"
    });

    var resultsRoot = window.FOSS.dom.el("div", {
      className: "data-tree-root wb-tree",
      "data-testid": "data-hdf5-results"
    });

    var treeFrame = framedScroll(treeRoot);
    var resultsFrame = framedScroll(resultsRoot);
    resultsFrame.classList.add("hidden");

    var detailsHost = window.FOSS.dom.el("div", {
      className: "wb-box-grow flex-col gap-2",
      "data-testid": "data-hdf5-details"
    }, [window.FOSS.dom.el("div", { className: "text-sm text-muted text-center", text: "Select a group or dataset to see its details." })]);

    var grid = window.FOSS.dom.el("div", { className: "split resizable", style: "--split-left: 15rem; min-height: 0; flex: 1 1 0%;" }, [
      window.FOSS.dom.el("div", { className: "flex-col", style: "width: 100%; min-width: 0;" }, [
        window.FOSS.dom.el("div", { className: "row items-center flex-wrap gap-2 mb-2" }, [searchInput]),
        treeFrame,
        resultsFrame
      ]),
      window.FOSS.components.splitDivider({ side: "left" }),
      window.FOSS.dom.el("div", { className: "flex-col grow", style: "width: 100%; min-width: 0;" }, [detailsHost])
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3 wb-card-fill hidden",
      "data-testid": "data-hdf5-explorer"
    }, [
      summaryEl,
      grid
    ]);

    function describeNode(node) {
      if (node.broken) return " -> " + (node.link.target || "?") + " (broken)";
      var parts = [];
      if (node.kind === "dataset") parts.push(JSON.stringify(node.shape) + " " + node.dtype);
      if (node.kind === "group") parts.push("(" + node.members + ")");
      if (node.link && node.link.type !== "hard" && node.link.type !== "root") {
        parts.push("-> " + (node.link.filename ? node.link.filename + ":" : "") + (node.link.target || ""));
      }
      return parts.length ? ": " + parts.join(" ") : "";
    }

    function badgeFor(node) {
      var cls = node.broken ? "null" : (node.kind === "dataset" ? "dataset" : (node.kind === "group" ? "group" : "attribute"));
      var label = node.kind === "link" ? "link" : node.kind;
      if (node.link && node.link.type && node.link.type !== "hard" && node.link.type !== "root" && !node.broken) {
        label = node.link.type;
      }
      return window.FOSS.dom.el("span", { className: "data-tree-badge data-tree-badge-" + cls, text: label });
    }

    function selectRow(row, path) {
      if (selectedRow) selectedRow.classList.remove("selected");
      selectedRow = row;
      if (row) row.classList.add("selected");
      showDetails(path);
    }

    function appendPage(container, parentPath, page) {
      page.children.forEach(function (child) {
        container.appendChild(makeNode(child));
      });
      if (page.has_more) {
        var remaining = page.total - page.offset - page.children.length;
        var moreBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "data-hdf5-load-more",
          text: "Load more (" + remaining + " remaining)",
          onClick: function () {
            moreBtn.remove();
            loadChildren(container, parentPath, page.offset + page.children.length);
          }
        });
        container.appendChild(moreBtn);
      }
    }

    function loadChildren(container, parentPath, offset) {
      window.FOSS.api("data_hdf5_children", { file_path: filePath, path: parentPath, offset: offset, limit: 200 }).then(function (page) {
        if (page && page.ok === false) {
          setStatus("Error: " + page.error);
          return;
        }
        appendPage(container, parentPath, page);
      }).catch(function (err) {
        setStatus("Error: " + errorText(err));
      });
    }

    function makeNode(node, firstPage) {
      var item = window.FOSS.dom.el("div", { className: "data-tree-item" });
      var childrenBox = null;
      var loaded = false;
      var toggle = window.FOSS.dom.el("span", {
        className: "data-tree-toggle",
        "data-decorative": "true",
        text: node.expandable ? "\u25b6" : " "
      });
      var row = window.FOSS.dom.el("div", {
        className: "data-tree-row",
        title: node.path,
        onClick: function (e) {
          e.stopPropagation();
          selectRow(row, node.path);
          if (!node.expandable) return;
          if (!childrenBox) {
            childrenBox = window.FOSS.dom.el("div", { className: "data-tree-children" });
            item.appendChild(childrenBox);
          }
          if (!loaded) {
            loaded = true;
            loadChildren(childrenBox, node.path, 0);
            toggle.textContent = "\u25bc";
            return;
          }
          var collapsed = childrenBox.classList.toggle("collapsed");
          toggle.textContent = collapsed ? "\u25b6" : "\u25bc";
        }
      }, [
        toggle,
        badgeFor(node),
        window.FOSS.dom.el("span", { className: "data-tree-key", text: node.name }),
        window.FOSS.dom.el("span", { className: "data-tree-val", text: describeNode(node) })
      ]);
      item.appendChild(row);
      if (firstPage) {
        childrenBox = window.FOSS.dom.el("div", { className: "data-tree-children" });
        item.appendChild(childrenBox);
        appendPage(childrenBox, node.path, firstPage);
        loaded = true;
        toggle.textContent = "\u25bc";
      }
      return item;
    }

    function renderSearch(res) {
      resultsRoot.innerHTML = "";
      var matches = res.matches || [];
      if (!matches.length) {
        resultsRoot.appendChild(window.FOSS.dom.el("div", { className: "text-sm text-muted p-4 text-center", text: "No members match this filter." }));
        return;
      }
      matches.forEach(function (node) {
        var row = window.FOSS.dom.el("div", {
          className: "data-tree-row",
          title: node.path,
          onClick: function () { selectRow(row, node.path); }
        }, [
          badgeFor(node),
          window.FOSS.dom.el("span", { className: "data-tree-key", text: node.path }),
          window.FOSS.dom.el("span", { className: "data-tree-val", text: describeNode(node) })
        ]);
        resultsRoot.appendChild(row);
      });
      if (res.truncated) {
        resultsRoot.appendChild(window.FOSS.dom.el("div", { className: "text-xs text-muted p-2", text: "Result list truncated. Refine the filter." }));
      }
    }

    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        var query = searchInput.value.trim();
        if (!filePath || !query) {
          resultsFrame.classList.add("hidden");
          treeFrame.classList.remove("hidden");
          return;
        }
        window.FOSS.api("data_hdf5_search", { file_path: filePath, query: query, limit: 200 }).then(function (res) {
          if (res && res.ok === false) {
            setStatus("Error: " + res.error);
            return;
          }
          treeFrame.classList.add("hidden");
          resultsFrame.classList.remove("hidden");
          renderSearch(res);
          setStatus("[OK] " + (res.matches || []).length + " member(s) match '" + query + "'");
        }).catch(function (err) {
          setStatus("Error: " + errorText(err));
        });
      }, 250);
    });

    function renderDetails(node) {
      detailsHost.innerHTML = "";
      detailsHost.appendChild(window.FOSS.dom.el("div", {
        className: "font-mono text-sm font-bold",
        "data-testid": "data-hdf5-node-path",
        text: node.path
      }));

      var metaContainer = window.FOSS.dom.el("div", { className: "flex-col gap-2" });
      var link = node.link || {};
      var rows = [["Kind", node.kind]];
      if (link.type && link.type !== "root") {
        rows.push(["Link", link.type + (link.filename ? " (" + link.filename + ")" : "") + (link.target ? " -> " + link.target : "")]);
      }
      if (node.error) rows.push(["Error", node.error]);
      if (node.kind === "group") rows.push(["Members", node.members]);
      if (node.kind === "dataset") {
        var dtype = node.dtype || {};
        rows.push(["Shape", JSON.stringify(node.shape)]);
        rows.push(["Max shape", JSON.stringify(node.maxshape)]);
        rows.push(["Data type", dtype.label]);
        rows.push(["Byte order", dtype.byte_order]);
        rows.push(["Elements", node.elements]);
        rows.push(["Logical size", formatBytes(node.nbytes)]);
        rows.push(["Stored size", formatBytes(node.storage_bytes)]);
        if (node.nbytes > 0 && node.storage_bytes > 0) rows.push(["Storage ratio", (node.nbytes / node.storage_bytes).toFixed(2) + " : 1"]);
        rows.push(["Layout", node.layout]);
        rows.push(["Chunks", node.chunks ? JSON.stringify(node.chunks) : ""]);
        rows.push(["Compression", node.compression ? node.compression + (node.compression_opts !== null ? " (level " + cellText(node.compression_opts) + ")" : "") : ""]);
        rows.push(["Shuffle", node.shuffle ? "yes" : ""]);
        rows.push(["Fletcher32", node.fletcher32 ? "yes" : ""]);
        rows.push(["Scale-offset", node.scaleoffset !== null && node.scaleoffset !== undefined ? node.scaleoffset : ""]);
        rows.push(["Filters", (node.filters || []).map(function (f) { return f.name || ("id " + f.id); }).join(", ")]);
        rows.push(["Fill value", node.fillvalue]);
        rows.push(["External files", (node.external || []).map(function (e) { return e.file; }).join(", ")]);
        if (dtype.enum) {
          rows.push(["Enum members", Object.keys(dtype.enum).map(function (k) { return k + "=" + dtype.enum[k]; }).join(", ")]);
        }
      }
      if (node.kind === "datatype" && node.dtype) rows.push(["Data type", node.dtype.label]);
      metaContainer.appendChild(keyValueTable(rows));

      if (node.fields && node.fields.length) {
        metaContainer.appendChild(sectionTitle("Compound fields"));
        metaContainer.appendChild(gridTable(["Field", "Type", "Offset"], node.fields.map(function (f) {
          return [f.name, f.dtype, f.offset];
        })));
      }

      var attrs = node.attributes || [];
      metaContainer.appendChild(sectionTitle("Attributes (" + attrs.length + ")"));
      if (attrs.length) {
        metaContainer.appendChild(gridTable(["Name", "Type", "Shape", "Value"], attrs.map(function (a) {
          var shown = a.error ? "Error: " + a.error : cellText(a.value);
          if (a.truncated) shown += " ... (" + a.total_elements + " elements)";
          return [a.name, a.dtype || "", JSON.stringify(a.shape || []), shown];
        })));
      } else {
        metaContainer.appendChild(window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "No attributes." }));
      }

      if (node.kind === "dataset") {
        detailsHost.appendChild(buildPreview(node));
        var toggleDetailsBtn = window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm text-xs mt-2 self-start",
          "data-testid": "data-hdf5-toggle-details",
          type: "button",
          onClick: function () {
            var hidden = metaContainer.classList.contains("hidden");
            metaContainer.classList.toggle("hidden", !hidden);
            toggleDetailsBtn.textContent = hidden ? "[-] Hide Dataset Details & Attributes" : "[+] View Dataset Details & Attributes";
          }
        }, [window.FOSS.dom.el("span", { text: "[+] View Dataset Details & Attributes" })]);
        metaContainer.classList.add("hidden");
        detailsHost.appendChild(toggleDetailsBtn);
        detailsHost.appendChild(metaContainer);
      } else {
        detailsHost.appendChild(metaContainer);
      }
    }

    function showDetails(path) {
      window.FOSS.api("data_hdf5_node", { file_path: filePath, path: path }).then(function (node) {
        if (node && node.ok === false) {
          setStatus("Error: " + node.error);
          return;
        }
        renderDetails(node);
        setStatus("Selected " + path);
      }).catch(function (err) {
        setStatus("Error: " + errorText(err));
      });
    }

    function numberInput(testid, label, value) {
      return window.FOSS.dom.el("input", {
        type: "number",
        className: "input input-sm wb-num-sm",
        "data-testid": testid,
        "aria-label": label,
        title: label,
        min: "0",
        value: String(value)
      });
    }

    function buildPreview(node) {
      var ndim = node.ndim || 0;
      var hasFields = !!(node.fields && node.fields.length);
      var showCols = ndim >= 2 || hasFields;
      var rowStart = numberInput("data-hdf5-row-start", "First row", 0);
      var rowCount = numberInput("data-hdf5-row-count", "Row count", 20);
      var colStart = numberInput("data-hdf5-col-start", "First column", 0);
      var colCount = numberInput("data-hdf5-col-count", "Column count", 12);
      var leadingInputs = [];
      for (var axis = 0; axis < ndim - 2; axis++) {
        leadingInputs.push(numberInput("data-hdf5-index-" + axis, "Index for dimension " + axis, 0));
      }
      var tableHost = window.FOSS.dom.el("div", { className: "wb-preview-scroll", "data-testid": "data-hdf5-preview-table" });
      var statsEl = window.FOSS.dom.el("div", { className: "text-xs font-mono wb-field-full", "data-testid": "data-hdf5-stats" });
      var infoEl = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "data-hdf5-preview-info" });
      var last = null;

      function renderStats(stats) {
        if (!stats) return;
        var text = "min " + cellText(stats.min) + " | max " + cellText(stats.max) + " | mean " + cellText(stats.mean) + " | std " + cellText(stats.std);
        text += " | " + stats.count + " values" + (stats.nan_count ? ", " + stats.nan_count + " NaN or inf" : "");
        text += " (" + (stats.scope === "dataset" ? "whole dataset" : "shown window") + ")";
        statsEl.textContent = text;
      }

      function load(includeStats) {
        var body = {
          file_path: filePath,
          path: node.path,
          row_start: parseInt(rowStart.value, 10) || 0,
          row_count: parseInt(rowCount.value, 10) || 20,
          col_start: parseInt(colStart.value, 10) || 0,
          col_count: parseInt(colCount.value, 10) || 12,
          index: leadingInputs.map(function (inp) { return parseInt(inp.value, 10) || 0; }),
          include_stats: includeStats
        };
        window.FOSS.api("data_hdf5_preview", body).then(function (res) {
          if (res && res.ok === false) {
            infoEl.textContent = "Error: " + res.error;
            return;
          }
          last = res;
          rowStart.value = String(res.row_start);
          colStart.value = String(res.col_start);
          rowCount.value = String(Math.max(res.row_count, 1));
          colCount.value = String(Math.max(res.col_count, 1));
          (res.leading_index || []).forEach(function (val, idx) { leadingInputs[idx].value = String(val); });
          tableHost.innerHTML = "";
          if (res.empty) {
            infoEl.textContent = "Dataset is empty.";
            return;
          }
          tableHost.appendChild(gridTable(res.columns, res.rows, ndim >= 1 ? res.row_start : undefined));
          infoEl.textContent = "Rows " + res.row_start + " to " + (res.row_start + res.row_count - 1) + " of " + res.total_rows
            + (showCols ? ", columns " + res.col_start + " to " + (res.col_start + res.col_count - 1) + " of " + res.total_cols : "");
          if (includeStats) {
            statsEl.textContent = "";
            renderStats(res.stats);
          }
        }).catch(function (err) {
          infoEl.textContent = "Error: " + errorText(err);
        });
      }

      function page(axisName, direction) {
        if (!last) return;
        if (axisName === "rows") {
          rowStart.value = String(Math.max(0, last.row_start + direction * Math.max(last.row_count, 1)));
        } else {
          colStart.value = String(Math.max(0, last.col_start + direction * Math.max(last.col_count, 1)));
        }
        load(false);
      }

      function pageButton(testid, text, axisName, direction) {
        return window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": testid,
          "aria-label": text,
          title: text,
          onClick: function () { page(axisName, direction); }
        }, [window.FOSS.dom.el("span", { text: text })]);
      }

      var exportBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary btn-sm",
        "data-testid": "data-hdf5-export",
        "aria-label": "Export shown slice",
        title: "Export the shown slice to CSV or JSON",
        onClick: function () {
          if (!last || last.empty) return;
          var spec = last.slice_spec;
          window.FOSS.api("select_save_path", {
            title: "Export HDF5 Slice",
            default_name: node.path.split("/").pop() || "slice",
            file_types: [
              { name: "CSV Table (*.csv)", extensions: ["csv"] },
              { name: "JSON Document (*.json)", extensions: ["json"] }
            ]
          }).then(function (res) {
            var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
            if (!outPath) return null;
            var fmt = outPath.toLowerCase().endsWith(".json") ? "json" : "csv";
            return window.FOSS.api("data_hdf5_export_slice", {
              file_path: filePath,
              dataset_path: node.path,
              slice_spec: spec,
              output_path: outPath,
              format: fmt
            }).then(function (out) {
              if (out && out.ok === false) {
                setStatus("Error: " + out.error);
                return;
              }
              setStatus("Saved slice to " + outPath);
              showToast("Saved slice to " + outPath, "success");
            });
          }).catch(function (err) {
            setStatus("Error: " + errorText(err));
          });
        }
      }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Export Slice" })]);

      var loadBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "data-hdf5-preview-load",
        "aria-label": "Load preview window",
        title: "Load preview window",
        onClick: function () { load(true); }
      }, [window.FOSS.icons.el("refresh", 14), window.FOSS.dom.el("span", { text: "Load" })]);

      var controls = window.FOSS.dom.el("div", { className: "row items-center flex-wrap gap-2" });
      controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs", text: "Row" }));
      controls.appendChild(rowStart);
      controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs", text: "Rows" }));
      controls.appendChild(rowCount);
      if (showCols) {
        controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs", text: "Col" }));
        controls.appendChild(colStart);
        controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs", text: "Cols" }));
        controls.appendChild(colCount);
      }
      leadingInputs.forEach(function (inp, idx) {
        controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs", text: "Dim " + idx }));
        controls.appendChild(inp);
      });
      controls.appendChild(loadBtn);
      controls.appendChild(pageButton("data-hdf5-rows-prev", "Prev Rows", "rows", -1));
      controls.appendChild(pageButton("data-hdf5-rows-next", "Next Rows", "rows", 1));
      if (showCols) {
        controls.appendChild(pageButton("data-hdf5-cols-prev", "Prev Cols", "cols", -1));
        controls.appendChild(pageButton("data-hdf5-cols-next", "Next Cols", "cols", 1));
      }
      var plotterCanvas = window.FOSS.dom.el("canvas", {
        style: "width: 100%; height: 160px; background: var(--bg-sunken); border-radius: var(--radius-sm); border: 1px solid var(--border);",
        "data-testid": "data-hdf5-plotter"
      });

      var plotModeSelect = window.FOSS.dom.el("select", { className: "select select-sm text-xs", "aria-label": "Plot Mode" }, [
        window.FOSS.dom.el("option", { value: "none", text: "Hide Plotter" }),
        window.FOSS.dom.el("option", { value: "col_vs_col", text: "Plot Column 1 vs Column 2" }),
        window.FOSS.dom.el("option", { value: "row_vs_row", text: "Plot Row 1 vs Row 2" }),
        window.FOSS.dom.el("option", { value: "series", text: "Plot All Columns as Series" })
      ]);

      var plotterWrap = window.FOSS.dom.el("div", { className: "flex-col gap-1 hidden mt-2" }, [
        plotterCanvas
      ]);

      plotModeSelect.addEventListener("change", function () {
        var isHidden = plotModeSelect.value === "none";
        plotterWrap.classList.toggle("hidden", isHidden);
        if (!isHidden && last) {
          drawPlot(last, plotModeSelect.value);
        }
      });

      function drawPlot(res, mode) {
        if (!res || !res.rows || !res.rows.length) return;
        var ctx = plotterCanvas.getContext("2d");
        var w = plotterCanvas.width = plotterCanvas.clientWidth || 400;
        var h = plotterCanvas.height = plotterCanvas.clientHeight || 160;
        ctx.clearRect(0, 0, w, h);

        var pad = 24;
        ctx.strokeStyle = "#475569";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad, pad);
        ctx.lineTo(pad, h - pad);
        ctx.lineTo(w - pad, h - pad);
        ctx.stroke();

        if (mode === "col_vs_col" && res.rows.length > 0 && res.rows[0].length >= 2) {
          var pts = [];
          var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          res.rows.forEach(function (r) {
            var x = parseFloat(r[0]);
            var y = parseFloat(r[1]);
            if (!isNaN(x) && !isNaN(y)) {
              pts.push({ x: x, y: y });
              if (x < minX) minX = x;
              if (x > maxX) maxX = x;
              if (y < minY) minY = y;
              if (y > maxY) maxY = y;
            }
          });
          if (pts.length > 1 && maxX > minX && maxY > minY) {
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 2;
            ctx.beginPath();
            pts.forEach(function (p, idx) {
              var px = pad + ((p.x - minX) / (maxX - minX)) * (w - 2 * pad);
              var py = (h - pad) - ((p.y - minY) / (maxY - minY)) * (h - 2 * pad);
              if (idx === 0) ctx.moveTo(px, py);
              else ctx.lineTo(px, py);
            });
            ctx.stroke();
          }
        } else {
          var rowsToPlot = res.rows.slice(0, 5);
          var colors = ["#38bdf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa"];
          rowsToPlot.forEach(function (r, rIdx) {
            var pts = [];
            var minY = Infinity, maxY = -Infinity;
            r.forEach(function (v) {
              var y = parseFloat(v);
              if (!isNaN(y)) {
                pts.push(y);
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
              }
            });
            if (pts.length > 1) {
              var span = (maxY > minY) ? (maxY - minY) : 1;
              ctx.strokeStyle = colors[rIdx % colors.length];
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              pts.forEach(function (yVal, idx) {
                var px = pad + (idx / (pts.length - 1)) * (w - 2 * pad);
                var py = (h - pad) - ((yVal - minY) / span) * (h - 2 * pad);
                if (idx === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
              });
              ctx.stroke();
            }
          });
        }
      }

      controls.appendChild(exportBtn);
      controls.appendChild(window.FOSS.dom.el("span", { className: "text-xs ml-2 text-muted", text: "Plot:" }));
      controls.appendChild(plotModeSelect);

      var wrap = window.FOSS.dom.el("div", { className: "flex-col gap-2 wb-field-full", "data-testid": "data-hdf5-preview" }, [
        sectionTitle("Data preview"),
        controls,
        infoEl,
        statsEl,
        plotterWrap,
        tableHost
      ]);
      load(true);
      return wrap;
    }

    function open(path) {
      filePath = path;
      selectedRow = null;
      searchInput.value = "";
      resultsFrame.classList.add("hidden");
      treeFrame.classList.remove("hidden");
      treeRoot.innerHTML = "";
      detailsHost.innerHTML = "";
      summaryEl.textContent = "Opening HDF5 file...";
      return window.FOSS.api("data_hdf5_open", { file_path: path }).then(function (res) {
        if (res && res.ok === false) {
          summaryEl.textContent = "Error: " + res.error;
          setStatus("Error: " + res.error);
          return;
        }
        var rootNode = {
          name: "/",
          path: "/",
          kind: "group",
          members: res.root.total,
          expandable: res.root.total > 0,
          link: { type: "root" },
          broken: false
        };
        treeRoot.appendChild(makeNode(rootNode, res.root));
        summaryEl.textContent = formatBytes(res.file_size) + " | " + res.root.total + " root member(s) | " + res.attributes.length + " file attribute(s)";
        setStatus("[OK] Opened HDF5 file with h5py " + res.h5py_version);
        showDetails("/");
      }).catch(function (err) {
        summaryEl.textContent = "Error: " + errorText(err);
        setStatus("Error: " + errorText(err));
      });
    }

    return { el: card, open: open };
  }

  function renderStructureTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "data-structure-status",
      text: "Ready"
    });

    var sidebarCol = window.FOSS.dom.el("div", { className: "data-sidebar-pane" });
    var filterQuery = "";
    var currentStructure = null;

    var inputCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var inputTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Structure Source" });

    var filePicker = window.FOSS.components.filePicker({
      testid: "data-structure-file-picker",
      title: "Open Data or HDF5 File",
      fileTypes: ["json", "yaml", "yml", "toml", "csv", "xml", "h5", "hdf5", "he5"],
      onSelect: function (val) {
        if (!val) return;
        if (isHdf5Path(val)) {
          showGenericTree(false);
          statusBar.textContent = "Opening HDF5 file...";
          hdf5Explorer.open(val);
          return;
        }
        showGenericTree(true);
        statusBar.textContent = "Inspecting structure...";
        window.FOSS.api("data_inspect_structure", { file_path: val }).then(function (res) {
          currentStructure = res;
          renderTree(res.root, filterQuery);
          statusBar.textContent = "[OK] Inspected " + res.format + " (" + (res.stats ? res.stats.total_nodes : 0) + " nodes)";
        }).catch(function (err) {
          statusBar.textContent = "Error: " + errorText(err);
        });
      }
    });

    var toggleLabel = window.FOSS.dom.el("span", { text: "Paste Text..." });
    var toggleTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-toggle-text-btn",
      "aria-label": "Toggle raw text input",
      title: "Paste Raw Text",
      onClick: function () {
        var isHidden = textEditorDrawer.classList.toggle("hidden");
        toggleLabel.textContent = isHidden ? "Paste Text..." : "Hide Text Box";
      }
    }, [window.FOSS.icons.el("file-text", 14), toggleLabel]);

    var textEditorDrawer = window.FOSS.dom.el("div", { className: "flex-col gap-2 hidden" });

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
        showGenericTree(true);
        statusBar.textContent = "Analyzing structure...";
        window.FOSS.api("data_inspect_structure", { content: content }).then(function (res) {
          currentStructure = res;
          renderTree(res.root, filterQuery);
          statusBar.textContent = "[OK] Inspected " + res.format + " payload (" + (res.stats ? res.stats.total_nodes : 0) + " nodes)";
        }).catch(function (err) {
          statusBar.textContent = "Error: " + errorText(err);
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Inspect Payload" })]);

    textEditorDrawer.appendChild(codeEditor.el);
    textEditorDrawer.appendChild(inspectTextBtn);

    inputCard.appendChild(inputTitle);
    inputCard.appendChild(filePicker.el);
    inputCard.appendChild(toggleTextBtn);
    inputCard.appendChild(textEditorDrawer);

    var detailsBox = window.FOSS.dom.el("div", {
      className: "wb-box wb-details text-xs font-mono",
      id: "data-node-details-content",
      text: "Click any node in the tree to view properties."
    });
    var detailsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-2" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Selected Node Details" }),
      detailsBox
    ]);

    sidebarCol.appendChild(inputCard);
    sidebarCol.appendChild(detailsCard);

    var stageCol = window.FOSS.dom.el("div", { className: "data-stage-pane" });
    var treeCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3 wb-card-fill" });
    var treeHeader = window.FOSS.dom.el("div", { className: "row items-center flex-wrap gap-2 wb-field-full" });

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
      className: "data-tree-root wb-tree",
      "data-testid": "data-structure-tree"
    });

    treeCard.appendChild(treeHeader);
    treeCard.appendChild(framedScroll(treeRoot));
    stageCol.appendChild(treeCard);

    var hdf5Explorer = createHdf5Explorer(function (msg) { statusBar.textContent = msg; });
    stageCol.appendChild(hdf5Explorer.el);

    function showGenericTree(generic) {
      detailsCard.classList.toggle("hidden", !generic);
      treeCard.classList.toggle("hidden", !generic);
      hdf5Explorer.el.classList.toggle("hidden", generic);
    }

    var workbench = window.FOSS.dom.el("div", { className: "split resizable data-workbench" }, [
      sidebarCol,
      window.FOSS.components.splitDivider({ side: "left" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(workbench);

    function renderTree(rootNode, filter) {
      treeRoot.innerHTML = "";
      if (!rootNode) {
        treeRoot.appendChild(window.FOSS.dom.el("div", {
          className: "text-sm text-muted p-4 text-center",
          text: "No structure to display. Open a file or paste data."
        }));
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
      var lines = [
        "Name: " + (node.name || ""),
        "Type: " + (node.type || ""),
        "Path: " + (node.path || "")
      ];
      if (node.shape) lines.push("Shape: " + JSON.stringify(node.shape));
      if (node.dtype) lines.push("Dtype: " + node.dtype);
      if (node.size_bytes !== undefined) lines.push("Size: " + node.size_bytes + " bytes");
      detailsBox.textContent = lines.join("\n");
    }

    renderTree(null, "");
  }

  function renderTablesTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
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

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [cleanBtn, transposeBtn, dedupBtn, csvToMdBtn, mdToCsvBtn]);

    var previewHost = window.FOSS.dom.el("div", { className: "wb-box-grow" }, [
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
        var tbl = window.FOSS.dom.el("table", { className: "table w-full" });
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

    var grid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [tableEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [previewHost])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(toolbar);
    panel.appendChild(grid);
  }

  function renderQueryTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "data-query-status",
      text: "Ready"
    });

    var pathInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
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
          statusBar.textContent = "Query error: " + errorText(err);
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
          statusBar.textContent = "Schema error: " + errorText(err);
        });
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Infer Schema" })]);

    var topBar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [
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

    var grid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [jsonEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [resultEditor])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(topBar);
    panel.appendChild(grid);
  }

  function renderUtilitiesTab(panel) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "data-utilities-status",
      text: "Ready"
    });

    var sidebarCol = window.FOSS.dom.el("div", { className: "data-sidebar-pane" });

    var randCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var randTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Random / Password Generator" });

    var defaultGeneratorType = String(toolDefault("generator_type", "password"));
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
    randKind.value = defaultGeneratorType;

    var randLen = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm wb-num-sm",
      value: "16",
      min: "4",
      max: "128",
      "aria-label": "Password Length"
    });

    var randOutput = window.FOSS.dom.el("div", {
      className: "wb-box font-mono text-sm",
      "data-testid": "data-utilities-random-output",
      text: "-"
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

    var stageCol = window.FOSS.dom.el("div", { className: "data-stage-pane" });

    var cronCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var cronTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Cron Expression Explainer" });

    var cronInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm font-mono",
      value: "*/15 * * * *",
      placeholder: "e.g. 0 0 * * * or */5 * * * *",
      "aria-label": "Cron Expression"
    });

    var cronDesc = window.FOSS.dom.el("div", {
      className: "wb-box text-sm font-bold text-success",
      text: "Every 15 minutes"
    });

    var cronRunsList = window.FOSS.dom.el("div", { className: "flex-col gap-1 wb-field-full" });

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
              className: "wb-box font-mono text-xs",
              text: dtStr
            }));
          });
          statusBar.textContent = "Upcoming execution schedule computed.";
        }).catch(function (err) {
          statusBar.textContent = "Cron error: " + errorText(err);
        });
      }
    }, [window.FOSS.icons.el("clock", 14), window.FOSS.dom.el("span", { text: "Calculate Schedule" })]);

    cronCard.appendChild(cronTitle);
    cronCard.appendChild(window.FOSS.components.field({
      label: "Expression (minute hour dom month dow)",
      control: cronInput,
      wrapOk: true
    }));
    cronCard.appendChild(cronBtn);
    cronCard.appendChild(cronDesc);
    cronCard.appendChild(cronRunsList);

    var icsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3 wb-grow" });
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

    var icsOutput = window.FOSS.components.codeEditor({
      testid: "data-ics-output",
      title: "Generated .ICS Event",
      placeholder: "ICS payload will appear here...",
      ariaLabel: "Generated ICS payload",
      fillHeight: true
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

    icsCard.appendChild(icsTitle);
    icsCard.appendChild(window.FOSS.components.field("Title", calTitleInput));
    icsCard.appendChild(window.FOSS.components.field("Start Time (ISO/UTC)", calStartInput));
    icsCard.appendChild(icsBtn);
    icsCard.appendChild(icsOutput.el);

    stageCol.appendChild(cronCard);
    stageCol.appendChild(icsCard);

    var workbench = window.FOSS.dom.el("div", { className: "split resizable data-workbench" }, [
      sidebarCol,
      window.FOSS.components.splitDivider({ side: "left" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(workbench);
  }

  window.FOSS.router.register({
    id: "data",
    title: "Data Studio",
    navName: "Data",
    category: "Data",
    icon: "data",
    workbench: true,
    defaults: [
      {
        key: "indent",
        label: "Indent spacing",
        type: "select",
        options: [
          { value: "2", label: "2 spaces" },
          { value: "4", label: "4 spaces" },
          { value: "8", label: "8 spaces" }
        ],
        default: "2",
        hint: "Spaces per level when formatting JSON, YAML, and XML."
      },
      {
        key: "target_format",
        label: "Conversion target",
        type: "select",
        options: TARGET_FORMATS.map(function (fmt) {
          return { value: fmt, label: fmt.toUpperCase() };
        }),
        default: "yaml",
        hint: "Format preselected in the Convert dropdown."
      },
      {
        key: "generator_type",
        label: "Default random generator type",
        type: "select",
        options: [
          { value: "password", label: "Cryptographic Password" },
          { value: "uuid", label: "UUID v4" },
          { value: "token", label: "Hex Auth Token" },
          { value: "number", label: "Random Integer" },
          { value: "name", label: "Full Name" }
        ],
        default: "password"
      }
    ],
    tabs: [
      { id: "editor", label: "Format & Convert", aliases: ["main", "format"], render: renderEditorTab },
      { id: "structure", label: "HDF5", aliases: ["tree", "hdf5"], render: renderStructureTab },
      { id: "tables", label: "Tables", render: renderTablesTab },
      { id: "query", label: "JSONPath & Schema", render: renderQueryTab },
      { id: "utilities", label: "Utilities", render: renderUtilitiesTab }
    ]
  });
})();
