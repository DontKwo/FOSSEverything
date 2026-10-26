// Encoding and decoding tool workspace for text and file transformations.
window.FOSS = window.FOSS || {};

(function () {
  function renderTextTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Encode and decode text and files between Base64, URL/percent-encoding, HTML entities, hex, and binary."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "encoding-text-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var schemeSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "encoding-text-scheme",
      "aria-label": "Scheme"
    }, [
      window.FOSS.dom.el("option", { value: "Base64", text: "Base64" }),
      window.FOSS.dom.el("option", { value: "URL", text: "URL" }),
      window.FOSS.dom.el("option", { value: "HTML", text: "HTML" }),
      window.FOSS.dom.el("option", { value: "Hex", text: "Hex" })
    ]);

    var schemeField = window.FOSS.components.field("Scheme:", schemeSelect, null, false, "encoding-text-scheme-field");

    var optionSwitch = window.FOSS.components.switch({
      testid: "encoding-text-option",
      label: "URL-safe alphabet",
      checked: false
    });

    function updateOptionLabel() {
      var s = schemeSelect.value;
      if (s === "Base64") {
        optionSwitch.setLabel("URL-safe alphabet");
      } else if (s === "URL") {
        optionSwitch.setLabel("Preserve reserved characters (full URL)");
      } else if (s === "HTML") {
        optionSwitch.setLabel("Numeric character references");
      } else if (s === "Hex") {
        optionSwitch.setLabel("Space-separated bytes");
      }
    }

    schemeSelect.addEventListener("change", updateOptionLabel);

    var editor = window.FOSS.components.codeEditor({
      testid: "encoding-text-editor",
      placeholder: "Type or paste text/encoded data here..."
    });

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "encoding-text-status",
      text: "Ready"
    });

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
      statusBar.textContent = "Error: " + msg;
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var encodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "encoding-text-encode",
      type: "button",
      onClick: function () {
        clearError();
        var txt = editor.getValue();
        if (!txt) {
          statusBar.textContent = "Ready";
          return;
        }
        var s = schemeSelect.value;
        var opt = optionSwitch.isChecked();
        var apiMethod = "encoding_base64_encode_text";
        var params = { text: txt };

        if (s === "Base64") {
          apiMethod = "encoding_base64_encode_text";
          params.url_safe = opt;
        } else if (s === "URL") {
          apiMethod = "encoding_url_encode";
          params.full_url = opt;
        } else if (s === "HTML") {
          apiMethod = opt ? "encoding_html_encode_numeric" : "encoding_html_encode";
        } else if (s === "Hex") {
          apiMethod = "encoding_hex_encode_text";
          params.spaced = opt;
        }

        window.FOSS.api(apiMethod, params).then(function (res) {
          if (res && res.ok) {
            editor.setValue(res.result);
            statusBar.textContent = "[OK] Encoded with " + s;
          } else {
            showError((res && res.error) || "Encoding failed");
          }
        });
      }
    }, [
      window.FOSS.icons.el("play", 16),
      window.FOSS.dom.el("span", { text: "Encode" })
    ]);

    var decodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "encoding-text-decode",
      type: "button",
      onClick: function () {
        clearError();
        var txt = editor.getValue();
        if (!txt) {
          statusBar.textContent = "Ready";
          return;
        }
        var s = schemeSelect.value;
        var opt = optionSwitch.isChecked();
        var apiMethod = "encoding_base64_decode_text";
        var params = { text: txt };

        if (s === "Base64") {
          apiMethod = "encoding_base64_decode_text";
          params.url_safe = opt;
        } else if (s === "URL") {
          apiMethod = "encoding_url_decode";
        } else if (s === "HTML") {
          apiMethod = "encoding_html_decode";
        } else if (s === "Hex") {
          apiMethod = "encoding_hex_decode_text";
        }

        window.FOSS.api(apiMethod, params).then(function (res) {
          if (res && res.ok) {
            editor.setValue(res.result);
            statusBar.textContent = "[OK] Decoded with " + s;
          } else {
            showError((res && res.error) || "Decoding failed");
          }
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Decode" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row",
      gap: "sm"
    }, [encodeBtn, decodeBtn]);

    var controlsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "md"
    }, [
      window.FOSS.dom.el("div", { className: "row", gap: "lg" }, [schemeField, optionSwitch.el]),
      actionsRow
    ]);

    var editorCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      editor.el,
      statusBar
    ]);

    panel.appendChild(window.FOSS.dom.el("div", { className: "page stack", gap: "md" }, [
      desc,
      errorBanner,
      controlsCard,
      editorCard
    ]));
  }

  function renderFileTab(panel, ctx) {
    panel.innerHTML = "";

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "encoding-file-error"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    var schemeSelect = window.FOSS.dom.el("select", {
      className: "select",
      "data-testid": "encoding-file-scheme",
      "aria-label": "File Encoding Scheme"
    }, [
      window.FOSS.dom.el("option", { value: "Base64", text: "Base64" }),
      window.FOSS.dom.el("option", { value: "Hex", text: "Hex" }),
      window.FOSS.dom.el("option", { value: "Binary", text: "Binary" })
    ]);

    var schemeField = window.FOSS.components.field("Scheme:", schemeSelect, null, false, "encoding-file-scheme-field");

    var optionSwitch = window.FOSS.components.switch({
      testid: "encoding-file-option",
      label: "URL-safe alphabet",
      checked: false
    });

    function updateOptionLabel() {
      var s = schemeSelect.value;
      if (s === "Base64") {
        optionSwitch.setLabel("URL-safe alphabet");
      } else {
        optionSwitch.setLabel("Space-separated bytes");
      }
    }

    schemeSelect.addEventListener("change", updateOptionLabel);

    var picker = window.FOSS.components.filePicker({
      testid: "encoding-file-picker",
      title: "Select file to encode or decode",
      fileTypes: [["All Files", "*.*"]]
    });

    var resultHost = window.FOSS.dom.el("div", {
      className: "stack",
      gap: "sm",
      "data-testid": "encoding-file-results"
    });

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var encodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "encoding-file-encode",
      type: "button",
      onClick: function () {
        clearError();
        var inPath = picker.getPath();
        if (!inPath) {
          showError("Please select an input file first.");
          return;
        }
        var s = schemeSelect.value;
        var opt = optionSwitch.isChecked();
        var apiMethod = "encoding_base64_encode_file";
        var params = { input_path: inPath };

        if (s === "Base64") {
          apiMethod = "encoding_base64_encode_file";
          params.url_safe = opt;
        } else if (s === "Hex") {
          apiMethod = "encoding_hex_encode_file";
          params.spaced = opt;
        } else if (s === "Binary") {
          apiMethod = "encoding_binary_encode_file";
          params.spaced = opt;
        }

        window.FOSS.api(apiMethod, params).then(function (res) {
          if (res && res.ok) {
            resultHost.innerHTML = "";
            var card = window.FOSS.components.resultCard({
              testid: "encoding-file-result",
              title: "File Encoded Successfully",
              outputPath: res.output_path || inPath,
              details: [
                { label: "Scheme", value: s },
                { label: "Output size", value: (res.result ? res.result.length + " chars" : "Written to file") }
              ]
            });
            resultHost.appendChild(card);
          } else {
            showError((res && res.error) || "File encoding failed");
          }
        });
      }
    }, [
      window.FOSS.icons.el("upload", 16),
      window.FOSS.dom.el("span", { text: "Encode File..." })
    ]);

    var decodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "encoding-file-decode",
      type: "button",
      onClick: function () {
        clearError();
        var inPath = picker.getPath();
        if (!inPath) {
          showError("Please select an encoded input file first.");
          return;
        }
        window.FOSS.api("select_save_path", {
          default_name: "decoded.bin",
          file_types: [["All Files", "*.*"]]
        }).then(function (saveRes) {
          if (!saveRes || !saveRes.paths || saveRes.paths.length === 0) return;
          var outPath = saveRes.paths[0];
          var s = schemeSelect.value;
          var opt = optionSwitch.isChecked();
          var apiMethod = "encoding_base64_decode_to_file";
          var params = { input_path: inPath, output_path: outPath };

          if (s === "Base64") {
            apiMethod = "encoding_base64_decode_to_file";
            params.url_safe = opt;
          } else if (s === "Hex") {
            apiMethod = "encoding_hex_decode_to_file";
          } else if (s === "Binary") {
            apiMethod = "encoding_binary_decode_to_file";
          }

          window.FOSS.api(apiMethod, params).then(function (res) {
            if (res && res.ok) {
              resultHost.innerHTML = "";
              var card = window.FOSS.components.resultCard({
                testid: "encoding-file-result",
                title: "File Decoded Successfully",
                outputPath: res.output_path,
                details: [
                  { label: "Scheme", value: s },
                  { label: "Destination", value: res.output_path }
                ]
              });
              resultHost.appendChild(card);
            } else {
              showError((res && res.error) || "File decoding failed");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Decode to File..." })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row",
      gap: "sm"
    }, [encodeBtn, decodeBtn]);

    var controlsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "md"
    }, [
      window.FOSS.dom.el("div", { className: "row", gap: "lg" }, [schemeField, optionSwitch.el]),
      picker.el,
      actionsRow
    ]);

    panel.appendChild(window.FOSS.dom.el("div", { className: "page stack", gap: "md" }, [
      errorBanner,
      controlsCard,
      resultHost
    ]));
  }

  window.FOSS.router.register({
    id: "encoding",
    title: "Encoding / Decoding",
    navName: "Encoding",
    category: "Data",
    icon: "code",
    workbench: false,
    tabs: [
      { id: "text", label: "Text", render: renderTextTab },
      { id: "file", label: "File", render: renderFileTab }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        window.FOSS.router.open("encoding", "file");
      }
    }
  });
})();
