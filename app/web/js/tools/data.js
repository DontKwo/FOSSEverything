// Data Studio workspace: formatting, conversions, queries, tables, units, calendar, writing, and cron.
window.FOSS = window.FOSS || {};

(function () {
  function renderEditorTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Format, pretty-print, minify, validate, and convert JSON, YAML, CSV, and XML."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "data-editor-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-editor-status",
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

    var editor = window.FOSS.components.codeEditor({
      testid: "data-editor-input",
      title: "Data Studio Input",
      placeholder: "paste or open json, yaml, xml, or csv data here",
      ariaLabel: "Data Studio input editor"
    });

    var langSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-editor-format-lang",
      "aria-label": "Data format language"
    }, [
      window.FOSS.dom.el("option", { value: "json", text: "json" }),
      window.FOSS.dom.el("option", { value: "yaml", text: "yaml" }),
      window.FOSS.dom.el("option", { value: "xml", text: "xml" }),
      window.FOSS.dom.el("option", { value: "csv", text: "csv" }),
      window.FOSS.dom.el("option", { value: "sql", text: "sql" }),
      window.FOSS.dom.el("option", { value: "javascript", text: "javascript" }),
      window.FOSS.dom.el("option", { value: "css", text: "css" })
    ]);

    var indentSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-editor-indent-select",
      "aria-label": "Indent spacing"
    }, [
      window.FOSS.dom.el("option", { value: "2", text: "2 spaces" }),
      window.FOSS.dom.el("option", { value: "4", text: "4 spaces" })
    ]);

    var convertTargetSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-editor-convert-target",
      "aria-label": "Convert to target format"
    }, [
      window.FOSS.dom.el("option", { value: "yaml", text: "yaml" }),
      window.FOSS.dom.el("option", { value: "json", text: "json" }),
      window.FOSS.dom.el("option", { value: "xml", text: "xml" }),
      window.FOSS.dom.el("option", { value: "csv", text: "csv" }),
      window.FOSS.dom.el("option", { value: "toml", text: "toml" }),
      window.FOSS.dom.el("option", { value: "ini", text: "ini" })
    ]);

    var formatBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-editor-format",
      "aria-label": "Format code",
      title: "Format code",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        if (!content.trim()) return;
        var lang = langSelect.value;
        var indent = parseInt(indentSelect.value, 10);
        window.FOSS.api("data_format_code", { content: content, language: lang, indent: indent }).then(function (res) {
          if (res && res.result !== undefined) {
            editor.setValue(res.result);
            clearError();
            statusBar.textContent = "[OK] Formatted as " + lang;
          }
        }).catch(function (err) {
          showError("Formatting error: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("edit", 16),
      window.FOSS.dom.el("span", { text: "Format" })
    ]);

    var minifyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-editor-minify",
      "aria-label": "Minify code",
      title: "Minify code",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        if (!content.trim()) return;
        var lang = langSelect.value;
        window.FOSS.api("data_minify_code", { content: content, language: lang }).then(function (res) {
          if (res && res.result !== undefined) {
            editor.setValue(res.result);
            clearError();
            statusBar.textContent = "[OK] Minified " + lang;
          }
        }).catch(function (err) {
          showError("Minify error: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("minus", 16),
      window.FOSS.dom.el("span", { text: "Minify" })
    ]);

    var validateBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-editor-validate",
      "aria-label": "Validate syntax",
      title: "Validate syntax",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        var lang = langSelect.value;
        window.FOSS.api("data_validate_syntax", { content: content, format: lang }).then(function (res) {
          if (res && res.valid) {
            clearError();
            statusBar.textContent = "[OK] Syntax valid (" + lang + ")";
          } else {
            showError("Syntax error (line " + (res.line || "?") + "): " + (res.message || "Invalid"));
          }
        }).catch(function (err) {
          showError("Validation error: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Validate" })
    ]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-editor-convert-btn",
      "aria-label": "Convert format",
      title: "Convert format",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        if (!content.trim()) return;
        var src = langSelect.value;
        var tgt = convertTargetSelect.value;
        var indent = parseInt(indentSelect.value, 10);
        window.FOSS.api("data_convert_format", { content: content, source_format: src, target_format: tgt, indent: indent }).then(function (res) {
          if (res && res.result !== undefined) {
            editor.setValue(res.result);
            langSelect.value = tgt;
            clearError();
            statusBar.textContent = "[OK] Converted from " + src + " to " + tgt;
          }
        }).catch(function (err) {
          showError("Conversion error: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Convert to" })
    ]);

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-editor-open",
      "aria-label": "Open file",
      title: "Open file",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var filePath = res.paths[0];
          window.FOSS.api("read_text_file", { file_path: filePath }).then(function (r) {
            editor.setValue(r.content || "");
            clearError();
            statusBar.textContent = "[OK] Loaded " + filePath;
          });
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Open" })
    ]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-editor-save",
      "aria-label": "Save file as",
      title: "Save file as",
      type: "button",
      onClick: function () {
        var content = editor.getValue();
        window.FOSS.api("select_save_path", { default_name: "data." + langSelect.value }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var p = res.paths[0];
          window.FOSS.api("write_text_file", { file_path: p, content: content }).then(function () {
            clearError();
            statusBar.textContent = "[OK] Saved to " + p;
          });
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Save As" })
    ]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Format:" }),
      langSelect,
      window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Indent:" }),
      indentSelect,
      formatBtn,
      minifyBtn,
      validateBtn,
      convertBtn,
      convertTargetSelect,
      openBtn,
      saveBtn
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [
      desc,
      toolbar,
      errorBanner,
      editor.el,
      statusBar
    ]));
  }

  function renderQueryTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "JSONPath query evaluator, schema inference, schema diffing, and schema validation preview."
    });

    var dataEditor = window.FOSS.components.codeEditor({
      testid: "data-query-data-input",
      title: "JSON / YAML Target Data",
      placeholder: '{"store": {"book": [{"title": "FOSS Tools", "price": 10}]}}',
      ariaLabel: "JSON or YAML target data"
    });

    var queryInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "data-query-path-input",
      placeholder: "e.g. $.tools[*], store.book[0].title, $..version, [(@.local_first == true)]",
      "aria-label": "JSONPath query expression"
    });

    var resultEditor = window.FOSS.components.codeEditor({
      testid: "data-query-output",
      title: "Query / Schema Output",
      placeholder: "Evaluation results or inferred schema appear here...",
      ariaLabel: "Query evaluation output",
      readOnly: true
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-query-status",
      text: "Ready"
    });

    var evalBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-query-evaluate",
      "aria-label": "Evaluate query",
      title: "Evaluate query",
      type: "button",
      onClick: function () {
        var content = dataEditor.getValue();
        var path = queryInput.value.trim() || "$";
        window.FOSS.api("data_query_jsonpath", { content: content, path: path }).then(function (res) {
          resultEditor.setValue(JSON.stringify(res.matches, null, 2));
          statusEl.textContent = "[OK] Query evaluated: " + (Array.isArray(res.matches) ? res.matches.length + " matches" : "1 match");
        }).catch(function (err) {
          statusEl.textContent = "Query error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Evaluate Query" })
    ]);

    var inferSchemaBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-query-infer-schema",
      "aria-label": "Infer JSON Schema (Draft-07)",
      title: "Infer JSON Schema (Draft-07)",
      type: "button",
      onClick: function () {
        var content = dataEditor.getValue();
        window.FOSS.api("data_infer_schema", { content: content }).then(function (res) {
          resultEditor.setValue(JSON.stringify(res.schema, null, 2));
          statusEl.textContent = "[OK] Schema inferred (Draft-07)";
        }).catch(function (err) {
          statusEl.textContent = "Inference error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("code", 16),
      window.FOSS.dom.el("span", { text: "Infer Schema" })
    ]);

    var validateSchemaBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-query-validate-schema",
      "aria-label": "Validate against schema",
      title: "Validate against schema",
      type: "button",
      onClick: function () {
        var dataContent = dataEditor.getValue();
        var schemaContent = resultEditor.getValue();
        window.FOSS.api("data_validate_against_schema", { content: dataContent, schema: schemaContent }).then(function (res) {
          if (res.valid) {
            statusEl.textContent = "[OK] Data strictly valid against schema";
          } else {
            statusEl.textContent = "[FAIL] Schema validation errors: " + (res.errors || []).join("; ");
          }
        }).catch(function (err) {
          statusEl.textContent = "Schema error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Validate Schema" })
    ]);

    var diffSchemaBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-query-diff-schema",
      "aria-label": "Diff two schemas",
      title: "Diff two schemas",
      type: "button",
      onClick: function () {
        var base = dataEditor.getValue();
        var candidate = resultEditor.getValue();
        window.FOSS.api("data_diff_schema", { base_schema: base, candidate_schema: candidate }).then(function (res) {
          var report = "Added: " + res.added.length + ", Removed: " + res.removed.length + ", Changed: " + res.changed.length;
          statusEl.textContent = "[OK] Diff: " + report;
        }).catch(function (err) {
          statusEl.textContent = "Diff error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Diff Schema" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [evalBtn, inferSchemaBtn, validateSchemaBtn, diffSchemaBtn]);

    var queryCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "JSONPath Query" }),
      queryInput,
      actionsRow
    ]);

    var split = window.FOSS.dom.el("div", {
      className: "split even"
    }, [dataEditor.el, resultEditor.el]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, queryCard, split, statusEl]));
  }

  function renderTablesTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Parse, clean, normalize, and convert tabular data between CSV and Markdown table formats."
    });

    var tableEditor = window.FOSS.components.codeEditor({
      testid: "data-tables-input",
      title: "Markdown Table / CSV",
      placeholder: "| Item | Price | Qty |\n| :--- | :--- | :--- |\n| Apple | $1.20 | 10 |",
      ariaLabel: "Table editor content"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-tables-status",
      text: "Ready"
    });

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
      "aria-label": "CSV to Markdown table",
      title: "CSV to Markdown table",
      type: "button",
      onClick: function () {
        var content = tableEditor.getValue();
        window.FOSS.api("data_csv_to_table", { content: content }).then(function (res) {
          tableEditor.setValue(res.result);
          statusEl.textContent = "[OK] Converted CSV to Markdown table";
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "CSV to Markdown" })
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
        });
      }
    }, [
      window.FOSS.icons.el("table", 16),
      window.FOSS.dom.el("span", { text: "Parse Table" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [cleanBtn, normalizeBtn, csvToMdBtn, parseBtn]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, actionsRow, tableEditor.el, statusEl]));
  }

  function renderUnitsTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Convert units across length, weight, temperature, and data, or generate pseudorandom values."
    });

    var valInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm",
      "data-testid": "data-units-val",
      value: "100",
      "aria-label": "Unit numerical value"
    });

    var srcUnitInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-units-from",
      value: "m",
      "aria-label": "Source measurement unit"
    });

    var tgtUnitInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-units-to",
      value: "ft",
      "aria-label": "Target measurement unit"
    });

    var unitRes = window.FOSS.dom.el("div", {
      className: "font-mono text-sm",
      "data-testid": "data-units-output",
      text: "Result: 328.084 ft"
    });

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-units-convert",
      "aria-label": "Convert units",
      title: "Convert units",
      type: "button",
      onClick: function () {
        var v = parseFloat(valInput.value);
        var u1 = srcUnitInput.value.trim();
        var u2 = tgtUnitInput.value.trim();
        window.FOSS.api("data_convert_units", { value: v, source_unit: u1, target_unit: u2 }).then(function (res) {
          unitRes.textContent = "Result: " + res.result + " " + u2;
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Convert Unit" })
    ]);

    var unitCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Physical Unit Converter" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        valInput, srcUnitInput, window.FOSS.dom.el("span", { text: "to" }), tgtUnitInput, convertBtn
      ]),
      unitRes
    ]);

    var randSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "data-units-random-type",
      "aria-label": "Random generator kind"
    }, [
      window.FOSS.dom.el("option", { value: "uuid", text: "UUID" }),
      window.FOSS.dom.el("option", { value: "password", text: "Password" }),
      window.FOSS.dom.el("option", { value: "number", text: "Number" }),
      window.FOSS.dom.el("option", { value: "hex", text: "Hex Token" }),
      window.FOSS.dom.el("option", { value: "string", text: "Alphanumeric" })
    ]);

    var randRes = window.FOSS.dom.el("div", {
      className: "font-mono text-sm",
      "data-testid": "data-units-random-output",
      text: "-"
    });

    var randBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-units-random-generate",
      "aria-label": "Generate random token",
      title: "Generate random token",
      type: "button",
      onClick: function () {
        var cat = randSelect.value;
        window.FOSS.api("data_random_value", { category: cat, length: 16 }).then(function (res) {
          randRes.textContent = String(res.value);
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "Generate Random" })
    ]);

    var randCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Random Generator" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [randSelect, randBtn]),
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

  function renderWritingTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Grammar inspection, citation generation, and unified document diffing."
    });

    var textEditor = window.FOSS.components.codeEditor({
      testid: "data-writing-input",
      title: "Writing Document",
      placeholder: "Type or paste text for offline grammar and style analysis...",
      ariaLabel: "Writing document editor"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "data-writing-status",
      text: "Ready"
    });

    var grammarBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-writing-grammar-check",
      "aria-label": "Check grammar",
      title: "Check grammar",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_grammar_check", { text: txt, advanced: false }).then(function (res) {
          var m = res.matches || [];
          statusEl.textContent = "[OK] Grammar check: " + m.length + " issues flagged";
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Grammar Check" })
    ]);

    var advancedGrammarBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-writing-grammar-advanced",
      "aria-label": "LanguageTool advanced check",
      title: "LanguageTool advanced check",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_grammar_check", { text: txt, advanced: true }).then(function (res) {
          statusEl.textContent = "[OK] Advanced LanguageTool analysis complete (LT available: " + res.lt_available + ")";
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Advanced Grammar" })
    ]);

    var citationBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-writing-citation-generate",
      "aria-label": "Generate citation",
      title: "Generate citation",
      type: "button",
      onClick: function () {
        var meta = { author: "Smith, J.", title: "Local First Software", year: "2026", publisher: "FOSS Press" };
        window.FOSS.api("data_generate_citation", { metadata: meta, style: "apa" }).then(function (res) {
          textEditor.setValue(res.citation);
          statusEl.textContent = "[OK] Generated APA citation";
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Generate Citation" })
    ]);

    var diffBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "data-writing-diff-btn",
      "aria-label": "Diff document",
      title: "Diff document",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_diff_documents", { doc1: txt, doc2: txt + "\nAdded Line" }).then(function (res) {
          statusEl.textContent = "[OK] Unified document diff calculated";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Diff Documents" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [grammarBtn, advancedGrammarBtn, citationBtn, diffBtn]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, actionsRow, textEditor.el, statusEl]));
  }

  function renderCronTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Describe standard 5-field cron schedules and preview upcoming execution runs."
    });

    var cronInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "data-cron-input",
      value: "*/15 * * * *",
      placeholder: "e.g. 0 9 * * 1-5",
      "aria-label": "Cron expression input"
    });

    var cronDesc = window.FOSS.dom.el("div", {
      className: "font-mono text-sm",
      "data-testid": "data-cron-description",
      text: "Every 15 minutes"
    });

    var upcomingList = window.FOSS.dom.el("div", {
      className: "stack",
      gap: "xs",
      "data-testid": "data-cron-upcoming"
    });

    var describeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-cron-describe-btn",
      "aria-label": "Describe cron expression",
      title: "Describe cron expression",
      type: "button",
      onClick: function () {
        var expr = cronInput.value.trim() || "* * * * *";
        window.FOSS.api("data_cron_describe", { expression: expr, count: 5 }).then(function (res) {
          cronDesc.textContent = res.description;
          upcomingList.innerHTML = "";
          (res.upcoming_runs || []).forEach(function (r) {
            upcomingList.appendChild(window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Run: " + r }));
          });
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Describe Cron" })
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Cron Expression Generator" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [cronInput, describeBtn]),
      cronDesc,
      upcomingList
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, card]));
  }

  function renderPreviewTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Offline Markdown live preview renderer for data notes and schemas."
    });

    var editor = window.FOSS.components.codeEditor({
      testid: "data-preview-input",
      title: "Markdown Document",
      placeholder: "# Header\n\nPreview text here.",
      ariaLabel: "Markdown preview editor input"
    });

    var previewBox = window.FOSS.dom.el("div", {
      className: "card grow",
      "data-testid": "data-preview-rendered",
      style: "min-height: 18rem; padding: var(--space-4);"
    });

    var renderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "data-preview-render",
      "aria-label": "Render preview",
      title: "Render preview",
      type: "button",
      onClick: function () {
        var txt = editor.getValue();
        window.FOSS.api("data_render_preview", { markdown: txt }).then(function (res) {
          previewBox.innerHTML = res.html || "";
        });
      }
    }, [
      window.FOSS.icons.el("eye", 16),
      window.FOSS.dom.el("span", { text: "Render Preview" })
    ]);

    var split = window.FOSS.dom.el("div", {
      className: "split even"
    }, [editor.el, previewBox]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, renderBtn, split]));
  }

  window.FOSS.router.register({
    id: "data",
    title: "Data Studio",
    navName: "Data",
    category: "Data",
    icon: "code",
    workbench: false,
    tabs: [
      { id: "editor", label: "Editor", render: renderEditorTab },
      { id: "query", label: "Query", render: renderQueryTab },
      { id: "tables", label: "Tables", render: renderTablesTab },
      { id: "units", label: "Units", render: renderUnitsTab },
      { id: "calendar", label: "Calendar", render: renderCalendarTab },
      { id: "writing", label: "Writing", render: renderWritingTab },
      { id: "cron", label: "Cron", render: renderCronTab },
      { id: "preview", label: "Preview", render: renderPreviewTab }
    ]
  });
})();
