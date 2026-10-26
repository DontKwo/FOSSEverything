// Batch File Renamer workspace: regex, numbering, casing, prefixes, templates, collision safety.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-renamer");

    var currentFiles = [];
    var lastExecutionResults = [];

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Batch File Renamer" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Rename groups of files with regex, sequential numbers, prefixes, or case transforms."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "renamer-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "renamer-error-banner"
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

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "renamer-result"
    });

    function showResultCard(titleText, summaryPath) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "renamer-result-card",
        title: titleText,
        outputPath: summaryPath || (currentFiles.length ? currentFiles[0] : "")
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Top Toolbar: file selection, clear, timeline
    var toolbarCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var filesInfo = window.FOSS.dom.el("div", {
      className: "text-sm text-muted grow",
      "data-testid": "renamer-files-info",
      "data-truncate-ok": "true",
      title: "No files loaded. Click browse to add files.",
      text: "No files loaded. Click browse to add files."
    });

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "renamer-choose-files",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        chooseFilesAction();
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-clear-btn",
      "aria-label": "Clear",
      title: "Clear",
      type: "button",
      onClick: function () {
        currentFiles = [];
        lastExecutionResults = [];
        undoBtn.disabled = true;
        filesInfo.textContent = "No files loaded. Click browse to add files.";
        filesInfo.title = "No files loaded. Click browse to add files.";
        resultHost.classList.add("hidden");
        clearError();
        updatePreview();
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var timelineCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-timeline-checkbox",
      className: "checkbox",
      "data-testid": "renamer-timeline-check",
      "aria-label": "Order files by capture date/time across all folders (timeline mode)",
      title: "Order files by capture date/time across all folders (timeline mode)",
      onChange: function () {
        updatePreview();
      }
    });

    var timelineLabel = window.FOSS.dom.el("label", {
      htmlFor: "renamer-timeline-checkbox",
      className: "flex items-center gap-2 text-sm cursor-pointer"
    }, [
      timelineCheck,
      window.FOSS.dom.el("span", {
        text: "Order files by capture date/time across all folders (timeline mode)"
      })
    ]);

    var toolbarActions = window.FOSS.dom.el("div", {
      className: "row"
    }, [browseBtn, clearBtn]);

    toolbarCard.appendChild(window.FOSS.dom.el("div", {
      className: "flex items-center justify-between flex-wrap gap-3"
    }, [filesInfo, toolbarActions]));
    toolbarCard.appendChild(timelineLabel);

    // Card 1: Renaming rules
    var rulesCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    rulesCard.appendChild(window.FOSS.dom.el("h3", {
      className: "card-title text-base",
      text: "Renaming rules"
    }));

    var modeSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "renamer-mode-select",
      "aria-label": "Action mode",
      title: "Action mode",
      onChange: function () {
        renderModeOptions();
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "find_replace", text: "find and replace" }),
      window.FOSS.dom.el("option", { value: "numbering", text: "numbering sequence" }),
      window.FOSS.dom.el("option", { value: "prefix_suffix", text: "add prefix / suffix" }),
      window.FOSS.dom.el("option", { value: "change_case", text: "change letter case" }),
      window.FOSS.dom.el("option", { value: "extension", text: "change extension" }),
      window.FOSS.dom.el("option", { value: "template", text: "template" })
    ]);

    var modeRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Action mode" }),
      modeSelect
    ]);
    rulesCard.appendChild(modeRow);

    var modeOptionsContainer = window.FOSS.dom.el("div", { className: "flex-col gap-3" });
    rulesCard.appendChild(modeOptionsContainer);

    // Options elements
    var findInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-find-input",
      "aria-label": "Text or regular expression to find",
      title: "Text or regular expression to find",
      placeholder: "text or regular expression to find",
      onInput: updatePreview
    });

    var replaceInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-replace-input",
      "aria-label": "Replacement text (can use $1 or \\1 for regex groups)",
      title: "Replacement text (can use $1 or \\1 for regex groups)",
      placeholder: "replacement text (can use $1 or \\1 for regex groups)",
      onInput: updatePreview
    });

    var regexCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-regex-checkbox",
      className: "checkbox",
      "data-testid": "renamer-regex-check",
      "aria-label": "use regular expressions (regex)",
      title: "use regular expressions (regex)",
      onChange: updatePreview
    });

    var caseCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-case-checkbox",
      className: "checkbox",
      "data-testid": "renamer-case-check",
      "aria-label": "case sensitive",
      title: "case sensitive",
      checked: true,
      onChange: updatePreview
    });

    var extCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-ext-checkbox",
      className: "checkbox",
      "data-testid": "renamer-ext-check",
      "aria-label": "include extension in match",
      title: "include extension in match",
      onChange: updatePreview
    });

    var startNumInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-24",
      "data-testid": "renamer-numbering-start",
      "aria-label": "Start number",
      title: "Start number",
      value: 1,
      min: 0,
      onInput: updatePreview
    });

    var paddingInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-24",
      "data-testid": "renamer-padding-input",
      "aria-label": "Padding",
      title: "Padding",
      value: 3,
      min: 1,
      max: 10,
      onInput: updatePreview
    });

    var stepInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-24",
      "data-testid": "renamer-step-input",
      "aria-label": "Step",
      title: "Step",
      value: 1,
      min: 1,
      onInput: updatePreview
    });

    var appendCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-append-checkbox",
      className: "checkbox",
      "data-testid": "renamer-append-check",
      "aria-label": "append number to original filename (instead of replacing it)",
      title: "append number to original filename (instead of replacing it)",
      onChange: updatePreview
    });

    var prefixInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-prefix-input",
      "aria-label": "Prefix text",
      title: "Prefix text",
      placeholder: "Prefix text",
      onInput: updatePreview
    });

    var suffixInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-suffix-input",
      "aria-label": "Suffix text",
      title: "Suffix text",
      placeholder: "Suffix text",
      onInput: updatePreview
    });

    var casingSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "renamer-casing-select",
      "aria-label": "Change letter case",
      title: "Change letter case",
      onChange: updatePreview
    }, [
      window.FOSS.dom.el("option", { value: "lower", text: "lowercase (e.g. myfile.png)" }),
      window.FOSS.dom.el("option", { value: "upper", text: "uppercase (e.g. myfile.png)" }),
      window.FOSS.dom.el("option", { value: "title", text: "title case (e.g. my file.png)" }),
      window.FOSS.dom.el("option", { value: "sentence", text: "sentence case (e.g. my file.png)" })
    ]);

    var extCaseCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "renamer-ext-case-checkbox",
      className: "checkbox",
      "data-testid": "renamer-ext-case-check",
      "aria-label": "apply case change to file extensions too",
      title: "apply case change to file extensions too",
      onChange: updatePreview
    });

    var extensionInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-extension-input",
      "aria-label": "Change extension",
      title: "Change extension",
      placeholder: "e.g. jpeg, webp, bak",
      onInput: updatePreview
    });

    var templateInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow",
      "data-testid": "renamer-template-input",
      "aria-label": "Metadata rename template",
      title: "Metadata rename template",
      placeholder: "{date}_{camera}_{stem}",
      value: "{stem}",
      onInput: updatePreview
    });

    function renderModeOptions() {
      modeOptionsContainer.innerHTML = "";
      var mode = modeSelect.value;

      if (mode === "find_replace") {
        var rowInputs = window.FOSS.dom.el("div", { className: "flex flex-wrap gap-2" }, [
          findInput,
          replaceInput
        ]);
        var checksRow = window.FOSS.dom.el("div", { className: "flex items-center flex-wrap gap-4 text-sm" }, [
          window.FOSS.dom.el("label", { htmlFor: "renamer-regex-checkbox", className: "flex items-center gap-2 cursor-pointer" }, [
            regexCheck,
            window.FOSS.dom.el("span", { text: "use regular expressions (regex)" })
          ]),
          window.FOSS.dom.el("label", { htmlFor: "renamer-case-checkbox", className: "flex items-center gap-2 cursor-pointer" }, [
            caseCheck,
            window.FOSS.dom.el("span", { text: "case sensitive" })
          ]),
          window.FOSS.dom.el("label", { htmlFor: "renamer-ext-checkbox", className: "flex items-center gap-2 cursor-pointer" }, [
            extCheck,
            window.FOSS.dom.el("span", { text: "include extension in match" })
          ])
        ]);
        modeOptionsContainer.appendChild(rowInputs);
        modeOptionsContainer.appendChild(checksRow);
      } else if (mode === "numbering") {
        var numInputs = window.FOSS.dom.el("div", { className: "flex items-center flex-wrap gap-3 text-sm" }, [
          window.FOSS.dom.el("label", { className: "flex items-center gap-2" }, [
            window.FOSS.dom.el("span", { className: "text-muted", text: "Start number" }),
            startNumInput
          ]),
          window.FOSS.dom.el("label", { className: "flex items-center gap-2" }, [
            window.FOSS.dom.el("span", { className: "text-muted", text: "Padding" }),
            paddingInput
          ]),
          window.FOSS.dom.el("label", { className: "flex items-center gap-2" }, [
            window.FOSS.dom.el("span", { className: "text-muted", text: "Step" }),
            stepInput
          ])
        ]);
        var numFixes = window.FOSS.dom.el("div", { className: "flex flex-wrap gap-2" }, [
          prefixInput,
          suffixInput
        ]);
        var numCheckRow = window.FOSS.dom.el("div", { className: "flex items-center gap-2 text-sm" }, [
          window.FOSS.dom.el("label", { htmlFor: "renamer-append-checkbox", className: "flex items-center gap-2 cursor-pointer" }, [
            appendCheck,
            window.FOSS.dom.el("span", { text: "append number to original filename (instead of replacing it)" })
          ])
        ]);
        modeOptionsContainer.appendChild(numInputs);
        modeOptionsContainer.appendChild(numFixes);
        modeOptionsContainer.appendChild(numCheckRow);
      } else if (mode === "prefix_suffix") {
        var fixRow = window.FOSS.dom.el("div", { className: "flex flex-wrap gap-2" }, [
          prefixInput,
          suffixInput
        ]);
        modeOptionsContainer.appendChild(fixRow);
      } else if (mode === "change_case") {
        var caseRow = window.FOSS.dom.el("div", { className: "flex items-center flex-wrap gap-3 text-sm" }, [
          casingSelect,
          window.FOSS.dom.el("label", { htmlFor: "renamer-ext-case-checkbox", className: "flex items-center gap-2 cursor-pointer" }, [
            extCaseCheck,
            window.FOSS.dom.el("span", { text: "apply case change to file extensions too" })
          ])
        ]);
        modeOptionsContainer.appendChild(caseRow);
      } else if (mode === "extension") {
        var extRow = window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
          extensionInput
        ]);
        modeOptionsContainer.appendChild(extRow);
      } else if (mode === "template") {
        var tempRow = window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
          templateInput
        ]);
        var tokensHint = window.FOSS.dom.el("div", {
          className: "text-xs text-muted",
          text: "Available tokens: {stem}, {original}, {ext}, {date}, {time}, {year}, {camera}, {artist}, {title}, {album}"
        });
        modeOptionsContainer.appendChild(tempRow);
        modeOptionsContainer.appendChild(tokensHint);
      }
    }

    renderModeOptions();

    // Presets Row
    var presetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "renamer-preset-select",
      "aria-label": "Choose preset",
      title: "Choose preset",
      onChange: function () {
        if (!presetSelect.value) return;
        var mode = presetSelect.value;
        modeSelect.value = mode;
        renderModeOptions();
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "", text: "choose preset" }),
      window.FOSS.dom.el("option", { value: "", text: "saved presets" }),
      window.FOSS.dom.el("option", { value: "find_replace", text: "Find and Replace clean" }),
      window.FOSS.dom.el("option", { value: "numbering", text: "Sequential 3-digit numbering" }),
      window.FOSS.dom.el("option", { value: "change_case", text: "Lowercase normalization" })
    ]);

    var presetNameInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "aria-label": "Preset name",
      title: "Preset name",
      placeholder: "Preset name"
    });

    var savePresetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm shrink-0",
      "data-testid": "renamer-save-preset-btn",
      "aria-label": "Save preset",
      title: "Save preset",
      type: "button",
      onClick: function () {
        var name = presetNameInput.value.trim() || "Preset 1";
        window.FOSS.api("renamer_save_preset", {
          preset_name: name,
          mode: modeSelect.value,
          options: calcGatherOptions()
        }).then(function (res) {
          if (res && res.saved) {
            statusBar.textContent = "Saved preset: " + name;
            var opt = window.FOSS.dom.el("option", { value: modeSelect.value, text: name });
            presetSelect.appendChild(opt);
          }
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save preset" })
    ]);

    var presetControls = window.FOSS.dom.el("div", {
      className: "row pt-2 border-t border-border"
    }, [presetSelect, presetNameInput, savePresetBtn]);
    rulesCard.appendChild(presetControls);

    // Card 2: Cross-folder rename planning
    var crossCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    crossCard.appendChild(window.FOSS.dom.el("h3", {
      className: "card-title text-base",
      text: "Cross-folder rename planning"
    }));

    var consolidateInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "renamer-consolidate-input",
      "aria-label": "Consolidate destination folder",
      "data-truncate-ok": "true",
      title: "optional: consolidate renamed files from every source folder here",
      placeholder: "optional: consolidate renamed files from every source folder here",
      onInput: updatePreview
    });

    var chooseFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm shrink-0",
      "aria-label": "Browse",
      title: "Browse destination folder",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            consolidateInput.value = res.paths[0];
            consolidateInput.title = res.paths[0];
            updatePreview();
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    var consolidateRow = window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
      consolidateInput,
      chooseFolderBtn
    ]);
    crossCard.appendChild(consolidateRow);

    var planSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "renamer-plan-select",
      "aria-label": "Choose cross-folder plan",
      title: "Choose cross-folder plan"
    }, [
      window.FOSS.dom.el("option", { value: "", text: "choose cross-folder plan" }),
      window.FOSS.dom.el("option", { value: "", text: "saved cross-folder plans" })
    ]);

    var planNameInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "aria-label": "Plan name",
      title: "Plan name",
      placeholder: "Plan name"
    });

    var savePlanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-save-plan-btn",
      "aria-label": "Save as cross-folder plan",
      title: "Save as cross-folder plan",
      type: "button",
      onClick: function () {
        var name = planNameInput.value.trim() || "Batch Plan 1";
        var dirs = calcSourceFolders();
        if (!dirs.length) {
          showError("No source folders loaded for cross-folder plan.");
          return;
        }
        window.FOSS.api("renamer_save_plan", {
          name: name,
          source_folders: dirs,
          mode: modeSelect.value,
          options: calcGatherOptions(),
          target_dir: consolidateInput.value.trim() || null,
          processed_files: currentFiles
        }).then(function (res) {
          if (res && res.plan) {
            statusBar.textContent = "Saved plan: " + name;
            var opt = window.FOSS.dom.el("option", { value: name, text: name });
            planSelect.appendChild(opt);
          }
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save as cross-folder plan" })
    ]);

    var rerunPlanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-rerun-plan-btn",
      "aria-label": "Re-run plan (new files only)",
      title: "Re-run plan (new files only)",
      type: "button",
      onClick: function () {
        var dirs = calcSourceFolders();
        if (!dirs.length) {
          showError("No source folders available to rescan.");
          return;
        }
        window.FOSS.api("renamer_find_new_files", {
          source_folders: dirs,
          processed_files: currentFiles
        }).then(function (res) {
          if (res && res.files) {
            if (res.files.length) {
              currentFiles = currentFiles.concat(res.files);
              filesInfo.textContent = currentFiles.length + " files loaded.";
              filesInfo.title = currentFiles.join(", ");
              statusBar.textContent = "Found " + res.files.length + " new files.";
              updatePreview();
            } else {
              statusBar.textContent = "No new files found in source folders.";
            }
          }
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Re-run plan (new files only)" })
    ]);

    var planControls = window.FOSS.dom.el("div", {
      className: "row pt-2 border-t border-border"
    }, [planSelect, planNameInput, savePlanBtn, rerunPlanBtn]);
    crossCard.appendChild(planControls);

    // Card 3: Live preview (collision-safe)
    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    previewCard.appendChild(window.FOSS.dom.el("h3", {
      className: "card-title text-base",
      text: "Live preview (collision-safe)"
    }));

    var applyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "renamer-apply-btn",
      "aria-label": "Apply renaming plan",
      title: "Apply renaming plan",
      type: "button",
      onClick: function () {
        applyRenamesAction();
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Apply renaming plan" })
    ]);

    var undoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-undo-btn",
      "aria-label": "Undo last rename",
      title: "Undo last rename",
      type: "button",
      disabled: true,
      onClick: function () {
        undoRenamesAction();
      }
    }, [
      window.FOSS.icons.el("undo", 16),
      window.FOSS.dom.el("span", { text: "Undo last rename" })
    ]);

    var previewActions = window.FOSS.dom.el("div", {
      className: "row"
    }, [applyBtn, undoBtn]);

    var tableContainer = window.FOSS.dom.el("div", {
      className: "table-wrap scroll-x",
      "data-testid": "renamer-preview-table"
    });

    previewCard.appendChild(previewActions);
    previewCard.appendChild(tableContainer);

    // Helpers
    function calcGatherOptions() {
      var mode = modeSelect.value;
      if (mode === "find_replace") {
        return {
          find: findInput.value,
          replace: replaceInput.value,
          use_regex: regexCheck.checked,
          case_sensitive: caseCheck.checked,
          include_extension: extCheck.checked
        };
      } else if (mode === "numbering") {
        return {
          start: parseInt(startNumInput.value, 10) || 1,
          padding: parseInt(paddingInput.value, 10) || 3,
          step: parseInt(stepInput.value, 10) || 1,
          prefix: prefixInput.value,
          suffix: suffixInput.value,
          keep_name: appendCheck.checked
        };
      } else if (mode === "prefix_suffix") {
        return {
          prefix: prefixInput.value,
          suffix: suffixInput.value
        };
      } else if (mode === "change_case") {
        return {
          case_type: casingSelect.value,
          affect_ext: extCaseCheck.checked
        };
      } else if (mode === "extension") {
        return {
          new_extension: extensionInput.value
        };
      } else if (mode === "template") {
        return {
          template: templateInput.value || "{stem}"
        };
      }
      return {};
    }

    function calcSourceFolders() {
      var dirs = {};
      for (var i = 0; i < currentFiles.length; i++) {
        var p = currentFiles[i];
        var idx = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"));
        if (idx > 0) {
          dirs[p.substring(0, idx)] = true;
        }
      }
      return Object.keys(dirs);
    }

    function chooseFilesAction() {
      clearError();
      window.FOSS.api("select_files", {}).then(function (res) {
        if (!res || res.cancelled || !res.paths || !res.paths.length) return;
        currentFiles = res.paths;
        filesInfo.textContent = currentFiles.length + " files loaded.";
        filesInfo.title = currentFiles.join(", ");
        updatePreview();
      });
    }

    function updatePreview() {
      if (!currentFiles.length) {
        tableContainer.innerHTML = '<div class="text-sm text-muted p-4 text-center">No files loaded. Click browse to add files.</div>';
        statusBar.textContent = "Ready";
        return;
      }

      var opts = calcGatherOptions();
      window.FOSS.api("renamer_preview", {
        file_paths: currentFiles,
        mode: modeSelect.value,
        timeline: timelineCheck.checked,
        consolidate_to: consolidateInput.value.trim(),
        options: opts
      }).then(function (res) {
        if (!res || !res.entries) {
          tableContainer.innerHTML = '<div class="text-sm text-muted p-4 text-center">Failed to generate preview.</div>';
          return;
        }

        renderPreviewTable(res.entries);
        if (res.has_conflicts) {
          statusBar.textContent = "Warning: collisions or duplicate names detected.";
        } else {
          statusBar.textContent = "Ready: " + res.entries.length + " files planned.";
        }
      });
    }

    function renderPreviewTable(entries) {
      tableContainer.innerHTML = "";
      var tbl = window.FOSS.dom.el("table", { className: "table w-full" });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { className: "w-24 text-left", text: "Status" }),
          window.FOSS.dom.el("th", { className: "text-left", text: "Original Name" }),
          window.FOSS.dom.el("th", { className: "text-left", text: "Proposed Name" }),
          window.FOSS.dom.el("th", { className: "text-left", text: "Path" })
        ])
      ]);
      tbl.appendChild(thead);

      var tbody = window.FOSS.dom.el("tbody", {});
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        var badgeClass = "badge badge-success";
        var badgeText = "OK";
        if (e.has_collision) {
          badgeClass = "badge badge-danger";
          badgeText = e.error || "Collision";
        } else if (e.old_name === e.new_name) {
          badgeClass = "badge badge-neutral";
          badgeText = "Unchanged";
        }

        var badgeEl = window.FOSS.dom.el("span", { className: badgeClass, text: badgeText });
        var origTd = window.FOSS.dom.el("td", {
          className: "font-mono text-sm",
          style: "word-break: break-all;",
          text: e.old_name
        });
        var propTd = window.FOSS.dom.el("td", {
          className: "font-mono text-sm",
          style: "word-break: break-all;",
          text: e.new_name
        });
        var pathTd = window.FOSS.dom.el("td", {
          className: "font-mono text-xs text-muted",
          "data-truncate-ok": "true",
          title: e.original,
          style: "word-break: break-all;",
          text: e.original
        });

        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", {}, [badgeEl]),
          origTd,
          propTd,
          pathTd
        ]);
        tbody.appendChild(tr);
      }
      tbl.appendChild(tbody);
      tableContainer.appendChild(tbl);
    }

    function applyRenamesAction() {
      if (!currentFiles.length) {
        showError("No files loaded to rename.");
        return;
      }
      clearError();
      var opts = calcGatherOptions();
      window.FOSS.api("renamer_execute", {
        file_paths: currentFiles,
        mode: modeSelect.value,
        timeline: timelineCheck.checked,
        consolidate_to: consolidateInput.value.trim(),
        options: opts
      }).then(function (res) {
        if (!res || !res.results) {
          showError("Rename execution failed.");
          return;
        }
        lastExecutionResults = res.results;
        undoBtn.disabled = false;
        var successCount = 0;
        var updatedPaths = [];
        for (var i = 0; i < res.results.length; i++) {
          var r = res.results[i];
          if (r.success) {
            successCount++;
            updatedPaths.push(r.target);
          } else {
            updatedPaths.push(r.original);
          }
        }
        currentFiles = updatedPaths;
        filesInfo.textContent = currentFiles.length + " files loaded.";
        filesInfo.title = currentFiles.join(", ");
        statusBar.textContent = "Renamed " + successCount + " files successfully.";
        showResultCard("Batch Rename Complete", currentFiles[0] || "");
        updatePreview();
      });
    }

    function undoRenamesAction() {
      if (!lastExecutionResults || !lastExecutionResults.length) {
        showError("No rename operations to undo.");
        return;
      }
      clearError();
      window.FOSS.api("renamer_undo", {
        results: lastExecutionResults
      }).then(function (res) {
        if (!res || !res.results) {
          showError("Undo failed.");
          return;
        }
        lastExecutionResults = [];
        undoBtn.disabled = true;
        var undonePaths = [];
        for (var i = 0; i < res.results.length; i++) {
          undonePaths.push(res.results[i].target);
        }
        currentFiles = undonePaths;
        filesInfo.textContent = currentFiles.length + " files loaded.";
        filesInfo.title = currentFiles.join(", ");
        statusBar.textContent = "Undone rename operations.";
        showResultCard("Undo Completed", currentFiles[0] || "");
        updatePreview();
      });
    }

    // Assemble page
    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(toolbarCard);
    panel.appendChild(rulesCard);
    panel.appendChild(crossCard);
    panel.appendChild(previewCard);

    updatePreview();
  }

  window.FOSS.router.register({
    id: "renamer",
    title: "Batch File Renamer",
    navName: "Renamer",
    category: "system",
    icon: "folder",
    tabs: [
      { id: "main", label: "Renamer", render: renderMain }
    ]
  });
})();
