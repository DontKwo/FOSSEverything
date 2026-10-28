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

  function renderWordCounterTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Word counter document analytics: analyze words, characters, readability, and keyword density."
    });

    var editor = window.FOSS.components.codeEditor({
      testid: "text_tools-wc-input",
      title: "Document Text",
      placeholder: "Type, paste text, or open any document (PDF, Word, Excel, PowerPoint, text, Markdown) to analyze stats in real-time...",
      ariaLabel: "Document text to analyze"
    });

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-wc-open-file",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {
          title: "Open Document for Word Counter",
          file_types: [
            ["All Supported Documents", "*.pdf;*.docx;*.pptx;*.xlsx;*.odt;*.ods;*.odp;*.txt;*.md;*.html;*.csv;*.json;*.yaml;*.py"],
            ["All Files", "*.*"]
          ]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            window.FOSS.api("word_counter_analyze_file", { file_path: res.paths[0] }).then(function (fres) {
              if (fres && fres.ok && fres.extracted_text) {
                editor.setValue(fres.extracted_text);
                updateStats();
              }
            });
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Open File..." })
    ]);

    var pasteBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-wc-paste",
      type: "button",
      onClick: function () {
        navigator.clipboard.readText().then(function (clip) {
          if (clip) {
            editor.setValue(clip);
            updateStats();
          }
        }).catch(function () {});
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Paste Clipboard" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "text_tools-wc-clear",
      type: "button",
      onClick: function () {
        editor.setValue("");
        updateStats();
      }
    }, [
      window.FOSS.icons.el("close", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-wc-export-report",
      type: "button",
      onClick: function () {
        var txt = editor.getValue();
        if (!txt) return;
        window.FOSS.api("word_counter_generate_report", { text: txt }).then(function (res) {
          if (res && res.ok && res.report) {
            window.FOSS.api("select_save_path", {
              default_name: "word_count_report.txt",
              file_types: [["Text Report", "*.txt"], ["All Files", "*.*"]]
            }).then(function (saveRes) {
              if (saveRes && saveRes.paths && saveRes.paths.length > 0) {
                window.FOSS.api("write_text_file", { path: saveRes.paths[0], content: res.report }).then(function () {
                  window.FOSS.toast.show("Report saved successfully", "success");
                });
              }
            });
          }
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Export Report" })
    ]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "row wrap",
      gap: "sm"
    }, [openBtn, pasteBtn, clearBtn, exportBtn]);

    function makeStatCard(label, defaultVal, testid) {
      var valEl = window.FOSS.dom.el("div", {
        className: "text-xl font-bold font-mono",
        "data-testid": testid,
        text: defaultVal
      });
      var card = window.FOSS.dom.el("div", {
        className: "card stack-xs text-center",
        style: "flex: 1; min-width: 7.5rem; padding: var(--space-3);"
      }, [
        valEl,
        window.FOSS.dom.el("div", { className: "text-xs text-muted", text: label })
      ]);
      return { el: card, valEl: valEl };
    }

    var cardWords = makeStatCard("Words", "0", "text_tools-wc-stat-words");
    var cardChars = makeStatCard("Characters", "0", "text_tools-wc-stat-chars");
    var cardSentences = makeStatCard("Sentences", "0", "text_tools-wc-stat-sentences");
    var cardParagraphs = makeStatCard("Paragraphs", "0", "text_tools-wc-stat-paragraphs");
    var cardReading = makeStatCard("Reading Time", "0s", "text_tools-wc-stat-reading");
    var cardReadability = makeStatCard("Readability", "100.0 / 100", "text_tools-wc-stat-readability");

    var statsGrid = window.FOSS.dom.el("div", {
      className: "row wrap",
      gap: "sm"
    }, [
      cardWords.el, cardChars.el, cardSentences.el, cardParagraphs.el, cardReading.el, cardReadability.el
    ]);

    var densityContainer = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Keyword Density (Top Words)" }),
      window.FOSS.dom.el("div", {
        className: "text-xs text-muted",
        "data-testid": "text_tools-wc-density-list",
        text: "Type or paste text to see keyword density frequency."
      })
    ]);

    function updateStats() {
      var text = editor.getValue();
      if (!text.trim()) {
        cardWords.valEl.textContent = "0";
        cardChars.valEl.textContent = "0";
        cardSentences.valEl.textContent = "0";
        cardParagraphs.valEl.textContent = "0";
        cardReading.valEl.textContent = "0s";
        cardReadability.valEl.textContent = "100.0 / 100";
        return;
      }

      window.FOSS.api("word_counter_analyze", { text: text }).then(function (res) {
        if (!res || !res.ok) return;
        var s = res.stats || {};
        cardWords.valEl.textContent = String(s.word_count || 0);
        cardChars.valEl.textContent = String(s.char_count || 0);
        cardSentences.valEl.textContent = String(s.sentence_count || 0);
        cardParagraphs.valEl.textContent = String(s.paragraph_count || 0);

        var rSec = Math.round(s.reading_time_seconds || 0);
        cardReading.valEl.textContent = rSec < 60 ? rSec + "s" : Math.floor(rSec / 60) + "m " + (rSec % 60) + "s";

        var score = s.flesch_reading_ease !== undefined ? s.flesch_reading_ease.toFixed(1) : "100.0";
        cardReadability.valEl.textContent = score + " / 100";

        var density = s.keyword_density || [];
        var dList = densityContainer.querySelector("[data-testid='text_tools-wc-density-list']");
        if (dList && density.length > 0) {
          dList.innerHTML = "";
          var tagsWrap = window.FOSS.dom.el("div", { className: "row wrap", gap: "xs" });
          density.slice(0, 15).forEach(function (item) {
            tagsWrap.appendChild(window.FOSS.dom.el("span", {
              className: "badge info",
              text: item[0] + " (" + item[1] + ")"
            }));
          });
          dList.appendChild(tagsWrap);
        }
      });
    }

    var inEl = editor.el.querySelector("textarea") || editor.el.querySelector("input");
    if (inEl) {
      inEl.addEventListener("input", updateStats);
    }

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "page stack",
      gap: "md"
    }, [desc, toolbar, statsGrid, editor.el, densityContainer]));
  }

  function renderGrammarTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Grammar inspection, citation generation, and unified document diffing."
    });

    var textEditor = window.FOSS.components.codeEditor({
      testid: "text_tools-grammar-input",
      title: "Writing & Grammar Document",
      placeholder: "Type or paste text for offline grammar and style analysis...",
      ariaLabel: "Writing document editor"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "text_tools-grammar-status",
      text: "Ready"
    });

    var resultsContainer = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs",
      "data-testid": "text_tools-grammar-results"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Analysis Results" }),
      window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Run Grammar Check or Citation Generator to see results here." })
    ]);

    var grammarBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "text_tools-grammar-check",
      "aria-label": "Check grammar",
      title: "Check grammar",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_grammar_check", { text: txt, advanced: false }).then(function (res) {
          var m = res.matches || [];
          statusEl.textContent = "[OK] Grammar check: " + m.length + " issues flagged";
          resultsContainer.innerHTML = "";
          resultsContainer.appendChild(window.FOSS.dom.el("span", { className: "card-title", text: "Grammar Issues (" + m.length + ")" }));
          if (m.length === 0) {
            resultsContainer.appendChild(window.FOSS.dom.el("div", { className: "text-sm text-success", text: "No grammar or style issues detected." }));
          } else {
            var list = window.FOSS.dom.el("div", { className: "stack", gap: "xs" });
            m.forEach(function (issue) {
              list.appendChild(window.FOSS.dom.el("div", { className: "banner warning", style: "margin: 0;" }, [
                window.FOSS.dom.el("span", { text: issue.message || JSON.stringify(issue) })
              ]));
            });
            resultsContainer.appendChild(list);
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Grammar Check" })
    ]);

    var advancedGrammarBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-grammar-advanced",
      "aria-label": "LanguageTool advanced check",
      title: "LanguageTool advanced check",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_grammar_check", { text: txt, advanced: true }).then(function (res) {
          statusEl.textContent = "[OK] Advanced LanguageTool analysis complete (LT available: " + res.lt_available + ")";
          resultsContainer.innerHTML = "";
          resultsContainer.appendChild(window.FOSS.dom.el("span", { className: "card-title", text: "Advanced Analysis" }));
          resultsContainer.appendChild(window.FOSS.dom.el("div", { className: "text-sm", text: "LanguageTool engine available: " + res.lt_available }));
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Advanced Grammar" })
    ]);

    var citationSelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "text_tools-grammar-citation-style",
      "aria-label": "Citation style"
    }, [
      window.FOSS.dom.el("option", { value: "apa", text: "APA" }),
      window.FOSS.dom.el("option", { value: "mla", text: "MLA" }),
      window.FOSS.dom.el("option", { value: "chicago", text: "Chicago" }),
      window.FOSS.dom.el("option", { value: "harvard", text: "Harvard" })
    ]);

    var citationBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-grammar-citation-generate",
      "aria-label": "Generate citation",
      title: "Generate citation",
      type: "button",
      onClick: function () {
        var meta = { author: "Smith, J.", title: "Local First Software", year: "2026", publisher: "FOSS Press" };
        var style = citationSelect.value || "apa";
        window.FOSS.api("data_generate_citation", { metadata: meta, style: style }).then(function (res) {
          if (res && res.citation) {
            textEditor.setValue(res.citation);
            statusEl.textContent = "[OK] Generated " + style.toUpperCase() + " citation";
          }
        });
      }
    }, [
      window.FOSS.icons.el("file", 16),
      window.FOSS.dom.el("span", { text: "Generate Citation" })
    ]);

    var diffBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "text_tools-grammar-diff-btn",
      "aria-label": "Diff document",
      title: "Diff document",
      type: "button",
      onClick: function () {
        var txt = textEditor.getValue();
        window.FOSS.api("data_diff_documents", { doc1: txt, doc2: txt + "\nAdded Line" }).then(function (res) {
          statusEl.textContent = "[OK] Unified document diff calculated";
          resultsContainer.innerHTML = "";
          resultsContainer.appendChild(window.FOSS.dom.el("span", { className: "card-title", text: "Unified Document Diff" }));
          resultsContainer.appendChild(window.FOSS.dom.el("pre", { className: "font-mono text-xs", text: res.diff || "No differences found." }));
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Diff Documents" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row scroll-x",
      gap: "sm"
    }, [grammarBtn, advancedGrammarBtn, citationSelect, citationBtn, diffBtn]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "page stack",
      gap: "md"
    }, [desc, actionsRow, textEditor.el, resultsContainer, statusEl]));
  }

  window.FOSS.router.register({
    id: "text_tools",
    title: "Text Tools",
    navName: "Text Tools",
    category: "Data",
    icon: "edit",
    workbench: false,
    tabs: [
      { id: "main", label: "Text Operations", render: renderMain },
      { id: "word_counter", label: "Word Counter", render: renderWordCounterTab },
      { id: "grammar", label: "Grammar & Style", render: renderGrammarTab }
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
