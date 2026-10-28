// Data Studio workspace: structure inspection, tables, units, random generator, and calendar.
window.FOSS = window.FOSS || {};

(function () {
  function renderStructureTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Inspect and explore schema structure, keys, nested objects, arrays, and HDF5 datasets and groups."
    });

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-structure-status",
      text: "Ready"
    });

    var statsContainer = window.FOSS.dom.el("div", {
      className: "card stack hidden",
      gap: "sm"
    });

    var treeRoot = window.FOSS.dom.el("div", {
      className: "data-tree-root",
      "data-testid": "data-structure-tree"
    });

    var detailsCard = window.FOSS.dom.el("div", {
      className: "card stack hidden",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Selected Node Details" }),
      window.FOSS.dom.el("div", { className: "text-xs font-mono", id: "data-node-details-content", text: "Click any node in the tree to view properties." })
    ]);

    var textEditorDrawer = window.FOSS.dom.el("div", {
      className: "card stack hidden",
      gap: "sm"
    });

    var codeEditor = window.FOSS.components.codeEditor({
      testid: "data-structure-text-input",
      title: "Raw Data Payload (JSON / YAML / TOML / CSV / XML)",
      placeholder: '{\n  "project": "FOSSEverything",\n  "version": "2.0",\n  "modules": ["pdf", "image", "data"]\n}',
      ariaLabel: "Raw data input for structure inspection"
    });

    var inspectTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-structure-inspect-btn",
      "aria-label": "Inspect pasted text structure",
      title: "Inspect pasted text structure",
      type: "button",
      onClick: function () {
        var content = codeEditor.getValue();
        if (!content.trim()) return;
        statusBar.textContent = "Analyzing structure...";
        window.FOSS.api("data_inspect_structure", { content: content }).then(function (res) {
          renderParsedStructure(res);
          statusBar.textContent = "[OK] Inspected " + res.format + " payload (" + res.stats.total_nodes + " nodes)";
        }).catch(function (err) {
          statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Inspect Payload" })
    ]);

    textEditorDrawer.appendChild(codeEditor.el);
    textEditorDrawer.appendChild(inspectTextBtn);

    var currentStructure = null;
    var filterQuery = "";

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
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
      type: "button",
      onClick: function () {
        var children = treeRoot.querySelectorAll(".data-tree-children");
        children.forEach(function (c) { c.classList.remove("collapsed"); });
        var toggles = treeRoot.querySelectorAll(".data-tree-toggle");
        toggles.forEach(function (t) { t.textContent = "\u25bc"; });
      }
    }, [
      window.FOSS.icons.el("plus", 14),
      window.FOSS.dom.el("span", { text: "Expand All" })
    ]);

    var collapseAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-collapse-all",
      "aria-label": "Collapse all sections",
      title: "Collapse all sections",
      type: "button",
      onClick: function () {
        var children = treeRoot.querySelectorAll(".data-tree-children");
        children.forEach(function (c) { c.classList.add("collapsed"); });
        var toggles = treeRoot.querySelectorAll(".data-tree-toggle");
        toggles.forEach(function (t) { t.textContent = "\u25b6"; });
      }
    }, [
      window.FOSS.icons.el("minus", 14),
      window.FOSS.dom.el("span", { text: "Collapse All" })
    ]);

    var toggleTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-structure-toggle-text-btn",
      "aria-label": "Toggle raw text input",
      title: "Toggle raw text input",
      type: "button",
      onClick: function () {
        textEditorDrawer.classList.toggle("hidden");
      }
    }, [
      window.FOSS.icons.el("edit", 16),
      window.FOSS.dom.el("span", { text: "Paste / Edit Text" })
    ]);

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-structure-open-btn",
      "aria-label": "Open file for structure inspection",
      title: "Open file for structure inspection",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var filePath = res.paths[0];
          statusBar.textContent = "Inspecting " + filePath + "...";
          window.FOSS.api("data_inspect_structure", { file_path: filePath }).then(function (r) {
            renderParsedStructure(r);
            statusBar.textContent = "[OK] Inspected " + r.format + " file: " + filePath;
          }).catch(function (err) {
            statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
          });
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Open File..." })
    ]);

    var sampleSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-structure-sample-select",
      "aria-label": "Load sample structure"
    }, [
      window.FOSS.dom.el("option", { value: "", text: "Load Sample Data..." }),
      window.FOSS.dom.el("option", { value: "json", text: "Sample JSON (Nested Users & Orders)" }),
      window.FOSS.dom.el("option", { value: "yaml", text: "Sample YAML (App Config)" }),
      window.FOSS.dom.el("option", { value: "csv", text: "Sample CSV (Sensors Table)" }),
      window.FOSS.dom.el("option", { value: "xml", text: "Sample XML (Catalog Hierarchy)" })
    ]);

    sampleSelect.addEventListener("change", function () {
      var val = sampleSelect.value;
      if (!val) return;
      var samplePayloads = {
        json: '{\n  "version": 2.4,\n  "company": "DeepSpace Dynamics",\n  "satellites": [\n    {"id": "SAT-01", "orbit_km": 540, "active": true, "sensors": ["optical", "infrared"]},\n    {"id": "SAT-02", "orbit_km": 720, "active": false, "sensors": ["radar"]}\n  ],\n  "telemetry": {"downlink_mbs": 1250, "packet_loss": 0.002, "healthy": true}\n}',
        yaml: 'app:\n  name: FOSSEverything\n  environment: production\n  database:\n    host: 127.0.0.1\n    port: 5432\n    pool_size: 20\n  features:\n    - data_studio\n    - pdf_tools\n    - model3d',
        csv: 'timestamp,sensor_id,temperature_c,pressure_kpa,status\n2026-10-27T10:00:00,TMP-01,23.5,101.3,OK\n2026-10-27T10:01:00,TMP-02,24.1,101.4,OK\n2026-10-27T10:02:00,TMP-03,28.7,100.9,WARN',
        xml: '<catalog version="1.0">\n  <book id="bk101">\n    <author>Gambardella, Matthew</author>\n    <title>XML Developer Guide</title>\n    <genre>Computer</genre>\n    <price>44.95</price>\n  </book>\n  <book id="bk102">\n    <author>Ralls, Kim</author>\n    <title>Midnight Rain</title>\n    <genre>Fantasy</genre>\n    <price>5.95</price>\n  </book>\n</catalog>'
      };
      var sample = samplePayloads[val];
      if (sample) {
        codeEditor.setValue(sample);
        window.FOSS.api("data_inspect_structure", { content: sample }).then(function (r) {
          renderParsedStructure(r);
          statusBar.textContent = "[OK] Loaded sample " + r.format + " data";
        });
      }
      sampleSelect.selectedIndex = 0;
    });

    function renderParsedStructure(res) {
      currentStructure = res;
      statsContainer.classList.remove("hidden");
      statsContainer.innerHTML = "";

      var formatBadge = window.FOSS.dom.el("span", {
        className: "badge info",
        text: res.format + (res.file_path ? " File" : " Payload")
      });

      var nodesCountPill = window.FOSS.dom.el("span", {
        className: "badge",
        text: (res.stats.total_nodes || 0) + " total elements"
      });

      var depthPill = window.FOSS.dom.el("span", {
        className: "badge",
        text: "Max depth: " + (res.stats.max_depth || 0)
      });

      var sizePill = window.FOSS.dom.el("span", {
        className: "badge",
        text: res.file_size ? (res.file_size + " bytes") : ""
      });

      var pillsRow = window.FOSS.dom.el("div", {
        className: "row scroll-x",
        gap: "xs"
      }, [formatBadge, nodesCountPill, depthPill, sizePill]);

      // Types breakdown row.
      var breakdownRow = window.FOSS.dom.el("div", {
        className: "row scroll-x text-xs text-muted",
        gap: "sm"
      });

      var tb = res.stats.types_breakdown || {};
      for (var typeKey in tb) {
        breakdownRow.appendChild(window.FOSS.dom.el("span", {
          text: typeKey + ": " + tb[typeKey]
        }));
      }

      statsContainer.appendChild(pillsRow);
      statsContainer.appendChild(breakdownRow);

      renderTree(res.root, filterQuery);
    }

    function renderTree(rootNode, filter) {
      treeRoot.innerHTML = "";
      if (!rootNode) return;

      var nodeEl = buildTreeNodeElement(rootNode, filter, 0);
      if (nodeEl) {
        treeRoot.appendChild(nodeEl);
      } else {
        treeRoot.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-xs p-2",
          text: "No elements match the current filter query."
        }));
      }
    }

    function buildTreeNodeElement(node, filter, depth) {
      var hasChildren = node.children && node.children.length > 0;
      var nameMatch = !filter || node.name.toLowerCase().indexOf(filter) !== -1;
      var valMatch = !filter || (node.value && String(node.value).toLowerCase().indexOf(filter) !== -1);

      var childElements = [];
      if (hasChildren) {
        for (var i = 0; i < node.children.length; i++) {
          var cEl = buildTreeNodeElement(node.children[i], filter, depth + 1);
          if (cEl) childElements.push(cEl);
        }
      }

      if (filter && !nameMatch && !valMatch && childElements.length === 0) {
        return null;
      }

      var itemContainer = window.FOSS.dom.el("div", { className: "data-tree-item" });

      var row = window.FOSS.dom.el("div", {
        className: "data-tree-row",
        onClick: function (e) {
          e.stopPropagation();
          showNodeDetails(node);
        }
      });

      var toggleIcon = window.FOSS.dom.el("span", {
        className: "data-tree-toggle",
        "data-decorative": "true",
        "aria-hidden": "true",
        text: hasChildren ? (depth < 2 ? "\u25bc" : "\u25b6") : " "
      });

      var badgeClass = "data-tree-badge data-tree-badge-" + (node.type || "string");
      var typeBadge = window.FOSS.dom.el("span", {
        className: badgeClass,
        text: node.type || "val"
      });

      var keyEl = window.FOSS.dom.el("span", {
        className: "data-tree-key",
        text: node.name
      });

      var valEl = window.FOSS.dom.el("span", {
        className: "data-tree-val",
        text: node.preview ? (": " + node.preview) : ""
      });

      row.appendChild(toggleIcon);
      row.appendChild(typeBadge);
      row.appendChild(keyEl);
      row.appendChild(valEl);
      itemContainer.appendChild(row);

      if (hasChildren) {
        var childrenBox = window.FOSS.dom.el("div", {
          className: "data-tree-children" + (depth >= 2 && !filter ? " collapsed" : "")
        });

        childElements.forEach(function (ce) { childrenBox.appendChild(ce); });
        itemContainer.appendChild(childrenBox);

        row.addEventListener("click", function (e) {
          e.stopPropagation();
          showNodeDetails(node);
          var isCollapsed = childrenBox.classList.toggle("collapsed");
          toggleIcon.textContent = isCollapsed ? "\u25b6" : "\u25bc";
        });
      } else {
        row.addEventListener("click", function (e) {
          e.stopPropagation();
          showNodeDetails(node);
        });
      }

      return itemContainer;
    }

    function showNodeDetails(node) {
      detailsCard.classList.remove("hidden");
      var host = detailsCard.querySelector("#data-node-details-content");
      if (!host) return;

      host.innerHTML = "";
      var grid = window.FOSS.dom.el("div", { className: "stack", gap: "xs" }, [
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("strong", { text: "Path:" }),
          window.FOSS.dom.el("span", { text: node.path || "-" })
        ]),
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("strong", { text: "Type:" }),
          window.FOSS.dom.el("span", { text: node.type || "unknown" }),
          window.FOSS.dom.el("strong", { text: "Elements/Length:" }),
          window.FOSS.dom.el("span", { text: String(node.length !== undefined ? node.length : "-") })
        ])
      ]);

      if (node.shape) {
        grid.appendChild(window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("strong", { text: "Dataset Shape:" }),
          window.FOSS.dom.el("span", { text: JSON.stringify(node.shape) }),
          window.FOSS.dom.el("strong", { text: "Data Type:" }),
          window.FOSS.dom.el("span", { text: String(node.dtype || "-") })
        ]));
      }

      if (node.shape || (currentStructure && currentStructure.format === "HDF5")) {
        var slicePathInput = window.FOSS.dom.el("input", {
          className: "input input-sm",
          "data-testid": "data-hdf5-slice-path",
          value: node.path || node.name || "/",
          "aria-label": "HDF5 Dataset Path",
          title: "HDF5 Dataset Path"
        });

        var sliceSpecInput = window.FOSS.dom.el("input", {
          className: "input input-sm",
          "data-testid": "data-hdf5-slice-spec",
          placeholder: "e.g. 0:100 or :",
          value: ":",
          "aria-label": "Slice expression",
          title: "Slice expression (e.g. 0:100, :)"
        });

        var formatSelect = window.FOSS.dom.el("select", {
          className: "input input-sm",
          "data-testid": "data-hdf5-slice-format",
          "aria-label": "Export format",
          title: "Export format"
        }, [
          window.FOSS.dom.el("option", { value: "csv", text: "CSV (.csv)" }),
          window.FOSS.dom.el("option", { value: "json", text: "JSON (.json)" }),
          window.FOSS.dom.el("option", { value: "npy", text: "NumPy (.npy)" })
        ]);

        var exportSliceBtn = window.FOSS.dom.el("button", {
          className: "btn btn-primary btn-sm",
          "data-testid": "data-hdf5-slice-export-btn",
          type: "button",
          onClick: function () {
            var targetPath = slicePathInput.value.trim();
            var spec = sliceSpecInput.value.trim() || ":";
            var fmt = formatSelect.value;
            var ext = "." + fmt;
            var defaultName = (targetPath.split("/").pop() || "dataset") + "_slice" + ext;
            window.FOSS.api("select_save_path", { title: "Save Sliced HDF5 Dataset", default_name: defaultName, file_types: [fmt] }).then(function (saveRes) {
              var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
              if (!outP) return;
              statusBar.textContent = "Exporting slice...";
              window.FOSS.api("data_hdf5_export_slice", {
                file_path: currentStructure ? currentStructure.file_path : "",
                dataset_path: targetPath,
                slice_spec: spec,
                output_path: outP,
                format: fmt
              }).then(function (res) {
                if (res && res.output_path) {
                  statusBar.textContent = "[OK] Exported HDF5 slice (" + res.size + " elements, shape " + JSON.stringify(res.shape) + ") to " + res.output_path;
                  window.FOSS.toast.show({ message: "Exported HDF5 slice to " + res.output_path, type: "success" });
                }
              }).catch(function (err) {
                statusBar.textContent = "Slice export error: " + (err && err.message ? err.message : String(err));
              });
            });
          }
        }, [
          window.FOSS.icons.el("download", 14),
          window.FOSS.dom.el("span", { text: "Export Slice" })
        ]);

        var sliceCard = window.FOSS.dom.el("div", {
          className: "card p-sm border rounded mt-sm",
          "data-testid": "data-hdf5-slice-card"
        }, [
          window.FOSS.dom.el("strong", { className: "text-xs font-semibold", text: "HDF5 Dataset Slice Exporter:" }),
          window.FOSS.dom.el("div", { className: "row gap-xs items-center mt-xs" }, [
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Dataset:" }),
            slicePathInput,
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Slice:" }),
            sliceSpecInput,
            formatSelect,
            exportSliceBtn
          ])
        ]);

        grid.appendChild(sliceCard);
      }

      if (node.value !== undefined) {
        var fullValBox = window.FOSS.dom.el("pre", {
          className: "p-2 bg-surface border rounded text-xs",
          style: "max-height: 8rem; overflow: auto; white-space: pre-wrap;",
          text: String(node.value)
        });
        grid.appendChild(fullValBox);
      }

      host.appendChild(grid);
    }

    var toolbar = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [
      openBtn,
      sampleSelect,
      toggleTextBtn,
      filterInput,
      expandAllBtn,
      collapseAllBtn
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [
      desc,
      toolbar,
      textEditorDrawer,
      statsContainer,
      treeRoot,
      detailsCard,
      statusBar
    ]));

    // Load initial sample JSON to give immediate interactive value.
    setTimeout(function () {
      var initialJson = '{\n  "service": "Telemetry Hub",\n  "active": true,\n  "endpoints": [\n    {"url": "/api/v1/sensors", "protocol": "https"},\n    {"url": "/api/v1/events", "protocol": "wss"}\n  ],\n  "metrics": {"uptime_seconds": 86400, "cpu_load": 0.14}\n}';
      codeEditor.setValue(initialJson);
      window.FOSS.api("data_inspect_structure", { content: initialJson }).then(function (r) {
        renderParsedStructure(r);
      }).catch(function () {});
    }, 50);
  }

  function renderTablesTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Clean, normalize, adjust separators, and convert tables between CSV, TSV, custom delimited, and Markdown."
    });

    var tableEditor = window.FOSS.components.codeEditor({
      testid: "data-tables-input",
      title: "Markdown Table / Delimited Data",
      placeholder: "| Item | Price | Qty |\n| :--- | :--- | :--- |\n| Apple | $1.20 | 10 |\n| Orange | $0.85 | 15 |",
      ariaLabel: "Table editor content"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-tables-status",
      text: "Ready"
    });

    var previewHost = window.FOSS.dom.el("div", {
      className: "card stack hidden",
      "data-testid": "data-tables-html-preview",
      gap: "sm"
    });

    var delimSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-tables-delimiter",
      "aria-label": "Table separator delimiter"
    }, [
      window.FOSS.dom.el("option", { value: "comma", text: "Comma (,)" }),
      window.FOSS.dom.el("option", { value: "semicolon", text: "Semicolon (;)" }),
      window.FOSS.dom.el("option", { value: "tab", text: "Tab (\\t)" }),
      window.FOSS.dom.el("option", { value: "pipe", text: "Pipe (|)" }),
      window.FOSS.dom.el("option", { value: "colon", text: "Colon (:)" }),
      window.FOSS.dom.el("option", { value: "custom", text: "Custom Delimiter..." })
    ]);

    var customDelimInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm hidden",
      "data-testid": "data-tables-custom-delimiter",
      value: "~",
      style: "width: 4rem;",
      placeholder: "Delim",
      "aria-label": "Custom delimiter string"
    });

    delimSelect.addEventListener("change", function () {
      if (delimSelect.value === "custom") {
        customDelimInput.classList.remove("hidden");
      } else {
        customDelimInput.classList.add("hidden");
      }
    });

    var quoteSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-tables-quote",
      "aria-label": "Quote character"
    }, [
      window.FOSS.dom.el("option", { value: '"', text: 'Double quote (")' }),
      window.FOSS.dom.el("option", { value: "'", text: "Single quote (')" }),
      window.FOSS.dom.el("option", { value: "none", text: "None" })
    ]);

    var headerCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "data-tables-header-check",
      checked: true,
      id: "data-tables-header-check-el",
      "aria-label": "Include header row"
    });

    var headerLabel = window.FOSS.dom.el("label", {
      htmlFor: "data-tables-header-check-el",
      className: "row text-xs cursor-pointer",
      gap: "xs"
    }, [
      headerCheck,
      window.FOSS.dom.el("span", { text: "Header Row" })
    ]);

    function getActiveDelimiter() {
      if (delimSelect.value === "custom") {
        return customDelimInput.value || ",";
      }
      return delimSelect.value;
    }

    var cleanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-tables-clean",
      "aria-label": "Clean table",
      title: "Clean table",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_clean_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Cleaned table whitespace and empty columns";
        });
      }
    }, [
      window.FOSS.icons.el("edit", 16),
      window.FOSS.dom.el("span", { text: "Clean Table" })
    ]);

    var normalizeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-normalize",
      "aria-label": "Normalize table",
      title: "Normalize table",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_normalize_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Normalized table padding";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Normalize" })
    ]);

    var csvToMdBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-csv-to-md",
      "aria-label": "CSV/DSV to Markdown table",
      title: "CSV/DSV to Markdown table",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        var delim = getActiveDelimiter();
        var incHeader = headerCheck.checked;
        window.FOSS.api("data_csv_to_table", { content: content, delimiter: delim, include_header: incHeader }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Converted delimited text to Markdown table";
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Delimited to Markdown" })
    ]);

    var tableToCsvBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-to-csv",
      "aria-label": "Markdown table to Delimited CSV/DSV",
      title: "Markdown table to Delimited CSV/DSV",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        var delim = getActiveDelimiter();
        var quote = quoteSelect.value === "none" ? "" : quoteSelect.value;
        var incHeader = headerCheck.checked;
        window.FOSS.api("data_table_to_csv", {
          content: content,
          delimiter: delim,
          include_header: incHeader,
          quote_char: quote
        }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Converted Markdown table to delimited text (" + delimSelect.value + ")";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Markdown to Delimited" })
    ]);

    var targetDelimSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-tables-target-delimiter",
      "aria-label": "Target delimiter for separator change"
    }, [
      window.FOSS.dom.el("option", { value: "tab", text: "Convert to Tab (\\t)" }),
      window.FOSS.dom.el("option", { value: "comma", text: "Convert to Comma (,)" }),
      window.FOSS.dom.el("option", { value: "semicolon", text: "Convert to Semicolon (;)" }),
      window.FOSS.dom.el("option", { value: "pipe", text: "Convert to Pipe (|)" })
    ]);

    var changeDelimBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-change-delimiter-btn",
      "aria-label": "Change separator delimiter",
      title: "Change separator delimiter",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        var srcDel = getActiveDelimiter();
        var tgtDel = targetDelimSelect.value;
        window.FOSS.api("data_change_delimiter", {
          content: content,
          from_delimiter: srcDel,
          to_delimiter: tgtDel
        }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Converted delimiter from " + srcDel + " to " + tgtDel;
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Change Separator" })
    ]);

    var parseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-tables-parse",
      "aria-label": "Parse Markdown table",
      title: "Parse Markdown table",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_table_to_rows", { content: content }).then(function (res) {
          var rows = res.rows || [];
          statusEl.textContent = "[OK] Parsed " + rows.length + " structured rows";
          renderHtmlTablePreview(rows);
        });
      }
    }, [
      window.FOSS.icons.el("table", 16),
      window.FOSS.dom.el("span", { text: "Parse Table" })
    ]);

    function renderHtmlTablePreview(rows) {
      if (!rows || !rows.length) {
        previewHost.classList.add("hidden");
        return;
      }
      previewHost.classList.remove("hidden");
      previewHost.innerHTML = "";
      previewHost.appendChild(window.FOSS.dom.el("span", { className: "card-title", text: "Live Table Preview" }));

      var table = window.FOSS.dom.el("table", {
        className: "table w-full text-xs font-mono border rounded",
        style: "border-collapse: collapse; text-align: left;"
      });

      var headers = Object.keys(rows[0]);
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", { className: "bg-raised" },
          headers.map(function (h) {
            return window.FOSS.dom.el("th", { className: "p-2 border", text: h });
          })
        )
      ]);

      var tbody = window.FOSS.dom.el("tbody", {},
        rows.map(function (row) {
          return window.FOSS.dom.el("tr", { className: "border" },
            headers.map(function (h) {
              return window.FOSS.dom.el("td", { className: "p-2 border", text: row[h] !== undefined ? String(row[h]) : "" });
            })
          );
        })
      );

      table.appendChild(thead);
      table.appendChild(tbody);
      previewHost.appendChild(table);
    }

    var optionsBar = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Separator:" }),
      delimSelect,
      customDelimInput,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Quote:" }),
      quoteSelect,
      headerLabel,
      targetDelimSelect,
      changeDelimBtn
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [
      cleanBtn,
      normalizeBtn,
      csvToMdBtn,
      tableToCsvBtn,
      parseBtn
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [
      desc,
      optionsBar,
      actionsRow,
      tableEditor.el,
      previewHost,
      statusEl
    ]));
  }

  var UNIT_CATEGORIES = {
    "Length": [
      { id: "m", label: "Meters (m)" },
      { id: "cm", label: "Centimeters (cm)" },
      { id: "mm", label: "Millimeters (mm)" },
      { id: "km", label: "Kilometers (km)" },
      { id: "in", label: "Inches (in)" },
      { id: "ft", label: "Feet (ft)" },
      { id: "yd", label: "Yards (yd)" },
      { id: "mi", label: "Miles (mi)" }
    ],
    "Weight": [
      { id: "kg", label: "Kilograms (kg)" },
      { id: "g", label: "Grams (g)" },
      { id: "mg", label: "Milligrams (mg)" },
      { id: "lb", label: "Pounds (lb)" },
      { id: "oz", label: "Ounces (oz)" },
      { id: "st", label: "Stones (st)" }
    ],
    "Temperature": [
      { id: "c", label: "Celsius (C)" },
      { id: "f", label: "Fahrenheit (F)" },
      { id: "k", label: "Kelvin (K)" }
    ],
    "Time": [
      { id: "s", label: "Seconds (s)" },
      { id: "ms", label: "Milliseconds (ms)" },
      { id: "min", label: "Minutes (min)" },
      { id: "h", label: "Hours (h)" },
      { id: "day", label: "Days (day)" }
    ],
    "Area": [
      { id: "m2", label: "Square Meters (m2)" },
      { id: "cm2", label: "Square Centimeters (cm2)" },
      { id: "mm2", label: "Square Millimeters (mm2)" },
      { id: "km2", label: "Square Kilometers (km2)" },
      { id: "ft2", label: "Square Feet (ft2)" },
      { id: "in2", label: "Square Inches (in2)" },
      { id: "yd2", label: "Square Yards (yd2)" },
      { id: "ac", label: "Acres (ac)" },
      { id: "ha", label: "Hectares (ha)" }
    ],
    "Volume": [
      { id: "l", label: "Liters (l)" },
      { id: "ml", label: "Milliliters (ml)" },
      { id: "m3", label: "Cubic Meters (m3)" },
      { id: "gal", label: "Gallons (gal)" },
      { id: "qt", label: "Quarts (qt)" },
      { id: "pt", label: "Pints (pt)" },
      { id: "cup", label: "Cups (cup)" },
      { id: "us_fl_oz", label: "Fluid Ounces (fl oz)" }
    ],
    "Speed": [
      { id: "kmh", label: "km/h" },
      { id: "mps", label: "m/s" },
      { id: "mph", label: "mph" },
      { id: "knot", label: "Knots" }
    ],
    "Pressure": [
      { id: "bar", label: "Bar" },
      { id: "pa", label: "Pascals (Pa)" },
      { id: "kpa", label: "Kilopascals (kPa)" },
      { id: "mpa", label: "Megapascals (MPa)" },
      { id: "psi", label: "PSI" }
    ],
    "Angle": [
      { id: "deg", label: "Degrees (deg)" },
      { id: "rad", label: "Radians (rad)" },
      { id: "grad", label: "Gradians (grad)" },
      { id: "turn", label: "Turns" }
    ],
    "Data": [
      { id: "mb", label: "Megabytes (MB)" },
      { id: "kb", label: "Kilobytes (KB)" },
      { id: "gb", label: "Gigabytes (GB)" },
      { id: "tb", label: "Terabytes (TB)" },
      { id: "b", label: "Bytes (B)" },
      { id: "mib", label: "Mebibytes (MiB)" },
      { id: "kib", label: "Kibibytes (KiB)" },
      { id: "gib", label: "Gibibytes (GiB)" }
    ]
  };

  function renderUnitsTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Convert units across physical dimensions or configure pseudorandom generators."
    });

    var catSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-units-category",
      "aria-label": "Unit category"
    });
    for (var catName in UNIT_CATEGORIES) {
      catSelect.appendChild(window.FOSS.dom.el("option", { value: catName, text: catName }));
    }

    var valInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-val",
      value: "100",
      "aria-label": "Unit numerical value"
    });

    var srcUnitSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-units-from",
      "aria-label": "Source measurement unit"
    });

    var tgtUnitSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-units-to",
      "aria-label": "Target measurement unit"
    });

    function populateUnits(cat) {
      srcUnitSelect.innerHTML = "";
      tgtUnitSelect.innerHTML = "";
      var units = UNIT_CATEGORIES[cat] || [];
      units.forEach(function (u, idx) {
        srcUnitSelect.appendChild(window.FOSS.dom.el("option", { value: u.id, text: u.label }));
        tgtUnitSelect.appendChild(window.FOSS.dom.el("option", { value: u.id, text: u.label }));
      });
      if (units.length > 1) {
        tgtUnitSelect.selectedIndex = 1;
      }
    }

    catSelect.addEventListener("change", function () {
      populateUnits(catSelect.value);
      doConvert();
    });

    populateUnits("Length");
    srcUnitSelect.value = "m";
    tgtUnitSelect.value = "ft";

    var unitRes = window.FOSS.dom.el("div", {
      className: "font-mono text-sm",
      "data-testid": "data-units-output",
      text: "Result: 328.084 ft"
    });

    function doConvert() {
      var v = parseFloat(valInput.value);
      if (isNaN(v)) return;
      var u1 = srcUnitSelect.value;
      var u2 = tgtUnitSelect.value;
      window.FOSS.api("data_convert_units", { value: v, source_unit: u1, target_unit: u2 }).then(function (res) {
        if (res && res.result !== undefined) {
          unitRes.textContent = "Result: " + res.result + " " + u2;
        }
      });
    }

    srcUnitSelect.addEventListener("change", doConvert);
    tgtUnitSelect.addEventListener("change", doConvert);
    valInput.addEventListener("input", doConvert);

    // Prominent Swap Units button interchanging From and To units.
    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-units-swap-btn",
      id: "data-units-swap",
      "aria-label": "Swap units",
      title: "Swap units",
      type: "button",
      onClick: function () {
        var s = srcUnitSelect.value;
        srcUnitSelect.value = tgtUnitSelect.value;
        tgtUnitSelect.value = s;
        doConvert();
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Swap Units" })
    ]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-units-convert",
      "aria-label": "Convert units",
      title: "Convert units",
      type: "button",
      onClick: doConvert
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Convert Unit" })
    ]);

    var unitCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Physical Unit Converter" }),
      window.FOSS.dom.el("div", { className: "row scroll-x", gap: "sm" }, [
        catSelect,
        valInput,
        srcUnitSelect,
        swapBtn,
        window.FOSS.dom.el("span", { text: "to" }),
        tgtUnitSelect,
        convertBtn
      ]),
      unitRes
    ]);

    // Enhanced Random Generator with configurable length, count, ranges, and charsets.
    var randSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-units-random-type",
      "aria-label": "Random generator kind"
    }, [
      window.FOSS.dom.el("option", { value: "string", text: "Alphanumeric String" }),
      window.FOSS.dom.el("option", { value: "password", text: "Secure Password" }),
      window.FOSS.dom.el("option", { value: "hex", text: "Hexadecimal Token" }),
      window.FOSS.dom.el("option", { value: "number", text: "Random Integer" }),
      window.FOSS.dom.el("option", { value: "float", text: "Random Float" }),
      window.FOSS.dom.el("option", { value: "uuid", text: "UUID v4" }),
      window.FOSS.dom.el("option", { value: "name", text: "Full Name" }),
      window.FOSS.dom.el("option", { value: "email", text: "Email Address" }),
      window.FOSS.dom.el("option", { value: "lorem", text: "Lorem Ipsum Text" })
    ]);

    var randLengthInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-random-length",
      value: "16",
      min: "1",
      max: "1024",
      style: "width: 5rem;",
      placeholder: "Length",
      "aria-label": "Random value length"
    });

    var randCountInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-random-count",
      value: "1",
      min: "1",
      max: "100",
      style: "width: 4.5rem;",
      placeholder: "Count",
      "aria-label": "Number of values to generate"
    });

    var randMinInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-random-min",
      value: "1",
      style: "width: 5rem;",
      placeholder: "Min",
      "aria-label": "Minimum number value"
    });

    var randMaxInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-random-max",
      value: "100",
      style: "width: 5rem;",
      placeholder: "Max",
      "aria-label": "Maximum number value"
    });

    var upperCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "data-units-random-upper",
      checked: true,
      id: "data-units-rand-upper-el",
      "aria-label": "Include uppercase letters"
    });

    var lowerCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "data-units-random-lower",
      checked: true,
      id: "data-units-rand-lower-el",
      "aria-label": "Include lowercase letters"
    });

    var digitsCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "data-units-random-digits",
      checked: true,
      id: "data-units-rand-digits-el",
      "aria-label": "Include digits"
    });

    var symbolsCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "data-units-random-symbols",
      checked: false,
      id: "data-units-rand-symbols-el",
      "aria-label": "Include special symbols"
    });

    var customAlphabetInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-units-random-alphabet",
      placeholder: "Custom charset...",
      "aria-label": "Custom alphabet characters"
    });

    var randRes = window.FOSS.dom.el("textarea", {
      className: "input font-mono text-xs w-full",
      "data-testid": "data-units-random-output",
      "aria-label": "Generated random output",
      rows: 3,
      readOnly: true,
      value: "-"
    });

    var randBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-units-random-generate",
      "aria-label": "Generate random token",
      title: "Generate random token",
      type: "button",
      onClick: function () {
        var cat = randSelect.value;
        var len = parseInt(randLengthInput.value, 10) || 16;
        var cnt = parseInt(randCountInput.value, 10) || 1;
        var minVal = parseInt(randMinInput.value, 10) || 0;
        var maxVal = parseInt(randMaxInput.value, 10) || 100;
        var alphabet = customAlphabetInput.value.trim() || undefined;

        window.FOSS.api("data_random_value", {
          category: cat,
          length: len,
          count: cnt,
          min_value: minVal,
          max_value: maxVal,
          include_uppercase: upperCheck.checked,
          include_lowercase: lowerCheck.checked,
          include_digits: digitsCheck.checked,
          include_symbols: symbolsCheck.checked,
          custom_alphabet: alphabet
        }).then(function (res) {
          if (Array.isArray(res.values)) {
            randRes.value = res.values.join("\n");
          } else {
            randRes.value = String(res.value);
          }
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Generate Random" })
    ]);

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-units-random-copy",
      "aria-label": "Copy generated value to clipboard",
      title: "Copy generated value to clipboard",
      type: "button",
      onClick: function () {
        if (navigator.clipboard && randRes.value) {
          navigator.clipboard.writeText(randRes.value).then(function () {
            if (window.FOSS.toast) window.FOSS.toast("Copied to clipboard!");
          });
        }
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Copy" })
    ]);

    var randCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Random Value Generator" }),
      window.FOSS.dom.el("div", { className: "row scroll-x", gap: "sm" }, [
        randSelect,
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Len:" }),
        randLengthInput,
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Count:" }),
        randCountInput,
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Range:" }),
        randMinInput,
        randMaxInput
      ]),
      window.FOSS.dom.el("div", { className: "row scroll-x text-xs", gap: "md" }, [
        window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [upperCheck, window.FOSS.dom.el("span", { text: "A-Z" })]),
        window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [lowerCheck, window.FOSS.dom.el("span", { text: "a-z" })]),
        window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [digitsCheck, window.FOSS.dom.el("span", { text: "0-9" })]),
        window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [symbolsCheck, window.FOSS.dom.el("span", { text: "#$%" })]),
        customAlphabetInput
      ]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [randBtn, copyBtn]),
      randRes
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, unitCard, randCard]));
  }

  function renderCalendarTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Create and parse iCalendar (.ics) files for events, schedules, and reminders."
    });

    var titleInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-calendar-title",
      value: "Team Sync",
      placeholder: "Event title",
      "aria-label": "Event title"
    });

    var startInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-calendar-start",
      value: "2026-10-30T10:00:00",
      placeholder: "Start time (YYYY-MM-DDTHH:MM:SS)",
      "aria-label": "Start time"
    });

    var icsEditor = window.FOSS.components.codeEditor({
      testid: "data-calendar-ics-output",
      title: "iCalendar (.ics) Payload",
      placeholder: "Generated or pasted ICS payload...",
      ariaLabel: "ICS payload editor"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-calendar-status",
      text: "Ready"
    });

    var genBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-calendar-generate",
      "aria-label": "Generate calendar event",
      title: "Generate calendar event",
      type: "button",
      onClick: function () {
        var t = titleInput.value.trim() || "Event";
        var s = startInput.value.trim() || "2026-10-30T10:00:00";
        window.FOSS.api("data_ics_generate", { title: t, start_time: s }).then(function (res) {
          icsEditor.setValue(res.ics);
          statusEl.textContent = "[OK] Generated .ics calendar event";
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "Generate .ICS" })
    ]);

    var parseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-calendar-parse",
      "aria-label": "Parse .ICS payload",
      title: "Parse .ICS payload",
      type: "button",
      onClick: function () {
        var content = icsEditor.getValue();
        window.FOSS.api("data_ics_parse", { content: content }).then(function (res) {
          var evs = res.events || [];
          statusEl.textContent = "[OK] Parsed " + evs.length + " calendar events";
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Parse .ICS" })
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [titleInput, startInput, genBtn, parseBtn])
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, card, icsEditor.el, statusEl]));
  }

  window.FOSS.router.register({
    id: "data",
    title: "Data Studio",
    navName: "Data",
    category: "Data",
    icon: "code",
    workbench: false,
    tabs: [
      { id: "structure", label: "Structure", render: renderStructureTab },
      { id: "tables", label: "Tables", render: renderTablesTab },
      { id: "units", label: "Units", render: renderUnitsTab },
      { id: "calendar", label: "Calendar", render: renderCalendarTab }
    ]
  });
})();
