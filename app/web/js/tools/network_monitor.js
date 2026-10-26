// Network Traffic Monitor: live connections, connection history, per-app summary, and host stats.
window.FOSS = window.FOSS || {};

(function () {
  var selectedDestination = "";

  function renderLive(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-network-monitor");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Live Connections" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Inspect active TCP and UDP sockets with remote destination domain resolution."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network-live-status",
      text: "waiting for first poll"
    });

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "network-live-filter",
      "aria-label": "Process name contains",
      title: "Process name contains",
      placeholder: "process name contains"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network-live-table-host"
    });

    var isPolling = false;
    function loadLive() {
      if (isPolling) return;
      isPolling = true;
      var flt = filterInput.value.trim();
      statusBar.textContent = "Polling live connections...";
      window.FOSS.api("network_get_connections", { filter: flt }).then(function (res) {
        isPolling = false;
        tableHost.innerHTML = "";
        var conns = (res && res.connections) || [];
        statusBar.textContent = "Live connections: " + conns.length;

        if (conns.length === 0) {
          tableHost.appendChild(window.FOSS.dom.el("div", {
            className: "p-lg text-center text-muted text-sm",
            "data-testid": "network-live-empty",
            text: "waiting for first poll"
          }));
          return;
        }

        var tbl = window.FOSS.dom.el("table", {
          className: "table w-full text-xs",
          style: "table-layout: fixed; width: 100%; word-break: break-word;",
          "data-testid": "network-live-table"
        });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 45px;", text: "PID" }),
            window.FOSS.dom.el("th", { style: "width: 90px;", text: "Process" }),
            window.FOSS.dom.el("th", { style: "width: 55px;", text: "Proto" }),
            window.FOSS.dom.el("th", { style: "width: 80px;", text: "Local" }),
            window.FOSS.dom.el("th", { style: "width: 100px;", text: "Remote" }),
            window.FOSS.dom.el("th", { text: "Host" }),
            window.FOSS.dom.el("th", { style: "width: 70px;", text: "Status" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody", {});

        conns.forEach(function (c) {
          var tr = window.FOSS.dom.el("tr", {
            style: "cursor: pointer;",
            onclick: function () {
              selectedDestination = c.domain || c.remote_address || "";
              var knownBtn = panel.querySelector("[data-testid='network-mark-known-btn']");
              if (knownBtn) knownBtn.textContent = "Mark Selected as Known: " + (selectedDestination || "None");
            }
          }, [
            window.FOSS.dom.el("td", { text: String(c.pid || "") }),
            window.FOSS.dom.el("td", { className: "font-semibold", text: c.process_name || "" }),
            window.FOSS.dom.el("td", { text: c.protocol || "" }),
            window.FOSS.dom.el("td", { text: c.local_address || "" }),
            window.FOSS.dom.el("td", { text: c.remote_address || "" }),
            window.FOSS.dom.el("td", { text: c.domain || "" }),
            window.FOSS.dom.el("td", { text: c.status || "" })
          ]);
          tbody.appendChild(tr);
        });

        tbl.appendChild(thead);
        tbl.appendChild(tbody);
        var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
        tableHost.appendChild(wrap);
      }).catch(function () {
        isPolling = false;
      });
    }

    var refreshBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "network-live-refresh-btn",
      "aria-label": "Refresh",
      title: "Refresh",
      style: "min-height: 36px;",
      onclick: loadLive
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Refresh" })
    ]);

    var markKnownBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "network-mark-known-btn",
      "aria-label": "Mark selected as known",
      title: "Mark selected as known",
      style: "min-height: 36px;",
      onclick: function () {
        if (!selectedDestination) return;
        window.FOSS.api("network_manage_destinations", { destination: selectedDestination, known: true }).then(function () {
          window.FOSS.toast.show({ message: "Marked " + selectedDestination + " as known.", type: "success" });
          loadLive();
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Mark Selected as Known" })]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-md" }, [
      filterInput,
      refreshBtn,
      markKnownBtn
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(controlsRow);
    panel.appendChild(tableHost);

    loadLive();
  }

  function renderHistory(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-network-monitor");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Connection History" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Search local connection history stored offline in SQLite database."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network-history-status",
      text: "Ready"
    });

    var procInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "network-history-proc-input",
      "aria-label": "Process",
      title: "Process",
      placeholder: "process name contains"
    });

    var domInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "network-history-dom-input",
      "aria-label": "Domain / IP",
      title: "Domain / IP",
      placeholder: "domain or ip contains"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network-history-table-host"
    });

    function searchHist() {
      var p = procInput.value.trim();
      var d = domInput.value.trim();
      statusBar.textContent = "Searching connection history...";
      window.FOSS.api("network_history", { process: p, domain: d, limit: 100 }).then(function (res) {
        tableHost.innerHTML = "";
        var evts = (res && res.events) || [];
        statusBar.textContent = "Found " + evts.length + " logged connections.";

        if (evts.length === 0) {
          tableHost.appendChild(window.FOSS.dom.el("div", {
            className: "p-lg text-center text-muted text-sm",
            "data-testid": "network-history-empty",
            text: "No connection events match criteria."
          }));
          return;
        }

        var tbl = window.FOSS.dom.el("table", {
          className: "table w-full text-xs",
          style: "table-layout: fixed; width: 100%; word-break: break-word;",
          "data-testid": "network-history-table"
        });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 110px;", text: "Time" }),
            window.FOSS.dom.el("th", { style: "width: 80px;", text: "Process" }),
            window.FOSS.dom.el("th", { style: "width: 50px;", text: "Proto" }),
            window.FOSS.dom.el("th", { style: "width: 70px;", text: "Local" }),
            window.FOSS.dom.el("th", { style: "width: 90px;", text: "Remote" }),
            window.FOSS.dom.el("th", { text: "Host" }),
            window.FOSS.dom.el("th", { style: "width: 60px;", text: "Status" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody", {});

        evts.forEach(function (e) {
          var tr = window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", { text: e.timestamp || "" }),
            window.FOSS.dom.el("td", { className: "font-semibold", text: e.process || "" }),
            window.FOSS.dom.el("td", { text: e.protocol || "" }),
            window.FOSS.dom.el("td", { text: e.local_address || "" }),
            window.FOSS.dom.el("td", { text: e.remote_address || "" }),
            window.FOSS.dom.el("td", { text: e.domain || "" }),
            window.FOSS.dom.el("td", { text: e.status || "" })
          ]);
          tbody.appendChild(tr);
        });

        tbl.appendChild(thead);
        tbl.appendChild(tbody);
        var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
        tableHost.appendChild(wrap);
      });
    }

    var searchBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "network-history-search-btn",
      "aria-label": "Search",
      title: "Search",
      style: "min-height: 36px;",
      onclick: searchHist
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Search" })
    ]);

    var retentionBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "network-history-retention-btn",
      "aria-label": "Set retention period",
      title: "Set retention period",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.api("network_database_ops", { action: "prune", days: 30 }).then(function (res) {
          window.FOSS.toast.show({ message: "Pruned " + (res.pruned_count || 0) + " older records.", type: "info" });
          searchHist();
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Set Retention Period" })]);

    var wipeBtn = window.FOSS.dom.el("button", {
      className: "btn danger",
      "data-testid": "network-history-wipe-btn",
      "aria-label": "Wipe all history",
      title: "Wipe all history",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.confirm({
          title: "Wipe All Network History",
          message: "Are you sure you want to delete all stored connection events?"
        }).then(function (ok) {
          if (ok) {
            window.FOSS.api("network_database_ops", { action: "wipe" }).then(function () {
              window.FOSS.toast.show({ message: "Network history database wiped.", type: "info" });
              searchHist();
            });
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Wipe All History" })]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-md flex-wrap" }, [
      procInput,
      domInput,
      searchBtn,
      retentionBtn,
      wipeBtn
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(controlsRow);
    panel.appendChild(tableHost);

    searchHist();
  }

  function renderStats(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-network-monitor");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Network Statistics & Insights" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Analyze top contacting processes, frequent destinations, and unrecognized hosts."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network-stats-status",
      text: "Ready"
    });

    var statsContainer = window.FOSS.dom.el("div", {
      className: "grid grid-cols-2 gap-md",
      "data-testid": "network-stats-grid"
    });

    function loadStats() {
      statusBar.textContent = "Loading stats...";
      window.FOSS.api("network_stats", { limit: 10, days: 30 }).then(function (res) {
        statsContainer.innerHTML = "";
        statusBar.textContent = "Stats updated.";

        var procsCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "network-stats-top-procs" }, [
          window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Top processes by connection count" })
        ]);
        var procsList = (res && res.top_processes) || [];
        if (!procsList.length) {
          procsCard.appendChild(window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "No process history recorded." }));
        } else {
          procsList.forEach(function (p) {
            procsCard.appendChild(window.FOSS.dom.el("div", { className: "row justify-between text-xs py-xs" }, [
              window.FOSS.dom.el("span", { className: "font-semibold", text: p.process_name || "Unknown" }),
              window.FOSS.dom.el("span", { className: "text-muted", text: String(p.connection_count || 0) + " conns" })
            ]));
          });
        }

        var domsCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "network-stats-top-doms" }, [
          window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Top domains contacted" })
        ]);
        var domsList = (res && res.top_domains) || [];
        if (!domsList.length) {
          domsCard.appendChild(window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "No domain history recorded." }));
        } else {
          domsList.forEach(function (d) {
            domsCard.appendChild(window.FOSS.dom.el("div", { className: "row justify-between text-xs py-xs" }, [
              window.FOSS.dom.el("span", { className: "font-semibold", text: d.destination || "Unknown" }),
              window.FOSS.dom.el("span", { className: "text-muted", text: String(d.connection_count || 0) + " conns" })
            ]));
          });
        }

        var unknownsCard = window.FOSS.dom.el("div", { className: "card col-span-2", "data-testid": "network-stats-unknowns" }, [
          window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "New / unknown destinations" }),
          window.FOSS.dom.el("p", { className: "text-xs text-muted mb-sm", text: "Connections over time (last 30 days)" })
        ]);
        var unkList = ((res && res.unknown_destinations) || []).slice(0, 10);
        if (!unkList.length) {
          unknownsCard.appendChild(window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "All destinations are approved and recognized." }));
        } else {
          unkList.forEach(function (u) {
            var destLabel = u.domain || u.ip || "Unknown";
            unknownsCard.appendChild(window.FOSS.dom.el("div", { className: "row justify-between items-center text-xs py-xs" }, [
              window.FOSS.dom.el("span", { className: "font-mono", text: destLabel }),
              window.FOSS.dom.el("button", {
                className: "btn ghost text-xs",
                "aria-label": "Mark selected as known",
                title: "Mark selected as known",
                style: "min-height: 36px; padding: 4px 10px;",
                onclick: function () {
                  window.FOSS.api("network_manage_destinations", { destination: destLabel, known: true }).then(function () {
                    loadStats();
                  });
                }
              }, [window.FOSS.dom.el("span", { text: "Mark Selected as Known" })])
            ]));
          });
        }

        statsContainer.appendChild(procsCard);
        statsContainer.appendChild(domsCard);
        statsContainer.appendChild(unknownsCard);
      });
    }

    var refreshStatsBtn = window.FOSS.dom.el("button", {
      className: "btn primary mb-md",
      "data-testid": "network-refresh-stats-btn",
      "aria-label": "Refresh stats",
      title: "Refresh stats",
      style: "min-height: 36px;",
      onclick: loadStats
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Refresh Stats" })
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(refreshStatsBtn);
    panel.appendChild(statsContainer);

    loadStats();
  }

  function renderApps(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-network-monitor");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Per-App Summary" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Summary of bandwidth usage and total connections grouped by executable process."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network-apps-status",
      text: "Ready"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network-apps-table-host"
    });

    function loadApps() {
      statusBar.textContent = "Loading app traffic summary...";
      window.FOSS.api("network_apps", {}).then(function (res) {
        tableHost.innerHTML = "";
        var apps = (res && res.summary) || [];
        statusBar.textContent = "Applications tracked: " + apps.length;

        if (apps.length === 0) {
          tableHost.appendChild(window.FOSS.dom.el("div", {
            className: "p-lg text-center text-muted text-sm",
            "data-testid": "network-apps-empty",
            text: "No applications logged yet."
          }));
          return;
        }

        var tbl = window.FOSS.dom.el("table", {
          className: "table w-full text-xs",
          style: "table-layout: fixed; width: 100%; word-break: break-word;",
          "data-testid": "network-apps-table"
        });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { text: "Process" }),
            window.FOSS.dom.el("th", { style: "width: 70px;", text: "Conns" }),
            window.FOSS.dom.el("th", { style: "width: 120px;", text: "First Seen" }),
            window.FOSS.dom.el("th", { style: "width: 120px;", text: "Last Seen" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody", {});

        apps.forEach(function (a) {
          var tr = window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", { className: "font-semibold", text: a.process_name || "" }),
            window.FOSS.dom.el("td", { text: String(a.total_connections || a.count || 0) }),
            window.FOSS.dom.el("td", { text: a.first_seen || "" }),
            window.FOSS.dom.el("td", { text: a.last_seen || "" })
          ]);
          tbody.appendChild(tr);
        });

        tbl.appendChild(thead);
        tbl.appendChild(tbody);
        var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
        tableHost.appendChild(wrap);
      });
    }

    var refreshAppsBtn = window.FOSS.dom.el("button", {
      className: "btn primary mb-md",
      "data-testid": "network-apps-refresh-btn",
      "aria-label": "Refresh",
      title: "Refresh",
      style: "min-height: 36px;",
      onclick: loadApps
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Refresh" })
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(refreshAppsBtn);
    panel.appendChild(tableHost);

    loadApps();
  }

  window.FOSS.router.register({
    id: "network_monitor",
    title: "Network Traffic Monitor",
    navName: "Network Monitor",
    category: "utilities",
    icon: "activity",
    tabs: [
      { id: "live", label: "Live Connections", render: renderLive },
      { id: "history", label: "History", render: renderHistory },
      { id: "stats", label: "Stats", render: renderStats },
      { id: "apps", label: "Per-App Summary", render: renderApps }
    ]
  });
})();
