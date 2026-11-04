// Unit Converter workspace: dimensional analysis, 30 categories, compound expressions.
window.FOSS = window.FOSS || {};

(function () {
  var cachedCatalog = null;
  var expressionHistory = [];

  function fetchCatalog(cb) {
    if (cachedCatalog) {
      cb(cachedCatalog);
      return;
    }
    window.FOSS.api("units_catalog", {}).then(function (res) {
      if (res && res.categories) {
        cachedCatalog = res;
        cb(res);
      }
    });
  }

  // TAB 1: Standard & All Units
  function renderStandard(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "unit_converter-page");

    var currentCategory = null;
    var currentCompatibleList = [];

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "unit_converter-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "unit_converter-error-banner"
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

    // Left Column Controls
    var categorySelect = window.FOSS.dom.el("select", {
      className: "select select-sm w-full font-semibold text-xs",
      "data-testid": "unit_converter-category-select",
      "aria-label": "Measurement Category",
      title: "Measurement Category",
      onChange: function () {
        onCategoryChanged();
      }
    });

    var valueInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input font-mono text-sm",
      "data-testid": "unit_converter-input-value",
      value: "1",
      step: "any",
      "aria-label": "Input Value",
      title: "Input Value",
      onInput: function () {
        triggerConvert();
      }
    });

    var prefixSelect = window.FOSS.dom.el("select", {
      className: "select select-sm font-mono text-xs",
      "data-testid": "unit_converter-prefix-select",
      "aria-label": "Unit Prefix Multiplier",
      title: "Unit Prefix Multiplier",
      onChange: function () {
        triggerConvert();
      }
    }, [
      window.FOSS.dom.el("option", { value: "1", text: "Prefix: None (1x)" }),
      window.FOSS.dom.el("option", { value: "1e3", text: "kilo (k) - 10^3" }),
      window.FOSS.dom.el("option", { value: "1e6", text: "mega (M) - 10^6" }),
      window.FOSS.dom.el("option", { value: "1e9", text: "giga (G) - 10^9" }),
      window.FOSS.dom.el("option", { value: "1e-3", text: "milli (m) - 10^-3" }),
      window.FOSS.dom.el("option", { value: "1e-6", text: "micro (\u03bc) - 10^-6" }),
      window.FOSS.dom.el("option", { value: "1e-9", text: "nano (n) - 10^-9" }),
      window.FOSS.dom.el("option", { value: "1024", text: "kibi (Ki) - 1,024" }),
      window.FOSS.dom.el("option", { value: "1048576", text: "mebi (Mi) - 1,048,576" })
    ]);

    var notationSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs",
      "data-testid": "unit_converter-notation-select",
      "aria-label": "Output Notation",
      title: "Output Notation",
      onChange: function () {
        triggerConvert();
      }
    }, [
      window.FOSS.dom.el("option", { value: "smart", text: "Smart Formatting" }),
      window.FOSS.dom.el("option", { value: "fixed", text: "Fixed Decimal" }),
      window.FOSS.dom.el("option", { value: "scientific", text: "Scientific Notation" }),
      window.FOSS.dom.el("option", { value: "engineering", text: "Engineering Notation" })
    ]);

    var precisionSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs",
      "data-testid": "unit_converter-precision-select",
      "aria-label": "Precision Significant Figures",
      title: "Precision Significant Figures",
      onChange: function () {
        triggerConvert();
      }
    }, [
      window.FOSS.dom.el("option", { value: "4", text: "4 digits" }),
      window.FOSS.dom.el("option", { value: "6", text: "6 digits" }),
      window.FOSS.dom.el("option", { value: "7", text: "7 digits (Standard)" }),
      window.FOSS.dom.el("option", { value: "9", text: "9 digits" }),
      window.FOSS.dom.el("option", { value: "12", text: "12 digits (High Precision)" })
    ]);
    precisionSelect.value = "7";

    var fromUnitSelect = window.FOSS.dom.el("select", {
      className: "select select-sm w-full font-mono text-xs",
      "data-testid": "unit_converter-from-unit-select",
      "aria-label": "Source Unit",
      title: "Source Unit",
      onChange: function () {
        triggerConvert();
      }
    });

    var toUnitSelect = window.FOSS.dom.el("select", {
      className: "select select-sm w-full font-mono text-xs",
      "data-testid": "unit_converter-to-unit-select",
      "aria-label": "Target Unit",
      title: "Target Unit",
      onChange: function () {
        triggerConvert();
      }
    });

    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-secondary btn-sm",
      style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
      "data-testid": "unit_converter-swap-btn",
      "aria-label": "Swap Source and Target Units",
      title: "Swap Source and Target Units",
      type: "button",
      onClick: function () {
        var temp = fromUnitSelect.value;
        fromUnitSelect.value = toUnitSelect.value;
        toUnitSelect.value = temp;
        triggerConvert();
      }
    }, [window.FOSS.icons.el("refresh", 14)]);

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "unit_converter-convert-btn",
      type: "button",
      onClick: function () {
        triggerConvert();
      }
    }, [window.FOSS.icons.el("check", 14), window.FOSS.dom.el("span", { text: "Convert Value" })]);

    // Top Section: Inputs and Primary Action
    var topRow = window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
      window.FOSS.components.field("Physical Dimension", categorySelect),
      window.FOSS.components.field("Quantity Value", valueInput),
      window.FOSS.components.field("From Unit", fromUnitSelect),
      swapBtn,
      window.FOSS.components.field("To Unit", toUnitSelect),
      convertBtn
    ]);

    var resultBanner = window.FOSS.dom.el("div", {
      className: "banner info",
      "data-testid": "unit_converter-result-banner",
      style: "display: none;"
    }, [
      window.FOSS.dom.el("span", { className: "font-mono font-bold", text: "" })
    ]);

    var primaryCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2 mb-3",
      "data-testid": "unit_converter-primary-card"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Standard Unit Conversion" }),
      topRow,
      resultBanner
    ]);

    // Bottom Section: Dimension and Notation Options
    var optionsRow = window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
      window.FOSS.components.field("Prefix Multiplier", prefixSelect),
      window.FOSS.components.field("Output Notation", notationSelect),
      window.FOSS.components.field("Significant Digits", precisionSelect)
    ]);

    var optionsCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2",
      "data-testid": "unit_converter-options-card"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-xs text-muted", text: "Measurement Unit Options" }),
      optionsRow
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "unit_converter-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [primaryCard, optionsCard]);

    // Right Column: Hero Result + Full Compatible Units Table
    var heroOutput = window.FOSS.dom.el("div", {
      className: "font-mono font-bold text-lg",
      "data-testid": "unit_converter-hero-result",
      "data-truncate-ok": "true",
      title: "Converted Value",
      style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      text: "-"
    });

    var heroFormula = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "unit_converter-hero-formula",
      "data-truncate-ok": "true",
      title: "Conversion Formula",
      style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      text: ""
    });

    var heroDim = window.FOSS.dom.el("span", {
      className: "badge badge-neutral text-xs font-mono",
      "data-testid": "unit_converter-hero-dim",
      "data-truncate-ok": "true",
      title: "Dimensionality",
      style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
      text: "Dimension: -"
    });

    var heroSi = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "unit_converter-hero-si",
      "data-truncate-ok": "true",
      title: "SI Base Equivalent",
      style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      text: "SI Base: -"
    });

    var copyValBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "unit_converter-copy-val-btn",
      type: "button",
      onClick: function () {
        if (navigator.clipboard && currentHeroResult !== null) {
          navigator.clipboard.writeText(String(currentHeroResult));
          statusBar.textContent = "Copied value to clipboard.";
        }
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Number" })]);

    var copyEqBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "unit_converter-copy-eq-btn",
      type: "button",
      onClick: function () {
        if (navigator.clipboard && heroFormula.textContent) {
          navigator.clipboard.writeText(heroFormula.textContent);
          statusBar.textContent = "Copied equation to clipboard.";
        }
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Equation" })]);

    var currentHeroResult = null;

    var heroCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2",
      style: "box-sizing: border-box; min-width: 0;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
        heroDim,
        window.FOSS.dom.el("div", { className: "row gap-2" }, [copyValBtn, copyEqBtn])
      ]),
      heroOutput,
      heroFormula,
      heroSi
    ]);

    // Table Controls
    var tableFilterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm text-xs font-mono grow",
      "data-testid": "unit_converter-table-filter",
      placeholder: "Filter compatible units...",
      "aria-label": "Filter compatible units",
      title: "Filter compatible units",
      onInput: function () {
        renderCompatibleTable();
      }
    });

    var includeAllCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "unit_converter-include-all",
      "aria-label": "Include All Units",
      title: "Include All Units",
      onChange: function () {
        loadCompatibleTable();
      }
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "table-wrap grow flex-col gap-2",
      "data-testid": "unit_converter-table",
      style: "min-width: 0; width: 100%; box-sizing: border-box;"
    });

    function onCategoryChanged() {
      if (!cachedCatalog) return;
      var catId = categorySelect.value;
      currentCategory = cachedCatalog.categories.find(function (c) { return c.id === catId; }) || cachedCatalog.categories[0];
      fromUnitSelect.innerHTML = "";
      toUnitSelect.innerHTML = "";

      if (currentCategory && currentCategory.units) {
        currentCategory.units.forEach(function (u, idx) {
          var opt1 = window.FOSS.dom.el("option", { value: u.id, text: u.label + " (" + u.symbol + ")" });
          var opt2 = window.FOSS.dom.el("option", { value: u.id, text: u.label + " (" + u.symbol + ")" });
          fromUnitSelect.appendChild(opt1);
          toUnitSelect.appendChild(opt2);
        });
        if (currentCategory.units.length > 1) {
          toUnitSelect.selectedIndex = 1;
        }
      }
      triggerConvert();
    }

    function triggerConvert() {
      clearError();
      var rawVal = parseFloat(valueInput.value);
      if (isNaN(rawVal)) rawVal = 0.0;
      var mult = parseFloat(prefixSelect.value) || 1.0;
      var val = rawVal * mult;
      var u1 = fromUnitSelect.value;
      var u2 = toUnitSelect.value;
      if (!u1 || !u2) return;

      var mode = notationSelect.value;
      var prec = parseInt(precisionSelect.value, 10) || 7;

      window.FOSS.api("units_convert", {
        value: val,
        from_unit: u1,
        to_unit: u2,
        format_mode: mode,
        sig_figs: prec
      }).then(function (res) {
        if (!res) return;
        if (res.ok === false) {
          showError(res.error || "Conversion failed");
          return;
        }
        currentHeroResult = res.result;
        heroOutput.textContent = res.formatted + " " + u2;
        heroFormula.textContent = res.formula_str || "";
        heroDim.textContent = "Dimension: " + (res.dimensionality || "[]");
        heroDim.title = "Dimension: " + (res.dimensionality || "[]");
        heroSi.textContent = "SI Base Unit: " + (res.si_base || "standard");
        statusBar.textContent = "Converted " + u1 + " to " + u2;
        if (resultBanner) {
          var rSpan = resultBanner.querySelector("span");
          if (rSpan) rSpan.textContent = res.formatted + " " + u2;
          resultBanner.style.removeProperty("display");
        }
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });

      loadCompatibleTable();
    }

    function loadCompatibleTable() {
      var rawVal = parseFloat(valueInput.value);
      if (isNaN(rawVal)) rawVal = 0.0;
      var mult = parseFloat(prefixSelect.value) || 1.0;
      var val = rawVal * mult;
      var u1 = fromUnitSelect.value;
      if (!u1) return;
      var catId = categorySelect.value;
      var incAll = includeAllCheck.checked;
      var mode = notationSelect.value;
      var prec = parseInt(precisionSelect.value, 10) || 7;

      window.FOSS.api("units_compatible_table", {
        value: val,
        from_unit: u1,
        category_id: catId,
        include_all: incAll,
        format_mode: mode,
        sig_figs: prec
      }).then(function (res) {
        if (!res || !res.items) return;
        currentCompatibleList = res.items;
        renderCompatibleTable();
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    function renderCompatibleTable() {
      tableHost.innerHTML = "";
      var filterTxt = tableFilterInput.value.toLowerCase().trim();
      var filtered = currentCompatibleList.filter(function (it) {
        if (!filterTxt) return true;
        return (it.label && it.label.toLowerCase().indexOf(filterTxt) >= 0) ||
               (it.symbol && it.symbol.toLowerCase().indexOf(filterTxt) >= 0) ||
               (it.id && it.id.toLowerCase().indexOf(filterTxt) >= 0);
      });

      if (filtered.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-6 text-center font-mono",
          text: "No compatible units match filter."
        }));
        return;
      }

      var rows = filtered.map(function (it) {
        var copyBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Copy " + it.label + " Value",
          title: "Copy " + it.label + " Value",
          type: "button",
          onClick: function () {
            if (navigator.clipboard) {
              navigator.clipboard.writeText(String(it.result));
              statusBar.textContent = "Copied " + it.formatted + " " + it.symbol + " to clipboard.";
            }
          }
        }, [window.FOSS.icons.el("copy", 14)]);

        return window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {
            className: "font-semibold text-sm",
            style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.label,
            "data-truncate-ok": "true",
            title: it.label
          }),
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono text-muted",
            style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.symbol,
            "data-truncate-ok": "true",
            title: it.symbol
          }),
          window.FOSS.dom.el("td", {
            className: "font-mono text-sm",
            style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: it.formatted,
            "data-truncate-ok": "true",
            title: it.formatted + " " + it.symbol
          }),
          window.FOSS.dom.el("td", {
            className: "text-right",
            style: "width: 2.5rem; padding: 0.25rem 0;"
          }, [copyBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", {
        className: "table w-full",
        style: "table-layout: fixed; width: 100%; min-width: 0;"
      }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Unit", "data-truncate-ok": "true", title: "Unit" }),
            window.FOSS.dom.el("th", { style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Symbol", "data-truncate-ok": "true", title: "Symbol" }),
            window.FOSS.dom.el("th", { style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Magnitude", "data-truncate-ok": "true", title: "Magnitude" }),
            window.FOSS.dom.el("th", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;", text: "", "data-truncate-ok": "true", title: "Action" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);

      tableHost.appendChild(table);
    }

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      heroCard,
      window.FOSS.dom.el("div", { className: "row gap-3 items-center justify-between flex-wrap" }, [
        tableFilterInput,
        window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center" }, [
          includeAllCheck,
          window.FOSS.dom.el("span", { text: "All Units" })
        ])
      ]),
      tableHost
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "unit_converter-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable unit_converter-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(split);

    fetchCatalog(function (catData) {
      categorySelect.innerHTML = "";
      catData.categories.forEach(function (c) {
        categorySelect.appendChild(window.FOSS.dom.el("option", {
          value: c.id,
          text: c.name + " (" + c.unit_count + " units)"
        }));
      });
      onCategoryChanged();
    });
  }

  // TAB 2: Compound Expression Calculator
  function renderExpression(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "unit_converter-page");

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "unit_converter-expr-status",
      text: "Ready for compound physical quantities"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "unit_converter-expr-error"
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

    var exprInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono text-sm",
      "data-testid": "unit_converter-expr-input",
      placeholder: "e.g. 350 BTU / (hr * ft**2 * delta_degF)",
      value: "350 BTU / (hr * ft**2 * delta_degF)",
      "aria-label": "Quantity Expression",
      title: "Quantity Expression"
    });

    var targetUnitInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono text-sm",
      "data-testid": "unit_converter-expr-target",
      placeholder: "Target unit (e.g. W / (m**2 * K))",
      value: "W / (m**2 * K)",
      "aria-label": "Target Unit (Optional)",
      title: "Target Unit (Optional)"
    });

    var evaluateBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "unit_converter-expr-btn",
      type: "button",
      onClick: function () {
        evaluateExpression();
      }
    }, [window.FOSS.icons.el("play", 14), window.FOSS.dom.el("span", { text: "Evaluate Expression" })]);

    var examples = [
      { label: "Ideal Gas Constant", expr: "8.314 J / (mol * K)", target: "cal / (mol * K)" },
      { label: "Heat Transfer Coeff", expr: "350 BTU / (hr * ft**2 * delta_degF)", target: "W / (m**2 * K)" },
      { label: "Mechanical Power", expr: "250 hp", target: "kW" },
      { label: "Fluid Head Pressure", expr: "1000 kg/m**3 * 9.80665 m/s**2 * 10 m", target: "bar" },
      { label: "Network Bandwidth", expr: "1.5 Gbps", target: "MB/s" },
      { label: "Kinetic Energy", expr: "0.5 * 1200 kg * (60 mph)**2", target: "kJ" }
    ];

    var examplesContainer = window.FOSS.dom.el("div", {
      className: "flex-col gap-1 pt-xs"
    }, examples.map(function (ex) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm unit_converter-preset-btn",
        "data-wrap-ok": "true",
        type: "button",
        "aria-label": "Example " + ex.label,
        title: ex.expr + " -> " + ex.target,
        onClick: function () {
          exprInput.value = ex.expr;
          targetUnitInput.value = ex.target;
          evaluateExpression();
        }
      }, [
        window.FOSS.icons.el("file-text", 12),
        window.FOSS.dom.el("span", { className: "text-xs font-semibold", text: ex.label + ": " }),
        window.FOSS.dom.el("span", { className: "text-xs font-mono text-muted", text: ex.expr })
      ]);
    }));

    var leftCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Expression Input" }),
      window.FOSS.components.field("Quantity Formula", exprInput),
      window.FOSS.components.field("Target Unit (Optional)", targetUnitInput),
      evaluateBtn,
      window.FOSS.dom.el("div", { className: "text-xs font-semibold text-muted pt-sm", text: "Engineering & Physics Quick Presets" }),
      examplesContainer
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "unit_converter-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [leftCard]);

    // Right Column: Result + History
    var resultOutput = window.FOSS.dom.el("div", {
      className: "font-mono font-bold text-lg",
      "data-testid": "unit_converter-expr-result",
      "data-truncate-ok": "true",
      title: "Expression Result",
      style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      text: "-"
    });

    var resultDim = window.FOSS.dom.el("span", {
      className: "badge badge-neutral text-xs font-mono",
      "data-testid": "unit_converter-expr-dim",
      "data-truncate-ok": "true",
      title: "Dimensionality",
      style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
      text: "Dimension: -"
    });

    var resultSi = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      "data-testid": "unit_converter-expr-si",
      "data-truncate-ok": "true",
      title: "SI Base Units",
      style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
      text: "SI Base: -"
    });

    var historyHost = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 grow overflow-y-auto",
      "data-testid": "unit_converter-history",
      style: "min-height: 0; min-width: 0;"
    });

    function renderHistory() {
      historyHost.innerHTML = "";
      if (expressionHistory.length === 0) {
        historyHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-xs p-4 text-center font-mono",
          text: "No previous expressions evaluated in this session."
        }));
        return;
      }
      expressionHistory.forEach(function (h) {
        historyHost.appendChild(window.FOSS.dom.el("div", {
          className: "p-2 rounded bg-neutral flex-col gap-1 cursor-pointer",
          onClick: function () {
            exprInput.value = h.expr;
            targetUnitInput.value = h.target;
            evaluateExpression();
          }
        }, [
          window.FOSS.dom.el("div", { className: "text-xs font-mono font-semibold", text: h.expr + " -> " + h.formatted }),
          window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono", text: "Dim: " + h.dim })
        ]));
      });
    }

    function evaluateExpression() {
      clearError();
      var expr = exprInput.value.trim();
      var target = targetUnitInput.value.trim();
      if (!expr) return;

      statusBar.textContent = "Evaluating expression...";
      window.FOSS.api("units_expression", {
        expression: expr,
        target_unit: target
      }).then(function (res) {
        if (!res) return;
        if (res.ok === false) {
          showError(res.error || "Expression evaluation failed");
          statusBar.textContent = "Expression error";
          return;
        }
        resultOutput.textContent = res.formatted;
        resultDim.textContent = "Dimension: " + (res.dimensionality || "[]");
        resultDim.title = "Dimension: " + (res.dimensionality || "[]");
        resultSi.textContent = "SI Base: " + (res.si_base || "standard");
        statusBar.textContent = "Evaluated successfully";

        expressionHistory.unshift({
          expr: expr,
          target: target,
          formatted: res.formatted,
          dim: res.dimensionality || "[]"
        });
        if (expressionHistory.length > 15) expressionHistory.pop();
        renderHistory();
      }).catch(function (err) {
        showError((err && err.message) || String(err));
        statusBar.textContent = "Expression error";
      });
    }

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "card card-compact flex-col gap-2" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
          window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Evaluated Result" }),
          resultDim
        ]),
        resultOutput,
        resultSi
      ]),
      window.FOSS.dom.el("div", { className: "font-semibold text-sm pt-sm", text: "Recent Expression History" }),
      historyHost
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "unit_converter-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable unit_converter-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(split);

    renderHistory();
    evaluateExpression();
  }

  window.FOSS.router.register({
    id: "unit_converter",
    title: "Unit Converter",
    navName: "Unit Converter",
    category: "Data",
    icon: "ruler",
    workbench: true,
    tabs: [
      { id: "standard", label: "Standard & All Units", render: renderStandard },
      { id: "expression", label: "Compound Expressions", render: renderExpression }
    ]
  });
})();

