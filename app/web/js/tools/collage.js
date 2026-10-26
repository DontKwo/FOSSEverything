// Image Collage Builder: grid compositing, layout presets, captions, watermarks, and export.
window.FOSS = window.FOSS || {};

(function () {
  function renderMain(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-collage");

    var currentImages = [];

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Image Collage Builder" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Arrange multiple images into a grid. Export as PNG, JPEG, or WEBP."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "collage-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "collage-error-banner"
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

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "collage-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "collage-result-card",
        title: titleText || "Collage Saved",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Card 1: Images List (Group: images)
    var imagesCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    imagesCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Images" }));

    var imagesList = window.FOSS.dom.el("div", {
      className: "flex flex-col gap-2",
      "data-testid": "collage-images-list"
    });
    imagesList.innerHTML = '<div class="text-xs text-muted p-2">No images added. Click Add Images to select photos.</div>';

    var addImagesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "collage-add-images",
      "aria-label": "Add images",
      title: "Add images",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          for (var i = 0; i < res.paths.length; i++) {
            currentImages.push(res.paths[i]);
          }
          renderImagesList();
          updatePreview();
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Add Images" })
    ]);

    var clearImagesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-clear-images",
      "aria-label": "Clear all images",
      title: "Clear all images",
      type: "button",
      onClick: function () {
        currentImages = [];
        renderImagesList();
        previewContainer.innerHTML = '<div class="text-sm text-muted p-4 text-center">No collage preview yet. Add images to generate preview.</div>';
        statusBar.textContent = "Ready";
      }
    }, [
      window.FOSS.icons.el("trash", 16),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var imagesToolbar = window.FOSS.dom.el("div", { className: "row" }, [addImagesBtn, clearImagesBtn]);
    imagesCard.appendChild(imagesToolbar);
    imagesCard.appendChild(imagesList);

    function renderImagesList() {
      imagesList.innerHTML = "";
      if (!currentImages.length) {
        imagesList.innerHTML = '<div class="text-xs text-muted p-2">No images added. Click Add Images to select photos.</div>';
        return;
      }
      for (var i = 0; i < currentImages.length; i++) {
        var p = currentImages[i];
        var item = window.FOSS.dom.el("div", {
          className: "flex items-center justify-between p-2 rounded bg-neutral-surface text-xs font-mono"
        }, [
          window.FOSS.dom.el("span", { className: "grow", "data-truncate-ok": "true", title: p, text: p }),
          window.FOSS.dom.el("button", {
            className: "btn btn-secondary btn-sm ml-2",
            "aria-label": "Remove image",
            title: "Remove image",
            type: "button",
            "data-index": i,
            onClick: function (e) {
              var idx = parseInt(e.currentTarget.getAttribute("data-index"), 10);
              currentImages.splice(idx, 1);
              renderImagesList();
              updatePreview();
            }
          }, [
            window.FOSS.icons.el("trash", 14)
          ])
        ]);
        imagesList.appendChild(item);
      }
    }

    // Card 2: Layout settings (Group: layout settings)
    var layoutCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    layoutCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Layout settings" }));

    // Presets
    var presetSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "collage-preset-select",
      "aria-label": "Preset layout",
      title: "Preset layout",
      onChange: function () {
        var val = presetSelect.value;
        if (val === "2col") colsSelect.value = "2";
        else if (val === "3col") colsSelect.value = "3";
        else if (val === "4col") colsSelect.value = "4";
        else if (val === "1col") colsSelect.value = "1";
        updatePreview();
      }
    }, [
      window.FOSS.dom.el("option", { value: "2col", text: "Side-by-side 2-up (2 columns)" }),
      window.FOSS.dom.el("option", { value: "3col", text: "Triptych (3 columns)" }),
      window.FOSS.dom.el("option", { value: "3col", text: "Instagram grid (3x3)" }),
      window.FOSS.dom.el("option", { value: "2col", text: "Product grid (2x2)" }),
      window.FOSS.dom.el("option", { value: "1col", text: "Story strip (1 column)" }),
      window.FOSS.dom.el("option", { value: "2col", text: "Wide panel (2x1)" })
    ]);

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0 w-24", text: "Preset" }),
      presetSelect
    ]));

    // Columns
    var colsSelect = window.FOSS.dom.el("select", {
      className: "select w-28",
      "data-testid": "collage-columns-select",
      "aria-label": "Columns count",
      title: "Columns count",
      onChange: updatePreview
    }, [
      window.FOSS.dom.el("option", { value: "1", text: "1" }),
      window.FOSS.dom.el("option", { value: "2", selected: true, text: "2" }),
      window.FOSS.dom.el("option", { value: "3", text: "3" }),
      window.FOSS.dom.el("option", { value: "4", text: "4" }),
      window.FOSS.dom.el("option", { value: "5", text: "5" }),
      window.FOSS.dom.el("option", { value: "6", text: "6" })
    ]);

    // Fit mode
    var fitSelect = window.FOSS.dom.el("select", {
      className: "select w-32",
      "data-testid": "collage-fit-select",
      "aria-label": "Fit mode",
      title: "Fit mode",
      onChange: updatePreview
    }, [
      window.FOSS.dom.el("option", { value: "cover", text: "cover" }),
      window.FOSS.dom.el("option", { value: "contain", text: "contain" }),
      window.FOSS.dom.el("option", { value: "stretch", text: "stretch" })
    ]);

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Columns:" }),
      colsSelect,
      window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Fit mode:" }),
      fitSelect
    ]));

    // Corner radius & Padding
    var cornerRadiusInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-24",
      "data-testid": "collage-corner-radius",
      "aria-label": "Corner radius",
      title: "Corner radius (pixels)",
      value: 0,
      min: 0,
      max: 100,
      onInput: updatePreview
    });

    var paddingInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input w-24",
      "data-testid": "collage-padding-input",
      "aria-label": "Cell padding",
      title: "Cell padding",
      value: 12,
      min: 0,
      max: 60,
      onInput: updatePreview
    });

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Padding:" }),
      paddingInput,
      window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Corner Radius:" }),
      cornerRadiusInput
    ]));

    // Background color
    var hiddenColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      hidden: true,
      "aria-label": "Hidden color picker",
      title: "Hidden color picker",
      value: "#f0f0f0",
      onChange: function () {
        bgColorInput.value = hiddenColorPicker.value;
        updatePreview();
      }
    });

    var bgColorInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input w-28 font-mono text-sm",
      "data-testid": "collage-bg-color",
      "aria-label": "Background color hex",
      title: "Background color hex",
      value: "#f0f0f0",
      onInput: updatePreview
    });

    var pickColorBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Pick background color",
      title: "Pick background color",
      type: "button",
      onClick: function () {
        hiddenColorPicker.click();
      }
    }, [
      window.FOSS.icons.el("palette", 16),
      window.FOSS.dom.el("span", { text: "Pick background color" })
    ]);

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted", text: "Background:" }),
      bgColorInput,
      pickColorBtn,
      hiddenColorPicker
    ]));

    // Captions & Watermark
    var captionsCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      id: "collage-captions-checkbox",
      className: "checkbox",
      "data-testid": "collage-captions-check",
      "aria-label": "Add filenames as captions",
      title: "Add filenames as captions",
      onChange: updatePreview
    });

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", {
        htmlFor: "collage-captions-checkbox",
        className: "flex items-center gap-2 text-sm cursor-pointer"
      }, [
        captionsCheck,
        window.FOSS.dom.el("span", { text: "add filenames as captions" })
      ])
    ]));

    var watermarkInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "collage-watermark-input",
      "aria-label": "Watermark text",
      title: "Optional watermark text",
      placeholder: "Optional watermark stamp",
      onInput: updatePreview
    });

    layoutCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0 w-24", text: "Watermark" }),
      watermarkInput
    ]));

    // Card 3: Collage Preview & Export
    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    previewCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Collage preview" }));

    var previewContainer = window.FOSS.dom.el("div", {
      className: "flex items-center justify-center p-4 rounded bg-neutral-surface min-h-48 overflow-hidden",
      "data-testid": "collage-preview-display"
    });
    previewContainer.innerHTML = '<div class="text-sm text-muted text-center">No collage preview yet. Add images to generate preview.</div>';
    previewCard.appendChild(previewContainer);

    var previewBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "collage-preview-btn",
      "aria-label": "Generate collage preview",
      title: "Generate collage preview",
      type: "button",
      onClick: updatePreview
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Generate collage preview" })
    ]);

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "collage-save-btn",
      "aria-label": "Save collage",
      title: "Save collage",
      type: "button",
      onClick: function () {
        if (!currentImages.length) {
          showError("Please add images before saving collage.");
          return;
        }
        clearError();
        statusBar.textContent = "Saving collage...";
        window.FOSS.api("collage_create", {
          image_paths: currentImages,
          columns: parseInt(colsSelect.value, 10) || 2,
          fit_mode: fitSelect.value,
          padding: parseInt(paddingInput.value, 10) || 12,
          corner_radius: parseInt(cornerRadiusInput.value, 10) || 0,
          bg_color: bgColorInput.value,
          add_captions: captionsCheck.checked,
          watermark_text: watermarkInput.value.trim() || undefined
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Collage saved: " + res.output_path;
            showResult(res.output_path, "Collage Saved Successfully");
          } else {
            showError("Failed to save collage.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save collage" })
    ]);

    previewCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [previewBtn, saveBtn]));

    function updatePreview() {
      if (!currentImages.length) {
        previewContainer.innerHTML = '<div class="text-sm text-muted text-center">No collage preview yet. Add images to generate preview.</div>';
        statusBar.textContent = "Ready";
        return;
      }
      statusBar.textContent = "Rendering preview...";
      window.FOSS.api("collage_preview", {
        image_paths: currentImages,
        columns: parseInt(colsSelect.value, 10) || 2,
        fit_mode: fitSelect.value,
        padding: parseInt(paddingInput.value, 10) || 12,
        corner_radius: parseInt(cornerRadiusInput.value, 10) || 0,
        bg_color: bgColorInput.value,
        add_captions: captionsCheck.checked,
        watermark_text: watermarkInput.value.trim() || undefined
      }).then(function (res) {
        if (res && res.data_url) {
          previewContainer.innerHTML = "";
          var img = window.FOSS.dom.el("img", {
            src: res.data_url,
            alt: "Collage preview",
            className: "max-w-full h-auto rounded border border-border"
          });
          previewContainer.appendChild(img);
          statusBar.textContent = "Preview updated (" + currentImages.length + " photos).";
        }
      });
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(imagesCard);
    panel.appendChild(layoutCard);
    panel.appendChild(previewCard);
  }

  window.FOSS.router.register({
    id: "collage",
    title: "Image Collage Builder",
    navName: "Collage",
    category: "system",
    icon: "grid",
    tabs: [
      { id: "main", label: "Collage Builder", render: renderMain }
    ]
  });
})();
