// Resume Studio: local-first master resume management, SpaceX GNC format, live preview, and exporters.
window.FOSS = window.FOSS || {};

(function () {
  var masterResume = {
    contact: {
      name: "Alex Morgan",
      title: "Quantitative Finance & Systems Engineering",
      email: "alex.morgan@utexas.edu",
      phone: "(512) 555-0199",
      location: "Austin, TX",
      linkedin: "linkedin.com/in/alexmorgan-finance",
      github: "github.com/alexmorgan",
      website: "alexmorgan.space"
    },
    summary: "",
    summary_enabled: false,
    sections: [
      {
        id: "sec_edu",
        type: "education",
        title: "EDUCATION",
        enabled: true,
        entries: [
          {
            id: "edu_1",
            title: "Bachelor of Science, Computational Engineering & Finance Honors",
            subtitle: "The University of Texas at Austin",
            date_range: "December 2026",
            gpa: "3.94 / 4.00",
            coursework: "Stochastic Calculus, Quantitative Risk, Numerical Analysis, Derivative Pricing, Financial Modeling, Algorithms",
            enabled: true,
            bullets: []
          }
        ]
      },
      {
        id: "sec_exp",
        type: "experience",
        title: "WORK EXPERIENCE",
        enabled: true,
        entries: [
          {
            id: "exp_1",
            title: "Quantitative Trading & Risk Intern",
            subtitle: "Apex Capital & Trading",
            date_range: "May 2025 - August 2025",
            enabled: true,
            bullets: [
              { id: "b1", text: "Built ultra-low latency statistical arbitrage backtesting pipelines in Python and C++, evaluating signals across 500M+ order book updates.", enabled: true },
              { id: "b2", text: "Engineered automated Monte Carlo value-at-risk (VaR) framework reducing intra-day risk calculation latency by 45%.", enabled: true }
            ]
          },
          {
            id: "exp_2",
            title: "Financial Systems Software Intern",
            subtitle: "Texas Investment Management",
            date_range: "June 2024 - August 2024",
            enabled: true,
            bullets: [
              { id: "b3", text: "Automated regression analytics on macro factor models across $2B portfolio, decreasing quarterly audit turnaround from 4 days to 2 hours.", enabled: true },
              { id: "b4", text: "Constructed real-time options Greeks dashboard with interactive volatility surface visualizations.", enabled: true }
            ]
          }
        ]
      },
      {
        id: "sec_proj",
        type: "projects",
        title: "PROJECTS",
        enabled: true,
        entries: [
          {
            id: "proj_1",
            title: "Longhorn Algorithmic Trading Group",
            subtitle: "Head of Quantitative Strategies",
            date_range: "2023 - Present",
            enabled: true,
            bullets: [
              { id: "b5", text: "Led engineering of high-throughput market data feed parser supporting FIX protocol and binary exchange formats.", enabled: true },
              { id: "b6", text: "Trained LSTM neural network models for predictive volatility estimation achieving 14% Sharpe improvement over baseline.", enabled: true }
            ]
          }
        ]
      },
      {
        id: "sec_skills",
        type: "skills",
        title: "SKILLS & EXPERTISE",
        enabled: true,
        entries: [
          {
            id: "sk_1",
            title: "Quantitative & Programming",
            skills_text: "Python, C++, SQL, R, MATLAB, Pandas, NumPy, Scikit-learn, Git, Linux/POSIX",
            enabled: true,
            bullets: []
          },
          {
            id: "sk_2",
            title: "Financial Knowledge",
            skills_text: "Fixed Income, Equity Derivatives, Portfolio Optimization, Monte Carlo Simulation, Black-Scholes, Risk Parity",
            enabled: true,
            bullets: []
          }
        ]
      }
    ],
    profiles: {},
    active_profile: "Full Master Resume"
  };

  var activeSubView = "personal";
  var previewDebounceTimer = null;
  var previewStageEl = null;
  var pageBadgeEl = null;
  var currentFontPt = 11.0;
  var currentTheme = "gnc";
  var currentDateFormat = "Month YYYY";
  var previewMode = "fit-width";
  var previewModeButtons = {};
  var defaultsLoaded = false;
  var idCounter = 100;
  var ZOOM_PRESETS = [50, 75, 100, 125];
  var EXPORT_TYPES = {
    docx: { name: "Microsoft Word Document (*.docx)", extensions: ["docx"] },
    pdf: { name: "PDF Document (*.pdf)", extensions: ["pdf"] },
    txt: { name: "Plain Text Document (*.txt)", extensions: ["txt"] }
  };

  function loadDefaults() {
    var values = window.FOSS.toolDefaults.all("resume");
    currentTheme = String(values.theme);
    currentDateFormat = String(values.date_format);
    currentFontPt = parseFloat(values.font_scale) || 11.0;
    if (values.include_summary !== undefined) {
      masterResume.summary_enabled = !!values.include_summary;
    }
    defaultsLoaded = true;
  }

  window.addEventListener("foss:tool-defaults-changed", function (evt) {
    if (!evt.detail || evt.detail.toolId !== "resume") return;
    loadDefaults();
    var fontSel = document.querySelector("[data-testid='resume-font-pt-select']");
    if (fontSel) fontSel.value = currentFontPt.toFixed(1);
    var themeSel = document.querySelector("[data-testid='resume-theme-select']");
    if (themeSel) themeSel.value = currentTheme;
    var dateSel = document.querySelector("[data-testid='resume-date-format-select']");
    if (dateSel) dateSel.value = currentDateFormat;
    schedulePreviewUpdate();
  });

  function previewPayload() {
    var payload = {
      resume: masterResume,
      font_pt: currentFontPt,
      theme: currentTheme,
      date_format: currentDateFormat
    };
    if (masterResume.active_profile && masterResume.active_profile !== "Full Master Resume") {
      payload.profile = masterResume.active_profile;
    }
    return payload;
  }

  function schedulePreviewUpdate() {
    if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(function () {
      fetchLivePreview();
    }, 180);
  }

  function fetchLivePreview() {
    if (!previewStageEl) return;
    var payload = previewPayload();
    payload.dpi = 160;
    window.FOSS.api("resume_render_preview", payload, { silent: true })
      .then(function (res) {
        if (!res) return;
        renderPreviewPages(res.pages || [], res.page_count || 1);
      })
      .catch(function () {});
  }

  function renderPreviewPages(pages, pageCount) {
    if (!previewStageEl) return;
    previewStageEl.innerHTML = "";
    if (pageBadgeEl) {
      if (pageCount === 1) {
        pageBadgeEl.className = "badge success text-xs";
        pageBadgeEl.textContent = "1 Page (Fits Cleanly)";
      } else {
        pageBadgeEl.className = "badge warning text-xs";
        pageBadgeEl.textContent = pageCount + " Pages (Overflow)";
      }
    }
    pages.forEach(function (pageUrl, pIdx) {
      previewStageEl.appendChild(window.FOSS.dom.el("img", {
        className: "resume-page-sheet",
        "data-testid": "resume-preview-page-" + pIdx,
        "data-overlay": "true",
        src: pageUrl,
        alt: "Resume Page " + (pIdx + 1)
      }));
    });
  }

  function applyPreviewMode() {
    if (!previewStageEl) return;
    var isZoom = typeof previewMode === "number";
    previewStageEl.classList.toggle("resume-stage-fit-width", previewMode === "fit-width");
    previewStageEl.classList.toggle("resume-stage-fit-page", previewMode === "fit-page");
    previewStageEl.classList.toggle("resume-stage-zoom", isZoom);
    if (isZoom) previewStageEl.style.setProperty("--resume-zoom", String(previewMode / 100));
    Object.keys(previewModeButtons).forEach(function (key) {
      var active = String(previewMode) === key;
      previewModeButtons[key].classList.toggle("active", active);
      previewModeButtons[key].setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setPreviewMode(mode) {
    previewMode = mode;
    applyPreviewMode();
  }

  function exportResume(preferredExt) {
    var order = [preferredExt].concat(Object.keys(EXPORT_TYPES).filter(function (key) { return key !== preferredExt; }));
    return window.FOSS.api("select_save_path", {
      title: "Export Resume",
      default_name: "resume",
      file_types: order.map(function (key) { return EXPORT_TYPES[key]; })
    }).then(function (res) {
      var savePath = res && (res.file_path || res.path || res.output_path);
      if (!savePath) return null;
      var payload = previewPayload();
      payload.output_path = savePath;
      return window.FOSS.api("resume_export", payload).then(function (info) {
        return { path: savePath, info: info };
      });
    });
  }

  function renderResumeWorkbench(panel, requestedView) {
    panel.innerHTML = "";
    if (requestedView) activeSubView = requestedView;
    if (!defaultsLoaded) loadDefaults();
    previewModeButtons = {};

    // Top action bar
    var topBar = window.FOSS.dom.el("div", {
      className: "row-between resume-btn-row"
    }, [
      window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
        window.FOSS.dom.el("span", {
          className: "badge badge-neutral",
          "data-testid": "resume-offline-badge",
          text: "100% Offline"
        }),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "resume-load-btn",
          onclick: function () {
            window.FOSS.api("select_file", { title: "Load Master Resume", file_types: ["json"] })
              .then(function (res) {
                var picked = res && res.paths && res.paths[0];
                if (picked) {
                  return window.FOSS.api("resume_load_file", { file_path: picked });
                }
              }).then(function (loadRes) {
                if (loadRes && loadRes.resume) {
                  masterResume = loadRes.resume;
                  renderLeftPane();
                  schedulePreviewUpdate();
                  window.FOSS.dialogs.toast("Master resume loaded.");
                }
              }).catch(function (err) {
                window.FOSS.dialogs.toast("Failed loading resume: " + (err.message || err));
              });
          }
        }, [window.FOSS.icons.el("folder", 12), window.FOSS.dom.el("span", { text: "Load JSON" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "resume-save-btn",
          onclick: function () {
            window.FOSS.api("select_save_path", {
              title: "Save Master Resume",
              default_name: "master_resume",
              file_types: [{ name: "JSON File (*.json)", extensions: ["json"] }]
            }).then(function (res) {
              if (res && res.file_path) {
                return window.FOSS.api("resume_save_file", { resume: masterResume, output_path: res.file_path });
              }
            }).then(function () {
              window.FOSS.dialogs.toast("Master resume saved.");
            }).catch(function (err) {
              window.FOSS.dialogs.toast("Save failed: " + (err.message || err));
            });
          }
        }, [window.FOSS.icons.el("save", 12), window.FOSS.dom.el("span", { text: "Save JSON" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "resume-sample-btn",
          onclick: function () {
            window.FOSS.api("resume_sample", {})
              .then(function (res) {
                if (res && res.resume) {
                  masterResume = res.resume;
                  renderLeftPane();
                  schedulePreviewUpdate();
                  window.FOSS.dialogs.toast("UT Austin Engineering sample loaded.");
                }
              });
          }
        }, [window.FOSS.icons.el("refresh-cw", 12), window.FOSS.dom.el("span", { text: "Load Sample" })])
      ]),
      window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
        pageBadgeEl = window.FOSS.dom.el("span", {
          className: "badge success text-xs",
          "data-testid": "resume-page-badge",
          text: "1 Page (Fits Cleanly)"
        })
      ])
    ]);

    // Resizable Split Workspace
    var splitWrap = window.FOSS.dom.el("div", {
      className: "split resizable even resume-workbench-split",
      "data-testid": "resume-split"
    });

    var leftPane = window.FOSS.dom.el("div", { className: "resume-editor-pane" });
    var rightPane = window.FOSS.dom.el("div", { className: "resume-preview-pane" });

    var editorContent = window.FOSS.dom.el("div", { className: "resume-flex-col-gap-3" });
    leftPane.appendChild(editorContent);

    function renderLeftPane() {
      editorContent.innerHTML = "";
      splitWrap.classList.toggle("resume-export-mode", activeSubView === "preview");
      if (activeSubView === "personal") {
        renderPersonalView(editorContent);
      } else if (activeSubView === "sections") {
        renderSectionsView(editorContent);
      } else if (activeSubView === "profiles") {
        renderProfilesView(editorContent);
      } else if (activeSubView === "preview") {
        renderExportView(editorContent);
      }
    }

    // Right Pane Toolbar & Stage
    var fontSelect = window.FOSS.dom.el("select", {
      className: "select resume-input-width-11",
      "data-testid": "resume-font-pt-select",
      "aria-label": "Font size",
      onchange: function (e) {
        currentFontPt = parseFloat(e.target.value) || 11.0;
        schedulePreviewUpdate();
      }
    }, [["11.0", "11.0 pt (Standard)"], ["10.5", "10.5 pt (Compact)"], ["10.0", "10.0 pt (Dense)"]].map(function (opt) {
      return window.FOSS.dom.el("option", { value: opt[0], text: opt[1], selected: currentFontPt.toFixed(1) === opt[0] });
    }));

    function modeButton(key, label, testid, mode) {
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": testid,
        "aria-pressed": "false",
        onclick: function () { setPreviewMode(mode); }
      }, [window.FOSS.dom.el("span", { text: label })]);
      previewModeButtons[key] = btn;
      return btn;
    }

    var modeButtons = [
      modeButton("fit-width", "Fit Width", "resume-fit-width", "fit-width"),
      modeButton("fit-page", "Fit Page", "resume-fit-page", "fit-page")
    ].concat(ZOOM_PRESETS.map(function (pct) {
      return modeButton(String(pct), pct + "%", "resume-zoom-" + pct, pct);
    }));

    var previewToolbar = window.FOSS.dom.el("div", {
      className: "row-between resume-preview-toolbar resume-row-gap-2",
      "data-testid": "resume-preview-toolbar"
    }, [
      window.FOSS.dom.el("div", { className: "row items-center resume-row-gap-2" }, [
        window.FOSS.dom.el("span", { className: "text-xs font-semibold text-muted", text: "Font:" }),
        fontSelect
      ].concat(modeButtons)),
      window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-primary btn-sm",
          "data-testid": "resume-export-btn",
          onclick: function () { runExport("docx"); }
        }, [window.FOSS.icons.el("save", 12), window.FOSS.dom.el("span", { text: "Export..." })])
      ])
    ]);

    previewStageEl = window.FOSS.dom.el("div", {
      className: "resume-preview-stage",
      "data-testid": "resume-preview-stage"
    });
    applyPreviewMode();

    var exportResultHost = window.FOSS.dom.el("div", { "data-testid": "resume-export-result", hidden: true });

    rightPane.appendChild(previewToolbar);
    rightPane.appendChild(previewStageEl);
    rightPane.appendChild(exportResultHost);

    var divider = window.FOSS.components.splitDivider({ targetSplit: splitWrap, side: "left" });
    splitWrap.appendChild(leftPane);
    splitWrap.appendChild(divider);
    splitWrap.appendChild(rightPane);

    panel.appendChild(topBar);
    panel.appendChild(splitWrap);

    renderLeftPane();
    setTimeout(function () {
      fetchLivePreview();
    }, 0);

    // --- Sub-views Implementations ------------------------------------------

    function renderPersonalView(container) {
      var contactCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "resume-contact-card" }, [
        window.FOSS.dom.el("h3", { className: "card-title resume-card-title-mb", text: "Contact Details" }),
        window.FOSS.components.field({
          label: "Full Name",
          testid: "resume-name-field",
          control: window.FOSS.dom.el("input", {
            className: "input",
            "data-testid": "resume-name-input",
            "data-truncate-ok": "true",
            "aria-label": "Full Name",
            title: "Full Name",
            value: masterResume.contact.name || "",
            oninput: function (e) {
              masterResume.contact.name = e.target.value;
              schedulePreviewUpdate();
            }
          })
        }),
        window.FOSS.components.field({
          label: "Professional Title",
          testid: "resume-title-field",
          control: window.FOSS.dom.el("input", {
            className: "input",
            "data-testid": "resume-title-input",
            "data-truncate-ok": "true",
            "aria-label": "Professional Title",
            title: "Professional Title",
            value: masterResume.contact.title || "",
            oninput: function (e) {
              masterResume.contact.title = e.target.value;
              schedulePreviewUpdate();
            }
          })
        }),
        window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.components.field({
            label: "Email",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-email-input",
              "data-truncate-ok": "true",
              "aria-label": "Email",
              title: "Email",
              value: masterResume.contact.email || "",
              oninput: function (e) {
                masterResume.contact.email = e.target.value;
                schedulePreviewUpdate();
              }
            })
          }),
          window.FOSS.components.field({
            label: "Phone",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-phone-input",
              "data-truncate-ok": "true",
              "aria-label": "Phone",
              title: "Phone",
              value: masterResume.contact.phone || "",
              oninput: function (e) {
                masterResume.contact.phone = e.target.value;
                schedulePreviewUpdate();
              }
            })
          })
        ]),
        window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.components.field({
            label: "Location",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-location-input",
              "data-truncate-ok": "true",
              "aria-label": "Location",
              title: "Location",
              value: masterResume.contact.location || "",
              oninput: function (e) {
                masterResume.contact.location = e.target.value;
                schedulePreviewUpdate();
              }
            })
          }),
          window.FOSS.components.field({
            label: "LinkedIn",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-linkedin-input",
              "data-truncate-ok": "true",
              "aria-label": "LinkedIn",
              title: "LinkedIn",
              value: masterResume.contact.linkedin || "",
              oninput: function (e) {
                masterResume.contact.linkedin = e.target.value;
                schedulePreviewUpdate();
              }
            })
          })
        ]),
        window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.components.field({
            label: "GitHub",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-github-input",
              "data-truncate-ok": "true",
              "aria-label": "GitHub",
              title: "GitHub",
              value: masterResume.contact.github || "",
              oninput: function (e) {
                masterResume.contact.github = e.target.value;
                schedulePreviewUpdate();
              }
            })
          }),
          window.FOSS.components.field({
            label: "Website",
            control: window.FOSS.dom.el("input", {
              className: "input",
              "data-testid": "resume-website-input",
              "data-truncate-ok": "true",
              "aria-label": "Website",
              title: "Website",
              value: masterResume.contact.website || "",
              oninput: function (e) {
                masterResume.contact.website = e.target.value;
                schedulePreviewUpdate();
              }
            })
          })
        ])
      ]);

      var sumToggle = window.FOSS.dom.el("input", {
        type: "checkbox",
        "data-testid": "resume-summary-toggle",
        "aria-label": "Include Summary",
        title: "Include Summary",
        checked: Boolean(masterResume.summary_enabled),
        onchange: function (e) {
          masterResume.summary_enabled = e.target.checked;
          sumText.disabled = !e.target.checked;
          schedulePreviewUpdate();
        }
      });

      var sumText = window.FOSS.dom.el("textarea", {
        className: "input",
        "data-testid": "resume-summary-input",
        "aria-label": "Professional Summary",
        title: "Professional Summary",
        rows: 3,
        disabled: !masterResume.summary_enabled,
        placeholder: "Optional summary (disabled by default in SpaceX GNC standard)...",
        value: masterResume.summary || "",
        oninput: function (e) {
          masterResume.summary = e.target.value;
          schedulePreviewUpdate();
        }
      });

      var summaryCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "resume-summary-card" }, [
        window.FOSS.dom.el("div", { className: "row-between resume-card-title-mb" }, [
          window.FOSS.dom.el("h3", { className: "card-title", text: "Professional Summary" }),
          window.FOSS.dom.el("label", { className: "row resume-bullet-row" }, [
            sumToggle,
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Include Summary" })
          ])
        ]),
        sumText
      ]);

      container.appendChild(contactCard);
      container.appendChild(summaryCard);
    }

    function renderSectionsView(container) {
      var topBarSec = window.FOSS.dom.el("div", {
        className: "row-between card card-compact resume-padding-2-3",
        "data-testid": "resume-master-mgmt"
      }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: (masterResume.sections || []).length + " Section(s)" }),
        window.FOSS.dom.el("button", {
          className: "btn btn-primary btn-sm",
          "data-testid": "resume-add-sec-btn",
          onclick: function () {
            var newSec = {
              id: "sec_" + (idCounter++),
              type: "experience",
              title: "WORK EXPERIENCE",
              enabled: true,
              entries: [
                {
                  id: "e_" + (idCounter++),
                  title: "Role / Degree / Project",
                  subtitle: "Company / Institution",
                  date_range: "2024 - Present",
                  enabled: true,
                  bullets: [
                    { id: "b_" + (idCounter++), text: "Key accomplishment with quantified impact.", enabled: true }
                  ]
                }
              ]
            };
            masterResume.sections.push(newSec);
            renderLeftPane();
            schedulePreviewUpdate();
          }
        }, [window.FOSS.icons.el("plus", 12), window.FOSS.dom.el("span", { text: "Add Section" })])
      ]);

      container.appendChild(topBarSec);

      (masterResume.sections || []).forEach(function (sec, sIdx) {
        var secCard = window.FOSS.dom.el("div", {
          className: "card card-compact resume-section-item"
        });

        var secHeader = window.FOSS.dom.el("div", { className: "row-between resume-row-gap-2" });
        var secTitleInput = window.FOSS.dom.el("input", {
          className: "input font-semibold text-base resume-flex-auto",
          "data-truncate-ok": "true",
          "aria-label": "Section Title",
          title: "Section Title",
          value: sec.title,
          oninput: function (e) {
            sec.title = e.target.value;
            schedulePreviewUpdate();
          }
        });
        var secTypeSelect = window.FOSS.dom.el("select", {
          className: "select select-sm text-xs resume-input-width-10",
          "aria-label": "Section Type",
          title: "Section Type",
          onchange: function (e) {
            sec.type = e.target.value;
            renderLeftPane();
            schedulePreviewUpdate();
          }
        }, [
          window.FOSS.dom.el("option", { value: "education", text: "Education", selected: sec.type === "education" }),
          window.FOSS.dom.el("option", { value: "experience", text: "Experience", selected: sec.type === "experience" }),
          window.FOSS.dom.el("option", { value: "projects", text: "Projects", selected: sec.type === "projects" }),
          window.FOSS.dom.el("option", { value: "organization", text: "Organization", selected: sec.type === "organization" }),
          window.FOSS.dom.el("option", { value: "skills", text: "Skills", selected: sec.type === "skills" }),
          window.FOSS.dom.el("option", { value: "accomplishments", text: "Accomplishments", selected: sec.type === "accomplishments" }),
          window.FOSS.dom.el("option", { value: "custom", text: "Custom", selected: sec.type === "custom" })
        ]);

        var secDelBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-icon text-danger btn-sm",
          title: "Delete Section",
          onclick: function () {
            masterResume.sections.splice(sIdx, 1);
            renderLeftPane();
            schedulePreviewUpdate();
          }
        }, [window.FOSS.icons.el("trash", 14)]);

        secHeader.appendChild(secTitleInput);
        secHeader.appendChild(secTypeSelect);
        secHeader.appendChild(secDelBtn);
        secCard.appendChild(secHeader);

        // Entries
        (sec.entries || []).forEach(function (entry, eIdx) {
          var entryBox = renderEntryEditor(sec, entry, function () {
            sec.entries.splice(eIdx, 1);
            renderLeftPane();
            schedulePreviewUpdate();
          });
          secCard.appendChild(entryBox);
        });

        // Add entry button
        var addEntryBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          onclick: function () {
            sec.entries.push({
              id: "e_" + (idCounter++),
              title: "Title / Degree / Project",
              subtitle: "",
              date_range: "",
              enabled: true,
              bullets: [
                { id: "b_" + (idCounter++), text: "Quantified bullet details here.", enabled: true }
              ]
            });
            renderLeftPane();
            schedulePreviewUpdate();
          }
        }, [window.FOSS.icons.el("plus", 12), window.FOSS.dom.el("span", { text: "Add Entry" })]);

        secCard.appendChild(addEntryBtn);
        container.appendChild(secCard);
      });
    }

    function renderEntryEditor(sec, entry, onDeleteEntry) {
      var box = window.FOSS.dom.el("div", {
        className: "card card-compact resume-item-card"
      });

      var topRow = window.FOSS.dom.el("div", { className: "row-between resume-row-gap-2" });
      var enableCheck = window.FOSS.dom.el("input", {
        type: "checkbox",
        "aria-label": "Enable entry",
        title: "Enable entry",
        checked: Boolean(entry.enabled),
        onchange: function (e) {
          entry.enabled = e.target.checked;
          schedulePreviewUpdate();
        }
      });
      var entryTitle = window.FOSS.dom.el("input", {
        className: "input font-semibold resume-flex-auto",
        "data-truncate-ok": "true",
        "aria-label": "Entry Title",
        title: "Entry Title",
        value: entry.title || "",
        placeholder: sec.type === "education" ? "Degree / Major" : (sec.type === "skills" ? "Category Name" : "Role / Title"),
        oninput: function (e) {
          entry.title = e.target.value;
          schedulePreviewUpdate();
        }
      });
      var delBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-icon text-danger btn-sm",
        "aria-label": "Delete Entry",
        title: "Delete Entry",
        onclick: onDeleteEntry
      }, [window.FOSS.icons.el("x", 12)]);

      topRow.appendChild(enableCheck);
      topRow.appendChild(entryTitle);
      topRow.appendChild(delBtn);
      box.appendChild(topRow);

      if (sec.type === "education") {
        var eduRow = window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.dom.el("input", {
            className: "input",
            "data-truncate-ok": "true",
            "aria-label": "Institution",
            title: "Institution",
            placeholder: "Institution (e.g. University of Texas at Austin)",
            value: entry.subtitle || "",
            oninput: function (e) { entry.subtitle = e.target.value; schedulePreviewUpdate(); }
          }),
          window.FOSS.dom.el("input", {
            className: "input resume-input-width-10",
            "data-truncate-ok": "true",
            "aria-label": "Graduation Date",
            title: "Graduation Date",
            placeholder: "Graduation Date",
            value: entry.date_range || "",
            oninput: function (e) { entry.date_range = e.target.value; schedulePreviewUpdate(); }
          })
        ]);
        var gpaRow = window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.dom.el("input", {
            className: "input resume-input-width-10",
            "data-truncate-ok": "true",
            "aria-label": "GPA",
            title: "GPA",
            placeholder: "GPA (e.g. 3.94 / 4.00)",
            value: entry.gpa || "",
            oninput: function (e) { entry.gpa = e.target.value; schedulePreviewUpdate(); }
          }),
          window.FOSS.dom.el("input", {
            className: "input",
            "data-truncate-ok": "true",
            "aria-label": "Relevant Coursework",
            title: "Relevant Coursework",
            placeholder: "Relevant Coursework (comma separated)",
            value: entry.coursework || "",
            oninput: function (e) { entry.coursework = e.target.value; schedulePreviewUpdate(); }
          })
        ]);
        box.appendChild(eduRow);
        box.appendChild(gpaRow);
      } else if (sec.type === "skills") {
        var skInput = window.FOSS.dom.el("input", {
          className: "input",
          "data-truncate-ok": "true",
          "aria-label": "Skills list",
          title: "Skills list",
          placeholder: "Skills (comma-separated list, e.g. C++, Python, MATLAB, ROS 2)",
          value: entry.skills_text || "",
          oninput: function (e) { entry.skills_text = e.target.value; schedulePreviewUpdate(); }
        });
        box.appendChild(skInput);
      } else {
        var metaRow = window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.dom.el("input", {
            className: "input",
            "data-truncate-ok": "true",
            "aria-label": "Subtitle",
            title: "Subtitle",
            placeholder: sec.type === "experience" ? "Company Name" : "Subtitle / Tech",
            value: entry.subtitle || "",
            oninput: function (e) { entry.subtitle = e.target.value; schedulePreviewUpdate(); }
          }),
          window.FOSS.dom.el("input", {
            className: "input resume-input-width-12",
            "data-truncate-ok": "true",
            "aria-label": "Dates",
            title: "Dates",
            placeholder: "Dates (e.g. May 2025 - Aug 2025)",
            value: entry.date_range || "",
            oninput: function (e) { entry.date_range = e.target.value; schedulePreviewUpdate(); }
          })
        ]);
        box.appendChild(metaRow);
      }

      // Bullets (for non-skills sections)
      if (sec.type !== "skills") {
        var bulletWrap = window.FOSS.dom.el("div", { className: "resume-bullet-wrap" });
        (entry.bullets || []).forEach(function (b, bIdx) {
          var bRow = window.FOSS.dom.el("div", { className: "row resume-bullet-row" }, [
            window.FOSS.dom.el("input", {
              type: "checkbox",
              "data-testid": "resume-bullet-toggle",
              "aria-label": "Toggle bullet point",
              title: "Toggle bullet point",
              checked: Boolean(b.enabled),
              onchange: function (e) {
                b.enabled = e.target.checked;
                schedulePreviewUpdate();
              }
            }),
            window.FOSS.dom.el("input", {
              className: "input resume-flex-auto",
              "data-truncate-ok": "true",
              "aria-label": "Bullet text",
              title: "Bullet text",
              value: b.text || "",
              oninput: function (e) {
                b.text = e.target.value;
                schedulePreviewUpdate();
              }
            }),
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-icon text-danger btn-sm",
              "aria-label": "Delete bullet",
              title: "Delete bullet",
              onclick: function () {
                entry.bullets.splice(bIdx, 1);
                renderLeftPane();
                schedulePreviewUpdate();
              }
            }, [window.FOSS.icons.el("x", 10)])
          ]);
          bulletWrap.appendChild(bRow);
        });

        var addBBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-xs resume-self-start",
          onclick: function () {
            entry.bullets.push({ id: "b_" + (idCounter++), text: "", enabled: true });
            renderLeftPane();
          }
        }, [window.FOSS.icons.el("plus", 10), window.FOSS.dom.el("span", { text: "Add Bullet" })]);

        box.appendChild(bulletWrap);
        box.appendChild(addBBtn);
      }

      return box;
    }

    function renderProfilesView(container) {
      var profileCard = window.FOSS.dom.el("div", { className: "card resume-flex-col-gap-3" }, [
        window.FOSS.dom.el("h3", { className: "card-title", text: "Tailor for Job Posting" }),
        window.FOSS.components.field({
          label: "Active Profile",
          testid: "resume-profile-field",
          control: window.FOSS.dom.el("select", {
            className: "select",
            "data-testid": "resume-profile-select",
            "aria-label": "Active Profile",
            title: "Active Profile",
            onchange: function (e) {
              masterResume.active_profile = e.target.value;
              schedulePreviewUpdate();
            }
          }, [
            window.FOSS.dom.el("option", { value: "Full Master Resume", text: "Full Master Resume" })
          ])
        }),
        window.FOSS.components.field({
          label: "Target Job Description",
          testid: "resume-jd-field",
          control: window.FOSS.dom.el("textarea", {
            className: "input",
            "data-testid": "resume-job-desc-input",
            "aria-label": "Target Job Description",
            title: "Target Job Description",
            rows: 6,
            placeholder: "Paste target job posting requirements and keywords here..."
          })
        }),
        window.FOSS.dom.el("button", {
          className: "btn btn-primary",
          "data-testid": "resume-analyze-ats-btn",
          onclick: function () {
            var jd = container.querySelector("[data-testid='resume-job-desc-input']").value.trim();
            if (!jd) {
              window.FOSS.dialogs.toast("Paste job description text first.");
              return;
            }
            window.FOSS.api("resume_analyze_ats", { resume: masterResume, job_description: jd })
              .then(function (res) {
                var atsBox = container.querySelector("[data-testid='resume-ats-results']");
                atsBox.removeAttribute("hidden");
                atsBox.innerHTML = "";
                var scorePill = window.FOSS.dom.el("div", {
                  className: "badge info text-sm",
                  text: "Keyword Match Score: " + res.score + "%"
                });
                var matchedList = window.FOSS.dom.el("p", {
                  className: "text-xs",
                  text: "Matched (" + (res.matched_keywords || []).length + "): " + (res.matched_keywords || []).join(", ")
                });
                var missingList = window.FOSS.dom.el("p", {
                  className: "text-xs text-muted",
                  text: "Missing (" + (res.missing_keywords || []).length + "): " + (res.missing_keywords || []).join(", ")
                });
                atsBox.appendChild(scorePill);
                atsBox.appendChild(matchedList);
                atsBox.appendChild(missingList);
              });
          }
        }, [window.FOSS.icons.el("activity", 14), window.FOSS.dom.el("span", { text: "Analyze ATS Match" })]),
        window.FOSS.dom.el("div", {
          className: "card card-compact stack resume-section-item",
          "data-testid": "resume-ats-results",
          hidden: true
        })
      ]);

      container.appendChild(profileCard);
    }

    function renderExportView(container) {
      var themeSelect = window.FOSS.dom.el("select", {
        className: "select",
        "data-testid": "resume-theme-select",
        "aria-label": "Theme",
        title: "Theme",
        onchange: function (e) {
          currentTheme = e.target.value;
          schedulePreviewUpdate();
        }
      }, [window.FOSS.dom.el("option", { value: "gnc", text: "UT Austin Engineering Theme", selected: currentTheme === "gnc" })]);
      var dateSelect = window.FOSS.dom.el("select", {
        className: "select",
        "data-testid": "resume-date-format-select",
        "aria-label": "Date format",
        title: "Date format",
        onchange: function (e) {
          currentDateFormat = e.target.value;
          schedulePreviewUpdate();
        }
      }, ["MM/YYYY", "Month YYYY"].map(function (fmt) {
        return window.FOSS.dom.el("option", { value: fmt, text: fmt, selected: currentDateFormat === fmt });
      }));
      var expCard = window.FOSS.dom.el("div", { className: "card resume-flex-col-gap-3" }, [
        window.FOSS.dom.el("h3", { className: "card-title", text: "Export Resume" }),
        window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "Word exports shrink the font until the document fits on one page. The saved file type follows the extension you choose." }),
        window.FOSS.components.field({ label: "Theme", control: themeSelect }),
        window.FOSS.components.field({ label: "Date format", control: dateSelect }),
        window.FOSS.dom.el("div", { className: "row resume-row-gap-2" }, [
          window.FOSS.dom.el("button", {
            className: "btn btn-primary",
            "data-testid": "resume-export-pdf-btn",
            onclick: function () { runExport("pdf"); }
          }, [window.FOSS.icons.el("check", 14), window.FOSS.dom.el("span", { text: "Export PDF..." })]),
          window.FOSS.dom.el("button", {
            className: "btn btn-secondary",
            "data-testid": "resume-export-docx-btn",
            onclick: function () { runExport("docx"); }
          }, [window.FOSS.icons.el("file", 14), window.FOSS.dom.el("span", { text: "Export DOCX..." })]),
          window.FOSS.dom.el("button", {
            className: "btn btn-ghost",
            "data-testid": "resume-export-txt-btn",
            onclick: function () { runExport("txt"); }
          }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Export Text..." })])
        ])
      ]);
      container.appendChild(expCard);
    }

    function runExport(preferredExt) {
      exportResume(preferredExt).then(function (done) {
        if (!done) return;
        var info = done.info || {};
        exportResultHost.removeAttribute("hidden");
        exportResultHost.innerHTML = "";
        exportResultHost.appendChild(window.FOSS.components.resultCard({
          testid: "resume-export-result-card",
          title: "Resume Exported",
          outputPath: done.path,
          details: [
            { label: "Format", value: String(info.format || "").toUpperCase() },
            { label: "Font", value: Number(info.font_pt || 0).toFixed(2) + " pt" },
            { label: "Fits one page", value: info.fits_one_page ? "Yes" : "No" }
          ]
        }));
        window.FOSS.dialogs.toast("Resume exported.");
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Export failed: " + (err.message || err));
      });
    }
  }

  // Register router
  window.FOSS.router.register({
    id: "resume",
    title: "Resume Studio",
    navName: "Resume",
    category: "Documents",
    icon: "resume",
    workbench: true,
    defaults: [
      { key: "theme", label: "Default theme", type: "select", options: [{ value: "gnc", label: "UT Austin Engineering Theme" }], default: "gnc" },
      { key: "date_format", label: "Default date format", type: "select", options: ["MM/YYYY", "Month YYYY"], default: "Month YYYY" },
      {
        key: "font_scale",
        label: "Default font scale",
        type: "select",
        options: [{ value: "11.0", label: "11.0 pt (Standard)" }, { value: "10.5", label: "10.5 pt (Compact)" }, { value: "10.0", label: "10.0 pt (Dense)" }],
        default: "11.0"
      },
      { key: "include_summary", label: "Include professional summary by default", type: "toggle", default: true }
    ],
    description: "UT Austin Engineering Theme resume builder with live document preview and multi-format export.",
    tabs: [
      { id: "personal", label: "Contact & Bio", render: function (p) { renderResumeWorkbench(p, "personal"); } },
      { id: "sections", label: "Sections", render: function (p) { renderResumeWorkbench(p, "sections"); } },
      { id: "profiles", label: "Tailor & ATS", render: function (p) { renderResumeWorkbench(p, "profiles"); } },
      { id: "preview", label: "Preview & Export", render: function (p) { renderResumeWorkbench(p, "preview"); } }
    ]
  });
})();
