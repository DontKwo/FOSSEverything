// Playlist Porter: convert playlists between Spotify, YouTube, and YouTube Music.
window.FOSS = window.FOSS || {};

(function () {
  var currentTracks = [];
  var currentDirection = "spotify -> youtube youtube music";

  function renderFetch(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-playlist");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Playlist Porter (Spotify <-> YouTube / YouTube Music)" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Port public or authenticated playlists between Spotify, YouTube, and YouTube Music."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "playlist-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    // Group: Fetch from URL
    var fetchGroup = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "Fetch from URL (Spotify playlist · YouTube playlist · YouTube Music playlist)"
      }),
      window.FOSS.dom.el("div", { className: "field" }, [
        window.FOSS.dom.el("input", {
          type: "text",
          className: "input",
          "data-testid": "playlist-url-input",
          "aria-label": "Paste playlist URL",
          title: "Playlist URL",
          placeholder: "paste spotify or youtube playlist url here - e.g. https://open.spotify.com/playlist/... or https://www.youtube.com/playlist?list="
        })
      ]),
      window.FOSS.dom.el("div", { className: "row mt-sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn primary",
          "data-testid": "playlist-fetch-btn",
          "aria-label": "Fetch playlist",
          title: "Fetch playlist",
          style: "min-height: 36px; min-width: 140px;",
          onclick: function () {
            clearError();
            var input = panel.querySelector("[data-testid='playlist-url-input']");
            var url = input ? input.value.trim() : "";
            if (!url) {
              showError("Please enter a valid playlist URL.");
              return;
            }
            statusBar.textContent = "Fetching playlist tracks...";
            window.FOSS.api("playlist_fetch", { url: url }).then(function (res) {
              if (res && res.tracks) {
                currentTracks = res.tracks;
                statusBar.textContent = "Loaded " + res.tracks.length + " tracks.";
                window.FOSS.toast.show({ message: "Loaded " + res.tracks.length + " tracks.", type: "success" });
                window.FOSS.router.open("playlist", "output");
              } else if (res && res.error) {
                showError(res.error.message || "Failed to fetch playlist.");
              }
            }).catch(function (err) {
              showError(err.message || "Fetch request failed.");
            });
          }
        }, [
          window.FOSS.icons.el("download", 16),
          window.FOSS.dom.el("span", { text: "Fetch Playlist" })
        ])
      ])
    ]);

    // Group: Spotify Login
    var spotifyClientIdInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-spotify-client-id",
      "aria-label": "Spotify Client ID",
      title: "Spotify Client ID",
      placeholder: "spotify client id"
    });

    var spotifyGroup = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "Spotify Login"
      }),
      window.FOSS.dom.el("div", { className: "field mb-sm" }, [spotifyClientIdInput]),
      window.FOSS.dom.el("div", { className: "row gap-sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn secondary",
          "data-testid": "playlist-spotify-save-id-btn",
          "aria-label": "Save client ID",
          title: "Save client ID",
          style: "min-height: 36px;",
          onclick: function () {
            var cid = spotifyClientIdInput.value.trim();
            window.FOSS.api("playlist_spotify_auth", { action: "save_client_id", client_id: cid }).then(function () {
              window.FOSS.toast.show({ message: "Spotify Client ID saved.", type: "success" });
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Save Client ID" })]),
        window.FOSS.dom.el("button", {
          className: "btn secondary",
          "data-testid": "playlist-spotify-login-btn",
          "aria-label": "Log in with Spotify",
          title: "Log in with Spotify",
          style: "min-height: 36px;",
          onclick: function () {
            window.FOSS.api("playlist_spotify_auth", { action: "login" }).then(function (res) {
              if (res && res.logged_in) {
                window.FOSS.toast.show({ message: "Logged in with Spotify.", type: "success" });
              }
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Log In with Spotify" })]),
        window.FOSS.dom.el("button", {
          className: "btn ghost",
          "data-testid": "playlist-spotify-instructions-btn",
          "aria-label": "See step-by-step instructions",
          title: "See step-by-step instructions",
          style: "min-height: 36px;",
          onclick: function () {
            window.FOSS.alert({
              title: "Spotify Setup Instructions",
              message: "1. Create an application in Spotify Developer Dashboard.\n2. Add http://127.0.0.1:8888/callback to Redirect URIs.\n3. Paste your Client ID and log in."
            });
          }
        }, [window.FOSS.dom.el("span", { text: "See step-by-step instructions" })])
      ])
    ]);

    // Group: YouTube Login
    var ytClientIdInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input mb-xs",
      "data-testid": "playlist-yt-client-id",
      "aria-label": "Google OAuth client ID",
      title: "Google OAuth client ID",
      placeholder: "google oauth client id"
    });

    var ytClientSecretInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input",
      "data-testid": "playlist-yt-client-secret",
      "aria-label": "Google OAuth client secret",
      title: "Google OAuth client secret",
      placeholder: "google oauth client secret"
    });

    var ytGroup = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "YouTube login (for creating a real YouTube playlist)"
      }),
      window.FOSS.dom.el("div", { className: "field mb-sm" }, [ytClientIdInput, ytClientSecretInput]),
      window.FOSS.dom.el("div", { className: "row gap-sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn secondary",
          "data-testid": "playlist-yt-save-btn",
          "aria-label": "Save credentials",
          title: "Save credentials",
          style: "min-height: 36px;",
          onclick: function () {
            var cid = ytClientIdInput.value.trim();
            var sec = ytClientSecretInput.value.trim();
            window.FOSS.api("playlist_youtube_auth", { action: "save_credentials", client_id: cid, client_secret: sec }).then(function () {
              window.FOSS.toast.show({ message: "YouTube credentials saved.", type: "success" });
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Save Credentials" })]),
        window.FOSS.dom.el("button", {
          className: "btn secondary",
          "data-testid": "playlist-yt-login-btn",
          "aria-label": "Log in with YouTube",
          title: "Log in with YouTube",
          style: "min-height: 36px;",
          onclick: function () {
            window.FOSS.api("playlist_youtube_auth", { action: "login" }).then(function (res) {
              if (res && res.logged_in) {
                window.FOSS.toast.show({ message: "Logged in with YouTube.", type: "success" });
              }
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Log In with YouTube" })])
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(fetchGroup);
    panel.appendChild(spotifyGroup);
    panel.appendChild(ytGroup);
  }

  function renderPaste(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-playlist");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Paste Tracklist Text" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Parse tracklists from raw text lines, numbered lists, or CSV spreadsheets."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-paste-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "playlist-paste-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var directionSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "playlist-direction-select",
      "aria-label": "Direction",
      title: "Direction",
      onchange: function () {
        currentDirection = directionSelect.value;
      }
    }, [
      window.FOSS.dom.el("option", { value: "spotify -> youtube youtube music", text: "Spotify -> YouTube YouTube Music" }),
      window.FOSS.dom.el("option", { value: "youtube -> spotify", text: "YouTube -> Spotify" })
    ]);
    directionSelect.value = currentDirection;

    var textarea = window.FOSS.dom.el("textarea", {
      className: "input font-mono text-sm",
      "data-testid": "playlist-paste-input",
      "aria-label": "Paste tracklist lines here",
      title: "Paste tracklist lines here",
      placeholder: "paste tracklist lines here",
      rows: 10,
      style: "width: 100%; min-height: 180px;"
    });

    var pasteGroup = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "Or paste tracklist text (artist - song, numbered lists, csv rows)"
      }),
      window.FOSS.dom.el("div", { className: "row items-center gap-sm mb-sm" }, [
        window.FOSS.dom.el("span", { className: "text-sm text-muted", text: "Direction" }),
        directionSelect
      ]),
      window.FOSS.dom.el("div", { className: "field mb-sm" }, [textarea]),
      window.FOSS.dom.el("div", { className: "row gap-sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn primary",
          "data-testid": "playlist-parse-btn",
          "aria-label": "Parse tracks",
          title: "Parse tracks",
          style: "min-height: 36px; min-width: 130px;",
          onclick: function () {
            clearError();
            var text = textarea.value.trim();
            if (!text) {
              showError("Please enter or paste tracklist text first.");
              return;
            }
            statusBar.textContent = "Parsing tracks...";
            window.FOSS.api("playlist_parse_text", { text: text }).then(function (res) {
              if (res && res.tracks) {
                currentTracks = res.tracks;
                statusBar.textContent = "Parsed " + res.tracks.length + " tracks.";
                window.FOSS.toast.show({ message: "Parsed " + res.tracks.length + " tracks.", type: "success" });
                window.FOSS.router.open("playlist", "output");
              } else if (res && res.error) {
                showError(res.error.message || "Failed to parse tracklist.");
              }
            }).catch(function (err) {
              showError(err.message || "Parse request failed.");
            });
          }
        }, [
          window.FOSS.icons.el("file-text", 16),
          window.FOSS.dom.el("span", { text: "Parse Tracks" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn ghost",
          "data-testid": "playlist-paste-clear-btn",
          "aria-label": "Clear",
          title: "Clear",
          style: "min-height: 36px;",
          onclick: function () {
            textarea.value = "";
            clearError();
            statusBar.textContent = "Cleared";
          }
        }, [window.FOSS.dom.el("span", { text: "Clear" })])
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(pasteGroup);
  }

  function renderOutput(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-playlist");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Mapped Tracklist & Output" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Review loaded tracks, open direct search query links, and export to CSV or M3U8."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-output-status",
      text: "Tracks: " + currentTracks.length
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "playlist-output-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var resultCardHost = window.FOSS.dom.el("div", {
      className: "hidden mb-sm",
      "data-testid": "playlist-output-result"
    });

    function showResult(path, titleText) {
      resultCardHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "playlist-result-card",
        title: titleText || "Playlist Export Ready",
        outputPath: path
      });
      resultCardHost.appendChild(card);
      resultCardHost.classList.remove("hidden");
    }

    var directionSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "playlist-output-direction",
      "aria-label": "Direction",
      title: "Direction",
      onchange: function () {
        currentDirection = directionSelect.value;
      }
    }, [
      window.FOSS.dom.el("option", { value: "spotify -> youtube youtube music", text: "Spotify -> YouTube YouTube Music" }),
      window.FOSS.dom.el("option", { value: "youtube -> spotify", text: "YouTube -> Spotify" })
    ]);
    directionSelect.value = currentDirection;

    var controlsRow = window.FOSS.dom.el("div", { className: "row items-center justify-between mb-sm flex-wrap gap-sm" }, [
      window.FOSS.dom.el("div", { className: "row items-center gap-sm" }, [
        window.FOSS.dom.el("span", { className: "text-sm text-muted", text: "Direction" }),
        directionSelect
      ]),
      window.FOSS.dom.el("div", { className: "row gap-sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn secondary text-xs",
          "data-testid": "playlist-export-csv-btn",
          "aria-label": "Export CSV",
          title: "Export CSV",
          style: "min-height: 36px;",
          onclick: function () {
            if (!currentTracks.length) return;
            window.FOSS.api("select_save_path", { title: "Save CSV Playlist", default_name: "playlist.csv" }).then(function (res) {
              var p = (res && res.paths && res.paths[0]) || "";
              if (!p) return;
              window.FOSS.api("playlist_export_csv", { tracks: currentTracks, output_path: p }).then(function (exportRes) {
                if (exportRes && exportRes.output_path) {
                  showResult(exportRes.output_path, "CSV Playlist Exported");
                }
              });
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Export CSV" })]),
        window.FOSS.dom.el("button", {
          className: "btn secondary text-xs",
          "data-testid": "playlist-export-m3u8-btn",
          "aria-label": "Export M3U8",
          title: "Export M3U8",
          style: "min-height: 36px;",
          onclick: function () {
            if (!currentTracks.length) return;
            window.FOSS.api("select_save_path", { title: "Save M3U8 Playlist", default_name: "playlist.m3u8" }).then(function (res) {
              var p = (res && res.paths && res.paths[0]) || "";
              if (!p) return;
              window.FOSS.api("playlist_export_m3u8", { tracks: currentTracks, output_path: p }).then(function (exportRes) {
                if (exportRes && exportRes.output_path) {
                  showResult(exportRes.output_path, "M3U8 Playlist Exported");
                }
              });
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Export M3U8" })])
      ])
    ]);

    var contentHost = window.FOSS.dom.el("div", { className: "card", "data-testid": "playlist-tracks-card" });

    if (!currentTracks || currentTracks.length === 0) {
      contentHost.appendChild(window.FOSS.dom.el("div", {
        className: "empty-state p-lg text-center text-muted",
        "data-testid": "playlist-empty-state"
      }, [
        window.FOSS.dom.el("p", {
          className: "text-sm",
          text: "no tracks loaded yet. paste a url above or enter tracks on the left."
        })
      ]));
    } else {
      var table = window.FOSS.dom.el("table", { className: "table w-full text-sm", "data-testid": "playlist-tracks-table" });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 40px;", text: "#" }),
          window.FOSS.dom.el("th", { text: "Title" }),
          window.FOSS.dom.el("th", { text: "Artist" }),
          window.FOSS.dom.el("th", { text: "Album" }),
          window.FOSS.dom.el("th", { style: "width: 180px;", text: "Quick Search" })
        ])
      ]);
      var tbody = window.FOSS.dom.el("tbody", {});

      currentTracks.forEach(function (t, idx) {
        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { text: String(idx + 1) }),
          window.FOSS.dom.el("td", { className: "font-semibold", text: t.title || "Unknown" }),
          window.FOSS.dom.el("td", { text: t.artist || "Unknown" }),
          window.FOSS.dom.el("td", { text: t.album || "" }),
          window.FOSS.dom.el("td", {}, [
            window.FOSS.dom.el("div", { className: "row gap-xs" }, [
              window.FOSS.dom.el("a", {
                className: "btn ghost text-xs",
                href: t.spotify_url || "#",
                target: "_blank",
                "aria-label": "Spotify",
                title: "Spotify",
                style: "min-height: 28px; padding: 2px 8px;",
                text: "Spotify"
              }),
              window.FOSS.dom.el("a", {
                className: "btn ghost text-xs",
                href: t.youtube_url || "#",
                target: "_blank",
                "aria-label": "YT",
                title: "YT",
                style: "min-height: 28px; padding: 2px 8px;",
                text: "YT"
              }),
              window.FOSS.dom.el("a", {
                className: "btn ghost text-xs",
                href: t.youtube_music_url || "#",
                target: "_blank",
                "aria-label": "YTM",
                title: "YTM",
                style: "min-height: 28px; padding: 2px 8px;",
                text: "YTM"
              })
            ])
          ])
        ]);
        tbody.appendChild(tr);
      });

      table.appendChild(thead);
      table.appendChild(tbody);
      contentHost.appendChild(table);
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultCardHost);
    panel.appendChild(controlsRow);
    panel.appendChild(contentHost);
  }

  window.FOSS.router.register({
    id: "playlist",
    title: "Playlist Porter (Spotify <-> YouTube / YouTube Music)",
    navName: "Playlist Porter",
    category: "media",
    icon: "music",
    tabs: [
      { id: "fetch", label: "Fetch from URL", render: renderFetch },
      { id: "paste", label: "Paste Text", render: renderPaste },
      { id: "output", label: "Tracklist & Output", render: renderOutput }
    ]
  });
})();
