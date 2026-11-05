// Batch File Renamer workspace: visual composable step engine, live preview, zero regex.
window.FOSS = window.FOSS || {};

(function () {
  var pendingPaths = [];

  function renderMain(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "renamer-page");

    var currentFiles = [];
    var lastExecutionResults = window.FOSS.store.get("renamer_history_log", []);
    var currentSteps = [
      {
        id: "step_default_1",
        type: "replace_text",
        enabled: true,
        find_text: "",
        replace_with: "",
        match_case: false,
        scope: "all"
      }
    ];
    var isExecuting = false;
    var previewDebounceTimer = null;
    var previewPlans = [];

    // Header & Status Elements
    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "renamer-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
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
      className: "hidden mb-sm",
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

    // Step Definition Helpers
    var STEP_METAS = {
      replace_text: { title: "Replace Text", icon: "edit" },
      add_text: { title: "Add Prefix / Suffix", icon: "file-plus" },
      number_sequence: { title: "Number Sequence", icon: "hash" },
      add_date: { title: "Date Stamp", icon: "calendar" },
      clean_name: { title: "Clean Up Characters", icon: "check" },
      change_case: { title: "Change Case", icon: "type" },
      change_extension: { title: "Change Extension", icon: "file" }
    };

    function createDefaultStep(type) {
      var id = "step_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
      if (type === "add_text") {
        return { id: id, type: type, enabled: true, prefix: "", suffix: "" };
      }
      if (type === "number_sequence") {
        return {
          id: id, type: type, enabled: true, mode: "suffix", base_name: "Photo", start_at: 1, increment: 1,
          padding: window.FOSS.toolDefaults.get("renamer", "number_padding", 2), separator: " - "
        };
      }
      if (type === "add_date") {
        return { id: id, type: type, enabled: true, date_source: "best_date", date_format: "YYYY-MM-DD", position: "prefix", separator: " - " };
      }
      if (type === "clean_name") {
        return { id: id, type: type, enabled: true, spaces: "collapse", remove_brackets: true, remove_digits: false, remove_punctuation: false, trim_first_n: 0, trim_last_n: 0 };
      }
      if (type === "change_case") {
        return { id: id, type: type, enabled: true, case_mode: window.FOSS.toolDefaults.get("renamer", "case_mode", "title") };
      }
      if (type === "change_extension") {
        return { id: id, type: type, enabled: true, extension: "" };
      }
      return { id: id, type: "replace_text", enabled: true, find_text: "", replace_with: "", match_case: false, scope: "all" };
    }

    // Left Column: Step Stack Builder
    var stepsHost = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 grow overflow-y-auto",
      "data-testid": "renamer-steps-list",
      style: "min-height: 0; min-width: 0;"
    });

    var addStepSelect = window.FOSS.dom.el("select", {
      className: "select select-sm grow text-xs font-semibold",
      "data-testid": "renamer-add-step-select",
      "aria-label": "Add Renaming Step",
      title: "Add Renaming Step",
      onChange: function () {
        var val = addStepSelect.value;
        if (!val) return;
        currentSteps.push(createDefaultStep(val));
        addStepSelect.value = "";
        renderSteps();
        schedulePreviewUpdate();
      }
    }, [
      window.FOSS.dom.el("option", { value: "", text: "+ Add Renaming Step..." }),
      window.FOSS.dom.el("option", { value: "replace_text", text: "Replace Text" }),
      window.FOSS.dom.el("option", { value: "add_text", text: "Add Prefix / Suffix" }),
      window.FOSS.dom.el("option", { value: "number_sequence", text: "Number Sequence" }),
      window.FOSS.dom.el("option", { value: "add_date", text: "Date Stamp" }),
      window.FOSS.dom.el("option", { value: "clean_name", text: "Clean Up Characters" }),
      window.FOSS.dom.el("option", { value: "change_case", text: "Change Case" }),
      window.FOSS.dom.el("option", { value: "change_extension", text: "Change Extension" })
    ]);

    var recipeSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs font-semibold",
      "data-testid": "renamer-recipe-select",
      "aria-label": "Load Recipe",
      title: "Load Starter or Saved Recipe",
      style: "width: 10rem;",
      onChange: function () {
        var val = recipeSelect.value;
        if (!val) return;
        applyRecipe(val);
      }
    }, [
      window.FOSS.dom.el("option", { value: "", text: "Recipes..." })
    ]);

    var saveRecipeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-save-recipe-btn",
      "aria-label": "Save Current Steps As Recipe",
      title: "Save Current Steps As Recipe",
      type: "button",
      onClick: function () {
        promptSaveRecipe();
      }
    }, [window.FOSS.icons.el("save", 14), window.FOSS.dom.el("span", { text: "Save Recipe" })]);

    var availableRecipes = [];

    function loadRecipes() {
      window.FOSS.api("renamer_presets", { action: "list" }).then(function (res) {
        if (!res) return;
        var starter = res.starter_recipes || [];
        var user = res.user_recipes || [];
        availableRecipes = starter.concat(user);

        recipeSelect.innerHTML = "";
        recipeSelect.appendChild(window.FOSS.dom.el("option", { value: "", text: "Recipes..." }));

        if (starter.length > 0) {
          var starterGroup = window.FOSS.dom.el("optgroup", { label: "Starter Recipes" });
          starter.forEach(function (r) {
            starterGroup.appendChild(window.FOSS.dom.el("option", { value: r.name, text: r.name }));
          });
          recipeSelect.appendChild(starterGroup);
        }

        if (user.length > 0) {
          var userGroup = window.FOSS.dom.el("optgroup", { label: "Saved Recipes" });
          user.forEach(function (r) {
            userGroup.appendChild(window.FOSS.dom.el("option", { value: r.name, text: r.name }));
          });
          recipeSelect.appendChild(userGroup);
        }
      });
    }

    function applyRecipe(name) {
      var found = availableRecipes.find(function (r) { return r.name === name; });
      if (!found || !found.steps) return;
      currentSteps = found.steps.map(function (s) {
        var copy = JSON.parse(JSON.stringify(s));
        copy.id = "step_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
        return copy;
      });
      recipeSelect.value = "";
      renderSteps();
      schedulePreviewUpdate();
    }

    function promptSaveRecipe() {
      var name = window.prompt("Enter name for this renaming recipe:");
      if (!name || !name.trim()) return;
      window.FOSS.api("renamer_presets", {
        action: "save",
        recipe: {
          name: name.trim(),
          steps: currentSteps
        }
      }).then(function () {
        loadRecipes();
      });
    }

    function renderSteps() {
      stepsHost.innerHTML = "";
      if (currentSteps.length === 0) {
        stepsHost.appendChild(window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-4 text-center font-mono",
          text: "No renaming steps added. Click Add Renaming Step above."
        }));
        return;
      }

      currentSteps.forEach(function (step, index) {
        var meta = STEP_METAS[step.type] || { title: "Step " + (index + 1), icon: "edit" };
        var card = window.FOSS.dom.el("div", {
          className: "renamer-step-card" + (step.enabled ? "" : " disabled"),
          "data-testid": "renamer-step-" + index,
          draggable: "true"
        });

        card.ondragstart = function (e) {
          e.dataTransfer.setData("application/json", JSON.stringify({ type: "renamer-step", index: index }));
          card.classList.add("dragging");
        };
        card.ondragend = function (e) {
          card.classList.remove("dragging");
        };
        card.ondragover = function (e) {
          e.preventDefault();
          card.classList.add("renamer-drag-over");
        };
        card.ondragleave = function (e) {
          card.classList.remove("renamer-drag-over");
        };
        card.ondrop = function (e) {
          e.preventDefault();
          card.classList.remove("renamer-drag-over");
          try {
            var data = JSON.parse(e.dataTransfer.getData("application/json"));
            if (data.type === "renamer-step" && data.index !== index) {
              var draggedItem = currentSteps.splice(data.index, 1)[0];
              currentSteps.splice(index, 0, draggedItem);
              renderSteps();
              schedulePreviewUpdate();
            }
          } catch (err) {}
        };

        // Top bar: badge, up, down, enable switch, remove
        var enableCheckbox = window.FOSS.dom.el("input", {
          type: "checkbox",
          checked: step.enabled,
          "aria-label": "Enable " + meta.title,
          title: "Enable or disable step",
          onChange: function () {
            step.enabled = enableCheckbox.checked;
            if (step.enabled) {
              card.classList.remove("disabled");
            } else {
              card.classList.add("disabled");
            }
            schedulePreviewUpdate();
          }
        });

        var upBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          disabled: index === 0,
          "aria-label": "Move Step Up",
          title: "Move Step Up",
          type: "button",
          onClick: function () {
            if (index > 0) {
              var temp = currentSteps[index - 1];
              currentSteps[index - 1] = currentSteps[index];
              currentSteps[index] = temp;
              renderSteps();
              schedulePreviewUpdate();
            }
          }
        }, [window.FOSS.icons.el("chevron-up", 14)]);

        var downBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          disabled: index === currentSteps.length - 1,
          "aria-label": "Move Step Down",
          title: "Move Step Down",
          type: "button",
          onClick: function () {
            if (index < currentSteps.length - 1) {
              var temp = currentSteps[index + 1];
              currentSteps[index + 1] = currentSteps[index];
              currentSteps[index] = temp;
              renderSteps();
              schedulePreviewUpdate();
            }
          }
        }, [window.FOSS.icons.el("chevron-down", 14)]);

        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Remove Step",
          title: "Remove Step",
          type: "button",
          onClick: function () {
            currentSteps.splice(index, 1);
            renderSteps();
            schedulePreviewUpdate();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        var gripHandle = window.FOSS.dom.el("span", {
          className: "text-muted",
          style: "cursor: grab; display: inline-flex; align-items: center;",
          "aria-hidden": "true"
        }, [window.FOSS.icons.el("grip", 14)]);

        var cardHeader = window.FOSS.dom.el("div", {
          className: "row gap-2 items-center justify-between"
        }, [
          window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
            gripHandle,
            window.FOSS.icons.el(meta.icon, 14),
            window.FOSS.dom.el("span", {
              className: "font-semibold text-xs",
              text: (index + 1) + ". " + meta.title
            })
          ]),
          window.FOSS.dom.el("div", { className: "row gap-1 items-center" }, [
            upBtn,
            downBtn,
            enableCheckbox,
            removeBtn
          ])
        ]);

        card.appendChild(cardHeader);

        // Controls by Type
        var bodyControls = window.FOSS.dom.el("div", { className: "flex-col gap-2" });

        if (step.type === "replace_text") {
          var findInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            "data-testid": "renamer-step-find-" + index,
            placeholder: "Find exact text...",
            value: step.find_text || "",
            "aria-label": "Text to find",
            title: "Text to find",
            onInput: function () {
              step.find_text = findInp.value;
              schedulePreviewUpdate();
            }
          });

          var repInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            "data-testid": "renamer-step-replace-" + index,
            placeholder: "Replace with...",
            value: step.replace_with || "",
            "aria-label": "Replacement text",
            title: "Replacement text",
            onInput: function () {
              step.replace_with = repInp.value;
              schedulePreviewUpdate();
            }
          });

          var scopeSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Match scope",
            title: "Match scope",
            onChange: function () {
              step.scope = scopeSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "all", text: "All occurrences" }),
            window.FOSS.dom.el("option", { value: "first", text: "First only" }),
            window.FOSS.dom.el("option", { value: "last", text: "Last only" })
          ]);
          scopeSel.value = step.scope || "all";

          var caseChk = window.FOSS.dom.el("input", {
            type: "checkbox",
            checked: !!step.match_case,
            "aria-label": "Match case sensitive",
            title: "Case sensitive matching",
            onChange: function () {
              step.match_case = caseChk.checked;
              schedulePreviewUpdate();
            }
          });

          bodyControls.appendChild(window.FOSS.components.field("Find Text", findInp));
          bodyControls.appendChild(window.FOSS.components.field("Replace With", repInp));
          bodyControls.appendChild(window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
            window.FOSS.dom.el("label", { className: "text-xs text-muted", text: "Scope" }),
            scopeSel,
            window.FOSS.dom.el("label", { className: "text-xs text-muted row gap-1 items-center" }, [
              caseChk,
              window.FOSS.dom.el("span", { text: "Match Case" })
            ])
          ]));
        } else if (step.type === "add_text") {
          var prefixInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            "data-testid": "renamer-step-prefix-" + index,
            placeholder: "e.g. Wedding - ",
            value: step.prefix || "",
            "aria-label": "Prefix to prepend",
            title: "Prefix to prepend",
            onInput: function () {
              step.prefix = prefixInp.value;
              schedulePreviewUpdate();
            }
          });

          var suffixInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            "data-testid": "renamer-step-suffix-" + index,
            placeholder: "e.g. - reviewed",
            value: step.suffix || "",
            "aria-label": "Suffix to append",
            title: "Suffix to append",
            onInput: function () {
              step.suffix = suffixInp.value;
              schedulePreviewUpdate();
            }
          });

          bodyControls.appendChild(window.FOSS.components.field("Add Prefix", prefixInp));
          bodyControls.appendChild(window.FOSS.components.field("Add Suffix", suffixInp));
        } else if (step.type === "number_sequence") {
          var numModeSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Number position mode",
            title: "Number position mode",
            onChange: function () {
              step.mode = numModeSel.value;
              baseField.classList.toggle("hidden", step.mode !== "replace_name");
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "suffix", text: "Suffix: name - 01" }),
            window.FOSS.dom.el("option", { value: "prefix", text: "Prefix: 01 - name" }),
            window.FOSS.dom.el("option", { value: "replace_name", text: "Replace Name: Photo - 01" })
          ]);
          numModeSel.value = step.mode || "suffix";

          var baseInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            placeholder: "Base name (e.g. Vacation)",
            value: step.base_name || "",
            "aria-label": "Base Filename",
            title: "Base Filename",
            onInput: function () {
              step.base_name = baseInp.value;
              schedulePreviewUpdate();
            }
          });

          var baseField = window.FOSS.components.field("Base Filename", baseInp);
          if (step.mode !== "replace_name") {
            baseField.classList.add("hidden");
          }

          var startInp = window.FOSS.dom.el("input", {
            type: "number",
            className: "input input-sm font-mono text-xs",
            value: String(step.start_at || 1),
            min: "0",
            "aria-label": "Start Number",
            title: "Start Number",
            onChange: function () {
              step.start_at = parseInt(startInp.value, 10) || 1;
              schedulePreviewUpdate();
            }
          });

          var padSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Number Digits Padding",
            title: "Number Digits Padding",
            onChange: function () {
              step.padding = parseInt(padSel.value, 10) || 2;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "1", text: "1 (1, 2, 3)" }),
            window.FOSS.dom.el("option", { value: "2", text: "2 (01, 02)" }),
            window.FOSS.dom.el("option", { value: "3", text: "3 (001, 002)" }),
            window.FOSS.dom.el("option", { value: "4", text: "4 (0001, 0002)" }),
            window.FOSS.dom.el("option", { value: "5", text: "5 (00001, 00002)" }),
            window.FOSS.dom.el("option", { value: "6", text: "6 (000001, 000002)" })
          ]);
          padSel.value = String(step.padding || 2);

          var sepSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Number Separator",
            title: "Number Separator",
            onChange: function () {
              step.separator = sepSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: " - ", text: " - (hyphen space)" }),
            window.FOSS.dom.el("option", { value: "_", text: "_ (underscore)" }),
            window.FOSS.dom.el("option", { value: " ", text: "  (space)" }),
            window.FOSS.dom.el("option", { value: ".", text: ". (dot)" }),
            window.FOSS.dom.el("option", { value: "", text: "(none)" })
          ]);
          sepSel.value = step.separator !== undefined ? step.separator : " - ";

          bodyControls.appendChild(window.FOSS.components.field("Numbering Placement", numModeSel));
          bodyControls.appendChild(baseField);
          bodyControls.appendChild(window.FOSS.dom.el("div", { className: "row gap-2" }, [
            window.FOSS.dom.el("div", { className: "grow flex-col gap-1" }, [
              window.FOSS.dom.el("label", { className: "text-xs text-muted", text: "Start At" }),
              startInp
            ]),
            window.FOSS.dom.el("div", { className: "grow flex-col gap-1" }, [
              window.FOSS.dom.el("label", { className: "text-xs text-muted", text: "Digits" }),
              padSel
            ]),
            window.FOSS.dom.el("div", { className: "grow flex-col gap-1" }, [
              window.FOSS.dom.el("label", { className: "text-xs text-muted", text: "Separator" }),
              sepSel
            ])
          ]));
        } else if (step.type === "add_date") {
          var dateSrcSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Date Source",
            title: "Date Source",
            onChange: function () {
              step.date_source = dateSrcSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "best_date", text: "Best (Photo EXIF or File Date)" }),
            window.FOSS.dom.el("option", { value: "modified", text: "File Modified Date" }),
            window.FOSS.dom.el("option", { value: "created", text: "File Created Date" })
          ]);
          dateSrcSel.value = step.date_source || "best_date";

          var dateFmtSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs font-mono",
            "aria-label": "Date Format",
            title: "Date Format",
            onChange: function () {
              step.date_format = dateFmtSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "YYYY-MM-DD", text: "YYYY-MM-DD (2026-10-31)" }),
            window.FOSS.dom.el("option", { value: "YYYYMMDD", text: "YYYYMMDD (20261031)" }),
            window.FOSS.dom.el("option", { value: "YYYY-MM-DD HH-mm", text: "YYYY-MM-DD HH-mm" }),
            window.FOSS.dom.el("option", { value: "MM-DD-YYYY", text: "MM-DD-YYYY" }),
            window.FOSS.dom.el("option", { value: "YYYY-MM", text: "YYYY-MM" })
          ]);
          dateFmtSel.value = step.date_format || "YYYY-MM-DD";

          var datePosSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Date Position",
            title: "Date Position",
            onChange: function () {
              step.position = datePosSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "prefix", text: "Prefix (2026-10-31 - name)" }),
            window.FOSS.dom.el("option", { value: "suffix", text: "Suffix (name - 2026-10-31)" })
          ]);
          datePosSel.value = step.position || "prefix";

          bodyControls.appendChild(window.FOSS.components.field("Date Source", dateSrcSel));
          bodyControls.appendChild(window.FOSS.components.field("Date Format", dateFmtSel));
          bodyControls.appendChild(window.FOSS.components.field("Position", datePosSel));
        } else if (step.type === "clean_name") {
          var spaceSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Space handling",
            title: "Space handling",
            onChange: function () {
              step.spaces = spaceSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "collapse", text: "Collapse Multiple Spaces" }),
            window.FOSS.dom.el("option", { value: "to_underscores", text: "Convert Spaces to Underscores" }),
            window.FOSS.dom.el("option", { value: "to_hyphens", text: "Convert Spaces to Hyphens" }),
            window.FOSS.dom.el("option", { value: "remove", text: "Remove All Spaces" }),
            window.FOSS.dom.el("option", { value: "keep", text: "Keep Spaces Unchanged" })
          ]);
          spaceSel.value = step.spaces || "collapse";

          var bracketsChk = window.FOSS.dom.el("input", {
            type: "checkbox",
            checked: !!step.remove_brackets,
            "aria-label": "Remove Brackets",
            title: "Remove (...) and [...]",
            onChange: function () {
              step.remove_brackets = bracketsChk.checked;
              schedulePreviewUpdate();
            }
          });

          var punctChk = window.FOSS.dom.el("input", {
            type: "checkbox",
            checked: !!step.remove_punctuation,
            "aria-label": "Remove Punctuation",
            title: "Remove Punctuation symbols",
            onChange: function () {
              step.remove_punctuation = punctChk.checked;
              schedulePreviewUpdate();
            }
          });

          bodyControls.appendChild(window.FOSS.components.field("Whitespace Options", spaceSel));
          bodyControls.appendChild(window.FOSS.dom.el("div", { className: "row gap-4 flex-wrap" }, [
            window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center" }, [
              bracketsChk,
              window.FOSS.dom.el("span", { text: "Strip Brackets (..)" })
            ]),
            window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center" }, [
              punctChk,
              window.FOSS.dom.el("span", { text: "Remove Punctuation" })
            ])
          ]));
        } else if (step.type === "change_case") {
          var caseSel = window.FOSS.dom.el("select", {
            className: "select select-sm text-xs",
            "aria-label": "Case Mode",
            title: "Case Mode",
            onChange: function () {
              step.case_mode = caseSel.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "title", text: "Title Case (Song Title)" }),
            window.FOSS.dom.el("option", { value: "lower", text: "lowercase (web-safe)" }),
            window.FOSS.dom.el("option", { value: "upper", text: "UPPERCASE" }),
            window.FOSS.dom.el("option", { value: "sentence", text: "Sentence case" }),
            window.FOSS.dom.el("option", { value: "snake", text: "snake_case" }),
            window.FOSS.dom.el("option", { value: "kebab", text: "kebab-case" })
          ]);
          caseSel.value = step.case_mode || "title";
          bodyControls.appendChild(window.FOSS.components.field("Capitalization Style", caseSel));
        } else if (step.type === "change_extension") {
          var extInp = window.FOSS.dom.el("input", {
            type: "text",
            className: "input input-sm font-mono text-xs",
            placeholder: "e.g. jpg, png, md",
            value: step.extension || "",
            "aria-label": "New Extension",
            title: "New Extension",
            onInput: function () {
              step.extension = extInp.value;
              schedulePreviewUpdate();
            }
          });
          bodyControls.appendChild(window.FOSS.components.field("New File Extension", extInp));
        }

        card.appendChild(bodyControls);
        stepsHost.appendChild(card);
      });
    }

    var sidebarCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-height: 0; min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
        window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Renaming Steps" }),
        recipeSelect
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
        addStepSelect,
        saveRecipeBtn
      ]),
      stepsHost
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "renamer-sidebar-pane",
      style: "width: 100%; min-width: 0;"
    }, [sidebarCard]);

    // Right Column: File List & Live Before -> After Preview
    var handleAddFiles = function () {
      clearError();
      window.FOSS.api("select_files", { title: "Select Files to Rename" }).then(function (res) {
        if (!res || res.cancelled || !res.paths || !res.paths.length) return;
        addFiles(res.paths);
      });
    };

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-add-files-btn",
      "aria-label": "Add Files",
      title: "Add Files",
      type: "button",
      onClick: handleAddFiles
    }, [window.FOSS.icons.el("file-plus", 14), window.FOSS.dom.el("span", { text: "Add Files..." })]);

    var addFilesBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-choose-files",
      "aria-label": "Choose Files",
      title: "Choose Files",
      type: "button",
      onClick: handleAddFiles
    }, [window.FOSS.icons.el("file-plus", 14), window.FOSS.dom.el("span", { text: "Choose Files..." })]);

    var addFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "renamer-add-folder-btn",
      "aria-label": "Add Folder",
      title: "Add Folder",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", { title: "Select Folder to Rename" }).then(function (res) {
          if (!res || res.cancelled || !res.path) return;
          window.FOSS.api("renamer_scan_inputs", {
            paths: [res.path],
            recursive: recursiveCheck.checked
          }).then(function (scanRes) {
            if (scanRes && scanRes.paths) {
              addFiles(scanRes.paths);
            }
          });
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Add Folder..." })]);

    var recursiveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "renamer-recursive",
      "aria-label": "Include Subfolders",
      title: "Include Subfolders"
    });

    var sortSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs font-semibold",
      "data-testid": "renamer-sort-select",
      "aria-label": "Sort Order",
      title: "Sort Order",
      onChange: function () {
        schedulePreviewUpdate();
      }
    }, [
      window.FOSS.dom.el("option", { value: "name_asc", text: "Sort: Name (A to Z)" }),
      window.FOSS.dom.el("option", { value: "name_desc", text: "Sort: Name (Z to A)" }),
      window.FOSS.dom.el("option", { value: "date_asc", text: "Sort: Date (Oldest First)" }),
      window.FOSS.dom.el("option", { value: "date_desc", text: "Sort: Date (Newest First)" }),
      window.FOSS.dom.el("option", { value: "size_asc", text: "Sort: Size (Smallest)" }),
      window.FOSS.dom.el("option", { value: "size_desc", text: "Sort: Size (Largest)" })
    ]);

    // Timeline checkbox alias for automated scenarios
    var timelineCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "renamer-timeline-check",
      "aria-label": "Sort Timeline",
      title: "Sort Timeline",
      onChange: function () {
        if (timelineCheck.checked) {
          sortSelect.value = "date_asc";
        } else {
          sortSelect.value = "name_asc";
        }
        schedulePreviewUpdate();
      }
    });

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "renamer-clear-btn",
      "aria-label": "Clear Files",
      title: "Clear Files",
      type: "button",
      onClick: function () {
        currentFiles = [];
        previewPlans = [];
        clearError();
        renderPreviewTable();
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    function addFiles(paths) {
      paths.forEach(function (p) {
        if (currentFiles.indexOf(p) === -1) {
          currentFiles.push(p);
        }
      });
      statusBar.textContent = currentFiles.length + " file(s) loaded.";
      schedulePreviewUpdate();
    }

    // Live Before -> After Table
    var tableHost = window.FOSS.dom.el("div", {
      className: "table-wrap grow flex-col gap-2",
      "data-testid": "renamer-preview-table",
      style: "min-width: 0; width: 100%; box-sizing: border-box;"
    });

    var summaryText = window.FOSS.dom.el("div", {
      className: "text-xs font-mono text-muted",
      "data-testid": "renamer-summary",
      text: "0 files ready"
    });

    var autoResolveCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "renamer-auto-resolve-conflicts",
      "aria-label": "Auto-resolve duplicate names with (2), (3)",
      title: "Auto-resolve duplicate names with (2), (3)",
      onChange: function () {
        schedulePreviewUpdate();
      }
    });

    var undoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary font-semibold",
      "data-testid": "renamer-undo-btn",
      title: "Reverse the most recent batch rename",
      disabled: !(lastExecutionResults && lastExecutionResults.length > 0),
      type: "button",
      onClick: function () {
        executeUndo();
      }
    }, [window.FOSS.icons.el("rotate-ccw", 14), window.FOSS.dom.el("span", { text: "Undo Last Rename" })]);

    var applyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "renamer-apply-btn",
      type: "button",
      onClick: function () {
        executeRename();
      }
    }, [window.FOSS.icons.el("check", 14), window.FOSS.dom.el("span", { text: "Rename Files" })]);

    function schedulePreviewUpdate() {
      if (previewDebounceTimer) {
        clearTimeout(previewDebounceTimer);
      }
      previewDebounceTimer = setTimeout(function () {
        updatePreview();
      }, 100);
    }

    function updatePreview() {
      if (currentFiles.length === 0) {
        previewPlans = [];
        renderPreviewTable();
        return;
      }

      var autoResolve = autoResolveCheck.checked;
      var request = { file_paths: currentFiles, steps: currentSteps, sort_by: sortSelect.value };
      var calls = [window.FOSS.api("renamer_preview", Object.assign({ auto_resolve_conflicts: autoResolve }, request))];
      if (autoResolve) {
        calls.push(window.FOSS.api("renamer_preview", Object.assign({ auto_resolve_conflicts: false }, request)));
      }
      Promise.all(calls).then(function (responses) {
        var res = responses[0];
        if (!res) return;
        previewPlans = res.entries || [];
        if (responses[1] && responses[1].entries) {
          responses[1].entries.forEach(function (raw, i) {
            if (raw.has_collision && previewPlans[i]) previewPlans[i].renumbered = true;
          });
        }
        renderPreviewTable();
        var conflictCount = previewPlans.filter(function (p) { return p.has_collision; }).length;
        var renumberedCount = previewPlans.filter(function (p) { return p.renumbered; }).length;
        if (conflictCount > 0) {
          summaryText.textContent = previewPlans.length + " files (" + conflictCount + " name collision(s) must be fixed)";
        } else if (renumberedCount > 0) {
          summaryText.textContent = previewPlans.length + " files (" + renumberedCount + " collision(s) auto-numbered)";
        } else {
          summaryText.textContent = previewPlans.length + " file(s) ready to rename";
        }
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    function renderPreviewTable() {
      tableHost.innerHTML = "";
      if (currentFiles.length === 0) {
        var emptyPrompt = window.FOSS.dom.el("div", {
          className: "text-muted text-sm p-6 text-center font-mono flex-col gap-2",
          text: "No files loaded. Click Add Files or Add Folder above."
        }, [
          window.FOSS.dom.el("div", {
            className: "text-xs text-muted font-mono p-2 bg-neutral rounded",
            text: "Rule Preview: IMG_2048 (Copy).JPG -> 2026-10-31 - Hawaii - 01.jpg"
          })
        ]);
        tableHost.appendChild(emptyPrompt);
        summaryText.textContent = "0 files loaded";
        return;
      }

      var rows = previewPlans.map(function (p, idx) {
        var statusBadge;
        if (p.has_collision) {
          statusBadge = window.FOSS.dom.el("span", {
            className: "badge badge-danger text-xs",
            style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
            "data-truncate-ok": "true",
            title: p.error || "Conflict: name already exists",
            text: "Conflict"
          });
        } else if (p.renumbered) {
          statusBadge = window.FOSS.dom.el("span", {
            className: "badge badge-warning text-xs",
            style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
            "data-truncate-ok": "true",
            title: "Name collision resolved by auto-numbering",
            text: "Renumbered"
          });
        } else if (p.old_name === p.new_name) {
          statusBadge = window.FOSS.dom.el("span", {
            className: "badge badge-neutral text-xs",
            style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
            "data-truncate-ok": "true",
            title: "Filename unchanged",
            text: "Unchanged"
          });
        } else {
          statusBadge = window.FOSS.dom.el("span", {
            className: "badge badge-success text-xs",
            style: "white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis;",
            "data-truncate-ok": "true",
            title: "Ready to rename",
            text: "Ready"
          });
        }

        var removeBtn = window.FOSS.dom.el("button", {
          className: "btn btn-icon btn-ghost btn-sm",
          style: "width: 2rem; height: 2rem; min-width: 2rem; min-height: 2rem; display: inline-flex; align-items: center; justify-content: center;",
          "aria-label": "Remove file from batch",
          title: "Remove file from batch",
          onClick: function () {
            var fileIdx = currentFiles.indexOf(p.original);
            if (fileIdx !== -1) currentFiles.splice(fileIdx, 1);
            schedulePreviewUpdate();
          }
        }, [window.FOSS.icons.el("x", 14)]);

        return window.FOSS.dom.el("tr", {
          className: (p.has_collision || p.renumbered) ? "renamer-conflict-row" : "",
          "data-testid": "renamer-preview-row-" + idx
        }, [
          window.FOSS.dom.el("td", {
            className: "text-xs font-mono text-muted text-center",
            style: "width: 2.5rem;",
            text: String(idx + 1)
          }),
          window.FOSS.dom.el("td", {
            className: "font-semibold text-sm",
            style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: p.old_name,
            "data-truncate-ok": "true",
            title: p.original
          }),
          window.FOSS.dom.el("td", {
            className: "text-muted text-center text-xs",
            style: "width: 2rem;",
            text: "->"
          }),
          window.FOSS.dom.el("td", {
            className: "font-mono text-sm",
            style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            text: p.new_name,
            "data-truncate-ok": "true",
            title: p.proposed
          }),
          window.FOSS.dom.el("td", {
            style: "width: 15%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: p.has_collision ? "Conflict" : (p.renumbered ? "Renumbered" : (p.old_name === p.new_name ? "Unchanged" : "Ready"))
          }, [statusBadge]),
          window.FOSS.dom.el("td", {
            className: "text-right",
            style: "width: 2.5rem; padding: 0.25rem 0;"
          }, [removeBtn])
        ]);
      });

      var table = window.FOSS.dom.el("table", {
        className: "table w-full",
        style: "table-layout: fixed; width: 100%; min-width: 0;"
      }, [
        window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 2.5rem; text-align: center;", text: "#" }),
            window.FOSS.dom.el("th", { style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Current Filename", "data-truncate-ok": "true", title: "Current Filename" }),
            window.FOSS.dom.el("th", { style: "width: 2rem; text-align: center;", text: "" }),
            window.FOSS.dom.el("th", { style: "width: 35%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "New Filename", "data-truncate-ok": "true", title: "New Filename" }),
            window.FOSS.dom.el("th", { style: "width: 15%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;", text: "Status", "data-truncate-ok": "true", title: "Status" }),
            window.FOSS.dom.el("th", { className: "text-right", style: "width: 2.5rem; padding: 0.25rem 0;", text: "", "data-truncate-ok": "true", title: "Actions" })
          ])
        ]),
        window.FOSS.dom.el("tbody", {}, rows)
      ]);

      tableHost.appendChild(table);
    }

    function executeRename() {
      if (currentFiles.length === 0 || isExecuting) {
        showError("No files loaded to rename.");
        return;
      }
      var blocking = previewPlans.filter(function (p) { return p.has_collision; }).length;
      if (blocking > 0) {
        showError(blocking + " name collision(s) must be resolved before renaming. Enable auto-numbering or edit the rules.");
        return;
      }
      isExecuting = true;
      clearError();
      statusBar.textContent = "Renaming files...";

      window.FOSS.api("renamer_execute", {
        file_paths: currentFiles,
        steps: currentSteps,
        sort_by: sortSelect.value,
        auto_resolve_conflicts: autoResolveCheck.checked
      }).then(function (res) {
        isExecuting = false;
        if (!res || !res.results) {
          showError("Rename execution failed.");
          return;
        }
        lastExecutionResults = res.results;
        window.FOSS.store.set("renamer_history_log", lastExecutionResults);
        undoBtn.disabled = !res.undo_available;
        var newFilesList = [];
        res.results.forEach(function (r) {
          if (r.success) {
            newFilesList.push(r.target);
          } else {
            newFilesList.push(r.original);
          }
        });
        currentFiles = newFilesList;
        statusBar.textContent = "Renamed " + (res.renamed_count || 0) + " file(s) successfully.";
        showResultCard("Batch Rename Complete", currentFiles[0] || "");
        updatePreview();
      }).catch(function (err) {
        isExecuting = false;
        showError((err && err.message) || String(err));
      });
    }

    function executeUndo() {
      if (!lastExecutionResults || lastExecutionResults.length === 0) {
        showError("No rename operations to undo.");
        return;
      }
      clearError();
      statusBar.textContent = "Undoing renames...";

      window.FOSS.api("renamer_undo", {
        results: lastExecutionResults
      }).then(function (res) {
        if (!res || !res.results) {
          showError("Undo operation failed.");
          return;
        }
        lastExecutionResults = [];
        window.FOSS.store.set("renamer_history_log", []);
        undoBtn.disabled = true;
        var restoredPaths = [];
        res.results.forEach(function (r) {
          restoredPaths.push(r.target);
        });
        currentFiles = restoredPaths;
        statusBar.textContent = "Restored " + (res.restored_count || 0) + " file(s).";
        showResultCard("Undo Completed", currentFiles[0] || "");
        updatePreview();
      }).catch(function (err) {
        showError((err && err.message) || String(err));
      });
    }

    var stageCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 grow",
      style: "min-width: 0; max-width: 100%; box-sizing: border-box;"
    }, [
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap items-center" }, [
          addFilesBtn,
          addFilesBtnAlias,
          addFolderBtn,
          window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center" }, [
            recursiveCheck,
            window.FOSS.dom.el("span", { text: "Subfolders" })
          ]),
          sortSelect,
          window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center" }, [
            timelineCheck,
            window.FOSS.dom.el("span", { text: "Timeline" })
          ])
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [clearBtn])
      ]),
      tableHost,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap pt-sm" }, [
        window.FOSS.dom.el("div", { className: "row gap-3 items-center" }, [
          window.FOSS.dom.el("label", { className: "text-xs row gap-1 items-center font-semibold" }, [
            autoResolveCheck,
            window.FOSS.dom.el("span", { text: "Auto-number duplicate names" })
          ]),
          summaryText
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          undoBtn,
          applyBtn
        ])
      ])
    ]);

    var stageWrapper = window.FOSS.dom.el("div", {
      className: "renamer-stage-pane grow",
      style: "width: 100%; min-width: 0;"
    }, [stageCard]);

    var split = window.FOSS.dom.el("div", {
      className: "split resizable renamer-workbench"
    }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stageWrapper
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(split);

    renderSteps();
    renderPreviewTable();
    loadRecipes();

    if (pendingPaths.length) {
      var droppedPaths = pendingPaths;
      pendingPaths = [];
      window.FOSS.api("renamer_scan_inputs", { paths: droppedPaths, recursive: false }).then(function (scanRes) {
        if (scanRes && scanRes.paths) addFiles(scanRes.paths);
      });
    }
  }

  window.FOSS.router.register({
    id: "renamer",
    title: "Batch File Renamer",
    navName: "Renamer",
    category: "Utilities",
    icon: "renamer",
    workbench: true,
    defaults: [
      { key: "number_padding", label: "Default numbering padding (digits)", type: "number", min: 1, max: 6, step: 1, default: 2 },
      {
        key: "case_mode",
        label: "Default case transformation",
        type: "select",
        options: [
          { value: "title", label: "Title Case" },
          { value: "lower", label: "lowercase" },
          { value: "upper", label: "UPPERCASE" },
          { value: "sentence", label: "Sentence case" },
          { value: "snake", label: "snake_case" },
          { value: "kebab", label: "kebab-case" }
        ],
        default: "title"
      }
    ],
    tabs: [
      { id: "rules", label: "Rules & Preview", aliases: ["main"], render: renderMain }
    ],
    onFiles: function (paths, ctx) {
      if (!paths || !paths.length) return;
      pendingPaths = paths.slice();
      window.FOSS.router.open("renamer", "rules");
    }
  });
})();
