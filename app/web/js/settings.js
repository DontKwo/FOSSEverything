// Settings view with appearance, ArtCraft external hub, shell associations, and privacy.
window.FOSS = window.FOSS || {};

(function () {
  var activeSection = "appearance";

  function render(container, targetSection) {
    if (targetSection) activeSection = targetSection;
    container.innerHTML = "";

    var page = window.FOSS.dom.el("div", { className: "page settings-page", "data-testid": "settings-view" });

    var header = window.FOSS.dom.el("div", { className: "page-head" }, [
      window.FOSS.dom.el("h1", { className: "title", text: "Settings" }),
      window.FOSS.dom.el("p", { className: "desc", text: "Configure themes, keybindings, external tools, file associations, and application privacy." })
    ]);
    page.appendChild(header);

    var split = window.FOSS.dom.el("div", { className: "split", "data-testid": "settings-split" });

    // Left nav sections list
    var sections = [
      { id: "appearance", label: "Appearance & Theme" },
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

    // UI Scale slider
    var currentScale = window.FOSS.store.get("ui_scale", 1.0);
    var scaleOutput = window.FOSS.dom.el("output", { text: Math.round(currentScale * 100) + "%" });
    var scaleInput = window.FOSS.dom.el("input", {
      type: "range",
      min: "0.85",
      max: "1.50",
      step: "0.05",
      value: String(currentScale),
      "data-testid": "settings-ui-scale-slider",
      "aria-label": "UI font and scale factor",
      onInput: function (e) {
        var val = parseFloat(e.target.value);
        scaleOutput.textContent = Math.round(val * 100) + "%";
        window.FOSS.theme.setScale(val);
      }
    });

    var scaleField = window.FOSS.dom.el("div", { className: "field" }, [
      window.FOSS.dom.el("label", { text: "Text & UI Scaling (0.85x - 1.50x)" }),
      window.FOSS.dom.el("div", { className: "slider-field" }, [scaleInput, scaleOutput]),
      window.FOSS.dom.el("span", { className: "hint", text: "Adjust root scale factor dynamically without restarts." })
    ]);
    panel.appendChild(scaleField);
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
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Keyboard Shortcuts" }));
    var tableWrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" });
    var table = window.FOSS.dom.el("table", { className: "table" }, [
      window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { text: "Action" }),
          window.FOSS.dom.el("th", { text: "Shortcut" })
        ])
      ]),
      window.FOSS.dom.el("tbody", {}, [
        window.FOSS.dom.el("tr", {}, [window.FOSS.dom.el("td", { text: "Find a Tool / Command Palette" }), window.FOSS.dom.el("td", {}, [window.FOSS.dom.el("kbd", { className: "kbd", text: "Ctrl + K" })])]),
        window.FOSS.dom.el("tr", {}, [window.FOSS.dom.el("td", { text: "Navigate to Home" }), window.FOSS.dom.el("td", {}, [window.FOSS.dom.el("kbd", { className: "kbd", text: "Alt + Home" })])]),
        window.FOSS.dom.el("tr", {}, [window.FOSS.dom.el("td", { text: "Toggle Fullscreen" }), window.FOSS.dom.el("td", {}, [window.FOSS.dom.el("kbd", { className: "kbd", text: "F11" })])]),
        window.FOSS.dom.el("tr", {}, [window.FOSS.dom.el("td", { text: "Zoom In / Out / Reset" }), window.FOSS.dom.el("td", {}, [window.FOSS.dom.el("kbd", { className: "kbd", text: "Ctrl + / Ctrl - / Ctrl 0" })])])
      ])
    ]);
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

    var resetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-danger",
      text: "Reset All Settings",
      "data-testid": "settings-reset-all-btn",
      onClick: function () {
        window.FOSS.confirm({
          title: "Reset All Settings?",
          message: "This will remove all saved settings, recents, and color overrides.",
          confirmText: "Reset",
          danger: true
        }).then(function (confirmed) {
          if (confirmed) {
            window.FOSS.api("reset_settings", {}).then(function () {
              window.FOSS.toast.show("Settings reset to defaults", "info");
              location.reload();
            });
          }
        });
      }
    });

    panel.appendChild(window.FOSS.dom.el("div", { className: "row" }, [openDataBtn, resetBtn]));
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

