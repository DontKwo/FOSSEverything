// QR Codes and Barcodes workspace: generator, 1D barcodes, file and webcam decoding, SVG, and label sheets.
window.FOSS = window.FOSS || {};

(function () {
  var activeCleanup = null;

  var RASTER_TYPES = [
    { name: "PNG Image (*.png)", extensions: ["png"] },
    { name: "SVG Vector Image (*.svg)", extensions: ["svg"] },
    { name: "JPEG Image (*.jpg)", extensions: ["jpg", "jpeg"] },
    { name: "WebP Image (*.webp)", extensions: ["webp"] },
    { name: "PDF Document (*.pdf)", extensions: ["pdf"] }
  ];
  var BARCODE_TYPES = [
    { name: "PNG Image (*.png)", extensions: ["png"] },
    { name: "SVG Vector Image (*.svg)", extensions: ["svg"] },
    { name: "JPEG Image (*.jpg)", extensions: ["jpg", "jpeg"] }
  ];
  var SVG_TYPES = [{ name: "SVG Vector Image (*.svg)", extensions: ["svg"] }];
  var PDF_TYPES = [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }];
  var ICS_TYPES = [{ name: "iCalendar File (*.ics)", extensions: ["ics"] }];

  var QUICK_TYPES = [
    { id: "url", label: "URL" },
    { id: "text", label: "Plain Text" },
    { id: "vcard", label: "Contact vCard" },
    { id: "wifi", label: "Wi-Fi Network" }
  ];

  var PAYLOAD_TYPES = [
    { id: "url", label: "URL / Web Link" },
    { id: "text", label: "Plain Text" },
    { id: "vcard", label: "Contact Card (vCard)" },
    { id: "wifi", label: "Wi-Fi Network" },
    { id: "mecard", label: "Business Card (MeCard)" },
    { id: "email", label: "Email Address" },
    { id: "phone", label: "Phone Number" },
    { id: "sms", label: "SMS Message" },
    { id: "whatsapp", label: "WhatsApp Message" },
    { id: "geo", label: "Geo Location" },
    { id: "calendar", label: "Calendar Event" },
    { id: "asset", label: "Asset / Inventory Tag" }
  ];

  var ECC_OPTIONS = [
    { value: "L", label: "L - Low (~7% recovery)" },
    { value: "M", label: "M - Standard (~15% recovery)" },
    { value: "Q", label: "Q - Medium-High (~25% recovery)" },
    { value: "H", label: "H - Highest (~30% recovery, best with logos)" }
  ];

  var FIELD_DEFS = {
    url: [{ key: "text", label: "Web URL", value: "https://github.com/DontKwo/FOSSEverything", placeholder: "https://example.com", testid: "qr-text-input" }],
    text: [{ key: "text", label: "Plain Text", kind: "textarea", placeholder: "Enter arbitrary text or notes", testid: "qr-text-input" }],
    vcard: [
      { key: "name", label: "Full Name", placeholder: "Full Name" },
      { key: "org", label: "Organization", placeholder: "Organization / Company" },
      { key: "title", label: "Job Title", placeholder: "Job Title" },
      { key: "phone", label: "Phone", placeholder: "Phone Number" },
      { key: "email", label: "Email", placeholder: "Email Address" },
      { key: "url", label: "Website", placeholder: "https://example.com" }
    ],
    wifi: [
      { key: "ssid", label: "SSID", placeholder: "Network SSID" },
      { key: "password", label: "Password", placeholder: "Wi-Fi Password" },
      {
        key: "security",
        label: "Security",
        kind: "select",
        options: [["WPA", "WPA/WPA2/WPA3"], ["WEP", "WEP"], ["nopass", "Open (No Password)"]]
      },
      { key: "hidden", label: "Hidden Network", kind: "checkbox" }
    ],
    mecard: [
      { key: "name", label: "Full Name", placeholder: "Full Name" },
      { key: "phone", label: "Phone", placeholder: "Phone Number" },
      { key: "email", label: "Email", placeholder: "Email Address" },
      { key: "org", label: "Organization", placeholder: "Organization / Company" },
      { key: "url", label: "Website", placeholder: "https://example.com" },
      { key: "address", label: "Address", placeholder: "Street, City" }
    ],
    email: [
      { key: "email", label: "Email Address", placeholder: "name@example.com" },
      { key: "subject", label: "Subject", placeholder: "Subject" },
      { key: "body", label: "Message", kind: "textarea", placeholder: "Message body" }
    ],
    phone: [{ key: "phone", label: "Phone Number", placeholder: "+1 555 0100" }],
    sms: [
      { key: "phone", label: "Phone Number", placeholder: "+1 555 0100" },
      { key: "message", label: "Message", kind: "textarea", placeholder: "Message text" }
    ],
    whatsapp: [
      { key: "phone", label: "Phone Number", placeholder: "+1 555 0100" },
      { key: "message", label: "Message", kind: "textarea", placeholder: "Message text" }
    ],
    geo: [
      { key: "lat", label: "Latitude", value: "40.7128", placeholder: "40.7128" },
      { key: "lon", label: "Longitude", value: "-74.0060", placeholder: "-74.0060" }
    ],
    calendar: [
      { key: "title", label: "Event Title", placeholder: "Team sync" },
      { key: "start_time", label: "Starts", kind: "datetime" },
      { key: "end_time", label: "Ends", kind: "datetime" },
      { key: "location", label: "Location", placeholder: "Room or address" },
      { key: "description", label: "Description", kind: "textarea", placeholder: "Details" }
    ],
    asset: [
      { key: "asset_id", label: "Asset ID", placeholder: "abc123" },
      { key: "category", label: "Category", placeholder: "Laptop" },
      { key: "location", label: "Location", placeholder: "Building A" },
      { key: "owner", label: "Owner", placeholder: "Owner name" },
      { key: "notes", label: "Notes", kind: "textarea", placeholder: "Notes" }
    ]
  };

  var sharedState = {
    payloadType: "url",
    fgColor: "#000000",
    bgColor: "#ffffff",
    logoPath: "",
    lastDecodedItems: []
  };

  function runCleanup() {
    if (activeCleanup) {
      var fn = activeCleanup;
      activeCleanup = null;
      fn();
    }
  }

  function callApi(method, params) {
    return window.FOSS.api(method, params).then(function (res) {
      if (res && res.ok === false) throw new Error(res.error || "Request failed");
      return res;
    });
  }

  function errText(err) {
    return err && err.message ? err.message : String(err);
  }

  function toolDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("qr", key, fallback);
  }

  function savePath(title, baseName, fileTypes) {
    return window.FOSS.api("select_save_path", {
      title: title,
      default_name: baseName,
      file_types: fileTypes
    }).then(function (res) {
      if (!res || res.cancelled) return "";
      return res.path || (res.paths && res.paths[0]) || "";
    });
  }

  function extOf(path) {
    var dot = String(path).lastIndexOf(".");
    return dot === -1 ? "" : String(path).substring(dot + 1).toLowerCase();
  }

  function copyTextToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
      return;
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.setProperty("position", "fixed");
    ta.style.setProperty("opacity", "0");
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  function copyImageToClipboard(dataUrl) {
    if (!dataUrl) return Promise.reject(new Error("No image data"));
    if (navigator.clipboard && window.ClipboardItem && fetch) {
      return fetch(dataUrl)
        .then(function (res) { return res.blob(); })
        .then(function (blob) {
          var item = new ClipboardItem({ "image/png": blob });
          return navigator.clipboard.write([item]);
        })
        .catch(function () {
          copyTextToClipboard(dataUrl);
        });
    }
    copyTextToClipboard(dataUrl);
    return Promise.resolve();
  }

  function makeChrome() {
    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "qr-status",
      text: "Ready"
    });
    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger",
      "data-testid": "qr-error-banner",
      hidden: true
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);
    var resultHost = window.FOSS.dom.el("div", { "data-testid": "qr-result", hidden: true });

    return {
      statusBar: statusBar,
      errorBanner: errorBanner,
      resultHost: resultHost,
      showError: function (msg) {
        var span = errorBanner.querySelector(".banner-msg");
        if (span) span.textContent = msg;
        errorBanner.removeAttribute("hidden");
        statusBar.textContent = "Error: " + msg;
      },
      clearError: function () {
        errorBanner.setAttribute("hidden", "true");
      },
      showResult: function (path, titleText) {
        resultHost.innerHTML = "";
        resultHost.appendChild(window.FOSS.components.resultCard({
          testid: "qr-result-card",
          title: titleText || "Export Complete",
          outputPath: path
        }));
        resultHost.removeAttribute("hidden");
      }
    };
  }

  function makeWorkbench(sidebar, stage) {
    return window.FOSS.dom.el("div", { className: "split resizable qr-workbench" }, [
      sidebar,
      window.FOSS.components.splitDivider({ vertical: true }),
      stage
    ]);
  }

  function makePreviewBox(testid, altText) {
    var img = window.FOSS.dom.el("img", {
      className: "qr-preview-img hidden",
      "data-testid": testid,
      alt: altText
    });
    var empty = window.FOSS.dom.el("div", { className: "text-muted text-sm text-center", text: "Generating preview..." });
    var box = window.FOSS.dom.el("div", { className: "qr-preview-box" }, [img, empty]);
    return {
      box: box,
      show: function (dataUrl) {
        img.src = dataUrl;
        img.classList.remove("hidden");
        empty.classList.add("hidden");
      }
    };
  }

  function colorRow(initial, label, onValue) {
    var textInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input qr-input-narrow",
      value: initial,
      "aria-label": label + " hex",
      title: label + " hex",
      onInput: function () {
        picker.value = textInput.value;
        onValue(textInput.value);
      }
    });
    var picker = window.FOSS.dom.el("input", {
      type: "color",
      value: initial,
      className: "qr-color-picker",
      "aria-label": "Pick " + label,
      title: "Pick " + label,
      onInput: function () {
        textInput.value = picker.value;
        onValue(picker.value);
      }
    });
    return window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [textInput, picker]);
  }

  function renderQRTab(panel) {
    runCleanup();
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "qr-page");

    var chrome = makeChrome();
    var currentPayload = "";
    var currentImageDataUrl = "";
    var refreshTimer = null;
    var refreshSeq = 0;

    var fieldInputs = {};
    Object.keys(FIELD_DEFS).forEach(function (typeId) {
      fieldInputs[typeId] = {};
      FIELD_DEFS[typeId].forEach(function (def) {
        fieldInputs[typeId][def.key] = buildFieldInput(def);
      });
    });

    function buildFieldInput(def) {
      var attrs = { "aria-label": def.label, title: def.label };
      if (def.testid) attrs["data-testid"] = def.testid;
      if (def.placeholder) attrs.placeholder = def.placeholder;
      var input;
      if (def.kind === "textarea") {
        attrs.className = "input";
        attrs.rows = "3";
        attrs.onInput = scheduleRefresh;
        input = window.FOSS.dom.el("textarea", attrs);
      } else if (def.kind === "select") {
        attrs.className = "input";
        attrs.onChange = scheduleRefresh;
        input = window.FOSS.dom.el("select", attrs, def.options.map(function (opt) {
          return window.FOSS.dom.el("option", { value: opt[0], text: opt[1] });
        }));
      } else if (def.kind === "checkbox") {
        attrs.type = "checkbox";
        attrs.onChange = scheduleRefresh;
        input = window.FOSS.dom.el("input", attrs);
      } else {
        attrs.className = "input";
        attrs.type = def.kind === "datetime" ? "datetime-local" : "text";
        attrs.onInput = scheduleRefresh;
        input = window.FOSS.dom.el("input", attrs);
      }
      if (def.value && def.kind !== "checkbox") input.value = def.value;
      return input;
    }

    function collectFields(typeId) {
      var values = {};
      FIELD_DEFS[typeId].forEach(function (def) {
        var input = fieldInputs[typeId][def.key];
        values[def.key] = def.kind === "checkbox" ? input.checked : input.value;
      });
      if (typeId === "geo") {
        values.lat = parseFloat(values.lat) || 0;
        values.lon = parseFloat(values.lon) || 0;
      }
      return values;
    }

    var typeCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "qr-templates-group"
    });
    var typeTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Type" });
    var quickRow = window.FOSS.dom.el("div", { className: "qr-type-row", "data-testid": "qr-segmented-types" });
    var quickButtons = {};

    var typeSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-type-select",
      "aria-label": "Payload type",
      title: "Payload type",
      onChange: function () { setPayloadType(typeSelect.value); }
    }, PAYLOAD_TYPES.map(function (pt) {
      return window.FOSS.dom.el("option", { value: pt.id, text: pt.label });
    }));

    QUICK_TYPES.forEach(function (qt) {
      var btn = window.FOSS.dom.el("button", {
        className: "btn btn-sm btn-secondary",
        type: "button",
        "data-testid": "qr-type-" + qt.id,
        text: qt.label,
        onClick: function () { setPayloadType(qt.id); }
      });
      quickButtons[qt.id] = btn;
      quickRow.appendChild(btn);
    });

    typeCard.appendChild(typeTitle);
    typeCard.appendChild(quickRow);
    typeCard.appendChild(window.FOSS.components.field("All payload types", typeSelect));

    var contentCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-content-details"
    });
    var contentBody = window.FOSS.dom.el("div", { className: "flex-col gap-2" });
    contentCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Content Details" }));
    contentCard.appendChild(contentBody);

    function updateContentFields() {
      contentBody.innerHTML = "";
      var typeId = sharedState.payloadType;
      FIELD_DEFS[typeId].forEach(function (def) {
        var input = fieldInputs[typeId][def.key];
        if (def.kind === "checkbox") {
          contentBody.appendChild(window.FOSS.dom.el("label", { className: "row items-center gap-2" }, [
            input,
            window.FOSS.dom.el("span", { text: def.label })
          ]));
        } else {
          contentBody.appendChild(window.FOSS.components.field(def.label, input));
        }
      });
    }

    function setPayloadType(typeId) {
      sharedState.payloadType = typeId;
      typeSelect.value = typeId;
      QUICK_TYPES.forEach(function (qt) {
        quickButtons[qt.id].className = "btn btn-sm " + (qt.id === typeId ? "btn-primary" : "btn-secondary");
      });
      icsBtn.classList.toggle("hidden", typeId !== "calendar");
      updateContentFields();
      scheduleRefresh();
    }

    var styleCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-styling-group"
    });
    var eccSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-ecc-select",
      "aria-label": "Error Correction",
      title: "Error Correction",
      onChange: scheduleRefresh
    }, ECC_OPTIONS.map(function (opt) {
      return window.FOSS.dom.el("option", { value: opt.value, text: opt.label });
    }));
    eccSelect.value = String(toolDefault("error_correction", "M"));

    var exportSizeInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input qr-input-narrow",
      min: "64",
      max: "4096",
      step: "64",
      value: String(toolDefault("export_resolution", 512)),
      "data-testid": "qr-export-size",
      "aria-label": "Export size in pixels",
      title: "Export size in pixels",
      onInput: updateInfoLabel
    });

    styleCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Styling & Resolution" }));
    styleCard.appendChild(window.FOSS.components.field("Foreground Color", colorRow(sharedState.fgColor, "foreground color", function (v) {
      sharedState.fgColor = v;
      scheduleRefresh();
    })));
    styleCard.appendChild(window.FOSS.components.field("Background Color", colorRow(sharedState.bgColor, "background color", function (v) {
      sharedState.bgColor = v;
      scheduleRefresh();
    })));
    styleCard.appendChild(window.FOSS.components.field("Error Correction", eccSelect));
    styleCard.appendChild(window.FOSS.components.field("Export Size (px)", exportSizeInput));

    var logoStatusLabel = window.FOSS.dom.el("span", {
      className: "text-sm text-muted",
      "data-truncate-ok": "true",
      text: sharedState.logoPath ? sharedState.logoPath.split(/[/\\]/).pop() : "No logo selected"
    });
    var chooseLogoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      type: "button",
      "data-testid": "qr-choose-logo-btn",
      "aria-label": "Choose Logo",
      title: "Choose Logo",
      onClick: function () {
        window.FOSS.api("select_file", {
          title: "Select Logo Image",
          file_types: ["png", "jpg", "jpeg", "webp"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            sharedState.logoPath = res.paths[0];
            logoStatusLabel.textContent = sharedState.logoPath.split(/[/\\]/).pop();
            scheduleRefresh();
          }
        }).catch(function (err) {
          chrome.showError(errText(err));
        });
      }
    }, [
      window.FOSS.icons.el("image", 14),
      window.FOSS.dom.el("span", { text: "Choose Logo" })
    ]);
    var clearLogoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      type: "button",
      "data-testid": "qr-clear-logo-btn",
      "aria-label": "Clear logo",
      title: "Clear",
      onClick: function () {
        sharedState.logoPath = "";
        logoStatusLabel.textContent = "No logo selected";
        scheduleRefresh();
      }
    }, [
      window.FOSS.icons.el("trash", 14),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);
    var logoCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "qr-logo-group"
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Center Logo / Icon Embedding" }),
      window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [chooseLogoBtn, clearLogoBtn]),
      logoStatusLabel
    ]);

    var sidebarCol = window.FOSS.dom.el("div", { className: "qr-sidebar-pane" }, [typeCard, contentCard, styleCard, logoCard]);

    var preview = makePreviewBox("qr-preview-img", "Generated QR Code");
    var infoLabel = window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono", text: "" });
    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3 items-center" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base self-start", text: "Live Preview" }),
      preview.box,
      infoLabel
    ]);

    function exportSize() {
      var size = parseInt(exportSizeInput.value, 10);
      return size > 0 ? size : 512;
    }

    function updateInfoLabel() {
      infoLabel.textContent = "QR Code - Export Size: " + exportSize() + " x " + exportSize() + " px | Error Correction: " + eccSelect.value;
    }

    function styleParams() {
      return {
        schema: sharedState.payloadType,
        fields: collectFields(sharedState.payloadType),
        fill_color: sharedState.fgColor,
        back_color: sharedState.bgColor,
        error_correction: eccSelect.value || "M",
        logo_path: sharedState.logoPath || null
      };
    }

    function scheduleRefresh() {
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshTimer = setTimeout(refreshCode, 120);
    }

    function refreshCode() {
      refreshTimer = null;
      chrome.clearError();
      updateInfoLabel();
      var seq = ++refreshSeq;
      var params = styleParams();
      params.box_size = 10;
      callApi("qr_generate", params).then(function (res) {
        if (seq !== refreshSeq) return;
        if (res && res.data_url) {
          currentImageDataUrl = res.data_url;
          currentPayload = res.payload || "";
          preview.show(res.data_url);
        }
      }).catch(function (err) {
        if (seq === refreshSeq) chrome.showError(errText(err));
      });
    }

    function saveImage() {
      chrome.clearError();
      savePath("Save QR Code Image", "barcode", RASTER_TYPES).then(function (outPath) {
        if (!outPath) return null;
        var params = styleParams();
        params.output_path = outPath;
        if (extOf(outPath) === "svg") {
          return callApi("qr_generate_svg", params).then(function (res) {
            chrome.showResult(res.output_path || outPath, "SVG Vector Exported");
            chrome.statusBar.textContent = "Saved SVG to " + (res.output_path || outPath);
          });
        }
        params.box_size = 10;
        params.size_px = exportSize();
        return callApi("qr_generate", params).then(function (res) {
          chrome.showResult(res.output_path || outPath, "Image Saved");
          chrome.statusBar.textContent = "Saved to " + (res.output_path || outPath);
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function exportSvg() {
      chrome.clearError();
      savePath("Export Vector SVG", "barcode", SVG_TYPES).then(function (outPath) {
        if (!outPath) return null;
        var params = styleParams();
        params.output_path = outPath;
        return callApi("qr_generate_svg", params).then(function (res) {
          chrome.showResult(res.output_path || outPath, "SVG Vector Exported");
          chrome.statusBar.textContent = "Saved SVG to " + (res.output_path || outPath);
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function exportCalendarIcs() {
      chrome.clearError();
      var values = collectFields("calendar");
      if (!values.title || !values.start_time) {
        chrome.showError("Enter an event title and start time first.");
        return;
      }
      savePath("Save as .ics File", "event", ICS_TYPES).then(function (outPath) {
        if (!outPath) return null;
        return callApi("qr_export_ics", {
          title: values.title,
          start_time: values.start_time,
          end_time: values.end_time,
          location: values.location,
          description: values.description,
          output_path: outPath
        }).then(function (res) {
          chrome.showResult(res.output_path || outPath, "Calendar .ICS File Saved");
          chrome.statusBar.textContent = "Saved .ics to " + (res.output_path || outPath);
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function exportLabelSheetPdf() {
      chrome.clearError();
      callApi("qr_label_presets", {}).then(function (presetsRes) {
        var presets = (presetsRes && presetsRes.presets) || ["Avery 5160"];
        return savePath("Save Printable Label Sheet (PDF)", "labels", PDF_TYPES).then(function (outPath) {
          if (!outPath) return null;
          return callApi("qr_label_sheet", {
            payload: currentPayload,
            output_path: outPath,
            preset: presets[0] || "Avery 5160",
            count: 30
          }).then(function (res) {
            chrome.showResult(res.output_path || outPath, "Label Sheet PDF Saved");
            chrome.statusBar.textContent = "Saved label sheet to " + (res.output_path || outPath);
          });
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function actionButton(testid, label, iconName, variant, handler) {
      return window.FOSS.dom.el("button", {
        className: "btn " + variant,
        type: "button",
        "data-testid": testid,
        "aria-label": label,
        title: label,
        onClick: handler
      }, [
        window.FOSS.icons.el(iconName, 16),
        window.FOSS.dom.el("span", { text: label })
      ]);
    }

    var saveImageBtn = actionButton("qr-save-image-btn", "Save Image...", "download", "btn-primary", saveImage);
    var copyBtn = actionButton("qr-copy-btn", "Copy Image to Clipboard", "copy", "btn-secondary", function () {
      if (!currentImageDataUrl) {
        chrome.showError("No image available to copy.");
        return;
      }
      copyImageToClipboard(currentImageDataUrl).then(function () {
        chrome.statusBar.textContent = "Copied QR code image to clipboard.";
      }).catch(function (err) {
        chrome.showError("Copy failed: " + errText(err));
      });
    });
    var exportSvgBtn = actionButton("qr-export-svg-btn", "Export Vector SVG", "file-text", "btn-secondary", exportSvg);
    var exportLabelsBtn = actionButton("qr-export-labels-btn", "Print Label Sheet (PDF)...", "printer", "btn-secondary", exportLabelSheetPdf);
    var icsBtn = actionButton("qr-save-ics-btn", "Save as .ics file", "file-text", "btn-secondary hidden", exportCalendarIcs);

    var exportCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export & Share" }),
      window.FOSS.dom.el("div", { className: "qr-actions-row" }, [saveImageBtn, copyBtn, exportSvgBtn, exportLabelsBtn, icsBtn])
    ]);

    var stageCol = window.FOSS.dom.el("div", { className: "qr-stage-pane" }, [previewCard, exportCard]);

    panel.appendChild(chrome.statusBar);
    panel.appendChild(chrome.errorBanner);
    panel.appendChild(chrome.resultHost);
    panel.appendChild(makeWorkbench(sidebarCol, stageCol));

    activeCleanup = function () {
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshSeq += 1;
    };

    var defaultType = String(toolDefault("default_type", "url"));
    setPayloadType(defaultType);
  }

  function renderBarcodeTab(panel) {
    runCleanup();
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "qr-barcode-page");

    var chrome = makeChrome();
    var currentPayload = "123456789012";
    var currentImageDataUrl = "";
    var refreshSeq = 0;

    var defaultSymbology = String(toolDefault("barcode_symbology", "code128"));
    var symbologySelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-barcode-symbology",
      "aria-label": "Symbology",
      title: "Symbology",
      onChange: function () {
        updateValidationHint();
        refreshBarcode();
      }
    }, [
      window.FOSS.dom.el("option", { value: "code128", text: "Code 128 (General Purpose ASCII)" }),
      window.FOSS.dom.el("option", { value: "ean13", text: "EAN-13 (13 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "code39", text: "Code 39 (Alphanumeric)" }),
      window.FOSS.dom.el("option", { value: "ean8", text: "EAN-8 (8 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "upca", text: "UPC-A (12 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "itf", text: "ITF (Interleaved 2 of 5)" })
    ]);
    symbologySelect.value = defaultSymbology;

    var hintLabel = window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "" });
    var hints = {
      ean13: "Requires 12 or 13 digits (numeric)",
      ean8: "Requires 7 or 8 digits (numeric)",
      upca: "Requires 11 or 12 digits (numeric)",
      itf: "Requires an even number of numeric digits",
      code39: "Supports uppercase letters, numbers, and - . $ / + % space",
      code128: "Supports all standard ASCII characters"
    };

    function updateValidationHint() {
      hintLabel.textContent = hints[symbologySelect.value] || hints.code128;
    }

    var valueInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: currentPayload,
      placeholder: "Barcode value",
      "data-testid": "qr-barcode-value",
      "aria-label": "Barcode value",
      title: "Barcode value",
      onInput: refreshBarcode
    });

    var defaultBarcodeLabel = toolDefault("barcode_show_label", true) !== false;
    var labelToggle = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: defaultBarcodeLabel,
      "data-testid": "qr-barcode-toggle",
      "aria-label": "Show Value Label",
      title: "Show Value Label",
      onChange: refreshBarcode
    });

    var heightInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input qr-input-narrow",
      value: "100",
      min: "30",
      max: "400",
      "aria-label": "Bar Height",
      title: "Bar Height",
      onInput: refreshBarcode
    });

    var configCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "1D Barcode Configuration" }),
      window.FOSS.components.field("Symbology", symbologySelect),
      hintLabel,
      window.FOSS.components.field("Payload Value", valueInput),
      window.FOSS.dom.el("label", { className: "row items-center gap-2" }, [
        labelToggle,
        window.FOSS.dom.el("span", { text: "Show Value Label" })
      ]),
      window.FOSS.components.field("Bar Height (px)", heightInput)
    ]);
    var sidebarCol = window.FOSS.dom.el("div", { className: "qr-sidebar-pane" }, [configCard]);

    var preview = makePreviewBox("qr-preview-img", "Generated Barcode");
    var infoLabel = window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono", text: "1D Barcode - Ready" });
    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3 items-center" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base self-start", text: "Barcode Preview" }),
      preview.box,
      infoLabel
    ]);

    function barcodeParams() {
      return {
        payload: valueInput.value || "12345678",
        barcode_type: symbologySelect.value || "code128",
        include_label: labelToggle.checked,
        height: parseInt(heightInput.value, 10) || 100
      };
    }

    function refreshBarcode() {
      chrome.clearError();
      var seq = ++refreshSeq;
      var params = barcodeParams();
      currentPayload = params.payload;
      callApi("qr_generate_barcode", params).then(function (res) {
        if (seq !== refreshSeq) return;
        if (res && res.data_url) {
          currentImageDataUrl = res.data_url;
          preview.show(res.data_url);
          infoLabel.textContent = "1D Barcode: " + params.barcode_type.toUpperCase() + " - " + res.width + " x " + res.height + " px";
        }
      }).catch(function (err) {
        if (seq === refreshSeq) chrome.showError(errText(err));
      });
    }

    function saveBarcodeFile() {
      chrome.clearError();
      savePath("Save Barcode Image", "barcode", BARCODE_TYPES).then(function (outPath) {
        if (!outPath) return null;
        var params = barcodeParams();
        params.output_path = outPath;
        return callApi("qr_generate_barcode", params).then(function (res) {
          chrome.showResult(res.output_path || outPath, "Barcode Saved");
          chrome.statusBar.textContent = "Saved to " + (res.output_path || outPath);
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function exportBarcodeLabels() {
      chrome.clearError();
      savePath("Save Barcode Label Sheet (PDF)", "labels", PDF_TYPES).then(function (outPath) {
        if (!outPath) return null;
        return callApi("qr_label_sheet", {
          payload: currentPayload,
          output_path: outPath,
          preset: "Avery 5160",
          barcode_type: symbologySelect.value || "code128",
          count: 30
        }).then(function (res) {
          chrome.showResult(res.output_path || outPath, "Label Sheet Saved");
          chrome.statusBar.textContent = "Saved to " + (res.output_path || outPath);
        });
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function actionButton(testid, label, iconName, variant, handler) {
      return window.FOSS.dom.el("button", {
        className: "btn " + variant,
        type: "button",
        "data-testid": testid,
        "aria-label": label,
        title: label,
        onClick: handler
      }, [
        window.FOSS.icons.el(iconName, 16),
        window.FOSS.dom.el("span", { text: label })
      ]);
    }

    var saveBtn = actionButton("qr-save-image-btn", "Save Barcode...", "download", "btn-primary", saveBarcodeFile);
    var copyBtn = actionButton("qr-copy-btn", "Copy Image", "copy", "btn-secondary", function () {
      if (!currentImageDataUrl) return;
      copyImageToClipboard(currentImageDataUrl).then(function () {
        chrome.statusBar.textContent = "Copied barcode image to clipboard.";
      });
    });
    var labelsBtn = actionButton("qr-export-labels-btn", "Print Label Sheet (PDF)...", "printer", "btn-secondary", exportBarcodeLabels);

    var exportCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export Barcode" }),
      window.FOSS.dom.el("div", { className: "qr-actions-row" }, [saveBtn, copyBtn, labelsBtn])
    ]);
    var stageCol = window.FOSS.dom.el("div", { className: "qr-stage-pane" }, [previewCard, exportCard]);

    panel.appendChild(chrome.statusBar);
    panel.appendChild(chrome.errorBanner);
    panel.appendChild(chrome.resultHost);
    panel.appendChild(makeWorkbench(sidebarCol, stageCol));

    activeCleanup = function () {
      refreshSeq += 1;
    };

    updateValidationHint();
    refreshBarcode();
  }

  function renderScanTab(panel) {
    runCleanup();
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "qr-scan-page");

    var chrome = makeChrome();
    var webcamStream = null;
    var webcamTimer = null;
    var webcamBusy = false;

    var scanPicker = window.FOSS.components.filePicker({
      testid: "qr-scan-file-picker",
      title: "Select Image or PDF to Scan",
      fileTypes: ["png", "jpg", "jpeg", "webp", "pdf", "bmp"],
      onSelect: function (val) {
        chrome.clearError();
        if (val) executeScan(val);
      },
      onClear: function () {
        sharedState.lastDecodedItems = [];
        renderDecodedResults();
      }
    });

    var pasteBanner = window.FOSS.dom.el("div", {
      className: "qr-paste-zone text-sm text-muted",
      text: "Paste screenshot from clipboard (Ctrl+V) anywhere on this screen"
    });

    var inputCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Input Image Preview" }),
      scanPicker.el,
      pasteBanner
    ]);

    var video = window.FOSS.dom.el("video", {
      className: "qr-webcam-video hidden",
      "data-testid": "qr-webcam-video",
      muted: true,
      playsinline: true,
      "aria-label": "Webcam preview"
    });
    video.muted = true;
    var canvas = document.createElement("canvas");

    function webcamButton(testid, label, variant, handler) {
      return window.FOSS.dom.el("button", {
        className: "btn btn-sm " + variant,
        type: "button",
        "data-testid": testid,
        "aria-label": label,
        title: label,
        onClick: handler
      }, [window.FOSS.dom.el("span", { text: label })]);
    }

    var webcamStartBtn = webcamButton("qr-webcam-start-btn", "Start Webcam", "btn-secondary", startWebcam);
    var webcamStopBtn = webcamButton("qr-webcam-stop-btn", "Stop Webcam", "btn-secondary hidden", stopWebcam);
    var webcamCaptureBtn = webcamButton("qr-webcam-capture-btn", "Capture and Decode", "btn-primary hidden", function () {
      decodeWebcamFrame(true);
    });
    var webcamCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Webcam Scan" }),
      video,
      window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [webcamStartBtn, webcamCaptureBtn, webcamStopBtn])
    ]);

    var detailsContent = window.FOSS.dom.el("div", {
      className: "qr-detail-box text-sm text-muted font-mono",
      text: "No code selected"
    });
    var detailsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-2" }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Details" }),
      detailsContent
    ]);

    var sidebarCol = window.FOSS.dom.el("div", { className: "qr-sidebar-pane" }, [inputCard, webcamCard, detailsCard]);

    var resultsList = window.FOSS.dom.el("div", { className: "flex-col gap-2 qr-results-list" });
    var resultsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-scan-results"
    }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Decoded Results" }),
      resultsList
    ]);
    var stageCol = window.FOSS.dom.el("div", { className: "qr-stage-pane" }, [resultsCard]);

    panel.appendChild(chrome.statusBar);
    panel.appendChild(chrome.errorBanner);
    panel.appendChild(makeWorkbench(sidebarCol, stageCol));

    function applyResults(res, label) {
      sharedState.lastDecodedItems = (res && res.results) || [];
      renderDecodedResults();
      chrome.statusBar.textContent = label + ": Found " + sharedState.lastDecodedItems.length + " code(s).";
    }

    function executeScan(imgPath) {
      chrome.clearError();
      chrome.statusBar.textContent = "Scanning image for QR and barcodes...";
      callApi("qr_decode", { image_path: imgPath }).then(function (res) {
        applyResults(res, "Scan complete");
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function executeDecodeDataUrl(dataUrl, label) {
      chrome.clearError();
      return callApi("qr_decode_data_url", { data_url: dataUrl }).then(function (res) {
        applyResults(res, label);
        return res;
      }).catch(function (err) {
        chrome.showError(errText(err));
      });
    }

    function startWebcam() {
      chrome.clearError();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        chrome.showError("Webcam access is not available in this environment.");
        return;
      }
      navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false }).then(function (stream) {
        webcamStream = stream;
        video.srcObject = stream;
        video.classList.remove("hidden");
        webcamStartBtn.classList.add("hidden");
        webcamStopBtn.classList.remove("hidden");
        webcamCaptureBtn.classList.remove("hidden");
        var playing = video.play();
        if (playing && playing.catch) playing.catch(function () {});
        chrome.statusBar.textContent = "Webcam running. Hold a code in view to scan it.";
        webcamTimer = setInterval(function () { decodeWebcamFrame(false); }, 900);
      }).catch(function (err) {
        chrome.showError("Webcam unavailable: " + errText(err) + ". Tip: You can drag and drop images or paste screenshots directly into this window.");
      });
    }

    function stopWebcam() {
      if (webcamTimer) {
        clearInterval(webcamTimer);
        webcamTimer = null;
      }
      if (webcamStream) {
        webcamStream.getTracks().forEach(function (track) { track.stop(); });
        webcamStream = null;
      }
      video.srcObject = null;
      video.classList.add("hidden");
      webcamStartBtn.classList.remove("hidden");
      webcamStopBtn.classList.add("hidden");
      webcamCaptureBtn.classList.add("hidden");
    }

    function decodeWebcamFrame(manual) {
      if (!webcamStream || webcamBusy || !video.videoWidth) return;
      var scale = Math.min(1, 1280 / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      webcamBusy = true;
      callApi("qr_decode_data_url", { data_url: canvas.toDataURL("image/png") }).then(function (res) {
        var found = (res && res.results) || [];
        if (found.length || manual) applyResults(res, "Webcam scan");
      }).catch(function (err) {
        if (manual) chrome.showError(errText(err));
      }).then(function () {
        webcamBusy = false;
      });
    }

    function onPaste(e) {
      if (!e.clipboardData || !e.clipboardData.items) return;
      var items = e.clipboardData.items;
      for (var i = 0; i < items.length; i++) {
        if (items[i].type && items[i].type.indexOf("image") !== -1) {
          var blob = items[i].getAsFile();
          if (blob) {
            var reader = new FileReader();
            reader.onload = function (evt) {
              if (evt.target && evt.target.result) {
                chrome.statusBar.textContent = "Decoding pasted screenshot...";
                executeDecodeDataUrl(evt.target.result, "Pasted scan complete");
              }
            };
            reader.readAsDataURL(blob);
            e.preventDefault();
            return;
          }
        }
      }
    }

    window.addEventListener("paste", onPaste);
    activeCleanup = function () {
      window.removeEventListener("paste", onPaste);
      stopWebcam();
    };

    function describe(item) {
      return (item.type || "Code") + ": " + (item.payload || item.data || "");
    }

    function renderDecodedResults() {
      resultsList.innerHTML = "";
      var items = sharedState.lastDecodedItems;
      if (items.length === 0) {
        resultsList.appendChild(window.FOSS.dom.el("div", {
          className: "text-sm text-muted p-4 text-center",
          text: "No QR codes or barcodes detected yet. Open an image or paste a screenshot, or start the webcam."
        }));
        detailsContent.textContent = "No code selected";
        return;
      }

      items.forEach(function (item) {
        var itemData = item.payload || item.data || "";
        var actionBtns = [
          window.FOSS.dom.el("button", {
            className: "btn btn-sm",
            type: "button",
            "aria-label": "Copy payload",
            title: "Copy text",
            onClick: function (ev) {
              ev.stopPropagation();
              copyTextToClipboard(itemData);
              chrome.statusBar.textContent = "Copied code data to clipboard.";
            }
          }, [
            window.FOSS.icons.el("copy", 14),
            window.FOSS.dom.el("span", { text: "Copy" })
          ])
        ];
        if (itemData.indexOf("http://") === 0 || itemData.indexOf("https://") === 0) {
          actionBtns.push(window.FOSS.dom.el("button", {
            className: "btn btn-sm btn-secondary",
            type: "button",
            "aria-label": "Open link in browser",
            title: "Open URL",
            onClick: function (ev) {
              ev.stopPropagation();
              window.FOSS.api("open_url", { url: itemData });
            }
          }, [
            window.FOSS.icons.el("external-link", 14),
            window.FOSS.dom.el("span", { text: "Open URL" })
          ]));
        }

        var row = window.FOSS.dom.el("div", { className: "qr-result-row" }, [
          window.FOSS.dom.el("div", { className: "flex-col flex-1 qr-result-text" }, [
            window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: item.type || "QR Code" }),
            window.FOSS.dom.el("span", { className: "font-mono text-xs text-muted qr-result-payload", text: itemData })
          ]),
          window.FOSS.dom.el("div", { className: "row gap-2" }, actionBtns)
        ]);
        row.addEventListener("click", function () {
          detailsContent.textContent = describe(item);
        });
        resultsList.appendChild(row);
      });
      detailsContent.textContent = describe(items[0]);
    }

    renderDecodedResults();
  }

  window.FOSS.router.register({
    id: "qr",
    title: "QR Code Generator",
    navName: "QR & Barcodes",
    category: "Utilities",
    icon: "qr",
    workbench: true,
    defaults: [
      {
        key: "default_type",
        label: "Default QR payload type",
        type: "select",
        default: "url",
        options: PAYLOAD_TYPES.map(function (p) { return { value: p.id, label: p.label }; })
      },
      {
        key: "error_correction",
        label: "Default error correction level",
        type: "select",
        default: "M",
        options: [
          { value: "L", label: "L - Low (~7% recovery)" },
          { value: "M", label: "M - Standard (~15% recovery)" },
          { value: "Q", label: "Q - Medium-High (~25% recovery)" },
          { value: "H", label: "H - Highest (~30% recovery)" }
        ]
      },
      { key: "export_resolution", label: "Default export resolution (px)", type: "number", default: 512, min: 64, max: 4096, step: 64 },
      {
        key: "barcode_symbology",
        label: "Default 1D barcode symbology",
        type: "select",
        default: "code128",
        options: [
          { value: "code128", label: "Code 128 (General Purpose ASCII)" },
          { value: "ean13", label: "EAN-13 (13 Digits Retail)" },
          { value: "code39", label: "Code 39 (Alphanumeric)" },
          { value: "ean8", label: "EAN-8 (8 Digits Retail)" },
          { value: "upca", label: "UPC-A (12 Digits Retail)" },
          { value: "itf", label: "ITF (Interleaved 2 of 5)" }
        ]
      },
      { key: "barcode_show_label", label: "Show value label on barcodes by default", type: "toggle", default: true }
    ],
    tabs: [
      { id: "qr", label: "QR Generator", aliases: ["main", "generate"], render: renderQRTab },
      { id: "barcode", label: "1D Barcodes", render: renderBarcodeTab },
      { id: "scan", label: "Scan & Decode", render: renderScanTab }
    ],
    onHide: runCleanup
  });
})();
