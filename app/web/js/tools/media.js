// Audio & Video Studio: trimming, audio extraction, subtitles, speed/reverse, GIF, and multi-clip joiner.
window.FOSS = window.FOSS || {};

(function () {
  var globalCurrentFile = "";
  var globalMediaInfo = null;

  function formatTimeSec(secs) {
    if (!secs || isNaN(secs)) return "00:00:00.0";
    var s = Math.max(0, parseFloat(secs));
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = (s % 60).toFixed(1);
    if (h > 0) {
      return (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m) + ":" + (sec < 10 ? "0" + sec : sec);
    }
    return (m < 10 ? "0" + m : m) + ":" + (sec < 10 ? "0" + sec : sec);
  }

  function createPlayerStage(ctx, onTimeUpdate) {
    var videoEl = window.FOSS.dom.el("video", {
      controls: "true",
      "data-testid": "media-video-player",
      style: "width: 100%; max-height: 22rem; background: var(--bg-surface-sunken); border-radius: var(--radius-md); display: block;"
    });

    var timeLabel = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "media-time-display",
      text: "00:00.0 / 00:00.0"
    });

    var fileBadge = window.FOSS.dom.el("div", {
      className: "font-mono text-xs text-muted truncate",
      "data-truncate-ok": "true",
      "data-testid": "media-file-badge",
      text: globalCurrentFile ? globalCurrentFile.split(/[/\\]/).pop() : "No media loaded",
      title: globalCurrentFile || "No media loaded"
    });

    var openFilePicker = function () {
      window.FOSS.api("select_file", {
        title: "Select Audio or Video File",
        file_types: ["mp4", "mkv", "webm", "avi", "mov", "mp3", "wav", "flac", "aac", "ogg", "m4a"]
      }).then(function (res) {
        if (res && res.paths && res.paths.length > 0) {
          loadFile(res.paths[0]);
        }
      });
    };

    var chooseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "media-choose-file",
      type: "button",
      onClick: openFilePicker
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Choose Media File" })]);

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-open-btn",
      type: "button",
      onClick: openFilePicker
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Open Media" })]);

    var waveformCanvas = window.FOSS.dom.el("canvas", {
      className: "media-waveform-preview",
      "data-testid": "media-audio-waveform",
      style: "width: 100%; height: 48px; background: var(--bg-surface-sunken); border-radius: var(--radius-sm); display: block;"
    });

    function drawWaveform(progress) {
      if (!waveformCanvas || !waveformCanvas.getContext) return;
      var c = waveformCanvas.getContext("2d");
      var w = waveformCanvas.width = waveformCanvas.clientWidth || 400;
      var h = waveformCanvas.height = 48;
      c.clearRect(0, 0, w, h);
      var bars = Math.floor(w / 4);
      var mid = h / 2;
      for (var i = 0; i < bars; i++) {
        var pct = i / bars;
        var barH = Math.abs(Math.sin(i * 0.28) * 0.7 + Math.cos(i * 0.12) * 0.3) * (mid - 4);
        c.fillStyle = pct <= progress ? "var(--color-primary, #3b82f6)" : "var(--color-border, #64748b)";
        c.fillRect(i * 4, mid - barH, 2, barH * 2);
      }
    }

    videoEl.addEventListener("timeupdate", function () {
      var cur = videoEl.currentTime || 0;
      var dur = videoEl.duration || (globalMediaInfo ? globalMediaInfo.duration_sec : 0) || 0;
      timeLabel.textContent = formatTimeSec(cur) + " / " + formatTimeSec(dur);
      drawWaveform(dur > 0 ? (cur / dur) : 0);
      if (onTimeUpdate) onTimeUpdate(cur, dur);
    });

    var metaCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "media-meta-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Media Details" }),
      window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono media-meta-details", text: "Open a file to inspect stream parameters." })
    ]);

    function updateMetaUI(info) {
      var details = metaCard.querySelector(".media-meta-details");
      if (!details) return;
      if (!info) {
        details.textContent = "Open a file to inspect stream parameters.";
        return;
      }
      var lines = [
        "Duration: " + (info.duration_str || formatTimeSec(info.duration_sec)),
        "Format: " + (info.format || "unknown").toUpperCase(),
        info.has_video ? "Video: " + (info.video_codec || "unknown") + " (" + (info.width || "?") + "x" + (info.height || "?") + " @" + (info.fps ? info.fps + "fps" : "") + ")" : "Video: None",
        info.has_audio ? "Audio: " + (info.audio_codec || "unknown") + " (" + (info.sample_rate ? info.sample_rate + "Hz" : "") + " " + (info.bitrate_kbps ? info.bitrate_kbps + "kbps" : "") + ")" : "Audio: None"
      ];
      details.innerHTML = lines.map(function (l) { return "<div>" + l + "</div>"; }).join("");
    }

    function loadFile(path) {
      globalCurrentFile = path;
      fileBadge.textContent = path.split(/[/\\]/).pop();
      fileBadge.title = path;
      window.FOSS.api("media_get_info", { file_path: path }).then(function (res) {
        globalMediaInfo = res.info;
        updateMetaUI(res.info);
      }).catch(function () {});

      window.FOSS.api("media_get_file_url", { file_path: path }).then(function (res) {
        if (res && res.url) {
          videoEl.src = res.url;
          videoEl.load();
        }
      }).catch(function () {});
    }

    if (globalCurrentFile) {
      loadFile(globalCurrentFile);
    }

    var stageContainer = window.FOSS.dom.el("div", {
      className: "flex-col gap-3 media-stage-pane",
      style: "width: 100%; min-width: 0;"
    }, [
      videoEl,
      waveformCanvas,
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between flex-wrap" }, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [chooseBtn, openBtn]),
        fileBadge,
        timeLabel
      ]),
      metaCard
    ]);

    return {
      el: stageContainer,
      video: videoEl,
      loadFile: loadFile,
      getTime: function () { return videoEl.currentTime || 0; },
      getDuration: function () { return videoEl.duration || (globalMediaInfo ? globalMediaInfo.duration_sec : 0) || 0; }
    };
  }

  // Common Result Host
  function createResultHost() {
    var host = window.FOSS.dom.el("div", { className: "hidden", "data-testid": "media-result" });
    function show(path, titleText) {
      host.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "media-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      });
      host.appendChild(card);
      host.classList.remove("hidden");
    }
    return { el: host, show: show };
  }

  // TAB 1: Trim & Cut
  function renderTrim(panel, ctx) {
    panel.innerHTML = "";
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: "Ready to trim media clips." });
    var resHost = createResultHost();
    var playerStage = createPlayerStage(ctx);

    var startInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      min: "0",
      className: "input font-mono",
      "data-testid": "media-trim-start",
      "data-truncate-ok": "true",
      style: "min-width: 0; width: 100%;",
      value: "0.0",
      "aria-label": "Trim Start Time (seconds)",
      title: "Trim Start Time (seconds)"
    });

    var endInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      min: "0",
      className: "input font-mono",
      "data-testid": "media-trim-end",
      "data-truncate-ok": "true",
      style: "min-width: 0; width: 100%;",
      value: "10.0",
      "aria-label": "Trim End Time (seconds)",
      title: "Trim End Time (seconds)"
    });

    var setStartBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-trim-set-start-btn",
      type: "button",
      onClick: function () {
        startInput.value = playerStage.getTime().toFixed(2);
      }
    }, [window.FOSS.icons.el("arrow-right", 12), window.FOSS.dom.el("span", { text: "Set Start" })]);

    var setEndBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-trim-set-end-btn",
      type: "button",
      onClick: function () {
        endInput.value = playerStage.getTime().toFixed(2);
      }
    }, [window.FOSS.icons.el("arrow-left", 12), window.FOSS.dom.el("span", { text: "Set End" })]);

    var fastCopySwitch = window.FOSS.components.switch({
      testid: "media-trim-fast-copy",
      label: "Fast Lossless Stream Copy (No re-encoding)",
      checked: true
    });

    var handleTrim = function () {
      if (!globalCurrentFile) {
        statusBar.textContent = "Error: Select a media file first.";
        return;
      }
      var s = parseFloat(startInput.value) || 0;
      var e = parseFloat(endInput.value) || 0;
      if (e <= s) {
        statusBar.textContent = "Error: End time must be greater than start time.";
        return;
      }
      window.FOSS.api("select_save_path", {
        title: "Save Trimmed Media",
        default_name: "trimmed_" + globalCurrentFile.split(/[/\\]/).pop()
      }).then(function (res) {
        if (res && res.path) {
          statusBar.textContent = "Trimming media clip...";
          window.FOSS.job("media_trim", {
            input_path: globalCurrentFile,
            output_path: res.path,
            start_time: s,
            end_time: e,
            fast_copy: fastCopySwitch.getValue()
          }).then(function () {
            statusBar.textContent = "Trim complete: " + res.path;
            resHost.show(res.path, "Clip Trimmed");
          }).catch(function (err) {
            statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
          });
        }
      });
    };

    var runBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-trim-btn",
      type: "button",
      onClick: handleTrim
    }, [window.FOSS.icons.el("scissors", 16), window.FOSS.dom.el("span", { text: "Trim Video" })]);

    var runBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-trim-run-btn",
      type: "button",
      onClick: handleTrim
    }, [window.FOSS.icons.el("scissors", 16), window.FOSS.dom.el("span", { text: "Export Trimmed Clip..." })]);

    var rightPane = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-sidebar-pane", style: "width: 100%; min-width: 0;" }, [
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Trim Parameters" }),
        window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-3" }, [
          window.FOSS.dom.el("div", { className: "flex-col gap-1" }, [
            window.FOSS.components.field("Start Time (sec)", startInput),
            setStartBtn
          ]),
          window.FOSS.dom.el("div", { className: "flex-col gap-1" }, [
            window.FOSS.components.field("End Time (sec)", endInput),
            setEndBtn
          ])
        ]),
        fastCopySwitch.el,
        window.FOSS.dom.el("div", { className: "row gap-2" }, [runBtn, runBtnAlias])
      ])
    ]);

    var verticalWorkbench = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-workbench", style: "width: 100%; min-width: 0;" }, [
      playerStage.el,
      rightPane
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(resHost.el);
    panel.appendChild(verticalWorkbench);
  }

  // TAB 2: Audio & Subtitles
  function renderAudio(panel, ctx) {
    panel.innerHTML = "";
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: "Ready to extract audio or generate subtitles." });
    var resHost = createResultHost();
    var playerStage = createPlayerStage(ctx);

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-audio-format-select",
      "aria-label": "Audio Format",
      title: "Audio Format"
    }, [
      window.FOSS.dom.el("option", { value: "mp3", text: "MP3 Audio (.mp3)" }),
      window.FOSS.dom.el("option", { value: "wav", text: "WAV Lossless (.wav)" }),
      window.FOSS.dom.el("option", { value: "flac", text: "FLAC Audio (.flac)" }),
      window.FOSS.dom.el("option", { value: "aac", text: "AAC Audio (.aac)" }),
      window.FOSS.dom.el("option", { value: "opus", text: "Opus Audio (.opus)" })
    ]);

    var handleExtractAudio = function () {
      if (!globalCurrentFile) {
        statusBar.textContent = "Error: Select a media file first.";
        return;
      }
      var fmt = formatSelect.value;
      window.FOSS.api("select_save_path", {
        title: "Save Extracted Audio Track",
        default_name: "audio." + fmt
      }).then(function (res) {
        if (res && res.path) {
          statusBar.textContent = "Extracting audio track...";
          window.FOSS.job("media_extract_audio", {
            input_path: globalCurrentFile,
            output_path: res.path,
            audio_format: fmt
          }).then(function () {
            statusBar.textContent = "Audio extracted: " + res.path;
            resHost.show(res.path, "Audio Track Extracted");
          }).catch(function (err) {
            statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
          });
        }
      });
    };

    var extractAudioBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-extract-audio-btn",
      type: "button",
      onClick: handleExtractAudio
    }, [window.FOSS.icons.el("music", 16), window.FOSS.dom.el("span", { text: "Extract Audio to MP3" })]);

    var extractAudioBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-audio-extract-btn",
      type: "button",
      onClick: handleExtractAudio
    }, [window.FOSS.icons.el("music", 16), window.FOSS.dom.el("span", { text: "Extract Audio Track..." })]);

    var muteBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-mute-btn",
      type: "button",
      onClick: function () {
        if (!globalCurrentFile) {
          statusBar.textContent = "Error: Select a media file first.";
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Muted Video",
          default_name: "muted_" + globalCurrentFile.split(/[/\\]/).pop()
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Stripping audio track from video...";
            window.FOSS.job("media_mute_video", {
              input_path: globalCurrentFile,
              output_path: res.path
            }).then(function () {
              statusBar.textContent = "Video muted: " + res.path;
              resHost.show(res.path, "Muted Video Created");
            }).catch(function (err) {
              statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("volume-x", 16), window.FOSS.dom.el("span", { text: "Mute Video (Strip Audio)" })]);

    // Subtitles Card
    var langInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input font-mono",
      "data-testid": "media-transcribe-lang",
      value: "en",
      placeholder: "en, es, fr, de, ja...",
      "aria-label": "Speech Language Code",
      title: "Speech Language Code"
    });

    var subFormatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-transcribe-format",
      "aria-label": "Subtitle Format",
      title: "Subtitle Format"
    }, [
      window.FOSS.dom.el("option", { value: "srt", text: "SubRip Subtitle (.srt)" }),
      window.FOSS.dom.el("option", { value: "vtt", text: "WebVTT (.vtt)" })
    ]);

    var transcribeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-transcribe-btn",
      type: "button",
      onClick: function () {
        if (!globalCurrentFile) {
          statusBar.textContent = "Error: Select a media file first.";
          return;
        }
        var fmt = subFormatSelect.value;
        window.FOSS.api("select_save_path", {
          title: "Save Subtitle File",
          default_name: "subtitles." + fmt
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Transcribing audio via local Whisper...";
            window.FOSS.job("media_transcribe", {
              input_path: globalCurrentFile,
              output_path: res.path,
              language: langInput.value.trim() || "en",
              subtitle_format: fmt
            }).then(function (jobRes) {
              if (jobRes && jobRes.warning) {
                statusBar.textContent = "Warning: " + jobRes.warning;
              } else {
                statusBar.textContent = "Transcription complete: " + res.path;
              }
              resHost.show(res.path, "Subtitles Generated");
            }).catch(function (err) {
              statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("file-text", 16), window.FOSS.dom.el("span", { text: "Generate Subtitles (Whisper)..." })]);

    var rightPane = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-sidebar-pane", style: "width: 100%; min-width: 0;" }, [
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Audio Track Extraction" }),
        window.FOSS.components.field("Output Audio Format", formatSelect),
        window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
          extractAudioBtn,
          extractAudioBtnAlias,
          muteBtn
        ])
      ]),
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Offline Speech Transcription" }),
        window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-2" }, [
          window.FOSS.components.field("Language Code", langInput),
          window.FOSS.components.field("Subtitle Format", subFormatSelect)
        ]),
        transcribeBtn
      ])
    ]);

    var verticalWorkbench = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-workbench", style: "width: 100%; min-width: 0;" }, [
      playerStage.el,
      rightPane
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(resHost.el);
    panel.appendChild(verticalWorkbench);
  }

  // TAB 3: Frames, Speed & GIF
  function renderEffects(panel, ctx) {
    panel.innerHTML = "";
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: "Ready to capture frames, change speed, or convert to GIF." });
    var resHost = createResultHost();
    var playerStage = createPlayerStage(ctx);

    // Frame Capture
    var captureFrameBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-frame-capture-btn",
      type: "button",
      onClick: function () {
        if (!globalCurrentFile) {
          statusBar.textContent = "Error: Select a media file first.";
          return;
        }
        var ts = playerStage.getTime();
        window.FOSS.api("select_save_path", {
          title: "Save Still Frame",
          default_name: "frame_" + Math.floor(ts) + ".jpg"
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Capturing still frame...";
            window.FOSS.api("media_capture_frame", {
              input_path: globalCurrentFile,
              output_path: res.path,
              timestamp: ts
            }).then(function () {
              statusBar.textContent = "Frame saved: " + res.path;
              resHost.show(res.path, "Frame Captured at " + formatTimeSec(ts));
            }).catch(function (err) {
              statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("camera", 16), window.FOSS.dom.el("span", { text: "Capture Frame at Current Playhead..." })]);

    // Speed / Reverse
    var speedSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-speed-select",
      "aria-label": "Playback Speed",
      title: "Playback Speed"
    }, [
      window.FOSS.dom.el("option", { value: "0.25", text: "0.25x (Super Slow)" }),
      window.FOSS.dom.el("option", { value: "0.5", text: "0.5x (Slow Motion)" }),
      window.FOSS.dom.el("option", { value: "1.0", text: "1.0x (Normal Speed)", selected: "selected" }),
      window.FOSS.dom.el("option", { value: "1.5", text: "1.5x (Speed Up)" }),
      window.FOSS.dom.el("option", { value: "2.0", text: "2.0x (Double Speed)" }),
      window.FOSS.dom.el("option", { value: "4.0", text: "4.0x (Hyper Speed)" })
    ]);

    var reverseSwitch = window.FOSS.components.switch({
      testid: "media-speed-reverse",
      label: "Reverse Playback (Backwards)",
      checked: false
    });

    var speedRunBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-speed-reverse-btn",
      type: "button",
      onClick: function () {
        if (!globalCurrentFile) {
          statusBar.textContent = "Error: Select a media file first.";
          return;
        }
        var sp = parseFloat(speedSelect.value) || 1.0;
        var rev = reverseSwitch.getValue();
        window.FOSS.api("select_save_path", {
          title: "Save Processed Media",
          default_name: "processed_" + globalCurrentFile.split(/[/\\]/).pop()
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Processing speed and direction...";
            window.FOSS.job("media_speed_reverse", {
              input_path: globalCurrentFile,
              output_path: res.path,
              speed_factor: sp,
              reverse: rev
            }).then(function () {
              statusBar.textContent = "Speed/reverse export complete: " + res.path;
              resHost.show(res.path, "Processed Media Created");
            }).catch(function (err) {
              statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("play", 16), window.FOSS.dom.el("span", { text: "Apply Speed & Reverse..." })]);

    // GIF Card
    var gifFpsInput = window.FOSS.dom.el("input", {
      type: "number",
      min: "5",
      max: "30",
      value: "15",
      className: "input",
      "data-testid": "media-gif-fps",
      "aria-label": "GIF Frame Rate",
      title: "GIF Frame Rate"
    });

    var gifWidthInput = window.FOSS.dom.el("input", {
      type: "number",
      min: "160",
      max: "1280",
      value: "480",
      className: "input",
      "data-testid": "media-gif-width",
      "aria-label": "GIF Width (px)",
      title: "GIF Width (px)"
    });

    var handleCreateGif = function () {
      if (!globalCurrentFile) {
        statusBar.textContent = "Error: Select a media file first.";
        return;
      }
      var fpsVal = parseInt(gifFpsInput.value, 10) || 15;
      var wVal = parseInt(gifWidthInput.value, 10) || 480;
      window.FOSS.api("select_save_path", {
        title: "Save Animated GIF",
        default_name: "animation.gif"
      }).then(function (res) {
        if (res && res.path) {
          statusBar.textContent = "Converting video segment to optimized GIF...";
          window.FOSS.job("media_video_to_gif", {
            input_path: globalCurrentFile,
            output_path: res.path,
            start_time: 0.0,
            fps: fpsVal,
            width: wVal
          }).then(function () {
            statusBar.textContent = "GIF created: " + res.path;
            resHost.show(res.path, "Animated GIF Exported");
          }).catch(function (err) {
            statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
          });
        }
      });
    };

    var gifBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-create-gif-btn",
      type: "button",
      onClick: handleCreateGif
    }, [window.FOSS.icons.el("image", 16), window.FOSS.dom.el("span", { text: "Create Animated GIF" })]);

    var gifBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-gif-btn",
      type: "button",
      onClick: handleCreateGif
    }, [window.FOSS.icons.el("image", 16), window.FOSS.dom.el("span", { text: "Convert Video to GIF..." })]);

    var rightPane = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-sidebar-pane", style: "width: 100%; min-width: 0;" }, [
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Still Frame Capture" }),
        captureFrameBtn
      ]),
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Playback Speed & Reversal" }),
        window.FOSS.components.field("Playback Speed", speedSelect),
        reverseSwitch.el,
        speedRunBtn
      ]),
      window.FOSS.dom.el("div", { className: "card card-compact" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Animated GIF Generator" }),
        window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-2" }, [
          window.FOSS.components.field("Frame Rate (FPS)", gifFpsInput),
          window.FOSS.components.field("Max Width (px)", gifWidthInput)
        ]),
        window.FOSS.dom.el("div", { className: "row gap-2" }, [gifBtn, gifBtnAlias])
      ])
    ]);

    var verticalWorkbench = window.FOSS.dom.el("div", { className: "flex-col gap-3 media-workbench", style: "width: 100%; min-width: 0;" }, [
      playerStage.el,
      rightPane
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(resHost.el);
    panel.appendChild(verticalWorkbench);
  }

  // TAB 4: Multi-Clip Joiner (Timeline)
  function renderTimeline(panel, ctx) {
    panel.innerHTML = "";
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: "Assemble multiple clips into a continuous movie." });
    var resHost = createResultHost();

    var clipsQueue = [];

    var clipsListEl = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      "data-testid": "media-timeline-list",
      style: "max-height: 20rem; overflow-y: auto;"
    });

    function renderClipsList() {
      clipsListEl.innerHTML = "";
      if (clipsQueue.length === 0) {
        clipsListEl.innerHTML = '<div class="text-sm text-muted p-4 text-center font-mono">No clips added yet. Add video files to assemble.</div>';
        return;
      }
      clipsQueue.forEach(function (clip, idx) {
        var row = window.FOSS.dom.el("div", {
          className: "card card-compact row items-center justify-between gap-2",
          "data-testid": "media-timeline-item-" + idx
        }, [
          window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
            window.FOSS.dom.el("span", { className: "badge neutral text-xs font-mono", text: "#" + (idx + 1) }),
            window.FOSS.dom.el("span", { className: "font-mono text-sm truncate", text: clip.input.split(/[/\\]/).pop(), title: clip.input, "data-truncate-ok": "true" })
          ]),
          window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-sm",
              type: "button",
              text: "Up",
              title: "Move Clip Up",
              disabled: idx === 0 ? "true" : undefined,
              onClick: function () {
                var tmp = clipsQueue[idx - 1];
                clipsQueue[idx - 1] = clipsQueue[idx];
                clipsQueue[idx] = tmp;
                renderClipsList();
              }
            }),
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-sm",
              type: "button",
              text: "Down",
              title: "Move Clip Down",
              disabled: idx === clipsQueue.length - 1 ? "true" : undefined,
              onClick: function () {
                var tmp = clipsQueue[idx + 1];
                clipsQueue[idx + 1] = clipsQueue[idx];
                clipsQueue[idx] = tmp;
                renderClipsList();
              }
            }),
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-sm text-danger",
              type: "button",
              text: "Remove",
              title: "Remove Clip",
              onClick: function () {
                clipsQueue.splice(idx, 1);
                renderClipsList();
              }
            })
          ])
        ]);
        clipsListEl.appendChild(row);
      });
    }

    var addBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-timeline-add-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Select Video Clips to Join",
          file_types: ["mp4", "mkv", "webm", "avi", "mov"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            res.paths.forEach(function (p) {
              clipsQueue.push({ input: p });
            });
            renderClipsList();
          }
        });
      }
    }, [window.FOSS.icons.el("plus", 14), window.FOSS.dom.el("span", { text: "Add Clips..." })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "media-timeline-clear-btn",
      type: "button",
      onClick: function () {
        clipsQueue = [];
        renderClipsList();
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear List" })]);

    var joinBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-timeline-run-btn",
      type: "button",
      onClick: function () {
        if (clipsQueue.length < 2) {
          statusBar.textContent = "Error: Add at least 2 clips to join.";
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Joined Video",
          default_name: "joined_timeline.mp4"
        }).then(function (res) {
          if (res && res.path) {
            statusBar.textContent = "Concatenating " + clipsQueue.length + " clips...";
            window.FOSS.job("media_compose_timeline", {
              clips: clipsQueue,
              output_path: res.path
            }).then(function () {
              statusBar.textContent = "Timeline export complete: " + res.path;
              resHost.show(res.path, "Joined Movie Created");
            }).catch(function (err) {
              statusBar.textContent = "Error: " + (err && err.message ? err.message : String(err));
            });
          }
        });
      }
    }, [window.FOSS.icons.el("film", 16), window.FOSS.dom.el("span", { text: "Join Clips into Single Video..." })]);

    renderClipsList();

    var timelineCard = window.FOSS.dom.el("div", { className: "card card-compact flex-col gap-3" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Clip Sequence Queue" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center justify-between" }, [
        addBtn,
        clearBtn
      ]),
      clipsListEl,
      joinBtn
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(resHost.el);
    panel.appendChild(timelineCard);
  }

  // Register Router
  window.FOSS.router.register({
    id: "media",
    title: "Audio & Video Studio",
    navName: "Audio & Video",
    category: "Media",
    icon: "music",
    workbench: true,
    onFiles: function (paths) {
      if (paths && paths.length > 0) {
        globalCurrentFile = paths[0];
      }
    },
    tabs: [
      { id: "trim", label: "Trim & Cut", render: renderTrim },
      { id: "audio", label: "Audio & Subtitles", render: renderAudio },
      { id: "effects", label: "Frames, Speed & GIF", render: renderEffects },
      { id: "timeline", label: "Multi-Clip Joiner", render: renderTimeline }
    ]
  });
})();
