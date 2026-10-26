// Resume Studio: local-first master resume management, granular job tailoring, ATS analyzer, and multi-format exporters.
window.FOSS = window.FOSS || {};

(function () {
  var masterResume = {
    name: "Alex Morgan",
    title: "Senior Full-Stack Software Engineer",
    contact: {
      email: "alex.morgan@example.com",
      phone: "+1 (555) 234-5678",
      location: "San Francisco, CA",
      linkedin: "linkedin.com/in/alexmorgan",
      github: "github.com/alexmorgan",
      website: "alexmorgan.dev"
    },
    summary: "Senior software engineer with 8+ years designing fault-tolerant distributed web systems and performant APIs.",
    include_summary: true,
    sections: [
      {
        id: "exp",
        title: "Work Experience",
        entries: [
          {
            id: "e1",
            title: "Lead Backend Engineer",
            organization: "Acme Cloud Platforms",
            dates: "2021 - Present",
            location: "San Francisco, CA",
            enabled: true,
            bullets: [
              { id: "b1", text: "Architected real-time streaming pipeline processing 40k events/sec with sub-50ms latency.", enabled: true },
              { id: "b2", text: "Reduced cloud infrastructure compute costs by 32% through container rightsizing.", enabled: true }
            ]
          }
        ]
      },
      {
        id: "skills",
        title: "Technical Skills",
        entries: [
          {
            id: "s1",
            title: "Languages & Frameworks",
            organization: "Core Competencies",
            dates: "Current",
            location: "",
            enabled: true,
            bullets: [
              { id: "sb1", text: "Python, TypeScript, Go, Rust, React, Node.js, PostgreSQL, Redis, Docker, Kubernetes", enabled: true }
            ]
          }
        ]
      }
    ],
    profiles: {},
    active_profile: "full master resume (default)"
  };

  var historySnapshots = [];
  var currentLayout = "single";
  var currentAccent = "#2563eb";

  function calcStats() {
    var secs = (masterResume.sections || []).length;
    var entries = 0;
    var bullets = 0;
    (masterResume.sections || []).forEach(function (s) {
      var ens = s.entries || [];
      entries += ens.length;
      ens.forEach(function (e) {
        bullets += (e.bullets || []).length;
      });
    });
    return "sections: " + secs + " | entries: " + entries + " | bullets: " + bullets;
  }

  function renderPersonal(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-resume");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Resume Studio" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "build a comprehensive master resume, then check/uncheck bullets and reorder sections to tailor per job."
      })
    ]);

    var offlineBadge = window.FOSS.dom.el("div", {
      className: "badge success text-xs mb-sm",
      "data-testid": "resume-offline-badge",
      text: "100% Offline & Private"
    });

    var statsBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-md",
      "data-testid": "resume-personal-stats",
      text: calcStats()
    });

    var nameInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-name-input",
      "data-truncate-ok": "true",
      "aria-label": "Your name",
      title: "Your name",
      placeholder: "your name",
      value: masterResume.name || ""
    });
    nameInput.oninput = function () { masterResume.name = nameInput.value; };

    var titleInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-title-input",
      "data-truncate-ok": "true",
      "aria-label": "Professional title",
      title: "Professional title",
      placeholder: "professional title",
      value: masterResume.title || ""
    });
    titleInput.oninput = function () { masterResume.title = titleInput.value; };

    var emailInput = window.FOSS.dom.el("input", {
      type: "email",
      className: "input",
      "data-testid": "resume-email-input",
      "data-truncate-ok": "true",
      "aria-label": "Email",
      title: "Email",
      placeholder: "email",
      value: (masterResume.contact && masterResume.contact.email) || ""
    });
    emailInput.oninput = function () { masterResume.contact.email = emailInput.value; };

    var phoneInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-phone-input",
      "data-truncate-ok": "true",
      "aria-label": "Phone",
      title: "Phone",
      placeholder: "phone",
      value: (masterResume.contact && masterResume.contact.phone) || ""
    });
    phoneInput.oninput = function () { masterResume.contact.phone = phoneInput.value; };

    var locInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-location-input",
      "data-truncate-ok": "true",
      "aria-label": "Location (e.g. San Francisco, CA)",
      title: "Location (e.g. San Francisco, CA)",
      placeholder: "location (e.g. san francisco, ca)",
      value: (masterResume.contact && masterResume.contact.location) || ""
    });
    locInput.oninput = function () { masterResume.contact.location = locInput.value; };

    var linkedinInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-linkedin-input",
      "data-truncate-ok": "true",
      "aria-label": "LinkedIn",
      title: "LinkedIn",
      placeholder: "linkedin",
      value: (masterResume.contact && masterResume.contact.linkedin) || ""
    });
    linkedinInput.oninput = function () { masterResume.contact.linkedin = linkedinInput.value; };

    var githubInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-github-input",
      "data-truncate-ok": "true",
      "aria-label": "GitHub",
      title: "GitHub",
      placeholder: "github",
      value: (masterResume.contact && masterResume.contact.github) || ""
    });
    githubInput.oninput = function () { masterResume.contact.github = githubInput.value; };

    var webInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "resume-website-input",
      "data-truncate-ok": "true",
      "aria-label": "Portfolio / website",
      title: "Portfolio / website",
      placeholder: "portfolio / website",
      value: (masterResume.contact && masterResume.contact.website) || ""
    });
    webInput.oninput = function () { masterResume.contact.website = webInput.value; };

    var contactGroup = window.FOSS.dom.el("div", { className: "card mb-md", "data-testid": "resume-contact-card" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "personal & contact details" }),
      window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-sm" }, [
        nameInput,
        titleInput,
        emailInput,
        phoneInput,
        locInput,
        linkedinInput,
        githubInput,
        webInput
      ])
    ]);

    var summaryCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: masterResume.include_summary !== false,
      "data-testid": "resume-summary-check",
      "aria-label": "include summary in tailored resume",
      title: "include summary in tailored resume"
    });
    summaryCheck.onchange = function () { masterResume.include_summary = summaryCheck.checked; };

    var summaryTextarea = window.FOSS.dom.el("textarea", {
      className: "input text-sm",
      rows: 4,
      "data-testid": "resume-summary-textarea",
      "aria-label": "Write a short profile summary for this resume",
      title: "Write a short profile summary for this resume",
      placeholder: "write a short profile summary for this resume",
      value: masterResume.summary || ""
    });
    summaryTextarea.oninput = function () { masterResume.summary = summaryTextarea.value; };

    var summaryGroup = window.FOSS.dom.el("div", { className: "card mb-md", "data-testid": "resume-summary-card" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "executive summary / objective" }),
      window.FOSS.dom.el("label", { className: "row items-center gap-xs text-sm mb-sm", style: "cursor: pointer;" }, [
        summaryCheck,
        window.FOSS.dom.el("span", { text: "include summary in tailored resume" })
      ]),
      summaryTextarea
    ]);

    panel.appendChild(header);
    panel.appendChild(offlineBadge);
    panel.appendChild(statsBar);
    panel.appendChild(contactGroup);
    panel.appendChild(summaryGroup);
  }

  function renderSections(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-resume");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Master Resume Sections & Experience" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "build a comprehensive master resume, then check/uncheck bullets and reorder sections to tailor per job."
      })
    ]);

    var statsBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-md",
      "data-testid": "resume-sections-stats",
      text: calcStats()
    });

    var sectionsHost = window.FOSS.dom.el("div", {
      className: "stack gap-md mb-md",
      "data-testid": "resume-master-mgmt"
    });

    function rebuildSections() {
      sectionsHost.innerHTML = "";
      statsBar.textContent = calcStats();

      (masterResume.sections || []).forEach(function (sec, sIdx) {
        var secTitleInput = window.FOSS.dom.el("input", {
          type: "text",
          className: "input font-semibold text-sm",
          "data-testid": "resume-sec-title-" + sIdx,
          "data-truncate-ok": "true",
          "aria-label": "section title",
          title: "section title",
          placeholder: "section title",
          value: sec.title || ""
        });
        secTitleInput.oninput = function () { sec.title = secTitleInput.value; };

        var moveUpSecBtn = window.FOSS.dom.el("button", {
          className: "btn ghost text-xs",
          "data-testid": "resume-section-reorder",
          "aria-label": "▲ move up",
          title: "▲ move up",
          style: "min-height: 36px;",
          onclick: function () {
            if (sIdx > 0) {
              var tmp = masterResume.sections[sIdx - 1];
              masterResume.sections[sIdx - 1] = masterResume.sections[sIdx];
              masterResume.sections[sIdx] = tmp;
              rebuildSections();
            }
          }
        }, [window.FOSS.dom.el("span", { text: "▲ move up" })]);

        var moveDownSecBtn = window.FOSS.dom.el("button", {
          className: "btn ghost text-xs",
          "aria-label": "▼ move down",
          title: "▼ move down",
          style: "min-height: 36px;",
          onclick: function () {
            if (sIdx < masterResume.sections.length - 1) {
              var tmp = masterResume.sections[sIdx + 1];
              masterResume.sections[sIdx + 1] = masterResume.sections[sIdx];
              masterResume.sections[sIdx] = tmp;
              rebuildSections();
            }
          }
        }, [window.FOSS.dom.el("span", { text: "▼ move down" })]);

        var delSecBtn = window.FOSS.dom.el("button", {
          className: "btn ghost text-xs text-danger",
          "aria-label": "delete section",
          title: "delete section",
          style: "min-height: 36px;",
          onclick: function () {
            masterResume.sections.splice(sIdx, 1);
            rebuildSections();
          }
        }, [window.FOSS.dom.el("span", { text: "delete section" })]);

        var secHeader = window.FOSS.dom.el("div", { className: "row items-center justify-between gap-sm mb-sm flex-wrap" }, [
          secTitleInput,
          window.FOSS.dom.el("div", { className: "row gap-xs" }, [moveUpSecBtn, moveDownSecBtn, delSecBtn])
        ]);

        var entriesHost = window.FOSS.dom.el("div", { className: "stack gap-sm pl-sm" });

        (sec.entries || []).forEach(function (ent, eIdx) {
          var entCheck = window.FOSS.dom.el("input", {
            type: "checkbox",
            checked: ent.enabled !== false,
            "aria-label": "enable entry",
            title: "enable entry"
          });
          entCheck.onchange = function () { ent.enabled = entCheck.checked; };

          var entTitleInput = window.FOSS.dom.el("input", {
            type: "text",
            className: "input text-xs",
            "data-truncate-ok": "true",
            "aria-label": "job title / degree / project name",
            title: "job title / degree / project name",
            placeholder: "job title / degree / project name",
            value: ent.title || "",
            style: "flex: 1;"
          });
          entTitleInput.oninput = function () { ent.title = entTitleInput.value; };

          var orgInput = window.FOSS.dom.el("input", {
            type: "text",
            className: "input text-xs",
            "data-truncate-ok": "true",
            "aria-label": "company / institution / tech",
            title: "company / institution / tech",
            placeholder: "company / institution / tech",
            value: ent.organization || "",
            style: "flex: 1;"
          });
          orgInput.oninput = function () { ent.organization = orgInput.value; };

          var datesInput = window.FOSS.dom.el("input", {
            type: "text",
            className: "input text-xs",
            "data-truncate-ok": "true",
            "aria-label": "dates (e.g. 2022 - present)",
            title: "dates (e.g. 2022 - present)",
            placeholder: "dates (e.g. 2022 - present)",
            value: ent.dates || "",
            style: "width: 140px;"
          });
          datesInput.oninput = function () { ent.dates = datesInput.value; };

          var entLocInput = window.FOSS.dom.el("input", {
            type: "text",
            className: "input text-xs",
            "data-truncate-ok": "true",
            "aria-label": "location",
            title: "location",
            placeholder: "location",
            value: ent.location || "",
            style: "width: 130px;"
          });
          entLocInput.oninput = function () { ent.location = entLocInput.value; };

          var delEntBtn = window.FOSS.dom.el("button", {
            className: "btn ghost text-xs",
            "aria-label": "delete entry",
            title: "delete entry",
            style: "min-height: 36px;",
            onclick: function () {
              sec.entries.splice(eIdx, 1);
              rebuildSections();
            }
          }, [window.FOSS.dom.el("span", { text: "delete entry" })]);

          var entRow = window.FOSS.dom.el("div", { className: "row gap-xs items-center flex-wrap mb-xs" }, [
            entCheck,
            entTitleInput,
            orgInput,
            datesInput,
            entLocInput,
            delEntBtn
          ]);

          var bulletsHost = window.FOSS.dom.el("div", { className: "stack gap-xs pl-md mb-xs" }, [
            window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "bullet points (check to include in tailored resume)" })
          ]);

          (ent.bullets || []).forEach(function (b, bIdx) {
            var bCheck = window.FOSS.dom.el("input", {
              type: "checkbox",
              checked: b.enabled !== false,
              "data-testid": "resume-bullet-toggle",
              "aria-label": "Include bullet point",
              title: "Include bullet point"
            });
            bCheck.onchange = function () { b.enabled = bCheck.checked; };

            var bInput = window.FOSS.dom.el("input", {
              type: "text",
              className: "input text-xs",
              "data-truncate-ok": "true",
              "aria-label": "Bullet text",
              title: "Bullet text",
              placeholder: "bullet text (e.g. achieved 40% performance gain by...)",
              value: b.text || "",
              style: "flex: 1;"
            });
            bInput.oninput = function () { b.text = bInput.value; };

            var delBulletBtn = window.FOSS.dom.el("button", {
              className: "btn ghost text-xs",
              "aria-label": "x",
              title: "x",
              style: "min-width: 36px; min-height: 36px; padding: 2px 8px;",
              onclick: function () {
                ent.bullets.splice(bIdx, 1);
                rebuildSections();
              }
            }, [window.FOSS.dom.el("span", { text: "x" })]);

            bulletsHost.appendChild(window.FOSS.dom.el("div", { className: "row gap-xs items-center" }, [
              bCheck,
              bInput,
              delBulletBtn
            ]));
          });

          var addBulletBtn = window.FOSS.dom.el("button", {
            className: "btn ghost text-xs",
            "data-testid": "resume-add-bullet-btn",
            "aria-label": "add bullet",
            title: "add bullet",
            style: "min-height: 36px; align-self: flex-start;",
            onclick: function () {
              ent.bullets = ent.bullets || [];
              ent.bullets.push({ id: "b" + Date.now(), text: "", enabled: true });
              rebuildSections();
            }
          }, [window.FOSS.dom.el("span", { text: "add bullet" })]);

          var entCard = window.FOSS.dom.el("div", { className: "border rounded p-sm mb-sm" }, [
            entRow,
            bulletsHost,
            addBulletBtn
          ]);
          entriesHost.appendChild(entCard);
        });

        var addEntBtn = window.FOSS.dom.el("button", {
          className: "btn secondary text-xs",
          "aria-label": "add role / item to section",
          title: "add role / item to section",
          style: "min-height: 36px; margin-top: 6px;",
          onclick: function () {
            sec.entries = sec.entries || [];
            sec.entries.push({ id: "e" + Date.now(), title: "", organization: "", dates: "", location: "", enabled: true, bullets: [] });
            rebuildSections();
          }
        }, [window.FOSS.dom.el("span", { text: "add role / item to section" })]);

        var secCard = window.FOSS.dom.el("div", { className: "card mb-md", "data-testid": "resume-section-card" }, [
          secHeader,
          entriesHost,
          addEntBtn
        ]);
        sectionsHost.appendChild(secCard);
      });
    }

    var addSecBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "resume-add-sec-btn",
      "aria-label": "add new section (experience, projects, skills, education, custom)",
      title: "add new section (experience, projects, skills, education, custom)",
      style: "min-height: 36px;",
      onclick: function () {
        masterResume.sections = masterResume.sections || [];
        masterResume.sections.push({ id: "sec_" + Date.now(), title: "New Section", entries: [] });
        rebuildSections();
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "add new section (experience, projects, skills, education, custom)" })
    ]);

    panel.appendChild(header);
    panel.appendChild(statsBar);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row mb-md" }, [addSecBtn]));
    panel.appendChild(sectionsHost);

    rebuildSections();
  }

  function renderProfiles(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-resume");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Job Tailoring Profiles & ATS Match" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Save tailored sub-configurations and calculate automated ATS keyword relevance scores."
      })
    ]);

    var profileSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "resume-profile-select",
      "aria-label": "job tailoring profile",
      title: "job tailoring profile"
    }, [
      window.FOSS.dom.el("option", { value: "full master resume (default)", text: "full master resume (default)" })
    ]);

    var profileCard = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "job tailoring profile" }),
      window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-sm" }, [profileSelect])
    ]);

    var jobDescTextarea = window.FOSS.dom.el("textarea", {
      className: "input font-mono text-sm",
      rows: 6,
      "data-testid": "resume-job-desc-input",
      "aria-label": "paste job posting requirements, skills, and qualifications here",
      title: "paste job posting requirements, skills, and qualifications here",
      placeholder: "paste job posting requirements, skills, and qualifications here"
    });

    var atsResultHost = window.FOSS.dom.el("div", {
      className: "hidden p-md border rounded mt-sm",
      "data-testid": "resume-ats-results"
    });

    var analyzeBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "resume-analyze-ats-btn",
      "aria-label": "analyze ats match score & missing keywords",
      title: "analyze ats match score & missing keywords",
      style: "min-height: 36px;",
      onclick: function () {
        var desc = jobDescTextarea.value.trim();
        if (!desc) {
          window.FOSS.toast.show({ message: "Please paste a job description first.", type: "warning" });
          return;
        }
        window.FOSS.api("resume_analyze_ats", { resume: masterResume, job_description: desc }).then(function (res) {
          if (res && res.score !== undefined) {
            atsResultHost.innerHTML = "";
            var scoreBadge = window.FOSS.dom.el("div", { className: "text-xl font-bold mb-xs", text: "ATS Match Score: " + res.score + "%" });
            var matchedText = window.FOSS.dom.el("div", { className: "text-xs mb-xs text-success", text: "Matched Keywords: " + ((res.matched_keywords || []).slice(0, 15).join(", ") || "None") });
            var missingText = window.FOSS.dom.el("div", { className: "text-xs text-danger", text: "Missing Keywords: " + ((res.missing_keywords || []).slice(0, 15).join(", ") || "None") });
            atsResultHost.appendChild(scoreBadge);
            atsResultHost.appendChild(matchedText);
            atsResultHost.appendChild(missingText);
            atsResultHost.classList.remove("hidden");
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "analyze ats match score & missing keywords" })]);

    var atsCard = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "paste target job description" }),
      window.FOSS.dom.el("div", { className: "field mb-sm" }, [jobDescTextarea]),
      analyzeBtn,
      atsResultHost
    ]);

    panel.appendChild(header);
    panel.appendChild(profileCard);
    panel.appendChild(atsCard);
  }

  function renderPreview(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-resume");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Live Preview & Export" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Review HTML preview and export to PDF, Word DOCX, Markdown, or clipboard."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "resume-preview-status",
      text: "Rendering preview..."
    });

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden mb-sm",
      "data-testid": "resume-export-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "resume-result-card",
        title: titleText || "Resume Exported",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var previewFrame = window.FOSS.dom.el("iframe", {
      className: "w-full border rounded mb-md",
      style: "height: 480px; background: white;",
      "data-testid": "resume-preview-iframe"
    });

    function updatePreview() {
      statusBar.textContent = "Rendering preview...";
      window.FOSS.api("resume_render_html", {
        resume: masterResume,
        layout: currentLayout,
        accent_color: currentAccent
      }).then(function (res) {
        if (res && res.html) {
          previewFrame.srcdoc = res.html;
          statusBar.textContent = "Preview updated";
        }
      });
    }

    var layoutSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "resume-layout-select",
      "aria-label": "Layout template",
      title: "Layout template",
      onchange: function () {
        currentLayout = layoutSelect.value;
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "single", text: "Standard Single-Column" }),
      window.FOSS.dom.el("option", { value: "two_column", text: "Modern Dual-Column" })
    ]);
    layoutSelect.value = currentLayout;

    var themeSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "resume-theme-select",
      "aria-label": "Accent theme",
      title: "Accent theme",
      onchange: function () {
        currentAccent = themeSelect.value;
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "#2563eb", text: "Classic Navy Blue" }),
      window.FOSS.dom.el("option", { value: "#059669", text: "Emerald Green" }),
      window.FOSS.dom.el("option", { value: "#7c3aed", text: "Royal Violet" }),
      window.FOSS.dom.el("option", { value: "#1f2937", text: "Slate Charcoal" })
    ]);
    themeSelect.value = currentAccent;

    var exportPdfBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "resume-export-pdf-btn",
      "aria-label": "Export PDF",
      title: "Export PDF",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.api("select_save_path", { title: "Save Resume PDF", default_name: "resume.pdf" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("resume_export_pdf", {
            resume: masterResume,
            output_path: outP,
            layout: currentLayout,
            accent_color: currentAccent
          }).then(function (res) {
            if (res && res.output_path) {
              showResult(res.output_path, "PDF Resume Exported");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Export PDF" })
    ]);

    var exportDocxBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "resume-export-docx-btn",
      "aria-label": "Export Word DOCX",
      title: "Export Word DOCX",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.api("select_save_path", { title: "Save Word DOCX Resume", default_name: "resume.docx" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("resume_export_docx", {
            resume: masterResume,
            output_path: outP
          }).then(function (res) {
            if (res && res.output_path) {
              showResult(res.output_path, "Word DOCX Resume Exported");
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Export Word (DOCX)" })]);

    var exportMdBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "resume-export-md-btn",
      "aria-label": "Export Markdown",
      title: "Export Markdown",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.api("select_save_path", { title: "Save Markdown Resume", default_name: "resume.md" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("resume_export_markdown", {
            resume: masterResume,
            output_path: outP
          }).then(function (res) {
            if (res && res.output_path) {
              showResult(res.output_path, "Markdown Resume Saved");
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Export Markdown" })]);

    var copyTxtBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "resume-copy-txt-btn",
      "aria-label": "Copy plain text",
      title: "Copy plain text",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.api("resume_export_markdown", { resume: masterResume }).then(function (res) {
          if (res && res.markdown) {
            navigator.clipboard.writeText(res.markdown).then(function () {
              window.FOSS.toast.show({ message: "Tailored text copied to clipboard.", type: "success" });
            });
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Copy Plain Text" })]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-md flex-wrap" }, [
      layoutSelect,
      themeSelect,
      exportPdfBtn,
      exportDocxBtn,
      exportMdBtn,
      copyTxtBtn
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(resultHost);
    panel.appendChild(controlsRow);
    panel.appendChild(previewFrame);

    updatePreview();
  }

  function renderHistory(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-resume");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Version History & Revision Diffing" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Save job tailoring snapshots and compare prior versions."
      })
    ]);

    var snapshotBtn = window.FOSS.dom.el("button", {
      className: "btn primary mb-md",
      "data-testid": "resume-snapshot-btn",
      "aria-label": "Save version snapshot",
      title: "Save version snapshot",
      style: "min-height: 36px;",
      onclick: function () {
        historySnapshots.push({
          timestamp: new Date().toLocaleTimeString(),
          title: "Snapshot #" + (historySnapshots.length + 1),
          resume: JSON.parse(JSON.stringify(masterResume))
        });
        window.FOSS.toast.show({ message: "Snapshot saved. Total: " + historySnapshots.length, type: "success" });
        loadHistoryList();
      }
    }, [
      window.FOSS.icons.el("camera", 16),
      window.FOSS.dom.el("span", { text: "Save Version Snapshot" })
    ]);

    var diffHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "resume-history-diff"
    });

    function loadHistoryList() {
      diffHost.innerHTML = "";
      if (!historySnapshots.length) {
        diffHost.appendChild(window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "No snapshots saved yet. Click Save Version Snapshot above." }));
        return;
      }
      historySnapshots.forEach(function (snap, idx) {
        diffHost.appendChild(window.FOSS.dom.el("div", { className: "row justify-between items-center text-xs py-xs border-b" }, [
          window.FOSS.dom.el("span", { className: "font-semibold", text: snap.title + " (" + snap.timestamp + ")" }),
          window.FOSS.dom.el("button", {
            className: "btn ghost text-xs",
            "aria-label": "Restore",
            title: "Restore",
            style: "min-height: 36px;",
            onclick: function () {
              masterResume = JSON.parse(JSON.stringify(snap.resume));
              window.FOSS.toast.show({ message: "Restored " + snap.title, type: "info" });
            }
          }, [window.FOSS.dom.el("span", { text: "Restore" })])
        ]));
      });
    }

    panel.appendChild(header);
    panel.appendChild(snapshotBtn);
    panel.appendChild(diffHost);

    loadHistoryList();
  }

  window.FOSS.router.register({
    id: "resume",
    title: "Resume Studio",
    navName: "Resume",
    category: "documents",
    icon: "file-text",
    tabs: [
      { id: "personal", label: "Personal & Contact", render: renderPersonal },
      { id: "sections", label: "Sections & Experience", render: renderSections },
      { id: "profiles", label: "Job Tailoring Profiles", render: renderProfiles },
      { id: "preview", label: "Live Preview & Export", render: renderPreview },
      { id: "history", label: "Version History", render: renderHistory }
    ]
  });
})();
