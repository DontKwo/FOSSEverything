// Audio & Video Studio: trimming, audio extraction, subtitles, speed/reverse, GIF, and multi-clip joiner.
window.FOSS = window.FOSS || {};

(function () {
  var TOOL_ID = "media";
  var state = { file: "", info: null, stage: null };

  var MEDIA_PICK_TYPES = ["mp4", "mkv", "webm", "avi", "mov", "mp3", "wav", "flac", "aac", "ogg", "m4a"];
  var AUDIO_EXTS = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus"];

  var TYPE_DEFS = {
    mp4: { name: "MP4 Video (*.mp4)", extensions: ["mp4"] },
    mp3: { name: "MP3 Audio (*.mp3)", extensions: ["mp3"] },
    wav: { name: "WAV Audio (*.wav)", extensions: ["wav"] },
    webm: { name: "WebM Video (*.webm)", extensions: ["webm"] },
    gif: { name: "Animated GIF (*.gif)", extensions: ["gif"] },
    flac: { name: "FLAC Audio (*.flac)", extensions: ["flac"] },
    aac: { name: "AAC Audio (*.aac)", extensions: ["aac"] },
    opus: { name: "Opus Audio (*.opus)", extensions: ["opus"] },
    srt: { name: "SubRip Subtitles (*.srt)", extensions: ["srt"] },
    vtt: { name: "WebVTT Subtitles (*.vtt)", extensions: ["vtt"] },
    txt: { name: "Text File (*.txt)", extensions: ["txt"] },
    jpg: { name: "JPEG Image (*.jpg)", extensions: ["jpg"] },
    png: { name: "PNG Image (*.png)", extensions: ["png"] }
  };

  function baseName(path) {
    return String(path || "").split(/[/\\]/).pop();
  }

  function extOf(path) {
    var name = baseName(path);
    var dot = name.lastIndexOf(".");
    return dot >= 0 ? name.substring(dot + 1).toLowerCase() : "";
  }

  function fileTypes(exts) {
    var seen = {};
    var out = [];
    exts.forEach(function (ext) {
      if (TYPE_DEFS[ext] && !seen[ext]) {
        seen[ext] = true;
        out.push(TYPE_DEFS[ext]);
      }
    });
    return out;
  }

  function isAudioOnly() {
    if (state.info) return !state.info.has_video;
    return AUDIO_EXTS.indexOf(extOf(state.file)) >= 0;
  }

  function sourceExportExts() {
    var own = extOf(state.file);
    var family = isAudioOnly() ? ["mp3", "wav"] : ["mp4", "webm", "mp3", "wav"];
    return [own].concat(family);
  }

  function formatTimeSec(secs) {
    if (!secs || isNaN(secs)) return "00:00.0";
    var s = Math.max(0, parseFloat(secs));
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = (s % 60).toFixed(1);
    var secText = parseFloat(sec) < 10 ? "0" + sec : sec;
    var minText = m < 10 ? "0" + m : String(m);
    if (h > 0) return (h < 10 ? "0" + h : h) + ":" + minText + ":" + secText;
    return minText + ":" + secText;
  }

  function errorText(res) {
    return res && res.error ? String(res.error) : "Unknown error";
  }

  function toastError(message) {
    if (window.FOSS.toast) window.FOSS.toast.show(message, "error");
  }

  function pickMediaFile() {
    return window.FOSS.api("select_file", {
      title: "Select Audio or Video File",
      file_types: MEDIA_PICK_TYPES
    }).then(function (res) {
      return res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
    });
  }

  function pickSavePath(title, exts) {
    return window.FOSS.api("select_save_path", {
      title: title,
      default_name: "media_export",
      file_types: fileTypes(exts)
    }).then(function (res) {
      return res && res.path ? res.path : "";
    });
  }

  function createResultHost() {
    var host = window.FOSS.dom.el("div", { className: "hidden", "data-testid": "media-result" });
    function show(path, titleText) {
      host.innerHTML = "";
      window.FOSS.dom.append(host, window.FOSS.components.resultCard({
        testid: "media-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      }));
      host.classList.remove("hidden");
    }
    return { el: host, show: show };
  }

  function accentColor(name, fallback) {
    var val = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return val || fallback;
  }

  function loadMedia(path, onReady) {
    state.file = path;
    state.info = null;
    window.FOSS.api("media_get_info", { file_path: path }, { silent: true }).then(function (res) {
      if (res && res.ok && res.info) {
        state.info = res.info;
      } else {
        toastError("Could not read media details: " + errorText(res));
      }
      if (onReady) onReady();
    });
  }

  function createPlayerStage(goToTab) {
    var D = window.FOSS.dom;
    var listeners = [];

    var videoEl = D.el("video", {
      controls: "true",
      preload: "metadata",
      className: "media-video hidden",
      "data-testid": "media-video-player"
    });

    var waveformCanvas = D.el("canvas", {
      className: "media-waveform-preview hidden",
      "data-testid": "media-audio-waveform"
    });

    var timeLabel = D.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "media-time-display",
      text: "00:00.0 / 00:00.0"
    });

    var fileBadge = D.el("div", {
      className: "font-mono text-xs text-muted truncate media-file-badge",
      "data-truncate-ok": "true",
      "data-testid": "media-file-badge",
      text: "No media loaded",
      title: "No media loaded"
    });

    function onPicked(path, targetTab) {
      if (!path) return;
      loadFile(path, targetTab);
    }

    function openPicker(targetTab) {
      pickMediaFile().then(function (path) { onPicked(path, targetTab); });
    }

    var chooseBtn = D.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "media-choose-file",
      type: "button",
      onClick: function () { openPicker(""); }
    }, [window.FOSS.icons.el("folder", 14), D.el("span", { text: "Choose Media File" })]);

    var openBtn = D.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-open-btn",
      type: "button",
      onClick: function () { openPicker(""); }
    }, [window.FOSS.icons.el("folder", 14), D.el("span", { text: "Open Media" })]);

    function actionCard(testid, iconName, title, desc, tabId) {
      return D.el("div", {
        className: "media-action-card",
        role: "button",
        tabindex: "0",
        "data-testid": testid,
        onClick: function () { openPicker(tabId); },
        onKeydown: function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPicker(tabId);
          }
        }
      }, [
        window.FOSS.icons.el(iconName, 20),
        D.el("span", { className: "media-action-title", text: title }),
        D.el("span", { className: "media-action-desc text-xs text-muted", text: desc })
      ]);
    }

    var dropzone = D.el("div", {
      className: "media-dropzone",
      role: "button",
      tabindex: "0",
      "data-testid": "media-dropzone",
      onClick: function () { openPicker(""); },
      onKeydown: function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openPicker("");
        }
      }
    }, [
      window.FOSS.icons.el("upload", 32),
      D.el("div", { className: "media-dropzone-title", text: "Drop an audio or video file here" }),
      D.el("div", { className: "text-sm text-muted", text: "or click to browse your files" })
    ]);

    var actionGrid = D.el("div", { className: "media-action-grid", "data-testid": "media-action-cards" }, [
      actionCard("media-action-trim", "scissors", "Trim & Cut", "Cut a clip between two timestamps.", "trim"),
      actionCard("media-action-audio", "music", "Audio Extraction", "Save the audio track as MP3, WAV, or more.", "audio"),
      actionCard("media-action-subtitles", "file-text", "Subtitle Generation", "Transcribe speech to SRT or VTT.", "audio"),
      actionCard("media-action-gif", "image", "GIF Creation", "Turn a video into an animated GIF.", "effects")
    ]);

    var emptyState = D.el("div", { className: "media-empty-state", "data-testid": "media-empty-state" }, [dropzone, actionGrid]);

    var detailsEl = D.el("div", { className: "text-xs text-muted font-mono media-meta-details", text: "Open a file to inspect stream parameters." });
    var metaCard = D.el("div", { className: "card card-compact", "data-testid": "media-meta-card" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Media Details" }),
      detailsEl
    ]);

    function updateMetaUI(info) {
      detailsEl.innerHTML = "";
      if (!info) {
        detailsEl.textContent = "Open a file to inspect stream parameters.";
        return;
      }
      var fps = info.fps ? " @" + info.fps + "fps" : "";
      var rate = info.sample_rate ? info.sample_rate + "Hz " : "";
      var kbps = info.bitrate_kbps ? info.bitrate_kbps + "kbps" : "";
      var lines = [
        "Duration: " + (info.duration_str || formatTimeSec(info.duration_sec)),
        "Format: " + String(info.format || "unknown").toUpperCase(),
        info.has_video ? "Video: " + (info.video_codec || "unknown") + " (" + (info.width || "?") + "x" + (info.height || "?") + fps + ")" : "Video: None",
        info.has_audio ? "Audio: " + (info.audio_codec || "unknown") + " (" + rate + kbps + ")" : "Audio: None"
      ];
      lines.forEach(function (line) {
        detailsEl.appendChild(D.el("div", { text: line }));
      });
    }

    function drawWaveform(progress) {
      if (!waveformCanvas.getContext) return;
      var c = waveformCanvas.getContext("2d");
      var w = waveformCanvas.width = waveformCanvas.clientWidth || 400;
      var h = waveformCanvas.height = waveformCanvas.clientHeight || 48;
      c.clearRect(0, 0, w, h);
      var bars = Math.floor(w / 4);
      var mid = h / 2;
      var active = accentColor("--accent", "currentColor");
      var idle = accentColor("--border-strong", "currentColor");
      for (var i = 0; i < bars; i++) {
        var barH = Math.abs(Math.sin(i * 0.28) * 0.7 + Math.cos(i * 0.12) * 0.3) * (mid - 4);
        c.fillStyle = (i / bars) <= progress ? active : idle;
        c.fillRect(i * 4, mid - barH, 2, barH * 2);
      }
    }

    function currentDuration() {
      return videoEl.duration || (state.info ? state.info.duration_sec : 0) || 0;
    }

    videoEl.addEventListener("timeupdate", function () {
      var cur = videoEl.currentTime || 0;
      var dur = currentDuration();
      timeLabel.textContent = formatTimeSec(cur) + " / " + formatTimeSec(dur);
      drawWaveform(dur > 0 ? (cur / dur) : 0);
    });

    videoEl.addEventListener("error", function () {
      toastError("This file cannot be previewed in the player. Exports still work.");
    });

    function applyLoadedUI() {
      var hasFile = !!state.file;
      emptyState.classList.toggle("hidden", hasFile);
      videoEl.classList.toggle("hidden", !hasFile);
      waveformCanvas.classList.toggle("hidden", !hasFile);
      fileBadge.textContent = hasFile ? baseName(state.file) : "No media loaded";
      fileBadge.title = hasFile ? state.file : "No media loaded";
      updateMetaUI(state.info);
      timeLabel.textContent = "00:00.0 / " + formatTimeSec(currentDuration());
      if (hasFile) drawWaveform(0);
    }

    function attachPlayback(path) {
      window.FOSS.api("media_get_file_url", { file_path: path }).then(function (res) {
        if (res && res.ok && res.url) {
          videoEl.src = res.url;
          videoEl.load();
        }
      });
    }

    function loadFile(path, targetTab) {
      loadMedia(path, function () {
        applyLoadedUI();
        attachPlayback(path);
        listeners.forEach(function (fn) { fn(state.info); });
        if (targetTab && goToTab) goToTab(targetTab);
      });
    }

    var stageContainer = D.el("div", { className: "media-stage-pane" }, [
      emptyState,
      videoEl,
      waveformCanvas,
      D.el("div", { className: "row gap-2 items-center flex-wrap" }, [chooseBtn, openBtn]),
      D.el("div", { className: "row gap-2 items-center justify-between media-file-row" }, [fileBadge, timeLabel]),
      metaCard
    ]);

    applyLoadedUI();
    if (state.file) attachPlayback(state.file);

    var stage = {
      el: stageContainer,
      video: videoEl,
      loadFile: function (path) { loadFile(path, ""); },
      onLoaded: function (fn) { listeners.push(fn); },
      getTime: function () { return videoEl.currentTime || 0; },
      getDuration: currentDuration
    };
    state.stage = stage;
    return stage;
  }

  function buildTab(panel, statusText, buildSidebar) {
    var D = window.FOSS.dom;
    panel.innerHTML = "";
    var statusBar = D.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: statusText });
    var resHost = createResultHost();
    var stage = createPlayerStage(function (tabId) { window.FOSS.router.open(TOOL_ID, tabId); });

    var ui = {
      stage: stage,
      host: resHost,
      setStatus: function (text) { statusBar.textContent = text; },
      requireFile: function () {
        if (state.file) return true;
        statusBar.textContent = "Error: Select a media file first.";
        toastError("Select a media file first.");
        return false;
      },
      run: function (method, params, spec) {
        statusBar.textContent = spec.busy;
        return window.FOSS.job(method, params).then(function (res) {
          if (!res || res.ok === false) {
            var msg = errorText(res);
            statusBar.textContent = "Error: " + msg;
            toastError(spec.failure + ": " + msg);
            return null;
          }
          statusBar.textContent = spec.done + params.output_path;
          resHost.show(params.output_path, spec.title);
          return res;
        });
      }
    };

    var sidebarPane = D.el("div", { className: "media-sidebar-pane" }, buildSidebar(ui));
    var divider = window.FOSS.components.splitDivider({ vertical: true, side: "right", testid: "media-split-divider" });
    var split = D.el("div", {
      className: "split resizable split-main-first media-workbench",
      "data-testid": "media-workbench"
    }, [stage.el, divider, sidebarPane]);

    D.append(panel, statusBar);
    D.append(panel, resHost.el);
    D.append(panel, split);
  }

  function numberInput(testid, label, value, extra) {
    var attrs = {
      type: "number",
      className: "input font-mono",
      "data-testid": testid,
      value: value,
      "aria-label": label,
      title: label
    };
    Object.keys(extra || {}).forEach(function (k) { attrs[k] = extra[k]; });
    return window.FOSS.dom.el("input", attrs);
  }

  function selectInput(testid, label, options, selected) {
    return window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": testid,
      "aria-label": label,
      title: label
    }, options.map(function (opt) {
      var attrs = { value: opt[0], text: opt[1] };
      if (String(opt[0]) === String(selected)) attrs.selected = "selected";
      return window.FOSS.dom.el("option", attrs);
    }));
  }

  // TAB 1: Trim & Cut
  function renderTrim(panel) {
    var D = window.FOSS.dom;
    buildTab(panel, "Ready to trim media clips.", function (ui) {
      var fpsVal = (state.info && state.info.fps) ? parseFloat(state.info.fps) : 30.0;
      if (isNaN(fpsVal) || fpsVal <= 0) fpsVal = 30.0;

      var startInput = numberInput("media-trim-start", "Trim Start Time (seconds)", "0.0", { step: "0.1", min: "0", "data-truncate-ok": "true" });
      var endInput = numberInput("media-trim-end", "Trim End Time (seconds)", "10.0", { step: "0.1", min: "0", "data-truncate-ok": "true" });

      var startFrameInput = numberInput("media-trim-start-frame", "Start Frame", "0", { step: "1", min: "0" });
      var endFrameInput = numberInput("media-trim-end-frame", "End Frame", "300", { step: "1", min: "0" });

      var readoutEl = D.el("div", {
        className: "text-xs font-mono text-muted mb-2 p-2 rounded bg-neutral",
        text: "Position: 0.00s (Frame 0)"
      });

      function updateReadout(timeSec) {
        var curFps = (state.info && state.info.fps) ? parseFloat(state.info.fps) : fpsVal;
        var f = Math.round(timeSec * curFps);
        readoutEl.textContent = "Current Position: " + timeSec.toFixed(2) + "s (Frame " + f + ")";
      }

      startInput.addEventListener("input", function () {
        var s = parseFloat(startInput.value);
        if (!isNaN(s) && ui.stage && ui.stage.video) {
          ui.stage.video.currentTime = Math.max(0, s);
          startFrameInput.value = String(Math.round(s * fpsVal));
          updateReadout(Math.max(0, s));
        }
      });
      endInput.addEventListener("input", function () {
        var e = parseFloat(endInput.value);
        if (!isNaN(e) && ui.stage && ui.stage.video) {
          ui.stage.video.currentTime = Math.max(0, e);
          endFrameInput.value = String(Math.round(e * fpsVal));
          updateReadout(Math.max(0, e));
        }
      });

      startFrameInput.addEventListener("input", function () {
        var f = parseInt(startFrameInput.value, 10);
        if (!isNaN(f) && ui.stage && ui.stage.video) {
          var t = Math.max(0, f / fpsVal);
          startInput.value = t.toFixed(2);
          ui.stage.video.currentTime = t;
          updateReadout(t);
        }
      });
      endFrameInput.addEventListener("input", function () {
        var f = parseInt(endFrameInput.value, 10);
        if (!isNaN(f) && ui.stage && ui.stage.video) {
          var t = Math.max(0, f / fpsVal);
          endInput.value = t.toFixed(2);
          ui.stage.video.currentTime = t;
          updateReadout(t);
        }
      });

      if (ui.stage && ui.stage.video) {
        ui.stage.video.addEventListener("timeupdate", function () {
          updateReadout(ui.stage.video.currentTime || 0);
        });
      }

      function syncEndToDuration() {
        var dur = ui.stage.getDuration();
        if (dur > 0) {
          endInput.value = dur.toFixed(1);
          endFrameInput.value = String(Math.round(dur * fpsVal));
        }
      }
      ui.stage.onLoaded(syncEndToDuration);
      syncEndToDuration();

      var setStartBtn = D.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "media-trim-set-start-btn",
        type: "button",
        onClick: function () {
          var curT = ui.stage.getTime();
          startInput.value = curT.toFixed(2);
          startFrameInput.value = String(Math.round(curT * fpsVal));
          updateReadout(curT);
        }
      }, [window.FOSS.icons.el("play", 12), D.el("span", { text: "Set Start" })]);

      var setEndBtn = D.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "media-trim-set-end-btn",
        type: "button",
        onClick: function () {
          var curT = ui.stage.getTime();
          endInput.value = curT.toFixed(2);
          endFrameInput.value = String(Math.round(curT * fpsVal));
          updateReadout(curT);
        }
      }, [window.FOSS.icons.el("pause", 12), D.el("span", { text: "Set End" })]);

      var fastCopySwitch = window.FOSS.components.switch({
        testid: "media-trim-fast-copy",
        label: "Fast Lossless Stream Copy (No re-encoding)",
        checked: !!window.FOSS.toolDefaults.get(TOOL_ID, "fast_copy", true)
      });

      var handleTrim = function () {
        if (!ui.requireFile()) return;
        var s = parseFloat(startInput.value) || 0;
        var e = parseFloat(endInput.value) || 0;
        if (e <= s) {
          ui.setStatus("Error: End time must be greater than start time.");
          return;
        }
        pickSavePath("Save Trimmed Media", sourceExportExts()).then(function (outPath) {
          if (!outPath) return;
          ui.run("media_trim", {
            input_path: state.file,
            output_path: outPath,
            start_time: s,
            end_time: e,
            fast_copy: fastCopySwitch.isChecked()
          }, { busy: "Trimming media clip...", done: "Trim complete: ", title: "Clip Trimmed", failure: "Trim failed" });
        });
      };

      var runBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-trim-btn",
        type: "button",
        onClick: handleTrim
      }, [window.FOSS.icons.el("scissors", 16), D.el("span", { text: "Trim Video" })]);

      var runBtnAlias = D.el("button", {
        className: "btn btn-secondary",
        "data-testid": "media-trim-run-btn",
        type: "button",
        onClick: handleTrim
      }, [window.FOSS.icons.el("scissors", 16), D.el("span", { text: "Export Trimmed Clip..." })]);

      return [D.el("div", { className: "card card-compact" }, [
        D.el("div", { className: "card-title text-sm font-semibold", text: "Trim Parameters" }),
        readoutEl,
        D.el("div", { className: "grid grid-cols-2 gap-3 mb-2" }, [
          D.el("div", { className: "flex-col gap-1" }, [window.FOSS.components.field("Start Time (sec)", startInput), setStartBtn]),
          D.el("div", { className: "flex-col gap-1" }, [window.FOSS.components.field("End Time (sec)", endInput), setEndBtn])
        ]),
        D.el("div", { className: "grid grid-cols-2 gap-3 mb-2" }, [
          D.el("div", { className: "flex-col gap-1" }, [window.FOSS.components.field("Start Frame", startFrameInput)]),
          D.el("div", { className: "flex-col gap-1" }, [window.FOSS.components.field("End Frame", endFrameInput)])
        ]),
        fastCopySwitch.el,
        D.el("div", { className: "row gap-2 flex-wrap" }, [runBtn, runBtnAlias])
      ])];
    });
  }

  // TAB 2: Audio & Subtitles
  function renderAudio(panel) {
    var D = window.FOSS.dom;
    buildTab(panel, "Ready to extract audio or generate subtitles.", function (ui) {
      var defaultFormat = String(window.FOSS.toolDefaults.get(TOOL_ID, "audio_format", "mp3"));
      var defaultBitrate = String(window.FOSS.toolDefaults.get(TOOL_ID, "bitrate", "192k"));

      var formatSelect = selectInput("media-audio-format-select", "Audio Format", [
        ["mp3", "MP3 Audio (.mp3)"],
        ["wav", "WAV Lossless (.wav)"],
        ["flac", "FLAC Audio (.flac)"],
        ["aac", "AAC Audio (.aac)"],
        ["opus", "Opus Audio (.opus)"]
      ], defaultFormat);

      var bitrateSelect = selectInput("media-audio-bitrate-select", "Audio Bitrate", [
        ["128k", "128 kbps"],
        ["192k", "192 kbps"],
        ["256k", "256 kbps"],
        ["320k", "320 kbps"]
      ], defaultBitrate);

      var handleExtractAudio = function () {
        if (!ui.requireFile()) return;
        var chosen = formatSelect.value;
        var order = [chosen].concat(["mp3", "wav", "flac", "aac", "opus"]);
        pickSavePath("Save Extracted Audio Track", order).then(function (outPath) {
          if (!outPath) return;
          var pathExt = extOf(outPath);
          var fmt = ["mp3", "wav", "flac", "aac", "opus"].indexOf(pathExt) >= 0 ? pathExt : chosen;
          ui.run("media_extract_audio", {
            input_path: state.file,
            output_path: outPath,
            audio_format: fmt,
            bitrate: bitrateSelect.value
          }, { busy: "Extracting audio track...", done: "Audio extracted: ", title: "Audio Track Extracted", failure: "Audio extraction failed" });
        });
      };

      var extractAudioBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-extract-audio-btn",
        type: "button",
        onClick: handleExtractAudio
      }, [window.FOSS.icons.el("music", 16), D.el("span", { text: "Extract Audio" })]);

      var extractAudioBtnAlias = D.el("button", {
        className: "btn btn-secondary",
        "data-testid": "media-audio-extract-btn",
        type: "button",
        onClick: handleExtractAudio
      }, [window.FOSS.icons.el("music", 16), D.el("span", { text: "Extract Audio Track..." })]);

      var muteBtn = D.el("button", {
        className: "btn btn-secondary",
        "data-testid": "media-mute-btn",
        type: "button",
        onClick: function () {
          if (!ui.requireFile()) return;
          pickSavePath("Save Muted Video", ["mp4", "webm"]).then(function (outPath) {
            if (!outPath) return;
            ui.run("media_mute_video", {
              input_path: state.file,
              output_path: outPath
            }, { busy: "Stripping audio track from video...", done: "Video muted: ", title: "Muted Video Created", failure: "Mute failed" });
          });
        }
      }, [window.FOSS.icons.el("volume-x", 16), D.el("span", { text: "Mute Video (Strip Audio)" })]);

      var langInput = D.el("input", {
        type: "text",
        className: "input font-mono",
        "data-testid": "media-transcribe-lang",
        value: "en",
        placeholder: "en, es, fr, de, ja...",
        "aria-label": "Speech Language Code",
        title: "Speech Language Code"
      });

      var subFormatSelect = selectInput("media-transcribe-format", "Transcription Output", [
        ["srt", "SubRip Subtitle (.srt)"],
        ["vtt", "WebVTT (.vtt)"],
        ["txt", "Plain Text File (.txt)"],
        ["app", "Direct In-App Transcript Display"]
      ], "srt");

      var inAppTranscriptEl = D.el("textarea", {
        className: "input font-mono text-xs w-full hidden",
        "data-testid": "media-transcript-inapp",
        rows: "6",
        readonly: true,
        placeholder: "Transcription text will appear here..."
      });

      var transcribeBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-transcribe-btn",
        type: "button",
        onClick: function () {
          if (!ui.requireFile()) return;
          var chosenFmt = subFormatSelect.value;
          if (chosenFmt === "app") {
            ui.setStatus("Transcribing audio via local Whisper...");
            window.FOSS.job("media_transcribe", {
              input_path: state.file,
              language: langInput.value.trim() || "en"
            }).then(function (res) {
              if (!res || res.ok === false) {
                ui.setStatus("Error: " + errorText(res));
                toastError("Transcription failed: " + errorText(res));
                return;
              }
              inAppTranscriptEl.value = res.text || "(No transcription text captured)";
              inAppTranscriptEl.classList.remove("hidden");
              ui.setStatus(res.warning ? "Warning: " + res.warning : "Transcription complete (displayed in app)");
            });
            return;
          }
          var order = chosenFmt === "vtt" ? ["vtt", "srt", "txt"] : (chosenFmt === "txt" ? ["txt", "srt", "vtt"] : ["srt", "vtt", "txt"]);
          pickSavePath("Save Transcription / Subtitles", order).then(function (outPath) {
            if (!outPath) return;
            var fmt = extOf(outPath) === "txt" ? "txt" : (extOf(outPath) === "vtt" ? "vtt" : "srt");
            ui.setStatus("Transcribing audio via local Whisper...");
            window.FOSS.job("media_transcribe", {
              input_path: state.file,
              output_path: outPath,
              language: langInput.value.trim() || "en",
              subtitle_format: fmt
            }).then(function (res) {
              if (!res || res.ok === false) {
                ui.setStatus("Error: " + errorText(res));
                toastError("Transcription failed: " + errorText(res));
                return;
              }
              if (res.text) {
                inAppTranscriptEl.value = res.text;
                inAppTranscriptEl.classList.remove("hidden");
              }
              ui.setStatus(res.warning ? "Warning: " + res.warning : "Transcription complete: " + outPath);
              ui.host.show(outPath, "Transcription Saved");
            });
          });
        }
      }, [window.FOSS.icons.el("file-text", 16), D.el("span", { text: "Transcribe Speech (Whisper)..." })]);

      return [
        D.el("div", { className: "card card-compact" }, [
          D.el("div", { className: "card-title text-sm font-semibold", text: "Audio Track Extraction" }),
          D.el("div", { className: "grid grid-cols-2 gap-2" }, [
            window.FOSS.components.field("Output Audio Format", formatSelect),
            window.FOSS.components.field("Bitrate", bitrateSelect)
          ]),
          D.el("div", { className: "row gap-2 flex-wrap" }, [extractAudioBtn, extractAudioBtnAlias, muteBtn])
        ]),
        D.el("div", { className: "card card-compact" }, [
          D.el("div", { className: "card-title text-sm font-semibold", text: "Offline Speech Transcription" }),
          D.el("div", { className: "grid grid-cols-2 gap-2" }, [
            window.FOSS.components.field("Language Code", langInput),
            window.FOSS.components.field("Transcription Output", subFormatSelect)
          ]),
          transcribeBtn,
          inAppTranscriptEl
        ])
      ];
    });
  }

  // TAB 3: Frames, Speed & GIF
  function renderEffects(panel) {
    var D = window.FOSS.dom;
    buildTab(panel, "Ready to capture frames, change speed, or convert to GIF.", function (ui) {
      var captureFrameBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-frame-capture-btn",
        type: "button",
        onClick: function () {
          if (!ui.requireFile()) return;
          var ts = ui.stage.getTime();
          pickSavePath("Save Still Frame", ["jpg", "png"]).then(function (outPath) {
            if (!outPath) return;
            ui.setStatus("Capturing still frame...");
            window.FOSS.api("media_capture_frame", {
              input_path: state.file,
              output_path: outPath,
              timestamp: ts
            }).then(function (res) {
              if (!res || res.ok === false) {
                ui.setStatus("Error: " + errorText(res));
                return;
              }
              ui.setStatus("Frame saved: " + outPath);
              ui.host.show(outPath, "Frame Captured at " + formatTimeSec(ts));
            });
          });
        }
      }, [window.FOSS.icons.el("camera", 16), D.el("span", { text: "Capture Frame at Current Playhead..." })]);

      var speedSelect = selectInput("media-speed-select", "Playback Speed", [
        ["0.25", "0.25x (Super Slow)"],
        ["0.5", "0.5x (Slow Motion)"],
        ["1.0", "1.0x (Normal Speed)"],
        ["1.5", "1.5x (Speed Up)"],
        ["2.0", "2.0x (Double Speed)"],
        ["4.0", "4.0x (Hyper Speed)"]
      ], "1.0");

      speedSelect.addEventListener("change", function () {
        var sp = parseFloat(speedSelect.value) || 1.0;
        if (ui.stage && ui.stage.video) {
          ui.stage.video.playbackRate = sp;
        }
      });

      var defaultReverse = Boolean(window.FOSS.toolDefaults.get(TOOL_ID, "reverse", false));
      var reverseSwitch = window.FOSS.components.switch({
        testid: "media-speed-reverse",
        label: "Reverse Playback (Backwards)",
        checked: defaultReverse
      });

      var speedRunBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-speed-reverse-btn",
        type: "button",
        onClick: function () {
          if (!ui.requireFile()) return;
          var sp = parseFloat(speedSelect.value) || 1.0;
          pickSavePath("Save Processed Media", sourceExportExts().slice(0, 3)).then(function (outPath) {
            if (!outPath) return;
            ui.run("media_speed_reverse", {
              input_path: state.file,
              output_path: outPath,
              speed_factor: sp,
              reverse: reverseSwitch.isChecked()
            }, { busy: "Processing speed and direction...", done: "Speed/reverse export complete: ", title: "Processed Media Created", failure: "Speed/reverse failed" });
          });
        }
      }, [window.FOSS.icons.el("play", 16), D.el("span", { text: "Apply Speed & Reverse..." })]);

      var defaultGifFps = String(window.FOSS.toolDefaults.get(TOOL_ID, "gif_fps", 15));
      var gifFpsInput = numberInput("media-gif-fps", "GIF Frame Rate", defaultGifFps, { min: "5", max: "30" });
      var gifWidthInput = numberInput("media-gif-width", "GIF Width (px)", "480", { min: "160", max: "1280" });

      var handleCreateGif = function () {
        if (!ui.requireFile()) return;
        var fpsVal = parseInt(gifFpsInput.value, 10) || 15;
        var wVal = parseInt(gifWidthInput.value, 10) || 480;
        pickSavePath("Save Animated GIF", ["gif"]).then(function (outPath) {
          if (!outPath) return;
          ui.run("media_video_to_gif", {
            input_path: state.file,
            output_path: outPath,
            start_time: 0.0,
            fps: fpsVal,
            width: wVal
          }, { busy: "Converting video segment to optimized GIF...", done: "GIF created: ", title: "Animated GIF Exported", failure: "GIF creation failed" });
        });
      };

      var gifBtn = D.el("button", {
        className: "btn btn-primary",
        "data-testid": "media-create-gif-btn",
        type: "button",
        onClick: handleCreateGif
      }, [window.FOSS.icons.el("image", 16), D.el("span", { text: "Create Animated GIF" })]);

      var gifBtnAlias = D.el("button", {
        className: "btn btn-secondary",
        "data-testid": "media-gif-btn",
        type: "button",
        onClick: handleCreateGif
      }, [window.FOSS.icons.el("image", 16), D.el("span", { text: "Convert Video to GIF..." })]);

      return [
        D.el("div", { className: "card card-compact" }, [
          D.el("div", { className: "card-title text-sm font-semibold", text: "Still Frame Capture" }),
          captureFrameBtn
        ]),
        D.el("div", { className: "card card-compact" }, [
          D.el("div", { className: "card-title text-sm font-semibold", text: "Playback Speed & Reversal" }),
          window.FOSS.components.field("Playback Speed", speedSelect),
          reverseSwitch.el,
          speedRunBtn
        ]),
        D.el("div", { className: "card card-compact" }, [
          D.el("div", { className: "card-title text-sm font-semibold", text: "Animated GIF Generator" }),
          D.el("div", { className: "grid grid-cols-2 gap-2" }, [
            window.FOSS.components.field("Frame Rate (FPS)", gifFpsInput),
            window.FOSS.components.field("Max Width (px)", gifWidthInput)
          ]),
          D.el("div", { className: "row gap-2 flex-wrap" }, [gifBtn, gifBtnAlias])
        ])
      ];
    });
  }

  // TAB 4: Multi-Clip Joiner (Timeline)
  function renderTimeline(panel) {
    var D = window.FOSS.dom;
    panel.innerHTML = "";
    state.stage = null;
    var statusBar = D.el("div", { className: "text-xs text-muted", "data-testid": "media-status", text: "Assemble multiple clips into a continuous movie." });
    var resHost = createResultHost();
    var clipsQueue = [];

    var clipsListEl = D.el("div", { className: "flex-col gap-2 media-timeline-list", "data-testid": "media-timeline-list" });

    function moveClip(idx, delta) {
      var tmp = clipsQueue[idx + delta];
      clipsQueue[idx + delta] = clipsQueue[idx];
      clipsQueue[idx] = tmp;
      renderClipsList();
    }

    function renderClipsList() {
      clipsListEl.innerHTML = "";
      if (clipsQueue.length === 0) {
        clipsListEl.appendChild(D.el("div", { className: "text-sm text-muted p-4 text-center font-mono", text: "No clips added yet. Add video files to assemble." }));
        return;
      }
      clipsQueue.forEach(function (clip, idx) {
        var row = D.el("div", {
          className: "card card-compact row items-center justify-between gap-2",
          "data-testid": "media-timeline-item-" + idx
        }, [
          D.el("div", { className: "row items-center gap-2 min-w-0" }, [
            D.el("span", { className: "badge neutral text-xs font-mono", text: "#" + (idx + 1) }),
            D.el("span", { className: "font-mono text-sm truncate", text: baseName(clip.input), title: clip.input, "data-truncate-ok": "true" })
          ]),
          D.el("div", { className: "row items-center gap-1" }, [
            D.el("button", {
              className: "btn btn-ghost btn-sm",
              type: "button",
              text: "Up",
              title: "Move Clip Up",
              disabled: idx === 0 ? "true" : undefined,
              onClick: function () { moveClip(idx, -1); }
            }),
            D.el("button", {
              className: "btn btn-ghost btn-sm",
              type: "button",
              text: "Down",
              title: "Move Clip Down",
              disabled: idx === clipsQueue.length - 1 ? "true" : undefined,
              onClick: function () { moveClip(idx, 1); }
            }),
            D.el("button", {
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

    var addBtn = D.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-timeline-add-btn",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Select Video Clips to Join",
          file_types: ["mp4", "mkv", "webm", "avi", "mov"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            res.paths.forEach(function (p) { clipsQueue.push({ input: p }); });
            renderClipsList();
          }
        });
      }
    }, [window.FOSS.icons.el("plus", 14), D.el("span", { text: "Add Clips..." })]);

    var clearBtn = D.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "media-timeline-clear-btn",
      type: "button",
      onClick: function () {
        clipsQueue = [];
        renderClipsList();
      }
    }, [window.FOSS.icons.el("trash", 14), D.el("span", { text: "Clear List" })]);

    var joinBtn = D.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-timeline-run-btn",
      type: "button",
      onClick: function () {
        if (clipsQueue.length < 2) {
          statusBar.textContent = "Error: Add at least 2 clips to join.";
          return;
        }
        pickSavePath("Save Joined Video", ["mp4", "webm"]).then(function (outPath) {
          if (!outPath) return;
          statusBar.textContent = "Concatenating " + clipsQueue.length + " clips...";
          window.FOSS.job("media_compose_timeline", { clips: clipsQueue, output_path: outPath }).then(function (res) {
            if (!res || res.ok === false) {
              statusBar.textContent = "Error: " + errorText(res);
              toastError("Join failed: " + errorText(res));
              return;
            }
            statusBar.textContent = "Timeline export complete: " + outPath;
            resHost.show(outPath, "Joined Movie Created");
          });
        });
      }
    }, [window.FOSS.icons.el("film", 16), D.el("span", { text: "Join Clips into Single Video..." })]);

    renderClipsList();

    var timelineCard = D.el("div", { className: "card card-compact flex-col gap-3" }, [
      D.el("div", { className: "card-title text-sm font-semibold", text: "Clip Sequence Queue" }),
      D.el("div", { className: "row gap-2 items-center justify-between" }, [addBtn, clearBtn]),
      clipsListEl,
      joinBtn
    ]);

    D.append(panel, statusBar);
    D.append(panel, resHost.el);
    D.append(panel, timelineCard);
  }

  window.FOSS.router.register({
    id: TOOL_ID,
    title: "Audio & Video Studio",
    navName: "Audio & Video",
    category: "Media",
    icon: "media",
    workbench: true,
    defaults: [
      { key: "audio_format", label: "Default audio export format", type: "select", options: ["mp3", "wav", "flac", "aac", "opus"], default: "mp3" },
      { key: "bitrate", label: "Default audio bitrate", type: "select", options: ["128k", "192k", "256k", "320k"], default: "192k" },
      { key: "fast_copy", label: "Fast stream copy when trimming", type: "toggle", default: true, hint: "Trim without re-encoding when possible." },
      { key: "reverse", label: "Reverse playback by default in effects", type: "toggle", default: false },
      { key: "gif_fps", label: "Default animated GIF frame rate", type: "number", min: 5, max: 30, step: 1, default: 15 }
    ],
    onFiles: function (paths) {
      if (!paths || paths.length === 0) return;
      if (state.stage) {
        state.stage.loadFile(paths[0]);
      } else {
        state.file = paths[0];
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
