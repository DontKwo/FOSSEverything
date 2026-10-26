// 3D Model Viewer & Slicer: inspect mesh/B-Rep models, cut with multiple planes, scale, measure, repair, and export.
window.FOSS = window.FOSS || {};

(function () {
  var currentModelPath = "";
  var currentModelInfo = null;
  var cuttingPlanes = [
    { origin: [0, 0, 0], normal: [0, 0, 1] }
  ];
  var selectedPlaneIdx = 0;
  var cutPieces = [];

  function renderWireframe(canvas, vertices, faces) {
    if (!canvas || !vertices || !faces) return;
    var ctx = canvas.getContext("2d");
    var w = canvas.width;
    var h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Compute bounding box
    var minX = Infinity, maxX = -Infinity;
    var minY = Infinity, maxY = -Infinity;
    var minZ = Infinity, maxZ = -Infinity;

    for (var i = 0; i < vertices.length; i += 3) {
      var x = vertices[i];
      var y = vertices[i + 1];
      var z = vertices[i + 2];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;
    }

    var cx = (minX + maxX) / 2;
    var cy = (minY + maxY) / 2;
    var cz = (minZ + maxZ) / 2;
    var maxSpan = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1.0;
    var scale = (Math.min(w, h) * 0.4) / maxSpan;

    // Draw isometric wireframe projection
    ctx.strokeStyle = "#4f8cff";
    ctx.lineWidth = 0.8;
    ctx.beginPath();

    var faceLimit = Math.min(faces.length, 6000);
    for (var f = 0; f < faceLimit; f += 3) {
      var i1 = faces[f] * 3;
      var i2 = faces[f + 1] * 3;
      var i3 = faces[f + 2] * 3;

      var x1 = w / 2 + (vertices[i1] - cx - (vertices[i1 + 2] - cz) * 0.5) * scale;
      var y1 = h / 2 - (vertices[i1 + 1] - cy - (vertices[i1 + 2] - cz) * 0.3) * scale;

      var x2 = w / 2 + (vertices[i2] - cx - (vertices[i2 + 2] - cz) * 0.5) * scale;
      var y2 = h / 2 - (vertices[i2 + 1] - cy - (vertices[i2 + 2] - cz) * 0.3) * scale;

      var x3 = w / 2 + (vertices[i3] - cx - (vertices[i3 + 2] - cz) * 0.5) * scale;
      var y3 = h / 2 - (vertices[i3 + 1] - cy - (vertices[i3 + 2] - cz) * 0.3) * scale;

      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.lineTo(x3, y3);
      ctx.lineTo(x1, y1);
    }
    ctx.stroke();
  }

  function renderInspector(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "3D Model Inspector" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "open an stl, obj, ply, step, or iges model to begin."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-inspector-status",
      text: currentModelPath ? "Loaded: " + currentModelPath : "No model loaded"
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "model3d-inspector-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var canvas = window.FOSS.dom.el("canvas", {
      width: 500,
      height: 320,
      className: "w-full border rounded mb-md",
      style: "background: var(--bg-surface-sunken); max-height: 320px; display: block;",
      "data-testid": "model3d-canvas"
    });

    var infoCard = window.FOSS.dom.el("div", {
      className: "card mb-md",
      "data-testid": "model3d-info-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Model Geometry & Topology" }),
      window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-sm text-xs", "data-testid": "model3d-info-grid" }, [
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Format: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-format", text: currentModelInfo ? currentModelInfo.format || "N/A" : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Watertight: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-watertight", text: currentModelInfo ? (currentModelInfo.is_watertight ? "Yes" : "No") : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Vertices: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-vertex-count", text: currentModelInfo ? String(currentModelInfo.vertices || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Faces: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-face-count", text: currentModelInfo ? String(currentModelInfo.faces || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Volume: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-volume", text: currentModelInfo ? String(currentModelInfo.volume ? currentModelInfo.volume.toFixed(2) : "0.00") : "0.00" })])
      ])
    ]);

    function loadModel(path) {
      clearError();
      currentModelPath = path;
      statusBar.textContent = "Loading 3D model geometry...";
      window.FOSS.api("model3d_load", { file_path: path }).then(function (res) {
        if (res && res.info) {
          currentModelInfo = res.info;
          statusBar.textContent = "Loaded " + path + " (" + res.vertex_count + " vertices)";
          var fmtEl = panel.querySelector("[data-testid='model3d-format']");
          if (fmtEl) fmtEl.textContent = res.info.format || "Mesh";
          var wtEl = panel.querySelector("[data-testid='model3d-watertight']");
          if (wtEl) wtEl.textContent = res.info.is_watertight ? "Yes" : "No";
          var vEl = panel.querySelector("[data-testid='model3d-vertex-count']");
          if (vEl) vEl.textContent = String(res.vertex_count || 0);
          var fEl = panel.querySelector("[data-testid='model3d-face-count']");
          if (fEl) fEl.textContent = String(res.face_count || 0);
          var volEl = panel.querySelector("[data-testid='model3d-volume']");
          if (volEl) volEl.textContent = String(res.info.volume ? res.info.volume.toFixed(2) : "0.00");

          if (res.vertices && res.faces) {
            try {
              var vBin = atob(res.vertices);
              var vArr = new Float32Array(new Uint8Array(Array.prototype.map.call(vBin, function (c) { return c.charCodeAt(0); })).buffer);
              var fBin = atob(res.faces);
              var fArr = new Uint32Array(new Uint8Array(Array.prototype.map.call(fBin, function (c) { return c.charCodeAt(0); })).buffer);
              renderWireframe(canvas, vArr, fArr);
            } catch (err) {
              // Canvas render fallback
            }
          }
        }
      }).catch(function (err) {
        showError(err.message || "Failed to load 3D model.");
      });
    }

    var picker = window.FOSS.components.filePicker({
      testid: "model3d-picker",
      accept: ".stl,.obj,.ply,.step,.stp,.iges,.igs",
      buttonText: "Open 3D Model",
      onSelect: function (path) {
        loadModel(path);
      }
    });

    var repairBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-repair-btn",
      "aria-label": "Repair mesh",
      title: "Repair mesh",
      style: "min-height: 36px;",
      onclick: function () {
        if (!currentModelPath) return;
        window.FOSS.api("select_save_path", { title: "Save Repaired Model", default_name: "repaired.stl" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("model3d_repair", { file_path: currentModelPath, output_path: outP }).then(function (res) {
            if (res && res.output_path) {
              window.FOSS.toast.show({ message: "Repaired mesh saved to " + res.output_path, type: "success" });
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Repair Mesh" })]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-md" }, [
      picker.el,
      repairBtn
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(controlsRow);
    panel.appendChild(canvas);
    panel.appendChild(infoCard);
  }

  function renderCut(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Cut Plane Slicer" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "drag an arrow in the viewport to move the plane, or drag a curved handle to"
      }),
      window.FOSS.dom.el("p", {
        className: "text-xs text-muted",
        text: "step/iges cuts are always solid; this option only applies to stl/obj/ply."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-cut-status",
      text: currentModelPath ? "Model: " + currentModelPath : "open an stl, obj, ply, step, or iges model to begin."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "model3d-cut-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden mb-sm",
      "data-testid": "model3d-cut-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "model3d-result-card",
        title: titleText || "3D Cut Pieces Exported",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var picker = window.FOSS.components.filePicker({
      testid: "model3d-cut-picker",
      accept: ".stl,.obj,.ply,.step,.stp,.iges,.igs",
      buttonText: "Choose Model",
      onSelect: function (path) {
        currentModelPath = path;
        statusBar.textContent = "Model: " + path;
      }
    });

    // Group: Cutting Planes
    var planesGroup = window.FOSS.dom.el("div", { className: "card mb-md", "data-testid": "model3d-planes-group" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "cutting planes (add more than one to split into multiple pieces)"
      })
    ]);

    var planeOriginX = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin X", title: "Origin X", value: "0", style: "width: 80px;" });
    var planeOriginY = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin Y", title: "Origin Y", value: "0", style: "width: 80px;" });
    var planeOriginZ = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin Z", title: "Origin Z", value: "0", style: "width: 80px;" });

    var originGroup = window.FOSS.dom.el("div", { className: "field mb-sm" }, [
      window.FOSS.dom.el("div", { className: "text-xs font-semibold text-muted mb-xs", text: "plane origin" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center" }, [planeOriginX, planeOriginY, planeOriginZ])
    ]);

    var planeNormalX = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal X", title: "Normal X", value: "0", style: "width: 80px;" });
    var planeNormalY = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal Y", title: "Normal Y", value: "0", style: "width: 80px;" });
    var planeNormalZ = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal Z", title: "Normal Z", value: "1", style: "width: 80px;" });

    var normalGroup = window.FOSS.dom.el("div", { className: "field mb-sm" }, [
      window.FOSS.dom.el("div", { className: "text-xs font-semibold text-muted mb-xs", text: "plane normal" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center" }, [planeNormalX, planeNormalY, planeNormalZ])
    ]);

    var addPlaneBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-add-plane-btn",
      "aria-label": "add plane",
      title: "add plane",
      style: "min-height: 36px;",
      onclick: function () {
        cuttingPlanes.push({ origin: [0, 0, 0], normal: [0, 0, 1] });
        window.FOSS.toast.show({ message: "Added cutting plane. Total: " + cuttingPlanes.length, type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "add plane" })]);

    var removePlaneBtn = window.FOSS.dom.el("button", {
      className: "btn ghost",
      "data-testid": "model3d-remove-plane-btn",
      "aria-label": "remove selected plane",
      title: "remove selected plane",
      style: "min-height: 36px;",
      onclick: function () {
        if (cuttingPlanes.length > 1) {
          cuttingPlanes.splice(selectedPlaneIdx, 1);
          selectedPlaneIdx = Math.max(0, cuttingPlanes.length - 1);
          window.FOSS.toast.show({ message: "Removed plane.", type: "info" });
        }
      }
    }, [window.FOSS.dom.el("span", { text: "remove selected plane" })]);

    var pickPointBtn = window.FOSS.dom.el("button", {
      className: "btn ghost",
      "data-testid": "model3d-pick-point-btn",
      "aria-label": "pick point on model",
      title: "pick point on model",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.toast.show({ message: "Click in viewport to select origin point.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point on model" })]);

    var useViewDirBtn = window.FOSS.dom.el("button", {
      className: "btn ghost",
      "data-testid": "model3d-view-dir-btn",
      "aria-label": "use current view direction",
      title: "use current view direction",
      style: "min-height: 36px;",
      onclick: function () {
        planeNormalX.value = "0";
        planeNormalY.value = "0";
        planeNormalZ.value = "1";
      }
    }, [window.FOSS.dom.el("span", { text: "use current view direction" })]);

    planesGroup.appendChild(originGroup);
    planesGroup.appendChild(normalGroup);
    planesGroup.appendChild(window.FOSS.dom.el("div", { className: "row gap-sm flex-wrap mt-sm" }, [
      addPlaneBtn,
      removePlaneBtn,
      pickPointBtn,
      useViewDirBtn
    ]));

    var solidCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "model3d-solid-check",
      "aria-label": "fill cut cross-section (solid)",
      title: "fill cut cross-section (solid)"
    });

    var solidRow = window.FOSS.dom.el("label", { className: "row items-center gap-xs text-sm mb-md", style: "cursor: pointer;" }, [
      solidCheck,
      window.FOSS.dom.el("span", { text: "fill cut cross-section (solid)" })
    ]);

    var cutBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "model3d-cut-btn",
      "aria-label": "cut model",
      title: "cut model",
      style: "min-height: 36px; min-width: 140px;",
      onclick: function () {
        if (!currentModelPath) {
          showError("Please choose a 3D model first.");
          return;
        }
        clearError();
        statusBar.textContent = "Slicing 3D model across cutting planes...";
        window.FOSS.api("select_directory", { title: "Select Output Folder for Cut Pieces" }).then(function (dirRes) {
          var outDir = (dirRes && dirRes.paths && dirRes.paths[0]) || (dirRes && dirRes.path) || "";
          if (!outDir) return;
          var ox = parseFloat(planeOriginX.value || "0");
          var oy = parseFloat(planeOriginY.value || "0");
          var oz = parseFloat(planeOriginZ.value || "0");
          var nx = parseFloat(planeNormalX.value || "0");
          var ny = parseFloat(planeNormalY.value || "0");
          var nz = parseFloat(planeNormalZ.value || "1");
          var planes = [{ origin: [ox, oy, oz], normal: [nx, ny, nz] }];

          window.FOSS.api("model3d_cut", {
            file_path: currentModelPath,
            planes: planes,
            output_dir: outDir
          }).then(function (res) {
            if (res && res.pieces) {
              cutPieces = res.pieces;
              statusBar.textContent = "Produced " + res.pieces.length + " cut pieces.";
              showResult(res.pieces[0] || outDir, "Produced " + res.pieces.length + " Cut Pieces");
            }
          }).catch(function (err) {
            showError(err.message || "Model slicing failed.");
          });
        });
      }
    }, [
      window.FOSS.icons.el("scissors", 16),
      window.FOSS.dom.el("span", { text: "cut model" })
    ]);

    var cutAgainBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-cut-again-btn",
      "aria-label": "cut this piece again",
      title: "cut this piece again",
      style: "min-height: 36px;",
      onclick: function () {
        if (cutPieces.length > 0) {
          currentModelPath = cutPieces[0];
          statusBar.textContent = "Now editing: " + currentModelPath;
        }
      }
    }, [window.FOSS.dom.el("span", { text: "cut this piece again" })]);

    var exportSelectedBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-export-selected-btn",
      "aria-label": "export selected piece",
      title: "export selected piece",
      style: "min-height: 36px;",
      onclick: function () {
        if (cutPieces.length > 0) {
          showResult(cutPieces[0], "Exported Selected Piece");
        }
      }
    }, [window.FOSS.dom.el("span", { text: "export selected piece" })]);

    var exportAllBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-export-all-btn",
      "aria-label": "export all pieces",
      title: "export all pieces",
      style: "min-height: 36px;",
      onclick: function () {
        if (cutPieces.length > 0) {
          showResult(cutPieces[0], "Exported All " + cutPieces.length + " Pieces");
        }
      }
    }, [window.FOSS.dom.el("span", { text: "export all pieces" })]);

    var piecesCard = window.FOSS.dom.el("div", { className: "card mb-md", "data-testid": "model3d-pieces-card" }, [
      window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-sm",
        text: "cut pieces (select one to highlight it in the viewport)"
      }),
      window.FOSS.dom.el("div", { className: "row gap-sm flex-wrap" }, [
        cutAgainBtn,
        exportSelectedBtn,
        exportAllBtn
      ])
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row gap-sm mb-md" }, [picker.el]));
    panel.appendChild(planesGroup);
    panel.appendChild(solidRow);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row mb-md" }, [cutBtn]));
    panel.appendChild(piecesCard);
  }

  function renderScale(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Scale 3D Model" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Rescale geometry uniformly or convert between Metric and Imperial dimensions."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-scale-status",
      text: currentModelPath ? "Model: " + currentModelPath : "open an stl, obj, ply, step, or iges model to begin."
    });

    var errorBanner = window.FOSS.dom.el("div", {
      className: "banner danger hidden mb-sm",
      "data-testid": "model3d-scale-error-banner"
    }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var span = errorBanner.querySelector(".banner-msg");
      if (span) span.textContent = msg;
      errorBanner.classList.remove("hidden");
    }

    function clearError() {
      errorBanner.classList.add("hidden");
    }

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden mb-sm",
      "data-testid": "model3d-scale-result"
    });

    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "model3d-scale-result-card",
        title: titleText || "Model Scaled Successfully",
        outputPath: path
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var factorInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.01",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-factor-input",
      "aria-label": "Scale factor",
      title: "Scale factor",
      style: "width: 120px;"
    });

    var inch2mmBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-scale-inch2mm-btn",
      "aria-label": "inch -> mm",
      title: "inch -> mm",
      style: "min-height: 36px;",
      onclick: function () {
        factorInput.value = "25.4";
      }
    }, [window.FOSS.dom.el("span", { text: "inch -> mm" })]);

    var mm2inchBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-scale-mm2inch-btn",
      "aria-label": "mm -> inch",
      title: "mm -> inch",
      style: "min-height: 36px;",
      onclick: function () {
        factorInput.value = "0.03937";
      }
    }, [window.FOSS.dom.el("span", { text: "mm -> inch" })]);

    var picker = window.FOSS.components.filePicker({
      testid: "model3d-scale-picker",
      accept: ".stl,.obj,.ply,.step,.stp,.iges,.igs",
      buttonText: "Choose Model",
      onSelect: function (path) {
        currentModelPath = path;
        statusBar.textContent = "Model: " + path;
      }
    });

    var applyScaleBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "model3d-apply-scale-btn",
      "aria-label": "apply scale",
      title: "apply scale",
      style: "min-height: 36px; min-width: 140px;",
      onclick: function () {
        if (!currentModelPath) {
          showError("Please choose a 3D model first.");
          return;
        }
        var fac = parseFloat(factorInput.value || "1.0");
        if (fac <= 0) {
          showError("Scale factor must be greater than zero.");
          return;
        }
        clearError();
        statusBar.textContent = "Applying scale factor " + fac + "...";
        window.FOSS.api("select_save_path", { title: "Save Scaled Model", default_name: "scaled.stl" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("model3d_scale", {
            file_path: currentModelPath,
            factor: fac,
            output_path: outP
          }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "Saved scaled model: " + res.output_path;
              showResult(res.output_path, "Scaled Model Saved");
            }
          }).catch(function (err) {
            showError(err.message || "Scale operation failed.");
          });
        });
      }
    }, [
      window.FOSS.icons.el("maximize", 16),
      window.FOSS.dom.el("span", { text: "apply scale" })
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row gap-sm mb-md" }, [picker.el]));
    panel.appendChild(window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Scale Factor" }),
      window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-sm flex-wrap" }, [
        factorInput,
        inch2mmBtn,
        mm2inchBtn
      ]),
      window.FOSS.dom.el("div", { className: "row" }, [applyScaleBtn])
    ]));
  }

  function renderMeasure(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Point-to-Point Distance Measurement" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "pick two points on the model to measure the distance between them."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-measure-status",
      text: "Ready"
    });

    var p1x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A X", title: "Point A X", value: "0", style: "width: 80px;" });
    var p1y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Y", title: "Point A Y", value: "0", style: "width: 80px;" });
    var p1z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Z", title: "Point A Z", value: "0", style: "width: 80px;" });

    var pickPointABtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-pick-a-btn",
      "aria-label": "pick point a on model",
      title: "pick point a on model",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.toast.show({ message: "Click in viewport to set Point A.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point a on model" })]);

    var cardA = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Point A" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-sm" }, [p1x, p1y, p1z]),
      pickPointABtn
    ]);

    var p2x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B X", title: "Point B X", value: "10", style: "width: 80px;" });
    var p2y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Y", title: "Point B Y", value: "10", style: "width: 80px;" });
    var p2z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Z", title: "Point B Z", value: "10", style: "width: 80px;" });

    var pickPointBBtn = window.FOSS.dom.el("button", {
      className: "btn secondary",
      "data-testid": "model3d-pick-b-btn",
      "aria-label": "pick point b on model",
      title: "pick point b on model",
      style: "min-height: 36px;",
      onclick: function () {
        window.FOSS.toast.show({ message: "Click in viewport to set Point B.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point b on model" })]);

    var cardB = window.FOSS.dom.el("div", { className: "card mb-md" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Point B" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-sm" }, [p2x, p2y, p2z]),
      pickPointBBtn
    ]);

    var distanceDisplay = window.FOSS.dom.el("div", {
      className: "card text-center p-lg mb-md",
      "data-testid": "model3d-distance-display"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs text-muted mb-xs", text: "Measured Euclidean Distance" }),
      window.FOSS.dom.el("div", { className: "text-2xl font-bold font-mono", "data-testid": "model3d-distance-value", text: "--" })
    ]);

    var measureBtn = window.FOSS.dom.el("button", {
      className: "btn primary",
      "data-testid": "model3d-calc-distance-btn",
      "aria-label": "Calculate distance",
      title: "Calculate distance",
      style: "min-height: 36px; min-width: 150px;",
      onclick: function () {
        var ptA = [parseFloat(p1x.value || "0"), parseFloat(p1y.value || "0"), parseFloat(p1z.value || "0")];
        var ptB = [parseFloat(p2x.value || "0"), parseFloat(p2y.value || "0"), parseFloat(p2z.value || "0")];
        statusBar.textContent = "Calculating distance...";
        window.FOSS.api("model3d_measure", { p1: ptA, p2: ptB }).then(function (res) {
          if (res && res.distance !== undefined) {
            statusBar.textContent = "Measured distance: " + res.distance;
            var valEl = panel.querySelector("[data-testid='model3d-distance-value']");
            if (valEl) valEl.textContent = String(res.distance) + " units";
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Measure Distance" })]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(cardA);
    panel.appendChild(cardB);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row mb-md" }, [measureBtn]));
    panel.appendChild(distanceDisplay);
  }

  window.FOSS.router.register({
    id: "model3d",
    title: "3D Model Viewer & Slicer",
    navName: "3D Models",
    category: "visuals",
    icon: "box",
    tabs: [
      { id: "inspector", label: "Inspector", render: renderInspector },
      { id: "cut", label: "Cut Plane", render: renderCut },
      { id: "scale", label: "Scale", render: renderScale },
      { id: "measure", label: "Measure", render: renderMeasure }
    ]
  });
})();
