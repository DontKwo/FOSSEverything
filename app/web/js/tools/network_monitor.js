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

  function renderTrustBadge(trustLevel, procName, onUpdated) {
    var cls = "badge cursor-pointer";
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
      text: trustLevel || "Unknown",
      title: "Click to change trust level for " + (procName || "this app"),
      onClick: function (e) {
        if (!procName) return;
        e.stopPropagation();
        openTrustChangeDialog(procName, trustLevel, onUpdated);
      }
    });
  }

  function openTrustChangeDialog(procName, currentTrust, onUpdated) {
    var select = window.FOSS.dom.el("select", { className: "select w-full" }, [
      window.FOSS.dom.el("option", { value: "Trusted System", text: "Trusted System" }),
      window.FOSS.dom.el("option", { value: "Trusted App", text: "Trusted App" }),
      window.FOSS.dom.el("option", { value: "Local Safe", text: "Local Safe" }),
      window.FOSS.dom.el("option", { value: "Local Dev", text: "Local Dev" }),
      window.FOSS.dom.el("option", { value: "Unverified", text: "Unverified" })
    ]);
    select.value = currentTrust || "Unverified";

    var content = window.FOSS.dom.el("div", { className: "stack-sm" }, [
      window.FOSS.dom.el("p", { className: "text-sm", text: "Set trust level for process: " + procName }),
      select
    ]);

    window.FOSS.dialogs.custom({
      title: "Change Application Trust Level",
      testid: "nm-trust-dialog",
      confirmText: "Save Trust Level",
      content: content,
      onConfirm: function () {
        var newTrust = select.value;
        window.FOSS.api("network_set_process_trust", { process_name: procName, trust_level: newTrust }).then(function () {
          window.FOSS.toast.show("Trust level set to " + newTrust, "success");
          if (onUpdated) onUpdated();
        });
      }
    });
  }

  var LIVE_COLUMNS = [
    { key: "pid", label: "PID", field: "pid", width: "7%", numeric: true },
    { key: "process", label: "Process", field: "process_name", width: "16%" },
    { key: "source_identity", label: "Source Identity", field: "source_identity", width: "14%" },
    { key: "trust_level", label: "Trust Level", field: "trust_level", width: "14%" },
    { key: "proto", label: "Proto", field: "protocol", width: "6%" },
    { key: "local", label: "Local", field: "local_address", width: "10%" },
    { key: "remote", label: "Remote", field: "remote_address", width: "15%" },
    { key: "host", label: "Host", field: "domain", width: "18%" }
  ];

  var currentSortCol = "process";
  var currentSortAsc = true;

  function columnByKey(colKey) {
    for (var i = 0; i < LIVE_COLUMNS.length; i++) {
      if (LIVE_COLUMNS[i].key === colKey) return LIVE_COLUMNS[i];
    }
    return LIVE_COLUMNS[1];
  }

  function sortConnections(list) {
    var col = columnByKey(currentSortCol);
    return list.slice().sort(function (a, b) {
      var rawA = a[col.field];
      var rawB = b[col.field];
      if (col.numeric) {
        var numA = Number(rawA || 0);
        var numB = Number(rawB || 0);
        if (numA === numB) return 0;
        return (numA < numB ? -1 : 1) * (currentSortAsc ? 1 : -1);
      }
      var valA = String(rawA || "").toLowerCase();
      var valB = String(rawB || "").toLowerCase();
      if (valA < valB) return currentSortAsc ? -1 : 1;
      if (valA > valB) return currentSortAsc ? 1 : -1;
      return 0;
    });
  }

  function isExternalDestination(c) {
    var ip = c.remote_ip || "";
    if (!ip || ip === "::" || ip === "0.0.0.0") return false;
    if (ip === "::1" || ip.indexOf("127.") === 0) return false;
    return true;
  }

  function destinationKey(c) {
    return isExternalDestination(c) ? (c.remote_ip || c.domain || "") : "";
  }

  function renderLive(panel, ctx) {
    clearLiveTimer();
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "network_monitor-page");

    var defaults = window.FOSS.toolDefaults;
    currentSortCol = String(defaults.get("network_monitor", "default_sort", "process"));
    currentSortAsc = true;
    selectedDestination = "";
    var pollSeconds = Number(defaults.get("network_monitor", "poll_interval", 2));
    if (!isFinite(pollSeconds) || pollSeconds < 0) pollSeconds = 0;

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Live Connections" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Inspect active TCP and UDP sockets with remote destination domain resolution."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network_monitor-live-status",
      text: "waiting for first poll"
    });

    var throughputPill = window.FOSS.dom.el("div", {
      className: "pill text-xs",
      "data-testid": "network_monitor-live-throughput",
      text: "Up: 0.0 KB/s | Down: 0.0 KB/s"
    });

    var selectedLabel = window.FOSS.dom.el("span", {
      className: "text-xs text-muted",
      "data-testid": "network_monitor-selected-label",
      text: "Selected: none"
    });

    var filterInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "network_monitor-live-filter",
      "aria-label": "Process or host filter",
      title: "Process or host filter",
      placeholder: "process, domain, or address contains"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network_monitor-live-table-host"
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

      renderLiveRows(sortConnections(filtered));
    }

    filterInput.addEventListener("input", applyLiveFilterAndRender);

    function handleHeaderClick(colKey) {
      if (currentSortCol === colKey) {
        currentSortAsc = !currentSortAsc;
      } else {
        currentSortCol = colKey;
        currentSortAsc = true;
      }
      applyLiveFilterAndRender();
    }

    function renderSortHeader(col) {
      var active = currentSortCol === col.key;
      var arrow = active ? (currentSortAsc ? " \u25b2" : " \u25bc") : "";
      return window.FOSS.dom.el("th", {
        className: "nm-sortable" + (active ? " nm-sorted" : ""),
        style: "width: " + col.width + ";",
        role: "button",
        tabindex: "0",
        "aria-sort": active ? (currentSortAsc ? "ascending" : "descending") : "none",
        "data-testid": "network_monitor-sort-" + col.key,
        "data-sort-dir": active ? (currentSortAsc ? "asc" : "desc") : "",
        "data-truncate-ok": "true",
        title: "Sort by " + col.label,
        text: col.label + arrow,
        onclick: function () { handleHeaderClick(col.key); },
        onkeydown: function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            handleHeaderClick(col.key);
          }
        }
      });
    }

    function renderHostCell(c) {
      var kids = [];
      if (isExternalDestination(c)) {
        kids.push(window.FOSS.dom.el("span", {
          className: "badge nm-dest-badge " + (c.is_known ? "success" : "warning"),
          "data-testid": "network_monitor-dest-badge",
          text: c.is_known ? "Known" : "Unknown"
        }));
      }
      var hostText = c.domain || (c.is_new ? "(new)" : "");
      kids.push(document.createTextNode(hostText));
      var badgeText = isExternalDestination(c) ? (c.is_known ? "Known " : "Unknown ") : "";
      return window.FOSS.dom.el("td", {
        className: "nm-cell",
        "data-truncate-ok": "true",
        title: (badgeText + hostText).trim() || "No host"
      }, kids);
    }

    function textCell(value, extraClass) {
      return window.FOSS.dom.el("td", {
        className: "nm-cell" + (extraClass ? " " + extraClass : ""),
        "data-truncate-ok": "true",
        title: value,
        text: value
      });
    }

    function renderLiveRows(conns) {
      tableHost.innerHTML = "";
      if (conns.length === 0) {
        tableHost.appendChild(window.FOSS.dom.el("div", {
          className: "p-lg text-center text-muted text-sm",
          "data-testid": "network_monitor-live-empty",
          text: rawLiveConnections.length === 0 ? "waiting for first poll" : "No connections match active filter."
        }));
        return;
      }

      var tbl = window.FOSS.dom.el("table", {
        className: "table w-full text-xs nm-table",
        "data-testid": "network_monitor-live-table"
      });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, LIVE_COLUMNS.map(renderSortHeader))
      ]);
      var tbody = window.FOSS.dom.el("tbody", {});

      conns.forEach(function (c) {
        var key = destinationKey(c);
        var isSelected = !!selectedDestination && key === selectedDestination;
        var tr = window.FOSS.dom.el("tr", {
          className: "nm-row" + (isSelected ? " nm-row-selected" : ""),
          "data-testid": "network_monitor-live-row",
          onclick: function () {
            selectedDestination = key;
            selectedLabel.textContent = "Selected: " + (key || "none (no remote destination)");
            applyLiveFilterAndRender();
          }
        }, [
          textCell(String(c.pid || "")),
          textCell(c.process_name || "", "font-semibold"),
          textCell(c.source_identity || "Application"),
          window.FOSS.dom.el("td", {
            className: "nm-cell",
            "data-truncate-ok": "true",
            title: c.trust_level || "Unverified"
          }, [renderTrustBadge(c.trust_level, c.process_name, loadLive)]),
          textCell(c.protocol || ""),
          textCell(c.local_address || ""),
          textCell(c.remote_address || ""),
          renderHostCell(c)
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

    function markSelected(known) {
      if (!selectedDestination) {
        window.FOSS.toast.show({ message: "Click a connection row first to select a destination.", type: "info" });
        return;
      }
      var target = selectedDestination;
      window.FOSS.api("network_manage_destinations", { destination: target, known: known }).then(function (res) {
        if (!res || res.ok === false) return;
        rawLiveConnections.forEach(function (c) {
          if (c.remote_ip === target || c.domain === target) {
            c.is_known = known;
            c.is_new = !known;
          }
        });
        window.FOSS.toast.show({ message: "Marked " + target + (known ? " as known." : " as unknown."), type: "success" });
        applyLiveFilterAndRender();
      });
    }

    var refreshBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "network_monitor-live-refresh-btn",
      "aria-label": "Refresh",
      title: "Refresh",
      onclick: loadLive
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Refresh" })
    ]);

    var markKnownBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "network_monitor-mark-known-btn",
      "aria-label": "Mark as Known",
      title: "Mark Selected as Known",
      onclick: function () { markSelected(true); }
    }, [window.FOSS.dom.el("span", { text: "Mark as Known" })]);

    var markUnknownBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "network_monitor-mark-unknown-btn",
      "aria-label": "Mark as Unknown",
      title: "Mark Selected as Unknown",
      onclick: function () { markSelected(false); }
    }, [window.FOSS.dom.el("span", { text: "Mark as Unknown" })]);

    function startLiveTimer() {
      clearLiveTimer();
      if (livePollIntervalMs > 0) {
        livePollTimer = setInterval(loadLive, livePollIntervalMs);
      }
    }

    var pollOptions = [0, 1, 2, 5, 10, 30];
    if (pollOptions.indexOf(pollSeconds) === -1) pollOptions.push(pollSeconds);
    pollOptions.sort(function (a, b) { return a - b; });

    var autoRefreshSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "network_monitor-live-auto-select",
      "aria-label": "Auto-refresh frequency",
      title: "Auto-refresh frequency",
      onchange: function () {
        livePollIntervalMs = parseInt(autoRefreshSelect.value, 10) || 0;
        startLiveTimer();
      }
    }, pollOptions.map(function (sec) {
      return window.FOSS.dom.el("option", {
        value: String(sec * 1000),
        text: sec === 0 ? "Auto: Off" : "Auto: " + sec + "s"
      });
    }));
    autoRefreshSelect.value = String(pollSeconds * 1000);
    livePollIntervalMs = pollSeconds * 1000;

    var filterPills = window.FOSS.dom.el("div", { className: "row gap-xs items-center" });
    var defaultStatusFilter = String(defaults.get("network_monitor", "status_filter", "ALL"));
    if (["ALL", "ESTABLISHED", "LISTEN", "UDP", "NEW"].indexOf(defaultStatusFilter) !== -1) {
      currentLiveFilterStatus = defaultStatusFilter;
    }

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
          "data-testid": "network_monitor-filter-" + p.id.toLowerCase(),
          "aria-label": "Filter " + p.label,
          title: "Filter " + p.label,
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
      markKnownBtn,
      markUnknownBtn
    ]);

    var toolbarBottom = window.FOSS.dom.el("div", { className: "row justify-between items-center mb-md flex-wrap gap-sm" }, [
      filterPills,
      selectedLabel,
      throughputPill
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(toolbarTop);
    panel.appendChild(toolbarBottom);
    panel.appendChild(tableHost);

    startLiveTimer();
    loadLive();
  }

  function renderHistory(panel, ctx) {
    clearLiveTimer();
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "network_monitor-page");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Connection History" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Search local connection history stored offline in SQLite database."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network_monitor-history-status",
      text: "Ready"
    });

    var procInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "network_monitor-history-proc-input",
      "aria-label": "Process",
      title: "Process",
      placeholder: "process name contains"
    });

    var domInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input flex-1",
      "data-testid": "network_monitor-history-dom-input",
      "aria-label": "Domain / IP",
      title: "Domain / IP",
      placeholder: "domain or ip contains"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network_monitor-history-table-host"
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
            "data-testid": "network_monitor-history-empty",
            text: "No connection events match criteria."
          }));
          return;
        }

        var tbl = window.FOSS.dom.el("table", {
          className: "table w-full text-xs",
          style: "table-layout: fixed; width: 100%; min-width: 0;",
          "data-testid": "network_monitor-history-table"
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
      "data-testid": "network_monitor-history-search-btn",
      "aria-label": "Search",
      title: "Search",
      onclick: searchHist
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Search" })
    ]);

    var retentionBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "network_monitor-history-retention-btn",
      "aria-label": "Set retention period",
      title: "Set retention period",
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
      "data-testid": "network_monitor-history-wipe-btn",
      "aria-label": "Wipe all history",
      title: "Wipe all history",
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
    panel.setAttribute("data-testid", "network_monitor-page");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Network Statistics & Insights" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Analyze top contacting processes, frequent destinations, and unrecognized hosts."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network_monitor-stats-status",
      text: "Ready"
    });

    var statsContainer = window.FOSS.dom.el("div", {
      className: "grid grid-cols-2 gap-md",
      "data-testid": "network_monitor-stats-grid"
    });

    function loadStats() {
      statusBar.textContent = "Loading stats...";
      window.FOSS.api("network_stats", { limit: 10, days: 30 }).then(function (res) {
        statsContainer.innerHTML = "";
        statusBar.textContent = "Stats updated.";

        var procsCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "network_monitor-stats-top-procs" }, [
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

        var domsCard = window.FOSS.dom.el("div", { className: "card", "data-testid": "network_monitor-stats-top-doms" }, [
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

        function destinationCard(testid, title, hint, emptyText, list, nextKnown, btnLabel) {
          var card = window.FOSS.dom.el("div", { className: "card col-span-2", "data-testid": testid }, [
            window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: title }),
            window.FOSS.dom.el("p", { className: "text-xs text-muted mb-sm", text: hint })
          ]);
          var shown = (list || []).slice(0, 10);
          if (!shown.length) {
            card.appendChild(window.FOSS.dom.el("p", { className: "text-xs text-muted", text: emptyText }));
            return card;
          }
          shown.forEach(function (u) {
            var destLabel = u.domain || u.ip || "Unknown";
            card.appendChild(window.FOSS.dom.el("div", { className: "row justify-between items-center text-xs py-xs" }, [
              window.FOSS.dom.el("span", { className: "font-mono", text: destLabel }),
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-sm",
                "aria-label": btnLabel + " " + destLabel,
                title: btnLabel + " " + destLabel,
                onclick: function () {
                  window.FOSS.api("network_manage_destinations", { destination: u.ip || destLabel, known: nextKnown }).then(function () {
                    loadStats();
                  });
                }
              }, [window.FOSS.dom.el("span", { text: btnLabel })])
            ]));
          });
          return card;
        }

        var unknownsCard = destinationCard(
          "network_monitor-stats-unknowns", "New / unknown destinations",
          "Destinations not yet explicitly marked as known.",
          "All destinations are approved and recognized.",
          res && res.unknown_destinations, true, "Mark as Known"
        );
        var knownsCard = destinationCard(
          "network_monitor-stats-knowns", "Known destinations",
          "Destinations you approved. Mark as unknown to flag them again.",
          "No destinations are marked as known yet.",
          res && res.known_destinations, false, "Mark as Unknown"
        );

        statsContainer.appendChild(procsCard);
        statsContainer.appendChild(domsCard);
        statsContainer.appendChild(unknownsCard);
        statsContainer.appendChild(knownsCard);
      });
    }

    var refreshStatsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary mb-md",
      "data-testid": "network_monitor-refresh-stats-btn",
      "aria-label": "Refresh stats",
      title: "Refresh stats",
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
    panel.setAttribute("data-testid", "network_monitor-page");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Per-App Summary" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Summary of bandwidth usage and total connections grouped by executable process."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "network_monitor-apps-status",
      text: "Ready"
    });

    var tableHost = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "network_monitor-apps-table-host"
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
            "data-testid": "network_monitor-apps-empty",
            text: "No applications logged yet."
          }));
          return;
        }

        var tbl = window.FOSS.dom.el("table", {
          className: "table w-full text-xs",
          style: "table-layout: fixed; width: 100%; min-width: 0;",
          "data-testid": "network_monitor-apps-table"
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
      "data-testid": "network_monitor-apps-refresh-btn",
      "aria-label": "Refresh",
      title: "Refresh",
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
    icon: "network_monitor",
    defaults: [
      { key: "poll_interval", label: "Live poll interval (seconds)", type: "number", default: 2, min: 0, max: 60, step: 1, hint: "0 turns automatic refresh off." },
      {
        key: "default_sort",
        label: "Default sort column",
        type: "select",
        default: "process",
        options: [
          { value: "pid", label: "PID" },
          { value: "process", label: "Process" },
          { value: "source_identity", label: "Source Identity" },
          { value: "trust_level", label: "Trust Level" },
          { value: "proto", label: "Proto" },
          { value: "local", label: "Local" },
          { value: "remote", label: "Remote" },
          { value: "host", label: "Host" }
        ]
      },
      {
        key: "status_filter",
        label: "Default connection state filter",
        type: "select",
        default: "ALL",
        options: [
          { value: "ALL", label: "All Connections" },
          { value: "ESTABLISHED", label: "Established" },
          { value: "LISTEN", label: "Listening" },
          { value: "UDP", label: "UDP" },
          { value: "NEW", label: "New Destinations" }
        ]
      }
    ],
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
