// Text manipulation workbench: transforms, diff, word counter, and writing tools.
window.FOSS = window.FOSS || {};

(function () {
  function showToast(msg, kind) {
    if (window.FOSS && window.FOSS.toast && typeof window.FOSS.toast.show === "function") {
      window.FOSS.toast.show(msg, kind);
    }
  }

  function renderTransformsTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "text_tools-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "text_tools-error",
      style: { marginBottom: "var(--space-2)" }
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
    var sidebar = window.FOSS.dom.el("div", {
      className: "text-tools-sidebar-pane",
      style: { width: "100%", height: "100%", overflowY: "auto" }
    });

    // Helper for card titles
    function makeCardTitle(title) {
      return window.FOSS.dom.el("div", {
        className: "text-xs font-semibold uppercase tracking-wider text-muted",
        style: { marginBottom: "var(--space-1)" },
        text: title
      });
    }

    // Category 1: Case Conversions
    var caseModes = [
      { id: "upper", label: "UPPERCASE" },
      { id: "lower", label: "lowercase" },
      { id: "title", label: "Title Case" },
      { id: "sentence", label: "Sentence case" },
      { id: "camel", label: "camelCase" },
      { id: "snake", label: "snake_case" },
      { id: "kebab", label: "kebab-case" },
      { id: "constant", label: "CONSTANT_CASE" },
      { id: "pascal", label: "PascalCase" }
    ];

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
        onClick: function () {
          var val = inputEditor.getValue();
          clearError();
          window.FOSS.api("text_tools_case", { text: val, mode: m.id }).then(function (res) {
            setOutput(res.result || "", "[OK] Converted to " + m.label);
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        }
      }, [window.FOSS.dom.el("span", { text: m.label })]);
      caseBtns.appendChild(btn);
    });

    var caseCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-1",
      style: { width: "100%" }
    }, [makeCardTitle("Case Conversions"), caseBtns]);

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
      className: "card card-compact flex-col gap-1",
      style: { width: "100%" }
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
      className: "card card-compact flex-col gap-1",
      style: { width: "100%" }
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
      className: "card card-compact flex-col gap-1",
      style: { width: "100%" }
    }, [makeCardTitle("Text Representation"), convBtns]);

    sidebar.appendChild(convCard);

    // Category 5: Regex Find & Replace
    var regexPattern = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-regex-pattern",
      placeholder: "Regex pattern (e.g. \\b\\w+\\b)",
      "aria-label": "Regex Pattern",
      style: { width: "100%", marginBottom: "var(--space-1)" }
    });

    var regexReplacement = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-regex-replacement",
      placeholder: "Replacement string",
      "aria-label": "Replacement String",
      style: { width: "100%", marginBottom: "var(--space-1)" }
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
      className: "row items-center flex-wrap gap-2",
      style: { marginBottom: "var(--space-2)" }
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
      style: { width: "100%" },
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
      className: "card card-compact flex-col gap-1",
      style: { width: "100%" }
    }, [
      makeCardTitle("Regex Find & Replace"),
      regexPattern,
      regexReplacement,
      regexFlagsRow,
      regexApplyBtn
    ]);

    sidebar.appendChild(regexCard);

    // Right Stage: Action toolbar + Side-by-Side Editors
    var stage = window.FOSS.dom.el("div", {
      className: "text-tools-stage-pane",
      style: { width: "100%", height: "100%", display: "flex", flexDirection: "column", gap: "var(--space-2)" }
    });

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

    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [filePicker.el, swapBtn, useOutBtn, copyOutBtn, clearBtn]);

    var editorsGrid = window.FOSS.dom.el("div", {
      className: "row gap-2 items-stretch code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "22rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0", height: "100%" } }, [inputEditor.el]),
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0", height: "100%" } }, [outputEditor.el])
    ]);

    stage.appendChild(toolbar);
    stage.appendChild(errorBanner);
    stage.appendChild(editorsGrid);
    stage.appendChild(statusBar);

    var workbench = window.FOSS.dom.el("div", {
      className: "split resizable text-tools-workbench",
      style: { height: "100%", width: "100%" }
    });

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
      className: "text-xs text-muted",
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

    var diffModeSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "aria-label": "Diff Mode",
      style: { width: "130px" }
    }, [
      window.FOSS.dom.el("option", { value: "lines", text: "Line by Line" }),
      window.FOSS.dom.el("option", { value: "words", text: "Word by Word" })
    ]);

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
      title: "Unified Diff",
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
          ignore_case: ignoreCaseCheck.checked
        }).then(function (res) {
          var added = res.added !== undefined ? res.added : (res.additions || 0);
          var removed = res.removed !== undefined ? res.removed : (res.deletions || 0);
          statsBadge.textContent = "+" + added + " additions, -" + removed + " deletions";
          diffOutput.setValue(res.diff || res.unified_diff || "Documents are identical.");
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

    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [
      compareBtn,
      swapBtn,
      clearBtn,
      diffModeSelect,
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [ignoreWhitespaceCheck, ignoreWhitespaceLabel]),
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [ignoreCaseCheck, ignoreCaseLabel]),
      statsBadge
    ]);

    var topGrid = window.FOSS.dom.el("div", {
      className: "row gap-2 items-stretch code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "15rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0", height: "100%" } }, [leftEditor.el]),
      window.FOSS.dom.el("div", { className: "flex-col flex-1 code-editor-fill", style: { minWidth: "0", height: "100%" } }, [rightEditor.el])
    ]);

    var bottomPane = window.FOSS.dom.el("div", {
      className: "flex-col code-editor-fill",
      style: { flex: "1 1 0%", minHeight: "15rem", width: "100%" }
    }, [diffOutput.el]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      style: { height: "100%", width: "100%", overflowY: "auto" }
    }, [toolbar, topGrid, bottomPane, statusBar]));
  }

  function renderWordCounterTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
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
    var statGrid = window.FOSS.dom.el("div", {
      className: "grid gap-2",
      style: { gridTemplateColumns: "repeat(4, minmax(0, 1fr))", width: "100%" }
    });

    statKeys.forEach(function (sk) {
      var valEl = window.FOSS.dom.el("div", {
        className: "text-xl font-bold font-mono",
        "data-testid": "text_tools-stat-" + sk.id,
        text: "0"
      });
      statEls[sk.id] = valEl;

      var card = window.FOSS.dom.el("div", {
        className: "p-2 rounded text-center",
        style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)" }
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
      className: "card card-compact flex-col gap-2 p-3",
      style: { width: "100%" }
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
      className: "flex-col gap-2",
      style: { width: "100%" }
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
        var tbl = window.FOSS.dom.el("table", { className: "table text-xs", style: { width: "100%" } });
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

    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-center flex-wrap gap-2 p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", width: "100%" }
    }, [filePicker.el, exportBtn, clearBtn]);

    var rightPane = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { flex: "1 1 0%", minWidth: "0", overflowY: "auto" }
    }, [statGrid, readabilityCard, kwTableHost]);

    var mainGrid = window.FOSS.dom.el("div", {
      className: "row gap-3 items-stretch",
      style: { flex: "1 1 0%", minHeight: "22rem", width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "0", height: "100%" } }, [counterEditor.el]),
      rightPane
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      style: { height: "100%", width: "100%", overflowY: "auto" }
    }, [toolbar, mainGrid, statusBar]));
  }

  function renderWritingTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
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
      className: "flex-col gap-2 p-2",
      "data-testid": "text_tools-grammar-results",
      style: { flex: "1 1 0%", minHeight: "10rem", overflowY: "auto" }
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
                className: "p-2 rounded flex-col gap-1",
                style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)" }
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
      className: "card card-compact flex-col gap-2 p-3",
      style: { width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Offline Grammar & Style Checker" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-stretch", style: { minHeight: "14rem" } }, [
        window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "0" } }, [grammarEditor.el]),
        window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "0" } }, [grammarResults])
      ]),
      window.FOSS.dom.el("div", { className: "row" }, [checkGrammarBtn])
    ]);

    // Sub-segment 2: Citation Builder
    var citTitle = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-title",
      placeholder: "Work / Article / Book Title",
      "aria-label": "Work Title",
      style: { flex: "2 1 12rem" }
    });

    var citAuthors = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-authors",
      placeholder: "Author(s) (e.g. Shannon, C. E.; Weaver, W.)",
      "aria-label": "Authors",
      style: { flex: "2 1 12rem" }
    });

    var citYear = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-year",
      placeholder: "Year (e.g. 1948)",
      "aria-label": "Year",
      style: { flex: "1 1 6rem" }
    });

    var citPublisher = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-publisher",
      placeholder: "Journal / Publisher / Source",
      "aria-label": "Publisher",
      style: { flex: "2 1 12rem" }
    });

    var citVolume = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-volume",
      placeholder: "Vol / Issue",
      "aria-label": "Volume",
      style: { flex: "1 1 5rem" }
    });

    var citPages = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-pages",
      placeholder: "Pages (e.g. 379-423)",
      "aria-label": "Pages",
      style: { flex: "1 1 6rem" }
    });

    var citDoi = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm",
      "data-testid": "text_tools-cit-doi",
      placeholder: "DOI or URL",
      "aria-label": "DOI or URL",
      style: { flex: "2 1 12rem" }
    });

    var citStyle = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "text_tools-cit-style",
      "aria-label": "Citation Style",
      style: { flex: "1 1 8rem" }
    }, [
      window.FOSS.dom.el("option", { value: "apa", text: "APA 7th Edition" }),
      window.FOSS.dom.el("option", { value: "mla", text: "MLA 9th Edition" }),
      window.FOSS.dom.el("option", { value: "chicago", text: "Chicago 17th" }),
      window.FOSS.dom.el("option", { value: "ieee", text: "IEEE Standard" }),
      window.FOSS.dom.el("option", { value: "bibtex", text: "BibTeX Entry" })
    ]);

    var citOutput = window.FOSS.dom.el("div", {
      className: "p-3 rounded font-mono text-sm",
      "data-testid": "text_tools-citation-output",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", minHeight: "3rem", wordBreak: "break-all" },
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
      className: "card card-compact flex-col gap-2 p-3",
      style: { width: "100%" }
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Academic Citation Builder" }),
      citInputsRow1,
      citInputsRow2,
      window.FOSS.dom.el("div", { className: "row gap-2" }, [generateCitBtn, copyCitBtn]),
      citOutput
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { height: "100%", width: "100%", overflowY: "auto" }
    }, [grammarSection, citationSection, statusBar]));
  }

  window.FOSS.router.register({
    id: "text_tools",
    title: "Text Tools",
    navName: "Text Tools",
    category: "Data",
    icon: "edit",
    workbench: true,
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
