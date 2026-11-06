// Text manipulation workbench: transforms, diff, word counter, and writing tools.
window.FOSS = window.FOSS || {};

(function () {
  var CASE_MODES = [
    { id: "upper", mode: "uppercase", label: "UPPERCASE" },
    { id: "lower", mode: "lowercase", label: "lowercase" },
    { id: "title", mode: "titlecase", label: "Title Case" },
    { id: "sentence", mode: "sentencecase", label: "Sentence case" },
    { id: "camel", mode: "camelcase", label: "camelCase" },
    { id: "snake", mode: "snakecase", label: "snake_case" },
    { id: "kebab", mode: "kebabcase", label: "kebab-case" },
    { id: "constant", mode: "constantcase", label: "CONSTANT_CASE" },
    { id: "pascal", mode: "pascalcase", label: "PascalCase" }
  ];

  function toolDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("text_tools", key, fallback);
  }

  function showToast(msg, kind) {
    if (window.FOSS && window.FOSS.toast && typeof window.FOSS.toast.show === "function") {
      window.FOSS.toast.show(msg, kind);
    }
  }

  function renderTransformsTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "text_tools-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "text_tools-error"
    }, [
      window.FOSS.icons.el("alert", 16),
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

    var inputEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-input",
      title: "Input Text",
      placeholder: "Type or paste text here to transform...",
      fillHeight: true
    });

    var outputEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-output",
      title: "Output Text",
      placeholder: "Transformed text appears here...",
      readOnly: false,
      fillHeight: true
    });

    function setOutput(txt, statusMsg) {
      clearError();
      outputEditor.setValue(txt);
      statusBar.textContent = statusMsg || "[OK] Applied transform";
    }

    // Sidebar: transparent container with individual cards
    var sidebar = window.FOSS.dom.el("div", { className: "text-tools-sidebar-pane" });

    // Helper for card titles
    function makeCardTitle(title) {
      return window.FOSS.dom.el("div", {
        className: "text-xs font-semibold uppercase tracking-wider text-muted",
        text: title
      });
    }

    // Category 1: Case Conversions
    var caseModes = CASE_MODES;

    function applyCase(mode, label) {
      var val = inputEditor.getValue();
      clearError();
      window.FOSS.api("text_tools_case", { text: val, mode: mode }).then(function (res) {
        setOutput(res.result || "", "[OK] Converted to " + label);
      }).catch(function (err) {
        showError(err.message || String(err));
      });
    }

    var caseSelect = window.FOSS.dom.el("select", {
      className: "input input-sm flex-1",
      "data-testid": "text_tools-case-select",
      "aria-label": "Default case mode"
    }, caseModes.map(function (m) {
      return window.FOSS.dom.el("option", { value: m.mode, text: m.label });
    }));
    caseSelect.value = String(toolDefault("case_mode", "titlecase"));

    var caseApplyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-case-apply",
      "aria-label": "Apply selected case mode",
      title: "Apply selected case mode",
      onClick: function () {
        var chosen = caseModes.find(function (m) { return m.mode === caseSelect.value; });
        applyCase(caseSelect.value, chosen ? chosen.label : caseSelect.value);
      }
    }, [window.FOSS.dom.el("span", { text: "Apply" })]);

    var caseQuickRow = window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [caseSelect, caseApplyBtn]);

    var caseBtns = window.FOSS.dom.el("div", {
      className: "row flex-wrap gap-1"
    });

    caseModes.forEach(function (m) {
      var isPascal = m.id === "pascal";
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": isPascal ? "text_tools-pascal-btn" : ("text_tools-case-" + m.id),
        "data-alt-testid": "text_tools-case-" + m.id,
        "aria-label": "Convert to " + m.label,
        title: m.label,
        onClick: function () { applyCase(m.id, m.label); }
      }, [window.FOSS.dom.el("span", { text: m.label })]);
      caseBtns.appendChild(btn);
    });

    var caseCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1"
    }, [makeCardTitle("Case Conversions"), caseQuickRow, caseBtns]);

    sidebar.appendChild(caseCard);

    // Category 2: Lines and Sorting
    var lineModes = [
      { id: "sort_asc", label: "Sort A-Z" },
      { id: "sort_desc", label: "Sort Z-A" },
      { id: "reverse", label: "Reverse Lines" },
      { id: "dedupe", label: "Deduplicate" },
      { id: "number", label: "Number Lines" },
      { id: "remove_blank", label: "Remove Blank Lines" }
    ];

    var lineBtns = window.FOSS.dom.el("div", {
      className: "row flex-wrap gap-1"
    });

    lineModes.forEach(function (lm) {
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-line-" + lm.id,
        "aria-label": lm.label,
        title: lm.label,
        onClick: function () {
          var val = inputEditor.getValue();
          clearError();
          window.FOSS.api("text_tools_lines", { text: val, operation: lm.id }).then(function (res) {
            setOutput(res.result || "", "[OK] Applied " + lm.label);
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        }
      }, [window.FOSS.dom.el("span", { text: lm.label })]);
      lineBtns.appendChild(btn);
    });

    var lineCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1"
    }, [makeCardTitle("Lines & Sorting"), lineBtns]);

    sidebar.appendChild(lineCard);

    // Category 3: Trim & Clean
    var cleanModes = [
      { id: "collapse_spaces", label: "Collapse Spaces" },
      { id: "trim_leading", label: "Trim Leading" },
      { id: "trim_trailing", label: "Trim Trailing" },
      { id: "tabs_to_spaces", label: "Tabs to Spaces" },
      { id: "spaces_to_tabs", label: "Spaces to Tabs" },
      { id: "normalize_line_endings", label: "Normalize LF" }
    ];

    var cleanBtns = window.FOSS.dom.el("div", {
      className: "row flex-wrap gap-1"
    });

    cleanModes.forEach(function (cm) {
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-clean-" + cm.id,
        "aria-label": cm.label,
        title: cm.label,
        onClick: function () {
          var val = inputEditor.getValue();
          clearError();
          window.FOSS.api("text_tools_cleanup", { text: val, operation: cm.id }).then(function (res) {
            setOutput(res.result || "", "[OK] Applied " + cm.label);
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        }
      }, [window.FOSS.dom.el("span", { text: cm.label })]);
      cleanBtns.appendChild(btn);
    });

    var cleanCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1"
    }, [makeCardTitle("Trim & Clean"), cleanBtns]);

    sidebar.appendChild(cleanCard);

    // Category 4: Encodings & Transforms
    var convModes = [
      { id: "reverse_characters", label: "Reverse Chars" },
      { id: "reverse_words", label: "Reverse Words" },
      { id: "text_to_binary", label: "Text -> Binary" },
      { id: "binary_to_text", label: "Binary -> Text" },
      { id: "text_to_code_points", label: "Text -> Code Points" },
      { id: "code_points_to_text", label: "Code Points -> Text" }
    ];

    var convBtns = window.FOSS.dom.el("div", {
      className: "row flex-wrap gap-1"
    });

    convModes.forEach(function (cv) {
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-conv-" + cv.id,
        "aria-label": cv.label,
        title: cv.label,
        onClick: function () {
          var val = inputEditor.getValue();
          clearError();
          window.FOSS.api("text_tools_convert", { text: val, operation: cv.id }).then(function (res) {
            setOutput(res.result || "", "[OK] Applied " + cv.label);
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        }
      }, [window.FOSS.dom.el("span", { text: cv.label })]);
      convBtns.appendChild(btn);
    });

    var convCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1"
    }, [makeCardTitle("Text Representation"), convBtns]);

    sidebar.appendChild(convCard);

    // Category 5: Regex Find & Replace
    var regexPattern = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-regex-pattern",
      placeholder: "Regex pattern (e.g. \\b\\w+\\b)",
      "aria-label": "Regex Pattern"
    });

    var regexReplacement = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-regex-replacement",
      placeholder: "Replacement string",
      "aria-label": "Replacement String"
    });

    var regexCaseCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "tt-regex-case" });
    var regexCaseLabel = window.FOSS.dom.el("label", {
      htmlFor: "tt-regex-case",
      className: "text-xs cursor-pointer",
      text: "Ignore Case"
    });

    var regexMultiCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "tt-regex-multi" });
    var regexMultiLabel = window.FOSS.dom.el("label", {
      htmlFor: "tt-regex-multi",
      className: "text-xs cursor-pointer",
      text: "Multiline"
    });

    var regexDotallCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "tt-regex-dotall" });
    var regexDotallLabel = window.FOSS.dom.el("label", {
      htmlFor: "tt-regex-dotall",
      className: "text-xs cursor-pointer",
      text: "DotAll"
    });

    var regexFlagsRow = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2"
    }, [
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [regexCaseCheck, regexCaseLabel]),
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [regexMultiCheck, regexMultiLabel]),
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [regexDotallCheck, regexDotallLabel])
    ]);

    var regexApplyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-regex-apply",
      "aria-label": "Apply regular expression replacement",
      title: "Replace All Matches",
      onClick: function () {
        var pattern = regexPattern.value;
        var text = inputEditor.getValue();
        if (!pattern) {
          showError("Regex pattern cannot be empty.");
          return;
        }
        clearError();
        statusBar.textContent = "Applying regex replace...";
        window.FOSS.api("text_tools_regex_replace", {
          text: text,
          pattern: pattern,
          replacement: regexReplacement.value,
          ignore_case: regexCaseCheck.checked,
          multiline: regexMultiCheck.checked,
          dotall: regexDotallCheck.checked
        }).then(function (res) {
          setOutput(res.result || "", "[OK] Replaced " + (res.count !== undefined ? res.count : 0) + " match(es)");
        }).catch(function (err) {
          showError(err.message || String(err));
        });
      }
    }, [window.FOSS.icons.el("search", 14), window.FOSS.dom.el("span", { text: "Replace All Matches" })]);

    var regexCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1"
    }, [
      makeCardTitle("Regex Find & Replace"),
      regexPattern,
      regexReplacement,
      regexFlagsRow,
      regexApplyBtn
    ]);

    sidebar.appendChild(regexCard);

    // Right Stage: Action toolbar + Side-by-Side Editors
    var stage = window.FOSS.dom.el("div", { className: "text-tools-stage-pane" });

    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-swap",
      "aria-label": "Swap input and output text",
      title: "Swap Input and Output",
      onClick: function () {
        var inVal = inputEditor.getValue();
        var outVal = outputEditor.getValue();
        inputEditor.setValue(outVal);
        outputEditor.setValue(inVal);
        statusBar.textContent = "[OK] Swapped input and output";
      }
    }, [window.FOSS.icons.el("refresh-cw", 14), window.FOSS.dom.el("span", { text: "Swap" })]);

    var useOutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-use-output",
      "aria-label": "Use output text as new input",
      title: "Use Output as Input",
      onClick: function () {
        var outVal = outputEditor.getValue();
        inputEditor.setValue(outVal);
        statusBar.textContent = "[OK] Copied output to input";
      }
    }, [window.FOSS.icons.el("arrow-left", 14), window.FOSS.dom.el("span", { text: "Use as Input" })]);

    var copyOutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-copy",
      "aria-label": "Copy output text to clipboard",
      title: "Copy Output",
      onClick: function () {
        var outVal = outputEditor.getValue();
        navigator.clipboard.writeText(outVal).then(function () {
          showToast("Copied output to clipboard", "success");
        });
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Output" })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "text_tools-clear",
      "aria-label": "Clear input and output text",
      title: "Clear All",
      onClick: function () {
        inputEditor.clear();
        outputEditor.clear();
        clearError();
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "text_tools-open-file",
      label: "Open File",
      onFileSelect: function (path) {
        if (!path) return;
        window.FOSS.api("read_text_file", { file_path: path }).then(function (res) {
          inputEditor.setValue(res.text || res.content || "");
          statusBar.textContent = "[OK] Loaded: " + path;
        });
      }
    });

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [filePicker.el, swapBtn, useOutBtn, copyOutBtn, clearBtn]);

    var editorsGrid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [inputEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [outputEditor])
    ]);

    stage.appendChild(toolbar);
    stage.appendChild(errorBanner);
    stage.appendChild(editorsGrid);
    stage.appendChild(statusBar);

    var workbench = window.FOSS.dom.el("div", { className: "split resizable text-tools-workbench" });

    var divider = window.FOSS.components.splitDivider({
      targetSplit: workbench,
      side: "left"
    });

    workbench.appendChild(sidebar);
    workbench.appendChild(divider);
    workbench.appendChild(stage);

    panel.appendChild(workbench);
  }

  function renderDiffTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "text_tools-diff-status",
      text: "Ready"
    });

    var leftEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-diff-left",
      title: "Original Text",
      placeholder: "Paste or type original text here...",
      fillHeight: true
    });

    var rightEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-diff-right",
      title: "Modified Text",
      placeholder: "Paste or type modified text here...",
      fillHeight: true
    });

    var diffViewSelect = window.FOSS.dom.el("select", {
      className: "input input-sm wb-select-md",
      "data-testid": "text_tools-diff-view",
      "aria-label": "Diff View Mode"
    }, [
      window.FOSS.dom.el("option", { value: "unified", text: "Unified Diff" }),
      window.FOSS.dom.el("option", { value: "side_by_side", text: "Side by Side" })
    ]);
    diffViewSelect.value = String(toolDefault("diff_view", "unified"));

    var ignoreWhitespaceCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "tt-diff-ws" });
    var ignoreWhitespaceLabel = window.FOSS.dom.el("label", {
      htmlFor: "tt-diff-ws",
      className: "text-xs cursor-pointer",
      text: "Ignore Whitespace"
    });

    var ignoreCaseCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "tt-diff-case" });
    var ignoreCaseLabel = window.FOSS.dom.el("label", {
      htmlFor: "tt-diff-case",
      className: "text-xs cursor-pointer",
      text: "Ignore Case"
    });

    var statsBadge = window.FOSS.dom.el("div", {
      className: "badge badge-neutral text-xs font-mono",
      "data-testid": "text_tools-diff-stats",
      text: "0 additions, 0 deletions"
    });

    var diffOutput = window.FOSS.components.codeEditor({
      testid: "text_tools-diff-output",
      title: "Diff Result",
      placeholder: "Diff output will be displayed here...",
      readOnly: true,
      fillHeight: true
    });

    var compareBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-diff-compare",
      "aria-label": "Compare both text documents",
      title: "Compare Texts",
      onClick: function () {
        var t1 = leftEditor.getValue();
        var t2 = rightEditor.getValue();
        statusBar.textContent = "Computing diff...";
        window.FOSS.api("text_tools_diff", {
          text1: t1,
          text2: t2,
          ignore_whitespace: ignoreWhitespaceCheck.checked,
          ignore_case: ignoreCaseCheck.checked,
          view: diffViewSelect.value
        }).then(function (res) {
          if (!res || res.ok === false) {
            statusBar.textContent = "Error: " + (res && res.error ? res.error : "Diff failed");
            return;
          }
          var added = res.additions !== undefined ? res.additions : (res.added || 0);
          var removed = res.deletions !== undefined ? res.deletions : (res.removed || 0);
          statsBadge.textContent = "+" + added + " additions, -" + removed + " deletions";
          var diffText = res.diff || res.unified_diff;
          if (!diffText && added === 0 && removed === 0) {
            diffText = "Documents are identical.";
          }
          diffOutput.setValue(diffText || "Documents are identical.");
          statusBar.textContent = "[OK] Diff computed: +" + added + " / -" + removed;
        }).catch(function (err) {
          statusBar.textContent = "Error: " + (err.message || String(err));
        });
      }
    }, [window.FOSS.icons.el("git-pull-request", 14), window.FOSS.dom.el("span", { text: "Compare" })]);

    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Swap left and right text",
      title: "Swap Texts",
      onClick: function () {
        var l = leftEditor.getValue();
        var r = rightEditor.getValue();
        leftEditor.setValue(r);
        rightEditor.setValue(l);
      }
    }, [window.FOSS.icons.el("refresh-cw", 14), window.FOSS.dom.el("span", { text: "Swap" })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "aria-label": "Clear all text",
      title: "Clear",
      onClick: function () {
        leftEditor.clear();
        rightEditor.clear();
        diffOutput.clear();
        statsBadge.textContent = "0 additions, 0 deletions";
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [
      compareBtn,
      swapBtn,
      clearBtn,
      diffViewSelect,
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [ignoreWhitespaceCheck, ignoreWhitespaceLabel]),
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [ignoreCaseCheck, ignoreCaseLabel]),
      statsBadge
    ]);

    var editorsGrid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [leftEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [rightEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [diffOutput])
    ]);

    panel.appendChild(toolbar);
    panel.appendChild(editorsGrid);
    panel.appendChild(statusBar);
  }

  function renderWordCounterTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "text_tools-counter-status",
      text: "Ready"
    });

    var counterEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-counter-input",
      title: "Document Text",
      placeholder: "Type, paste, or open a document to inspect live word count and readability stats...",
      fillHeight: true
    });

    // Stat cards map
    var statKeys = [
      { id: "words", label: "Words" },
      { id: "characters", label: "Characters" },
      { id: "characters_no_spaces", label: "No Spaces" },
      { id: "sentences", label: "Sentences" },
      { id: "paragraphs", label: "Paragraphs" },
      { id: "pages_est", label: "Pages (Est.)" },
      { id: "reading_time_min", label: "Reading Time", suffix: " min" },
      { id: "speaking_time_min", label: "Speaking Time", suffix: " min" }
    ];

    var statEls = {};
    var statGrid = window.FOSS.dom.el("div", { className: "wb-stat-grid" });

    statKeys.forEach(function (sk) {
      var valEl = window.FOSS.dom.el("div", {
        className: "text-xl font-bold font-mono",
        "data-testid": "text_tools-stat-" + sk.id,
        text: "0"
      });
      statEls[sk.id] = valEl;

      var card = window.FOSS.dom.el("div", {
        className: "wb-box text-center"
      }, [
        valEl,
        window.FOSS.dom.el("div", { className: "text-xs text-muted", text: sk.label })
      ]);
      statGrid.appendChild(card);
    });

    // Readability card
    var fleschEaseEl = window.FOSS.dom.el("div", {
      className: "text-lg font-bold font-mono",
      "data-testid": "text_tools-stat-flesch-ease",
      text: "100.0"
    });

    var fkGradeEl = window.FOSS.dom.el("div", {
      className: "text-lg font-bold font-mono",
      "data-testid": "text_tools-stat-fk-grade",
      text: "0.0"
    });

    var readLabelEl = window.FOSS.dom.el("div", {
      className: "badge badge-neutral text-xs",
      "data-testid": "text_tools-stat-read-label",
      text: "Very Easy"
    });

    var readabilityCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2 p-3"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: "Readability & Reading Level" }),
      window.FOSS.dom.el("div", { className: "row items-center justify-between" }, [
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Flesch Reading Ease" }), fleschEaseEl]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Flesch-Kincaid Grade" }), fkGradeEl]),
        readLabelEl
      ])
    ]);

    // Keywords table container: no border/card to avoid A4 table height containment violation
    var kwTableHost = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 wb-field-full"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: "Top Keywords & Density" }),
      window.FOSS.dom.el("div", { className: "text-muted text-xs text-center", text: "Enter text to compute keyword density." })
    ]);

    function updateStats(res) {
      statKeys.forEach(function (sk) {
        var rawVal = res[sk.id];
        if (rawVal === undefined) rawVal = res[sk.id.replace("_min", "_minutes")];
        if (rawVal === undefined) rawVal = 0;
        statEls[sk.id].textContent = String(rawVal) + (sk.suffix || "");
      });

      fleschEaseEl.textContent = String(res.flesch_reading_ease !== undefined ? res.flesch_reading_ease : (res.flesch_ease || 100.0));
      fkGradeEl.textContent = "Grade " + String(res.flesch_kincaid_grade !== undefined ? res.flesch_kincaid_grade : (res.fk_grade || 0.0));
      readLabelEl.textContent = String(res.readability_label || "N/A");

      var kws = res.top_keywords || res.keywords || [];
      if (kws.length > 0) {
        kwTableHost.innerHTML = "";
        kwTableHost.appendChild(window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: "Top Keywords & Density" }));
        var tbl = window.FOSS.dom.el("table", { className: "table text-xs w-full" });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "Keyword" }),
            window.FOSS.dom.el("th", { text: "Occurrences" }),
            window.FOSS.dom.el("th", { text: "Density" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody");
        kws.slice(0, 10).forEach(function (kw) {
          tbody.appendChild(window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", { className: "font-mono font-medium", text: String(kw.word) }),
            window.FOSS.dom.el("td", { text: String(kw.count) }),
            window.FOSS.dom.el("td", { text: String(kw.density_pct) + "%" })
          ]));
        });
        tbl.appendChild(thead);
        tbl.appendChild(tbody);
        kwTableHost.appendChild(tbl);
      }
    }

    var debounceTimer = null;
    function triggerAnalyze() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        var text = counterEditor.getValue();
        if (!text.trim()) {
          updateStats({
            words: 0, characters: 0, characters_no_spaces: 0,
            sentences: 0, paragraphs: 0, pages_est: 0,
            reading_time_min: 0, speaking_time_min: 0,
            flesch_reading_ease: 100, flesch_kincaid_grade: 0,
            readability_label: "N/A", top_keywords: []
          });
          return;
        }
        window.FOSS.api("word_counter_analyze", { text: text }).then(function (res) {
          updateStats(res);
          statusBar.textContent = "[OK] Document analyzed: " + (res.words || 0) + " words";
        });
      }, 250);
    }

    // Bind typing
    var textareaEl = counterEditor.el.querySelector("textarea");
    if (textareaEl) {
      textareaEl.addEventListener("input", triggerAnalyze);
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "text_tools-counter-open-file",
      label: "Open Document",
      onFileSelect: function (path) {
        if (!path) return;
        statusBar.textContent = "Analyzing document file...";
        window.FOSS.api("word_counter_analyze_file", { file_path: path }).then(function (res) {
          counterEditor.setValue(res.text || "");
          updateStats(res);
          statusBar.textContent = "[OK] Loaded & analyzed: " + path;
        });
      }
    });

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-counter-export",
      "aria-label": "Export full document analysis report",
      title: "Export Report",
      onClick: function () {
        var text = counterEditor.getValue();
        window.FOSS.api("word_counter_generate_report", { text: text }).then(function (res) {
          var rep = res.report || "";
          navigator.clipboard.writeText(rep).then(function () {
            showToast("Report copied to clipboard", "success");
          });
        });
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Copy Report" })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "aria-label": "Clear counter text",
      title: "Clear",
      onClick: function () {
        counterEditor.clear();
        triggerAnalyze();
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [filePicker.el, exportBtn, clearBtn]);

    var rightPane = window.FOSS.dom.el("div", {
      className: "wb-editor-col wb-scroll gap-3"
    }, [statGrid, readabilityCard, kwTableHost]);

    var mainGrid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [counterEditor]),
      rightPane
    ]);

    panel.appendChild(toolbar);
    panel.appendChild(mainGrid);
    panel.appendChild(statusBar);
  }

  function renderWritingTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "text_tools-writing-status",
      text: "Ready"
    });

    // Sub-segment 1: Grammar and Style
    var grammarEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-grammar-input",
      title: "Text to Review",
      placeholder: "Paste or type text here to inspect for spelling, sentence spacing, and stylistic issues...",
      fillHeight: true
    });

    var grammarResults = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 wb-box-grow",
      "data-testid": "text_tools-grammar-results"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: "Grammar & Style Issues" }),
      window.FOSS.dom.el("div", { className: "text-muted text-xs text-center", text: "Click 'Check Grammar' to inspect text." })
    ]);

    var checkGrammarBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-grammar-check",
      "aria-label": "Check grammar and style",
      title: "Check Grammar",
      onClick: function () {
        var text = grammarEditor.getValue();
        statusBar.textContent = "Checking grammar...";
        window.FOSS.api("data_grammar_check", { text: text, advanced: false }).then(function (res) {
          grammarResults.innerHTML = "";
          var headRow = window.FOSS.dom.el("div", { className: "row items-center justify-between" }, [
            window.FOSS.dom.el("div", { className: "text-xs font-semibold uppercase text-muted", text: "Grammar & Style Issues" }),
            window.FOSS.dom.el("div", { className: "badge badge-neutral text-xs", text: "Score: " + (res.score || 100) + "/100" })
          ]);
          grammarResults.appendChild(headRow);

          var issues = res.issues || [];
          if (!issues.length) {
            grammarResults.appendChild(window.FOSS.dom.el("div", {
              className: "text-success text-sm text-center p-3",
              text: "Looks clean! No obvious issues detected."
            }));
          } else {
            issues.forEach(function (iss) {
              var card = window.FOSS.dom.el("div", {
                className: "wb-box flex-col gap-1"
              }, [
                window.FOSS.dom.el("div", { className: "text-xs font-semibold text-warning", text: iss.type || "Issue" }),
                window.FOSS.dom.el("div", { className: "text-xs", text: iss.message })
              ]);
              grammarResults.appendChild(card);
            });
          }
          statusBar.textContent = "[OK] Checked grammar: " + issues.length + " issue(s)";
        });
      }
    }, [window.FOSS.icons.el("check-circle", 14), window.FOSS.dom.el("span", { text: "Check Grammar" })]);

    var grammarSection = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2 p-3 wb-grow"
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Offline Grammar & Style Checker" }),
      window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
        window.FOSS.dom.el("div", { className: "wb-editor-col" }, [grammarEditor]),
        window.FOSS.dom.el("div", { className: "wb-editor-col" }, [grammarResults])
      ]),
      window.FOSS.dom.el("div", { className: "row" }, [checkGrammarBtn])
    ]);

    // Sub-segment 2: Citation Builder
    var citTitle = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-title",
      placeholder: "Work / Article / Book Title",
      "aria-label": "Work Title"
    });

    var citAuthors = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-authors",
      placeholder: "Author(s) (e.g. Shannon, C. E.; Weaver, W.)",
      "aria-label": "Authors"
    });

    var citYear = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-year",
      placeholder: "Year (e.g. 1948)",
      "aria-label": "Year"
    });

    var citPublisher = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-publisher",
      placeholder: "Journal / Publisher / Source",
      "aria-label": "Publisher"
    });

    var citVolume = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-volume",
      placeholder: "Vol / Issue",
      "aria-label": "Volume"
    });

    var citPages = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-pages",
      placeholder: "Pages (e.g. 379-423)",
      "aria-label": "Pages"
    });

    var citDoi = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-doi",
      placeholder: "DOI or URL",
      "aria-label": "DOI or URL"
    });

    var defaultCitStyle = String(toolDefault("citation_style", "apa"));
    var citStyle = window.FOSS.dom.el("select", {
      className: "input input-sm wb-flow",
      "data-testid": "text_tools-cit-style",
      "aria-label": "Citation Style"
    }, [
      window.FOSS.dom.el("option", { value: "apa", text: "APA 7th Edition" }),
      window.FOSS.dom.el("option", { value: "mla", text: "MLA 9th Edition" }),
      window.FOSS.dom.el("option", { value: "chicago", text: "Chicago 17th" }),
      window.FOSS.dom.el("option", { value: "ieee", text: "IEEE Standard" }),
      window.FOSS.dom.el("option", { value: "bibtex", text: "BibTeX Entry" })
    ]);
    citStyle.value = defaultCitStyle;

    var citOutput = window.FOSS.dom.el("div", {
      className: "wb-box wb-details font-mono text-sm",
      "data-testid": "text_tools-citation-output",
      text: "Formatted citation will appear here."
    });

    var copyCitBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-citation-copy",
      "aria-label": "Copy formatted citation",
      title: "Copy",
      onClick: function () {
        var val = citOutput.textContent;
        navigator.clipboard.writeText(val).then(function () {
          showToast("Citation copied to clipboard", "success");
        });
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy" })]);

    var generateCitBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-citation-generate",
      "aria-label": "Generate citation in chosen style",
      title: "Generate Citation",
      onClick: function () {
        var meta = {
          title: citTitle.value || "Untitled",
          authors: citAuthors.value ? citAuthors.value.split(";").map(function (s) { return s.trim(); }) : ["Unknown Author"],
          year: citYear.value || "n.d.",
          publisher: citPublisher.value || "",
          volume: citVolume.value || "",
          pages: citPages.value || "",
          doi: citDoi.value || "",
          url: citDoi.value || ""
        };
        statusBar.textContent = "Formatting citation...";
        window.FOSS.api("data_generate_citation", {
          metadata: meta,
          style: citStyle.value
        }).then(function (res) {
          citOutput.textContent = res.citation || "";
          statusBar.textContent = "[OK] Generated " + citStyle.value.toUpperCase() + " citation";
        });
      }
    }, [window.FOSS.icons.el("book-open", 14), window.FOSS.dom.el("span", { text: "Generate Citation" })]);

    var citInputsRow1 = window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap items-center" }, [citTitle, citAuthors, citYear]);
    var citInputsRow2 = window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap items-center" }, [citPublisher, citVolume, citPages, citDoi, citStyle]);

    var citationSection = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2 p-3"
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Academic Citation Builder" }),
      citInputsRow1,
      citInputsRow2,
      window.FOSS.dom.el("div", { className: "row gap-2" }, [generateCitBtn, copyCitBtn]),
      citOutput
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "wb-fill wb-scroll gap-3"
    }, [grammarSection, citationSection, statusBar]));
  }

  window.FOSS.router.register({
    id: "text_tools",
    title: "Text Tools",
    navName: "Text Tools",
    category: "Data",
    icon: "text_tools",
    workbench: true,
    defaults: [
      {
        key: "case_mode",
        label: "Default case mode",
        type: "select",
        options: CASE_MODES.map(function (m) { return { value: m.mode, label: m.label }; }),
        default: "titlecase",
        hint: "Case mode preselected in the Case Conversions quick selector."
      },
      {
        key: "diff_view",
        label: "Default diff view",
        type: "select",
        options: [
          { value: "unified", label: "Unified" },
          { value: "side_by_side", label: "Side by side" }
        ],
        default: "unified",
        hint: "View used when comparing texts."
      },
      {
        key: "citation_style",
        label: "Default citation style",
        type: "select",
        options: [
          { value: "apa", label: "APA 7th Edition" },
          { value: "mla", label: "MLA 9th Edition" },
          { value: "chicago", label: "Chicago 17th" },
          { value: "ieee", label: "IEEE Standard" },
          { value: "bibtex", label: "BibTeX Entry" }
        ],
        default: "apa"
      }
    ],
    tabs: [
      { id: "transforms", label: "Text Transforms", aliases: ["main", "case"], render: renderTransformsTab },
      { id: "diff", label: "Side-by-Side Diff", aliases: ["diff_checker"], render: renderDiffTab },
      { id: "counter", label: "Word Counter", aliases: ["word_counter"], render: renderWordCounterTab },
      { id: "writing", label: "Grammar & Citations", aliases: ["grammar"], render: renderWritingTab }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        window.FOSS.api("read_text_file", { file_path: paths[0] }).then(function (res) {
          if (res && (res.text || res.content)) {
            var inEl = document.querySelector("[data-testid='text_tools-input-input']");
            if (inEl) {
              inEl.value = res.text || res.content;
              inEl.dispatchEvent(new Event("input"));
            }
          }
        });
      }
    }
  });
})();
