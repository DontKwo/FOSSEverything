// Sherlock: Find usernames across social networks and online platforms.
// Powered by Sherlock Project (MIT License, https://github.com/sherlock-project/sherlock).
window.FOSS = window.FOSS || {};

(function () {
  var currentResults = [];
  var activeJobHandle = null;
  var currentFilterStatus = "ALL";
  var cachedSitesList = [];

  function renderStatusBadge(status) {
    var cls = "badge";
    if (status === "Claimed") {
      cls += " success";
    } else if (status === "Available") {
      cls += " badge-neutral";
    } else if (status === "WAF") {
      cls += " warning";
    } else if (status === "Illegal") {
      cls += " danger";
    } else {
      cls += " info";
    }
    return window.FOSS.dom.el("span", {
      className: cls,
      "data-testid": "sherlock-status-badge",
      text: status || "Unknown"
    });
  }

  function renderSearchTab(panel, ctx) {
    panel.innerHTML = "";
    panel.className = "tab-panel stack p-4 grow";
    panel.setAttribute("data-testid", "sherlock-page");

    var defaults = window.FOSS.toolDefaults;
    var defaultMode = String(defaults.get("sherlock", "default_mode", "popular"));
    var defaultTimeout = Number(defaults.get("sherlock", "timeout", 10));
    var defaultNsfw = Boolean(defaults.get("sherlock", "include_nsfw", false));

    var header = window.FOSS.dom.el("div", { className: "stack-sm mb-3" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Search Accounts by Username" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Hunt down user accounts across 400+ online platforms and social networks."
      })
    ]);

    var usernameInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "sherlock-username-input",
      "aria-label": "Target username",
      title: "Target username",
      placeholder: "Enter username (e.g. joshsmith, developer42)"
    });

    var modeSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "sherlock-mode-select",
      "aria-label": "Scan scope",
      title: "Scan scope"
    }, [
      window.FOSS.dom.el("option", { value: "popular", text: "Popular Sites (~30 major platforms)" }),
      window.FOSS.dom.el("option", { value: "all", text: "All Sites (Full scan, 400+ platforms)" })
    ]);
    modeSelect.value = defaultMode;

    var nsfwLabel = window.FOSS.dom.el("label", {
      className: "row gap-2 items-center cursor-pointer text-xs text-muted",
      title: "Include adult/NSFW platforms in search"
    });
    var nsfwCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "sherlock-nsfw-check",
      checked: defaultNsfw
    });
    nsfwLabel.appendChild(nsfwCheck);
    nsfwLabel.appendChild(window.FOSS.dom.el("span", { text: "Include NSFW" }));

    var searchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "sherlock-search-btn",
      "aria-label": "Search Username",
      title: "Search Username across sites",
      onclick: startSearch
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Search" })
    ]);

    var cancelBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "sherlock-cancel-btn",
      "aria-label": "Cancel Search",
      title: "Cancel current search",
      disabled: true,
      onclick: cancelSearch
    }, [
      window.FOSS.icons.el("x", 16),
      window.FOSS.dom.el("span", { text: "Cancel" })
    ]);

    var progressWrap = window.FOSS.dom.el("div", {
      className: "stack-sm mb-3",
      "data-testid": "sherlock-progress-wrap"
    });

    var progressBar = window.FOSS.dom.el("div", {
      className: "progress-bar",
      "data-testid": "sherlock-progress-bar"
    });
    var progressFill = window.FOSS.dom.el("div", {
      className: "progress-fill",
      "data-testid": "sherlock-progress-fill"
    });
    progressBar.appendChild(progressFill);

    var progressStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted row justify-between",
      "data-testid": "sherlock-progress-status",
      text: "Ready to search."
    });
    progressWrap.appendChild(progressBar);
    progressWrap.appendChild(progressStatus);

    var summaryRow = window.FOSS.dom.el("div", {
      className: "row gap-3 items-center mb-3 flex-wrap",
      "data-testid": "sherlock-summary-row"
    });

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "sherlock-filter-input",
      "aria-label": "Filter results by site name",
      title: "Filter results by site name",
      placeholder: "Filter results by site name..."
    });
    filterInput.addEventListener("input", applyFilterAndRender);

    var filterPills = window.FOSS.dom.el("div", { className: "row gap-2 items-center" });
    var pillDefinitions = [
      { id: "ALL", label: "All Results" },
      { id: "CLAIMED", label: "Found Only" },
      { id: "AVAILABLE", label: "Available" },
      { id: "ERRORS", label: "Errors & WAF" }
    ];

    function updatePills() {
      filterPills.innerHTML = "";
      pillDefinitions.forEach(function (pill) {
        var isActive = currentFilterStatus === pill.id;
        var btn = window.FOSS.dom.el("button", {
          className: "btn btn-sm " + (isActive ? "btn-primary" : "btn-secondary"),
          "data-testid": "sherlock-filter-" + pill.id.toLowerCase(),
          "aria-label": "Show " + pill.label,
          title: "Show " + pill.label,
          onclick: function () {
            currentFilterStatus = pill.id;
            updatePills();
            applyFilterAndRender();
          }
        }, [window.FOSS.dom.el("span", { text: pill.label })]);
        filterPills.appendChild(btn);
      });
    }
    updatePills();

    var exportJsonBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm btn-secondary",
      "data-testid": "sherlock-export-json-btn",
      "aria-label": "Export JSON",
      title: "Export results as JSON",
      onclick: function () { triggerExport("json"); }
    }, [
      window.FOSS.icons.el("download", 14),
      window.FOSS.dom.el("span", { text: "JSON" })
    ]);

    var exportCsvBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm btn-secondary",
      "data-testid": "sherlock-export-csv-btn",
      "aria-label": "Export CSV",
      title: "Export results as CSV",
      onclick: function () { triggerExport("csv"); }
    }, [
      window.FOSS.icons.el("download", 14),
      window.FOSS.dom.el("span", { text: "CSV" })
    ]);

    var exportTxtBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm btn-secondary",
      "data-testid": "sherlock-export-txt-btn",
      "aria-label": "Export Text",
      title: "Export results as formatted report",
      onclick: function () { triggerExport("txt"); }
    }, [
      window.FOSS.icons.el("download", 14),
      window.FOSS.dom.el("span", { text: "Report" })
    ]);

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-4",
      "data-testid": "sherlock-table-host"
    });

    var citationFooter = window.FOSS.dom.el("div", {
      className: "text-xs text-muted text-center pt-2 border-t",
      "data-testid": "sherlock-citation"
    }, [
      window.FOSS.dom.el("span", {
        text: "Powered by Sherlock Project (MIT License, https://github.com/sherlock-project/sherlock)"
      })
    ]);

    function updateSummaryCards(total, found, available, errors) {
      summaryRow.innerHTML = "";
      var statItems = [
        { label: "Total Checked", val: total, color: "text-primary" },
        { label: "Found Accounts", val: found, color: "text-success font-semibold" },
        { label: "Available", val: available, color: "text-muted" },
        { label: "Errors / WAF", val: errors, color: "text-warning" }
      ];
      statItems.forEach(function (stat) {
        var card = window.FOSS.dom.el("div", { className: "pill text-xs row gap-2" }, [
          window.FOSS.dom.el("span", { className: "text-muted", text: stat.label + ": " }),
          window.FOSS.dom.el("span", { className: stat.color, text: String(stat.val) })
        ]);
        summaryRow.appendChild(card);
      });
    }

    function applyFilterAndRender() {
      var query = filterInput.value.trim().toLowerCase();
      var filtered = currentResults.filter(function (row) {
        if (currentFilterStatus === "CLAIMED" && row.status !== "Claimed") return false;
        if (currentFilterStatus === "AVAILABLE" && row.status !== "Available") return false;
        if (currentFilterStatus === "ERRORS" && row.status !== "Unknown" && row.status !== "WAF") return false;
        if (!query) return true;
        var hay = [row.site_name, row.url_user, row.status, row.error_context || ""].join(" ").toLowerCase();
        return hay.indexOf(query) !== -1;
      });
      renderResultRows(filtered);
    }

    function renderResultRows(rows) {
      tableHost.innerHTML = "";
      if (rows.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "p-lg text-center text-muted text-sm",
          "data-testid": "sherlock-empty-results",
          text: currentResults.length === 0 ? "No active search. Enter a username above to start." : "No results match active filter."
        }));
        return;
      }

      var tbl = window.FOSS.dom.el("table", {
        className: "table w-full text-xs",
        "data-testid": "sherlock-results-table"
      });

      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 24%;", text: "Platform" }),
          window.FOSS.dom.el("th", { style: "width: 10%;", text: "NSFW" }),
          window.FOSS.dom.el("th", { style: "width: 14%;", text: "Status" }),
          window.FOSS.dom.el("th", { style: "width: 40%;", text: "Profile URL" }),
          window.FOSS.dom.el("th", { style: "width: 12%;", text: "Latency" })
        ])
      ]);

      var tbody = window.FOSS.dom.el("tbody", {});
      rows.forEach(function (row) {
        var isFound = row.status === "Claimed";
        var nsfwEl = row.is_nsfw
          ? window.FOSS.dom.el("span", { className: "badge warning", text: "Yes" })
          : window.FOSS.dom.el("span", { className: "text-muted", text: "No" });

        var linkEl;
        if (isFound && row.url_user) {
          linkEl = window.FOSS.dom.el("a", {
            href: row.url_user,
            target: "_blank",
            rel: "noopener noreferrer",
            className: "text-primary hover:underline",
            text: row.url_user,
            title: "Open in browser: " + row.url_user,
            onClick: function (e) {
              e.preventDefault();
              window.FOSS.api("open_url", { url: row.url_user });
            }
          });
        } else {
          linkEl = window.FOSS.dom.el("span", {
            className: "text-muted",
            text: row.url_user || row.url_main || "-",
            title: row.error_context || ""
          });
        }

        var latencyText = row.response_time_ms ? (row.response_time_ms + " ms") : "-";
        var tr = window.FOSS.dom.el("tr", {
          className: isFound ? "font-semibold" : ""
        }, [
          window.FOSS.dom.el("td", { text: row.site_name, title: row.site_name }),
          window.FOSS.dom.el("td", {}, [nsfwEl]),
          window.FOSS.dom.el("td", {}, [renderStatusBadge(row.status)]),
          window.FOSS.dom.el("td", { className: "scroll-x", "data-truncate-ok": "true" }, [linkEl]),
          window.FOSS.dom.el("td", { className: "text-muted", text: latencyText })
        ]);
        tbody.appendChild(tr);
      });

      tbl.appendChild(thead);
      tbl.appendChild(tbody);
      var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
      tableHost.appendChild(wrap);
    }

    function cancelSearch() {
      if (activeJobHandle && typeof activeJobHandle.cancel === "function") {
        activeJobHandle.cancel();
      }
      cancelBtn.disabled = true;
      searchBtn.disabled = false;
      progressStatus.textContent = "Search cancelled by user.";
    }

    function triggerExport(format) {
      var username = usernameInput.value.trim();
      if (!username || currentResults.length === 0) {
        window.FOSS.toast.show("No search results to export.", "info");
        return;
      }
      window.FOSS.api("sherlock_export", {
        username: username,
        results: currentResults,
        format: format
      }).then(function (res) {
        if (res && res.ok && res.file_path) {
          window.FOSS.toast.show("Saved " + format.toUpperCase() + " report to " + res.file_path, "success");
        }
      });
    }

    function startSearch() {
      var username = usernameInput.value.trim();
      if (!username) {
        window.FOSS.toast.show("Please enter a username to search.", "warning");
        usernameInput.focus();
        return;
      }

      currentResults = [];
      updateSummaryCards(0, 0, 0, 0);
      applyFilterAndRender();

      searchBtn.disabled = true;
      cancelBtn.disabled = false;
      progressFill.style.transform = "scaleX(0)";
      progressStatus.textContent = "Starting search for " + username + "...";

      var params = {
        username: username,
        mode: modeSelect.value,
        include_nsfw: nsfwCheck.checked,
        timeout: defaultTimeout
      };

      if (window.FOSS.job) {
        window.FOSS.job("sherlock_search", params, {
          onStart: function (handle) {
            activeJobHandle = handle;
          },
          onProgress: function (fraction, message) {
            var pct = Math.max(0, Math.min(100, Math.round((fraction || 0) * 100)));
            progressFill.style.transform = "scaleX(" + (pct / 100) + ")";
            progressStatus.textContent = message || ("Progress: " + pct + "%");
          }
        }).then(function (res) {
          searchBtn.disabled = false;
          cancelBtn.disabled = true;
          activeJobHandle = null;
          progressFill.style.transform = "scaleX(1)";

          if (!res || res.ok === false) {
            progressStatus.textContent = "Search failed: " + ((res && res.error) || "Unknown error");
            return;
          }

          currentResults = res.results || [];
          var total = res.total_checked || currentResults.length;
          var found = res.found_count || 0;
          var available = res.available_count || 0;
          var errors = res.error_count || 0;

          updateSummaryCards(total, found, available, errors);
          progressStatus.textContent = "Search complete. Found " + found + " accounts across " + total + " platforms.";
          applyFilterAndRender();
        }).catch(function (err) {
          searchBtn.disabled = false;
          cancelBtn.disabled = true;
          activeJobHandle = null;
          progressStatus.textContent = "Search encountered an error: " + err;
        });
      } else {
        window.FOSS.api("sherlock_search", params).then(function (res) {
          searchBtn.disabled = false;
          cancelBtn.disabled = true;
          if (res && res.ok) {
            currentResults = res.results || [];
            updateSummaryCards(res.total_checked || 0, res.found_count || 0, res.available_count || 0, res.error_count || 0);
            applyFilterAndRender();
          }
        });
      }
    }

    usernameInput.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") {
        ev.preventDefault();
        startSearch();
      }
    });

    var inputRow = window.FOSS.dom.el("div", { className: "row gap-3 items-center mb-3 flex-wrap" }, [
      usernameInput,
      modeSelect,
      nsfwLabel,
      searchBtn,
      cancelBtn
    ]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row justify-between items-center mb-4 flex-wrap gap-3" }, [
      filterPills,
      filterInput,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
        exportJsonBtn,
        exportCsvBtn,
        exportTxtBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(inputRow);
    panel.appendChild(progressWrap);
    panel.appendChild(summaryRow);
    panel.appendChild(controlsRow);
    panel.appendChild(tableHost);
    panel.appendChild(citationFooter);

    updateSummaryCards(0, 0, 0, 0);
    renderResultRows([]);
  }

  function renderSitesTab(panel, ctx) {
    panel.innerHTML = "";
    panel.className = "tab-panel stack p-4 grow";
    panel.setAttribute("data-testid", "sherlock-sites-page");

    var header = window.FOSS.dom.el("div", { className: "stack-sm mb-3" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Supported Sites & Platforms" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Browse site definitions and detection signatures bundled from the Sherlock Project."
      })
    ]);

    var searchInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "sherlock-sites-search-input",
      "aria-label": "Search platforms",
      title: "Search platforms",
      placeholder: "Search platforms by name..."
    });

    var updateDbBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "sherlock-update-db-btn",
      "aria-label": "Update Site Database",
      title: "Download latest manifest from data.sherlockproject.xyz",
      onclick: function () {
        updateDbBtn.disabled = true;
        statusBar.textContent = "Downloading latest manifest from Sherlock project...";
        window.FOSS.api("sherlock_update_database", {}).then(function (res) {
          updateDbBtn.disabled = false;
          if (res && res.ok && res.success) {
            window.FOSS.toast.show(res.message || "Database updated successfully.", "success");
            loadSites();
          } else {
            window.FOSS.toast.show(((res && res.message) || "Failed to update database."), "error");
            statusBar.textContent = "Update failed.";
          }
        }).catch(function () {
          updateDbBtn.disabled = false;
          statusBar.textContent = "Update failed.";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Update Database" })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-2",
      "data-testid": "sherlock-sites-status",
      text: "Loading supported platforms..."
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-4",
      "data-testid": "sherlock-sites-table-host"
    });

    function applySitesFilter() {
      var query = searchInput.value.trim().toLowerCase();
      var filtered = cachedSitesList.filter(function (s) {
        if (!query) return true;
        return (s.name || "").toLowerCase().indexOf(query) !== -1 || (s.url_main || "").toLowerCase().indexOf(query) !== -1;
      });
      renderSitesTable(filtered);
    }

    searchInput.addEventListener("input", applySitesFilter);

    function renderSitesTable(sites) {
      tableHost.innerHTML = "";
      if (sites.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "p-lg text-center text-muted text-sm",
          text: "No platforms match search."
        }));
        return;
      }

      var tbl = window.FOSS.dom.el("table", {
        className: "table w-full text-xs",
        "data-testid": "sherlock-sites-table"
      });

      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 25%;", text: "Platform Name" }),
          window.FOSS.dom.el("th", { style: "width: 10%;", text: "NSFW" }),
          window.FOSS.dom.el("th", { style: "width: 35%;", text: "Homepage" }),
          window.FOSS.dom.el("th", { style: "width: 15%;", text: "Method" }),
          window.FOSS.dom.el("th", { style: "width: 15%;", text: "Tags" })
        ])
      ]);

      var tbody = window.FOSS.dom.el("tbody", {});
      sites.forEach(function (site) {
        var tags = [];
        if (site.is_popular) {
          tags.push(window.FOSS.dom.el("span", { className: "badge info mr-xs", text: "Popular" }));
        }

        var nsfwSiteEl = site.is_nsfw
          ? window.FOSS.dom.el("span", { className: "badge warning", text: "Yes" })
          : window.FOSS.dom.el("span", { className: "text-muted", text: "No" });

        var linkEl = site.url_main ? window.FOSS.dom.el("a", {
          href: site.url_main,
          target: "_blank",
          rel: "noopener noreferrer",
          className: "text-primary hover:underline",
          text: site.url_main,
          onClick: function (e) {
            e.preventDefault();
            window.FOSS.api("open_url", { url: site.url_main });
          }
        }) : window.FOSS.dom.el("span", { className: "text-muted", text: "-" });

        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "font-semibold", text: site.name }),
          window.FOSS.dom.el("td", {}, [nsfwSiteEl]),
          window.FOSS.dom.el("td", { className: "scroll-x", "data-truncate-ok": "true" }, [linkEl]),
          window.FOSS.dom.el("td", { className: "text-muted", text: site.error_type || "status_code" }),
          window.FOSS.dom.el("td", {}, tags)
        ]);
        tbody.appendChild(tr);
      });

      tbl.appendChild(thead);
      tbl.appendChild(tbody);
      var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
      tableHost.appendChild(wrap);
    }

    function loadSites() {
      statusBar.textContent = "Loading sites catalog...";
      window.FOSS.api("sherlock_get_sites", {}).then(function (res) {
        if (!res || res.ok === false) {
          statusBar.textContent = "Failed to load sites catalog.";
          return;
        }
        cachedSitesList = res.sites || [];
        statusBar.textContent = "Supported platforms: " + res.total_count + " (" + res.popular_count + " popular, " + res.nsfw_count + " NSFW)";
        applySitesFilter();
      }).catch(function () {
        statusBar.textContent = "Failed to load sites catalog.";
      });
    }

    var toolbar = window.FOSS.dom.el("div", { className: "row gap-3 items-center mb-4 flex-wrap" }, [
      searchInput,
      updateDbBtn
    ]);

    panel.appendChild(header);
    panel.appendChild(toolbar);
    panel.appendChild(statusBar);
    panel.appendChild(tableHost);

    loadSites();
  }

  window.FOSS.router.register({
    id: "sherlock",
    title: "Sherlock Username Search",
    navName: "Sherlock",
    category: "Utilities",
    icon: "sherlock",
    defaults: [
      {
        key: "default_mode",
        label: "Default scan mode",
        type: "select",
        default: "popular",
        options: [
          { value: "popular", label: "Popular Sites (~30 major platforms)" },
          { value: "all", label: "All Sites (Full scan, 400+ platforms)" }
        ]
      },
      {
        key: "timeout",
        label: "Per-request timeout (seconds)",
        type: "number",
        default: 10,
        min: 2,
        max: 60,
        step: 1
      },
      {
        key: "include_nsfw",
        label: "Include adult/NSFW platforms",
        type: "boolean",
        default: false
      }
    ],
    tabs: [
      { id: "search", label: "Username Search", render: renderSearchTab },
      { id: "catalog", label: "Sites Catalog", render: renderSitesTab }
    ]
  });
})();
