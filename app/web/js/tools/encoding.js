// Developer encoding workbench: text ciphers/encodings and binary file conversions.
window.FOSS = window.FOSS || {};

(function () {
  var TEXT_SCHEMES = [
    { value: "Base64", label: "Base64" },
    { value: "Base64URL", label: "Base64 URL-Safe" },
    { value: "Hex", label: "Hexadecimal" },
    { value: "Binary", label: "Binary (8-bit)" },
    { value: "URL", label: "URL Percent-Encoding" },
    { value: "HTML", label: "HTML Named Entities" },
    { value: "HTMLNumeric", label: "HTML Numeric Entities" },
    { value: "ROT13", label: "ROT13 Cipher" },
    { value: "Caesar", label: "Caesar Cipher (+3)" },
    { value: "Morse", label: "Morse Code" },
    { value: "JWT", label: "JWT Token Inspector" }
  ];

  var PAYLOAD_TEXT_FIRST = [
    { name: "Text File (*.txt)", extensions: ["txt"] },
    { name: "Binary File (*.bin)", extensions: ["bin"] }
  ];

  var PAYLOAD_BINARY_FIRST = [
    { name: "Binary File (*.bin)", extensions: ["bin"] },
    { name: "Text File (*.txt)", extensions: ["txt"] }
  ];

  function toolDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("encoding", key, fallback);
  }

  function showToast(msg, kind) {
    if (window.FOSS && window.FOSS.toast && typeof window.FOSS.toast.show === "function") {
      window.FOSS.toast.show(msg, kind);
    }
  }

  // Client-side cipher helpers for supplementary schemes
  var MORSE_TABLE = {
    A: ".-", B: "-...", C: "-.-.", D: "-..", E: ".", F: "..-.", G: "--.", H: "....",
    I: "..", J: ".---", K: "-.-", L: ".-..", M: "--", N: "-.", O: "---", P: ".--.",
    Q: "--.-", R: ".-.", S: "...", T: "-", U: "..-", V: "...-", W: ".--", X: "-..-",
    Y: "-.--", Z: "--..", 1: ".----", 2: "..---", 3: "...--", 4: "....-", 5: ".....",
    6: "-....", 7: "--...", 8: "---..", 9: "----.", 0: "-----", " ": "/"
  };
  var MORSE_REVERSE = {};
  Object.keys(MORSE_TABLE).forEach(function (k) { MORSE_REVERSE[MORSE_TABLE[k]] = k; });

  function rot13(str) {
    return str.replace(/[a-zA-Z]/g, function (c) {
      var base = c <= "Z" ? 65 : 97;
      return String.fromCharCode(((c.charCodeAt(0) - base + 13) % 26) + base);
    });
  }

  function caesar(str, shift) {
    var s = (shift % 26 + 26) % 26;
    return str.replace(/[a-zA-Z]/g, function (c) {
      var base = c <= "Z" ? 65 : 97;
      return String.fromCharCode(((c.charCodeAt(0) - base + s) % 26) + base);
    });
  }

  function morseEncode(str) {
    return str.toUpperCase().split("").map(function (c) {
      return MORSE_TABLE[c] || c;
    }).join(" ");
  }

  function morseDecode(str) {
    return str.trim().split(/\s+/).map(function (code) {
      return MORSE_REVERSE[code] || (code === "/" ? " " : code);
    }).join("");
  }

  function inspectJwt(str) {
    var parts = str.trim().split(".");
    if (parts.length < 2) throw new Error("Invalid JWT format (requires header.payload.signature)");
    function b64u(s) {
      var norm = s.replace(/-/g, "+").replace(/_/g, "/");
      while (norm.length % 4 !== 0) norm += "=";
      return decodeURIComponent(escape(atob(norm)));
    }
    var head = JSON.parse(b64u(parts[0]));
    var body = JSON.parse(b64u(parts[1]));
    return "=== Header ===\n" + JSON.stringify(head, null, 2) + "\n\n=== Payload ===\n" + JSON.stringify(body, null, 2);
  }

  function renderTextTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "encoding-text-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "encoding-text-error"
    }, [
      window.FOSS.icons.el("alert", 16),
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

    var schemeSelect = window.FOSS.dom.el("select", {
      className: "input input-sm wb-select-md",
      "data-testid": "encoding-text-scheme",
      "aria-label": "Encoding Scheme"
    }, TEXT_SCHEMES.map(function (sch) {
      return window.FOSS.dom.el("option", { value: sch.value, text: sch.label });
    }));
    schemeSelect.value = String(toolDefault("scheme", "Base64"));

    var spacedCheck = window.FOSS.dom.el("input", { type: "checkbox", id: "enc-spaced-check", checked: !!toolDefault("spaced", false) });
    var spacedLabel = window.FOSS.dom.el("label", {
      htmlFor: "enc-spaced-check",
      className: "text-xs cursor-pointer",
      text: "Spaced Bytes"
    });

    var inputEditor = window.FOSS.components.codeEditor({
      testid: "encoding-text-editor",
      title: "Input Text",
      placeholder: "Type or paste text/encoded data here...",
      fillHeight: true
    });

    var outputEditor = window.FOSS.components.codeEditor({
      testid: "encoding-text-output",
      title: "Output Result",
      placeholder: "Transformed output appears here...",
      readOnly: false,
      fillHeight: true
    });

    function executeTransform(direction) {
      clearError();
      var txt = inputEditor.getValue();
      if (!txt) {
        outputEditor.clear();
        statusBar.textContent = "Ready";
        return;
      }
      var s = schemeSelect.value;
      statusBar.textContent = (direction === "encode" ? "Encoding" : "Decoding") + " with " + s + "...";

      // Client-side quick schemes
      if (s === "ROT13") {
        outputEditor.setValue(rot13(txt));
        statusBar.textContent = "[OK] Applied ROT13";
        return;
      }
      if (s === "Caesar") {
        outputEditor.setValue(caesar(txt, direction === "encode" ? 3 : -3));
        statusBar.textContent = "[OK] Applied Caesar Cipher";
        return;
      }
      if (s === "Morse") {
        outputEditor.setValue(direction === "encode" ? morseEncode(txt) : morseDecode(txt));
        statusBar.textContent = "[OK] Processed Morse Code";
        return;
      }
      if (s === "JWT") {
        try {
          outputEditor.setValue(inspectJwt(txt));
          statusBar.textContent = "[OK] Decoded JWT Token";
        } catch (err) {
          showError(err.message || String(err));
        }
        return;
      }

      // Backend API schemes
      var apiMethod = "";
      var params = { text: txt };

      if (s === "Base64") {
        apiMethod = direction === "encode" ? "encoding_base64_encode_text" : "encoding_base64_decode_text";
        params.url_safe = false;
      } else if (s === "Base64URL") {
        apiMethod = direction === "encode" ? "encoding_base64_encode_text" : "encoding_base64_decode_text";
        params.url_safe = true;
      } else if (s === "Hex") {
        apiMethod = direction === "encode" ? "encoding_hex_encode_text" : "encoding_hex_decode_text";
        params.spaced = spacedCheck.checked;
      } else if (s === "Binary") {
        apiMethod = direction === "encode" ? "encoding_binary_encode_text" : "encoding_binary_decode_text";
        params.spaced = spacedCheck.checked;
      } else if (s === "URL") {
        apiMethod = direction === "encode" ? "encoding_url_encode" : "encoding_url_decode";
      } else if (s === "HTML") {
        apiMethod = direction === "encode" ? "encoding_html_encode" : "encoding_html_decode";
      } else if (s === "HTMLNumeric") {
        apiMethod = direction === "encode" ? "encoding_html_encode_numeric" : "encoding_html_decode";
        params.hex_format = false;
      }

      window.FOSS.api(apiMethod, params).then(function (res) {
        if (res && res.ok) {
          outputEditor.setValue(res.result !== undefined ? res.result : "");
          statusBar.textContent = "[OK] " + (direction === "encode" ? "Encoded" : "Decoded") + " with " + s;
        } else {
          showError((res && res.error) || (direction + " failed"));
        }
      }).catch(function (err) {
        showError(err.message || String(err));
      });
    }

    var encodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "encoding-encode-btn",
      "data-alt-testid": "encoding-text-encode",
      "aria-label": "Encode input text",
      title: "Encode",
      onClick: function () { executeTransform("encode"); }
    }, [window.FOSS.icons.el("play", 14), window.FOSS.dom.el("span", { text: "Encode" })]);

    var decodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "encoding-decode-btn",
      "data-alt-testid": "encoding-text-decode",
      "aria-label": "Decode input text",
      title: "Decode",
      onClick: function () { executeTransform("decode"); }
    }, [window.FOSS.icons.el("refresh-cw", 14), window.FOSS.dom.el("span", { text: "Decode" })]);

    var swapBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "encoding-text-swap",
      "aria-label": "Swap input and output text",
      title: "Swap Input and Output",
      onClick: function () {
        var inV = inputEditor.getValue();
        var outV = outputEditor.getValue();
        inputEditor.setValue(outV);
        outputEditor.setValue(inV);
        statusBar.textContent = "[OK] Swapped input and output";
      }
    }, [window.FOSS.icons.el("arrow-left-right", 14), window.FOSS.dom.el("span", { text: "Swap" })]);

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "encoding-text-copy",
      "aria-label": "Copy output result to clipboard",
      title: "Copy Output",
      onClick: function () {
        var outV = outputEditor.getValue();
        navigator.clipboard.writeText(outV).then(function () {
          showToast("Copied output to clipboard", "success");
        });
      }
    }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Copy Output" })]);

    var savePayloadBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "encoding-save-payload-btn",
      "aria-label": "Save Payload to File",
      title: "Save Payload",
      onClick: function () {
        var outV = outputEditor.getValue() || inputEditor.getValue() || "";
        if (!outV) {
          showError("No payload to save.");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Payload",
          default_name: "payload",
          file_types: PAYLOAD_TEXT_FIRST
        }).then(function (res) {
          var outPath = res && res.paths && res.paths.length > 0 ? res.paths[0] : "";
          if (!outPath) return;
          window.FOSS.api("write_text_file", {
            file_path: outPath,
            content: outV
          }).then(function () {
            statusBar.textContent = "Saved payload to " + outPath;
            showToast("Saved payload to " + outPath, "success");
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        }).catch(function (err) {
          showError(err.message || String(err));
        });
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Save Payload" })]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "aria-label": "Clear input and output text",
      title: "Clear",
      onClick: function () {
        inputEditor.clear();
        outputEditor.clear();
        clearError();
        statusBar.textContent = "Ready";
      }
    }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Clear" })]);

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [
      schemeSelect,
      encodeBtn,
      decodeBtn,
      swapBtn,
      copyBtn,
      savePayloadBtn,
      clearBtn,
      window.FOSS.dom.el("div", { className: "row items-center gap-1" }, [spacedCheck, spacedLabel])
    ]);

    var editorsGrid = window.FOSS.dom.el("div", { className: "wb-editor-grid" }, [
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [inputEditor]),
      window.FOSS.dom.el("div", { className: "wb-editor-col" }, [outputEditor])
    ]);

    panel.appendChild(toolbar);
    panel.appendChild(errorBanner);
    panel.appendChild(editorsGrid);
    panel.appendChild(statusBar);
  }

  function renderFileTab(panel, ctx) {
    panel.innerHTML = "";

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted wb-status",
      "data-testid": "encoding-file-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "encoding-file-error"
    }, [
      window.FOSS.icons.el("alert", 16),
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

    var schemeSelect = window.FOSS.dom.el("select", {
      className: "input input-sm wb-select-md",
      "data-testid": "encoding-file-scheme",
      "aria-label": "File Encoding Scheme"
    }, [
      window.FOSS.dom.el("option", { value: "Base64", text: "Base64" }),
      window.FOSS.dom.el("option", { value: "Hex", text: "Hexadecimal" }),
      window.FOSS.dom.el("option", { value: "Binary", text: "Binary (8-bit)" })
    ]);
    var defaultScheme = String(toolDefault("scheme", "Base64"));
    schemeSelect.value = ["Base64", "Hex", "Binary"].indexOf(defaultScheme) >= 0 ? defaultScheme : "Base64";

    var filePicker = window.FOSS.components.filePicker({
      testid: "encoding-file-picker",
      label: "Choose File"
    });

    var resultHost = window.FOSS.dom.el("div", { className: "flex-col gap-2 wb-field-full" });

    var encodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "encoding-file-encode",
      "aria-label": "Encode binary file to text",
      title: "Encode File",
      onClick: function () {
        clearError();
        var inPath = filePicker.getPath();
        if (!inPath) {
          showError("Please select an input file first.");
          return;
        }
        var s = schemeSelect.value;
        var apiMethod = "encoding_base64_encode_file";
        var params = { input_path: inPath };

        window.FOSS.api("select_save_path", {
          title: "Save Encoded Payload",
          default_name: "payload",
          file_types: PAYLOAD_TEXT_FIRST
        }).then(function (saveRes) {
          var outPath = (saveRes && saveRes.paths && saveRes.paths.length > 0) ? saveRes.paths[0] : "";
          if (!outPath) return;
          if (s === "Base64") {
            apiMethod = "encoding_base64_encode_file";
            params.url_safe = false;
          } else if (s === "Hex") {
            apiMethod = "encoding_hex_encode_file";
            params.spaced = !!toolDefault("spaced", false);
          } else if (s === "Binary") {
            apiMethod = "encoding_binary_encode_file";
            params.spaced = !!toolDefault("spaced", false);
          }
          params.output_path = outPath;

          statusBar.textContent = "Encoding file with " + s + "...";
          window.FOSS.api(apiMethod, params).then(function (res) {
            if (res && res.ok) {
              resultHost.innerHTML = "";
              var card = window.FOSS.components.resultCard({
                testid: "encoding-file-result",
                title: "File Encoded Successfully",
                outputPath: res.output_path || outPath,
                details: [
                  { label: "Scheme", value: s },
                  { label: "Result Size", value: (res.result ? res.result.length + " characters" : "Output file written") }
                ]
              });
              resultHost.appendChild(card);
              statusBar.textContent = "[OK] File encoded with " + s;
            } else {
              showError((res && res.error) || "File encoding failed");
            }
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        });
      }
    }, [window.FOSS.icons.el("upload", 14), window.FOSS.dom.el("span", { text: "Encode File" })]);

    var decodeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "encoding-file-decode",
      "aria-label": "Decode text file to binary",
      title: "Decode File",
      onClick: function () {
        clearError();
        var inPath = filePicker.getPath();
        if (!inPath) {
          showError("Please select an input file first.");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Decoded Payload",
          default_name: "payload",
          file_types: PAYLOAD_BINARY_FIRST
        }).then(function (saveRes) {
          var outPath = (saveRes && saveRes.paths && saveRes.paths.length > 0) ? saveRes.paths[0] : "";
          if (!outPath) return;
          var s = schemeSelect.value;
          var apiMethod = "encoding_base64_decode_to_file";
          var params = { input_path: inPath, output_path: outPath };

          if (s === "Base64") {
            apiMethod = "encoding_base64_decode_to_file";
            params.url_safe = false;
          } else if (s === "Hex") {
            apiMethod = "encoding_hex_decode_to_file";
          } else if (s === "Binary") {
            apiMethod = "encoding_binary_decode_to_file";
          }

          statusBar.textContent = "Decoding file to " + outPath + "...";
          window.FOSS.api(apiMethod, params).then(function (res) {
            if (res && res.ok) {
              resultHost.innerHTML = "";
              var card = window.FOSS.components.resultCard({
                testid: "encoding-file-result",
                title: "File Decoded Successfully",
                outputPath: res.output_path || outPath,
                details: [
                  { label: "Scheme", value: s },
                  { label: "Output Path", value: res.output_path || outPath }
                ]
              });
              resultHost.appendChild(card);
              statusBar.textContent = "[OK] Decoded to: " + (res.output_path || outPath);
            } else {
              showError((res && res.error) || "File decoding failed");
            }
          }).catch(function (err) {
            showError(err.message || String(err));
          });
        });
      }
    }, [window.FOSS.icons.el("download", 14), window.FOSS.dom.el("span", { text: "Decode File..." })]);

    var toolbar = window.FOSS.dom.el("div", { className: "wb-toolbar" }, [filePicker.el, schemeSelect, encodeBtn, decodeBtn]);

    var fileCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-3 p-4"
    }, [
      window.FOSS.dom.el("div", { className: "text-sm font-semibold", text: "Binary File <-> Encoded Text Converter" }),
      window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Select any file to encode its binary bytes into Base64, Hex, or 8-bit Binary representation, or decode back to binary." }),
      toolbar,
      resultHost
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "wb-fill wb-scroll"
    }, [errorBanner, fileCard, statusBar]));
  }

  window.FOSS.router.register({
    id: "encoding",
    title: "Encoding & Decoding",
    navName: "Encoding",
    category: "Data",
    icon: "encoding",
    workbench: true,
    defaults: [
      {
        key: "scheme",
        label: "Default scheme",
        type: "select",
        options: TEXT_SCHEMES,
        default: "Base64",
        hint: "Scheme preselected for text and file encoding."
      },
      {
        key: "spaced",
        label: "Spaced bytes",
        type: "toggle",
        default: false,
        hint: "Separate Hex and Binary bytes with spaces by default."
      }
    ],
    tabs: [
      { id: "text", label: "Text Ciphers & Encodings", aliases: ["main", "base64"], render: renderTextTab },
      { id: "file", label: "Binary File Encoding", aliases: ["binary"], render: renderFileTab }
    ],
    onFiles: function (paths, ctx) {
      if (paths && paths.length > 0) {
        var pickerInput = document.querySelector("[data-testid='encoding-file-picker-input']");
        if (pickerInput) {
          pickerInput.value = paths[0];
          pickerInput.dispatchEvent(new Event("input"));
        }
      }
    }
  });
})();
