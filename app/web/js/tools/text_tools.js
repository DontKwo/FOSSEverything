// Text manipulation tool workspace: casing, reversal, cleanup, line ops, conversions, regex, and diff.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Case conversion, reversal, whitespace cleanup, line operations, and text/ASCII/binary conversion."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "text_tools-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "text_tools-status",
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

    var inputEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-input",
      title: "Input Text",
      placeholder: "Type or paste text here to case-convert, reverse, clean up, sort, or convert it..."
    });

    var outputEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-output",
      title: "Output Text",
      placeholder: "Transformed output appears here...",
      readOnly: false
    });

    function setOutput(txt, statusMsg) {
      clearError();
      outputEditor.setValue(txt);
      statusBar.textContent = statusMsg || "[OK] Operation applied";
    }

    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-swap",
      type: "button",
      onClick: function () {
        var inVal = inputEditor.getValue();
        var outVal = outputEditor.getValue();
        inputEditor.setValue(outVal);
        outputEditor.setValue(inVal);
        statusBar.textContent = "[OK] Swapped input and output";
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Swap" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "text_tools-clear",
      type: "button",
      onClick: function () {
        inputEditor.clear();
        outputEditor.clear();
        clearError();
        statusBar.textContent = "Ready";
      }
    }, [
      window.FOSS.icons.el("close", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var globalActions = window.FOSS.dom.el("div", {
      className: "row",
      gap: "sm"
    }, [swapBtn, clearBtn]);

    // Section 1: Case (8 modes)
    var caseModes = [
      { id: "upper", label: "UPPERCASE" },
      { id: "lower", label: "lowercase" },
      { id: "title", label: "Title Case" },
      { id: "sentence", label: "Sentence case" },
      { id: "camel", label: "camelCase" },
      { id: "snake", label: "snake_case" },
      { id: "kebab", label: "kebab-case" },
      { id: "constant", label: "CONSTANT_CASE" }
    ];

    var caseBtns = caseModes.map(function (m) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-case-" + m.id,
        type: "button",
        onClick: function () {
          var txt = inputEditor.getValue();
          if (!txt) return;
          window.FOSS.api("text_tools_case", { text: txt, mode: m.id }).then(function (res) {
            if (res && res.ok) {
              setOutput(res.result, "[OK] Converted to " + m.label);
            } else {
              showError((res && res.error) || "Case conversion failed");
            }
          });
        }
      }, [window.FOSS.dom.el("span", { text: m.label })]);
    });

    var caseCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Case" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" }, caseBtns)
    ]);

    // Section 2: Reverse (3 modes)
    var reverseModes = [
      { id: "reverse_characters", label: "Reverse Characters" },
      { id: "reverse_words", label: "Reverse Words" },
      { id: "reverse_lines", label: "Reverse Lines" }
    ];

    var reverseBtns = reverseModes.map(function (m) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-reverse-" + m.id,
        type: "button",
        onClick: function () {
          var txt = inputEditor.getValue();
          if (!txt) return;
          var method = m.id === "reverse_lines" ? "text_tools_lines" : "text_tools_convert";
          window.FOSS.api(method, { text: txt, operation: m.id }).then(function (res) {
            if (res && res.ok) {
              setOutput(res.result, "[OK] " + m.label);
            } else {
              showError((res && res.error) || "Reversal failed");
            }
          });
        }
      }, [window.FOSS.dom.el("span", { text: m.label })]);
    });

    var reverseCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Reverse" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" }, reverseBtns)
    ]);

    // Section 3: Cleanup
    var tabWidthInput = window.FOSS.dom.el("input", {
      type: "number",
      min: "1",
      max: "16",
      value: "4",
      className: "input",
      "data-testid": "text_tools-cleanup-tab-width",
      "aria-label": "Tab width"
    });

    var lineEndingsSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "text_tools-cleanup-line-endings",
      "aria-label": "Line endings"
    }, [
      window.FOSS.dom.el("option", { value: "lf", text: "LF" }),
      window.FOSS.dom.el("option", { value: "crlf", text: "CRLF" }),
      window.FOSS.dom.el("option", { value: "cr", text: "CR" })
    ]);

    var cleanupActions = [
      { id: "collapse_spaces", label: "Collapse Spaces" },
      { id: "trim_leading", label: "Trim Leading" },
      { id: "trim_trailing", label: "Trim Trailing" },
      { id: "remove_blank", label: "Remove Blank Lines" }
    ].map(function (c) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-cleanup-" + c.id,
        type: "button",
        onClick: function () {
          var txt = inputEditor.getValue();
          if (!txt) return;
          var method = c.id === "remove_blank" ? "text_tools_lines" : "text_tools_cleanup";
          window.FOSS.api(method, { text: txt, operation: c.id }).then(function (res) {
            if (res && res.ok) {
              setOutput(res.result, "[OK] " + c.label);
            } else {
              showError((res && res.error) || "Cleanup failed");
            }
          });
        }
      }, [window.FOSS.dom.el("span", { text: c.label })]);
    });

    var tabsToSpacesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-cleanup-tabs-to-spaces",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        var w = Number(tabWidthInput.value) || 4;
        window.FOSS.api("text_tools_cleanup", { text: txt, operation: "tabs_to_spaces", width: w }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Tabs to Spaces (width " + w + ")");
          } else {
            showError((res && res.error) || "Tabs conversion failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Tabs to Spaces" })]);

    var spacesToTabsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-cleanup-spaces-to-tabs",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        var w = Number(tabWidthInput.value) || 4;
        window.FOSS.api("text_tools_cleanup", { text: txt, operation: "spaces_to_tabs", width: w }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Spaces to Tabs (width " + w + ")");
          } else {
            showError((res && res.error) || "Spaces conversion failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Spaces to Tabs" })]);

    var normalizeEndingsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-cleanup-normalize-endings",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        var st = lineEndingsSelect.value;
        window.FOSS.api("text_tools_cleanup", { text: txt, operation: "normalize_line_endings", style: st }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Normalized line endings to " + st.toUpperCase());
          } else {
            showError((res && res.error) || "Line ending normalization failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Normalize Endings" })]);

    var cleanupCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Cleanup" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" }, cleanupActions),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "sm" }, [
        window.FOSS.dom.el("label", { text: "Tab width:", className: "text-xs" }),
        tabWidthInput,
        tabsToSpacesBtn,
        spacesToTabsBtn
      ]),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "sm" }, [
        window.FOSS.dom.el("label", { text: "Line endings:", className: "text-xs" }),
        lineEndingsSelect,
        normalizeEndingsBtn
      ])
    ]);

    // Section 4: Lines
    var prefixInput = window.FOSS.dom.el("input", {
      type: "text",
      placeholder: "Prefix...",
      className: "input",
      "data-testid": "text_tools-lines-prefix",
      "aria-label": "Prefix"
    });

    var suffixInput = window.FOSS.dom.el("input", {
      type: "text",
      placeholder: "Suffix...",
      className: "input",
      "data-testid": "text_tools-lines-suffix",
      "aria-label": "Suffix"
    });

    var delimiterInput = window.FOSS.dom.el("input", {
      type: "text",
      value: ",",
      className: "input",
      "data-testid": "text_tools-lines-delimiter",
      "aria-label": "Delimiter"
    });

    var lineActions = [
      { id: "sort_asc", label: "Sort Ascending" },
      { id: "sort_desc", label: "Sort Descending" },
      { id: "dedupe", label: "Deduplicate Lines" },
      { id: "number", label: "Number Lines" }
    ].map(function (la) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-lines-" + la.id,
        type: "button",
        onClick: function () {
          var txt = inputEditor.getValue();
          if (!txt) return;
          window.FOSS.api("text_tools_lines", { text: txt, operation: la.id }).then(function (res) {
            if (res && res.ok) {
              setOutput(res.result, "[OK] " + la.label);
            } else {
              showError((res && res.error) || "Line operation failed");
            }
          });
        }
      }, [window.FOSS.dom.el("span", { text: la.label })]);
    });

    var addPrefixSuffixBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-lines-add-prefix-suffix",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        window.FOSS.api("text_tools_lines", {
          text: txt,
          operation: "prefix_suffix",
          prefix: prefixInput.value,
          suffix: suffixInput.value
        }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Added Prefix/Suffix");
          } else {
            showError((res && res.error) || "Prefix/suffix failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Add Prefix/Suffix" })]);

    var joinLinesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-lines-join",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        window.FOSS.api("text_tools_lines", {
          text: txt,
          operation: "join",
          delimiter: delimiterInput.value
        }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Joined Lines");
          } else {
            showError((res && res.error) || "Join lines failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Join Lines" })]);

    var splitTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-lines-split",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        window.FOSS.api("text_tools_lines", {
          text: txt,
          operation: "split",
          delimiter: delimiterInput.value
        }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Split Text");
          } else {
            showError((res && res.error) || "Split text failed");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Split Text" })]);

    var linesCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Lines" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" }, lineActions),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "sm" }, [
        prefixInput,
        suffixInput,
        addPrefixSuffixBtn
      ]),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "sm" }, [
        window.FOSS.dom.el("label", { text: "Delimiter:", className: "text-xs" }),
        delimiterInput,
        joinLinesBtn,
        splitTextBtn
      ])
    ]);

    // Section 5: Convert (Code points & Binary)
    var convertActions = [
      { id: "text_to_code_points", label: "Text to Code Points" },
      { id: "code_points_to_text", label: "Code Points to Text" },
      { id: "text_to_binary", label: "Text to Binary" },
      { id: "binary_to_text", label: "Binary to Text" }
    ].map(function (cv) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "text_tools-convert-" + cv.id,
        type: "button",
        onClick: function () {
          var txt = inputEditor.getValue();
          if (!txt) return;
          window.FOSS.api("text_tools_convert", { text: txt, operation: cv.id }).then(function (res) {
            if (res && res.ok) {
              setOutput(res.result, "[OK] " + cv.label);
            } else {
              showError((res && res.error) || "Conversion failed");
            }
          });
        }
      }, [window.FOSS.dom.el("span", { text: cv.label })]);
    });

    var convertCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Convert" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" }, convertActions)
    ]);

    // Section 6: Regex Find & Replace
    var patternInput = window.FOSS.dom.el("input", {
      type: "text",
      placeholder: "Pattern (e.g. \\d+)",
      className: "input",
      "data-testid": "text_tools-regex-pattern",
      "aria-label": "Pattern"
    });

    var replacementInput = window.FOSS.dom.el("input", {
      type: "text",
      placeholder: "Replacement...",
      className: "input",
      "data-testid": "text_tools-regex-replacement",
      "aria-label": "Replacement"
    });

    var ignoreCaseSwitch = window.FOSS.components.switch({
      testid: "text_tools-regex-ignore-case",
      label: "Case-insensitive",
      checked: false
    });

    var multilineSwitch = window.FOSS.components.switch({
      testid: "text_tools-regex-multiline",
      label: "Multiline",
      checked: false
    });

    var dotallSwitch = window.FOSS.components.switch({
      testid: "text_tools-regex-dotall",
      label: "Dot matches all",
      checked: false
    });

    var applyRegexBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-regex-apply",
      type: "button",
      onClick: function () {
        var txt = inputEditor.getValue();
        if (!txt) return;
        var pat = patternInput.value;
        if (!pat) {
          showError("Regex pattern cannot be empty");
          return;
        }
        window.FOSS.api("text_tools_regex_replace", {
          text: txt,
          pattern: pat,
          replacement: replacementInput.value,
          ignore_case: ignoreCaseSwitch.isChecked(),
          multiline: multilineSwitch.isChecked(),
          dotall: dotallSwitch.isChecked()
        }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.result, "[OK] Regex replaced " + res.count + " match(es)");
          } else {
            showError((res && res.error) || "Regex replace failed");
          }
        });
      }
    }, [
      window.FOSS.icons.el("play", 16),
      window.FOSS.dom.el("span", { text: "Apply Regex" })
    ]);

    var regexCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Regex Find & Replace" }),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "sm" }, [
        patternInput,
        replacementInput,
        applyRegexBtn
      ]),
      window.FOSS.dom.el("div", { className: "row wrap", gap: "md" }, [
        ignoreCaseSwitch.el,
        multilineSwitch.el,
        dotallSwitch.el
      ])
    ]);

    // Section 7: Diff Checker
    var diffRightInput = window.FOSS.dom.el("textarea", {
      className: "code-editor",
      placeholder: "Paste the text you want to compare against the left side...",
      "data-testid": "text_tools-diff-right-input",
      "aria-label": "Right (compare against)"
    });

    var compareDiffBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-diff-compare",
      type: "button",
      onClick: function () {
        var leftTxt = inputEditor.getValue();
        var rightTxt = diffRightInput.value;
        window.FOSS.api("text_tools_diff", { text1: leftTxt, text2: rightTxt }).then(function (res) {
          if (res && res.ok) {
            setOutput(res.diff || "No differences found.", "[OK] Diff complete: " + res.additions + " added, " + res.deletions + " removed");
          } else {
            showError((res && res.error) || "Diff computation failed");
          }
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Compare Diff" })
    ]);

    var diffCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Diff Checker" }),
      window.FOSS.dom.el("div", { className: "stack", gap: "xs" }, [
        window.FOSS.dom.el("label", { text: "Left (original):", className: "text-xs text-muted" }),
        window.FOSS.dom.el("label", { text: "Right (compare against):", className: "text-xs text-muted" }),
        diffRightInput,
        compareDiffBtn
      ])
    ]);

    var editorsSplit = window.FOSS.dom.el("div", {
      className: "split even"
    }, [
      inputEditor.el,
      outputEditor.el
    ]);

    var operationsPalette = window.FOSS.dom.el("div", {
      className: "stack",
      gap: "sm"
    }, [
      caseCard,
      reverseCard,
      cleanupCard,
      linesCard,
      convertCard,
      regexCard,
      diffCard
    ]);

    panel.appendChild(window.FOSS.dom.el("div", { className: "page stack", gap: "md" }, [
      desc,
      errorBanner,
      globalActions,
      editorsSplit,
      operationsPalette,
      statusBar
    ]));
  }

  window.FOSS.router.register({
    id: "text_tools",
    title: "Text Tools",
    navName: "Text Tools",
    category: "Data",
    icon: "edit",
    workbench: false,
    tabs: [
      { id: "main", label: "Text Operations", render: renderMain }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        window.FOSS.api("read_text_file", { path: paths[0] }).then(function (res) {
          if (res && res.ok && res.content) {
            var inEl = document.querySelector("[data-testid='text_tools-input-input']");
            if (inEl) {
              inEl.value = res.content;
              inEl.dispatchEvent(new Event("input"));
            }
          }
        });
      }
    }
  });
})();
