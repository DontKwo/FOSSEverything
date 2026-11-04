// Settings view with appearance, sidebar customizer, file associations, and privacy.
window.FOSS = window.FOSS || {};

(function () {
  var activeSection = "appearance";
  var activeRebindAction = null;
  var rebindKeyHandler = null;

  function render(container, targetSection) {
    if (targetSection) activeSection = targetSection;
    container.innerHTML = "";

    var page = window.FOSS.dom.el("div", { className: "page settings-page", "data-testid": "settings-view" });

    var header = window.FOSS.dom.el("div", { className: "page-head" }, [
      window.FOSS.dom.el("h1", { className: "title", text: "Settings" }),
      window.FOSS.dom.el("p", { className: "desc", text: "Configure themes, sidebar navigation, keybindings, shell integration, and privacy." })
    ]);
    page.appendChild(header);

    var split = window.FOSS.dom.el("div", { className: "split", "data-testid": "settings-split" });

    // Left nav sections list
    var sections = [
      { id: "appearance", label: "Appearance & Theme" },
      { id: "sidebar", label: "Sidebar & Apps" },
      { id: "home", label: "Home & Workspaces" },
      { id: "keybindings", label: "Keybindings" },
      { id: "shell", label: "File Associations & Shell" },
      { id: "privacy", label: "Privacy & Data" },
      { id: "about", label: "About" }
    ];

    var navEl = window.FOSS.dom.el("div", { className: "card settings-nav stack-sm" });
    sections.forEach(function (sec) {
      var isAct = activeSection === sec.id;
      var btn = window.FOSS.dom.el("button", {
        className: "btn " + (isAct ? "btn-primary" : "btn-ghost"),
        text: sec.label,
        "data-testid": "settings-nav-" + sec.id,
        onClick: function () {
          activeSection = sec.id;
          render(container, sec.id);
        }
      });
      navEl.appendChild(btn);
    });
    split.appendChild(navEl);

    // Right content panel
    var contentPanel = window.FOSS.dom.el("div", { className: "card settings-content", "data-testid": "settings-content-panel" });
    renderSectionContent(contentPanel, activeSection);
    split.appendChild(contentPanel);

    page.appendChild(split);
    container.appendChild(page);
  }

  function renderSectionContent(panel, secId) {
    panel.innerHTML = "";

    if (secId === "appearance") {
      renderAppearance(panel);
    } else if (secId === "sidebar") {
      renderSidebarCustomizer(panel);
    } else if (secId === "home") {
      renderHomeSettings(panel);
    } else if (secId === "keybindings") {
      renderKeybindings(panel);
    } else if (secId === "shell") {
      renderShell(panel);
    } else if (secId === "privacy") {
      renderPrivacy(panel);
    } else if (secId === "about") {
      renderAbout(panel);
    }
  }

  function renderScaleCustomizer(panel) {
    var currentScale = window.FOSS.store.get("ui_scale", 1.0);
    var scaleDebounceTimer = null;
    var visualDebounceTimer = null;

    var scaleOutput = window.FOSS.dom.el("output", {
      id: "settings-scale-value",
      text: Math.round(currentScale * 100) + "%"
    });

    var scaleInput = window.FOSS.dom.el("input", {
      type: "range",
      id: "settings-scale-slider",
      min: "0.50",
      max: "2.50",
      step: "0.05",
      value: String(currentScale),
      "data-testid": "settings-ui-scale-slider",
      "aria-label": "UI font and scale factor",
      onInput: function (e) {
        var val = parseFloat(e.target.value);
        scaleOutput.textContent = Math.round(val * 100) + "%";
        if (visualDebounceTimer) cancelAnimationFrame(visualDebounceTimer);
        visualDebounceTimer = requestAnimationFrame(function () {
          window.FOSS.theme.applyScale(val);
        });
        if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
        scaleDebounceTimer = setTimeout(function () {
          window.FOSS.theme.setScale(val);
        }, 150);
      },
      onChange: function (e) {
        if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
        var val = parseFloat(e.target.value);
        window.FOSS.theme.setScale(val);
      }
    });

    var stepDownBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "settings-scale-step-down",
      "aria-label": "Decrease UI scale",
      onClick: function () {
        if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
        var cur = parseFloat(scaleInput.value);
        var next = Math.round(Math.max(0.50, cur - 0.05) * 100) / 100;
        scaleInput.value = String(next);
        scaleOutput.textContent = Math.round(next * 100) + "%";
        window.FOSS.theme.setScale(next);
      }
    }, [window.FOSS.icons.el("minus", 14)]);

    var stepUpBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "settings-scale-step-up",
      "aria-label": "Increase UI scale",
      onClick: function () {
        if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
        var cur = parseFloat(scaleInput.value);
        var next = Math.round(Math.min(2.50, cur + 0.05) * 100) / 100;
        scaleInput.value = String(next);
        scaleOutput.textContent = Math.round(next * 100) + "%";
        window.FOSS.theme.setScale(next);
      }
    }, [window.FOSS.icons.el("plus", 14)]);

    var presets = [50, 75, 100, 125, 150, 200, 250];
    var presetBtns = presets.map(function (pct) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        text: pct + "%",
        "data-testid": "settings-scale-preset-" + pct,
        onClick: function () {
          if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
          var val = pct / 100;
          scaleInput.value = String(val);
          scaleOutput.textContent = pct + "%";
          window.FOSS.theme.setScale(val);
        }
      });
    });
    var presetRow = window.FOSS.dom.el("div", { className: "row gap-2 mt-2" }, presetBtns);

    var sliderRow = window.FOSS.dom.el("div", { className: "slider-field row gap-2 items-center" }, [
      stepDownBtn,
      scaleInput,
      stepUpBtn,
      scaleOutput
    ]);

    var scaleField = window.FOSS.dom.el("div", { className: "field" }, [
      window.FOSS.dom.el("label", { text: "Text & UI Scaling (50% - 250%)" }),
      sliderRow,
      presetRow,
      window.FOSS.dom.el("span", {
        className: "hint",
        text: "Tip: Hold Ctrl + Scroll Wheel anywhere to zoom in or out (Ctrl+0 to reset)."
      })
    ]);
    panel.appendChild(scaleField);
  }

  function renderAppearance(panel) {
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Appearance & Themes" }));

    // Theme selector
    var currentTheme = window.FOSS.store.get("theme", "dark");
    var themeSelect = window.FOSS.dom.el("select", {
      "data-testid": "settings-theme-select",
      "aria-label": "Select theme",
      onChange: function (e) {
        window.FOSS.theme.setTheme(e.target.value);
      }
    }, [
      window.FOSS.dom.el("option", { value: "dark", text: "Dark (Default)", selected: currentTheme === "dark" }),
      window.FOSS.dom.el("option", { value: "light", text: "Light", selected: currentTheme === "light" }),
      window.FOSS.dom.el("option", { value: "solarized", text: "Solarized", selected: currentTheme === "solarized" }),
      window.FOSS.dom.el("option", { value: "monokai", text: "Monokai", selected: currentTheme === "monokai" }),
      window.FOSS.dom.el("option", { value: "cyberpunk", text: "Cyberpunk", selected: currentTheme === "cyberpunk" }),
      window.FOSS.dom.el("option", { value: "ut_austin", text: "UT Austin", selected: currentTheme === "ut_austin" || currentTheme === "ut" })
    ]);
    var themeField = window.FOSS.dom.el("div", { className: "field" }, [
      window.FOSS.dom.el("label", { text: "Color Theme" }),
      themeSelect,
      window.FOSS.dom.el("span", { className: "hint", text: "Choose from 6 WCAG AA contrast-verified color themes." })
    ]);
    panel.appendChild(themeField);

    renderScaleCustomizer(panel);
  }

  function renderSidebarCustomizer(panel) {
    panel.innerHTML = "";
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Sidebar and Navigation Customizer" }));
    panel.appendChild(window.FOSS.dom.el("p", {
      className: "desc",
      text: "Drag sections or app cards to reorder. Place apps in multiple sections or hide tools."
    }));

    var editor = window.FOSS.dom.el("div", { className: "stack", "data-testid": "settings-sidebar-editor" });
    var layout = window.FOSS.router.resolveSidebarLayout();
    var registeredTools = window.FOSS.router.getRegisteredTools();

    function persistAndRefresh() {
      window.FOSS.store.set("sidebar_layout", layout);
      window.FOSS.router.renderSidebar();
      renderSidebarCustomizer(panel);
    }

    // Top action bar
    var newSecInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      placeholder: "New section name (e.g. Favorites)",
      "data-testid": "settings-new-section-input",
      "aria-label": "New section name"
    });

    var addSecBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      text: "Add Section",
      "data-testid": "settings-add-section-btn",
      onClick: function () {
        var name = (newSecInput.value || "").trim();
        if (!name) return;
        var newId = "sec_" + Date.now();
        layout.sections.push({ id: newId, name: name, collapsed: false, items: [] });
        newSecInput.value = "";
        persistAndRefresh();
      }
    });

    var showAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      text: "Show All Apps",
      "data-testid": "settings-show-all-apps-btn",
      onClick: function () {
        layout.sections.forEach(function (s) {
          (s.items || []).forEach(function (it) { it.visible = true; });
        });
        persistAndRefresh();
      }
    });

    var resetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      text: "Reset Sidebar Layout",
      "data-testid": "settings-reset-sidebar-btn",
      onClick: function () {
        window.FOSS.store.set("sidebar_layout", null);
        layout = window.FOSS.router.resolveSidebarLayout();
        persistAndRefresh();
      }
    });

    var actionBar = window.FOSS.dom.el("div", { className: "row gap-2" }, [
      newSecInput,
      addSecBtn,
      showAllBtn,
      resetBtn
    ]);
    editor.appendChild(actionBar);

    // Section cards loop
    layout.sections.forEach(function (sec, secIdx) {
      var secCard = window.FOSS.dom.el("div", {
        className: "card card-compact stack-sm",
        "data-testid": "settings-section-" + sec.id,
        draggable: "true"
      });

      secCard.ondragstart = function (e) {
        e.dataTransfer.setData("text/plain", JSON.stringify({ type: "section", secId: sec.id }));
      });
      secCard.ondragover = function (e) {
        e.preventDefault();
        secCard.classList.add("drop-target-above");
      });
      secCard.ondragleave = function () {
        secCard.classList.remove("drop-target-above");
      });
      secCard.ondrop = function (e) {
        e.preventDefault();
        secCard.classList.remove("drop-target-above");
        try {
          var data = JSON.parse(e.dataTransfer.getData("text/plain"));
          if (data.type === "section" && data.secId !== sec.id) {
            var srcIdx = layout.sections.findIndex(function (s) { return s.id === data.secId; });
            if (srcIdx >= 0) {
              var moved = layout.sections.splice(srcIdx, 1)[0];
              layout.sections.splice(secIdx, 0, moved);
              persistAndRefresh();
            }
          } else if (data.type === "app" && data.fromSec !== sec.id) {
            var fromS = layout.sections.find(function (s) { return s.id === data.fromSec; });
            if (fromS) {
              var itIdx = fromS.items.findIndex(function (it) { return it.id === data.appId; });
              if (itIdx >= 0) {
                var movedItem = fromS.items.splice(itIdx, 1)[0];
                sec.items.push(movedItem);
                persistAndRefresh();
              }
            }
          }
        } catch (err) {}
      });

      var nameInput = window.FOSS.dom.el("input", {
        type: "text",
        className: "input",
        value: sec.name,
        "data-testid": "settings-section-name-" + sec.id,
        "aria-label": "Section name for " + sec.name,
        onChange: function (e) {
          sec.name = e.target.value.trim() || sec.name;
          window.FOSS.store.set("sidebar_layout", layout);
          window.FOSS.router.renderSidebar();
        }
      });

      var deleteBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        text: "Delete",
        "data-testid": "settings-delete-section-" + sec.id,
        disabled: layout.sections.length <= 1,
        onClick: function () {
          if (layout.sections.length <= 1) return;
          layout.sections = layout.sections.filter(function (s) { return s.id !== sec.id; });
          persistAndRefresh();
        }
      });

      var secHeader = window.FOSS.dom.el("div", { className: "row-between" }, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          window.FOSS.icons.el("grip", 16),
          nameInput
        ]),
        deleteBtn
      ]);
      secCard.appendChild(secHeader);

      // App rows inside section
      var itemsContainer = window.FOSS.dom.el("div", { className: "stack-sm" });
      sec.items.forEach(function (item, itemIdx) {
        var tool = registeredTools.find(function (t) { return t.id === item.id; });
        var appRow = window.FOSS.dom.el("div", {
          className: "row-between p-2 rounded surface-hover",
          "data-testid": "settings-app-row-" + item.id,
          draggable: "true"
        });

        appRow.ondragstart = function (e) {
          e.stopPropagation();
          e.dataTransfer.setData("text/plain", JSON.stringify({ type: "app", appId: item.id, fromSec: sec.id }));
        });
        appRow.ondragover = function (e) {
          e.preventDefault();
          e.stopPropagation();
          appRow.classList.add("drop-target-above");
        });
        appRow.ondragleave = function () {
          appRow.classList.remove("drop-target-above");
        });
        appRow.ondrop = function (e) {
          e.preventDefault();
          e.stopPropagation();
          appRow.classList.remove("drop-target-above");
          try {
            var data = JSON.parse(e.dataTransfer.getData("text/plain"));
            if (data.type === "app") {
              var fromS = layout.sections.find(function (s) { return s.id === data.fromSec; });
              if (fromS) {
                var itIdx = fromS.items.findIndex(function (it) { return it.id === data.appId; });
                if (itIdx >= 0) {
                  var movedItem = fromS.items.splice(itIdx, 1)[0];
                  sec.items.splice(itemIdx, 0, movedItem);
                  persistAndRefresh();
                }
              }
            }
          } catch (err) {}
        });

        var check = window.FOSS.dom.el("input", {
          type: "checkbox",
          checked: !!item.visible,
          "data-testid": "settings-app-check-" + item.id,
          "aria-label": "Toggle tool visibility",
          onChange: function (e) {
            item.visible = e.target.checked;
            window.FOSS.store.set("sidebar_layout", layout);
            window.FOSS.router.renderSidebar();
          }
        });

        var removeAppBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "aria-label": "Remove tool from section",
          title: "Remove from section",
          onClick: function () {
            sec.items.splice(itemIdx, 1);
            persistAndRefresh();
          }
        }, [window.FOSS.icons.el("close", 14)]);

        var iconEl = window.FOSS.icons.el(tool ? tool.icon || "file" : "file", 18);
        var labelGroup = window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          window.FOSS.icons.el("grip", 14),
          check,
          iconEl,
          window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: tool ? tool.title : item.id })
        ]);

        appRow.appendChild(labelGroup);
        appRow.appendChild(removeAppBtn);
        itemsContainer.appendChild(appRow);
      });

      // Add tool dropdown for section
      var addAppSelect = window.FOSS.dom.el("select", {
        className: "select select-sm mt-1",
        "data-dense": "true",
        "aria-label": "Add tool to " + sec.name,
        onChange: function (e) {
          var toolId = e.target.value;
          if (!toolId) return;
          if (!sec.items.some(function (it) { return it.id === toolId; })) {
            sec.items.push({ id: toolId, visible: true });
            persistAndRefresh();
          }
        }
      }, [
        window.FOSS.dom.el("option", { value: "", text: "+ Add tool to section...", disabled: true, selected: true })
      ].concat(
        registeredTools.map(function (t) {
          return window.FOSS.dom.el("option", { value: t.id, text: t.title });
        })
      ));

      secCard.appendChild(itemsContainer);
      secCard.appendChild(addAppSelect);
      editor.appendChild(secCard);
    });

    panel.appendChild(editor);
  }

  function renderHomeSettings(panel) {
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Home & Workspaces" }));

    var clearRecentsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      text: "Clear Recent Files History",
      "data-testid": "settings-clear-recents-btn",
      onClick: function () {
        window.FOSS.api("clear_recents", {}).then(function () {
          window.FOSS.toast.show("Recent files history cleared", "success");
        });
      }
    });
    panel.appendChild(clearRecentsBtn);
  }

  function renderKeybindings(panel) {
    // Implements interactive Rebind, Clear, and Reset buttons
    panel.innerHTML = "";
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Keyboard Shortcuts" }));
    panel.appendChild(window.FOSS.dom.el("p", {
      className: "desc",
      text: "Customize keyboard shortcuts for global actions. Click Rebind and press any key combination."
    }));

    var defaultKeymap = (window.FOSS.shortcuts && window.FOSS.shortcuts.DEFAULT_KEYMAP) || {
      "open_palette": { label: "Command Palette", key: "k", ctrl: true, alt: false, shift: false, display: "Ctrl+K" },
      "go_home": { label: "Navigate to Home", key: "Home", ctrl: false, alt: true, shift: false, display: "Alt+Home" },
      "open_settings": { label: "Open Settings", key: "s", ctrl: false, alt: true, shift: false, display: "Alt+S" },
      "toggle_fullscreen": { label: "Toggle Fullscreen", key: "F11", ctrl: false, alt: false, shift: false, display: "F11" },
      "zoom_in": { label: "Zoom In", key: "=", ctrl: true, alt: false, shift: false, display: "Ctrl+=" },
      "zoom_out": { label: "Zoom Out", key: "-", ctrl: true, alt: false, shift: false, display: "Ctrl+-" },
      "zoom_reset": { label: "Reset Zoom", key: "0", ctrl: true, alt: false, shift: false, display: "Ctrl+0" }
    };

    var keymap = window.FOSS.store.get("custom_keybindings", JSON.parse(JSON.stringify(defaultKeymap)));

    // Cleanup previous rebind listener if any
    if (rebindKeyHandler) {
      window.removeEventListener("keydown", rebindKeyHandler, true);
      rebindKeyHandler = null;
    }

    var resetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm mb-3",
      text: "Reset to Defaults",
      "data-testid": "settings-reset-shortcuts-btn",
      onClick: function () {
        activeRebindAction = null;
        window.FOSS.store.set("custom_keybindings", JSON.parse(JSON.stringify(defaultKeymap)));
        renderKeybindings(panel);
      }
    });
    panel.appendChild(resetBtn);

    var tableWrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" });
    var table = window.FOSS.dom.el("table", { className: "table" });
    var thead = window.FOSS.dom.el("thead", {}, [
      window.FOSS.dom.el("tr", {}, [
        window.FOSS.dom.el("th", { text: "Action" }),
        window.FOSS.dom.el("th", { text: "Shortcut" }),
        window.FOSS.dom.el("th", { text: "Manage" })
      ])
    ]);
    table.appendChild(thead);

    var tbody = window.FOSS.dom.el("tbody");

    function formatBinding(ctrl, alt, shift, key) {
      var parts = [];
      if (ctrl) parts.push("Ctrl");
      if (alt) parts.push("Alt");
      if (shift) parts.push("Shift");
      var keyStr = key.length === 1 ? key.toUpperCase() : key;
      parts.push(keyStr);
      return parts.join("+");
    }

    var actions = Object.keys(defaultKeymap);
    actions.forEach(function (action) {
      var binding = keymap[action] || defaultKeymap[action];
      var isListening = activeRebindAction === action;

      var nameCell = window.FOSS.dom.el("td", { text: binding.label || defaultKeymap[action].label || action });

      var badgeText = isListening ? "Press keys (Esc cancels)..." : (binding.display || "Unassigned");
      var kbdBadge = window.FOSS.dom.el("kbd", {
        className: "kbd" + (isListening ? " bg-primary text-primary-content" : ""),
        "data-testid": "settings-kbd-" + action,
        text: badgeText
      });
      var kbdCell = window.FOSS.dom.el("td", {}, [kbdBadge]);

      var rebindBtn = window.FOSS.dom.el("button", {
        className: "btn " + (isListening ? "btn-primary" : "btn-secondary") + " btn-sm",
        text: isListening ? "Listening..." : "Rebind",
        "data-testid": "settings-rebind-" + action,
        onClick: function () {
          if (isListening) {
            activeRebindAction = null;
            renderKeybindings(panel);
            return;
          }
          activeRebindAction = action;
          renderKeybindings(panel);

          rebindKeyHandler = function (e) {
            if (e.key === "Control" || e.key === "Shift" || e.key === "Alt" || e.key === "Meta") {
              return;
            }
            e.preventDefault();
            e.stopPropagation();
            window.removeEventListener("keydown", rebindKeyHandler, true);
            rebindKeyHandler = null;

            if (e.key !== "Escape") {
              var isCtrl = e.ctrlKey || e.metaKey;
              var isAlt = e.altKey;
              var isShift = e.shiftKey;
              var keyName = e.key;
              var displayStr = formatBinding(isCtrl, isAlt, isShift, keyName);
              keymap[action] = {
                label: binding.label || defaultKeymap[action].label,
                key: keyName,
                ctrl: isCtrl,
                alt: isAlt,
                shift: isShift,
                display: displayStr
              };
              window.FOSS.store.set("custom_keybindings", keymap);
            }
            activeRebindAction = null;
            renderKeybindings(panel);
          };
          window.addEventListener("keydown", rebindKeyHandler, true);
        }
      });

      var clearBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        text: "Clear",
        "data-testid": "settings-clear-" + action,
        onClick: function () {
          activeRebindAction = null;
          keymap[action] = {
            label: binding.label || defaultKeymap[action].label,
            key: "",
            ctrl: false,
            alt: false,
            shift: false,
            display: "None"
          };
          window.FOSS.store.set("custom_keybindings", keymap);
          renderKeybindings(panel);
        }
      });

      var actionsCell = window.FOSS.dom.el("td", {}, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [rebindBtn, clearBtn])
      ]);

      var row = window.FOSS.dom.el("tr", { "data-testid": "settings-keybinding-row-" + action }, [
        nameCell,
        kbdCell,
        actionsCell
      ]);
      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    tableWrap.appendChild(table);
    panel.appendChild(tableWrap);
  }

  function renderShell(panel) {
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "File Associations & Windows Shell" }));

    var regBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      text: "Register Windows Context Menu",
      "data-testid": "settings-shell-register-btn",
      onClick: function () {
        window.FOSS.api("shell_register", {}).then(function (res) {
          window.FOSS.toast.show(res.message || "Context menu updated", "success");
        });
      }
    });

    var unregBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      text: "Unregister Context Menu",
      "data-testid": "settings-shell-unregister-btn",
      onClick: function () {
        window.FOSS.api("shell_unregister", {}).then(function (res) {
          window.FOSS.toast.show(res.message || "Context menu removed", "info");
        });
      }
    });

    panel.appendChild(window.FOSS.dom.el("div", { className: "row" }, [regBtn, unregBtn]));
  }

  function renderPrivacy(panel) {
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Privacy & Data Storage" }));

    var openDataBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      text: "Open Data Directory",
      "data-testid": "settings-open-data-dir-btn",
      onClick: function () {
        window.FOSS.api("get_data_dir", {}).then(function (res) {
          if (res && res.path) window.FOSS.api("open_path", { path: res.path });
        });
      }
    });

    var resetDefaultsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      text: "Reset All Settings",
      "data-testid": "settings-reset-defaults-btn",
      onClick: function () {
        window.FOSS.dialogs.confirm("Reset all settings to defaults?").then(function (confirmed) {
          if (confirmed) {
            window.FOSS.api("reset_settings_defaults", {}).then(function (res) {
              window.FOSS.store.loadAll().then(function () {
                window.FOSS.theme.init();
                var msg = (res && res.message) ? res.message : "Settings reset to defaults";
                window.FOSS.toast.show(msg, "success");
              });
            });
          }
        });
      }
    });

    panel.appendChild(window.FOSS.dom.el("div", { className: "row" }, [openDataBtn, resetDefaultsBtn]));
  }

  function renderAbout(panel) {
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "About FOSSEverything" }));
    panel.appendChild(window.FOSS.dom.el("p", { className: "desc", text: "Version 0.1.0 | AGPL-3.0-or-later" }));
    panel.appendChild(window.FOSS.dom.el("p", {
      className: "desc",
      text: "Zero telemetry. Fully local-first and offline processing. No account, ads, or tracking."
    }));
  }

  window.FOSS.settings = {
    render: render
  };
})();
