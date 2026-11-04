// Playlist Porter: convert playlists between Spotify, YouTube, and YouTube Music.
window.FOSS = window.FOSS || {};

(function () {
  var currentTracks = [];
  var currentDirection = "spotify -> youtube / youtube music";

  function formatDuration(ms) {
    if (!ms || isNaN(ms)) return "";
    var totalSec = Math.floor(ms / 1000);
    var min = Math.floor(totalSec / 60);
    var sec = totalSec % 60;
    return min + ":" + (sec < 10 ? "0" + sec : sec);
  }

  function renderFetch(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-status",
      text: "Enter a playlist URL or configure API access below."
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
    var urlInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-url-input",
      "aria-label": "Paste playlist URL",
      title: "Playlist URL",
      placeholder: "Paste Spotify or YouTube playlist URL (e.g. https://open.spotify.com/playlist/... or https://www.youtube.com/playlist?list=...)"
    });

    var fetchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "playlist-fetch-btn",
      "aria-label": "Fetch playlist",
      title: "Fetch playlist",
      onClick: function () {
        try {
          clearError();
          var url = urlInput.value.trim();
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
              var errMsg = (res.error && res.error.message) || String(res.error) || "Failed to fetch playlist.";
              showError(errMsg);
              window.FOSS.toast.show({ message: errMsg, type: "error" });
            }
          }).catch(function (err) {
            var errMsg = (err && err.message) || String(err) || "Fetch request failed.";
            showError(errMsg);
            window.FOSS.toast.show({ message: errMsg, type: "error" });
          });
        } catch (err) {
          var errMsg = (err && err.message) || String(err) || "Fetch request failed.";
          showError(errMsg);
          window.FOSS.toast.show({ message: errMsg, type: "error" });
        }
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Fetch Playlist" })
    ]);

    var chooseFileBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "playlist-choose-file",
      type: "button",
      onClick: function () {
        try {
          clearError();
          window.FOSS.api("select_file", {
            title: "Select Playlist File",
            file_types: ["m3u8", "m3u", "csv", "txt", "json"]
          }).then(function (res) {
            var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
            if (!p) return;
            statusBar.textContent = "Importing playlist file...";
            window.FOSS.api("playlist_import_file", { file_path: p }).then(function (importRes) {
              if (importRes && importRes.tracks && importRes.tracks.length) {
                currentTracks = importRes.tracks;
                statusBar.textContent = "Loaded " + importRes.tracks.length + " tracks from file.";
                window.FOSS.toast.show({ message: "Loaded " + importRes.tracks.length + " tracks.", type: "success" });
              } else {
                showError("No tracks found in playlist file.");
              }
            }).catch(function (err) {
              var errMsg = (err && err.message) || String(err) || "Failed to import file.";
              showError(errMsg);
              window.FOSS.toast.show({ message: errMsg, type: "error" });
            });
          }).catch(function (err) {
            var errMsg = (err && err.message) || String(err) || "Failed to select file.";
            showError(errMsg);
            window.FOSS.toast.show({ message: errMsg, type: "error" });
          });
        } catch (err) {
          var errMsg = (err && err.message) || String(err) || "Failed to process file selection.";
          showError(errMsg);
          window.FOSS.toast.show({ message: errMsg, type: "error" });
        }
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Import Playlist File (M3U8, CSV)..." })]);

    var exportCsvDirectBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "playlist-export-csv-btn",
      type: "button",
      onClick: function () {
        try {
          if (!currentTracks.length) {
            showError("No tracks to export. Import a playlist first.");
            return;
          }
          window.FOSS.api("select_save_path", { title: "Save CSV Playlist", default_name: "playlist.csv" }).then(function (res) {
            var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
            if (!p) return;
            window.FOSS.api("playlist_export_csv", { tracks: currentTracks, output_path: p }).then(function (exportRes) {
              if (exportRes && exportRes.output_path) {
                statusBar.textContent = "CSV Playlist Exported: " + exportRes.output_path;
                window.FOSS.toast.show({ message: "CSV Playlist Exported", type: "success" });
              }
            }).catch(function (err) {
              window.FOSS.toast.show({ message: "Failed to export CSV: " + (err.message || String(err)), type: "error" });
            });
          }).catch(function (err) {
            window.FOSS.toast.show({ message: "Failed to select save path: " + (err.message || String(err)), type: "error" });
          });
        } catch (err) {
          window.FOSS.toast.show({ message: "Failed to process CSV export: " + (err.message || String(err)), type: "error" });
        }
      }
    }, [window.FOSS.icons.el("file-text", 16), window.FOSS.dom.el("span", { text: "Export CSV" })]);

    var fileCard = window.FOSS.dom.el("div", { className: "card card-compact" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold",
        text: "Import Local Playlist File"
      }),
      window.FOSS.dom.el("div", { className: "text-xs text-muted mb-2", text: "Open existing M3U, M3U8, or CSV playlist files." }),
      window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [chooseFileBtn, exportCsvDirectBtn])
    ]);

    var fetchCard = window.FOSS.dom.el("div", { className: "card card-compact" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold",
        text: "Fetch from URL (Spotify or YouTube Playlist)"
      }),
      urlInput,
      window.FOSS.dom.el("div", { className: "row mt-2" }, [fetchBtn])
    ]);

    // Group: Spotify Login
    var spotifyClientIdInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-spotify-client-id",
      "aria-label": "Spotify Client ID",
      title: "Spotify Client ID",
      placeholder: "Paste Spotify Client ID"
    });

    var spotifyCard = window.FOSS.dom.el("div", { className: "card card-compact" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold",
        text: "Spotify Account Setup (Optional)"
      }),
      window.FOSS.components.field("Spotify Client ID", spotifyClientIdInput),
      window.FOSS.dom.el("div", { className: "row gap-2 mt-2 flex-wrap" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-spotify-save-id-btn",
          type: "button",
          onClick: function () {
            try {
              var cid = spotifyClientIdInput.value.trim();
              window.FOSS.api("playlist_spotify_auth", { action: "save_client_id", client_id: cid }).then(function () {
                window.FOSS.toast.show({ message: "Spotify Client ID saved.", type: "success" });
              }).catch(function (err) {
                window.FOSS.toast.show({ message: "Failed to save Spotify Client ID: " + (err.message || String(err)), type: "error" });
              });
            } catch (err) {
              window.FOSS.toast.show({ message: "Failed to process Spotify Client ID: " + (err.message || String(err)), type: "error" });
            }
          }
        }, [window.FOSS.dom.el("span", { text: "Save Client ID" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-spotify-login-btn",
          type: "button",
          onClick: function () {
            try {
              window.FOSS.api("playlist_spotify_auth", { action: "login" }).then(function (res) {
                if (res && res.logged_in) {
                  window.FOSS.toast.show({ message: "Logged in with Spotify.", type: "success" });
                }
              }).catch(function (err) {
                window.FOSS.toast.show({ message: "Failed to login with Spotify: " + (err.message || String(err)), type: "error" });
              });
            } catch (err) {
              window.FOSS.toast.show({ message: "Failed to process Spotify login: " + (err.message || String(err)), type: "error" });
            }
          }
        }, [window.FOSS.dom.el("span", { text: "Log In with Spotify" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "playlist-spotify-instructions-btn",
          type: "button",
          onClick: function () {
            window.FOSS.toast.show({
              message: "1. Create app in Spotify Developer Dashboard. 2. Set Redirect URI to http://127.0.0.1:8888/callback. 3. Save Client ID.",
              type: "info"
            });
          }
        }, [window.FOSS.dom.el("span", { text: "Setup Guide" })])
      ])
    ]);

    // Group: YouTube Login
    var ytClientIdInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "playlist-yt-client-id",
      "aria-label": "Google OAuth Client ID",
      title: "Google OAuth Client ID",
      placeholder: "Google OAuth Client ID"
    });

    var ytClientSecretInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input",
      "data-testid": "playlist-yt-client-secret",
      "aria-label": "Google OAuth Client Secret",
      title: "Google OAuth Client Secret",
      placeholder: "Google OAuth Client Secret"
    });

    var ytCard = window.FOSS.dom.el("div", { className: "card card-compact" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold",
        text: "YouTube Account Setup (Optional for Playlist Creation)"
      }),
      window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-2" }, [
        window.FOSS.components.field("Client ID", ytClientIdInput),
        window.FOSS.components.field("Client Secret", ytClientSecretInput)
      ]),
      window.FOSS.dom.el("div", { className: "row gap-2 mt-2 flex-wrap" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-yt-save-btn",
          type: "button",
          onClick: function () {
            try {
              var cid = ytClientIdInput.value.trim();
              var sec = ytClientSecretInput.value.trim();
              window.FOSS.api("playlist_youtube_auth", { action: "save_credentials", client_id: cid, client_secret: sec }).then(function () {
                window.FOSS.toast.show({ message: "YouTube credentials saved.", type: "success" });
              }).catch(function (err) {
                window.FOSS.toast.show({ message: "Failed to save YouTube credentials: " + (err.message || String(err)), type: "error" });
              });
            } catch (err) {
              window.FOSS.toast.show({ message: "Failed to process YouTube credentials: " + (err.message || String(err)), type: "error" });
            }
          }
        }, [window.FOSS.dom.el("span", { text: "Save Credentials" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "playlist-yt-login-btn",
          type: "button",
          onClick: function () {
            try {
              window.FOSS.api("playlist_youtube_auth", { action: "login" }).then(function (res) {
                if (res && res.logged_in) {
                  window.FOSS.toast.show({ message: "Logged in with YouTube.", type: "success" });
                }
              }).catch(function (err) {
                window.FOSS.toast.show({ message: "Failed to login with YouTube: " + (err.message || String(err)), type: "error" });
              });
            } catch (err) {
              window.FOSS.toast.show({ message: "Failed to process YouTube login: " + (err.message || String(err)), type: "error" });
            }
          }
        }, [window.FOSS.dom.el("span", { text: "Log In with YouTube" })])
      ])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(window.FOSS.dom.el("div", { className: "flex-col gap-3" }, [
      fileCard,
      fetchCard,
      spotifyCard,
      ytCard
    ]));
  }

  function renderPaste(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-paste-status",
      text: "Paste track lines formatted as Artist - Song Title."
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
      className: "input",
      "data-testid": "playlist-direction-select",
      "aria-label": "Direction",
      title: "Direction",
      onChange: function () {
        currentDirection = directionSelect.value;
      }
    }, [
      window.FOSS.dom.el("option", { value: "spotify -> youtube / youtube music", text: "Spotify -> YouTube / YouTube Music" }),
      window.FOSS.dom.el("option", { value: "youtube -> spotify", text: "YouTube -> Spotify" })
    ]);
    directionSelect.value = currentDirection;

    var textarea = window.FOSS.dom.el("textarea", {
      className: "input font-mono text-sm",
      "data-testid": "playlist-paste-input",
      "aria-label": "Paste Tracklist Lines",
      title: "Paste Tracklist Lines",
      placeholder: "Queen - Bohemian Rhapsody\nThe Beatles - Hey Jude\nPink Floyd - Comfortably Numb",
      rows: 10,
      style: "width: 100%; min-height: 180px;"
    });

    var pasteGroup = window.FOSS.dom.el("div", { className: "card card-compact flex-col gap-3" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold",
        text: "Paste Tracklist Text (Artist - Title, Numbered Lists, CSV Lines)"
      }),
      window.FOSS.components.field("Conversion Direction", directionSelect),
      textarea,
      window.FOSS.dom.el("div", { className: "row gap-2" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-primary",
          "data-testid": "playlist-parse-btn",
          type: "button",
          onClick: function () {
            try {
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
                  window.FOSS.toast.show({ message: res.error.message || "Failed to parse tracklist.", type: "error" });
                }
              }).catch(function (err) {
                showError((err && err.message) || "Parse request failed.");
                window.FOSS.toast.show({ message: (err && err.message) || "Parse request failed.", type: "error" });
              });
            } catch (err) {
              showError((err && err.message) || "Parse request failed.");
              window.FOSS.toast.show({ message: (err && err.message) || "Parse request failed.", type: "error" });
            }
          }
        }, [
          window.FOSS.icons.el("file-text", 16),
          window.FOSS.dom.el("span", { text: "Parse Tracks" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost",
          "data-testid": "playlist-paste-clear-btn",
          type: "button",
          onClick: function () {
            textarea.value = "";
            clearError();
            statusBar.textContent = "Cleared tracklist text.";
          }
        }, [window.FOSS.dom.el("span", { text: "Clear" })])
      ])
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(pasteGroup);
  }

  function renderOutput(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "playlist-output-status",
      text: "Loaded Tracks: " + currentTracks.length
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

    var exportCsvBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "playlist-export-csv-btn",
      type: "button",
      onClick: function () {
        try {
          if (!currentTracks.length) return;
          window.FOSS.api("select_save_path", { title: "Save CSV Playlist", default_name: "playlist.csv" }).then(function (res) {
            var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
            if (!p) return;
            window.FOSS.api("playlist_export_csv", { tracks: currentTracks, output_path: p }).then(function (exportRes) {
              if (exportRes && exportRes.output_path) {
                showResult(exportRes.output_path, "CSV Playlist Exported");
              }
            }).catch(function (err) {
              window.FOSS.toast.show({ message: "Failed to export CSV: " + (err.message || String(err)), type: "error" });
            });
          }).catch(function (err) {
            window.FOSS.toast.show({ message: "Failed to select save path: " + (err.message || String(err)), type: "error" });
          });
        } catch (err) {
          window.FOSS.toast.show({ message: "Failed to process CSV export: " + (err.message || String(err)), type: "error" });
        }
      }
    }, [window.FOSS.icons.el("file-text", 14), window.FOSS.dom.el("span", { text: "Export CSV" })]);

    var exportM3u8Btn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "playlist-export-m3u8-btn",
      type: "button",
      onClick: function () {
        try {
          if (!currentTracks.length) return;
          window.FOSS.api("select_save_path", { title: "Save M3U8 Playlist", default_name: "playlist.m3u8" }).then(function (res) {
            var p = (res && res.path) || (res && res.paths && res.paths[0]) || "";
            if (!p) return;
            window.FOSS.api("playlist_export_m3u8", { tracks: currentTracks, output_path: p }).then(function (exportRes) {
              if (exportRes && exportRes.output_path) {
                showResult(exportRes.output_path, "M3U8 Playlist Exported");
              }
            }).catch(function (err) {
              window.FOSS.toast.show({ message: "Failed to export M3U8: " + (err.message || String(err)), type: "error" });
            });
          }).catch(function (err) {
            window.FOSS.toast.show({ message: "Failed to select save path: " + (err.message || String(err)), type: "error" });
          });
        } catch (err) {
          window.FOSS.toast.show({ message: "Failed to process M3U8 export: " + (err.message || String(err)), type: "error" });
        }
      }
    }, [window.FOSS.icons.el("music", 14), window.FOSS.dom.el("span", { text: "Export M3U8" })]);

    var copyLinksBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "playlist-copy-links-btn",
      type: "button",
      onClick: function () {
        try {
          if (!currentTracks.length) return;
          var links = currentTracks.map(function (t) {
            return (t.artist || "") + " - " + (t.title || "") + ": " + (t.spotify_url || t.youtube_url || "");
          }).join("\n");
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(links).then(function () {
              window.FOSS.toast.show({ message: "Copied track links to clipboard.", type: "success" });
            }).catch(function (err) {
              window.FOSS.toast.show({ message: "Failed to copy links: " + (err.message || String(err)), type: "error" });
            });
          }
        } catch (err) {
          window.FOSS.toast.show({ message: "Failed to process copying links: " + (err.message || String(err)), type: "error" });
        }
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Links" })]);

    var buildYtBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "playlist-yt-build-btn",
      type: "button",
      onClick: function () {
        try {
          if (!currentTracks.length) {
            window.FOSS.toast.show({ message: "No tracks to export.", type: "error" });
            return;
          }
          var playlistName = prompt("Enter YouTube Playlist Title:", "Imported Playlist");
          if (!playlistName) return;
          statusBar.textContent = "Creating YouTube playlist: " + playlistName + "...";
          window.FOSS.job("playlist_youtube_build", {
            playlist_title: playlistName,
            tracks: currentTracks
          }).then(function (res) {
            if (res && res.playlist_url) {
              statusBar.textContent = "Created YouTube playlist (" + (res.added_count || currentTracks.length) + " tracks).";
              window.FOSS.toast.show({ message: "Playlist created on YouTube!", type: "success" });
            }
          }).catch(function (err) {
            var errMsg = (err && err.message) || String(err) || "Failed to create YouTube playlist.";
            statusBar.textContent = "Error: " + errMsg;
            window.FOSS.toast.show({ message: errMsg, type: "error" });
          });
        } catch (err) {
          var errMsg = (err && err.message) || String(err) || "Failed to create YouTube playlist.";
          statusBar.textContent = "Error: " + errMsg;
          window.FOSS.toast.show({ message: errMsg, type: "error" });
        }
      }
    }, [window.FOSS.icons.el("play", 14), window.FOSS.dom.el("span", { text: "Create YouTube Playlist..." })]);

    var exportToolbar = window.FOSS.dom.el("div", {
      className: "row gap-2 items-center justify-between flex-wrap card card-compact",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Export & Sync" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        exportCsvBtn,
        exportM3u8Btn,
        copyLinksBtn,
        buildYtBtn
      ])
    ]);

    var contentHost = window.FOSS.dom.el("div", { className: "card card-compact", "data-testid": "playlist-tracks-card" });

    if (!currentTracks || currentTracks.length === 0) {
      contentHost.appendChild(window.FOSS.dom.el("div", {
        className: "p-4 text-center text-muted font-mono text-sm",
        "data-testid": "playlist-empty-state",
        text: "No tracks loaded yet. Fetch a URL or paste text."
      }));
    } else {
      var table = window.FOSS.dom.el("table", { className: "table w-full text-sm", "data-testid": "playlist-tracks-table" });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 2.5rem;", text: "#" }),
          window.FOSS.dom.el("th", { text: "Title" }),
          window.FOSS.dom.el("th", { text: "Artist" }),
          window.FOSS.dom.el("th", { text: "Album" }),
          window.FOSS.dom.el("th", { text: "Duration" }),
          window.FOSS.dom.el("th", { style: "width: 12rem;", text: "Search Links" })
        ])
      ]);
      var tbody = window.FOSS.dom.el("tbody", {});

      currentTracks.forEach(function (t, idx) {
        var query = encodeURIComponent((t.artist || "") + " " + (t.title || ""));
        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "font-mono text-muted text-xs", text: String(idx + 1) }),
          window.FOSS.dom.el("td", { className: "font-semibold", text: t.title || "Unknown" }),
          window.FOSS.dom.el("td", { text: t.artist || "Unknown" }),
          window.FOSS.dom.el("td", { className: "text-muted", text: t.album || "" }),
          window.FOSS.dom.el("td", { className: "font-mono text-xs text-muted", text: formatDuration(t.duration_ms) }),
          window.FOSS.dom.el("td", {}, [
            window.FOSS.dom.el("div", { className: "row gap-1" }, [
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-sm",
                type: "button",
                text: "Spotify",
                title: "Search on Spotify",
                onClick: function () {
                  try {
                    window.FOSS.api("open_url", { url: "https://open.spotify.com/search/" + query }).catch(function (err) {
                      window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                    });
                  } catch (err) {
                    window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                  }
                }
              }),
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-sm",
                type: "button",
                text: "YT",
                title: "Search on YouTube",
                onClick: function () {
                  try {
                    window.FOSS.api("open_url", { url: "https://www.youtube.com/results?search_query=" + query }).catch(function (err) {
                      window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                    });
                  } catch (err) {
                    window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                  }
                }
              }),
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-sm",
                type: "button",
                text: "YTM",
                title: "Search on YouTube Music",
                onClick: function () {
                  try {
                    window.FOSS.api("open_url", { url: "https://music.youtube.com/search?q=" + query }).catch(function (err) {
                      window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                    });
                  } catch (err) {
                    window.FOSS.toast.show({ message: "Failed to open URL: " + (err.message || String(err)), type: "error" });
                  }
                }
              })
            ])
          ])
        ]);
        tbody.appendChild(tr);
      });

      table.appendChild(thead);
      table.appendChild(tbody);
      var tableWrap = window.FOSS.dom.el("div", { className: "table-wrap scroll-x", style: "width: 100%; overflow-x: auto;" }, [table]);
      contentHost.appendChild(tableWrap);
    }

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultCardHost);
    panel.appendChild(window.FOSS.dom.el("div", { className: "flex-col gap-3" }, [
      exportToolbar,
      contentHost
    ]));
  }

  window.FOSS.router.register({
    id: "playlist",
    title: "Playlist Porter",
    navName: "Playlist Porter",
    category: "Media",
    icon: "music",
    tabs: [
      { id: "import", label: "Import / Fetch", aliases: ["fetch"], render: renderFetch },
      { id: "paste", label: "Paste Text", render: renderPaste },
      { id: "output", label: "Tracklist & Output", render: renderOutput }
    ]
  });
})();
