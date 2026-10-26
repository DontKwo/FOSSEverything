// Hash & Verify workspace: file hashing, directory manifests, text HMAC, comparison, verification, and Ed25519 signing.
window.FOSS = window.FOSS || {};

(function () {
  var ALGORITHMS = ["sha256", "sha512", "sha1", "md5", "sha224", "sha384", "blake2b", "blake2s"];

  function makeAlgoSelect(testid) {
    return window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": testid,
      "aria-label": "Algorithm"
    }, ALGORITHMS.map(function (a) {
      return window.FOSS.dom.el("option", { value: a, text: a.toUpperCase() });
    }));
  }

  function renderFileTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Compute SHA-256, MD5, file hashes, and directory manifests locally. Zero cloud involvement."
    });

    var pathInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-file-path",
      "data-truncate-ok": "true",
      title: "File path",
      placeholder: "select or drop a file",
      "aria-label": "Select or drop a file"
    });

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-file-browse",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            pathInput.value = res.paths[0];
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    var fileCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Select File" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [pathInput, browseBtn])
    ]);

    var algoSelect = makeAlgoSelect("hash-file-algo");

    var algoCheckboxes = window.FOSS.dom.el("div", {
      className: "row",
      gap: "md",
      style: "flex-wrap: wrap;"
    }, ["sha256", "sha512", "sha1", "md5"].map(function (a) {
      return window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [
        window.FOSS.dom.el("input", {
          type: "checkbox",
          value: a,
          checked: true,
          "data-testid": "hash-check-" + a,
          "aria-label": a.toUpperCase()
        }),
        window.FOSS.dom.el("span", { className: "text-sm", text: a.toUpperCase() })
      ]);
    }));

    var algoCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Algorithms to Compute" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Algorithm:" }),
        algoSelect
      ]),
      algoCheckboxes
    ]);

    var resultsTableHost = window.FOSS.dom.el("div", {
      className: "table-wrap",
      "data-testid": "hash-file-results"
    });

    var statusEl = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "hash-file-status",
      text: "Ready"
    });

    var computeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-file-compute",
      "aria-label": "Compute hashes",
      title: "Compute hashes",
      type: "button",
      onClick: function () {
        var p = pathInput.value.trim();
        if (!p) {
          statusEl.textContent = "Please select a file first.";
          return;
        }
        var algo = algoSelect.value;
        window.FOSS.api("hash_file", { file_path: p, algorithm: algo }).then(function (res) {
          resultsTableHost.innerHTML = "";
          var table = window.FOSS.dom.el("table", { className: "table" }, [
            window.FOSS.dom.el("thead", {}, [
              window.FOSS.dom.el("tr", {}, [
                window.FOSS.dom.el("th", { text: "Algorithm" }),
                window.FOSS.dom.el("th", { text: "Digest" }),
                window.FOSS.dom.el("th", { text: "Action" })
              ])
            ]),
            window.FOSS.dom.el("tbody", {}, [
              window.FOSS.dom.el("tr", {}, [
                window.FOSS.dom.el("td", { text: res.algorithm.toUpperCase() }),
                window.FOSS.dom.el("td", { className: "font-mono text-sm", text: res.hash, style: "word-break: break-all;" }),
                window.FOSS.dom.el("td", {}, [
                  window.FOSS.dom.el("button", {
                    className: "btn btn-ghost btn-sm",
                    "data-testid": "hash-copy-btn",
                    "aria-label": "Copy",
                    title: "Copy",
                    type: "button",
                    onClick: function () {
                      window.FOSS.api("copy_to_clipboard", { text: res.hash });
                    }
                  }, [window.FOSS.dom.el("span", { text: "Copy" })])
                ])
              ])
            ])
          ]);
          resultsTableHost.appendChild(table);
          statusEl.textContent = "[OK] Computed " + res.algorithm.toUpperCase();
        }).catch(function (err) {
          statusEl.textContent = "Error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Compute Hashes" })
    ]);

    var multiHashBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-file-multihash",
      "aria-label": "Multi-hash all algorithms",
      title: "Multi-hash all algorithms",
      type: "button",
      onClick: function () {
        var p = pathInput.value.trim();
        if (!p) {
          statusEl.textContent = "Please select a file first.";
          return;
        }
        window.FOSS.api("hash_multi", { file_path: p, algorithms: ["sha256", "sha512", "sha1", "md5"] }).then(function (res) {
          resultsTableHost.innerHTML = "";
          var rows = Object.entries(res.hashes || {}).map(function (entry) {
            return window.FOSS.dom.el("tr", {}, [
              window.FOSS.dom.el("td", { text: entry[0].toUpperCase() }),
              window.FOSS.dom.el("td", { className: "font-mono text-sm", text: entry[1], style: "word-break: break-all;" }),
              window.FOSS.dom.el("td", {}, [
                window.FOSS.dom.el("button", {
                  className: "btn btn-ghost btn-sm",
                  "data-testid": "hash-copy-" + entry[0],
                  "aria-label": "Copy",
                  title: "Copy",
                  type: "button",
                  onClick: function () {
                    window.FOSS.api("copy_to_clipboard", { text: entry[1] });
                  }
                }, [window.FOSS.dom.el("span", { text: "Copy" })])
              ])
            ]);
          });
          var table = window.FOSS.dom.el("table", { className: "table" }, [
            window.FOSS.dom.el("thead", {}, [
              window.FOSS.dom.el("tr", {}, [
                window.FOSS.dom.el("th", { text: "Algorithm" }),
                window.FOSS.dom.el("th", { text: "Digest" }),
                window.FOSS.dom.el("th", { text: "Action" })
              ])
            ]),
            window.FOSS.dom.el("tbody", {}, rows)
          ]);
          resultsTableHost.appendChild(table);
          statusEl.textContent = "[OK] Multi-hash calculated for 4 algorithms";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Compute Multi-Hash" })
    ]);

    var actionsRow = window.FOSS.dom.el("div", {
      className: "row",
      gap: "sm"
    }, [computeBtn, multiHashBtn]);

    var resultsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Checksum Results" }),
      resultsTableHost
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, fileCard, algoCard, actionsRow, resultsCard, statusEl]));
  }

  function renderDirectoryTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Recursively hash entire directory hierarchies, track progress, and generate GNU/BSD manifests."
    });

    var dirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-directory-path",
      "data-truncate-ok": "true",
      title: "Directory path",
      placeholder: "select a folder to hash recursively",
      "aria-label": "Select a folder to hash recursively"
    });

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-directory-browse",
      "aria-label": "Browse folder",
      title: "Browse folder",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            dirInput.value = res.paths[0];
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse Folder" })
    ]);

    var algoSelect = makeAlgoSelect("hash-dir-algo");

    var progressWrap = window.FOSS.dom.el("div", {
      className: "progress-container hidden",
      "data-testid": "hash-directory-progress"
    }, [
      window.FOSS.components.progress({ testid: "hash-dir-prog", value: 100, label: "Hashing files..." }).el
    ]);

    var dirStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "hash-directory-status",
      text: "No directory hashed yet."
    });

    var manifestResults = window.FOSS.dom.el("div", {
      className: "table-wrap",
      "data-testid": "hash-directory-results"
    });

    var hashDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-directory-hash-btn",
      "aria-label": "Hash directory",
      title: "Hash directory",
      type: "button",
      onClick: function () {
        var d = dirInput.value.trim();
        if (!d) {
          dirStatus.textContent = "Please select a directory first.";
          return;
        }
        progressWrap.classList.remove("hidden");
        window.FOSS.api("hash_directory_tree", { directory_path: d, algorithm: algoSelect.value }).then(function (res) {
          progressWrap.classList.add("hidden");
          dirStatus.textContent = "[OK] Hashed " + res.count + " files in directory";
          manifestResults.innerHTML = "";
          var rows = (res.files || []).map(function (f) {
            return window.FOSS.dom.el("tr", {}, [
              window.FOSS.dom.el("td", { className: "text-sm", text: f.path || f.relpath || f.name }),
              window.FOSS.dom.el("td", { className: "font-mono text-xs", text: f.hash })
            ]);
          });
          var tbl = window.FOSS.dom.el("table", { className: "table" }, [
            window.FOSS.dom.el("thead", {}, [
              window.FOSS.dom.el("tr", {}, [
                window.FOSS.dom.el("th", { text: "Relative Path" }),
                window.FOSS.dom.el("th", { text: "Digest" })
              ])
            ]),
            window.FOSS.dom.el("tbody", {}, rows)
          ]);
          manifestResults.appendChild(tbl);
        }).catch(function (err) {
          progressWrap.classList.add("hidden");
          dirStatus.textContent = "Error: " + (err && err.message ? err.message : String(err));
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Hash Directory" })
    ]);

    var exportManifestBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-directory-export-manifest",
      "aria-label": "Export manifest",
      title: "Export manifest",
      type: "button",
      onClick: function () {
        var d = dirInput.value.trim();
        if (!d) return;
        window.FOSS.api("select_save_path", { default_name: "checksums.txt" }).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          var saveP = res.paths[0];
          window.FOSS.api("hash_directory_tree", { directory_path: d, algorithm: algoSelect.value, output_manifest: saveP }).then(function () {
            dirStatus.textContent = "[OK] Manifest exported to " + saveP;
          });
        });
      }
    }, [
      window.FOSS.icons.el("download", 16),
      window.FOSS.dom.el("span", { text: "Export Manifest" })
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Directory Manifest" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [dirInput, browseBtn]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Algorithm:" }),
        algoSelect,
        hashDirBtn,
        exportManifestBtn
      ]),
      progressWrap,
      dirStatus,
      manifestResults
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, card]));
  }

  function renderTextTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Compute real-time cryptographic digests and HMACs for arbitrary text strings."
    });

    var editor = window.FOSS.components.codeEditor({
      testid: "hash-text-input",
      title: "Text to Hash",
      placeholder: "type or paste text here to hash in real-time",
      ariaLabel: "Text string to hash",
      onChange: function () {
        updateDigest();
      }
    });

    var hmacInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-hmac-key",
      placeholder: "optional key for keyed hashing",
      "aria-label": "HMAC key"
    });
    hmacInput.addEventListener("input", function () {
      updateDigest();
    });

    var algoSelect = makeAlgoSelect("hash-text-algo");
    algoSelect.addEventListener("change", function () {
      updateDigest();
    });

    var digestOutput = window.FOSS.dom.el("div", {
      className: "font-mono text-sm",
      "data-testid": "hash-text-digest-val",
      text: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    });

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "hash-text-copy-btn",
      "aria-label": "Copy",
      title: "Copy",
      type: "button",
      onClick: function () {
        window.FOSS.api("copy_to_clipboard", { text: digestOutput.textContent });
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Copy" })
    ]);

    function updateDigest() {
      var txt = editor.getValue();
      var key = hmacInput.value.trim();
      var algo = algoSelect.value;
      if (key) {
        window.FOSS.api("hash_hmac", { data: txt, key: key, algorithm: algo }).then(function (res) {
          digestOutput.textContent = res.hmac || "";
        });
      } else {
        window.FOSS.api("hash_text", { text: txt, algorithm: algo }).then(function (res) {
          digestOutput.textContent = res.hash || "";
        });
      }
    }

    var digestCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Digest" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm", style: "justify-content: space-between;" }, [
        digestOutput,
        copyBtn
      ])
    ]);

    var controlsCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Algorithm:" }),
        algoSelect
      ]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "HMAC Key:" }),
        hmacInput
      ])
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, editor.el, controlsCard, digestCard]));

    updateDigest();
  }

  function renderCompareTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Compare two files directly for identical checksums with zero network activity."
    });

    var file1Input = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-compare-file1",
      "data-truncate-ok": "true",
      title: "File 1 path",
      placeholder: "choose first file",
      "aria-label": "Choose first file"
    });

    var file2Input = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-compare-file2",
      "data-truncate-ok": "true",
      title: "File 2 path",
      placeholder: "choose second file",
      "aria-label": "Choose second file"
    });

    var b1 = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-compare-browse1",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) file1Input.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var b2 = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-compare-browse2",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) file2Input.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var algoSelect = makeAlgoSelect("hash-compare-algo");

    var resultBox = window.FOSS.dom.el("div", {
      className: "card text-sm",
      "data-testid": "hash-compare-result",
      text: "waiting for two files to compare."
    });

    var compareBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-compare-btn",
      "aria-label": "Compare files",
      title: "Compare files",
      type: "button",
      onClick: function () {
        var p1 = file1Input.value.trim();
        var p2 = file2Input.value.trim();
        if (!p1 || !p2) return;
        window.FOSS.api("hash_compare_files", { path1: p1, path2: p2, algorithm: algoSelect.value }).then(function (res) {
          if (res.identical) {
            resultBox.innerHTML = "<div class='text-success font-bold'>[MATCH] Checksums are identical!</div>" +
              "<div class='font-mono text-xs'>Hash: " + res.hash1 + "</div>";
          } else {
            resultBox.innerHTML = "<div class='text-danger font-bold'>[DIFF] Checksums differ!</div>" +
              "<div class='font-mono text-xs'>File 1: " + res.hash1 + "</div>" +
              "<div class='font-mono text-xs'>File 2: " + res.hash2 + "</div>";
          }
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Compare Files" })
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "File Checksum Comparison" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [file1Input, b1]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [file2Input, b2]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Algorithm:" }),
        algoSelect,
        compareBtn
      ]),
      resultBox
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, card]));
  }

  function renderVerifyTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Verify file integrity against an expected hash or verify whole checksum manifests."
    });

    var fileInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-verify-file",
      "data-truncate-ok": "true",
      title: "File to verify",
      placeholder: "select file to verify",
      "aria-label": "Select file to verify"
    });

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-verify-browse",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) fileInput.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var expectedInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-verify-expected",
      placeholder: "paste the expected hash here",
      "aria-label": "Expected hash"
    });

    var algoSelect = makeAlgoSelect("hash-verify-algo");

    var resultBox = window.FOSS.dom.el("div", {
      className: "card text-sm",
      "data-testid": "hash-verify-result",
      text: "Waiting to verify..."
    });

    var verifyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-verify-btn",
      "aria-label": "Verify integrity",
      title: "Verify integrity",
      type: "button",
      onClick: function () {
        var p = fileInput.value.trim();
        var exp = expectedInput.value.trim();
        if (!p || !exp) return;
        window.FOSS.api("hash_verify", { file_path: p, expected_hash: exp, algorithm: algoSelect.value }).then(function (res) {
          if (res.matches) {
            resultBox.innerHTML = "<div class='text-success font-bold'>PASS: Checksum matches expected hash!</div>";
          } else {
            resultBox.innerHTML = "<div class='text-danger font-bold'>FAILED: Checksum mismatch!</div>" +
              "<div class='font-mono text-xs'>Expected: " + res.expected_hash + "</div>" +
              "<div class='font-mono text-xs'>Actual:   " + res.actual_hash + "</div>";
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Verify Integrity" })
    ]);

    var fileCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Verify Single File Hash" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [fileInput, browseBtn]),
      expectedInput,
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Algorithm:" }),
        algoSelect,
        verifyBtn
      ]),
      resultBox
    ]);

    var manifestPathInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-manifest-path",
      "data-truncate-ok": "true",
      title: "Manifest path",
      placeholder: "choose older/original manifest",
      "aria-label": "Manifest path"
    });

    var manifestResultsTable = window.FOSS.dom.el("div", {
      className: "table-wrap",
      "data-testid": "hash-manifest-results-table"
    });

    var openManifestBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-verify-manifest-open",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) manifestPathInput.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var verifyManifestBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-verify-manifest-btn",
      "aria-label": "Verify manifest",
      title: "Verify manifest",
      type: "button",
      onClick: function () {
        var mp = manifestPathInput.value.trim();
        if (!mp) return;
        window.FOSS.api("hash_verify_manifest", { manifest_path: mp }).then(function (res) {
          var s = res.summary || {};
          manifestResultsTable.innerHTML = "<div class='text-sm mb-2'>Status: Passed " + (s.passed_count || 0) + ", Failed " + (s.failed_count || 0) + ", Missing " + (s.missing_count || 0) + "</div>";
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Verify Manifest" })
    ]);

    var manifestCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Manifest Verification" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [manifestPathInput, openManifestBtn, verifyManifestBtn]),
      manifestResultsTable
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, fileCard, manifestCard]));
  }

  function renderDiffTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Compare two checksum manifests to identify added, removed, and changed files with old/new hashes."
    });

    var man1 = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-diff-man1",
      "data-truncate-ok": "true",
      title: "Older manifest",
      placeholder: "choose older/original manifest",
      "aria-label": "Older manifest"
    });

    var man2 = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-diff-man2",
      "data-truncate-ok": "true",
      title: "Newer manifest",
      placeholder: "choose newer/updated manifest",
      "aria-label": "Newer manifest"
    });

    var b1 = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-diff-browse1",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) man1.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var b2 = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-diff-browse2",
      "aria-label": "Browse",
      title: "Browse",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_file", {}).then(function (r) {
          if (r && !r.cancelled && r.paths && r.paths.length) man2.value = r.paths[0];
        });
      }
    }, [window.FOSS.icons.el("folder", 16), window.FOSS.dom.el("span", { text: "Browse" })]);

    var resultBox = window.FOSS.dom.el("div", {
      className: "card text-sm",
      "data-testid": "hash-diff-result",
      text: "choose two manifests to compare."
    });

    var compareBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-diff-compare-btn",
      "aria-label": "Compare manifests",
      title: "Compare manifests",
      type: "button",
      onClick: function () {
        var m1 = man1.value.trim();
        var m2 = man2.value.trim();
        if (!m1 || !m2) return;
        window.FOSS.api("hash_diff_manifests", { manifest1_path: m1, manifest2_path: m2 }).then(function (res) {
          var d = res.diff || {};
          resultBox.innerHTML = "<div class='font-bold mb-2'>Manifest Diff Results:</div>" +
            "<div>Added: " + (d.added ? d.added.length : 0) + "</div>" +
            "<div>Removed: " + (d.removed ? d.removed.length : 0) + "</div>" +
            "<div>Changed: " + (d.changed ? d.changed.length : 0) + "</div>";
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Compare Manifests" })
    ]);

    var card = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Manifest Diff" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [man1, b1]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [man2, b2]),
      compareBtn,
      resultBox
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, card]));
  }

  function renderSignTab(panel, ctx) {
    panel.innerHTML = "";

    var desc = window.FOSS.dom.el("p", {
      className: "text-muted",
      text: "Generate Ed25519 signing keypairs, sign files, verify signatures, and enforce verification policies."
    });

    var keypairStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "hash-sign-keypair-status",
      text: "no keypair generated yet."
    });

    var genKeypairBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "hash-sign-generate-keypair",
      "aria-label": "Generate keypair",
      title: "Generate keypair",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (r) {
          if (!r || r.cancelled || !r.paths || !r.paths.length) return;
          var dir = r.paths[0];
          window.FOSS.api("hash_generate_keypair", { output_dir: dir, name: "id_ed25519" }).then(function (res) {
            keypairStatus.textContent = "[OK] Keypair generated at: " + res.public_key_path;
          });
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "Generate Keypair" })
    ]);

    var keypairCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Signing Keypair (Ed25519)" }),
      genKeypairBtn,
      keypairStatus
    ]);

    var signFileInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-sign-file-path",
      "data-truncate-ok": "true",
      title: "File to sign",
      placeholder: "select or drop a file",
      "aria-label": "Select file to sign"
    });

    var signKeyInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input input-sm grow font-mono",
      "data-testid": "hash-sign-privkey-path",
      "data-truncate-ok": "true",
      title: "Private key path",
      placeholder: "private key path (.pem)",
      "aria-label": "Private key path"
    });

    var timestampCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "hash-sign-timestamp-check",
      "aria-label": "include local timestamp (multi-party bundle)"
    });

    var signStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "hash-sign-status",
      text: "Ready to sign"
    });

    var signBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-sign-execute-btn",
      "aria-label": "Sign file",
      title: "Sign file",
      type: "button",
      onClick: function () {
        var fp = signFileInput.value.trim();
        var kp = signKeyInput.value.trim();
        if (!fp || !kp) return;
        window.FOSS.api("hash_sign", { file_path: fp, private_key_path: kp }).then(function (res) {
          signStatus.textContent = "[OK] Signature created (" + (res.signature ? res.signature.length : 0) + " bytes)";
        });
      }
    }, [
      window.FOSS.icons.el("edit", 16),
      window.FOSS.dom.el("span", { text: "Sign File" })
    ]);

    var signCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Sign a File" }),
      signFileInput,
      signKeyInput,
      window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [
        timestampCheck,
        window.FOSS.dom.el("span", { className: "text-sm", text: "include local timestamp (multi-party bundle)" })
      ]),
      signBtn,
      signStatus
    ]);

    var verifySigCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Verify a Signature" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "leave the public key path blank to use the trusted key selected above instead." }),
      window.FOSS.dom.el("label", { className: "row", gap: "xs" }, [
        window.FOSS.dom.el("input", {
          type: "checkbox",
          "data-testid": "hash-verify-sigjson-check",
          "aria-label": "this is a timestamped bundle (.sigjson)"
        }),
        window.FOSS.dom.el("span", { className: "text-sm", text: "this is a timestamped bundle (.sigjson)" })
      ]),
      window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": "hash-verify-sig-btn",
        "aria-label": "Verify signature",
        title: "Verify signature",
        type: "button",
        onClick: function () {}
      }, [
        window.FOSS.icons.el("check", 16),
        window.FOSS.dom.el("span", { text: "Verify Signature" })
      ])
    ]);

    var policySelect = window.FOSS.dom.el("select", {
      className: "input input-sm",
      "data-testid": "hash-policy-select",
      "aria-label": "Policy preset"
    }, [
      window.FOSS.dom.el("option", { value: "Quick Check", text: "Quick Check" }),
      window.FOSS.dom.el("option", { value: "Standard Release", text: "Standard Release" }),
      window.FOSS.dom.el("option", { value: "Signed Release", text: "Signed Release" }),
      window.FOSS.dom.el("option", { value: "Compliance Archive", text: "Compliance Archive" })
    ]);

    var policyStatus = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "hash-policy-status",
      text: "Ready"
    });

    var verifyPolicyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "hash-policy-verify-btn",
      "aria-label": "Verify against policy",
      title: "Verify against policy",
      type: "button",
      onClick: function () {
        var p = policySelect.value;
        window.FOSS.api("hash_policy_presets", { policy: p, results: [] }).then(function (res) {
          policyStatus.textContent = "[OK] Evaluated policy preset: " + p;
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Verify Against Policy" })
    ]);

    var policyCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Policy-Based Manifest Verification" }),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [policySelect, verifyPolicyBtn]),
      policyStatus
    ]);

    var trustedKeysCard = window.FOSS.dom.el("div", {
      className: "card stack",
      gap: "sm"
    }, [
      window.FOSS.dom.el("span", { className: "card-title", text: "Trusted Keys (Local Keyring)" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "select a trusted key above to use it for verification below instead of browsing a .pem file." }),
      window.FOSS.dom.el("select", {
        className: "input input-sm",
        "data-testid": "hash-trusted-key-select",
        "aria-label": "Trusted key"
      }, [
        window.FOSS.dom.el("option", { value: "", text: "(none selected)" })
      ]),
      window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "hash-add-key-btn",
          "aria-label": "Add trusted key",
          title: "Add trusted key",
          type: "button",
          onClick: function () {}
        }, [
          window.FOSS.icons.el("plus", 16),
          window.FOSS.dom.el("span", { text: "Add Trusted Key" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "hash-remove-key-btn",
          "aria-label": "Remove selected",
          title: "Remove selected",
          type: "button",
          onClick: function () {}
        }, [
          window.FOSS.icons.el("trash", 16),
          window.FOSS.dom.el("span", { text: "Remove Selected" })
        ])
      ])
    ]);

    panel.appendChild(window.FOSS.dom.el("div", {
      className: "stack",
      gap: "md"
    }, [desc, keypairCard, signCard, verifySigCard, policyCard, trustedKeysCard]));
  }

  window.FOSS.router.register({
    id: "hash",
    title: "Hash and Verify",
    navName: "Hash & Verify",
    category: "Utilities",
    icon: "lock",
    workbench: false,
    tabs: [
      { id: "file", label: "File Hash", render: renderFileTab },
      { id: "directory", label: "Directory Manifest", render: renderDirectoryTab },
      { id: "text", label: "Text Hash", render: renderTextTab },
      { id: "compare", label: "Compare Files", render: renderCompareTab },
      { id: "verify", label: "Verify Hash", render: renderVerifyTab },
      { id: "manifest_diff", label: "Manifest Diff", render: renderDiffTab },
      { id: "sign", label: "Sign & Policy", render: renderSignTab }
    ]
  });
})();
