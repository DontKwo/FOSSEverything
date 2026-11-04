// 3D Model Studio: Inspect, slice with cutting planes, rescale, measure, repair, and export.
window.FOSS = window.FOSS || {};

(function () {
  var currentModelPath = "";
  var currentModelInfo = null;
  var currentVertices = null;
  var currentFaces = null;
  var modelMeshBuffer = null;
  var modelBounds = { center: [0, 0, 0], span: 1.0, min: [-0.5, -0.5, -0.5], max: [0.5, 0.5, 0.5] };
  var cuttingPlanes = [
    { origin: [0, 0, 0], normal: [0, 0, 1] }
  ];
  var selectedPlaneIdx = 0;
  var cutPieces = [];
  var selectedPieceIdx = -1;
  var wireframeMode = false;
  var showAxes = true;
  var showScales = true;
  var showBoundingBox = true;
  var measurePoints = { a: [0, 0, 0], b: [10, 10, 10] };
  var pickMode = null;

  var camera = {
    yaw: 0.785,
    pitch: 0.523,
    distance: 3.0,
    target: [0, 0, 0]
  };

  function base64ToFloat32Array(b64) {
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) {
      bytes[i] = bin.charCodeAt(i);
    }
    return new Float32Array(bytes.buffer);
  }

  function base64ToUint32Array(b64) {
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) {
      bytes[i] = bin.charCodeAt(i);
    }
    return new Uint32Array(bytes.buffer);
  }

  function buildMeshBuffers(vertices, faces) {
    if (!vertices || !faces) return null;
    var faceLimit = Math.min(faces.length / 3, 500000);
    var posArr = new Float32Array(faceLimit * 9);
    var normArr = new Float32Array(faceLimit * 9);
    var wireframeArr = new Float32Array(faceLimit * 18);

    var minX = Infinity, maxX = -Infinity;
    var minY = Infinity, maxY = -Infinity;
    var minZ = Infinity, maxZ = -Infinity;

    for (var v = 0; v < vertices.length; v += 3) {
      var vx = vertices[v];
      var vy = vertices[v + 1];
      var vz = vertices[v + 2];
      if (vx < minX) minX = vx;
      if (vx > maxX) maxX = vx;
      if (vy < minY) minY = vy;
      if (vy > maxY) maxY = vy;
      if (vz < minZ) minZ = vz;
      if (vz > maxZ) maxZ = vz;
    }

    var cx = (minX + maxX) / 2;
    var cy = (minY + maxY) / 2;
    var cz = (minZ + maxZ) / 2;
    var span = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1.0;
    modelBounds = { center: [cx, cy, cz], span: span, min: [minX, minY, minZ], max: [maxX, maxY, maxZ] };
    camera.target = [0, 0, 0];
    camera.distance = span * 2.2;

    var outIdx = 0;
    for (var f = 0; f < faceLimit * 3; f += 3) {
      var i0 = faces[f] * 3;
      var i1 = faces[f + 1] * 3;
      var i2 = faces[f + 2] * 3;

      var x0 = vertices[i0] - cx, y0 = vertices[i0 + 1] - cy, z0 = vertices[i0 + 2] - cz;
      var x1 = vertices[i1] - cx, y1 = vertices[i1 + 1] - cy, z1 = vertices[i1 + 2] - cz;
      var x2 = vertices[i2] - cx, y2 = vertices[i2 + 1] - cy, z2 = vertices[i2 + 2] - cz;

      var ax = x1 - x0, ay = y1 - y0, az = z1 - z0;
      var bx = x2 - x0, by = y2 - y0, bz = z2 - z0;
      var nx = ay * bz - az * by;
      var ny = az * bx - ax * bz;
      var nz = ax * by - ay * bx;
      var nLen = Math.hypot(nx, ny, nz) || 1.0;
      nx /= nLen; ny /= nLen; nz /= nLen;

      // Solid triangle vertices
      posArr[outIdx] = x0; posArr[outIdx + 1] = y0; posArr[outIdx + 2] = z0;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;

      posArr[outIdx] = x1; posArr[outIdx + 1] = y1; posArr[outIdx + 2] = z1;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;

      posArr[outIdx] = x2; posArr[outIdx + 1] = y2; posArr[outIdx + 2] = z2;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;

      // Wireframe triangle edges: (v0, v1), (v1, v2), (v2, v0)
      var wBase = (f / 3) * 18;
      wireframeArr[wBase + 0] = x0; wireframeArr[wBase + 1] = y0; wireframeArr[wBase + 2] = z0;
      wireframeArr[wBase + 3] = x1; wireframeArr[wBase + 4] = y1; wireframeArr[wBase + 5] = z1;

      wireframeArr[wBase + 6] = x1; wireframeArr[wBase + 7] = y1; wireframeArr[wBase + 8] = z1;
      wireframeArr[wBase + 9] = x2; wireframeArr[wBase + 10] = y2; wireframeArr[wBase + 11] = z2;

      wireframeArr[wBase + 12] = x2; wireframeArr[wBase + 13] = y2; wireframeArr[wBase + 14] = z2;
      wireframeArr[wBase + 15] = x0; wireframeArr[wBase + 16] = y0; wireframeArr[wBase + 17] = z0;
    }

    return {
      positions: posArr,
      normals: normArr,
      wireframePositions: wireframeArr,
      vertexCount: faceLimit * 3,
      wireframeCount: faceLimit * 6
    };
  }

  function mat4Perspective(fovRad, aspect, near, far) {
    var f = 1.0 / Math.tan(fovRad / 2);
    var nf = 1.0 / (near - far);
    return new Float32Array([
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far + near) * nf, -1,
      0, 0, (2 * far * near) * nf, 0
    ]);
  }

  function mat4LookAt(eye, center, up) {
    var z0 = eye[0] - center[0], z1 = eye[1] - center[1], z2 = eye[2] - center[2];
    var len = Math.hypot(z0, z1, z2) || 1.0;
    z0 /= len; z1 /= len; z2 /= len;

    var x0 = up[1] * z2 - up[2] * z1;
    var x1 = up[2] * z0 - up[0] * z2;
    var x2 = up[0] * z1 - up[1] * z0;
    len = Math.hypot(x0, x1, x2) || 1.0;
    x0 /= len; x1 /= len; x2 /= len;

    var y0 = z1 * x2 - z2 * x1;
    var y1 = z2 * x0 - z0 * x2;
    var y2 = z0 * x1 - z1 * x0;

    return new Float32Array([
      x0, y0, z0, 0,
      x1, y1, z1, 0,
      x2, y2, z2, 0,
      -(x0 * eye[0] + x1 * eye[1] + x2 * eye[2]),
      -(y0 * eye[0] + y1 * eye[1] + y2 * eye[2]),
      -(z0 * eye[0] + z1 * eye[1] + z2 * eye[2]),
      1
    ]);
  }

  // Shared 3D Viewport Singleton
  var sharedViewportInstance = null;

  function getSharedViewport() {
    if (sharedViewportInstance) return sharedViewportInstance;

    var container = window.FOSS.dom.el("div", {
      className: "model3d-viewport-wrapper",
      "data-testid": "model3d-viewport-container"
    });

    var canvas = window.FOSS.dom.el("canvas", {
      width: 640,
      height: 480,
      "data-testid": "model3d-canvas",
      style: "width: 100%; height: 100%; display: block; cursor: grab;"
    });

    var tripodCanvas = window.FOSS.dom.el("canvas", {
      width: 72,
      height: 72,
      "data-testid": "model3d-tripod",
      "data-overlay": "true",
      "data-decorative": "true",
      style: "position: absolute; bottom: var(--space-3); right: var(--space-3); width: 4.5rem; height: 4.5rem; pointer-events: none; z-index: 10;"
    });

    var bboxBadge = window.FOSS.dom.el("div", {
      className: "model3d-overlay-badge hidden",
      "data-testid": "model3d-bbox-dimensions",
      text: "L: -- x W: -- x H: --"
    });

    var scaleBadge = window.FOSS.dom.el("div", {
      className: "model3d-overlay-badge hidden",
      "data-testid": "model3d-scale-indicator",
      text: "Scale: --"
    });

    var axesCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: showAxes,
      "data-testid": "model3d-view-axes",
      "aria-label": "Toggle Coordinate Directions",
      title: "Toggle Coordinate Directions (X: Red, Y: Green, Z: Blue)",
      onChange: function () {
        showAxes = axesCheckbox.checked;
        render();
      }
    });

    var scalesCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: showScales,
      "data-testid": "model3d-view-scales",
      "aria-label": "Toggle Coordinate Grid",
      title: "Toggle Coordinate Reference Grid and Scales",
      onChange: function () {
        showScales = scalesCheckbox.checked;
        render();
      }
    });

    var bboxCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: showBoundingBox,
      "data-testid": "model3d-view-bbox",
      "aria-label": "Toggle Bounding Box",
      title: "Toggle Bounding Box and Dimensions",
      onChange: function () {
        showBoundingBox = bboxCheckbox.checked;
        render();
      }
    });

    var resetBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "model3d-reset-view-btn",
      title: "Reset View",
      type: "button",
      onClick: function () {
        camera.yaw = 0.785;
        camera.pitch = 0.523;
        camera.distance = modelBounds.span * 2.2;
        camera.target = [0, 0, 0];
        render();
      }
    }, [window.FOSS.dom.el("span", { text: "Reset" })]);

    var wireframeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "model3d-wireframe-btn",
      title: "Toggle Wireframe",
      type: "button",
      onClick: function () {
        wireframeMode = !wireframeMode;
        render();
      }
    }, [window.FOSS.dom.el("span", { text: "Wireframe" })]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "model3d-viewport-toolbar btn-group",
      "data-overlay": "true",
      "data-obscure-ok": "true"
    }, [
      resetBtn,
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-top",
        title: "Top View",
        type: "button",
        onClick: function () {
          camera.yaw = 0;
          camera.pitch = 1.55;
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Top" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-front",
        title: "Front View",
        type: "button",
        onClick: function () {
          camera.yaw = 0;
          camera.pitch = 0;
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Front" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-side",
        title: "Side View",
        type: "button",
        onClick: function () {
          camera.yaw = 1.57;
          camera.pitch = 0;
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Side" })]),
      wireframeBtn,
      window.FOSS.dom.el("label", {
        className: "row items-center gap-xs text-xs",
        style: "cursor: pointer; margin-left: var(--space-2);"
      }, [
        axesCheckbox,
        window.FOSS.dom.el("span", { text: "Axes" })
      ]),
      window.FOSS.dom.el("label", {
        className: "row items-center gap-xs text-xs",
        style: "cursor: pointer; margin-left: var(--space-1);"
      }, [
        scalesCheckbox,
        window.FOSS.dom.el("span", { text: "Grid" })
      ]),
      window.FOSS.dom.el("label", {
        className: "row items-center gap-xs text-xs",
        style: "cursor: pointer; margin-left: var(--space-1);"
      }, [
        bboxCheckbox,
        window.FOSS.dom.el("span", { text: "Bounds" })
      ])
    ]);

    var emptyHint = window.FOSS.dom.el("div", {
      className: "model3d-overlay-badge",
      "data-overlay": "true",
      style: "bottom: var(--space-3); left: var(--space-3);",
      text: "Left-Drag: Rotate | Right-Drag: Pan | Wheel: Zoom"
    });

    var overlayStack = window.FOSS.dom.el("div", {
      className: "model3d-overlay-stack",
      "data-overlay": "true"
    }, [scaleBadge, bboxBadge]);

    container.appendChild(toolbar);
    container.appendChild(canvas);
    container.appendChild(tripodCanvas);
    container.appendChild(overlayStack);
    container.appendChild(emptyHint);

    var gl = null;
    var shaderProg = null;
    var posBuffer = null;
    var normBuffer = null;
    var linesPosBuffer = null;

    try {
      gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (gl) {
        var vsSource = [
          "attribute vec3 aPos;",
          "attribute vec3 aNorm;",
          "uniform mat4 uProj;",
          "uniform mat4 uView;",
          "varying vec3 vNorm;",
          "varying vec3 vPos;",
          "void main() {",
          "  vNorm = aNorm;",
          "  vPos = aPos;",
          "  gl_Position = uProj * uView * vec4(aPos, 1.0);",
          "}"
        ].join("\n");

        var fsSource = [
          "precision mediump float;",
          "varying vec3 vNorm;",
          "varying vec3 vPos;",
          "uniform vec4 uColor;",
          "uniform vec3 uLightDir;",
          "uniform int uUnlit;",
          "void main() {",
          "  if (uUnlit == 1) {",
          "    gl_FragColor = uColor;",
          "  } else {",
          "    vec3 norm = normalize(vNorm);",
          "    vec3 light = normalize(uLightDir);",
          "    float diff = max(dot(norm, light), 0.25);",
          "    vec3 col = uColor.rgb * diff;",
          "    gl_FragColor = vec4(col, uColor.a);",
          "  }",
          "}"
        ].join("\n");

        function compileShader(type, src) {
          var s = gl.createShader(type);
          gl.shaderSource(s, src);
          gl.compileShader(s);
          return s;
        }

        var vs = compileShader(gl.VERTEX_SHADER, vsSource);
        var fs = compileShader(gl.FRAGMENT_SHADER, fsSource);
        shaderProg = gl.createProgram();
        gl.attachShader(shaderProg, vs);
        gl.attachShader(shaderProg, fs);
        gl.linkProgram(shaderProg);

        shaderProg.aPos = gl.getAttribLocation(shaderProg, "aPos");
        shaderProg.aNorm = gl.getAttribLocation(shaderProg, "aNorm");
        shaderProg.uProj = gl.getUniformLocation(shaderProg, "uProj");
        shaderProg.uView = gl.getUniformLocation(shaderProg, "uView");
        shaderProg.uColor = gl.getUniformLocation(shaderProg, "uColor");
        shaderProg.uLightDir = gl.getUniformLocation(shaderProg, "uLightDir");
        shaderProg.uUnlit = gl.getUniformLocation(shaderProg, "uUnlit");

        posBuffer = gl.createBuffer();
        normBuffer = gl.createBuffer();
        linesPosBuffer = gl.createBuffer();
      }
    } catch (e) {
      gl = null;
    }

    function drawLines(coords, color) {
      if (!gl || !coords || coords.length === 0) return;
      gl.uniform1i(shaderProg.uUnlit, 1);
      gl.uniform4fv(shaderProg.uColor, new Float32Array(color));
      gl.bindBuffer(gl.ARRAY_BUFFER, linesPosBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, coords, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(shaderProg.aPos);
      gl.vertexAttribPointer(shaderProg.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.disableVertexAttribArray(shaderProg.aNorm);
      gl.vertexAttrib3f(shaderProg.aNorm, 0, 1, 0);
      gl.drawArrays(gl.LINES, 0, coords.length / 3);
    }

    function renderTripodGizmo() {
      if (!tripodCanvas) return;
      if (!showAxes) {
        tripodCanvas.classList.add("hidden");
        return;
      }
      tripodCanvas.classList.remove("hidden");
      var tctx = tripodCanvas.getContext("2d");
      if (!tctx) return;
      tctx.clearRect(0, 0, 72, 72);

      var cx = 36;
      var cy = 36;
      var len = 24;
      var cosP = Math.cos(camera.pitch);
      var sinP = Math.sin(camera.pitch);
      var sinY = Math.sin(camera.yaw);
      var cosY = Math.cos(camera.yaw);

      var axes = [
        { label: "X", dir: [cosY, -sinY * sinP], color: "rgb(235, 75, 75)" },
        { label: "Y", dir: [0, -cosP], color: "rgb(45, 200, 65)" },
        { label: "Z", dir: [-sinY, -cosY * sinP], color: "rgb(65, 145, 255)" }
      ];

      axes.forEach(function (ax) {
        var ex = cx + ax.dir[0] * len;
        var ey = cy + ax.dir[1] * len;
        tctx.beginPath();
        tctx.moveTo(cx, cy);
        tctx.lineTo(ex, ey);
        tctx.strokeStyle = ax.color;
        tctx.lineWidth = 2.5;
        tctx.stroke();

        tctx.fillStyle = ax.color;
        tctx.font = "bold 10px sans-serif";
        var offsetX = ax.dir[0] >= 0 ? 4 : -10;
        var offsetY = ax.dir[1] >= 0 ? 10 : -4;
        tctx.fillText(ax.label, ex + offsetX, ey + offsetY);
      });
    }

    function render() {
      if (!canvas) return;
      var w = canvas.clientWidth || 640;
      var h = canvas.clientHeight || 480;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      renderTripodGizmo();

      if (showBoundingBox && modelBounds && modelBounds.min && modelBounds.max) {
        var dx = modelBounds.max[0] - modelBounds.min[0];
        var dy = modelBounds.max[1] - modelBounds.min[1];
        var dz = modelBounds.max[2] - modelBounds.min[2];
        bboxBadge.textContent = "L: " + dx.toFixed(2) + " x W: " + dy.toFixed(2) + " x H: " + dz.toFixed(2);
        bboxBadge.classList.remove("hidden");
      } else {
        bboxBadge.classList.add("hidden");
      }

      if (showScales && modelBounds) {
        var sp = modelBounds.span || 1.0;
        var st = sp / 10;
        scaleBadge.textContent = "Grid: " + st.toFixed(st < 1 ? 2 : 1) + " | Span: " + sp.toFixed(2);
        scaleBadge.classList.remove("hidden");
      } else {
        scaleBadge.classList.add("hidden");
      }

      if (!gl) {
        var ctx2d = canvas.getContext("2d");
        if (ctx2d) {
          ctx2d.clearRect(0, 0, w, h);
          ctx2d.fillStyle = "#888";
          ctx2d.font = "14px sans-serif";
          ctx2d.textAlign = "center";
          ctx2d.fillText("WebGL not available.", w / 2, h / 2);
        }
        return;
      }

      gl.viewport(0, 0, w, h);
      gl.enable(gl.DEPTH_TEST);
      gl.clearColor(0.12, 0.14, 0.17, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      gl.useProgram(shaderProg);

      var aspect = w / Math.max(1, h);
      var proj = mat4Perspective(0.785, aspect, 0.05, 5000.0);

      var eyeX = camera.target[0] + camera.distance * Math.sin(camera.yaw) * Math.cos(camera.pitch);
      var eyeY = camera.target[1] + camera.distance * Math.sin(camera.pitch);
      var eyeZ = camera.target[2] + camera.distance * Math.cos(camera.yaw) * Math.cos(camera.pitch);
      var view = mat4LookAt([eyeX, eyeY, eyeZ], camera.target, [0, 1, 0]);

      gl.uniformMatrix4fv(shaderProg.uProj, false, proj);
      gl.uniformMatrix4fv(shaderProg.uView, false, view);
      gl.uniform3f(shaderProg.uLightDir, 0.4, 0.8, 0.6);

      // Render Reference Grid
      if (showScales) {
        var gridPoints = [];
        var gHalf = Math.max((modelBounds.span || 1.0) * 1.5, 5.0);
        var gStep = gHalf / 5;
        var gFloor = modelBounds && modelBounds.min ? (modelBounds.min[1] - modelBounds.center[1]) : 0;
        for (var coord = -gHalf; coord <= gHalf + 0.001; coord += gStep) {
          gridPoints.push(coord, gFloor, -gHalf, coord, gFloor, gHalf);
          gridPoints.push(-gHalf, gFloor, coord, gHalf, gFloor, coord);
        }
        drawLines(new Float32Array(gridPoints), [0.38, 0.44, 0.52, 0.4]);
      }

      // Render 3D Model Mesh or Wireframe
      if (modelMeshBuffer) {
        if (wireframeMode) {
          gl.uniform1i(shaderProg.uUnlit, 1);
          gl.uniform4f(shaderProg.uColor, 0.9, 0.55, 0.2, 1.0);
          gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, modelMeshBuffer.wireframePositions, gl.DYNAMIC_DRAW);
          gl.enableVertexAttribArray(shaderProg.aPos);
          gl.vertexAttribPointer(shaderProg.aPos, 3, gl.FLOAT, false, 0, 0);
          gl.disableVertexAttribArray(shaderProg.aNorm);
          gl.drawArrays(gl.LINES, 0, modelMeshBuffer.wireframeCount);
        } else {
          gl.uniform1i(shaderProg.uUnlit, 0);
          gl.uniform4f(shaderProg.uColor, 0.65, 0.68, 0.76, 1.0);

          gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, modelMeshBuffer.positions, gl.DYNAMIC_DRAW);
          gl.enableVertexAttribArray(shaderProg.aPos);
          gl.vertexAttribPointer(shaderProg.aPos, 3, gl.FLOAT, false, 0, 0);

          gl.bindBuffer(gl.ARRAY_BUFFER, normBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, modelMeshBuffer.normals, gl.DYNAMIC_DRAW);
          gl.enableVertexAttribArray(shaderProg.aNorm);
          gl.vertexAttribPointer(shaderProg.aNorm, 3, gl.FLOAT, false, 0, 0);

          gl.drawArrays(gl.TRIANGLES, 0, modelMeshBuffer.vertexCount);
        }
      }

      // Render 3D Coordinate Axes
      if (showAxes) {
        var axisLen = Math.max((modelBounds.span || 1.0) * 0.5, 1.0);
        var xAxis = new Float32Array([
          0, 0, 0, axisLen, 0, 0,
          axisLen * 0.9, axisLen * 0.03, 0, axisLen, 0, 0,
          axisLen * 0.9, -axisLen * 0.03, 0, axisLen, 0, 0,
          -axisLen * 0.35, 0, 0, 0, 0, 0
        ]);
        drawLines(xAxis, [0.92, 0.22, 0.22, 1.0]);

        var yAxis = new Float32Array([
          0, 0, 0, 0, axisLen, 0,
          axisLen * 0.03, axisLen * 0.9, 0, 0, axisLen, 0,
          -axisLen * 0.03, axisLen * 0.9, 0, 0, axisLen, 0,
          0, -axisLen * 0.35, 0, 0, 0, 0
        ]);
        drawLines(yAxis, [0.2, 0.85, 0.25, 1.0]);

        var zAxis = new Float32Array([
          0, 0, 0, 0, 0, axisLen,
          0, axisLen * 0.03, axisLen * 0.9, 0, 0, axisLen,
          0, -axisLen * 0.03, axisLen * 0.9, 0, 0, axisLen,
          0, 0, -axisLen * 0.35, 0, 0, 0
        ]);
        drawLines(zAxis, [0.25, 0.55, 0.95, 1.0]);
      }

      // Render Bounding Box Wireframe
      if (showBoundingBox && modelBounds && modelBounds.min && modelBounds.max) {
        var bMin = modelBounds.min;
        var bMax = modelBounds.max;
        var mcx = modelBounds.center[0];
        var mcy = modelBounds.center[1];
        var mcz = modelBounds.center[2];
        var x0 = bMin[0] - mcx, x1 = bMax[0] - mcx;
        var y0 = bMin[1] - mcy, y1 = bMax[1] - mcy;
        var z0 = bMin[2] - mcz, z1 = bMax[2] - mcz;

        var bboxEdges = new Float32Array([
          x0, y0, z0, x1, y0, z0,
          x1, y0, z0, x1, y1, z0,
          x1, y1, z0, x0, y1, z0,
          x0, y1, z0, x0, y0, z0,
          x0, y0, z1, x1, y0, z1,
          x1, y0, z1, x1, y1, z1,
          x1, y1, z1, x0, y1, z1,
          x0, y1, z1, x0, y0, z1,
          x0, y0, z0, x0, y0, z1,
          x1, y0, z0, x1, y0, z1,
          x1, y1, z0, x1, y1, z1,
          x0, y1, z0, x0, y1, z1
        ]);
        drawLines(bboxEdges, [0.65, 0.45, 0.85, 0.9]);
      }

      // Render Cutting Planes
      cuttingPlanes.forEach(function (plane, pIdx) {
        var norm = plane.normal;
        var orig = plane.origin;
        var mcx = modelBounds.center[0];
        var mcy = modelBounds.center[1];
        var mcz = modelBounds.center[2];
        var ox = orig[0] - mcx;
        var oy = orig[1] - mcy;
        var oz = orig[2] - mcz;

        var pSpan = Math.max((modelBounds.span || 1.0) * 0.8, 1.0);
        var uVec = [0, 1, 0];
        if (Math.abs(norm[1]) > 0.9) uVec = [1, 0, 0];
        var vVec = [
          norm[1] * uVec[2] - norm[2] * uVec[1],
          norm[2] * uVec[0] - norm[0] * uVec[2],
          norm[0] * uVec[1] - norm[1] * uVec[0]
        ];
        var vLen = Math.hypot(vVec[0], vVec[1], vVec[2]) || 1.0;
        vVec[0] /= vLen; vVec[1] /= vLen; vVec[2] /= vLen;

        var uFinal = [
          vVec[1] * norm[2] - vVec[2] * norm[1],
          vVec[2] * norm[0] - vVec[0] * norm[2],
          vVec[0] * norm[1] - vVec[1] * norm[0]
        ];

        var c0 = [ox - uFinal[0] * pSpan - vVec[0] * pSpan, oy - uFinal[1] * pSpan - vVec[1] * pSpan, oz - uFinal[2] * pSpan - vVec[2] * pSpan];
        var c1 = [ox + uFinal[0] * pSpan - vVec[0] * pSpan, oy + uFinal[1] * pSpan - vVec[1] * pSpan, oz + uFinal[2] * pSpan - vVec[2] * pSpan];
        var c2 = [ox + uFinal[0] * pSpan + vVec[0] * pSpan, oy + uFinal[1] * pSpan + vVec[1] * pSpan, oz + uFinal[2] * pSpan + vVec[2] * pSpan];
        var c3 = [ox - uFinal[0] * pSpan + vVec[0] * pSpan, oy - uFinal[1] * pSpan + vVec[1] * pSpan, oz - uFinal[2] * pSpan + vVec[2] * pSpan];

        var pColor = (pIdx === selectedPlaneIdx) ? [0.95, 0.45, 0.15, 0.9] : [0.35, 0.65, 0.95, 0.6];
        var pEdges = new Float32Array([
          c0[0], c0[1], c0[2], c1[0], c1[1], c1[2],
          c1[0], c1[1], c1[2], c2[0], c2[1], c2[2],
          c2[0], c2[1], c2[2], c3[0], c3[1], c3[2],
          c3[0], c3[1], c3[2], c0[0], c0[1], c0[2]
        ]);
        drawLines(pEdges, pColor);
      });
    }

    // Interactive mouse drag controls
    var isDragging = false;
    var dragButton = 0;
    var lastMouseX = 0;
    var lastMouseY = 0;

    canvas.addEventListener("mousedown", function (e) {
      if (e.button !== 0 && e.button !== 2) return;
      isDragging = true;
      dragButton = e.button;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      canvas.style.setProperty("cursor", "grabbing");
    });

    window.addEventListener("mousemove", function (e) {
      if (!isDragging) return;
      var dx = e.clientX - lastMouseX;
      var dy = e.clientY - lastMouseY;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      if (dragButton === 0 && !e.shiftKey) {
        camera.yaw += dx * 0.01;
        camera.pitch = Math.max(-1.52, Math.min(1.52, camera.pitch + dy * 0.01));
      } else {
        var panSpeed = camera.distance * 0.002;
        var cY = Math.cos(camera.yaw);
        var sY = Math.sin(camera.yaw);
        camera.target[0] -= (dx * cY) * panSpeed;
        camera.target[1] += dy * panSpeed;
        camera.target[2] += (dx * sY) * panSpeed;
      }
      render();
    });

    window.addEventListener("mouseup", function () {
      if (isDragging) {
        isDragging = false;
        canvas.style.setProperty("cursor", "grab");
      }
    });

    canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      var zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
      camera.distance = Math.max(0.1, Math.min(2000.0, camera.distance * zoomFactor));
      render();
    }, { passive: false });

    canvas.addEventListener("click", function (e) {
      if (pickMode && sharedViewportInstance.onPickPoint) {
        var rect = canvas.getBoundingClientRect();
        var clickX = e.clientX - rect.left;
        var clickY = e.clientY - rect.top;
        var nx = (clickX / rect.width) * 2 - 1;
        var ny = -(clickY / rect.height) * 2 + 1;
        var pickedPt = [
          modelBounds.center[0] + nx * modelBounds.span * 0.5,
          modelBounds.center[1] + ny * modelBounds.span * 0.5,
          modelBounds.center[2]
        ];
        sharedViewportInstance.onPickPoint(pickMode, pickedPt);
        pickMode = null;
        render();
      }
    });

    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        render();
      });
      ro.observe(container);
    }

    sharedViewportInstance = {
      el: container,
      canvas: canvas,
      render: render,
      setPickMode: function (mode) { pickMode = mode; },
      onPickPoint: null
    };

    setTimeout(render, 50);
    return sharedViewportInstance;
  }

  // Model Loading helper
  function loadModelGeometry(path, onLoaded) {
    currentModelPath = path;
    window.FOSS.api("model3d_load", { file_path: path }).then(function (res) {
      if (res && res.info) {
        currentModelInfo = res.info;
        if (res.vertices && res.faces) {
          try {
            currentVertices = base64ToFloat32Array(res.vertices);
            currentFaces = base64ToUint32Array(res.faces);
            modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
            var vp = getSharedViewport();
            vp.render();
          } catch (err) {
            // Ignore buffer errors
          }
        }
        if (onLoaded) onLoaded(res);
      }
    }).catch(function (err) {
      window.FOSS.toast.show({ message: err.message || "Failed to load 3D model.", type: "error" });
    });
  }

  // Top Model Toolbar
  function createModelToolbar(onModelChange) {
    var toolbar = window.FOSS.dom.el("div", {
      className: "model3d-topbar",
      "data-testid": "model3d-topbar"
    });

    var fileBadge = window.FOSS.dom.el("span", {
      className: "font-mono text-xs text-muted",
      "data-testid": "model3d-loaded-file",
      "data-truncate-ok": "true",
      title: currentModelPath ? currentModelPath.split(/[/\\]/).pop() : "No model loaded",
      text: currentModelPath ? currentModelPath.split(/[/\\]/).pop() : "No model loaded"
    });

    var chipsContainer = window.FOSS.dom.el("div", {
      className: "row gap-1 items-center",
      "data-testid": "model3d-chips"
    });

    function updateChips() {
      chipsContainer.innerHTML = "";
      if (currentModelInfo) {
        var vCount = currentModelInfo.vertex_count || 0;
        var fCount = currentModelInfo.triangle_count || 0;
        var wt = currentModelInfo.watertight ? "Watertight" : "Non-Manifold";
        chipsContainer.appendChild(window.FOSS.dom.el("span", { className: "badge text-xs", text: vCount + " Vertices" }));
        chipsContainer.appendChild(window.FOSS.dom.el("span", { className: "badge text-xs", text: fCount + " Faces" }));
        chipsContainer.appendChild(window.FOSS.dom.el("span", { className: "badge " + (currentModelInfo.watertight ? "success" : "neutral") + " text-xs", text: wt }));
      }
      var fName = currentModelPath ? currentModelPath.split(/[/\\]/).pop() : "No model loaded";
      fileBadge.textContent = fName;
      fileBadge.title = fName;
    }

    updateChips();

    var openBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "model3d-open-btn",
      text: "Open 3D Model",
      onClick: function () {
        window.FOSS.api("select_files", {
          title: "Open 3D Model",
          file_types: ["stl", "obj", "ply", "off", "glb", "gltf", "3mf", "step", "stp", "iges", "igs"]
        }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            loadModelGeometry(res.paths[0], function () {
              updateChips();
              if (onModelChange) onModelChange();
            });
          }
        });
      }
    }, [window.FOSS.icons.el("folder", 14), window.FOSS.dom.el("span", { text: "Open 3D Model" })]);

    var centerOriginBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-center-origin-btn",
      text: "Center Origin",
      onClick: function () {
        if (!currentModelPath) return;
        window.FOSS.api("select_save_path", { title: "Save Centered Model", default_name: "centered.stl" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("model3d_center_origin", { file_path: currentModelPath, output_path: outP }).then(function (res) {
            if (res && res.output_path) {
              window.FOSS.toast.show({ message: "Centered mesh saved to " + res.output_path, type: "success" });
              loadModelGeometry(res.output_path, function () {
                updateChips();
                if (onModelChange) onModelChange();
              });
            }
          });
        });
      }
    });

    var repairBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-repair-btn",
      text: "Repair Mesh",
      onClick: function () {
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
    });

    var leftGroup = window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
      openBtn,
      fileBadge,
      chipsContainer
    ]);

    var rightGroup = window.FOSS.dom.el("div", { className: "row gap-1 items-center flex-wrap" }, [
      centerOriginBtn,
      repairBtn
    ]);

    toolbar.appendChild(leftGroup);
    toolbar.appendChild(rightGroup);
    return { el: toolbar, update: updateChips };
  }

  // Tab 1: Inspector & Tools
  function renderUnifiedInspector(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var viewport = getSharedViewport();

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "model3d-inspector-status",
      text: "Ready"
    });

    var topbarObj = createModelToolbar(function () {
      updateInspectorData();
    });

    // Inspector Cards
    var infoCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "model3d-info-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Model Geometry & Topology" }),
      window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-sm text-xs", "data-testid": "model3d-info-grid" }, [
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Format: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-format", text: currentModelInfo ? currentModelInfo.format || "Mesh" : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Watertight: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-watertight", text: currentModelInfo ? (currentModelInfo.watertight ? "Yes" : "No") : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Vertices: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-vertex-count", text: currentModelInfo ? String(currentModelInfo.vertex_count || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Faces: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-face-count", text: currentModelInfo ? String(currentModelInfo.triangle_count || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Volume: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-volume", text: currentModelInfo ? String(currentModelInfo.volume ? currentModelInfo.volume.toFixed(2) : "0.00") : "0.00" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Surface Area: " }), window.FOSS.dom.el("span", { text: currentModelInfo ? String(currentModelInfo.surface_area ? currentModelInfo.surface_area.toFixed(2) : "0.00") : "0.00" })]),
        window.FOSS.dom.el("div", { className: "col-span-2" }, [
          window.FOSS.dom.el("span", { className: "text-muted", text: "Dimensions (L x W x H): " }),
          window.FOSS.dom.el("span", {
            "data-testid": "model3d-bbox-lwh",
            className: "font-mono font-semibold",
            text: modelBounds && modelBounds.min ? (modelBounds.max[0] - modelBounds.min[0]).toFixed(2) + " x " + (modelBounds.max[1] - modelBounds.min[1]).toFixed(2) + " x " + (modelBounds.max[2] - modelBounds.min[2]).toFixed(2) : "--"
          })
        ])
      ])
    ]);

    function updateInspectorData() {
      var stats = currentModelInfo || {};
      var fmtEl = panel.querySelector("[data-testid='model3d-format']");
      if (fmtEl) fmtEl.textContent = stats.format || stats.backend || "Mesh";
      var wtEl = panel.querySelector("[data-testid='model3d-watertight']");
      if (wtEl) wtEl.textContent = stats.watertight ? "Yes" : "No";
      var vEl = panel.querySelector("[data-testid='model3d-vertex-count']");
      if (vEl) vEl.textContent = String(stats.vertex_count || 0);
      var fEl = panel.querySelector("[data-testid='model3d-face-count']");
      if (fEl) fEl.textContent = String(stats.triangle_count || 0);
      var volEl = panel.querySelector("[data-testid='model3d-volume']");
      if (volEl) volEl.textContent = String(stats.volume ? stats.volume.toFixed(2) : "0.00");
      var lwhEl = panel.querySelector("[data-testid='model3d-bbox-lwh']");
      if (lwhEl && modelBounds && modelBounds.min) {
        var dx = modelBounds.max[0] - modelBounds.min[0];
        var dy = modelBounds.max[1] - modelBounds.min[1];
        var dz = modelBounds.max[2] - modelBounds.min[2];
        lwhEl.textContent = dx.toFixed(2) + " x " + dy.toFixed(2) + " x " + dz.toFixed(2);
      }
      if (typeof updateDimReadouts === "function") {
        updateDimReadouts();
      }
    }

    // Scale Model Card
    var factorInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-factor",
      "aria-label": "Scale Factor",
      title: "Scale Factor (e.g. 2.0 = double size, 0.5 = half size)",
      style: "width: 5rem;"
    });

    var scaleXInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-x",
      "aria-label": "Scale X",
      title: "Scale X Factor",
      style: "min-width: 0; width: 100%;"
    });
    var dimXReadout = window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono mt-1", "data-testid": "model3d-dim-x", text: "X: --" });

    var scaleYInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-y",
      "aria-label": "Scale Y",
      title: "Scale Y Factor",
      style: "min-width: 0; width: 100%;"
    });
    var dimYReadout = window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono mt-1", "data-testid": "model3d-dim-y", text: "Y: --" });

    var scaleZInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.1",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-z",
      "aria-label": "Scale Z",
      title: "Scale Z Factor",
      style: "min-width: 0; width: 100%;"
    });
    var dimZReadout = window.FOSS.dom.el("div", { className: "text-xs text-muted font-mono mt-1", "data-testid": "model3d-dim-z", text: "Z: --" });

    var uniformCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "model3d-uniform-scale-check"
    });

    function updateDimReadouts() {
      if (!dimXReadout) return;
      if (!modelBounds || !modelBounds.min) {
        dimXReadout.textContent = "X: --";
        dimYReadout.textContent = "Y: --";
        dimZReadout.textContent = "Z: --";
        return;
      }
      var dx = modelBounds.max[0] - modelBounds.min[0];
      var dy = modelBounds.max[1] - modelBounds.min[1];
      var dz = modelBounds.max[2] - modelBounds.min[2];

      var fx = parseFloat(scaleXInput.value) || 1.0;
      var fy = parseFloat(scaleYInput.value) || 1.0;
      var fz = parseFloat(scaleZInput.value) || 1.0;

      dimXReadout.textContent = "X: " + (dx * fx).toFixed(2);
      dimYReadout.textContent = "Y: " + (dy * fy).toFixed(2);
      dimZReadout.textContent = "Z: " + (dz * fz).toFixed(2);
    }

    factorInput.addEventListener("input", function () {
      if (uniformCheck.checked) {
        scaleXInput.value = factorInput.value;
        scaleYInput.value = factorInput.value;
        scaleZInput.value = factorInput.value;
      }
      updateDimReadouts();
    });

    scaleXInput.addEventListener("input", updateDimReadouts);
    scaleYInput.addEventListener("input", updateDimReadouts);
    scaleZInput.addEventListener("input", updateDimReadouts);

    uniformCheck.addEventListener("change", function () {
      if (uniformCheck.checked) {
        scaleXInput.value = factorInput.value;
        scaleYInput.value = factorInput.value;
        scaleZInput.value = factorInput.value;
      }
      updateDimReadouts();
    });

    var scaleResultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "model3d-scale-result",
      style: "min-width: 0; max-width: 100%; overflow-x: hidden;"
    });

    var applyScaleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "model3d-apply-scale-btn",
      text: "Apply Scale",
      onClick: function () {
        if (!currentModelPath) return;
        var factor = parseFloat(factorInput.value || "1.0");
        var fx = uniformCheck.checked ? factor : parseFloat(scaleXInput.value || factorInput.value || "1.0");
        var fy = uniformCheck.checked ? factor : parseFloat(scaleYInput.value || factorInput.value || "1.0");
        var fz = uniformCheck.checked ? factor : parseFloat(scaleZInput.value || factorInput.value || "1.0");
        window.FOSS.api("select_save_path", { title: "Save Scaled Model", default_name: "scaled.stl" }).then(function (saveRes) {
          var outP = (saveRes && (saveRes.path || (saveRes.paths && saveRes.paths[0]))) || "";
          if (!outP) return;
          window.FOSS.api("model3d_scale", {
            file_path: currentModelPath,
            factor: factor,
            factor_x: fx,
            factor_y: fy,
            factor_z: fz,
            output_path: outP
          }).then(function (res) {
            if (res && res.output_path) {
              scaleResultHost.innerHTML = "";
              scaleResultHost.appendChild(window.FOSS.components.resultCard({
                title: "Model Scaled",
                outputPath: res.output_path
              }));
              scaleResultHost.classList.remove("hidden");
            }
          });
        });
      }
    });

    var inchToMmBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      text: "In -> Mm (x25.4)",
      onClick: function () {
        factorInput.value = "25.4";
        scaleXInput.value = "25.4";
        scaleYInput.value = "25.4";
        scaleZInput.value = "25.4";
        updateDimReadouts();
      }
    });

    var mmToInchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      text: "Mm -> In (/25.4)",
      onClick: function () {
        factorInput.value = "0.03937";
        scaleXInput.value = "0.03937";
        scaleYInput.value = "0.03937";
        scaleZInput.value = "0.03937";
        updateDimReadouts();
      }
    });

    var scaleCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2",
      "data-testid": "model3d-scale-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Scale Model Dimensions" }),
      window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
        window.FOSS.components.field("Uniform Scale", factorInput),
        applyScaleBtn
      ]),
      window.FOSS.dom.el("label", { className: "row gap-2 items-center text-xs" }, [
        uniformCheck,
        window.FOSS.dom.el("span", { text: "Uniform scale across axes" })
      ]),
      window.FOSS.dom.el("div", { className: "grid grid-cols-3 gap-1", style: "width: 100%;" }, [
        window.FOSS.components.field("Scale X", window.FOSS.dom.el("div", {}, [scaleXInput, dimXReadout])),
        window.FOSS.components.field("Scale Y", window.FOSS.dom.el("div", {}, [scaleYInput, dimYReadout])),
        window.FOSS.components.field("Scale Z", window.FOSS.dom.el("div", {}, [scaleZInput, dimZReadout]))
      ]),
      window.FOSS.dom.el("div", { className: "row gap-1 items-center flex-wrap" }, [
        inchToMmBtn,
        mmToInchBtn
      ]),
      scaleResultHost
    ]);

    // Measurement Card
    var p1x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A X", title: "Point A X", value: "0", style: "min-width: 0; width: 100%;" });
    var p1y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Y", title: "Point A Y", value: "0", style: "min-width: 0; width: 100%;" });
    var p1z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Z", title: "Point A Z", value: "0", style: "min-width: 0; width: 100%;" });

    var p2x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B X", title: "Point B X", value: "10", style: "min-width: 0; width: 100%;" });
    var p2y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Y", title: "Point B Y", value: "10", style: "min-width: 0; width: 100%;" });
    var p2z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Z", title: "Point B Z", value: "10", style: "min-width: 0; width: 100%;" });

    var pickPointABtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-pick-a-btn",
      text: "Pick Point A",
      onClick: function () {
        viewport.setPickMode("point_a");
        window.FOSS.toast.show({ message: "Click on 3D model to select Point A.", type: "info" });
      }
    });

    var pickPointBBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-pick-b-btn",
      text: "Pick Point B",
      onClick: function () {
        viewport.setPickMode("point_b");
        window.FOSS.toast.show({ message: "Click on 3D model to select Point B.", type: "info" });
      }
    });

    viewport.onPickPoint = function (mode, pt) {
      if (mode === "point_a") {
        p1x.value = pt[0].toFixed(2);
        p1y.value = pt[1].toFixed(2);
        p1z.value = pt[2].toFixed(2);
      } else if (mode === "point_b") {
        p2x.value = pt[0].toFixed(2);
        p2y.value = pt[1].toFixed(2);
        p2z.value = pt[2].toFixed(2);
      }
    };

    var distanceDisplay = window.FOSS.dom.el("div", {
      className: "card card-compact text-center",
      "data-testid": "model3d-distance-display"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Distance" }),
      window.FOSS.dom.el("div", { className: "text-lg font-bold font-mono", "data-testid": "model3d-distance-value", text: "--" })
    ]);

    var calcDistanceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "model3d-measure-btn",
      text: "Calculate Distance",
      onClick: function () {
        var ptA = [parseFloat(p1x.value || "0"), parseFloat(p1y.value || "0"), parseFloat(p1z.value || "0")];
        var ptB = [parseFloat(p2x.value || "0"), parseFloat(p2y.value || "0"), parseFloat(p2z.value || "0")];
        window.FOSS.api("model3d_measure", { p1: ptA, p2: ptB }).then(function (res) {
          if (res && res.distance !== undefined) {
            var valEl = distanceDisplay.querySelector("[data-testid='model3d-distance-value']");
            if (valEl) valEl.textContent = String(res.distance) + " units";
          }
        });
      }
    });

    var measureCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "model3d-measure-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Point-to-Point Distance" }),
      window.FOSS.dom.el("div", { className: "row justify-between items-center" }, [
        window.FOSS.dom.el("span", { className: "text-xs font-semibold", text: "Point A" }),
        pickPointABtn
      ]),
      window.FOSS.dom.el("div", { className: "grid grid-cols-3 gap-1" }, [p1x, p1y, p1z]),
      window.FOSS.dom.el("div", { className: "row justify-between items-center" }, [
        window.FOSS.dom.el("span", { className: "text-xs font-semibold", text: "Point B" }),
        pickPointBBtn
      ]),
      window.FOSS.dom.el("div", { className: "grid grid-cols-3 gap-1" }, [p2x, p2y, p2z]),
      calcDistanceBtn,
      distanceDisplay
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "model3d-sidebar-pane stack scroll-y",
      "data-testid": "model3d-sidebar"
    }, [
      infoCard,
      scaleCard,
      measureCard
    ]);

    var divider = window.FOSS.components.splitDivider({ vertical: true });
    divider.addEventListener("mousedown", function () {
      if (viewport && viewport.canvas) {
        viewport.canvas.style.setProperty("pointer-events", "none");
        function onUp() {
          if (viewport && viewport.canvas) {
            viewport.canvas.style.removeProperty("pointer-events");
          }
          window.removeEventListener("mouseup", onUp);
        }
        window.addEventListener("mouseup", onUp);
      }
    });

    var split = window.FOSS.dom.el("div", {
      className: "split resizable split-main-first model3d-workbench",
      "data-testid": "model3d-workbench"
    }, [
      viewport.el,
      divider,
      sidebar
    ]);

    panel.appendChild(topbarObj.el);
    panel.appendChild(statusBar);
    panel.appendChild(split);

    viewport.render();
  }

  // Tab 2: Cut Plane
  function renderCut(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var viewport = getSharedViewport();

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "model3d-cut-status",
      text: "Ready"
    });

    var topbarObj = createModelToolbar();

    // Plane Origin & Normal Inputs
    var origX = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin X", title: "Origin X", value: "0", style: "min-width: 0; width: 100%;" });
    var origY = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin Y", title: "Origin Y", value: "0", style: "min-width: 0; width: 100%;" });
    var origZ = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Origin Z", title: "Origin Z", value: "0", style: "min-width: 0; width: 100%;" });

    var normX = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal X", title: "Normal X", value: "0", style: "min-width: 0; width: 100%;" });
    var normY = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal Y", title: "Normal Y", value: "0", style: "min-width: 0; width: 100%;" });
    var normZ = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Normal Z", title: "Normal Z", value: "1", style: "min-width: 0; width: 100%;" });

    function syncInputsWithCurrentPlane() {
      var p = cuttingPlanes[selectedPlaneIdx] || { origin: [0, 0, 0], normal: [0, 0, 1] };
      origX.value = String(p.origin[0]);
      origY.value = String(p.origin[1]);
      origZ.value = String(p.origin[2]);
      normX.value = String(p.normal[0]);
      normY.value = String(p.normal[1]);
      normZ.value = String(p.normal[2]);
    }

    function updateCurrentPlane() {
      if (!cuttingPlanes[selectedPlaneIdx]) return;
      cuttingPlanes[selectedPlaneIdx].origin = [
        parseFloat(origX.value || "0"),
        parseFloat(origY.value || "0"),
        parseFloat(origZ.value || "0")
      ];
      cuttingPlanes[selectedPlaneIdx].normal = [
        parseFloat(normX.value || "0"),
        parseFloat(normY.value || "0"),
        parseFloat(normZ.value || "1")
      ];
      viewport.render();
    }

    [origX, origY, origZ, normX, normY, normZ].forEach(function (inp) {
      inp.addEventListener("input", updateCurrentPlane);
    });

    syncInputsWithCurrentPlane();

    var pickOriginBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      text: "Pick Origin",
      onClick: function () {
        viewport.setPickMode("plane_origin");
        window.FOSS.toast.show({ message: "Click on 3D model to place plane origin.", type: "info" });
      }
    });

    viewport.onPickPoint = function (mode, pt) {
      if (mode === "plane_origin") {
        origX.value = pt[0].toFixed(2);
        origY.value = pt[1].toFixed(2);
        origZ.value = pt[2].toFixed(2);
        updateCurrentPlane();
      }
    };

    var viewDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      text: "From View Direction",
      onClick: function () {
        var cosP = Math.cos(camera.pitch);
        var sinP = Math.sin(camera.pitch);
        var sinY = Math.sin(camera.yaw);
        var cosY = Math.cos(camera.yaw);
        normX.value = (cosP * sinY).toFixed(3);
        normY.value = sinP.toFixed(3);
        normZ.value = (cosP * cosY).toFixed(3);
        updateCurrentPlane();
      }
    });

    var originCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "model3d-origin-card"
    }, [
      window.FOSS.dom.el("div", { className: "row justify-between items-center" }, [
        window.FOSS.dom.el("span", { className: "card-title text-sm font-semibold", text: "Plane Origin" }),
        pickOriginBtn
      ]),
      window.FOSS.dom.el("div", { className: "grid grid-cols-3 gap-1" }, [origX, origY, origZ])
    ]);

    var normalCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      "data-testid": "model3d-normal-card"
    }, [
      window.FOSS.dom.el("div", { className: "row justify-between items-center" }, [
        window.FOSS.dom.el("span", { className: "card-title text-sm font-semibold", text: "Plane Normal" }),
        viewDirBtn
      ]),
      window.FOSS.dom.el("div", { className: "grid grid-cols-3 gap-1" }, [normX, normY, normZ])
    ]);

    var solidCapCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "model3d-cap-check",
      "aria-label": "Cap Cut Faces (Watertight Solid)",
      title: "Cap Cut Faces (Watertight Solid)"
    });

    var solidCapLabel = window.FOSS.dom.el("label", { className: "row items-center gap-2 text-xs" }, [
      solidCapCheck,
      window.FOSS.dom.el("span", { text: "Cap Cut Cross-Sections (Watertight Solid)" })
    ]);

    var resultHost = window.FOSS.dom.el("div", {
      className: "hidden",
      "data-testid": "model3d-cut-result",
      style: "min-width: 0; max-width: 100%; overflow-x: hidden;"
    });

    var cutPiecesListEl = window.FOSS.dom.el("div", {
      className: "flex-col gap-1",
      style: "max-height: 10rem; overflow-y: auto;"
    });

    var cutPiecesCard = window.FOSS.dom.el("div", {
      className: "card card-compact hidden",
      "data-testid": "model3d-cut-pieces-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Cut Pieces" }),
      cutPiecesListEl,
      window.FOSS.dom.el("div", { className: "row gap-1 items-center flex-wrap" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "model3d-export-piece-btn",
          text: "Export Piece",
          onClick: function () {
            if (selectedPieceIdx < 0 || !cutPieces[selectedPieceIdx]) {
              window.FOSS.toast.show({ message: "Select a cut piece first.", type: "info" });
              return;
            }
            window.FOSS.api("select_save_path", {
              title: "Save Cut Piece",
              default_name: "piece_" + (selectedPieceIdx + 1) + ".stl"
            }).then(function (saveRes) {
              var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
              if (!outP) return;
              window.FOSS.api("model3d_export", { file_path: cutPieces[selectedPieceIdx], output_path: outP });
            });
          }
        }),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "model3d-export-all-pieces-btn",
          text: "Export All Pieces",
          onClick: function () {
            if (!cutPieces || !cutPieces.length) return;
            window.FOSS.api("select_directory", { title: "Select Destination Directory" }).then(function (dirRes) {
              var outDir = (dirRes && dirRes.paths && dirRes.paths[0]) || "";
              if (!outDir) return;
              cutPieces.forEach(function (piecePath, idx) {
                var targetPath = outDir + "/piece_" + (idx + 1) + ".stl";
                window.FOSS.api("model3d_export", { file_path: piecePath, output_path: targetPath });
              });
              window.FOSS.toast.show({ message: "Exported all pieces to " + outDir, type: "success" });
            });
          }
        }),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "model3d-recut-piece-btn",
          text: "Cut Piece Again",
          onClick: function () {
            if (selectedPieceIdx < 0 || !cutPieces[selectedPieceIdx]) return;
            loadModelGeometry(cutPieces[selectedPieceIdx]);
          }
        })
      ])
    ]);

    function updateCutPiecesUI(pieces) {
      cutPieces = pieces || [];
      cutPiecesListEl.innerHTML = "";
      if (cutPieces.length > 0) {
        cutPiecesCard.classList.remove("hidden");
        cutPieces.forEach(function (pPath, idx) {
          var row = window.FOSS.dom.el("div", {
            className: "row justify-between items-center p-1",
            style: "cursor: pointer; border-radius: var(--radius-sm); border: 1px solid var(--border); min-width: 0; max-width: 100%; overflow-x: hidden;" + (idx === selectedPieceIdx ? " background: var(--bg-raised); border-color: var(--accent);" : ""),
            "data-testid": "model3d-piece-item-" + idx,
            onClick: function () {
              selectedPieceIdx = idx;
              updateCutPiecesUI(cutPieces);
              loadModelGeometry(pPath);
            }
          }, [
            window.FOSS.dom.el("span", { className: "text-xs font-semibold", text: "Piece " + (idx + 1) }),
            window.FOSS.dom.el("span", {
              className: "text-xs text-muted truncate font-mono",
              "data-truncate-ok": "true",
              title: pPath.split(/[/\\]/).pop(),
              style: "min-width: 0; max-width: 60%;",
              text: pPath.split(/[/\\]/).pop()
            })
          ]);
          cutPiecesListEl.appendChild(row);
        });
      }
    }

    var cutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "model3d-cut-btn",
      text: "Slice Model Across Plane(s)",
      onClick: function () {
        if (!currentModelPath) {
          window.FOSS.toast.show({ message: "Please open a 3D model first.", type: "error" });
          return;
        }
        window.FOSS.api("select_directory", { title: "Select Destination Directory for Cut Pieces" }).then(function (dirRes) {
          var outDir = (dirRes && dirRes.paths && dirRes.paths[0]) || "";
          if (!outDir) return;
          statusBar.textContent = "Slicing 3D model...";
          window.FOSS.api("model3d_cut", {
            file_path: currentModelPath,
            planes: cuttingPlanes,
            output_dir: outDir,
            cap: solidCapCheck.checked
          }).then(function (res) {
            if (res && res.pieces) {
              statusBar.textContent = "Sliced into " + res.pieces.length + " piece(s).";
              resultHost.innerHTML = "";
              resultHost.appendChild(window.FOSS.components.resultCard({
                title: "Cut Completed",
                outputPath: outDir
              }));
              resultHost.classList.remove("hidden");
              updateCutPiecesUI(res.pieces);
            }
          });
        });
      }
    });

    var sidebar = window.FOSS.dom.el("div", {
      className: "model3d-sidebar-pane stack",
      "data-testid": "model3d-cut-sidebar"
    }, [
      originCard,
      normalCard,
      solidCapLabel,
      cutBtn,
      resultHost,
      cutPiecesCard
    ]);

    var dividerCut = window.FOSS.components.splitDivider({ vertical: true });
    dividerCut.addEventListener("mousedown", function () {
      if (viewport && viewport.canvas) {
        viewport.canvas.style.setProperty("pointer-events", "none");
        function onUp() {
          if (viewport && viewport.canvas) {
            viewport.canvas.style.removeProperty("pointer-events");
          }
          window.removeEventListener("mouseup", onUp);
        }
        window.addEventListener("mouseup", onUp);
      }
    });

    var split = window.FOSS.dom.el("div", {
      className: "split resizable split-main-first model3d-workbench",
      "data-testid": "model3d-workbench"
    }, [
      viewport.el,
      dividerCut,
      sidebar
    ]);

    panel.appendChild(topbarObj.el);
    panel.appendChild(statusBar);
    panel.appendChild(split);

    viewport.render();
  }

  // Tab 3: Export & Convert
  function renderExport(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var viewport = getSharedViewport();

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted",
      "data-testid": "model3d-export-status",
      text: "Ready"
    });

    var topbarObj = createModelToolbar();

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "model3d-export-format",
      "aria-label": "Target Format",
      title: "Target Format",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("option", { value: "stl", text: "STL (Mesh)" }),
      window.FOSS.dom.el("option", { value: "obj", text: "OBJ (Wavefront)" }),
      window.FOSS.dom.el("option", { value: "ply", text: "PLY (Polygon)" }),
      window.FOSS.dom.el("option", { value: "step", text: "STEP (CAD Solid)" }),
      window.FOSS.dom.el("option", { value: "iges", text: "IGES (CAD Surface)" })
    ]);

    var exportBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "model3d-export-btn",
      text: "Export 3D Model",
      onClick: function () {
        if (!currentModelPath) {
          window.FOSS.toast.show({ message: "Open a 3D model first.", type: "error" });
          return;
        }
        var ext = formatSelect.value;
        window.FOSS.api("select_save_path", { title: "Export 3D Model", default_name: "model." + ext }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("model3d_export", { file_path: currentModelPath, output_path: outP, format: ext }).then(function (res) {
            if (res && res.output_path) {
              window.FOSS.toast.show({ message: "Exported to " + res.output_path, type: "success" });
            }
          });
        });
      }
    });

    var exportCard = window.FOSS.dom.el("div", {
      className: "card card-compact",
      style: "width: 100%;"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold", text: "Export Format" }),
      window.FOSS.components.field("Target Format", formatSelect),
      exportBtn
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "model3d-sidebar-pane stack",
      "data-testid": "model3d-export-sidebar"
    }, [
      exportCard
    ]);

    var dividerExport = window.FOSS.components.splitDivider({ vertical: true });
    dividerExport.addEventListener("mousedown", function () {
      if (viewport && viewport.canvas) {
        viewport.canvas.style.setProperty("pointer-events", "none");
        function onUp() {
          if (viewport && viewport.canvas) {
            viewport.canvas.style.removeProperty("pointer-events");
          }
          window.removeEventListener("mouseup", onUp);
        }
        window.addEventListener("mouseup", onUp);
      }
    });

    var split = window.FOSS.dom.el("div", {
      className: "split resizable split-main-first model3d-workbench",
      "data-testid": "model3d-workbench"
    }, [
      viewport.el,
      dividerExport,
      sidebar
    ]);

    panel.appendChild(topbarObj.el);
    panel.appendChild(statusBar);
    panel.appendChild(split);

    viewport.render();
  }

  window.FOSS.router.register({
    id: "model3d",
    title: "3D Model Studio",
    navName: "3D Models",
    category: "Visuals",
    icon: "box",
    workbench: true,
    tabs: [
      { id: "inspector", label: "Inspector & Tools", render: renderUnifiedInspector },
      { id: "cut", label: "Cut Plane", render: renderCut },
      { id: "export", label: "Export & Convert", render: renderExport }
    ]
  });
})();
