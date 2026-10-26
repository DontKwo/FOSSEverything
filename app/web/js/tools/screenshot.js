// Screenshot & Snipping Tool: full screen desktop captures, custom snip regions, delay countdown, and export.
window.FOSS = window.FOSS || {};

(function () {
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
  }

  function renderCapture(panel, ctx) {
    panel.innerHTML = "";
    var currentDataUrl = "";
    var captureMode = "full"; // "full" or "region"

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Screenshot & Screen Snipping" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "capture desktop screen or select a custom area." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "screenshot-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "screenshot-error", hidden: true }, [
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

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "screenshot-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "screenshot-result-card", title: titleText || "Screenshot Captured", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Mode Radios
    var fullRadio = window.FOSS.dom.el("input", {
      type: "radio",
      name: "screenshot-mode",
      value: "full",
      checked: true,
      "data-testid": "screenshot-mode-full",
      "aria-label": "full screen",
      title: "full screen",
      style: { cursor: "pointer" },
      onChange: function (e) {
        if (e.target.checked) captureMode = "full";
      }
    });

    var fullLabel = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--text-sm)", cursor: "pointer" }
    }, [
      fullRadio,
      window.FOSS.dom.el("span", { text: "full screen" })
    ]);

    var regionRadio = window.FOSS.dom.el("input", {
      type: "radio",
      name: "screenshot-mode",
      value: "region",
      "data-testid": "screenshot-mode-region",
      "aria-label": "select region / snip (interactive)",
      title: "select region / snip (interactive)",
      style: { cursor: "pointer" },
      onChange: function (e) {
        if (e.target.checked) captureMode = "region";
      }
    });

    var regionLabel = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--text-sm)", cursor: "pointer" }
    }, [
      regionRadio,
      window.FOSS.dom.el("span", { text: "select region / snip (interactive)" })
    ]);

    var modeGroup = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }
    }, [fullLabel, regionLabel]);

    // Delay Countdown
    var delaySelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "screenshot-delay",
      "aria-label": "delay countdown",
      title: "delay countdown",
      style: { minHeight: "36px", minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "0", text: "No delay (Instant)" }),
      window.FOSS.dom.el("option", { value: "1", text: "1 second" }),
      window.FOSS.dom.el("option", { value: "3", text: "3 seconds" }),
      window.FOSS.dom.el("option", { value: "5", text: "5 seconds" })
    ]);

    var previewCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { border: "1px solid var(--border)", padding: "var(--space-3)", width: "100%", minHeight: "200px", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "var(--bg-raised)" }
    });

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "screenshot-preview-img",
      alt: "Captured Screenshot",
      style: {
        maxWidth: "100%",
        maxHeight: "340px",
        objectFit: "contain",
        display: "none",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-md)"
      }
    });

    var previewPlaceholder = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center",
      "data-testid": "screenshot-placeholder",
      text: "No screenshot captured yet. Choose capture mode and click Capture."
    });

    previewCard.appendChild(previewPlaceholder);
    previewCard.appendChild(previewImg);

    var captureBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "screenshot-capture-btn",
      "aria-label": "capture",
      title: "capture",
      type: "button",
      style: { minHeight: "36px", minWidth: "100px" },
      onClick: function () {
        clearError();
        var sec = parseInt(delaySelect.value, 10) || 0;
        statusBar.textContent = sec > 0 ? "Waiting " + sec + "s countdown..." : "Capturing screen...";

        var method = captureMode === "region" ? "screenshot_capture_region" : "screenshot_capture_full";
        var params = { delay: sec };
        if (captureMode === "region") {
          params.x1 = 100;
          params.y1 = 100;
          params.x2 = 900;
          params.y2 = 700;
        }

        ctx.api(method, params).then(function (res) {
          if (res && res.ok && res.data_url) {
            currentDataUrl = res.data_url;
            previewImg.src = res.data_url;
            previewImg.style.display = "block";
            previewPlaceholder.style.display = "none";
            statusBar.textContent = "Screenshot captured (" + res.width + "x" + res.height + ").";
            showResult(res.output_path || "screenshot.png", "Screenshot Captured");
          } else {
            showError((res && res.error) || "Screenshot capture failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("camera", 18),
      window.FOSS.dom.el("span", { text: "capture" })
    ]);

    var cancelBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "screenshot-cancel-btn",
      "aria-label": "cancel",
      title: "cancel",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        currentDataUrl = "";
        previewImg.src = "";
        previewImg.style.display = "none";
        previewPlaceholder.style.display = "block";
        statusBar.textContent = "Capture cancelled.";
      }
    }, [window.FOSS.dom.el("span", { text: "cancel" })]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "screenshot-save-btn",
      "aria-label": "Save Screenshot",
      title: "Save Screenshot",
      type: "button",
      style: { minHeight: "36px" },
      onClick: function () {
        if (!currentDataUrl) {
          showError("No screenshot to save.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Screenshot", default_name: "screenshot.png", file_types: ["png"] }).then(function (res) {
          var saveP = (res && res.paths && res.paths[0]) || "";
          if (!saveP) return;
          ctx.api("save_file_text", { path: saveP, content: currentDataUrl }).then(function () {
            statusBar.textContent = "Saved screenshot to " + saveP;
            showResult(saveP, "Screenshot Saved");
          });
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save Image" })
    ]);

    var controlsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { width: "100%", border: "1px solid var(--border)", padding: "var(--space-3)" }
    });

    var actionRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      modeGroup,
      window.FOSS.components.field("delay countdown", delaySelect),
      captureBtn,
      cancelBtn,
      saveBtn
    ]);

    controlsCard.appendChild(actionRow);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(controlsCard);
    panel.appendChild(previewCard);
  }

  window.FOSS.router.register({
    id: "screenshot",
    title: "Screenshot & Snipping",
    navName: "Screenshot",
    category: "Visuals",
    icon: "camera",
    tabs: [
      { id: "capture", label: "Capture", render: renderCapture }
    ]
  });
})();

