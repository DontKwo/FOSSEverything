// Playlist Porter: convert playlists between Spotify, YouTube, and YouTube Music.
window.FOSS = window.FOSS || {};

(function () {
  var TOOL_ID = "playlist";
  var currentTracks = [];
  var currentDirection = "spotify -> youtube / youtube music";
  function defaultDirection() {
    return String(window.FOSS.toolDefaults.get(TOOL_ID, "direction", "spotify -> youtube / youtube music"));
  }

  var EXPORT_TYPES = {
    m3u8: { label: "M3U8", method: "playlist_export_m3u8", type: { name: "M3U8 Playlist (*.m3u8)", extensions: ["m3u8"] } },
    csv: { label: "CSV", method: "playlist_export_csv", type: { name: "CSV Spreadsheet (*.csv)", extensions: ["csv"] } },
    json: { label: "JSON", method: "playlist_export_json", type: { name: "JSON Document (*.json)", extensions: ["json"] } }
  };

  function formatDuration(ms) {
    if (!ms || isNaN(ms)) return "";
    var totalSec = Math.floor(ms / 1000);
    var min = Math.floor(totalSec / 60);
    var sec = totalSec % 60;
    return min + ":" + (sec < 10 ? "0" + sec : sec);
  }

  function trackDuration(track) {
    return track.duration_str || formatDuration(track.duration_ms);
  }

  function defaultExportFormat() {
    var value = String(window.FOSS.toolDefaults.get(TOOL_ID, "export_format", "m3u8"));
    return EXPORT_TYPES[value] ? value : "m3u8";
  }

  function failureReason(res, fallback) {
    if (res && res.error) {
      return typeof res.error === "string" ? res.error : (res.error.message || fallback);
    }
    return fallback;
  }

  function toastError(message) {
    window.FOSS.toast.show({ message: message, type: "error" });
  }

  function toastSuccess(message) {
    window.FOSS.toast.show({ message: message, type: "success" });
  }

  function extOf(path) {
    var match = /\.([A-Za-z0-9]+)$/.exec(path || "");
    return match ? match[1].toLowerCase() : "";
  }

  function orderedExportTypes(preferred) {
    var order = [preferred].concat(Object.keys(EXPORT_TYPES).filter(function (key) { return key !== preferred; }));
    return order.map(function (key) { return EXPORT_TYPES[key].type; });
  }

  function exportTracks(preferred) {
    if (!currentTracks.length) {
      return Promise.resolve({ ok: false, error: "No tracks to export. Import or parse a playlist first." });
    }
    return window.FOSS.api("select_save_path", {
      title: "Export Playlist",
      default_name: "playlist",
      file_types: orderedExportTypes(preferred)
    }).then(function (sel) {
      var path = (sel && (sel.path || (sel.paths && sel.paths[0]))) || "";
      if (!path) return { ok: false, cancelled: true };
      var fmt = EXPORT_TYPES[extOf(path)] ? extOf(path) : preferred;
      return window.FOSS.api(EXPORT_TYPES[fmt].method, { tracks: currentTracks, output_path: path }, { silent: true }).then(function (res) {
        if (!res || res.ok === false || !res.output_path) {
          return { ok: false, error: failureReason(res, "The playlist file could not be written.") };
        }
        return { ok: true, output_path: res.output_path, label: EXPORT_TYPES[fmt].label };
      });
    });
  }

  function exportButton(fmt, testid, onDone) {
    var isDefault = fmt === defaultExportFormat();
    return window.FOSS.dom.el("button", {
      className: "btn btn-sm " + (isDefault ? "btn-primary" : "btn-secondary"),
      "data-testid": testid,
      type: "button",
      title: "Export as " + EXPORT_TYPES[fmt].label,
      onClick: function () {
        exportTracks(fmt).then(function (result) {
          if (result.cancelled) return;
          if (!result.ok) {
            toastError("Export failed: " + result.error);
            return;
          }
          onDone(result);
        });
      }
    }, [
      window.FOSS.icons.el(fmt === "m3u8" ? "music" : "file-text", 14),
      window.FOSS.dom.el("span", { text: "Export " + EXPORT_TYPES[fmt].label })
    ]);
  }

  function createBanner(testid) {
    var span = window.FOSS.dom.el("span", { className: "banner-msg", text: "" });
    var banner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": testid
    }, [window.FOSS.icons.el("alert", 18), span]);
    return {
      el: banner,
      show: function (msg) {
        span.textContent = msg;
        banner.classList.remove("hidden");
      },
      clear: function () {
        banner.classList.add("hidden");
      }
    };
  }

  function openSearchUrl(url) {
    window.FOSS.api("open_url", { url: url });
  }

  function renderFetch(panel) {
    var D = window.FOSS.dom;
    panel.innerHTML = "";

    var statusBar = D.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-status",
      text: "Enter a playlist URL or configure API access below."
    });
    var banner = createBanner("playlist-error-banner");

    function fail(prefix, reason) {
      var msg = prefix + ": " + reason;
      banner.show(msg);
      statusBar.textContent = "Error: " + msg;
      toastError(msg);
    }

    var urlInput = D.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-url-input",
      "aria-label": "Paste playlist URL",
      title: "Playlist URL",
      placeholder: "Paste Spotify or YouTube playlist URL (e.g. https://open.spotify.com/playlist/... or https://www.youtube.com/playlist?list=...)"
    });

    var fetchBtn = D.el("button", {
      className: "btn btn-primary",
      "data-testid": "playlist-fetch-btn",
      "aria-label": "Fetch playlist",
      title: "Fetch playlist",
      type: "button",
      onClick: function () {
        banner.clear();
        var url = urlInput.value.trim();
        if (!url) {
          banner.show("Please enter a valid playlist URL.");
          statusBar.textContent = "Error: Please enter a valid playlist URL.";
          return;
        }
        statusBar.textContent = "Fetching playlist tracks...";
        window.FOSS.api("playlist_fetch", { url: url }, { silent: true }).then(function (res) {
          if (res && res.ok !== false && res.tracks) {
            currentTracks = res.tracks;
            statusBar.textContent = "Loaded " + res.tracks.length + " tracks.";
            toastSuccess("Loaded " + res.tracks.length + " tracks.");
            window.FOSS.router.open(TOOL_ID, "output");
            return;
          }
          fail("Could not fetch playlist", failureReason(res, "The remote service returned no tracks."));
        });
      }
    }, [window.FOSS.icons.el("download", 16), D.el("span", { text: "Fetch Playlist" })]);

    var chooseFileBtn = D.el("button", {
      className: "btn btn-primary",
      "data-testid": "playlist-choose-file",
      type: "button",
      onClick: function () {
        banner.clear();
        window.FOSS.api("select_file", {
          title: "Select Playlist File",
          file_types: ["m3u8", "m3u", "csv", "txt", "json"]
        }).then(function (res) {
          var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          if (!p) return;
          statusBar.textContent = "Importing playlist file...";
          window.FOSS.api("playlist_import_file", { file_path: p }, { silent: true }).then(function (importRes) {
            if (importRes && importRes.ok !== false && importRes.tracks && importRes.tracks.length) {
              currentTracks = importRes.tracks;
              statusBar.textContent = "Loaded " + importRes.tracks.length + " tracks from file.";
              toastSuccess("Loaded " + importRes.tracks.length + " tracks.");
              window.FOSS.router.open(TOOL_ID, "output");
              return;
            }
            fail("Could not import file", failureReason(importRes, "No tracks found in playlist file."));
          });
        });
      }
    }, [window.FOSS.icons.el("folder", 16), D.el("span", { text: "Import Playlist File (M3U8, CSV)..." })]);

    var exportDefaultBtn = exportButton(defaultExportFormat(), "playlist-export-default-btn", function (result) {
      statusBar.textContent = result.label + " Playlist Exported: " + result.output_path;
      toastSuccess(result.label + " playlist exported.");
    });

    var fileCard = D.el("div", { className: "card card-compact" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Import Local Playlist File" }),
      D.el("div", { className: "text-xs text-muted mb-2", text: "Open existing M3U, M3U8, CSV, or JSON playlist files." }),
      D.el("div", { className: "row gap-2 flex-wrap" }, [chooseFileBtn, exportDefaultBtn])
    ]);

    var fetchCard = D.el("div", { className: "card card-compact" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Fetch from URL (Spotify or YouTube Playlist)" }),
      urlInput,
      D.el("div", { className: "row mt-2" }, [fetchBtn])
    ]);

    var spotifyClientIdInput = D.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-spotify-client-id",
      "aria-label": "Spotify Client ID",
      title: "Spotify Client ID",
      placeholder: "Paste Spotify Client ID"
    });

    function authCall(method, params, okMessage, failPrefix) {
      window.FOSS.api(method, params, { silent: true }).then(function (res) {
        if (res && res.ok !== false && (res.saved || res.logged_in !== false)) {
          toastSuccess(okMessage);
          return;
        }
        toastError(failPrefix + ": " + failureReason(res, "The service did not confirm the request."));
      });
    }

    var spotifyCard = D.el("div", { className: "card card-compact" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Spotify Account Setup (Optional)" }),
      window.FOSS.components.field("Spotify Client ID", spotifyClientIdInput),
      D.el("div", { className: "row gap-2 mt-2 flex-wrap" }, [
        D.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-spotify-save-id-btn",
          type: "button",
          onClick: function () {
            authCall("playlist_spotify_auth", { action: "save_client_id", client_id: spotifyClientIdInput.value.trim() }, "Spotify Client ID saved.", "Failed to save Spotify Client ID");
          }
        }, [D.el("span", { text: "Save Client ID" })]),
        D.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-spotify-login-btn",
          type: "button",
          onClick: function () {
            authCall("playlist_spotify_auth", { action: "login" }, "Logged in with Spotify.", "Failed to log in with Spotify");
          }
        }, [D.el("span", { text: "Spotify Login" })]),
        D.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "playlist-spotify-instructions-btn",
          type: "button",
          onClick: function () {
            window.FOSS.toast.show({
              message: "1. Create app in Spotify Developer Dashboard. 2. Set Redirect URI to http://127.0.0.1:8888/callback. 3. Save Client ID.",
              type: "info"
            });
          }
        }, [D.el("span", { text: "Setup Guide" })])
      ])
    ]);

    var ytClientIdInput = D.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-yt-client-id",
      "aria-label": "Google OAuth Client ID",
      title: "Google OAuth Client ID",
      placeholder: "Google OAuth Client ID"
    });

    var ytClientSecretInput = D.el("input", {
      type: "password",
      className: "input",
      "data-testid": "playlist-yt-client-secret",
      "aria-label": "Google OAuth Client Secret",
      title: "Google OAuth Client Secret",
      placeholder: "Google OAuth Client Secret"
    });

    var ytCard = D.el("div", { className: "card card-compact" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "YouTube Account Setup (Optional for Playlist Creation)" }),
      D.el("div", { className: "grid grid-cols-2 gap-2" }, [
        window.FOSS.components.field("Client ID", ytClientIdInput),
        window.FOSS.components.field("Client Secret", ytClientSecretInput)
      ]),
      D.el("div", { className: "row gap-2 mt-2 flex-wrap" }, [
        D.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-yt-save-btn",
          type: "button",
          onClick: function () {
            authCall("playlist_youtube_auth", {
              action: "save_credentials",
              client_id: ytClientIdInput.value.trim(),
              client_secret: ytClientSecretInput.value.trim()
            }, "YouTube credentials saved.", "Failed to save YouTube credentials");
          }
        }, [D.el("span", { text: "Save Credentials" })]),
        D.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-yt-login-btn",
          type: "button",
          onClick: function () {
            authCall("playlist_youtube_auth", { action: "login" }, "Logged in with YouTube.", "Failed to log in with YouTube");
          }
        }, [D.el("span", { text: "Log In with YouTube" })])
      ])
    ]);

    var privacyNotice = D.el("div", {
      className: "text-xs text-muted p-2 rounded bg-surface border border-border",
      text: "Privacy & Offline Note: FOSSEverything is completely offline by default. Connecting accounts or fetching remote playlists is strictly optional and only initiates requests when you click Fetch or Log In."
    });

    D.append(panel, statusBar);
    D.append(panel, banner.el);
    D.append(panel, D.el("div", { className: "flex-col gap-3" }, [fileCard, fetchCard, privacyNotice, spotifyCard, ytCard]));
  }

  function renderPaste(panel) {
    var D = window.FOSS.dom;
    panel.innerHTML = "";

    var statusBar = D.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-paste-status",
      text: "Paste track lines formatted as Artist - Song Title."
    });
    var banner = createBanner("playlist-paste-error-banner");

    var directionSelect = D.el("select", {
      className: "input",
      "data-testid": "playlist-direction-select",
      "aria-label": "Direction",
      title: "Direction",
      onChange: function () { currentDirection = directionSelect.value; }
    }, [
      D.el("option", { value: "spotify -> youtube / youtube music", text: "Spotify -> YouTube / YouTube Music" }),
      D.el("option", { value: "youtube -> spotify", text: "YouTube -> Spotify" })
    ]);
    currentDirection = defaultDirection();
    directionSelect.value = currentDirection;

    var textarea = D.el("textarea", {
      className: "input font-mono text-sm playlist-paste-input",
      "data-testid": "playlist-paste-input",
      "aria-label": "Paste Tracklist Lines",
      title: "Paste Tracklist Lines",
      placeholder: "Queen - Bohemian Rhapsody\nThe Beatles - Hey Jude\nPink Floyd - Comfortably Numb",
      rows: 10
    });

    var pasteGroup = D.el("div", { className: "card card-compact flex-col gap-3" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Paste Tracklist Text (Artist - Title, Numbered Lists, CSV Lines)" }),
      window.FOSS.components.field("Conversion Direction", directionSelect),
      textarea,
      D.el("div", { className: "row gap-2" }, [
        D.el("button", {
          className: "btn btn-primary",
          "data-testid": "playlist-parse-btn",
          type: "button",
          onClick: function () {
            banner.clear();
            var text = textarea.value.trim();
            if (!text) {
              banner.show("Please enter or paste tracklist text first.");
              return;
            }
            statusBar.textContent = "Parsing tracks...";
            window.FOSS.api("playlist_parse_text", { text: text }, { silent: true }).then(function (res) {
              if (res && res.ok !== false && res.tracks) {
                currentTracks = res.tracks;
                statusBar.textContent = "Parsed " + res.tracks.length + " tracks.";
                toastSuccess("Parsed " + res.tracks.length + " tracks.");
                window.FOSS.router.open(TOOL_ID, "output");
                return;
              }
              var reason = failureReason(res, "Failed to parse tracklist.");
              banner.show(reason);
              toastError("Could not parse tracklist: " + reason);
            });
          }
        }, [window.FOSS.icons.el("file-text", 16), D.el("span", { text: "Parse Tracks" })]),
        D.el("button", {
          className: "btn btn-ghost",
          "data-testid": "playlist-paste-clear-btn",
          type: "button",
          onClick: function () {
            textarea.value = "";
            banner.clear();
            statusBar.textContent = "Cleared tracklist text.";
          }
        }, [D.el("span", { text: "Clear" })])
      ])
    ]);

    D.append(panel, statusBar);
    D.append(panel, banner.el);
    D.append(panel, pasteGroup);
  }

  function searchButton(label, title, url) {
    return window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      type: "button",
      text: label,
      title: title,
      onClick: function () { openSearchUrl(url); }
    });
  }

  function buildTrackTable() {
    var D = window.FOSS.dom;
    var thead = D.el("thead", {}, [
      D.el("tr", {}, [
        D.el("th", { className: "playlist-col-num", text: "#" }),
        D.el("th", { text: "Title" }),
        D.el("th", { text: "Artist" }),
        D.el("th", { text: "Album" }),
        D.el("th", { text: "Duration" }),
        D.el("th", { className: "playlist-col-links", text: "Search Links" })
      ])
    ]);
    var tbody = D.el("tbody", {});
    currentTracks.forEach(function (t, idx) {
      var query = encodeURIComponent((t.artist || "") + " " + (t.title || ""));
      tbody.appendChild(D.el("tr", {}, [
        D.el("td", { className: "font-mono text-muted text-xs", text: String(idx + 1) }),
        D.el("td", { className: "font-semibold", text: t.title || "Unknown" }),
        D.el("td", { text: t.artist || "Unknown" }),
        D.el("td", { className: "text-muted", text: t.album || "" }),
        D.el("td", { className: "font-mono text-xs text-muted", text: trackDuration(t) }),
        D.el("td", {}, [
          D.el("div", { className: "row gap-1" }, [
            searchButton("Spotify", "Search on Spotify", "https://open.spotify.com/search/" + query),
            searchButton("YT", "Search on YouTube", "https://www.youtube.com/results?search_query=" + query),
            searchButton("YTM", "Search on YouTube Music", "https://music.youtube.com/search?q=" + query)
          ])
        ])
      ]));
    });
    var table = D.el("table", { className: "table text-sm playlist-table", "data-testid": "playlist-tracks-table" }, [thead, tbody]);
    return D.el("div", { className: "table-wrap playlist-table-wrap", "data-testid": "playlist-table-scroll" }, [table]);
  }

  function renderOutput(panel) {
    var D = window.FOSS.dom;
    panel.innerHTML = "";

    var statusBar = D.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-output-status",
      text: "Loaded Tracks: " + currentTracks.length
    });
    var banner = createBanner("playlist-output-error-banner");

    var resultCardHost = D.el("div", { className: "hidden mb-sm", "data-testid": "playlist-output-result" });

    function showResult(path, titleText) {
      resultCardHost.innerHTML = "";
      D.append(resultCardHost, window.FOSS.components.resultCard({
        testid: "playlist-result-card",
        title: titleText || "Playlist Export Ready",
        outputPath: path
      }));
      resultCardHost.classList.remove("hidden");
    }

    function onExported(result) {
      showResult(result.output_path, result.label + " Playlist Exported");
    }

    var exportCsvBtn = exportButton("csv", "playlist-export-csv-btn", onExported);
    var exportM3u8Btn = exportButton("m3u8", "playlist-export-m3u8-btn", onExported);
    var exportJsonBtn = exportButton("json", "playlist-export-json-btn", onExported);

    var copyLinksBtn = D.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "playlist-copy-links-btn",
      type: "button",
      onClick: function () {
        if (!currentTracks.length) return;
        var links = currentTracks.map(function (t) {
          return (t.artist || "") + " - " + (t.title || "") + ": " + (t.spotify_url || t.youtube_url || "");
        }).join("\n");
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          toastError("Clipboard access is not available in this window.");
          return;
        }
        navigator.clipboard.writeText(links).then(function () {
          toastSuccess("Copied track links to clipboard.");
        }).catch(function (err) {
          toastError("Failed to copy links: " + ((err && err.message) || String(err)));
        });
      }
    }, [window.FOSS.icons.el("copy", 14), D.el("span", { text: "Copy Links" })]);

    var buildYtBtn = D.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "playlist-yt-build-btn",
      type: "button",
      onClick: function () {
        if (!currentTracks.length) {
          toastError("No tracks to export.");
          return;
        }
        window.FOSS.dialogs.prompt({
          title: "Create YouTube Playlist",
          message: "Enter YouTube playlist title:",
          defaultValue: "Imported Playlist",
          confirmText: "Create"
        }).then(function (playlistName) {
          if (!playlistName) return;
          statusBar.textContent = "Creating YouTube playlist: " + playlistName + "...";
          window.FOSS.job("playlist_youtube_build", { playlist_title: playlistName, tracks: currentTracks }).then(function (res) {
            if (res && res.ok !== false && res.playlist_url) {
              statusBar.textContent = "Created YouTube playlist (" + (res.added_count || currentTracks.length) + " tracks).";
              toastSuccess("Playlist created on YouTube.");
              return;
            }
            var reason = failureReason(res, "YouTube did not return a playlist URL.");
            statusBar.textContent = "Error: " + reason;
            toastError("Could not create YouTube playlist: " + reason);
          });
        });
      }
    }, [window.FOSS.icons.el("play", 14), D.el("span", { text: "Create YouTube Playlist..." })]);

    var exportToolbar = D.el("div", {
      className: "row gap-2 items-center justify-between flex-wrap card card-compact playlist-export-bar"
    }, [
      D.el("div", { className: "text-sm font-semibold", text: "Export & Sync" }),
      D.el("div", { className: "row gap-2 items-center flex-wrap" }, [exportCsvBtn, exportM3u8Btn, exportJsonBtn, copyLinksBtn, buildYtBtn])
    ]);

    var contentHost = D.el("div", { className: "card card-compact", "data-testid": "playlist-tracks-card" });
    if (!currentTracks || currentTracks.length === 0) {
      contentHost.appendChild(D.el("div", {
        className: "p-4 text-center text-muted font-mono text-sm",
        "data-testid": "playlist-empty-state",
        text: "No tracks loaded yet. Fetch a URL or paste text."
      }));
    } else {
      D.append(contentHost, buildTrackTable());
    }

    D.append(panel, statusBar);
    D.append(panel, banner.el);
    D.append(panel, resultCardHost);
    D.append(panel, D.el("div", { className: "flex-col gap-3" }, [exportToolbar, contentHost]));
  }

  window.FOSS.router.register({
    id: TOOL_ID,
    title: "Playlist Porter",
    navName: "Playlist Porter",
    category: "Media",
    icon: "playlist",
    defaults: [
      { key: "export_format", label: "Default export format", type: "select", options: [{ value: "m3u8", label: "M3U8" }, { value: "csv", label: "CSV" }, { value: "json", label: "JSON" }], default: "m3u8" },
      { key: "direction", label: "Default conversion direction", type: "select", options: [
        { value: "spotify -> youtube / youtube music", label: "Spotify -> YouTube / YouTube Music" },
        { value: "youtube -> spotify", label: "YouTube -> Spotify" }
      ], default: "spotify -> youtube / youtube music" }
    ],
    tabs: [
      { id: "import", label: "Import / Fetch", aliases: ["fetch"], render: renderFetch },
      { id: "paste", label: "Paste Text", render: renderPaste },
      { id: "output", label: "Tracklist & Output", render: renderOutput }
    ]
  });
})();
