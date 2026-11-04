// QR Codes and Barcodes workspace: generator, scanner, custom styles, logos, vector SVG, and label sheets.
window.FOSS = window.FOSS || {};

(function () {
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

  // Shared state across tabs if needed
  var sharedState = {
    payloadType: "url",
    fgColor: "#000000",
    bgColor: "#ffffff",
    logoPath: "",
    lastDecodedItems: []
  };

  function renderQRTab(panel) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-qr");

    var currentPayload = "https://github.com/fosseverything";
    var currentImageDataUrl = "";

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

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", {
      "data-testid": "qr-result",
      hidden: true
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "qr-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    // Left Column: Configuration Forms
    var sidebarCol = window.FOSS.dom.el("div", {
      className: "qr-sidebar-pane"
    });

    // Group 1: Payload Type
    var typeCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "qr-templates-group"
    });
    var typeTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Type" });

    var segmentedRow = window.FOSS.dom.el("div", {
      className: "row",
      style: { display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginBottom: "var(--space-2)" },
      "data-testid": "qr-segmented-types"
    });

    var segTypes = [
      { id: "url", label: "URL" },
      { id: "text", label: "Plain Text" },
      { id: "vcard", label: "Contact vCard" },
      { id: "wifi", label: "Wi-Fi Network" }
    ];

    var segButtons = {};
    function updateSegmentButtons() {
      var current = typeSelect ? typeSelect.value : "url";
      segTypes.forEach(function (st) {
        var btn = segButtons[st.id];
        if (btn) {
          if (current === st.id) {
            btn.className = "btn btn-sm btn-primary";
          } else {
            btn.className = "btn btn-sm btn-secondary";
          }
        }
      });
    }

    segTypes.forEach(function (st) {
      var btn = window.FOSS.dom.el("button", {
        className: st.id === "url" ? "btn btn-sm btn-primary" : "btn btn-sm btn-secondary",
        "data-testid": "qr-type-" + st.id,
        text: st.label,
        onClick: function () {
          typeSelect.value = st.id;
          updateSegmentButtons();
          updateContentFields();
          refreshCode();
        }
      });
      segButtons[st.id] = btn;
      segmentedRow.appendChild(btn);
    });

    var typeSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-payload-type",
      "aria-label": "Payload Type",
      title: "Payload Type",
      style: { width: "100%" },
      onChange: function () {
        updateSegmentButtons();
        if (typeSelect.value === "barcode") {
          window.FOSS.router.open("qr", "barcode");
          return;
        }
        updateContentFields();
        refreshCode();
      }
    }, [
      window.FOSS.dom.el("option", { value: "url", text: "URL / Web Link" }),
      window.FOSS.dom.el("option", { value: "wifi", text: "Wi-Fi Network" }),
      window.FOSS.dom.el("option", { value: "text", text: "Plain Text" }),
      window.FOSS.dom.el("option", { value: "vcard", text: "Contact Card (vCard)" }),
      window.FOSS.dom.el("option", { value: "email", text: "Email Address" }),
      window.FOSS.dom.el("option", { value: "phone", text: "Phone Number" }),
      window.FOSS.dom.el("option", { value: "sms", text: "SMS Message" }),
      window.FOSS.dom.el("option", { value: "whatsapp", text: "WhatsApp Message" }),
      window.FOSS.dom.el("option", { value: "geo", text: "Geo Location" }),
      window.FOSS.dom.el("option", { value: "calendar", text: "Calendar Event" }),
      window.FOSS.dom.el("option", { value: "asset", text: "Asset / Inventory Tag" }),
      window.FOSS.dom.el("option", { value: "barcode", text: "1D Barcode" })
    ]);

    typeCard.appendChild(typeTitle);
    typeCard.appendChild(segmentedRow);
    typeCard.appendChild(typeSelect);

    // Group 2: Content Details
    var contentCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-content-details"
    });
    var contentTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Content Details" });
    var contentBody = window.FOSS.dom.el("div", {
      className: "flex-col gap-2"
    });
    contentCard.appendChild(contentTitle);
    contentCard.appendChild(contentBody);

    // Inputs
    var urlInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      value: "https://github.com/fosseverything",
      placeholder: "https://example.com",
      "data-testid": "qr-text-input",
      "aria-label": "URL web address",
      title: "URL web address",
      onInput: refreshCode
    });

    var wifiSsid = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      placeholder: "Network SSID",
      "aria-label": "Network SSID",
      title: "Network SSID",
      onInput: refreshCode
    });
    var wifiPass = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      placeholder: "Wi-Fi Password",
      "aria-label": "Wi-Fi Password",
      title: "Wi-Fi Password",
      onInput: refreshCode
    });
    var wifiSec = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Wi-Fi Security",
      title: "Wi-Fi Security",
      onChange: refreshCode
    }, [
      window.FOSS.dom.el("option", { value: "WPA", text: "WPA/WPA2/WPA3" }),
      window.FOSS.dom.el("option", { value: "WEP", text: "WEP" }),
      window.FOSS.dom.el("option", { value: "nopass", text: "Open (No Password)" })
    ]);
    var wifiHidden = window.FOSS.dom.el("input", {
      type: "checkbox",
      "aria-label": "Hidden network",
      title: "Hidden network",
      onChange: refreshCode
    });

    var textInput = window.FOSS.dom.el("textarea", {
      className: "input",
      rows: "3",
      placeholder: "Enter arbitrary text or notes",
      "data-testid": "qr-text-input",
      "aria-label": "Arbitrary text notes",
      title: "Arbitrary text notes",
      onInput: refreshCode
    });

    var vcardName = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Full Name", "aria-label": "Full Name", title: "Full Name", onInput: refreshCode });
    var vcardOrg = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Organization / Company", "aria-label": "Organization", title: "Organization", onInput: refreshCode });
    var vcardTitle = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Job Title", "aria-label": "Job Title", title: "Job Title", onInput: refreshCode });
    var vcardPhone = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Phone Number", "aria-label": "Phone Number", title: "Phone Number", onInput: refreshCode });
    var vcardEmail = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Email Address", "aria-label": "Email Address", title: "Email Address", onInput: refreshCode });

    var emailTo = window.FOSS.dom.el("input", { type: "email", className: "input", placeholder: "recipient@example.com", "aria-label": "Email Recipient", title: "Email Recipient", onInput: refreshCode });
    var emailSubject = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Email Subject", "aria-label": "Email Subject", title: "Email Subject", onInput: refreshCode });
    var emailBody = window.FOSS.dom.el("textarea", { className: "input", rows: "2", placeholder: "Email message body", "aria-label": "Email Body", title: "Email Body", onInput: refreshCode });

    var phoneInput = window.FOSS.dom.el("input", { type: "tel", className: "input", placeholder: "+1-555-0199", "aria-label": "Phone Number", title: "Phone Number", onInput: refreshCode });

    var smsPhone = window.FOSS.dom.el("input", { type: "tel", className: "input", placeholder: "+1-555-0199", "aria-label": "SMS Phone Number", title: "SMS Phone Number", onInput: refreshCode });
    var smsMsg = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Prefilled text message", "aria-label": "SMS Message", title: "SMS Message", onInput: refreshCode });

    var waPhone = window.FOSS.dom.el("input", { type: "tel", className: "input", placeholder: "+15550199 (with country code)", "aria-label": "WhatsApp Phone", title: "WhatsApp Phone", onInput: refreshCode });
    var waMsg = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Prefilled message", "aria-label": "WhatsApp Message", title: "WhatsApp Message", onInput: refreshCode });

    var geoLat = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "37.7749", "aria-label": "Latitude", title: "Latitude", onInput: refreshCode });
    var geoLon = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "-122.4194", "aria-label": "Longitude", title: "Longitude", onInput: refreshCode });

    var calTitle = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Event Title", "aria-label": "Event Title", title: "Event Title", onInput: refreshCode });
    var calStart = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "20261101T120000Z", value: "20261101T120000Z", "aria-label": "Start Time", title: "Start Time", onInput: refreshCode });
    var calEnd = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "20261101T130000Z", "aria-label": "End Time", title: "End Time", onInput: refreshCode });
    var calLoc = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Location / Room", "aria-label": "Location", title: "Location", onInput: refreshCode });

    var assetId = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "ASSET-1001", "aria-label": "Asset ID", title: "Asset ID", onInput: refreshCode });
    var assetLocation = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Server Room B", "aria-label": "Location", title: "Location", onInput: refreshCode });

    // Barcode fallback in QR tab
    var barcodeSymbology = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-barcode-symbology",
      "aria-label": "Barcode Symbology",
      title: "Barcode Symbology",
      onChange: refreshCode
    }, [
      window.FOSS.dom.el("option", { value: "code128", text: "Code 128" }),
      window.FOSS.dom.el("option", { value: "code39", text: "Code 39" }),
      window.FOSS.dom.el("option", { value: "ean13", text: "EAN-13" }),
      window.FOSS.dom.el("option", { value: "ean8", text: "EAN-8" }),
      window.FOSS.dom.el("option", { value: "upca", text: "UPC-A" }),
      window.FOSS.dom.el("option", { value: "isbn13", text: "ISBN-13" }),
      window.FOSS.dom.el("option", { value: "itf", text: "ITF" })
    ]);
    var barcodeVal = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: "12345678",
      placeholder: "Barcode value",
      "aria-label": "Barcode value",
      title: "Barcode value",
      onInput: refreshCode
    });
    var barcodeLabelToggle = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "qr-barcode-toggle",
      "aria-label": "Show Value Label",
      title: "Show Value Label",
      onChange: refreshCode
    });

    function updateContentFields() {
      contentBody.innerHTML = "";
      var t = typeSelect.value;
      if (t === "url") {
        contentBody.appendChild(window.FOSS.components.field("Web URL", urlInput));
      } else if (t === "wifi") {
        contentBody.appendChild(window.FOSS.components.field("SSID", wifiSsid));
        contentBody.appendChild(window.FOSS.components.field("Password", wifiPass));
        contentBody.appendChild(window.FOSS.components.field("Security", wifiSec));
        var hidRow = window.FOSS.dom.el("label", { className: "row items-center", style: { gap: "var(--space-2)", cursor: "pointer" } }, [
          wifiHidden,
          window.FOSS.dom.el("span", { text: "Hidden Network" })
        ]);
        contentBody.appendChild(hidRow);
      } else if (t === "text") {
        contentBody.appendChild(window.FOSS.components.field("Plain Text", textInput));
      } else if (t === "vcard") {
        contentBody.appendChild(window.FOSS.components.field("Full Name", vcardName));
        contentBody.appendChild(window.FOSS.components.field("Organization", vcardOrg));
        contentBody.appendChild(window.FOSS.components.field("Job Title", vcardTitle));
        contentBody.appendChild(window.FOSS.components.field("Phone", vcardPhone));
        contentBody.appendChild(window.FOSS.components.field("Email", vcardEmail));
      } else if (t === "email") {
        contentBody.appendChild(window.FOSS.components.field("Recipient Email", emailTo));
        contentBody.appendChild(window.FOSS.components.field("Subject", emailSubject));
        contentBody.appendChild(window.FOSS.components.field("Message Body", emailBody));
      } else if (t === "phone") {
        contentBody.appendChild(window.FOSS.components.field("Phone Number", phoneInput));
      } else if (t === "sms") {
        contentBody.appendChild(window.FOSS.components.field("Phone Number", smsPhone));
        contentBody.appendChild(window.FOSS.components.field("Prefilled Message", smsMsg));
      } else if (t === "whatsapp") {
        contentBody.appendChild(window.FOSS.components.field("Phone Number (with Country Code)", waPhone));
        contentBody.appendChild(window.FOSS.components.field("Prefilled Message", waMsg));
      } else if (t === "geo") {
        contentBody.appendChild(window.FOSS.components.field("Latitude", geoLat));
        contentBody.appendChild(window.FOSS.components.field("Longitude", geoLon));
      } else if (t === "calendar") {
        contentBody.appendChild(window.FOSS.components.field("Event Title", calTitle));
        contentBody.appendChild(window.FOSS.components.field("Start Time (ISO/UTC)", calStart));
        contentBody.appendChild(window.FOSS.components.field("End Time (Optional)", calEnd));
        contentBody.appendChild(window.FOSS.components.field("Location", calLoc));
      } else if (t === "asset") {
        contentBody.appendChild(window.FOSS.components.field("Asset ID", assetId));
        contentBody.appendChild(window.FOSS.components.field("Location / Room", assetLocation));
      } else if (t === "barcode") {
        contentBody.appendChild(window.FOSS.components.field("Symbology", barcodeSymbology));
        contentBody.appendChild(window.FOSS.components.field("Value", barcodeVal));
        var chkRow = window.FOSS.dom.el("label", {
          className: "row items-center",
          style: { gap: "var(--space-2)", cursor: "pointer" }
        }, [
          barcodeLabelToggle,
          window.FOSS.dom.el("span", { text: "Show Value Label" })
        ]);
        contentBody.appendChild(chkRow);
      } else {
        contentBody.appendChild(window.FOSS.components.field("Value", urlInput));
      }

      // Show Save as .ics only when calendar payload
      if (t === "calendar") {
        exportIcsBtn.style.setProperty("display", "inline-flex");
      } else {
        exportIcsBtn.style.setProperty("display", "none");
      }
    }

    // Group 3: Styling & Resolution
    var styleCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-styling-group"
    });
    var styleTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Colors & Quiet Zone" });

    var fgInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: sharedState.fgColor,
      style: { width: "100px" },
      "aria-label": "Foreground color hex",
      title: "Foreground color hex",
      onInput: function () {
        sharedState.fgColor = fgInput.value;
        fgColorPicker.value = sharedState.fgColor;
        refreshCode();
      }
    });
    var fgColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      value: sharedState.fgColor,
      hidden: true,
      onChange: function () {
        sharedState.fgColor = fgColorPicker.value;
        fgInput.value = sharedState.fgColor;
        refreshCode();
      }
    });
    var fgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-sm",
      "aria-label": "Pick foreground color",
      title: "Pick color",
      onClick: function () { fgColorPicker.click(); }
    }, [window.FOSS.icons.el("palette", 14)]);
    var fgRow = window.FOSS.dom.el("div", { className: "row items-center", style: { gap: "var(--space-2)" } }, [
      fgInput, fgColorPicker, fgBtn
    ]);

    var bgInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: sharedState.bgColor,
      style: { width: "100px" },
      "aria-label": "Background color hex",
      title: "Background color hex",
      onInput: function () {
        sharedState.bgColor = bgInput.value;
        bgColorPicker.value = sharedState.bgColor;
        refreshCode();
      }
    });
    var bgColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      value: sharedState.bgColor,
      hidden: true,
      onChange: function () {
        sharedState.bgColor = bgColorPicker.value;
        bgInput.value = sharedState.bgColor;
        refreshCode();
      }
    });
    var bgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-sm",
      "aria-label": "Pick background color",
      title: "Pick color",
      onClick: function () { bgColorPicker.click(); }
    }, [window.FOSS.icons.el("palette", 14)]);
    var bgRow = window.FOSS.dom.el("div", { className: "row items-center", style: { gap: "var(--space-2)" } }, [
      bgInput, bgColorPicker, bgBtn
    ]);

    var eccSelect = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Error Correction",
      title: "Error Correction",
      onChange: refreshCode
    }, [
      window.FOSS.dom.el("option", { value: "L", text: "L (Low - 7% damage recovery)" }),
      window.FOSS.dom.el("option", { value: "M", text: "M (Medium - 15% recovery)", selected: true }),
      window.FOSS.dom.el("option", { value: "Q", text: "Q (Quartile - 25% recovery)" }),
      window.FOSS.dom.el("option", { value: "H", text: "H (High - 30% recovery)" })
    ]);

    var boxSizeInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      value: "10",
      min: "2",
      max: "30",
      style: { width: "80px" },
      "aria-label": "Box Size",
      title: "Box Size",
      onInput: refreshCode
    });

    var styleGrid = window.FOSS.dom.el("div", {
      className: "flex-col gap-2"
    }, [
      window.FOSS.components.field("Foreground Color", fgRow),
      window.FOSS.components.field("Background Color", bgRow),
      window.FOSS.components.field("Error Correction", eccSelect),
      window.FOSS.components.field("Module Size", boxSizeInput)
    ]);
    styleCard.appendChild(styleTitle);
    styleCard.appendChild(styleGrid);

    // Group 4: Center Logo
    var logoCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "qr-logo-group"
    });
    var logoTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Center Logo / Icon" });
    var logoStatusLabel = window.FOSS.dom.el("span", {
      className: "text-sm text-muted",
      text: sharedState.logoPath ? sharedState.logoPath.split(/[/\\]/).pop() : "No logo selected"
    });

    var chooseLogoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-sm",
      "aria-label": "Choose Logo",
      title: "Choose Logo",
      onClick: function () {
        window.FOSS.api("select_file", {
          title: "Select Logo Image",
          file_types: ["png", "jpg", "jpeg", "webp", "svg"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            sharedState.logoPath = res.paths[0];
            logoStatusLabel.textContent = sharedState.logoPath.split(/[/\\]/).pop();
            refreshCode();
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("image", 14),
      window.FOSS.dom.el("span", { text: "Choose Logo" })
    ]);

    var clearLogoBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Clear logo",
      title: "Clear",
      onClick: function () {
        sharedState.logoPath = "";
        logoStatusLabel.textContent = "No logo selected";
        refreshCode();
      }
    }, [
      window.FOSS.icons.el("trash-2", 14),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var logoRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)" }
    }, [chooseLogoBtn, clearLogoBtn, logoStatusLabel]);
    logoCard.appendChild(logoTitle);
    logoCard.appendChild(logoRow);

    sidebarCol.appendChild(typeCard);
    sidebarCol.appendChild(contentCard);
    sidebarCol.appendChild(styleCard);
    sidebarCol.appendChild(logoCard);

    // Right Column: Live Preview & Export
    var stageCol = window.FOSS.dom.el("div", {
      className: "qr-stage-pane"
    });

    var previewCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3 items-center"
    });
    var previewTitle = window.FOSS.dom.el("h3", { className: "card-title text-base self-start", text: "Live Preview" });

    var previewDisplay = window.FOSS.dom.el("div", {
      style: {
        width: "100%",
        minHeight: "260px",
        background: "var(--color-bg-base)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-3)"
      }
    });

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "qr-preview-img",
      alt: "Generated QR Code",
      style: {
        maxWidth: "100%",
        maxHeight: "330px",
        objectFit: "contain",
        display: "none"
      }
    });

    var previewEmpty = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center",
      text: "Generating preview..."
    });

    previewDisplay.appendChild(previewImg);
    previewDisplay.appendChild(previewEmpty);

    var infoLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      text: "QR Code - Export Size: 512 x 512 px"
    });

    previewCard.appendChild(previewTitle);
    previewCard.appendChild(previewDisplay);
    previewCard.appendChild(infoLabel);

    // Export Card
    var exportCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3"
    });
    var exportTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export & Share" });

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      style: { width: "100px" },
      "aria-label": "Export Format",
      title: "Export Format"
    }, [
      window.FOSS.dom.el("option", { value: "png", text: "PNG" }),
      window.FOSS.dom.el("option", { value: "svg", text: "SVG" }),
      window.FOSS.dom.el("option", { value: "pdf", text: "PDF" }),
      window.FOSS.dom.el("option", { value: "webp", text: "WEBP" }),
      window.FOSS.dom.el("option", { value: "jpeg", text: "JPEG" })
    ]);

    var savePngBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "qr-save-png-btn",
      "aria-label": "Save PNG",
      title: "Save PNG",
      onClick: function () {
        saveCodeFile("png");
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Save PNG" })
    ]);

    var saveImageBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-save-image-btn",
      "aria-label": "Save Code Image",
      title: "Save Code Image",
      onClick: function () {
        saveCodeFile(formatSelect.value);
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Save Other..." })
    ]);

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-copy-btn",
      "aria-label": "Copy Image to Clipboard",
      title: "Copy Image to Clipboard",
      onClick: function () {
        if (!currentImageDataUrl) {
          showError("No image available to copy.");
          return;
        }
        copyImageToClipboard(currentImageDataUrl).then(function () {
          statusBar.textContent = "Copied QR code image to clipboard.";
          if (window.FOSS.toast) window.FOSS.toast("Copied QR code image to clipboard.", "success");
        }).catch(function (err) {
          showError("Copy failed: " + (err && err.message ? err.message : String(err)));
        });
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Copy Image" })
    ]);

    var exportSvgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-svg-btn",
      "aria-label": "Export Vector SVG",
      title: "Export Vector SVG",
      onClick: function () {
        saveCodeFile("svg");
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "Export Vector SVG" })
    ]);

    var exportIcsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-ics-btn",
      "aria-label": "Save as .ics Event...",
      title: "Save as .ics Event...",
      style: { display: "none" },
      onClick: function () {
        exportCalendarIcs();
      }
    }, [
      window.FOSS.icons.el("calendar", 16),
      window.FOSS.dom.el("span", { text: "Save as .ics Event..." })
    ]);

    var exportLabelsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-labels-btn",
      "aria-label": "Print Label Sheet (PDF)...",
      title: "Print Label Sheet (PDF)...",
      onClick: function () {
        exportLabelSheetPdf();
      }
    }, [
      window.FOSS.icons.el("printer", 16),
      window.FOSS.dom.el("span", { text: "Print Label Sheet (PDF)..." })
    ]);

    var exportActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }
    }, [
      savePngBtn,
      formatSelect,
      saveImageBtn,
      copyBtn,
      exportSvgBtn,
      exportIcsBtn,
      exportLabelsBtn
    ]);

    exportCard.appendChild(exportTitle);
    exportCard.appendChild(exportActionsRow);

    stageCol.appendChild(previewCard);
    stageCol.appendChild(exportCard);

    // Workbench layout
    var workbench = window.FOSS.dom.el("div", {
      className: "qr-workbench",
      style: { width: "100%", height: "100%" }
    }, [
      sidebarCol,
      window.FOSS.dom.el("div", { className: "split-divider", "data-decorative": "true" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(workbench);

    function buildPayload() {
      var t = typeSelect.value;
      if (t === "url") {
        return urlInput.value || "https://github.com/fosseverything";
      } else if (t === "wifi") {
        return "WIFI:S:" + (wifiSsid.value || "Network") + ";T:" + wifiSec.value + ";P:" + (wifiPass.value || "") + ";H:" + (wifiHidden.checked ? "true" : "false") + ";;";
      } else if (t === "text") {
        return textInput.value || "Plain text notes";
      } else if (t === "vcard") {
        var lines = [
          "BEGIN:VCARD",
          "VERSION:3.0",
          "FN:" + (vcardName.value || "User"),
          "ORG:" + (vcardOrg.value || ""),
          "TITLE:" + (vcardTitle.value || ""),
          "TEL:" + (vcardPhone.value || ""),
          "EMAIL:" + (vcardEmail.value || ""),
          "END:VCARD"
        ];
        return lines.join("\n");
      } else if (t === "email") {
        var to = emailTo.value || "user@example.com";
        var q = [];
        if (emailSubject.value) q.push("subject=" + encodeURIComponent(emailSubject.value));
        if (emailBody.value) q.push("body=" + encodeURIComponent(emailBody.value));
        return "mailto:" + to + (q.length > 0 ? "?" + q.join("&") : "");
      } else if (t === "phone") {
        return "tel:" + (phoneInput.value || "+15550199");
      } else if (t === "sms") {
        return "SMSTO:" + (smsPhone.value || "+15550199") + ":" + (smsMsg.value || "");
      } else if (t === "whatsapp") {
        var digits = (waPhone.value || "").replace(/[^0-9]/g, "");
        var msg = encodeURIComponent(waMsg.value || "");
        return "https://wa.me/" + digits + (msg ? "?text=" + msg : "");
      } else if (t === "geo") {
        return "geo:" + (geoLat.value || "37.7749") + "," + (geoLon.value || "-122.4194");
      } else if (t === "calendar") {
        return "BEGIN:VEVENT\nSUMMARY:" + (calTitle.value || "Event") + "\nDTSTART:" + (calStart.value || "20261101T120000Z") + "\nEND:VEVENT";
      } else if (t === "asset") {
        return "ASSET:" + (assetId.value || "ASSET-1001") + ";LOC:" + (assetLocation.value || "HQ") + ";;";
      } else if (t === "barcode") {
        return barcodeVal.value || "12345678";
      }
      return urlInput.value || "https://example.com";
    }

    function refreshCode() {
      clearError();
      currentPayload = buildPayload();
      var t = typeSelect.value;

      if (t === "barcode") {
        var sym = barcodeSymbology.value || "code128";
        window.FOSS.api("qr_generate_barcode", {
          payload: currentPayload,
          barcode_type: sym,
          include_label: barcodeLabelToggle.checked
        }).then(function (res) {
          if (res && res.data_url) {
            currentImageDataUrl = res.data_url;
            previewImg.src = res.data_url;
            previewImg.style.setProperty("display", "block");
            previewEmpty.style.setProperty("display", "none");
            infoLabel.textContent = "Barcode: " + sym.toUpperCase() + " - Export Size: " + res.width + " x " + res.height + " px";
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      } else {
        var boxSize = parseInt(boxSizeInput.value, 10) || 10;
        var ecc = eccSelect.value || "M";
        window.FOSS.api("qr_generate", {
          payload: currentPayload,
          box_size: boxSize,
          fill_color: sharedState.fgColor,
          back_color: sharedState.bgColor,
          error_correction: ecc,
          logo_path: sharedState.logoPath || null
        }).then(function (res) {
          if (res && res.data_url) {
            currentImageDataUrl = res.data_url;
            previewImg.src = res.data_url;
            previewImg.style.setProperty("display", "block");
            previewEmpty.style.setProperty("display", "none");
            infoLabel.textContent = "QR Code - Export Size: " + res.width + " x " + res.height + " px | Error Correction: " + ecc;
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }

    function saveCodeFile(format) {
      clearError();
      currentPayload = buildPayload();
      var ext = (format || "png").toLowerCase();
      var filters = ext === "svg" ? [{ name: "SVG Vector", extensions: ["svg"] }] : [{ name: ext.toUpperCase() + " Image", extensions: [ext] }];

      window.FOSS.api("select_save_path", {
        title: "Save " + ext.toUpperCase() + " File",
        default_name: "code." + ext,
        filters: filters
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        if (ext === "svg") {
          window.FOSS.api("qr_generate_svg", {
            payload: currentPayload,
            output_path: outPath
          }).then(function (saveRes) {
            var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
            showResult(finalPath, "SVG Vector Exported");
            statusBar.textContent = "Saved SVG to " + finalPath;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        } else {
          var t = typeSelect.value;
          var apiMethod = t === "barcode" ? "qr_generate_barcode" : "qr_generate";
          var params = {
            payload: currentPayload,
            output_path: outPath
          };
          if (t === "barcode") {
            params.barcode_type = barcodeSymbology.value || "code128";
            params.include_label = barcodeLabelToggle.checked;
          } else {
            params.box_size = parseInt(boxSizeInput.value, 10) || 10;
            params.fill_color = sharedState.fgColor;
            params.back_color = sharedState.bgColor;
            params.error_correction = eccSelect.value || "M";
            params.logo_path = sharedState.logoPath || null;
          }

          window.FOSS.api(apiMethod, params).then(function (saveRes) {
            var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
            showResult(finalPath, "Image Saved");
            statusBar.textContent = "Saved to " + finalPath;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        }
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function exportCalendarIcs() {
      clearError();
      var sm = calTitle.value || "Event";
      var st = calStart.value || "20261101T120000Z";

      window.FOSS.api("select_save_path", {
        title: "Save as .ics File",
        default_name: "event.ics",
        filters: [{ name: "iCalendar File", extensions: ["ics"] }]
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        window.FOSS.api("qr_export_ics", {
          title: sm,
          start_time: st,
          output_path: outPath
        }).then(function (saveRes) {
          var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(finalPath, "Calendar .ICS File Saved");
          statusBar.textContent = "Saved .ics to " + finalPath;
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function exportLabelSheetPdf() {
      clearError();
      window.FOSS.api("qr_label_presets", {}).then(function (presetsRes) {
        var presets = (presetsRes && presetsRes.presets) || ["Avery 5160"];
        var presetToUse = presets[0] || "Avery 5160";

        window.FOSS.api("select_save_path", {
          title: "Save Printable Label Sheet (PDF)",
          default_name: "label_sheet.pdf",
          filters: [{ name: "PDF Document", extensions: ["pdf"] }]
        }).then(function (res) {
          var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outPath) return;

          var params = {
            payload: currentPayload,
            output_path: outPath,
            preset: presetToUse,
            count: 30
          };
          if (typeSelect.value === "barcode") {
            params.barcode_type = barcodeSymbology.value || "code128";
          }

          window.FOSS.api("qr_label_sheet", params).then(function (saveRes) {
            var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
            showResult(finalPath, "Label Sheet PDF Saved");
            statusBar.textContent = "Saved label sheet to " + finalPath;
          }).catch(function (err) {
            showError(err && err.message ? err.message : String(err));
          });
        });
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    updateContentFields();
    refreshCode();
  }

  function renderBarcodeTab(panel) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-qr-barcode");

    var currentPayload = "123456789012";
    var currentImageDataUrl = "";

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

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", {
      "data-testid": "qr-result",
      hidden: true
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "qr-result-card",
        title: titleText || "Export Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var sidebarCol = window.FOSS.dom.el("div", { className: "qr-sidebar-pane" });

    var configCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var configTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "1D Barcode Configuration" });

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
      window.FOSS.dom.el("option", { value: "code39", text: "Code 39 (Alphanumeric)" }),
      window.FOSS.dom.el("option", { value: "ean13", text: "EAN-13 (13 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "ean8", text: "EAN-8 (8 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "upca", text: "UPC-A (12 Digits Retail)" }),
      window.FOSS.dom.el("option", { value: "isbn13", text: "ISBN-13 (Books)" }),
      window.FOSS.dom.el("option", { value: "itf", text: "ITF (Interleaved 2 of 5)" })
    ]);

    var hintLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      text: "Supports all standard ASCII characters"
    });

    function updateValidationHint() {
      var sym = symbologySelect.value;
      if (sym === "ean13") {
        hintLabel.textContent = "Requires 12 or 13 digits (numeric)";
      } else if (sym === "ean8") {
        hintLabel.textContent = "Requires 7 or 8 digits (numeric)";
      } else if (sym === "upca") {
        hintLabel.textContent = "Requires 11 or 12 digits (numeric)";
      } else if (sym === "isbn13") {
        hintLabel.textContent = "Requires 12 or 13 digits (typically begins with 978 or 979)";
      } else if (sym === "itf") {
        hintLabel.textContent = "Requires an even number of numeric digits";
      } else if (sym === "code39") {
        hintLabel.textContent = "Supports uppercase letters, numbers, and - . $ / + % space";
      } else {
        hintLabel.textContent = "Supports all standard ASCII characters";
      }
    }

    var valueInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: "123456789012",
      placeholder: "Barcode value",
      "aria-label": "Barcode value",
      title: "Barcode value",
      onInput: refreshBarcode
    });

    var labelToggle = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "qr-barcode-toggle",
      "aria-label": "Show Value Label",
      title: "Show Value Label",
      onChange: refreshBarcode
    });

    var labelToggleRow = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { gap: "var(--space-2)", cursor: "pointer" }
    }, [
      labelToggle,
      window.FOSS.dom.el("span", { text: "Show Human-Readable Text Below Bars" })
    ]);

    var heightInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      value: "100",
      min: "30",
      max: "400",
      style: { width: "100px" },
      "aria-label": "Bar Height",
      title: "Bar Height",
      onInput: refreshBarcode
    });

    configCard.appendChild(configTitle);
    configCard.appendChild(window.FOSS.components.field("Symbology", symbologySelect));
    configCard.appendChild(hintLabel);
    configCard.appendChild(window.FOSS.components.field("Payload Value", valueInput));
    configCard.appendChild(labelToggleRow);
    configCard.appendChild(window.FOSS.components.field("Bar Height (px)", heightInput));

    sidebarCol.appendChild(configCard);

    var stageCol = window.FOSS.dom.el("div", { className: "qr-stage-pane" });

    var previewCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3 items-center" });
    var previewTitle = window.FOSS.dom.el("h3", { className: "card-title text-base self-start", text: "Barcode Preview" });

    var previewDisplay = window.FOSS.dom.el("div", {
      style: {
        width: "100%",
        minHeight: "220px",
        background: "var(--color-bg-base)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-3)"
      }
    });

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "qr-preview-img",
      alt: "Generated Barcode",
      style: {
        maxWidth: "100%",
        maxHeight: "260px",
        objectFit: "contain",
        display: "none"
      }
    });

    var previewEmpty = window.FOSS.dom.el("div", {
      className: "text-muted text-sm text-center",
      text: "Generating barcode..."
    });

    previewDisplay.appendChild(previewImg);
    previewDisplay.appendChild(previewEmpty);

    var infoLabel = window.FOSS.dom.el("div", {
      className: "text-xs text-muted font-mono",
      text: "1D Barcode - Ready"
    });

    previewCard.appendChild(previewTitle);
    previewCard.appendChild(previewDisplay);
    previewCard.appendChild(infoLabel);

    var exportCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var exportTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export Barcode" });

    var saveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "qr-save-image-btn",
      "aria-label": "Save Barcode Image",
      title: "Save Barcode Image",
      onClick: function () {
        saveBarcodeFile("png");
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Save PNG..." })
    ]);

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-copy-btn",
      "aria-label": "Copy Image",
      title: "Copy Image",
      onClick: function () {
        if (!currentImageDataUrl) return;
        copyImageToClipboard(currentImageDataUrl).then(function () {
          statusBar.textContent = "Copied barcode image to clipboard.";
          if (window.FOSS.toast) window.FOSS.toast("Copied barcode image to clipboard.", "success");
        });
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Copy Image" })
    ]);

    var labelsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-labels-btn",
      "aria-label": "Print Label Sheet",
      title: "Print Label Sheet",
      onClick: function () {
        exportBarcodeLabels();
      }
    }, [
      window.FOSS.icons.el("printer", 16),
      window.FOSS.dom.el("span", { text: "Print Label Sheet (PDF)..." })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }
    }, [saveBtn, copyBtn, labelsBtn]);

    exportCard.appendChild(exportTitle);
    exportCard.appendChild(actionsRow);

    stageCol.appendChild(previewCard);
    stageCol.appendChild(exportCard);

    var workbench = window.FOSS.dom.el("div", {
      className: "qr-workbench",
      style: { width: "100%", height: "100%" }
    }, [
      sidebarCol,
      window.FOSS.dom.el("div", { className: "split-divider", "data-decorative": "true" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(workbench);

    function refreshBarcode() {
      clearError();
      currentPayload = valueInput.value || "12345678";
      var sym = symbologySelect.value || "code128";
      var h = parseInt(heightInput.value, 10) || 100;

      window.FOSS.api("qr_generate_barcode", {
        payload: currentPayload,
        barcode_type: sym,
        include_label: labelToggle.checked,
        height: h
      }).then(function (res) {
        if (res && res.data_url) {
          currentImageDataUrl = res.data_url;
          previewImg.src = res.data_url;
          previewImg.style.setProperty("display", "block");
          previewEmpty.style.setProperty("display", "none");
          infoLabel.textContent = "1D Barcode: " + sym.toUpperCase() + " - " + res.width + " x " + res.height + " px";
        }
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function saveBarcodeFile(ext) {
      clearError();
      window.FOSS.api("select_save_path", {
        title: "Save Barcode Image",
        default_name: "barcode." + ext,
        filters: [{ name: "PNG Image", extensions: ["png"] }]
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        window.FOSS.api("qr_generate_barcode", {
          payload: currentPayload,
          barcode_type: symbologySelect.value || "code128",
          include_label: labelToggle.checked,
          height: parseInt(heightInput.value, 10) || 100,
          output_path: outPath
        }).then(function (saveRes) {
          var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(finalPath, "Barcode Saved");
          statusBar.textContent = "Saved to " + finalPath;
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      });
    }

    function exportBarcodeLabels() {
      clearError();
      window.FOSS.api("select_save_path", {
        title: "Save Barcode Label Sheet (PDF)",
        default_name: "barcode_labels.pdf",
        filters: [{ name: "PDF Document", extensions: ["pdf"] }]
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        window.FOSS.api("qr_label_sheet", {
          payload: currentPayload,
          output_path: outPath,
          preset: "Avery 5160",
          barcode_type: symbologySelect.value || "code128",
          count: 30
        }).then(function (saveRes) {
          var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(finalPath, "Label Sheet Saved");
          statusBar.textContent = "Saved to " + finalPath;
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      });
    }

    updateValidationHint();
    refreshBarcode();
  }

  function renderScanTab(panel) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-qr-scan");

    var currentScanImagePath = "";

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

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var sidebarCol = window.FOSS.dom.el("div", { className: "qr-sidebar-pane" });

    var inputCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    var inputTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Choose or Paste Image" });

    var scanPicker = window.FOSS.components.filePicker({
      testid: "qr-scan-file-picker",
      title: "Select Image or PDF to Scan",
      fileTypes: ["png", "jpg", "jpeg", "webp", "pdf", "bmp"],
      onSelect: function (val) {
        currentScanImagePath = val;
        clearError();
        if (val) executeScan(val);
      },
      onClear: function () {
        currentScanImagePath = "";
        sharedState.lastDecodedItems = [];
        renderDecodedResults();
      }
    });

    var pasteBanner = window.FOSS.dom.el("div", {
      className: "p-3 rounded text-center text-sm text-muted",
      style: {
        border: "1px dashed var(--color-border)",
        background: "var(--color-bg-subtle)",
        cursor: "pointer"
      },
      text: "Paste screenshot from clipboard (Ctrl+V) anywhere on this screen"
    });

    inputCard.appendChild(inputTitle);
    inputCard.appendChild(scanPicker.el);
    inputCard.appendChild(pasteBanner);

    var detailsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-2" });
    var detailsTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Details" });
    var detailsContent = window.FOSS.dom.el("div", {
      className: "text-sm text-muted font-mono p-2 rounded",
      style: { background: "var(--color-bg-base)", border: "1px solid var(--color-border)", minHeight: "60px", wordBreak: "break-all" },
      text: "No code selected"
    });
    detailsCard.appendChild(detailsTitle);
    detailsCard.appendChild(detailsContent);

    sidebarCol.appendChild(inputCard);
    sidebarCol.appendChild(detailsCard);

    var stageCol = window.FOSS.dom.el("div", { className: "qr-stage-pane" });

    var resultsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-scan-results"
    });
    var resultsTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Decoded Results" });

    var resultsList = window.FOSS.dom.el("div", {
      className: "flex-col gap-2 scroll-y",
      style: { maxHeight: "500px", width: "100%" }
    });

    resultsCard.appendChild(resultsTitle);
    resultsCard.appendChild(resultsList);
    stageCol.appendChild(resultsCard);

    var workbench = window.FOSS.dom.el("div", {
      className: "qr-workbench",
      style: { width: "100%", height: "100%" }
    }, [
      sidebarCol,
      window.FOSS.dom.el("div", { className: "split-divider", "data-decorative": "true" }),
      stageCol
    ]);

    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(workbench);

    function executeScan(imgPath) {
      clearError();
      statusBar.textContent = "Scanning image for QR and barcodes...";
      window.FOSS.api("qr_decode", { image_path: imgPath }).then(function (res) {
        sharedState.lastDecodedItems = (res && res.results) || [];
        renderDecodedResults();
        statusBar.textContent = "Scan complete: Found " + sharedState.lastDecodedItems.length + " code(s).";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function executeDecodeDataUrl(dataUrl) {
      clearError();
      statusBar.textContent = "Decoding pasted screenshot...";
      window.FOSS.api("qr_decode_data_url", { data_url: dataUrl }).then(function (res) {
        sharedState.lastDecodedItems = (res && res.results) || [];
        renderDecodedResults();
        statusBar.textContent = "Pasted scan complete: Found " + sharedState.lastDecodedItems.length + " code(s).";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
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
                executeDecodeDataUrl(evt.target.result);
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
    panel._cleanup = function () {
      window.removeEventListener("paste", onPaste);
    };

    function renderDecodedResults() {
      resultsList.innerHTML = "";
      if (sharedState.lastDecodedItems.length === 0) {
        resultsList.innerHTML = '<div class="text-sm text-muted p-4 text-center">No QR codes or barcodes detected yet. Select an image or paste a screenshot.</div>';
        detailsContent.textContent = "No code selected";
        return;
      }

      for (var i = 0; i < sharedState.lastDecodedItems.length; i++) {
        var item = sharedState.lastDecodedItems[i];
        var itemData = item.data || item.payload || "";
        var itemType = item.type || "QR Code";

        var copyBtn = window.FOSS.dom.el("button", {
          className: "btn btn-sm",
          "aria-label": "Copy payload: " + itemData,
          title: "Copy text",
          onClick: (function (d) {
            return function (ev) {
              ev.stopPropagation();
              copyTextToClipboard(d);
              statusBar.textContent = "Copied code data to clipboard.";
              if (window.FOSS.toast) window.FOSS.toast("Copied code data to clipboard.", "success");
            };
          })(itemData)
        }, [
          window.FOSS.icons.el("copy", 14),
          window.FOSS.dom.el("span", { text: "Copy" })
        ]);

        var actionBtns = [copyBtn];
        if (itemData.startsWith("http://") || itemData.startsWith("https://")) {
          var openBtn = window.FOSS.dom.el("button", {
            className: "btn btn-sm btn-secondary",
            "aria-label": "Open link in browser",
            title: "Open URL",
            onClick: (function (u) {
              return function (ev) {
                ev.stopPropagation();
                window.FOSS.api("open_url", { url: u });
              };
            })(itemData)
          }, [
            window.FOSS.icons.el("external-link", 14),
            window.FOSS.dom.el("span", { text: "Open URL" })
          ]);
          actionBtns.push(openBtn);
        }

        var row = window.FOSS.dom.el("div", {
          className: "row items-center justify-between p-3 rounded",
          style: {
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--space-2)",
            background: "var(--color-bg-muted)",
            border: "1px solid var(--color-border)",
            width: "100%",
            cursor: "pointer"
          }
        }, [
          window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "140px" } }, [
            window.FOSS.dom.el("span", { className: "font-bold text-sm", text: itemType }),
            window.FOSS.dom.el("span", { className: "font-mono text-xs text-muted", text: itemData })
          ]),
          window.FOSS.dom.el("div", { className: "row", style: { gap: "var(--space-2)" } }, actionBtns)
        ]);

        row.addEventListener("click", (function (it) {
          return function () {
            detailsContent.textContent = (it.type || "Code") + ": " + (it.data || it.payload || "");
          };
        })(item));

        resultsList.appendChild(row);
      }
      detailsContent.textContent = (sharedState.lastDecodedItems[0].type || "Code") + ": " + (sharedState.lastDecodedItems[0].data || sharedState.lastDecodedItems[0].payload || "");
    }

    renderDecodedResults();
  }

  window.FOSS.router.register({
    id: "qr",
    title: "QR Code Generator",
    navName: "QR & Barcodes",
    category: "Utilities",
    icon: "grid",
    workbench: true,
    tabs: [
      { id: "qr", label: "QR Generator", aliases: ["main", "generate"], render: renderQRTab },
      { id: "barcode", label: "1D Barcodes", render: renderBarcodeTab },
      { id: "scan", label: "Scan & Decode", render: renderScanTab }
    ],
    onHide: function () {
      var panel = document.getElementById("view-root");
      if (panel && panel._cleanup) {
        panel._cleanup();
      }
    }
  });
})();
