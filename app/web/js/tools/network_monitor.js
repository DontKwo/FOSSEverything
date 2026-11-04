// Network Traffic Monitor: live connections, connection history, per-app summary, and host stats.
window.FOSS = window.FOSS || {};

(function () {
  var selectedDestination = "";
  var livePollTimer = null;
  var livePollIntervalMs = 0;
  var currentLiveFilterStatus = "ALL";
  var rawLiveConnections = [];

  function formatTimestamp(isoStr) {
    if (!isoStr) return "";
    try {
      var d = new Date(isoStr);
      if (isNaN(d.getTime())) return String(isoStr);
      var pad = function (n) { return (n < 10 ? "0" : "") + n; };
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " +
        pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
    } catch (e) {
      return String(isoStr);
    }
  }

  function clearLiveTimer() {
    if (livePollTimer) {
      clearInterval(livePollTimer);
      livePollTimer = null;
    }
  }

  function renderTrustBadge(trustLevel) {
    var cls = "badge";
    if (trustLevel === "Trusted System" || trustLevel === "Trusted App" || trustLevel === "Trusted Service" || trustLevel === "Local Safe") {
      cls += " success";
    } else if (trustLevel === "Local Dev") {
      cls += " info";
    } else if (trustLevel === "Unverified") {
      cls += " warning";
    } else {
      cls += " badge-neutral";
    }
    return window.FOSS.dom.el("span", {
      className: cls,
      text: trustLevel || "Unknown"
    });
  }

  function renderLive(panel, ctx) {
    clearLiveTimer();
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

    var throughputPill = window.FOSS.dom.el("div", {
      className: "pill text-xs",
      "data-testid": "network-live-throughput",
      text: "Up: 0.0 KB/s | Down: 0.0 KB/s"
    });

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "network-live-filter",
      "aria-label": "Process or host filter",
      title: "Process or host filter",
      placeholder: "process, domain, or address contains"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network-live-table-host"
    });

    function applyLiveFilterAndRender() {
      var query = filterInput.value.trim().toLowerCase();
      var filtered = rawLiveConnections.filter(function (c) {
        if (currentLiveFilterStatus === "ESTABLISHED") {
          if (c.status !== "ESTABLISHED") return false;
        } else if (currentLiveFilterStatus === "LISTEN") {
          if (c.status !== "LISTEN" && c.status !== "LISTENING") return false;
        } else if (currentLiveFilterStatus === "UDP") {
          if ((c.protocol || "").toUpperCase() !== "UDP") return false;
        } else if (currentLiveFilterStatus === "NEW") {
          if (!c.is_new) return false;
        }

        if (!query) return true;
        var hay = [c.process_name, c.local_address, c.remote_address, c.domain, c.status, c.protocol].join(" ").toLowerCase();
        return hay.indexOf(query) !== -1;
      });

      renderLiveRows(filtered);
    }

    filterInput.addEventListener("input", applyLiveFilterAndRender);

    function renderLiveRows(conns) {
      tableHost.innerHTML = "";
      if (conns.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "p-lg text-center text-muted text-sm",
          "data-testid": "network-live-empty",
          text: rawLiveConnections.length === 0 ? "waiting for first poll" : "No connections match active filter."
        }));
        return;
      }

      var tbl = window.FOSS.dom.el("table", {
        className: "table w-full text-xs",
        style: "table-layout: fixed; width: 100%; min-width: 0;",
        "data-testid": "network-live-table"
      });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 8%; white-space: nowrap;", text: "PID", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 18%; white-space: nowrap;", text: "Process", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 16%; white-space: nowrap;", text: "Source Identity", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 14%; white-space: nowrap;", text: "Trust Level", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 8%; white-space: nowrap;", text: "Proto", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Local", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Remote", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Host", "data-truncate-ok": "true" })
        ])
      ]);
      var tbody = window.FOSS.dom.el("tbody", {});

      conns.forEach(function (c) {
        var tr = window.FOSS.dom.el("tr", {
          style: "cursor: pointer;",
          onclick: function () {
            selectedDestination = c.domain || c.remote_ip || c.remote_address || "";
            var knownBtn = panel.querySelector("[data-testid='network_monitor-mark-known-btn']");
            if (knownBtn) {
              knownBtn.textContent = "Mark Selected as Known: " + (selectedDestination || "None");
            }
          }
        }, [
          window.FOSS.dom.el("td", {
            style: "width: 8%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: String(c.pid || ""),
            text: String(c.pid || "")
          }),
          window.FOSS.dom.el("td", {
            className: "font-semibold",
            style: "width: 18%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.process_name || "",
            text: c.process_name || ""
          }),
          window.FOSS.dom.el("td", {
            style: "width: 16%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.source_identity || "Application",
            text: c.source_identity || "Application"
          }),
          window.FOSS.dom.el("td", {
            style: "width: 14%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.trust_level || "Unverified"
          }, [renderTrustBadge(c.trust_level)]),
          window.FOSS.dom.el("td", {
            style: "width: 8%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.protocol || "",
            text: c.protocol || ""
          }),
          window.FOSS.dom.el("td", {
            style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.local_address || "",
            text: c.local_address || ""
          }),
          window.FOSS.dom.el("td", {
            style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.remote_address || "",
            text: c.remote_address || ""
          }),
          window.FOSS.dom.el("td", {
            style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
            "data-truncate-ok": "true",
            title: c.domain || "",
            text: c.domain || (c.is_new ? "(new)" : "")
          })
        ]);
        tbody.appendChild(tr);
      });

      tbl.appendChild(thead);
      tbl.appendChild(tbody);
      var wrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x" }, [tbl]);
      tableHost.appendChild(wrap);
    }

    var isPolling = false;
    function loadLive() {
      if (isPolling) return;
      isPolling = true;
      statusBar.textContent = "Polling live connections...";
      window.FOSS.api("network_get_connections", {}).then(function (res) {
        isPolling = false;
        rawLiveConnections = (res && res.connections) || [];
        var count = rawLiveConnections.length;
        var tp = (res && res.throughput) || {};
        var upKb = (tp.up_kb !== undefined ? tp.up_kb : 0).toFixed(1);
        var downKb = (tp.down_kb !== undefined ? tp.down_kb : 0).toFixed(1);

        throughputPill.textContent = "Up: " + upKb + " KB/s | Down: " + downKb + " KB/s";
        statusBar.textContent = "Live connections: " + count;
        applyLiveFilterAndRender();
      }).catch(function () {
        isPolling = false;
      });
    }

    var refreshBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
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
      className: "btn btn-secondary",
      "data-testid": "network_monitor-mark-known-btn",
      "aria-label": "Mark selected as known",
      title: "Mark selected as known",
      style: "min-height: 36px;",
      onclick: function () {
        if (!selectedDestination) {
          window.FOSS.toast.show({ message: "Click a connection row first to select a destination.", type: "info" });
          return;
        }
        window.FOSS.api("network_manage_destinations", { destination: selectedDestination, known: true }).then(function () {
          window.FOSS.toast.show({ message: "Marked " + selectedDestination + " as known.", type: "success" });
          loadLive();
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Mark Selected as Known" })]);

    var autoRefreshSelect = window.FOSS.dom.el("select", {
      className: "select",
      "aria-label": "Auto-refresh frequency",
      title: "Auto-refresh frequency",
      style: "min-height: 36px;",
      onchange: function () {
        clearLiveTimer();
        var val = parseInt(autoRefreshSelect.value, 10);
        livePollIntervalMs = val;
        if (val > 0) {
          livePollTimer = setInterval(loadLive, val);
        }
      }
    }, [
      window.FOSS.dom.el("option", { value: "0", text: "Auto: Off" }),
      window.FOSS.dom.el("option", { value: "2000", text: "Auto: 2s" }),
      window.FOSS.dom.el("option", { value: "5000", text: "Auto: 5s" })
    ]);

    var filterPills = window.FOSS.dom.el("div", { className: "row gap-xs items-center" });
    var pillStatuses = [
      { id: "ALL", label: "All" },
      { id: "ESTABLISHED", label: "Established" },
      { id: "LISTEN", label: "Listening" },
      { id: "UDP", label: "UDP" },
      { id: "NEW", label: "New Destinations" }
    ];

    function updatePills() {
      filterPills.innerHTML = "";
      pillStatuses.forEach(function (p) {
        var isActive = currentLiveFilterStatus === p.id;
        var btn = window.FOSS.dom.el("button", {
          className: "btn btn-sm " + (isActive ? "btn-primary" : "btn-secondary"),
          "aria-label": "Filter " + p.label,
          title: "Filter " + p.label,
          style: "min-height: 36px;",
          onclick: function () {
            currentLiveFilterStatus = p.id;
            updatePills();
            applyLiveFilterAndRender();
          }
        }, [window.FOSS.dom.el("span", { text: p.label })]);
        filterPills.appendChild(btn);
      });
    }
    updatePills();

    var toolbarTop = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-sm flex-wrap" }, [
      filterInput,
      autoRefreshSelect,
      refreshBtn,
      markKnownBtn
    ]);

    var toolbarBottom = window.FOSS.dom.el("div", { className: "row justify-between items-center mb-md flex-wrap gap-sm" }, [
      filterPills,
      throughputPill
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(toolbarTop);
    panel.appendChild(toolbarBottom);
    panel.appendChild(tableHost);

    loadLive();
  }

  function renderHistory(panel, ctx) {
    clearLiveTimer();
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
      className: "input flex-1",
      "data-testid": "network-history-proc-input",
      "aria-label": "Process",
      title: "Process",
      placeholder: "process name contains"
    });

    var domInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
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
          style: "table-layout: fixed; width: 100%; min-width: 0;",
          "data-testid": "network-history-table"
        });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 14%; white-space: nowrap;", "data-truncate-ok": "true", text: "Timestamp" }),
            window.FOSS.dom.el("th", { style: "width: 16%; white-space: nowrap;", "data-truncate-ok": "true", text: "Process" }),
            window.FOSS.dom.el("th", { style: "width: 14%; white-space: nowrap;", "data-truncate-ok": "true", text: "Source Identity" }),
            window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", "data-truncate-ok": "true", text: "Trust Level" }),
            window.FOSS.dom.el("th", { style: "width: 8%; white-space: nowrap;", "data-truncate-ok": "true", text: "Proto" }),
            window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", "data-truncate-ok": "true", text: "Local" }),
            window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", "data-truncate-ok": "true", text: "Remote" }),
            window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", "data-truncate-ok": "true", text: "Host" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody", {});

        evts.forEach(function (e) {
          var compactTime = formatTimestamp(e.timestamp);
          var tr = window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", {
              style: "width: 14%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.timestamp || "",
              text: compactTime
            }),
            window.FOSS.dom.el("td", {
              className: "font-semibold",
              style: "width: 16%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.process || "",
              text: e.process || ""
            }),
            window.FOSS.dom.el("td", {
              style: "width: 14%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.source_identity || "Application",
              text: e.source_identity || "Application"
            }),
            window.FOSS.dom.el("td", {
              style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.trust_level || "Unverified"
            }, [renderTrustBadge(e.trust_level)]),
            window.FOSS.dom.el("td", {
              style: "width: 8%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.protocol || "",
              text: e.protocol || ""
            }),
            window.FOSS.dom.el("td", {
              style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.local_address || "",
              text: e.local_address || ""
            }),
            window.FOSS.dom.el("td", {
              style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.remote_address || "",
              text: e.remote_address || ""
            }),
            window.FOSS.dom.el("td", {
              style: "width: 12%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: e.domain || "",
              text: e.domain || ""
            })
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
      className: "btn btn-primary",
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
      className: "btn btn-secondary",
      "data-testid": "network-history-retention-btn",
      "aria-label": "Set retention period",
      title: "Set retention period",
      style: "min-height: 36px;",
      onclick: function () {
        var confFn = (window.FOSS.dialogs && window.FOSS.dialogs.confirm) || window.FOSS.confirm;
        confFn({
          title: "Prune Older Connection History",
          message: "Prune logged connection events older than 30 days?",
          confirmText: "Prune",
          cancelText: "Cancel"
        }).then(function (ok) {
          if (!ok) return;
          window.FOSS.api("network_database_ops", { action: "prune", days: 30 }).then(function (res) {
            window.FOSS.toast.show({ message: "Pruned " + (res.pruned_count || 0) + " older records.", type: "info" });
            searchHist();
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Prune >30 Days" })]);

    var wipeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-danger",
      "data-testid": "network-history-wipe-btn",
      "aria-label": "Wipe all history",
      title: "Wipe all history",
      style: "min-height: 36px;",
      onclick: function () {
        var confFn = (window.FOSS.dialogs && window.FOSS.dialogs.confirm) || window.FOSS.confirm;
        confFn({
          title: "Wipe All Network History",
          message: "Are you sure you want to delete all stored connection events?",
          confirmText: "Wipe All",
          cancelText: "Cancel"
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
    clearLiveTimer();
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
          window.FOSS.dom.el("p", { className: "text-xs text-muted mb-sm", text: "Destinations not yet explicitly marked as known." })
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
                className: "btn btn-ghost btn-sm",
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
      className: "btn btn-primary mb-md",
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
    clearLiveTimer();
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
          style: "table-layout: fixed; width: 100%; min-width: 0;",
          "data-testid": "network-apps-table"
        });
        var thead = window.FOSS.dom.el("thead", {}, [
          window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("th", { style: "width: 40%; white-space: nowrap;", "data-truncate-ok": "true", text: "Process" }),
            window.FOSS.dom.el("th", { style: "width: 15%; white-space: nowrap;", "data-truncate-ok": "true", text: "Conns" }),
            window.FOSS.dom.el("th", { style: "width: 22%; white-space: nowrap;", "data-truncate-ok": "true", text: "First Seen" }),
            window.FOSS.dom.el("th", { style: "width: 23%; white-space: nowrap;", "data-truncate-ok": "true", text: "Last Seen" })
          ])
        ]);
        var tbody = window.FOSS.dom.el("tbody", {});

        apps.forEach(function (a) {
          var tr = window.FOSS.dom.el("tr", {}, [
            window.FOSS.dom.el("td", {
              className: "font-semibold",
              style: "width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: a.process_name || "",
              text: a.process_name || ""
            }),
            window.FOSS.dom.el("td", {
              style: "width: 15%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: String(a.total_connections || a.count || 0),
              text: String(a.total_connections || a.count || 0)
            }),
            window.FOSS.dom.el("td", {
              style: "width: 22%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: a.first_seen || "",
              text: formatTimestamp(a.first_seen)
            }),
            window.FOSS.dom.el("td", {
              style: "width: 23%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
              "data-truncate-ok": "true",
              title: a.last_seen || "",
              text: formatTimestamp(a.last_seen)
            })
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
      className: "btn btn-primary mb-md",
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
    category: "Utilities",
    icon: "activity",
    onHide: function () {
      clearLiveTimer();
    },
    tabs: [
      { id: "live", label: "Live Connections", render: renderLive },
      { id: "history", label: "History", render: renderHistory },
      { id: "stats", label: "Stats", render: renderStats },
      { id: "apps", label: "Per-App Summary", render: renderApps }
    ]
  });
})();
