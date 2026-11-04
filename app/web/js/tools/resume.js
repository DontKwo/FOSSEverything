// Resume Studio: local-first master resume management, SpaceX GNC format, live preview, and exporters.
window.FOSS = window.FOSS || {};

(function () {
  var masterResume = {
    contact: {
      name: "Alex Morgan",
      title: "Guidance, Navigation, and Control Engineer",
      email: "alex.morgan@utexas.edu",
      phone: "(512) 555-0199",
      location: "Austin, TX",
      linkedin: "linkedin.com/in/alexmorgan-aero",
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
            title: "Bachelor of Science, Aerospace Engineering Honors",
            subtitle: "The University of Texas at Austin",
            date_range: "December 2026",
            gpa: "3.94 / 4.00",
            coursework: "Orbital Mechanics, Spacecraft Dynamics & Control, Flight Mechanics, Numerical Methods",
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
            title: "Guidance, Navigation, and Control Intern",
            subtitle: "Space Exploration Technologies (SpaceX)",
            date_range: "May 2025 - August 2025",
            enabled: true,
            bullets: [
              { id: "b1", text: "Designed and validated 6-DOF entry guidance Monte Carlo simulations in C++ and Python.", enabled: true },
              { id: "b2", text: "Implemented quaternion-based attitude estimation filters integrating IMU and star tracker telemetry.", enabled: true }
            ]
          }
        ]
      },
      {
        id: "sec_skills",
        type: "skills",
        title: "ADDITIONAL SKILLS AND LANGUAGES",
        enabled: true,
        entries: [
          {
            id: "sk_1",
            title: "Simulation & Analysis",
            skills_text: "C++, Python, MATLAB, Simulink, ROS 2, PyMuPDF, Linux/POSIX",
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
  var resumeZoom = 1.0;
  var idCounter = 100;

  function schedulePreviewUpdate() {
    if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(function () {
      fetchLivePreview();
    }, 180);
  }

  function fetchLivePreview() {
    if (!previewStageEl) return;
    var payload = {
      resume: masterResume,
      font_pt: currentFontPt,
      dpi: 160
    };
    if (masterResume.active_profile && masterResume.active_profile !== "Full Master Resume") {
      payload.profile = masterResume.active_profile;
    }
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
        pageBadgeEl.className = "badge badge-success text-xs";
        pageBadgeEl.textContent = "1 Page (Fits Cleanly)";
      } else {
        pageBadgeEl.className = "badge badge-warning text-xs";
        pageBadgeEl.textContent = pageCount + " Pages (Overflow)";
      }
    }
    pages.forEach(function (pageUrl, pIdx) {
      var img = window.FOSS.dom.el("img", {
        className: "resume-page-sheet",
        "data-testid": "resume-preview-page-" + pIdx,
        "data-overlay": "true",
        src: pageUrl,
        alt: "Resume Page " + (pIdx + 1)
      });
      if (resumeZoom !== 1.0) {
        img.style.setProperty("transform", "scale(" + resumeZoom + ")");
        img.style.setProperty("transform-origin", "top center");
      }
      previewStageEl.appendChild(img);
    });
  }

  function applyResumeZoom() {
    if (!previewStageEl) return;
    var imgs = previewStageEl.querySelectorAll(".resume-page-sheet");
    imgs.forEach(function (img) {
      if (resumeZoom !== 1.0) {
        img.style.setProperty("transform", "scale(" + resumeZoom + ")");
        img.style.setProperty("transform-origin", "top center");
      } else {
        img.style.removeProperty("transform");
        img.style.removeProperty("transform-origin");
      }
    });
    var label = document.getElementById("resume-zoom-label");
    if (label) label.textContent = Math.round(resumeZoom * 100) + "%";
  }

  function renderResumeWorkbench(panel, requestedView) {
    panel.innerHTML = "";
    if (requestedView) activeSubView = requestedView;

    // Top action bar
    var topBar = window.FOSS.dom.el("div", {
      className: "row-between",
      style: "margin-bottom: var(--space-2); flex-wrap: wrap; gap: var(--space-2); flex-shrink: 0;"
    }, [
      window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2); flex-wrap: wrap;" }, [
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
                if (res && res.file_path) {
                  return window.FOSS.api("resume_load_file", { file_path: res.file_path });
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
              default_filename: "master_resume.json",
              file_types: [["JSON Files", "*.json"]]
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
                  window.FOSS.dialogs.toast("SpaceX GNC sample loaded.");
                }
              });
          }
        }, [window.FOSS.icons.el("refresh-cw", 12), window.FOSS.dom.el("span", { text: "Load Sample" })])
      ]),
      window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
        pageBadgeEl = window.FOSS.dom.el("span", {
          className: "badge badge-success text-xs",
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

    // Sub-view selector on Left Pane
    var subNav = window.FOSS.components.segmented({
      testid: "resume-subnav",
      options: [
        { id: "personal", label: "Contact & Bio" },
        { id: "sections", label: "Sections" },
        { id: "profiles", label: "Tailor & ATS" },
        { id: "preview", label: "Export" }
      ],
      value: activeSubView,
      onChange: function (val) {
        activeSubView = val;
        renderLeftPane();
      }
    });

    var editorContent = window.FOSS.dom.el("div", { style: "display: flex; flex-direction: column; gap: var(--space-3);" });
    leftPane.appendChild(subNav.el);
    leftPane.appendChild(editorContent);

    function renderLeftPane() {
      editorContent.innerHTML = "";
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
    var previewToolbar = window.FOSS.dom.el("div", { className: "row-between", style: "gap: var(--space-2); flex-wrap: wrap;" }, [
      window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2); align-items: center;" }, [
        window.FOSS.dom.el("span", { className: "text-xs font-semibold text-muted", text: "Font:" }),
        window.FOSS.dom.el("select", {
          className: "select",
          "data-testid": "resume-font-pt-select",
          onchange: function (e) {
            currentFontPt = parseFloat(e.target.value) || 11.0;
            schedulePreviewUpdate();
          }
        }, [
          window.FOSS.dom.el("option", { value: "11.0", text: "11.0 pt (Standard)", selected: true }),
          window.FOSS.dom.el("option", { value: "10.5", text: "10.5 pt (Compact)" }),
          window.FOSS.dom.el("option", { value: "10.0", text: "10.0 pt (Dense)" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "resume-zoom-out",
          title: "Zoom Out",
          onclick: function () {
            resumeZoom = Math.max(0.5, Math.round((resumeZoom - 0.1) * 10) / 10);
            applyResumeZoom();
          }
        }, [window.FOSS.icons.el("minus", 12)]),
        window.FOSS.dom.el("span", {
          className: "text-xs font-mono text-muted",
          id: "resume-zoom-label",
          text: Math.round(resumeZoom * 100) + "%"
        }),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "resume-zoom-in",
          title: "Zoom In",
          onclick: function () {
            resumeZoom = Math.min(2.0, Math.round((resumeZoom + 0.1) * 10) / 10);
            applyResumeZoom();
          }
        }, [window.FOSS.icons.el("plus", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "resume-zoom-reset",
          title: "Reset Zoom",
          onclick: function () {
            resumeZoom = 1.0;
            applyResumeZoom();
          }
        }, [window.FOSS.icons.el("refresh-cw", 12)])
      ]),
      window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "resume-export-md-btn",
          onclick: function () {
            exportMarkdown();
          }
        }, [window.FOSS.icons.el("file-text", 12), window.FOSS.dom.el("span", { text: "Markdown" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "resume-export-docx-btn",
          onclick: function () {
            exportDocx();
          }
        }, [window.FOSS.icons.el("file", 12), window.FOSS.dom.el("span", { text: "Word (.docx)" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-primary btn-sm",
          "data-testid": "resume-export-pdf-btn",
          onclick: function () {
            exportPdf();
          }
        }, [window.FOSS.icons.el("check", 12), window.FOSS.dom.el("span", { text: "Export PDF" })])
      ])
    ]);

    previewStageEl = window.FOSS.dom.el("div", {
      className: "resume-preview-stage",
      "data-testid": "resume-preview-stage"
    });

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
    fetchLivePreview();

    // --- Sub-views Implementations ------------------------------------------

    function renderPersonalView(container) {
      var contactCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "resume-contact-card" }, [
        window.FOSS.dom.el("h3", { className: "card-title", text: "Contact Details", style: "margin-bottom: var(--space-2);" }),
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
        window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
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
        window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
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
        window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
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
        window.FOSS.dom.el("div", { className: "row-between", style: "margin-bottom: var(--space-2);" }, [
          window.FOSS.dom.el("h3", { className: "card-title", text: "Professional Summary" }),
          window.FOSS.dom.el("label", { className: "row", style: "gap: var(--space-1); cursor: pointer;" }, [
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
        className: "row-between card",
        "data-testid": "resume-master-mgmt",
        style: "padding: var(--space-2) var(--space-3);"
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
          className: "card",
          style: "display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-3);"
        });

        var secHeader = window.FOSS.dom.el("div", { className: "row-between", style: "gap: var(--space-2);" });
        var secTitleInput = window.FOSS.dom.el("input", {
          className: "input font-semibold",
          "data-truncate-ok": "true",
          "aria-label": "Section Title",
          title: "Section Title",
          value: sec.title,
          style: "flex: 1 1 auto;",
          oninput: function (e) {
            sec.title = e.target.value;
            schedulePreviewUpdate();
          }
        });
        var secTypeSelect = window.FOSS.dom.el("select", {
          className: "select",
          "aria-label": "Section Type",
          title: "Section Type",
          style: "width: 10rem;",
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
        style: "border: 1px solid var(--border); border-radius: var(--radius-sm); padding: var(--space-2); background: var(--bg-sunken); display: flex; flex-direction: column; gap: var(--space-2);"
      });

      var topRow = window.FOSS.dom.el("div", { className: "row-between", style: "gap: var(--space-2);" });
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
        className: "input font-semibold",
        style: "flex: 1 1 auto;",
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
        var eduRow = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
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
            className: "input",
            style: "width: 10rem;",
            "data-truncate-ok": "true",
            "aria-label": "Graduation Date",
            title: "Graduation Date",
            placeholder: "Graduation Date",
            value: entry.date_range || "",
            oninput: function (e) { entry.date_range = e.target.value; schedulePreviewUpdate(); }
          })
        ]);
        var gpaRow = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
          window.FOSS.dom.el("input", {
            className: "input",
            style: "width: 10rem;",
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
        var metaRow = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
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
            className: "input",
            style: "width: 12rem;",
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
        var bulletWrap = window.FOSS.dom.el("div", { style: "display: flex; flex-direction: column; gap: var(--space-1);" });
        (entry.bullets || []).forEach(function (b, bIdx) {
          var bRow = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-1);" }, [
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
              className: "input",
              style: "flex: 1 1 auto;",
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
          className: "btn btn-ghost btn-xs",
          style: "align-self: flex-start;",
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
      var profileCard = window.FOSS.dom.el("div", { className: "card", style: "display: flex; flex-direction: column; gap: var(--space-3);" }, [
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
                  className: "badge badge-primary text-sm",
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
          className: "card card-compact",
          "data-testid": "resume-ats-results",
          style: "display: flex; flex-direction: column; gap: var(--space-2);",
          hidden: true
        })
      ]);

      container.appendChild(profileCard);
    }

    function renderExportView(container) {
      var expCard = window.FOSS.dom.el("div", { className: "card", style: "display: flex; flex-direction: column; gap: var(--space-3);" }, [
        window.FOSS.dom.el("h3", { className: "card-title", text: "Export Resume" }),
        window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "Export formatted resume in PDF, Word (.docx), or structured Markdown." }),
        window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
          window.FOSS.dom.el("button", {
            className: "btn btn-primary",
            "data-testid": "resume-export-pdf-btn-view",
            onclick: exportPdf
          }, [window.FOSS.icons.el("check", 14), window.FOSS.dom.el("span", { text: "Export PDF..." })]),
          window.FOSS.dom.el("button", {
            className: "btn btn-secondary",
            "data-testid": "resume-export-docx-btn",
            onclick: exportDocx
          }, [window.FOSS.icons.el("file", 14), window.FOSS.dom.el("span", { text: "Export DOCX..." })]),
          window.FOSS.dom.el("button", {
            className: "btn btn-ghost",
            onclick: exportMarkdown
          }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Export Markdown..." })])
        ])
      ]);
      container.appendChild(expCard);
    }

    function exportPdf() {
      window.FOSS.api("select_save_path", {
        title: "Export Resume PDF",
        default_name: "resume.pdf",
        filter: "pdf",
        file_types: [["PDF Documents", "*.pdf"]]
      }).then(function (res) {
        var savePath = res && (res.file_path || res.path || res.output_path);
        if (!savePath) return;
        if (!savePath.toLowerCase().endsWith(".pdf")) {
          savePath = savePath + ".pdf";
        }
        return window.FOSS.api("resume_export_pdf", {
          resume: masterResume,
          output_path: savePath,
          font_pt: currentFontPt
        }).then(function () {
          window.FOSS.dialogs.toast("PDF exported successfully.");
        });
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Export PDF failed: " + (err.message || err));
      });
    }

    function exportDocx() {
      window.FOSS.api("select_save_path", {
        title: "Export Resume DOCX",
        default_name: "resume.docx",
        filter: "docx",
        file_types: [["Word Documents", "*.docx"]]
      }).then(function (res) {
        var savePath = res && (res.file_path || res.path || res.output_path);
        if (!savePath) return;
        if (!savePath.toLowerCase().endsWith(".docx")) {
          savePath = savePath + ".docx";
        }
        return window.FOSS.api("resume_export_docx", {
          resume: masterResume,
          output_path: savePath
        }).then(function () {
          window.FOSS.dialogs.toast("DOCX exported successfully.");
        });
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Export DOCX failed: " + (err.message || err));
      });
    }

    function exportMarkdown() {
      window.FOSS.api("select_save_path", {
        title: "Export Resume Markdown",
        default_filename: (masterResume.contact.name || "resume").replace(/\s+/g, "_") + ".md",
        file_types: [["Markdown Files", "*.md"]]
      }).then(function (res) {
        if (!res || !res.file_path) return;
        return window.FOSS.api("resume_export_markdown", {
          resume: masterResume,
          output_path: res.file_path
        }).then(function () {
          exportResultHost.removeAttribute("hidden");
          exportResultHost.innerHTML = "";
          exportResultHost.appendChild(window.FOSS.components.resultCard({
            testid: "resume-export-result-card",
            title: "Markdown Exported",
            outputPath: res.file_path
          }));
          window.FOSS.dialogs.toast("Markdown exported successfully.");
        });
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Export Markdown failed: " + (err.message || err));
      });
    }
  }

  // Register router
  window.FOSS.router.register({
    id: "resume",
    title: "Resume Studio",
    navName: "Resume",
    category: "Documents",
    icon: "award",
    workbench: true,
    description: "SpaceX GNC format resume builder with live document preview and multi-format export.",
    tabs: [
      { id: "personal", label: "Contact & Bio", render: function (p) { renderResumeWorkbench(p, "personal"); } },
      { id: "sections", label: "Sections", render: function (p) { renderResumeWorkbench(p, "sections"); } },
      { id: "profiles", label: "Tailor & ATS", render: function (p) { renderResumeWorkbench(p, "profiles"); } },
      { id: "preview", label: "Preview & Export", render: function (p) { renderResumeWorkbench(p, "preview"); } }
    ]
  });
})();
