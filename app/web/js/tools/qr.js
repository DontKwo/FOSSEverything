// QR Codes and Barcodes workspace: generator, scanner, custom styles, logos, vector SVG, and label sheets.
window.FOSS = window.FOSS || {};

(function () {
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
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

  function renderQR(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-qr");

    var activeTab = "generate";
    var currentPayload = "https://github.com/fosseverything";
    var currentFgColor = "#000000";
    var currentBgColor = "#FFFFFF";
    var currentLogoPath = "";
    var currentImageDataUrl = "";
    var currentScanImagePath = "";
    var lastDecodedItems = [];

    // Header
    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", {
        className: "card-title",
        text: "QR Code Generator"
      }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Generate custom QR codes 100% offline. No internet required."
      })
    ]);

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

    // Top Tabs: QR Generator / Scan & Decode
    var tabGenBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "qr-tab-generate",
      "aria-label": "QR Generator",
      title: "QR Generator",
      onClick: function () {
        switchTab("generate");
      }
    }, [
      window.FOSS.icons.el("grid", 16),
      window.FOSS.dom.el("span", { text: "QR Generator" })
    ]);

    var tabScanBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-tab-scan",
      "aria-label": "Scan & Decode",
      title: "Scan & Decode",
      onClick: function () {
        switchTab("scan");
      }
    }, [
      window.FOSS.icons.el("camera", 16),
      window.FOSS.dom.el("span", { text: "Scan & Decode" })
    ]);

    var tabNav = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-2)",
        borderBottom: "1px solid var(--color-border)",
        paddingBottom: "var(--space-2)",
        width: "100%"
      }
    }, [
      tabGenBtn,
      tabScanBtn
    ]);

    // PANE 1: QR Generator
    var genPane = window.FOSS.dom.el("div", {
      className: "flex-col gap-4",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });

    // Left Column: Configuration Forms
    var configCol = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { flex: "1 1 340px", minWidth: "0", maxWidth: "100%", width: "100%" }
    });

    // Group 1: Payload Type
    var typeCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      "data-testid": "qr-templates-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var typeTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Type" });

    var typeSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-payload-type",
      "aria-label": "Payload Type",
      title: "Payload Type",
      style: { width: "100%" },
      onChange: function () {
        updateContentFields();
        refreshCode();
      }
    }, [
      window.FOSS.dom.el("option", { value: "url", text: "URL / Web Link" }),
      window.FOSS.dom.el("option", { value: "wifi", text: "Wi-Fi Network" }),
      window.FOSS.dom.el("option", { value: "text", text: "Plain Text" }),
      window.FOSS.dom.el("option", { value: "vcard", text: "Contact Card (vCard)" }),
      window.FOSS.dom.el("option", { value: "mecard", text: "Business Card (MeCard)" }),
      window.FOSS.dom.el("option", { value: "email", text: "Email Address" }),
      window.FOSS.dom.el("option", { value: "phone", text: "Phone Number" }),
      window.FOSS.dom.el("option", { value: "sms", text: "SMS Message" }),
      window.FOSS.dom.el("option", { value: "whatsapp", text: "WhatsApp Message" }),
      window.FOSS.dom.el("option", { value: "geo", text: "Geo Location" }),
      window.FOSS.dom.el("option", { value: "calendar", text: "Calendar Event" }),
      window.FOSS.dom.el("option", { value: "asset", text: "Asset / Inventory Tag" }),
      window.FOSS.dom.el("option", { value: "barcode", text: "Barcode" })
    ]);

    typeCard.appendChild(typeTitle);
    typeCard.appendChild(typeSelect);

    // Group 2: Content Details
    var contentCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-content-details",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var contentTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Content Details" });
    var contentBody = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    contentCard.appendChild(contentTitle);
    contentCard.appendChild(contentBody);

    // Dynamic Input References
    var urlInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      value: "https://github.com/fosseverything",
      placeholder: "https://example.com",
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

    var textInput = window.FOSS.dom.el("textarea", {
      className: "input",
      rows: "3",
      placeholder: "enter arbitrary text or notes",
      "aria-label": "Arbitrary text notes",
      title: "Arbitrary text notes",
      onInput: refreshCode
    });

    var vcardName = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Full Name", "aria-label": "Full Name", title: "Full Name", style: { minHeight: "36px" }, onInput: refreshCode });
    var vcardPhone = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Phone Number", "aria-label": "Phone Number", title: "Phone Number", style: { minHeight: "36px" }, onInput: refreshCode });
    var vcardEmail = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Email Address", "aria-label": "Email Address", title: "Email Address", style: { minHeight: "36px" }, onInput: refreshCode });

    var calTitle = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Event Title", "aria-label": "Event Title", title: "Event Title", style: { minHeight: "36px" }, onInput: refreshCode });
    var calStart = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "YYYYMMDDTHHMMSSZ", value: "20261101T120000Z", "aria-label": "Start Time", title: "Start Time", style: { minHeight: "36px" }, onInput: refreshCode });

    var assetId = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "abc123", "aria-label": "Asset ID", title: "Asset ID", style: { minHeight: "36px" }, onInput: refreshCode });
    var assetLocation = window.FOSS.dom.el("input", { type: "text", className: "input", placeholder: "Location / Room", "aria-label": "Location", title: "Location", style: { minHeight: "36px" }, onInput: refreshCode });

    var barcodeSymbology = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "qr-barcode-symbology",
      "aria-label": "Barcode Symbology",
      title: "Barcode Symbology",
      style: { minHeight: "36px" },
      onChange: refreshCode
    }, [
      window.FOSS.dom.el("option", { value: "code39", text: "Code 39" }),
      window.FOSS.dom.el("option", { value: "code128", text: "Code 128" }),
      window.FOSS.dom.el("option", { value: "ean13", text: "EAN-13" }),
      window.FOSS.dom.el("option", { value: "ean8", text: "EAN-8" }),
      window.FOSS.dom.el("option", { value: "upca", text: "UPC-A" }),
      window.FOSS.dom.el("option", { value: "itf", text: "ITF" })
    ]);

    var barcodeVal = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: "12345678",
      placeholder: "Barcode numeric or alphanumeric value",
      "aria-label": "Barcode value",
      title: "Barcode value",
      style: { minHeight: "36px" },
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
      } else if (t === "text") {
        contentBody.appendChild(window.FOSS.components.field("Plain Text", textInput));
      } else if (t === "vcard" || t === "mecard") {
        contentBody.appendChild(window.FOSS.components.field("Name", vcardName));
        contentBody.appendChild(window.FOSS.components.field("Phone", vcardPhone));
        contentBody.appendChild(window.FOSS.components.field("Email", vcardEmail));
      } else if (t === "calendar") {
        contentBody.appendChild(window.FOSS.components.field("Event Title", calTitle));
        contentBody.appendChild(window.FOSS.components.field("Start Time", calStart));
      } else if (t === "asset") {
        contentBody.appendChild(window.FOSS.components.field("Asset ID", assetId));
        contentBody.appendChild(window.FOSS.components.field("Location", assetLocation));
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
    }
    updateContentFields();

    // Group 3: Styling & Resolution
    var styleCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-styling-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var styleTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Styling & Resolution" });

    // Foreground Color Controls
    var fgInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: "#000000",
      style: { width: "100px" },
      "aria-label": "Foreground color hex",
      title: "Foreground color hex",
      onInput: function () {
        currentFgColor = fgInput.value;
        fgColorPicker.value = currentFgColor;
        refreshCode();
      }
    });

    var fgColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      value: "#000000",
      hidden: true,
      "aria-label": "Foreground color picker",
      title: "Foreground color picker",
      onChange: function () {
        currentFgColor = fgColorPicker.value;
        fgInput.value = currentFgColor;
        refreshCode();
      }
    });

    var fgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "aria-label": "Foreground Color",
      title: "Foreground Color",
      onClick: function () {
        fgColorPicker.click();
      }
    }, [
      window.FOSS.icons.el("palette", 14),
      window.FOSS.dom.el("span", { text: "Foreground Color" })
    ]);

    var fgRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)" }
    }, [
      fgBtn,
      fgInput,
      fgColorPicker
    ]);

    // Background Color Controls
    var bgInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      value: "#FFFFFF",
      style: { width: "100px" },
      "aria-label": "Background color hex",
      title: "Background color hex",
      onInput: function () {
        currentBgColor = bgInput.value;
        bgColorPicker.value = currentBgColor;
        refreshCode();
      }
    });

    var bgColorPicker = window.FOSS.dom.el("input", {
      type: "color",
      value: "#FFFFFF",
      hidden: true,
      "aria-label": "Background color picker",
      title: "Background color picker",
      onChange: function () {
        currentBgColor = bgColorPicker.value;
        bgInput.value = currentBgColor;
        refreshCode();
      }
    });

    var bgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "aria-label": "Background Color",
      title: "Background Color",
      onClick: function () {
        bgColorPicker.click();
      }
    }, [
      window.FOSS.icons.el("palette", 14),
      window.FOSS.dom.el("span", { text: "Background Color" })
    ]);

    var bgRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)" }
    }, [
      bgBtn,
      bgInput,
      bgColorPicker
    ]);

    // Error Correction
    var eccSelect = window.FOSS.dom.el("select", {
      className: "input",
      "aria-label": "Error Correction",
      title: "Error Correction",
      onChange: refreshCode
    }, [
      window.FOSS.dom.el("option", { value: "L", text: "L - Low (~7% recovery)" }),
      window.FOSS.dom.el("option", { value: "M", selected: true, text: "M - Standard (~15% recovery)" }),
      window.FOSS.dom.el("option", { value: "Q", text: "Q - Medium-High (~25% recovery)" }),
      window.FOSS.dom.el("option", { value: "H", text: "H - Highest (~30% recovery, best with logos)" })
    ]);

    // Box Size
    var boxSizeInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      value: "10",
      min: "1",
      max: "40",
      style: { width: "80px" },
      "aria-label": "Box Size",
      title: "Box Size",
      onInput: refreshCode
    });

    var styleGrid = window.FOSS.dom.el("div", {
      className: "flex-col gap-2",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
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
      "data-testid": "qr-logo-group",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var logoTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Center Logo / Icon Embedding" });

    var logoStatusLabel = window.FOSS.dom.el("span", {
      className: "text-sm text-muted",
      text: "No logo selected"
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
            currentLogoPath = res.paths[0];
            logoStatusLabel.textContent = currentLogoPath.split(/[/\\]/).pop();
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
        currentLogoPath = "";
        logoStatusLabel.textContent = "No logo selected";
        refreshCode();
      }
    }, [
      window.FOSS.icons.el("trash-2", 14),
      window.FOSS.dom.el("span", { text: "Clear" })
    ]);

    var logoActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { gap: "var(--space-2)" }
    }, [
      chooseLogoBtn,
      clearLogoBtn,
      logoStatusLabel
    ]);

    logoCard.appendChild(logoTitle);
    logoCard.appendChild(logoActionsRow);

    configCol.appendChild(typeCard);
    configCol.appendChild(contentCard);
    configCol.appendChild(styleCard);
    configCol.appendChild(logoCard);

    // Right Column: Live Preview & Export
    var previewCol = window.FOSS.dom.el("div", {
      className: "flex-col gap-3",
      style: { flex: "1 1 320px", minWidth: "0", maxWidth: "100%", width: "100%" }
    });

    // Group 5: Live Preview
    var previewCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3 items-center",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
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
      text: "export size: 330x330 px"
    });

    previewCard.appendChild(previewTitle);
    previewCard.appendChild(previewDisplay);
    previewCard.appendChild(infoLabel);

    // Group 6: Export & Share
    var exportCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var exportTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Export & Share" });

    var saveImageBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "qr-save-image-btn",
      "aria-label": "Save Image (PNG / JPEG / WEBP / PDF)",
      title: "Save Image (PNG / JPEG / WEBP / PDF)",
      onClick: function () {
        saveCodeFile("png");
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Save Image (PNG / JPEG / WEBP / PDF)" })
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
        copyToClipboard(currentImageDataUrl);
        statusBar.textContent = "Copied QR code data to clipboard.";
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Copy Image to Clipboard" })
    ]);

    var exportSvgBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-svg-btn",
      "aria-label": "Export Vector SVG (Lossless Print)",
      title: "Export Vector SVG (Lossless Print)",
      onClick: function () {
        saveCodeFile("svg");
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "Export Vector SVG (Lossless Print)" })
    ]);

    var exportIcsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-ics-btn",
      "aria-label": "Save as .ics File",
      title: "Save as .ics File",
      onClick: function () {
        exportCalendarIcs();
      }
    }, [
      window.FOSS.icons.el("calendar", 16),
      window.FOSS.dom.el("span", { text: "Save as .ics File" })
    ]);

    var exportLabelsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "qr-export-labels-btn",
      "aria-label": "Print Label Sheet (PDF)",
      title: "Print Label Sheet (PDF)",
      onClick: function () {
        exportLabelSheetPdf();
      }
    }, [
      window.FOSS.icons.el("printer", 16),
      window.FOSS.dom.el("span", { text: "Print Label Sheet (PDF)" })
    ]);

    var exportActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-2)",
        width: "100%"
      }
    }, [
      saveImageBtn,
      copyBtn,
      exportSvgBtn,
      exportIcsBtn,
      exportLabelsBtn
    ]);

    exportCard.appendChild(exportTitle);
    exportCard.appendChild(exportActionsRow);

    previewCol.appendChild(previewCard);
    previewCol.appendChild(exportCard);

    var genColumns = window.FOSS.dom.el("div", {
      className: "row items-start",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-4)",
        width: "100%"
      }
    }, [
      configCol,
      previewCol
    ]);

    genPane.appendChild(genColumns);

    // PANE 2: Scan & Decode
    var scanPane = window.FOSS.dom.el("div", {
      className: "flex-col gap-4",
      hidden: true,
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });

    var scanIntroCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    }, [
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Open an image/PDF or paste a screenshot to detect QR codes and barcodes."
      })
    ]);

    // Group: Input Image Preview
    var scanInputCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var scanInputTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Input Image Preview" });

    var scanPicker = window.FOSS.components.filePicker({
      testid: "qr-scan-file-picker",
      title: "Select Image or PDF to Scan",
      fileTypes: ["png", "jpg", "jpeg", "webp", "pdf", "bmp"],
      onSelect: function (val) {
        currentScanImagePath = val;
        clearError();
        if (val) {
          executeScan(val);
        }
      },
      onClear: function () {
        currentScanImagePath = "";
        lastDecodedItems = [];
        renderDecodedResults();
      }
    });

    var webcamBtn = window.FOSS.dom.el("button", {
      className: "btn",
      "data-testid": "qr-webcam-scan-btn",
      "aria-label": "Direct webcam scanning",
      title: "Direct webcam scanning",
      onClick: function () {
        showError("Webcam scan initialized: No local camera feed connected.");
      }
    }, [
      window.FOSS.icons.el("video", 16),
      window.FOSS.dom.el("span", { text: "Scan from Webcam" })
    ]);

    var scanActionsRow = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-2)",
        width: "100%"
      }
    }, [
      webcamBtn
    ]);

    scanInputCard.appendChild(scanInputTitle);
    scanInputCard.appendChild(scanPicker.el);
    scanInputCard.appendChild(scanActionsRow);

    // Group: Decoded Results
    var resultsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-3",
      "data-testid": "qr-scan-results",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var resultsTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Decoded Results" });

    var resultsList = window.FOSS.dom.el("div", {
      className: "flex-col gap-3 scroll-y",
      style: { maxHeight: "400px", width: "100%" }
    });

    resultsCard.appendChild(resultsTitle);
    resultsCard.appendChild(resultsList);

    // Group: Payload Details
    var detailsCard = window.FOSS.dom.el("div", {
      className: "card flex-col gap-2",
      style: { width: "100%", maxWidth: "100%", minWidth: "0" }
    });
    var detailsTitle = window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Payload Details" });
    var detailsContent = window.FOSS.dom.el("div", {
      className: "text-sm text-muted",
      text: "No code selected"
    });
    detailsCard.appendChild(detailsTitle);
    detailsCard.appendChild(detailsContent);

    scanPane.appendChild(scanIntroCard);
    scanPane.appendChild(scanInputCard);
    scanPane.appendChild(resultsCard);
    scanPane.appendChild(detailsCard);

    // Page Assembly
    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(tabNav);
    panel.appendChild(genPane);
    panel.appendChild(scanPane);

    // Tab Switching
    function switchTab(tabId) {
      activeTab = tabId;
      if (tabId === "generate") {
        genPane.removeAttribute("hidden");
        scanPane.setAttribute("hidden", "true");
        tabGenBtn.className = "btn btn-primary";
        tabScanBtn.className = "btn";
      } else {
        genPane.setAttribute("hidden", "true");
        scanPane.removeAttribute("hidden");
        tabGenBtn.className = "btn";
        tabScanBtn.className = "btn btn-primary";
        renderDecodedResults();
      }
    }

    // Generator Refresh
    function getPayloadString() {
      var t = typeSelect.value;
      if (t === "url") {
        return urlInput.value || "https://github.com/fosseverything";
      } else if (t === "wifi") {
        var h = false;
        return "WIFI:S:" + (wifiSsid.value || "Network") + ";T:" + wifiSec.value + ";P:" + wifiPass.value + ";H:" + h + ";;";
      } else if (t === "text") {
        return textInput.value || "Arbitrary text notes";
      } else if (t === "vcard") {
        var n = vcardName.value || "User";
        var p = vcardPhone.value || "";
        var e = vcardEmail.value || "";
        return "BEGIN:VCARD\nVERSION:3.0\nFN:" + n + "\nTEL:" + p + "\nEMAIL:" + e + "\nEND:VCARD";
      } else if (t === "mecard") {
        return "MECARD:N:" + (vcardName.value || "User") + ";TEL:" + vcardPhone.value + ";EMAIL:" + vcardEmail.value + ";;";
      } else if (t === "calendar") {
        var sm = calTitle.value || "Event";
        var st = calStart.value || "20261101T120000Z";
        return "BEGIN:VEVENT\nSUMMARY:" + sm + "\nDTSTART:" + st + "\nEND:VEVENT";
      } else if (t === "asset") {
        return "ASSET:" + (assetId.value || "ABC123") + ";LOC:" + (assetLocation.value || "HQ") + ";;";
      } else if (t === "barcode") {
        return barcodeVal.value || "12345678";
      }
      return urlInput.value || "https://example.com";
    }

    function refreshCode() {
      clearError();
      var t = typeSelect.value;
      currentPayload = getPayloadString();

      if (t === "barcode") {
        var sym = barcodeSymbology.value || "code39";
        var showLbl = barcodeLabelToggle.checked;
        window.FOSS.api("qr_generate_barcode", {
          payload: currentPayload,
          barcode_type: sym,
          include_label: showLbl
        }).then(function (res) {
          if (res && res.data_url) {
            currentImageDataUrl = res.data_url;
            previewImg.src = res.data_url;
            previewImg.style.setProperty("display", "block");
            previewEmpty.style.setProperty("display", "none");
            infoLabel.textContent = "export size: " + res.width + "x" + res.height + " px | " + sym.toUpperCase();
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
          fill_color: currentFgColor,
          back_color: currentBgColor,
          error_correction: ecc,
          logo_path: currentLogoPath || null
        }).then(function (res) {
          if (res && res.data_url) {
            currentImageDataUrl = res.data_url;
            previewImg.src = res.data_url;
            previewImg.style.setProperty("display", "block");
            previewEmpty.style.setProperty("display", "none");
            infoLabel.textContent = "export size: " + res.width + "x" + res.height + " px | Payload: " + currentPayload.length + " chars";
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }
    }

    // Save Code File
    function saveCodeFile(type) {
      clearError();
      var ext = type === "svg" ? "svg" : "png";
      var filters = type === "svg" ? [{ name: "SVG Vector", extensions: ["svg"] }] : [{ name: "PNG Image", extensions: ["png"] }];

      window.FOSS.api("select_save_path", {
        title: "Save " + (type === "svg" ? "Vector SVG" : "Image"),
        default_name: "qrcode." + ext,
        filters: filters
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        if (type === "svg") {
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
            params.barcode_type = barcodeSymbology.value || "code39";
            params.include_label = barcodeLabelToggle.checked;
          } else {
            params.box_size = parseInt(boxSizeInput.value, 10) || 10;
            params.fill_color = currentFgColor;
            params.back_color = currentBgColor;
            params.error_correction = eccSelect.value || "M";
            params.logo_path = currentLogoPath || null;
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

    // Export .ics Calendar File
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

    // Export Printable Label Sheet PDF
    function exportLabelSheetPdf() {
      clearError();
      window.FOSS.api("select_save_path", {
        title: "Save Printable Label Sheet (PDF)",
        default_name: "label_sheet.pdf",
        filters: [{ name: "PDF Document", extensions: ["pdf"] }]
      }).then(function (res) {
        var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
        if (!outPath) return;

        var t = typeSelect.value;
        var params = {
          payload: currentPayload,
          output_path: outPath,
          preset: "Avery 5160",
          count: 30
        };
        if (t === "barcode") {
          params.barcode_type = barcodeSymbology.value || "code39";
        }

        window.FOSS.api("qr_label_sheet", params).then(function (saveRes) {
          var finalPath = saveRes && saveRes.output_path ? saveRes.output_path : outPath;
          showResult(finalPath, "Label Sheet PDF Saved");
          statusBar.textContent = "Saved label sheet to " + finalPath;
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    // Scanner Execution
    function executeScan(imgPath) {
      clearError();
      statusBar.textContent = "Scanning image for QR and barcodes...";
      window.FOSS.api("qr_decode", { image_path: imgPath }).then(function (res) {
        lastDecodedItems = (res && res.results) || [];
        renderDecodedResults();
        statusBar.textContent = "Scan complete: Found " + lastDecodedItems.length + " code(s).";
      }).catch(function (err) {
        showError(err && err.message ? err.message : String(err));
      });
    }

    function renderDecodedResults() {
      resultsList.innerHTML = "";
      if (lastDecodedItems.length === 0) {
        resultsList.innerHTML = '<div class="text-sm text-muted p-4 text-center">no qr codes or barcodes detected in image.</div>';
        detailsContent.textContent = "no code selected";
        return;
      }

      for (var i = 0; i < lastDecodedItems.length; i++) {
        var item = lastDecodedItems[i];
        var itemData = item.data || item.payload || "";
        var itemType = item.type || "QR Code";

        var actionBtn = window.FOSS.dom.el("button", {
          className: "btn btn-sm",
          "data-testid": "qr-scan-action-btn",
          "aria-label": "Copy payload: " + itemData,
          title: "Copy text",
          onClick: (function (d) {
            return function () {
              copyToClipboard(d);
              statusBar.textContent = "Copied code data to clipboard.";
            };
          })(itemData)
        }, [
          window.FOSS.icons.el("copy", 14),
          window.FOSS.dom.el("span", { text: "Copy" })
        ]);

        var row = window.FOSS.dom.el("div", {
          className: "row items-center justify-between p-3 rounded",
          style: {
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--space-2)",
            background: "var(--color-bg-muted)",
            border: "1px solid var(--color-border)",
            width: "100%"
          }
        }, [
          window.FOSS.dom.el("div", { className: "flex-col flex-1", style: { minWidth: "140px" } }, [
            window.FOSS.dom.el("span", { className: "font-bold text-sm", text: itemType }),
            window.FOSS.dom.el("span", { className: "font-mono text-xs text-muted", text: itemData })
          ]),
          actionBtn
        ]);

        row.addEventListener("click", (function (it) {
          return function () {
            detailsContent.textContent = (it.type || "Code") + ": " + (it.data || it.payload || "");
          };
        })(item));

        resultsList.appendChild(row);
      }
      detailsContent.textContent = (lastDecodedItems[0].type || "Code") + ": " + (lastDecodedItems[0].data || lastDecodedItems[0].payload || "");
    }

    // Initial render
    refreshCode();
  }

  window.FOSS.router.register({
    id: "qr",
    title: "QR Code Generator",
    navName: "QR & Barcodes",
    category: "Utilities",
    icon: "grid",
    tabs: [
      { id: "main", label: "QR Generator", render: renderQR }
    ]
  });
})();
