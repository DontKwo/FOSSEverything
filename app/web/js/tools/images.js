// AI Background Removal and Replacement Tool.
window.FOSS = window.FOSS || {};

(function () {
  function renderBackground(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "AI Background Removal" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "All models run locally. A selected model may download once, then remains on this computer."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "images-bg-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "images-bg-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "images-bg-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "images-bg-result-card",
        title: titleText || "Background Removed",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var mainCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: "width: 100%; max-width: 100%; min-width: 0;"
    });

    var filePicker = window.FOSS.components.filePicker({
      testid: "images-bg-picker",
      title: "Select Image for Background Removal",
      fileTypes: ["png", "jpg", "jpeg", "webp"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + (val ? val.split(/[/\\]/).pop() : "");
      },
      onClear: function () {
        currentFile = "";
      }
    });

    var modelSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "images-bg-model-select",
      "aria-label": "Background Model",
      title: "Background Model",
      style: "min-width: 160px;"
    }, [
      window.FOSS.dom.el("option", { value: "u2netp", text: "U2Net-P (Fast Lightweight)" }),
      window.FOSS.dom.el("option", { value: "u2net", text: "U2Net (Balanced Standard)" }),
      window.FOSS.dom.el("option", { value: "isnet-general-use", text: "ISNet (General Use)" }),
      window.FOSS.dom.el("option", { value: "birefnet-general", text: "BiRefNet (General, High Precision)" }),
      window.FOSS.dom.el("option", { value: "birefnet-portrait", text: "BiRefNet (Portrait)" })
    ]);

    var removeBgChk = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "aria-label": "Remove Background (Local AI Model)",
      title: "Remove Background (Local AI Model)"
    });

    var removeBgLbl = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: "gap: var(--space-2); cursor: pointer;"
    }, [
      removeBgChk,
      window.FOSS.dom.el("span", { text: "Remove Background (Local AI Model)" })
    ]);

    var removeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "images-bg-btn",
      "aria-label": "Remove Background",
      title: "Remove Background",
      onClick: function () {
        if (!currentFile) return showError("Select an image first.");
        window.FOSS.api("select_save_path", {
          title: "Save Transparent PNG",
          default_name: "nobg.png",
          filters: [{ name: "PNG Image", extensions: ["png"] }]
        }).then(function (res) {
          var outP = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outP) return;
          statusBar.textContent = "Running background removal model...";
          window.FOSS.api("images_remove_background", {
            file_path: currentFile,
            model: modelSelect.value,
            output_path: outP
          }).then(function () {
            showResult(outP, "Transparent Image Saved");
            statusBar.textContent = "Saved to " + outP;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("sparkles", 16),
      window.FOSS.dom.el("span", { text: "Remove Background" })
    ]);

    var batchBgBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "images-batch-bg-btn",
      "aria-label": "Batch Background Removal",
      title: "Batch Background Removal",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Select Images for Batch Background Removal",
          file_types: ["png", "jpg", "jpeg"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            window.FOSS.api("select_directory", { title: "Select Output Folder" }).then(function (dRes) {
              var outD = dRes && dRes.paths && dRes.paths.length > 0 ? dRes.paths[0] : "";
              if (!outD) return;
              statusBar.textContent = "Processing " + res.paths.length + " files...";
              window.FOSS.api("images_batch_process", {
                file_paths: res.paths,
                output_dir: outD,
                remove_background: true,
                bg_model: modelSelect.value
              }).then(function () {
                showResult(outD, "Batch Background Removal Complete");
              });
            });
          }
        });
      }
    }, [
      window.FOSS.icons.el("layers", 16),
      window.FOSS.dom.el("span", { text: "Batch Background Removal" })
    ]);

    var bgControls = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: "display: flex; flex-wrap: wrap; gap: var(--space-3); width: 100%;"
    }, [
      window.FOSS.components.field("Model", modelSelect),
      removeBgLbl,
      removeBtn,
      batchBgBtn
    ]);

    mainCard.appendChild(filePicker.el);
    mainCard.appendChild(bgControls);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(mainCard);
  }

  window.FOSS.router.register({
    id: "images",
    title: "Image Tools",
    navName: "Images",
    category: "Visuals",
    icon: "image",
    tabs: [
      { id: "background", label: "Background", render: renderBackground }
    ]
  });
})();
