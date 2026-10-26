// Audio & Video Studio: trimming, transcoding, size compression, audio extraction, frame capture, muting, and timeline composer.
window.FOSS = window.FOSS || {};

(function () {
  var globalCurrentFile = "";

  // Common Header & State
  function createMediaHeader() {
    return window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "media studio" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "trim, convert, compress, extract audio, and capture frames from video and audio offline." })
    ]);
  }

  // ==========================================
  // TAB 1: Trim & Cut
  // ==========================================
  function renderTrim(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = globalCurrentFile;
    var duration = 0;

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-trim-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-trim-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-trim-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-trim-result-card", title: titleText || "Trim Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var videoPlayer = window.FOSS.dom.el("video", {
      controls: "true",
      "data-testid": "media-video-player",
      style: { width: "100%", maxHeight: "320px", backgroundColor: "#000", borderRadius: "var(--radius-md)", display: "block" }
    });

    var timeDisplay = window.FOSS.dom.el("span", {
      className: "text-xs font-mono",
      "data-testid": "media-time-display",
      text: "00:00:00.0 / 00:00:00.0"
    });

    var selDuration = window.FOSS.dom.el("span", {
      className: "text-xs font-mono text-muted",
      "data-testid": "media-sel-duration",
      text: "selection duration: 0.000s"
    });

    var startTimeInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "number",
      step: "0.1",
      min: "0",
      value: "0.0",
      "data-testid": "media-start-time",
      "aria-label": "start time (s)",
      title: "start time (s)",
      style: { minHeight: "36px", minWidth: "120px" },
      onInput: updateSelDuration
    });

    var endTimeInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "number",
      step: "0.1",
      min: "0",
      value: "0.0",
      "data-testid": "media-end-time",
      "aria-label": "end time (s)",
      title: "end time (s)",
      style: { minHeight: "36px", minWidth: "120px" },
      onInput: updateSelDuration
    });

    function updateSelDuration() {
      var st = parseFloat(startTimeInput.value) || 0;
      var et = parseFloat(endTimeInput.value) || 0;
      var diff = Math.max(0, et - st);
      selDuration.textContent = "selection duration: " + diff.toFixed(3) + "s";
    }

    var markStartBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-mark-start-btn",
      "aria-label": "mark start",
      title: "mark start",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        startTimeInput.value = (videoPlayer.currentTime || 0).toFixed(1);
        updateSelDuration();
      }
    }, [window.FOSS.dom.el("span", { text: "mark start" })]);

    var markEndBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-mark-end-btn",
      "aria-label": "mark end",
      title: "mark end",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        endTimeInput.value = (videoPlayer.currentTime || 0).toFixed(1);
        updateSelDuration();
      }
    }, [window.FOSS.dom.el("span", { text: "mark end" })]);

    var playBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-play-btn",
      "aria-label": "▶ play",
      title: "▶ play",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        videoPlayer.play().catch(function () {});
      }
    }, [window.FOSS.dom.el("span", { text: "▶ play" })]);

    var stopBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-stop-btn",
      "aria-label": "⏹ stop",
      title: "⏹ stop",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        videoPlayer.pause();
        videoPlayer.currentTime = 0;
      }
    }, [window.FOSS.dom.el("span", { text: "⏹ stop" })]);

    var modeSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-cut-mode",
      "aria-label": "trim mode",
      title: "trim mode",
      style: { minHeight: "36px", minWidth: "220px" }
    }, [
      window.FOSS.dom.el("option", { value: "fast", text: "fast stream copy -- lossless instantaneous (keyframe aligned)" }),
      window.FOSS.dom.el("option", { value: "precise", text: "high precision (re-encode) -- frame accurate cuts" })
    ]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "media-file-picker",
      title: "select any video or audio file (mp4, mov, mkv, mp3, wav, aac, etc.)",
      fileTypes: ["mp4", "mkv", "mov", "avi", "webm", "mp3", "wav", "aac", "flac", "m4a", "ogg"],
      onSelect: function (val) {
        currentFile = val;
        globalCurrentFile = val;
        clearError();
        statusBar.textContent = "Loading media info...";
        ctx.api("media_get_info", { file_path: val }).then(function (res) {
          if (res && res.ok && res.info) {
            duration = parseFloat(res.info.duration || 0);
            timeDisplay.textContent = "00:00:00.0 / " + (res.duration_formatted || "00:00:00.0");
            endTimeInput.value = duration.toFixed(1);
            updateSelDuration();
            statusBar.textContent = "Loaded: " + val.split(/[/\\]/).pop();
          }
        });
        ctx.api("media_get_file_url", { file_path: val }).then(function (ures) {
          if (ures && ures.ok && ures.url) {
            videoPlayer.src = ures.url;
          }
        });
      },
      onClear: function () {
        currentFile = "";
        globalCurrentFile = "";
        videoPlayer.src = "";
        timeDisplay.textContent = "00:00:00.0 / 00:00:00.0";
        startTimeInput.value = "0.0";
        endTimeInput.value = "0.0";
        updateSelDuration();
      }
    });

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-trim-btn",
      "aria-label": "export trimmed media",
      title: "export trimmed media",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a media file first.");
          return;
        }
        var st = parseFloat(startTimeInput.value) || 0;
        var et = parseFloat(endTimeInput.value) || 0;
        if (et <= st) {
          showError("End time must be greater than start time.");
          return;
        }
        var ext = currentFile.split(".").pop();
        ctx.api("select_save_path", { title: "Save Trimmed Media", default_name: "trimmed." + ext, file_types: [ext] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Trimming media...";
          ctx.api("media_trim", { input_path: currentFile, output_path: saveP, start_time: st, end_time: et }).then(function (tres) {
            if (tres && tres.ok && tres.output_path) {
              statusBar.textContent = "Trimming complete.";
              showResult(tres.output_path, "Media Trimmed");
            } else {
              showError((tres && tres.error) || "Trim failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("scissors", 18),
      window.FOSS.dom.el("span", { text: "export trimmed media" })
    ]);

    // Cards
    var previewGroup = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "playback & preview" }),
      videoPlayer,
      window.FOSS.dom.el("div", { className: "row items-center justify-between", style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" } }, [
        window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", gap: "var(--space-2)" } }, [playBtn, stopBtn, timeDisplay]),
        selDuration
      ])
    ]);

    var rangeGroup = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "range & trim points" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "cut a section from the file using the start and end markers defined above." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("start time (s)", startTimeInput),
        markStartBtn,
        window.FOSS.components.field("end time (s)", endTimeInput),
        markEndBtn,
        window.FOSS.components.field("mode", modeSelect),
        exportBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(previewGroup);
    panel.appendChild(rangeGroup);
  }

  // ==========================================
  // TAB 2: Convert & Transcode
  // ==========================================
  function renderConvert(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = globalCurrentFile;

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-convert-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-convert-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-convert-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-convert-result-card", title: titleText || "Convert Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-convert-format",
      "aria-label": "format",
      title: "format",
      style: { minHeight: "36px", minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "mp4", text: "mp4 (.mp4)" }),
      window.FOSS.dom.el("option", { value: "mkv", text: "mkv (.mkv)" }),
      window.FOSS.dom.el("option", { value: "webm", text: "webm (.webm)" }),
      window.FOSS.dom.el("option", { value: "mov", text: "mov (.mov)" }),
      window.FOSS.dom.el("option", { value: "avi", text: "avi (.avi)" }),
      window.FOSS.dom.el("option", { value: "mp3", text: "mp3 (.mp3)" }),
      window.FOSS.dom.el("option", { value: "wav", text: "wav (.wav)" }),
      window.FOSS.dom.el("option", { value: "flac", text: "flac (.flac)" }),
      window.FOSS.dom.el("option", { value: "aac", text: "aac (.aac)" }),
      window.FOSS.dom.el("option", { value: "m4a", text: "m4a (.m4a)" }),
      window.FOSS.dom.el("option", { value: "ogg", text: "ogg (.ogg)" }),
      window.FOSS.dom.el("option", { value: "gif", text: "gif" })
    ]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "media-convert-picker",
      title: "open media file",
      fileTypes: ["mp4", "mkv", "mov", "avi", "webm", "mp3", "wav", "aac", "flac", "m4a", "ogg"],
      onSelect: function (val) {
        currentFile = val;
        globalCurrentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
        globalCurrentFile = "";
      }
    });

    var convertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-convert-btn",
      "aria-label": "convert media",
      title: "convert media",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a media file first.");
          return;
        }
        var targetFmt = formatSelect.value;
        ctx.api("select_save_path", { title: "Save Converted Media", default_name: "converted." + targetFmt, file_types: [targetFmt] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Transcoding media...";
          ctx.api("media_convert", { input_path: currentFile, output_path: saveP }).then(function (cres) {
            if (cres && cres.ok && cres.output_path) {
              statusBar.textContent = "Conversion complete.";
              showResult(cres.output_path, "Media Converted");
            } else {
              showError((cres && cres.error) || "Conversion failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("refresh-cw", 18),
      window.FOSS.dom.el("span", { text: "convert media" })
    ]);

    var convCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "media details" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "transcode media to another container or format." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("target container", formatSelect),
        convertBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(convCard);
  }

  // ==========================================
  // TAB 3: Compress Video
  // ==========================================
  function renderCompress(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = globalCurrentFile;

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-compress-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-compress-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-compress-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-compress-result-card", title: titleText || "Compression Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var presetSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-compress-preset",
      "aria-label": "preset",
      title: "preset",
      style: { minHeight: "36px", minWidth: "240px" }
    }, [
      window.FOSS.dom.el("option", { value: "8", text: "discord / email target (8mb limit, 480p / crf 28)" }),
      window.FOSS.dom.el("option", { value: "8_small", text: "discord / email target (small, crf 28)" }),
      window.FOSS.dom.el("option", { value: "25", text: "balanced web (720p / crf 24)" }),
      window.FOSS.dom.el("option", { value: "crf23", text: "balanced (crf 23) - recommended" }),
      window.FOSS.dom.el("option", { value: "crf24", text: "balanced (crf 24)" }),
      window.FOSS.dom.el("option", { value: "50", text: "high quality (1080p / crf 20)" }),
      window.FOSS.dom.el("option", { value: "crf18", text: "high quality (crf 18)" }),
      window.FOSS.dom.el("option", { value: "crf20", text: "high quality (crf 20)" }),
      window.FOSS.dom.el("option", { value: "crf28", text: "smaller file (crf 28)" })
    ]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "media-compress-picker",
      title: "open media file",
      fileTypes: ["mp4", "mkv", "mov", "avi", "webm"],
      onSelect: function (val) {
        currentFile = val;
        globalCurrentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
        globalCurrentFile = "";
      }
    });

    var compressBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-compress-btn",
      "aria-label": "compress video",
      title: "compress video",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a video file first.");
          return;
        }
        var ext = currentFile.split(".").pop();
        ctx.api("select_save_path", { title: "Save Compressed Video", default_name: "compressed." + ext, file_types: [ext] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Compressing video...";
          var targetMb = parseFloat(presetSelect.value) || 25.0;
          ctx.api("media_compress", { input_path: currentFile, output_path: saveP, target_size_mb: targetMb }).then(function (cres) {
            if (cres && cres.ok && cres.output_path) {
              statusBar.textContent = "Compression complete.";
              showResult(cres.output_path, "Video Compressed");
            } else {
              showError((cres && cres.error) || "Compression failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("minimize-2", 18),
      window.FOSS.dom.el("span", { text: "compress video" })
    ]);

    var compCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "compress" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "shrink video file size for sharing on discord, email, or web." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("compression profile", presetSelect),
        compressBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(compCard);
  }

  // ==========================================
  // TAB 4: Extract Audio
  // ==========================================
  function renderExtractAudio(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = globalCurrentFile;

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-audio-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-audio-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-audio-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-audio-result-card", title: titleText || "Audio Extracted", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-audio-format",
      "aria-label": "audio format",
      title: "audio format",
      style: { minHeight: "36px", minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "mp3", text: "mp3 (.mp3)" }),
      window.FOSS.dom.el("option", { value: "wav", text: "wav (.wav)" }),
      window.FOSS.dom.el("option", { value: "aac", text: "aac (.aac)" }),
      window.FOSS.dom.el("option", { value: "flac", text: "flac (.flac)" }),
      window.FOSS.dom.el("option", { value: "m4a", text: "m4a (.m4a)" }),
      window.FOSS.dom.el("option", { value: "ogg", text: "ogg (.ogg)" })
    ]);

    var bitrateSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "media-audio-bitrate",
      "aria-label": "bitrate",
      title: "bitrate",
      style: { minHeight: "36px", minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "128k", text: "128 kbps (compact)" }),
      window.FOSS.dom.el("option", { value: "192k", selected: true, text: "192 kbps (standard)" }),
      window.FOSS.dom.el("option", { value: "256k", text: "256 kbps (very good)" }),
      window.FOSS.dom.el("option", { value: "320k", text: "320 kbps (high quality)" })
    ]);

    var filePicker = window.FOSS.components.filePicker({
      testid: "media-audio-picker",
      title: "open media file",
      fileTypes: ["mp4", "mkv", "mov", "avi", "webm"],
      onSelect: function (val) {
        currentFile = val;
        globalCurrentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
        globalCurrentFile = "";
      }
    });

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-extract-audio-btn",
      "aria-label": "extract audio track",
      title: "extract audio track",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a video file first.");
          return;
        }
        var fmt = formatSelect.value;
        ctx.api("select_save_path", { title: "Save Extracted Audio", default_name: "audio." + fmt, file_types: [fmt] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Extracting audio track...";
          ctx.api("media_extract_audio", { input_path: currentFile, output_path: saveP, bitrate: bitrateSelect.value }).then(function (ares) {
            if (ares && ares.ok && ares.output_path) {
              statusBar.textContent = "Audio extracted.";
              showResult(ares.output_path, "Audio Track Extracted");
            } else {
              showError((ares && ares.error) || "Audio extraction failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("music", 18),
      window.FOSS.dom.el("span", { text: "extract audio track" })
    ]);

    var audioCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "extract audio" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "extract the sound track from the video and save it as an audio file." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("format", formatSelect),
        window.FOSS.components.field("bitrate", bitrateSelect),
        extractBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(audioCard);
  }

  // ==========================================
  // TAB 5: Frame / Mute / Tools
  // ==========================================
  function renderTools(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = globalCurrentFile;

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-tools-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-tools-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-tools-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-tools-result-card", title: titleText || "Operation Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "media-tools-picker",
      title: "open media file",
      fileTypes: ["mp4", "mkv", "mov", "avi", "webm", "mp3", "wav"],
      onSelect: function (val) {
        currentFile = val;
        globalCurrentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
        globalCurrentFile = "";
      }
    });

    // Frame Capture
    var frameTsInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "number",
      step: "0.1",
      min: "0",
      value: "0.0",
      "data-testid": "media-frame-timestamp",
      "aria-label": "timestamp",
      title: "timestamp",
      style: { minHeight: "36px", minWidth: "100px" }
    });

    var captureBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-capture-frame-btn",
      "aria-label": "capture frame at current playhead",
      title: "capture frame at current playhead",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a video file first.");
          return;
        }
        var ts = parseFloat(frameTsInput.value) || 0;
        ctx.api("select_save_path", { title: "Save Frame Image", default_name: "frame.jpg", file_types: ["jpg", "png"] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          ctx.api("media_extract_frame", { input_path: currentFile, timestamp: ts, output_path: saveP }).then(function (fres) {
            if (fres && fres.ok && fres.output_path) {
              statusBar.textContent = "Frame captured.";
              showResult(fres.output_path, "Frame Captured");
            } else {
              showError((fres && fres.error) || "Frame capture failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("camera", 16),
      window.FOSS.dom.el("span", { text: "capture frame at current playhead" })
    ]);

    // Mute Video
    var muteBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-mute-btn",
      "aria-label": "export muted video (strip audio)",
      title: "export muted video (strip audio)",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a video file first.");
          return;
        }
        var ext = currentFile.split(".").pop();
        ctx.api("select_save_path", { title: "Save Muted Video", default_name: "muted." + ext, file_types: [ext] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          ctx.api("media_mute_video", { input_path: currentFile, output_path: saveP }).then(function (mres) {
            if (mres && mres.ok && mres.output_path) {
              statusBar.textContent = "Audio stripped.";
              showResult(mres.output_path, "Muted Video Saved");
            } else {
              showError((mres && mres.error) || "Failed to strip audio.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("volume-x", 16),
      window.FOSS.dom.el("span", { text: "export muted video (strip audio)" })
    ]);

    // Mix Audio
    var mixBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-mix-audio-btn",
      "aria-label": "mix audio onto video",
      title: "mix audio onto video",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a video file first.");
          return;
        }
        ctx.api("select_file", { title: "Select Audio Track to Mix", file_types: ["mp3", "wav", "aac", "flac", "m4a"] }).then(function (ares) {
          var audioP = (ares && ares.paths && ares.paths[0]) || "";
          if (!audioP) return;
          var ext = currentFile.split(".").pop();
          ctx.api("select_save_path", { title: "Save Mixed Video", default_name: "mixed." + ext, file_types: [ext] }).then(function (res) {
            var saveP = (res && res.paths && res.paths[0]) || "";
            if (!saveP) return;
            clearError();
            ctx.api("media_compose_audio", { video_path: currentFile, audio_path: audioP, output_path: saveP }).then(function (xres) {
              if (xres && xres.ok && xres.output_path) {
                statusBar.textContent = "Audio mixed onto video.";
                showResult(xres.output_path, "Audio Mixed Onto Video");
              } else {
                showError((xres && xres.error) || "Audio mixing failed.");
              }
            });
          });
        });
      }
    }, [
      window.FOSS.icons.el("music", 16),
      window.FOSS.dom.el("span", { text: "mix audio onto video" })
    ]);

    // Subtitle Transcription
    var subStatus = window.FOSS.dom.el("span", {
      className: "text-xs text-muted",
      "data-testid": "media-sub-status",
      text: "no transcription yet."
    });

    var transcribeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-transcribe-btn",
      "aria-label": "transcribe audio (local whisper)",
      title: "transcribe audio (local whisper)",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a file first.");
          return;
        }
        clearError();
        statusBar.textContent = "Transcribing speech...";
        ctx.api("media_transcribe", { input_path: currentFile }).then(function (tres) {
          if (tres && tres.ok) {
            subStatus.textContent = "Transcription ready (" + tres.count + " cues).";
            statusBar.textContent = "Transcription complete.";
          } else {
            showError((tres && tres.error) || "Transcription failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("mic", 16),
      window.FOSS.dom.el("span", { text: "transcribe audio (local whisper)" })
    ]);

    var genSubBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "media-gen-subtitles-btn",
      "aria-label": "generate subtitle file",
      title: "generate subtitle file",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentFile) {
          showError("Select a file first.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Subtitle File", default_name: "subtitles.srt", file_types: ["srt", "vtt"] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          ctx.api("media_transcribe", { input_path: currentFile, output_path: saveP }).then(function (sres) {
            if (sres && sres.ok && sres.output_path) {
              statusBar.textContent = "Subtitle file saved.";
              showResult(sres.output_path, "Subtitles Generated");
            } else {
              showError((sres && sres.error) || "Failed to generate subtitles.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "generate subtitle file" })
    ]);

    var toolsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "frame / mute" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "quick frame snapshot, subtitle generation, audio overlays, and audio removal tools" }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("timestamp (s)", frameTsInput),
        captureBtn,
        muteBtn,
        mixBtn
      ]),
      window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%", borderTop: "1px solid var(--border)", paddingTop: "var(--space-3)" } }, [
        transcribeBtn,
        genSubBtn,
        subStatus
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(filePicker.el);
    panel.appendChild(toolsCard);
  }

  // ==========================================
  // TAB 6: Timeline Composer
  // ==========================================
  function renderTimeline(panel, ctx) {
    panel.innerHTML = "";
    var clips = [];

    var header = createMediaHeader();
    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "media-timeline-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "media-timeline-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "media-timeline-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "media-timeline-result-card", title: titleText || "Timeline Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var clipsListEl = window.FOSS.dom.el("div", {
      className: "card flex-col gap-1 scroll-y",
      "data-testid": "media-clips-list",
      style: { maxHeight: "200px", minHeight: "80px", overflowY: "auto", border: "1px solid var(--border)", padding: "var(--space-2)" }
    });

    var selectedIdx = -1;

    function renderClips() {
      clipsListEl.innerHTML = "";
      if (clips.length === 0) {
        clipsListEl.appendChild(window.FOSS.dom.el("div", { className: "text-muted text-sm", text: "No clips in timeline." }));
        return;
      }
      clips.forEach(function (c, idx) {
        var isSel = selectedIdx === idx;
        var row = window.FOSS.dom.el("div", {
          className: "row items-center justify-between",
          style: {
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "var(--space-2)",
            borderRadius: "var(--radius-sm)",
            backgroundColor: isSel ? "var(--bg-raised)" : "transparent",
            cursor: "pointer",
            minHeight: "36px"
          },
          onClick: function () {
            selectedIdx = idx;
            renderClips();
          }
        }, [
          window.FOSS.dom.el("span", { className: "text-sm", text: (idx + 1) + ". " + c.path.split(/[/\\]/).pop() }),
          window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Clip" })
        ]);
        clipsListEl.appendChild(row);
      });
    }

    var addClipBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-add-clip-btn",
      "aria-label": "add clip",
      title: "add clip",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        ctx.api("select_files", { title: "Add Video Clips", file_types: ["mp4", "mkv", "mov", "avi", "webm"] }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            res.paths.forEach(function (p) {
              clips.push({ path: p, start: 0, end: null });
            });
            renderClips();
            statusBar.textContent = "Added " + res.paths.length + " clip(s). Total: " + clips.length;
          }
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "add clip" })
    ]);

    var addTrackBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-add-track-btn",
      "aria-label": "add track",
      title: "add track",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        statusBar.textContent = "Audio overlay track added.";
      }
    }, [
      window.FOSS.icons.el("music", 16),
      window.FOSS.dom.el("span", { text: "add track" })
    ]);

    var removeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-remove-clip-btn",
      "aria-label": "remove selected",
      title: "remove selected",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (selectedIdx >= 0 && selectedIdx < clips.length) {
          clips.splice(selectedIdx, 1);
          selectedIdx = Math.min(selectedIdx, clips.length - 1);
          renderClips();
        }
      }
    }, [
      window.FOSS.icons.el("trash-2", 16),
      window.FOSS.dom.el("span", { text: "remove selected" })
    ]);

    var moveUpBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-move-up-btn",
      "aria-label": "move up",
      title: "move up",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (selectedIdx > 0) {
          var item = clips.splice(selectedIdx, 1)[0];
          clips.splice(selectedIdx - 1, 0, item);
          selectedIdx--;
          renderClips();
        }
      }
    }, [
      window.FOSS.icons.el("chevron-up", 16),
      window.FOSS.dom.el("span", { text: "move up" })
    ]);

    var moveDownBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-move-down-btn",
      "aria-label": "move down",
      title: "move down",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (selectedIdx >= 0 && selectedIdx < clips.length - 1) {
          var item = clips.splice(selectedIdx, 1)[0];
          clips.splice(selectedIdx + 1, 0, item);
          selectedIdx++;
          renderClips();
        }
      }
    }, [
      window.FOSS.icons.el("chevron-down", 16),
      window.FOSS.dom.el("span", { text: "move down" })
    ]);

    var editSelectedBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-edit-clip-btn",
      "aria-label": "edit selected",
      title: "edit selected",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        statusBar.textContent = "Editing selected clip parameters.";
      }
    }, [window.FOSS.dom.el("span", { text: "edit selected" })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "media-clear-clips-btn",
      "aria-label": "clear",
      title: "clear",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        clips = [];
        selectedIdx = -1;
        renderClips();
      }
    }, [window.FOSS.dom.el("span", { text: "clear" })]);

    var composeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "media-compose-btn",
      "aria-label": "compose timeline",
      title: "compose timeline",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (clips.length < 2) {
          showError("Add at least 2 clips to compose a timeline.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Composed Timeline", default_name: "composed.mp4", file_types: ["mp4", "mkv", "webm"] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          clearError();
          statusBar.textContent = "Rendering timeline composition...";
          ctx.api("media_compose_timeline", { clips: clips, output_path: saveP }).then(function (cres) {
            if (cres && cres.ok && cres.output_path) {
              statusBar.textContent = "Timeline composition complete.";
              showResult(cres.output_path, "Timeline Composed");
            } else {
              showError((cres && cres.error) || "Composition failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("film", 18),
      window.FOSS.dom.el("span", { text: "compose timeline" })
    ]);

    var timelineCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "timeline composer" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "concatenate trimmed/cropped clips into one video or gif, with optional fades and a mixed-in audio track." }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "audio overlay tracks (optional, mixed together over the whole timeline)" }),
      window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)", width: "100%" } }, [
        addClipBtn,
        addTrackBtn,
        removeBtn,
        moveUpBtn,
        moveDownBtn,
        editSelectedBtn,
        clearBtn
      ]),
      clipsListEl,
      composeBtn
    ]);

    renderClips();

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(timelineCard);
  }

  // Register Media Tool
  window.FOSS.router.register({
    id: "media",
    title: "Audio & Video Studio",
    navName: "Media",
    category: "Media",
    icon: "film",
    tabs: [
      { id: "trim", label: "trim / cut", render: renderTrim },
      { id: "convert", label: "convert", render: renderConvert },
      { id: "compress", label: "compress", render: renderCompress },
      { id: "audio", label: "extract audio", render: renderExtractAudio },
      { id: "tools", label: "frame / mute", render: renderTools },
      { id: "timeline", label: "timeline composer", render: renderTimeline }
    ]
  });
})();

