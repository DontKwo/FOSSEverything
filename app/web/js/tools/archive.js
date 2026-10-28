// Archive & Packaging tool: create, extract, inspect, protect (encryption & key rotation), and incremental backup.
window.FOSS = window.FOSS || {};

(function () {
  function renderCreate(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-archive");

    var currentSources = [];

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Create Archive" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Package files or folders into ZIP, TAR, or TAR.GZ bundles locally without cloud dependencies."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "archive-create-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "archive-create-error"
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
      "data-testid": "archive-create-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-create-card",
        title: titleText || "Archive Created",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    // Source picker
    var sourceDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "archive-source-display",
      "data-truncate-ok": "true",
      title: "No sources selected",
      text: "No sources selected"
    });

    var chooseFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-choose-source",
      "aria-label": "Choose files",
      title: "Choose files",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_files", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentSources = res.paths;
          sourceDisplay.textContent = currentSources.length === 1 ? currentSources[0] : currentSources.length + " items selected";
          sourceDisplay.title = currentSources.join(", ");
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Files" })
    ]);

    var chooseFolderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Choose folder",
      title: "Choose folder",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentSources = res.paths;
          sourceDisplay.textContent = currentSources[0];
          sourceDisplay.title = currentSources[0];
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Folder" })
    ]);

    var sourceToolbar = window.FOSS.dom.el("div", { className: "row" }, [chooseFilesBtn, chooseFolderBtn]);
    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [sourceDisplay, sourceToolbar]));

    // Policy presets
    var presetSelect = window.FOSS.dom.el("select", {
      className: "select grow",
      "data-testid": "archive-preset-select",
      "aria-label": "Archive Policy Preset",
      title: "Archive Policy Preset",
      onChange: function () {
        var v = presetSelect.value;
        if (v === "photos" || v === "share") {
          formatSelect.value = "zip";
        } else if (v === "code" || v === "longterm") {
          formatSelect.value = "tar.gz";
        } else if (v === "media") {
          formatSelect.value = "tar";
        }
      }
    }, [
      window.FOSS.dom.el("option", { value: "photos", text: "Personal Photos (ZIP container)" }),
      window.FOSS.dom.el("option", { value: "code", text: "Source Code (TAR.GZ archive)" }),
      window.FOSS.dom.el("option", { value: "sensitive", text: "Sensitive Documents (Encrypted bundle)" }),
      window.FOSS.dom.el("option", { value: "media", text: "Media Backup (TAR uncompressed)" }),
      window.FOSS.dom.el("option", { value: "share", text: "Quick Share (ZIP lightweight)" }),
      window.FOSS.dom.el("option", { value: "longterm", text: "Long-term Archive (TAR.GZ max compression)" })
    ]);

    var presetRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Policy Preset" }),
      presetSelect
    ]);
    card.appendChild(presetRow);

    // Format selection
    var formatSelect = window.FOSS.dom.el("select", {
      className: "select w-36",
      "data-testid": "archive-format-select",
      "aria-label": "Archive Format",
      title: "Archive Format"
    }, [
      window.FOSS.dom.el("option", { value: "zip", text: "ZIP (.zip)" }),
      window.FOSS.dom.el("option", { value: "tar", text: "TAR (.tar)" }),
      window.FOSS.dom.el("option", { value: "tar.gz", text: "TAR.GZ (.tar.gz)" })
    ]);

    var formatRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Format" }),
      formatSelect
    ]);
    card.appendChild(formatRow);

    // Password input
    var passwordInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input grow",
      "data-testid": "archive-create-password",
      "aria-label": "Optional password",
      title: "Optional password",
      placeholder: "Optional password (leaves unencrypted if empty)"
    });

    var passwordRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Password" }),
      passwordInput
    ]);
    card.appendChild(passwordRow);

    // Create button
    var createBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-create-btn",
      "aria-label": "Create Archive",
      title: "Create Archive",
      type: "button",
      onClick: function () {
        if (!currentSources.length) {
          showError("Please select at least one file or folder to archive.");
          return;
        }
        clearError();
        statusBar.textContent = "Creating archive...";

        var pw = passwordInput.value.trim();
        if (pw) {
          window.FOSS.api("archive_protect", {
            source_paths: currentSources,
            password: pw,
            format: formatSelect.value
          }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "Protected bundle created successfully.";
              showResult(res.output_path, "Protected Bundle Created");
            } else {
              showError("Failed to create protected bundle.");
            }
          });
        } else {
          window.FOSS.api("archive_create", {
            sources: currentSources,
            format: formatSelect.value
          }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "Archive created successfully.";
              showResult(res.output_path, "Archive Created");
            } else {
              showError("Failed to create archive.");
            }
          });
        }
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Create Archive" })
    ]);

    var actionRow = window.FOSS.dom.el("div", { className: "row" }, [createBtn]);
    card.appendChild(actionRow);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(card);
  }

  function renderExtract(panel, ctx) {
    panel.innerHTML = "";

    var currentArchive = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Extract Archive" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Extract ZIP or TAR archives to a target directory locally."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "archive-extract-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "archive-extract-error"
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
      "data-testid": "archive-extract-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-extract-card",
        title: titleText || "Files Extracted",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var archiveDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "archive-file-display",
      "data-truncate-ok": "true",
      title: "No archive selected",
      text: "No archive selected"
    });

    var chooseArchiveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-choose-archive",
      "aria-label": "Choose archive",
      title: "Choose archive",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentArchive = res.paths[0];
          archiveDisplay.textContent = currentArchive;
          archiveDisplay.title = currentArchive;
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Archive" })
    ]);

    var archiveRow = window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [
      archiveDisplay,
      window.FOSS.dom.el("div", { className: "row" }, [chooseArchiveBtn])
    ]);
    card.appendChild(archiveRow);

    var destInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "archive-extract-dest",
      "aria-label": "Target extraction folder",
      "data-truncate-ok": "true",
      title: "Optional: extraction directory",
      placeholder: "Optional: extraction directory (defaults to archive folder)"
    });

    var chooseDestBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Browse destination",
      title: "Browse destination",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            destInput.value = res.paths[0];
            destInput.title = res.paths[0];
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    var destRow = window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
      destInput,
      chooseDestBtn
    ]);
    card.appendChild(destRow);

    var passwordInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input grow",
      "data-testid": "archive-extract-password",
      "aria-label": "Password (if bundle is encrypted)",
      title: "Password (if bundle is encrypted)",
      placeholder: "Password (if bundle is encrypted)"
    });

    var pwRow = window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Password" }),
      passwordInput
    ]);
    card.appendChild(pwRow);

    var extractBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-extract-btn",
      "aria-label": "Extract Archive",
      title: "Extract Archive",
      type: "button",
      onClick: function () {
        if (!currentArchive) {
          showError("Please choose an archive file to extract.");
          return;
        }
        clearError();
        statusBar.textContent = "Extracting archive...";

        var pw = passwordInput.value.trim();
        if (pw) {
          window.FOSS.api("archive_unprotect", {
            bundle_path: currentArchive,
            target_dir: destInput.value.trim(),
            password: pw
          }).then(function (res) {
            if (res && res.extracted) {
              statusBar.textContent = "Extracted " + res.extracted.length + " files successfully.";
              showResult(res.target_dir, "Decrypted and Extracted");
            } else {
              showError("Failed to extract encrypted bundle. Check password.");
            }
          });
        } else {
          window.FOSS.api("archive_extract", {
            archive_path: currentArchive,
            target_dir: destInput.value.trim()
          }).then(function (res) {
            if (res && res.extracted) {
              statusBar.textContent = "Extracted " + res.extracted.length + " files successfully.";
              showResult(res.target_dir, "Extracted Successfully");
            } else {
              showError("Failed to extract archive.");
            }
          });
        }
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Extract Archive" })
    ]);

    var actionRow = window.FOSS.dom.el("div", { className: "row" }, [extractBtn]);
    card.appendChild(actionRow);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(card);
  }

  function renderInspect(panel, ctx) {
    panel.innerHTML = "";

    var currentArchive = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Inspect Archive" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Inspect archive member list, inspect uncompressed sizes, and verify local integrity."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "archive-inspect-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "archive-inspect-error"
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

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    var archiveDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "archive-inspect-display",
      "data-truncate-ok": "true",
      title: "No archive selected",
      text: "No archive selected"
    });

    var chooseArchiveBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-inspect-choose",
      "aria-label": "Choose archive to inspect",
      title: "Choose archive to inspect",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentArchive = res.paths[0];
          archiveDisplay.textContent = currentArchive;
          archiveDisplay.title = currentArchive;
          loadArchiveMembers();
        });
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Choose Archive" })
    ]);

    var testIntegrityBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-test-integrity-btn",
      "aria-label": "Test integrity",
      title: "Test integrity",
      type: "button",
      onClick: function () {
        if (!currentArchive) {
          showError("Please choose an archive file first.");
          return;
        }
        clearError();
        statusBar.textContent = "Testing integrity...";
        window.FOSS.api("archive_test", { archive_path: currentArchive }).then(function (res) {
          if (res && res.valid) {
            statusBar.textContent = "Integrity check passed: archive is valid.";
          } else {
            showError(res && res.message ? res.message : "Archive integrity check failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Test Integrity" })
    ]);

    var toolbar = window.FOSS.dom.el("div", { className: "row" }, [chooseArchiveBtn, testIntegrityBtn]);
    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [archiveDisplay, toolbar]));

    var tableContainer = window.FOSS.dom.el("div", {
      className: "table-wrap scroll-x",
      "data-testid": "archive-member-table"
    });
    tableContainer.innerHTML = '<div class="text-sm text-muted p-4 text-center">No archive loaded. Choose an archive to view its member list.</div>';
    card.appendChild(tableContainer);

    function loadArchiveMembers() {
      if (!currentArchive) return;
      statusBar.textContent = "Reading member list...";
      window.FOSS.api("archive_list", { archive_path: currentArchive }).then(function (res) {
        if (!res || !res.contents) {
          showError("Failed to read archive contents.");
          return;
        }
        statusBar.textContent = "Loaded " + res.contents.length + " members (" + (res.format || "archive") + ").";
        renderMemberTable(res.contents);
      });
    }

    function renderMemberTable(members) {
      tableContainer.innerHTML = "";
      var tbl = window.FOSS.dom.el("table", { className: "table w-full" });
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { className: "w-12 text-left", text: "#" }),
          window.FOSS.dom.el("th", { className: "text-left", text: "Member Path" }),
          window.FOSS.dom.el("th", { className: "w-24 text-left", text: "Type" })
        ])
      ]);
      tbl.appendChild(thead);

      var tbody = window.FOSS.dom.el("tbody", {});
      for (var i = 0; i < members.length; i++) {
        var m = members[i];
        var isDir = m.endsWith("/") || m.endsWith("\\");
        var tr = window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("td", { className: "text-muted text-xs", text: String(i + 1) }),
          window.FOSS.dom.el("td", { className: "font-mono text-sm", style: "word-break: break-all;", text: m }),
          window.FOSS.dom.el("td", { className: "text-xs", text: isDir ? "Directory" : "File" })
        ]);
        tbody.appendChild(tr);
      }
      tbl.appendChild(tbody);
      tableContainer.appendChild(tbl);
    }

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(card);
  }

  function renderProtect(panel, ctx) {
    panel.innerHTML = "";

    var currentSource = "";
    var currentBundle = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Password-Protected Bundles" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Create encrypted archive bundles with a password-derived key, rotate passwords, and verify integrity."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "archive-protect-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "archive-protect-error"
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
      "data-testid": "archive-protect-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-protect-card",
        title: titleText || "Bundle Action Complete",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    // Card 1: Create encrypted bundle
    var encryptCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    encryptCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Create Encrypted Bundle" }));

    var protectSourceDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "archive-protect-source",
      "data-truncate-ok": "true",
      title: "No source selected",
      text: "No source selected"
    });

    var chooseProtectSourceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Choose source folder or file",
      title: "Choose source folder or file",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentSource = res.paths[0];
          protectSourceDisplay.textContent = currentSource;
          protectSourceDisplay.title = currentSource;
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Source" })
    ]);

    encryptCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [protectSourceDisplay, chooseProtectSourceBtn]));

    var protectPwInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input grow",
      "data-testid": "archive-protect-password",
      "aria-label": "Bundle encryption password",
      title: "Bundle encryption password",
      placeholder: "Enter encryption password"
    });

    encryptCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-3" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Password" }),
      protectPwInput
    ]));

    var protectBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-protect-btn",
      "aria-label": "Create Protected Bundle",
      title: "Create Protected Bundle",
      type: "button",
      onClick: function () {
        if (!currentSource) {
          showError("Please select a source folder or file to protect.");
          return;
        }
        var pw = protectPwInput.value.trim();
        if (!pw) {
          showError("Please enter a password for the encrypted bundle.");
          return;
        }
        clearError();
        statusBar.textContent = "Creating protected bundle...";
        window.FOSS.api("archive_protect", {
          source_paths: [currentSource],
          password: pw
        }).then(function (res) {
          if (res && res.output_path) {
            statusBar.textContent = "Protected bundle created: " + res.output_path;
            showResult(res.output_path, "Encrypted Bundle Ready");
          } else {
            showError("Failed to create encrypted bundle.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("lock", 16),
      window.FOSS.dom.el("span", { text: "Create Protected Bundle" })
    ]);

    encryptCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [protectBtn]));

    // Card 2: Key rotation
    var rotateCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });
    rotateCard.appendChild(window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Key Rotation" }));

    var rotateBundleDisplay = window.FOSS.dom.el("div", {
      className: "font-mono text-sm text-muted grow",
      "data-testid": "archive-rotate-bundle",
      "data-truncate-ok": "true",
      title: "No bundle selected",
      text: "No bundle selected"
    });

    var chooseRotateBundleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Choose bundle to rotate",
      title: "Choose bundle to rotate",
      type: "button",
      onClick: function () {
        clearError();
        window.FOSS.api("select_file", {}).then(function (res) {
          if (!res || res.cancelled || !res.paths || !res.paths.length) return;
          currentBundle = res.paths[0];
          rotateBundleDisplay.textContent = currentBundle;
          rotateBundleDisplay.title = currentBundle;
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose Bundle" })
    ]);

    rotateCard.appendChild(window.FOSS.dom.el("div", { className: "flex items-center justify-between flex-wrap gap-2" }, [rotateBundleDisplay, chooseRotateBundleBtn]));

    var oldPwInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input grow",
      "data-testid": "archive-rotate-old-pw",
      "aria-label": "Current bundle password",
      title: "Current bundle password",
      placeholder: "Current password"
    });

    var newPwInput = window.FOSS.dom.el("input", {
      type: "password",
      className: "input grow",
      "data-testid": "archive-rotate-new-pw",
      "aria-label": "New bundle password",
      title: "New bundle password",
      placeholder: "New password"
    });

    rotateCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "Old Password" }),
      oldPwInput,
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0", text: "New Password" }),
      newPwInput
    ]));

    var rotateBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-rotate-key-btn",
      "aria-label": "Rotate bundle key",
      title: "Rotate bundle key",
      type: "button",
      onClick: function () {
        if (!currentBundle) {
          showError("Please select a bundle file to rotate.");
          return;
        }
        var oldP = oldPwInput.value.trim();
        var newP = newPwInput.value.trim();
        if (!oldP || !newP) {
          showError("Please provide both old and new passwords.");
          return;
        }
        clearError();
        statusBar.textContent = "Rotating bundle key...";
        window.FOSS.api("archive_rotate_key", {
          bundle_path: currentBundle,
          old_password: oldP,
          new_password: newP
        }).then(function (res) {
          if (res && res.rotated) {
            statusBar.textContent = "Key rotated successfully: " + res.output_path;
            showResult(res.output_path, "Bundle Key Rotated");
          } else {
            showError("Key rotation failed. Check old password.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("refresh", 16),
      window.FOSS.dom.el("span", { text: "Rotate Bundle Key" })
    ]);

    var verifyBundleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-verify-integrity-btn",
      "aria-label": "Verify bundle integrity",
      title: "Verify bundle integrity",
      type: "button",
      onClick: function () {
        if (!currentBundle) {
          showError("Please select a bundle file first.");
          return;
        }
        clearError();
        statusBar.textContent = "Verifying bundle integrity...";
        window.FOSS.api("archive_verify_integrity", {
          bundle_path: currentBundle,
          password: oldPwInput.value.trim() || undefined
        }).then(function (res) {
          if (res && res.valid) {
            statusBar.textContent = "Integrity verified: " + res.entries.length + " valid member hashes.";
          } else {
            showError("Bundle integrity check failed.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Verify Integrity" })
    ]);

    rotateCard.appendChild(window.FOSS.dom.el("div", { className: "row" }, [rotateBtn, verifyBundleBtn]));

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(encryptCard);
    panel.appendChild(rotateCard);
  }

  function renderBackup(panel, ctx) {
    panel.innerHTML = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Incremental Backup & Snapshots" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Compare directory snapshots and generate incremental backup sets that only include changed files."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "archive-backup-status",
      text: "Ready"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden",
      "data-testid": "archive-backup-error"
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
      "data-testid": "archive-backup-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "archive-backup-card",
        title: titleText || "Backup Created",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var card = window.FOSS.dom.el("div", { className: "card flex-col gap-3" });

    // Source folder
    var sourceInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "archive-backup-source",
      "aria-label": "Source directory for backup",
      "data-truncate-ok": "true",
      title: "Source directory",
      placeholder: "Source directory"
    });

    var chooseSourceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Browse source directory",
      title: "Browse source directory",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            sourceInput.value = res.paths[0];
            sourceInput.title = res.paths[0];
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0 w-28", text: "Source Folder" }),
      sourceInput,
      chooseSourceBtn
    ]));

    // Backup folder
    var targetInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input grow font-mono text-sm",
      "data-testid": "archive-backup-target",
      "aria-label": "Target backup directory",
      "data-truncate-ok": "true",
      title: "Backup directory",
      placeholder: "Backup directory"
    });

    var chooseTargetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "aria-label": "Browse backup directory",
      title: "Browse backup directory",
      type: "button",
      onClick: function () {
        window.FOSS.api("select_folder", {}).then(function (res) {
          if (res && !res.cancelled && res.paths && res.paths.length) {
            targetInput.value = res.paths[0];
            targetInput.title = res.paths[0];
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Browse" })
    ]);

    card.appendChild(window.FOSS.dom.el("div", { className: "flex items-center gap-2" }, [
      window.FOSS.dom.el("label", { className: "text-sm text-muted shrink-0 w-28", text: "Backup Folder" }),
      targetInput,
      chooseTargetBtn
    ]));

    var snapshotBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "archive-snapshot-btn",
      "aria-label": "Take directory snapshot",
      title: "Take directory snapshot",
      type: "button",
      onClick: function () {
        var src = sourceInput.value.trim();
        if (!src) {
          showError("Please enter or select a source directory.");
          return;
        }
        clearError();
        statusBar.textContent = "Taking filesystem snapshot...";
        window.FOSS.api("archive_snapshot", { directory_path: src }).then(function (res) {
          if (res && res.snapshot) {
            statusBar.textContent = "Snapshot created: " + res.file_count + " files indexed.";
          } else {
            showError("Failed to take directory snapshot.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("camera", 16),
      window.FOSS.dom.el("span", { text: "Take Snapshot" })
    ]);

    var incrementalBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "archive-incremental-backup-btn",
      "aria-label": "Create incremental backup",
      title: "Create incremental backup",
      type: "button",
      onClick: function () {
        var src = sourceInput.value.trim();
        var dst = targetInput.value.trim();
        if (!src || !dst) {
          showError("Please specify both source directory and backup destination folder.");
          return;
        }
        clearError();
        statusBar.textContent = "Creating incremental backup...";
        window.FOSS.api("archive_incremental_backup", {
          directory_path: src,
          backup_dir: dst
        }).then(function (res) {
          if (res && res.archive_path) {
            statusBar.textContent = "Incremental backup created: " + res.total_files + " changed files.";
            showResult(res.archive_path, "Incremental Backup Archive");
          } else {
            showError("Failed to create incremental backup.");
          }
        });
      }
    }, [
      window.FOSS.icons.el("check", 16),
      window.FOSS.dom.el("span", { text: "Create Incremental Backup" })
    ]);

    var actionRow = window.FOSS.dom.el("div", { className: "row" }, [snapshotBtn, incrementalBtn]);
    card.appendChild(actionRow);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(card);
  }

  window.FOSS.router.register({
    id: "archive",
    title: "Archive & Packaging",
    navName: "Archive",
    category: "Utilities",
    icon: "archive",
    tabs: [
      { id: "create", label: "Create", render: renderCreate },
      { id: "extract", label: "Extract", render: renderExtract },
      { id: "inspect", label: "Inspect", render: renderInspect },
      { id: "protect", label: "Protect", render: renderProtect },
      { id: "backup", label: "Backup", render: renderBackup }
    ]
  });
})();
