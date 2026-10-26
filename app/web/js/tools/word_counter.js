// Word counter and document analytics workspace: stats, readability, and keyword density.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";

    var headerRow = window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
      window.FOSS.dom.el("h3", {
        className: "brand-name",
        text: "Word Counter & Document Analytics"
      })
    ]);

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "word_counter-open-file",
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
            loadFile(res.paths[0]);
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Open File (PDF, DOCX, XLSX, PPTX, TXT)..." })
    ]);

    var pasteBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "word_counter-paste",
      type: "button",
      onClick: function () {
        navigator.clipboard.readText().then(function (clip) {
          if (clip) {
            editor.setValue(clip);
          }
        }).catch(function () {});
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Paste Clipboard" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "word_counter-clear",
      type: "button",
      onClick: function () {
        editor.setValue("");
      }
    }, [
      window.FOSS.icons.el("close", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "word_counter-export-report",
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

    // Stat badges
    function makeStatBadge(title, defaultVal, testid) {
      var valEl = window.FOSS.dom.el("div", {
        className: "text-xl font-bold",
        text: defaultVal,
        "data-testid": testid + "-val"
      });
      var titleEl = window.FOSS.dom.el("div", {
        className: "text-xs text-muted",
        text: title
      });
      var card = window.FOSS.dom.el("div", {
        className: "card stack center",
        gap: "xs",
        "data-testid": testid
      }, [valEl, titleEl]);
      return { el: card, valEl: valEl };
    }

    var badgeWords = makeStatBadge("Words", "0", "word_counter-stat-words");
    var badgeChars = makeStatBadge("Characters", "0", "word_counter-stat-chars");
    var badgeCharsNs = makeStatBadge("Chars (No Space)", "0", "word_counter-stat-chars-ns");
    var badgeSentences = makeStatBadge("Sentences", "0", "word_counter-stat-sentences");
    var badgeParagraphs = makeStatBadge("Paragraphs", "0", "word_counter-stat-paragraphs");
    var badgeReadTime = makeStatBadge("Reading Time", "0s", "word_counter-stat-read-time");
    var badgeSpeakTime = makeStatBadge("Speaking Time", "0s", "word_counter-stat-speak-time");

    var badgesGrid = window.FOSS.dom.el("div", {
      className: "grid-auto",
      "data-min": "100"
    }, [
      badgeWords.el,
      badgeChars.el,
      badgeCharsNs.el,
      badgeSentences.el,
      badgeParagraphs.el,
      badgeReadTime.el,
      badgeSpeakTime.el
    ]);

    // Readability metrics
    var readingEaseVal = window.FOSS.dom.el("span", {
      className: "font-mono font-bold",
      "data-testid": "word_counter-readability-ease-val",
      text: "100.0 / 100"
    });
    var gradeLevelVal = window.FOSS.dom.el("span", {
      className: "font-mono",
      "data-testid": "word_counter-readability-grade-val",
      text: "5th Grade - Very Easy"
    });
    var pagesEstVal = window.FOSS.dom.el("span", {
      className: "font-mono",
      "data-testid": "word_counter-readability-pages-val",
      text: "0.0 pages"
    });
    var avgWordLenVal = window.FOSS.dom.el("span", {
      className: "font-mono",
      "data-testid": "word_counter-readability-word-len-val",
      text: "0.0 chars"
    });
    var avgSentLenVal = window.FOSS.dom.el("span", {
      className: "font-mono",
      "data-testid": "word_counter-readability-sent-len-val",
      text: "0.0 words"
    });

    var readabilityCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Readability & structure" }),
      window.FOSS.dom.el("div", { className: "stack", gap: "xs" }, [
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted text-xs", text: "Reading Ease:" }),
          readingEaseVal
        ]),
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted text-xs", text: "Grade Level:" }),
          gradeLevelVal
        ]),
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted text-xs", text: "Estimated Pages:" }),
          pagesEstVal
        ]),
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted text-xs", text: "Avg Word Length:" }),
          avgWordLenVal
        ]),
        window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted text-xs", text: "Avg Sentence Length:" }),
          avgSentLenVal
        ])
      ])
    ]);

    // Keywords table
    var kwTable = window.FOSS.components.table({
      testid: "word_counter-keywords-table",
      columns: [
        { key: "word", title: "Word" },
        { key: "count", title: "Count" },
        { key: "density_pct", title: "Density", render: function (val) { return val + "%"; } }
      ],
      rows: []
    });

    var keywordsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "xs"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Keyword density (top words)" }),
      kwTable.el
    ]);

    // Editor
    var debounceTimer = null;

    var editor = window.FOSS.components.codeEditor({
      testid: "word_counter-editor",
      title: "Document text",
      placeholder: "Type, paste text, or open any document (PDF, Word, Excel, PowerPoint, Text, Markdown) to analyze stats in real-time...",
      onChange: function (val) {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
          updateStats(val);
        }, 150);
      }
    });

    function updateStats(text) {
      window.FOSS.api("word_counter_analyze", { text: text || "" }).then(function (res) {
        if (!res || !res.ok) return;

        badgeWords.valEl.textContent = (res.words || 0).toLocaleString();
        badgeChars.valEl.textContent = (res.characters || res.characters_with_spaces || 0).toLocaleString();
        badgeCharsNs.valEl.textContent = (res.characters_no_spaces || 0).toLocaleString();
        badgeSentences.valEl.textContent = (res.sentences || 0).toLocaleString();
        badgeParagraphs.valEl.textContent = (res.paragraphs || 0).toLocaleString();

        var rSecs = res.reading_time_secs || 0;
        badgeReadTime.valEl.textContent = rSecs >= 60 ? Math.floor(rSecs / 60) + "m " + (rSecs % 60) + "s" : rSecs + "s";

        var sSecs = res.speaking_time_secs || 0;
        badgeSpeakTime.valEl.textContent = sSecs >= 60 ? Math.floor(sSecs / 60) + "m " + (sSecs % 60) + "s" : sSecs + "s";

        readingEaseVal.textContent = (res.flesch_reading_ease !== undefined ? Number(res.flesch_reading_ease).toFixed(1) : "100.0") + " / 100";
        gradeLevelVal.textContent = (res.flesch_kincaid_grade !== undefined ? res.flesch_kincaid_grade : "5th Grade") + " - " + (res.readability_label || "Very Easy");
        pagesEstVal.textContent = (res.pages_est !== undefined ? res.pages_est : "0.0") + " pages";
        avgWordLenVal.textContent = (res.avg_word_length !== undefined ? res.avg_word_length : "0.0") + " chars";
        avgSentLenVal.textContent = (res.avg_sentence_length !== undefined ? res.avg_sentence_length : "0.0") + " words";

        kwTable.setRows(res.top_keywords || []);
      });
    }

    function loadFile(filePath) {
      window.FOSS.api("word_counter_analyze_file", { file_path: filePath }).then(function (res) {
        if (res && res.ok && res.text !== undefined) {
          editor.setValue(res.text);
          window.FOSS.toast.show("Loaded " + filePath.split(/[/\\]/).pop(), "success");
        }
      });
    }

    var analyticsCol = window.FOSS.dom.el("div", {
      className: "stack",
      gap: "sm"
    }, [readabilityCard, keywordsCard]);

    var contentSplit = window.FOSS.dom.el("div", {
      className: "split even"
    }, [
      editor.el,
      analyticsCol
    ]);

    panel.appendChild(window.FOSS.dom.el("div", { className: "page stack", gap: "md" }, [
      headerRow,
      toolbar,
      badgesGrid,
      contentSplit
    ]));
  }

  window.FOSS.router.register({
    id: "word_counter",
    title: "Word Counter & Document Analytics",
    navName: "Word Counter",
    category: "Documents",
    icon: "file",
    workbench: false,
    tabs: [
      { id: "main", label: "Analytics", render: renderMain }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        window.FOSS.router.open("word_counter", "main");
        window.FOSS.api("word_counter_analyze_file", { file_path: paths[0] }).then(function (res) {
          if (res && res.ok && res.text) {
            var inEl = document.querySelector("[data-testid='word_counter-editor-input']");
            if (inEl) {
              inEl.value = res.text;
              inEl.dispatchEvent(new Event("input"));
            }
          }
        });
      }
    }
  });
})();
