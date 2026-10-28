// 3D Model Viewer & Slicer: inspect, slice with planes, scale, measure, repair, and export.
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
    var faceLimit = Math.min(faces.length / 3, 25000);
    var posArr = new Float32Array(faceLimit * 9);
    var normArr = new Float32Array(faceLimit * 9);

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

      posArr[outIdx] = x0; posArr[outIdx + 1] = y0; posArr[outIdx + 2] = z0;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;

      posArr[outIdx] = x1; posArr[outIdx + 1] = y1; posArr[outIdx + 2] = z1;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;

      posArr[outIdx] = x2; posArr[outIdx + 1] = y2; posArr[outIdx + 2] = z2;
      normArr[outIdx] = nx; normArr[outIdx + 1] = ny; normArr[outIdx + 2] = nz;
      outIdx += 3;
    }

    return {
      positions: posArr,
      normals: normArr,
      vertexCount: faceLimit * 3
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

  function create3DViewport(options) {
    options = options || {};
    var showCut = !!options.showCut;
    var showMeasure = !!options.showMeasure;

    var container = window.FOSS.dom.el("div", {
      className: "card flex-col",
      style: "width: 100%; height: 100%; min-height: 480px; position: relative; padding: 0; overflow: hidden; background: var(--bg-surface-sunken);"
    });

    var canvas = window.FOSS.dom.el("canvas", {
      width: 560,
      height: 440,
      "data-testid": "model3d-canvas",
      style: "width: 100%; height: 100%; min-height: 420px; display: block; cursor: grab;"
    });

    var tripodCanvas = window.FOSS.dom.el("canvas", {
      width: 64,
      height: 64,
      style: "position: absolute; bottom: var(--space-7); left: var(--space-2); z-index: 10; pointer-events: none; width: 64px; height: 64px;"
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
      "aria-label": "Toggle coordinate directions",
      title: "Toggle coordinate directions (X: red, Y: green, Z: blue)",
      onChange: function () {
        showAxes = axesCheckbox.checked;
        render();
      }
    });

    var scalesCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: showScales,
      "data-testid": "model3d-view-scales",
      "aria-label": "Toggle coordinate scales",
      title: "Toggle coordinate reference grid and scales",
      onChange: function () {
        showScales = scalesCheckbox.checked;
        render();
      }
    });

    var bboxCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: showBoundingBox,
      "data-testid": "model3d-view-bbox",
      "aria-label": "Toggle bounding box",
      title: "Toggle bounding box and LWH dimensions",
      onChange: function () {
        showBoundingBox = bboxCheckbox.checked;
        render();
      }
    });

    var toolbar = window.FOSS.dom.el("div", {
      className: "model3d-viewport-toolbar btn-group"
    }, [
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-reset",
        title: "Reset view",
        type: "button",
        onClick: function () {
          camera.yaw = 0.785;
          camera.pitch = 0.523;
          camera.distance = modelBounds.span * 2.2;
          camera.target = [0, 0, 0];
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Reset" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-top",
        title: "Top view",
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
        title: "Front view",
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
        title: "Side view",
        type: "button",
        onClick: function () {
          camera.yaw = 1.57;
          camera.pitch = 0;
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Side" })]),
      window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        "data-testid": "model3d-view-wireframe",
        title: "Toggle wireframe",
        type: "button",
        onClick: function () {
          wireframeMode = !wireframeMode;
          render();
        }
      }, [window.FOSS.dom.el("span", { text: "Wireframe" })]),
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
        window.FOSS.dom.el("span", { text: "Scales" })
      ]),
      window.FOSS.dom.el("label", {
        className: "row items-center gap-xs text-xs",
        style: "cursor: pointer; margin-left: var(--space-1);"
      }, [
        bboxCheckbox,
        window.FOSS.dom.el("span", { text: "Bounding Box" })
      ])
    ]);

    var emptyHint = window.FOSS.dom.el("div", {
      className: "model3d-overlay-badge",
      style: "bottom: var(--space-2); left: var(--space-2);",
      text: "Left-drag: rotate | Right-drag: pan | Wheel: zoom"
    });

    var overlayStack = window.FOSS.dom.el("div", {
      className: "model3d-overlay-stack"
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
          "  vec4 p = uView * vec4(aPos, 1.0);",
          "  vPos = p.xyz;",
          "  gl_Position = uProj * p;",
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
          "    float diff = max(abs(dot(normalize(vNorm), normalize(uLightDir))), 0.28);",
          "    vec3 col = uColor.rgb * (0.32 + 0.68 * diff);",
          "    gl_FragColor = vec4(col, uColor.a);",
          "  }",
          "}"
        ].join("\n");

        var vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, vsSource);
        gl.compileShader(vs);

        var fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, fsSource);
        gl.compileShader(fs);

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
      tctx.clearRect(0, 0, 64, 64);

      var cx = 32;
      var cy = 32;
      var len = 20;
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
        tctx.lineWidth = 2;
        tctx.stroke();

        tctx.fillStyle = ax.color;
        tctx.font = "bold 9px sans-serif";
        var offsetX = ax.dir[0] >= 0 ? 3 : -8;
        var offsetY = ax.dir[1] >= 0 ? 8 : -3;
        tctx.fillText(ax.label, ex + offsetX, ey + offsetY);
      });
    }

    function render() {
      if (!canvas) return;
      var w = canvas.clientWidth || 560;
      var h = canvas.clientHeight || 440;
      canvas.width = w;
      canvas.height = h;

      renderTripodGizmo();

      // Bounding box overlay text
      if (showBoundingBox && modelBounds && modelBounds.min && modelBounds.max) {
        var dx = modelBounds.max[0] - modelBounds.min[0];
        var dy = modelBounds.max[1] - modelBounds.min[1];
        var dz = modelBounds.max[2] - modelBounds.min[2];
        bboxBadge.textContent = "L: " + dx.toFixed(2) + " x W: " + dy.toFixed(2) + " x H: " + dz.toFixed(2);
        bboxBadge.classList.remove("hidden");
      } else {
        bboxBadge.classList.add("hidden");
      }

      // Scale indicator overlay text
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
        ctx2d.clearRect(0, 0, w, h);
        ctx2d.fillStyle = "#1e222b";
        ctx2d.fillRect(0, 0, w, h);
        if (!modelMeshBuffer) {
          ctx2d.fillStyle = "#888888";
          ctx2d.font = "14px sans-serif";
          ctx2d.fillText("Open an STL, OBJ, PLY, STEP, or IGES model to begin.", 40, h / 2);
          return;
        }
        ctx2d.strokeStyle = "#bf5700";
        ctx2d.lineWidth = 1;
        ctx2d.strokeRect(w / 4, h / 4, w / 2, h / 2);
        return;
      }

      gl.viewport(0, 0, w, h);
      gl.clearColor(0.12, 0.14, 0.18, 1.0);
      gl.enable(gl.DEPTH_TEST);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      var cosP = Math.cos(camera.pitch);
      var sinP = Math.sin(camera.pitch);
      var sinY = Math.sin(camera.yaw);
      var cosY = Math.cos(camera.yaw);

      var eye = [
        camera.target[0] + camera.distance * cosP * sinY,
        camera.target[1] + camera.distance * sinP,
        camera.target[2] + camera.distance * cosP * cosY
      ];
      var projMat = mat4Perspective(0.785, w / h, 0.1, 1000.0);
      var viewMat = mat4LookAt(eye, camera.target, [0, 1, 0]);

      gl.useProgram(shaderProg);
      gl.uniformMatrix4fv(shaderProg.uProj, false, projMat);
      gl.uniformMatrix4fv(shaderProg.uView, false, viewMat);
      gl.uniform3f(shaderProg.uLightDir, 0.6, 0.8, 1.0);

      // Render Coordinate Scales (Ground Grid)
      if (showScales) {
        var gSpan = modelBounds.span || 1.0;
        var gFloor = modelBounds.min ? (modelBounds.min[1] - modelBounds.center[1]) : -gSpan * 0.5;
        var gHalf = gSpan * 0.75;
        var gDivs = 10;
        var gStep = (gHalf * 2) / gDivs;
        var gridPoints = [];

        for (var gi = -gDivs / 2; gi <= gDivs / 2; gi++) {
          var coord = gi * gStep;
          gridPoints.push(coord, gFloor, -gHalf, coord, gFloor, gHalf);
          gridPoints.push(-gHalf, gFloor, coord, gHalf, gFloor, coord);
        }
        drawLines(new Float32Array(gridPoints), [0.38, 0.44, 0.52, 0.4]);
      }

      // Render 3D Model Mesh
      if (modelMeshBuffer) {
        gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, modelMeshBuffer.positions, gl.DYNAMIC_DRAW);
        gl.enableVertexAttribArray(shaderProg.aPos);
        gl.vertexAttribPointer(shaderProg.aPos, 3, gl.FLOAT, false, 0, 0);

        gl.bindBuffer(gl.ARRAY_BUFFER, normBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, modelMeshBuffer.normals, gl.DYNAMIC_DRAW);
        gl.enableVertexAttribArray(shaderProg.aNorm);
        gl.vertexAttribPointer(shaderProg.aNorm, 3, gl.FLOAT, false, 0, 0);

        if (wireframeMode) {
          gl.uniform1i(shaderProg.uUnlit, 1);
          gl.uniform4f(shaderProg.uColor, 0.9, 0.55, 0.2, 1.0);
          gl.drawArrays(gl.LINES, 0, modelMeshBuffer.vertexCount);
        } else {
          gl.uniform1i(shaderProg.uUnlit, 0);
          gl.uniform4f(shaderProg.uColor, 0.65, 0.68, 0.76, 1.0);
          gl.drawArrays(gl.TRIANGLES, 0, modelMeshBuffer.vertexCount);
        }
      }

      // Render Coordinate Directions (3D Axes)
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
        drawLines(zAxis, [0.25, 0.55, 1.0, 1.0]);
      }

      // Render Bounding Box Wireframe
      if (showBoundingBox && modelBounds && modelBounds.min && modelBounds.max) {
        var bMin = modelBounds.min;
        var bMax = modelBounds.max;
        var mcx = modelBounds.center[0];
        var mcy = modelBounds.center[1];
        var mcz = modelBounds.center[2];
        var bx0 = bMin[0] - mcx, bx1 = bMax[0] - mcx;
        var by0 = bMin[1] - mcy, by1 = bMax[1] - mcy;
        var bz0 = bMin[2] - mcz, bz1 = bMax[2] - mcz;

        var bboxLines = new Float32Array([
          bx0, by0, bz0, bx1, by0, bz0,
          bx1, by0, bz0, bx1, by1, bz0,
          bx1, by1, bz0, bx0, by1, bz0,
          bx0, by1, bz0, bx0, by0, bz0,

          bx0, by0, bz1, bx1, by0, bz1,
          bx1, by0, bz1, bx1, by1, bz1,
          bx1, by1, bz1, bx0, by1, bz1,
          bx0, by1, bz1, bx0, by0, bz1,

          bx0, by0, bz0, bx0, by0, bz1,
          bx1, by0, bz0, bx1, by0, bz1,
          bx1, by1, bz0, bx1, by1, bz1,
          bx0, by1, bz0, bx0, by1, bz1
        ]);
        drawLines(bboxLines, [0.95, 0.65, 0.15, 0.9]);
      }

      // Render ALL Cutting Planes (Never deletes or hides previous planes)
      if (showCut && cuttingPlanes.length > 0) {
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        for (var pi = 0; pi < cuttingPlanes.length; pi++) {
          var plane = cuttingPlanes[pi];
          var isSelected = (pi === selectedPlaneIdx);

          var ox = plane.origin[0] - modelBounds.center[0];
          var oy = plane.origin[1] - modelBounds.center[1];
          var oz = plane.origin[2] - modelBounds.center[2];

          var nx = plane.normal[0], ny = plane.normal[1], nz = plane.normal[2];
          var nlen = Math.hypot(nx, ny, nz) || 1.0;
          nx /= nlen; ny /= nlen; nz /= nlen;

          var hx = Math.abs(nz) < 0.9 ? 0.0 : 1.0;
          var hy = 0.0;
          var hz = Math.abs(nz) < 0.9 ? 1.0 : 0.0;

          var ux = hy * nz - hz * ny, uy = hz * nx - hx * nz, uz = hx * ny - hy * nx;
          var ulen = Math.hypot(ux, uy, uz) || 1.0;
          ux /= ulen; uy /= ulen; uz /= ulen;

          var vx = ny * uz - nz * uy, vy = nz * ux - nx * uz, vz = nx * uy - ny * ux;

          var r = (modelBounds.span || 1.0) * 1.35;
          var p0 = [ox - r * ux - r * vx, oy - r * uy - r * vy, oz - r * uz - r * vz];
          var p1 = [ox + r * ux - r * vx, oy + r * uy - r * vy, oz + r * uz - r * vz];
          var p2 = [ox + r * ux + r * vx, oy + r * uy + r * vy, oz + r * uz + r * vz];
          var p3 = [ox - r * ux + r * vx, oy - r * uy + r * vy, oz - r * uz + r * vz];

          var planeVerts = new Float32Array([
            p0[0], p0[1], p0[2],
            p1[0], p1[1], p1[2],
            p2[0], p2[1], p2[2],
            p0[0], p0[1], p0[2],
            p2[0], p2[1], p2[2],
            p3[0], p3[1], p3[2]
          ]);

          var planeNorms = new Float32Array([
            nx, ny, nz, nx, ny, nz, nx, ny, nz,
            nx, ny, nz, nx, ny, nz, nx, ny, nz
          ]);

          gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, planeVerts, gl.DYNAMIC_DRAW);
          gl.enableVertexAttribArray(shaderProg.aPos);
          gl.vertexAttribPointer(shaderProg.aPos, 3, gl.FLOAT, false, 0, 0);

          gl.bindBuffer(gl.ARRAY_BUFFER, normBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, planeNorms, gl.DYNAMIC_DRAW);
          gl.enableVertexAttribArray(shaderProg.aNorm);
          gl.vertexAttribPointer(shaderProg.aNorm, 3, gl.FLOAT, false, 0, 0);

          gl.uniform1i(shaderProg.uUnlit, 0);
          if (isSelected) {
            gl.uniform4f(shaderProg.uColor, 0.75, 0.34, 0.0, 0.55);
          } else {
            gl.uniform4f(shaderProg.uColor, 0.15, 0.55, 0.75, 0.38);
          }
          gl.drawArrays(gl.TRIANGLES, 0, 6);

          var borderVerts = new Float32Array([
            p0[0], p0[1], p0[2], p1[0], p1[1], p1[2],
            p1[0], p1[1], p1[2], p2[0], p2[1], p2[2],
            p2[0], p2[1], p2[2], p3[0], p3[1], p3[2],
            p3[0], p3[1], p3[2], p0[0], p0[1], p0[2],
            ox, oy, oz, ox + nx * r * 0.45, oy + ny * r * 0.45, oz + nz * r * 0.45
          ]);
          if (isSelected) {
            drawLines(borderVerts, [1.0, 0.5, 0.05, 1.0]);
          } else {
            drawLines(borderVerts, [0.25, 0.75, 0.95, 0.85]);
          }
        }

        gl.disable(gl.BLEND);
      }

      // Render Measure Points
      if (showMeasure && measurePoints.a && measurePoints.b) {
        var ax = measurePoints.a[0] - modelBounds.center[0];
        var ay = measurePoints.a[1] - modelBounds.center[1];
        var az = measurePoints.a[2] - modelBounds.center[2];
        var bx = measurePoints.b[0] - modelBounds.center[0];
        var by = measurePoints.b[1] - modelBounds.center[1];
        var bz = measurePoints.b[2] - modelBounds.center[2];

        var mLine = new Float32Array([ax, ay, az, bx, by, bz]);
        drawLines(mLine, [0.2, 0.9, 0.3, 1.0]);
      }
    }

    var isDragging = false;
    var dragButton = 0;
    var lastMouseX = 0;
    var lastMouseY = 0;

    canvas.addEventListener("mousedown", function (e) {
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
      isDragging = false;
      canvas.style.setProperty("cursor", "grab");
    });

    canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      var zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
      camera.distance = Math.max(0.1, Math.min(2000.0, camera.distance * zoomFactor));
      render();
    }, { passive: false });

    canvas.addEventListener("click", function (e) {
      if (pickMode && options.onPickPoint) {
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
        options.onPickPoint(pickMode, pickedPt);
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

    setTimeout(render, 50);

    return {
      el: container,
      canvas: canvas,
      render: render,
      setPickMode: function (mode) {
        pickMode = mode;
      }
    };
  }

  // Unified Inspector, Scale & Measure page
  function renderUnifiedInspector(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "3D Model Inspector & Studio" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "open an stl, obj, ply, step, or iges model to begin."
      }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-xs",
        text: "pick two points on the model to measure the distance between them."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-inspector-status",
      text: currentModelPath ? "Loaded: " + currentModelPath : "open an stl, obj, ply, step, or iges model to begin."
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

    var viewport = create3DViewport({
      showMeasure: true,
      onPickPoint: function (mode, pt) {
        if (mode === "point_a") {
          p1x.value = String(pt[0].toFixed(2));
          p1y.value = String(pt[1].toFixed(2));
          p1z.value = String(pt[2].toFixed(2));
        } else if (mode === "point_b") {
          p2x.value = String(pt[0].toFixed(2));
          p2y.value = String(pt[1].toFixed(2));
          p2z.value = String(pt[2].toFixed(2));
        }
        measurePoints.a = [parseFloat(p1x.value), parseFloat(p1y.value), parseFloat(p1z.value)];
        measurePoints.b = [parseFloat(p2x.value), parseFloat(p2y.value), parseFloat(p2z.value)];
        viewport.render();
      }
    });

    var infoCard = window.FOSS.dom.el("div", {
      className: "card mb-sm",
      "data-testid": "model3d-info-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Model Geometry & Topology" }),
      window.FOSS.dom.el("div", { className: "grid grid-cols-2 gap-sm text-xs", "data-testid": "model3d-info-grid" }, [
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Format: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-format", text: currentModelInfo ? currentModelInfo.format || "Mesh" : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Watertight: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-watertight", text: currentModelInfo ? (currentModelInfo.watertight ? "Yes" : "No") : "N/A" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Vertices: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-vertex-count", text: currentModelInfo ? String(currentModelInfo.vertex_count || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Faces: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-face-count", text: currentModelInfo ? String(currentModelInfo.triangle_count || 0) : "0" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Volume: " }), window.FOSS.dom.el("span", { "data-testid": "model3d-volume", text: currentModelInfo ? String(currentModelInfo.volume ? currentModelInfo.volume.toFixed(2) : "0.00") : "0.00" })]),
        window.FOSS.dom.el("div", {}, [window.FOSS.dom.el("span", { className: "text-muted", text: "Surface Area: " }), window.FOSS.dom.el("span", { text: currentModelInfo ? String(currentModelInfo.surface_area ? currentModelInfo.surface_area.toFixed(2) : "0.00") : "0.00" })]),
        window.FOSS.dom.el("div", { className: "col-span-2 mt-xs" }, [
          window.FOSS.dom.el("span", { className: "text-muted", text: "Bounding Box (L x W x H): " }),
          window.FOSS.dom.el("span", {
            "data-testid": "model3d-bbox-lwh",
            className: "font-mono font-semibold",
            text: modelBounds && modelBounds.min ? (modelBounds.max[0] - modelBounds.min[0]).toFixed(2) + " x " + (modelBounds.max[1] - modelBounds.min[1]).toFixed(2) + " x " + (modelBounds.max[2] - modelBounds.min[2]).toFixed(2) : "--"
          })
        ])
      ])
    ]);

    function updateInspectorData(stats) {
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
    }

    function loadModel(path) {
      clearError();
      currentModelPath = path;
      statusBar.textContent = "Loading 3D model geometry...";
      window.FOSS.api("model3d_load", { file_path: path }).then(function (res) {
        if (res && res.info) {
          currentModelInfo = res.info;
          statusBar.textContent = "Loaded " + path + " (" + (res.vertex_count || res.info.vertex_count || 0) + " vertices)";
          if (res.vertices && res.faces) {
            try {
              currentVertices = base64ToFloat32Array(res.vertices);
              currentFaces = base64ToUint32Array(res.faces);
              modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
              updateInspectorData(res.info);
              viewport.render();
            } catch (err) {
              // Ignore buffer conversion errors
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

    var scalePicker = window.FOSS.components.filePicker({
      testid: "model3d-scale-picker",
      accept: ".stl,.obj,.ply,.step,.stp,.iges,.igs",
      buttonText: "Open Model to Scale",
      onSelect: function (path) {
        loadModel(path);
      }
    });

    var repairBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "model3d-repair-btn",
      "aria-label": "Repair mesh",
      title: "Repair mesh",
      style: "min-height: 36px;",
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
    }, [window.FOSS.dom.el("span", { text: "Repair Mesh" })]);

    var centerOriginBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "model3d-center-origin-btn",
      "aria-label": "Center origin",
      title: "Re-center geometry origin at (0, 0, 0) and export",
      style: "min-height: 36px;",
      onClick: function () {
        if (!currentModelPath) return;
        window.FOSS.api("select_save_path", { title: "Save Centered Model", default_name: "centered.stl" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          window.FOSS.api("model3d_center_origin", { file_path: currentModelPath, output_path: outP }).then(function (res) {
            if (res && res.output_path) {
              window.FOSS.toast.show({ message: "Centered mesh saved to " + res.output_path, type: "success" });
              loadModel(res.output_path);
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Center Origin" })]);

    var controlsRow = window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-sm" }, [
      picker.el,
      repairBtn,
      centerOriginBtn
    ]);

    // Scale Section Card
    var factorInput = window.FOSS.dom.el("input", {
      type: "number",
      step: "0.01",
      value: "1.0",
      className: "input",
      "data-testid": "model3d-scale-factor",
      "aria-label": "Scale factor",
      title: "Scale factor",
      style: "width: 100px;"
    });

    var inchToMmBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-inch-to-mm",
      "aria-label": "inch -> mm",
      title: "inch -> mm",
      onClick: function () {
        factorInput.value = "25.4";
      }
    }, [window.FOSS.dom.el("span", { text: "inch -> mm" })]);

    var mmToInchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-mm-to-inch",
      "aria-label": "mm -> inch",
      title: "mm -> inch",
      onClick: function () {
        factorInput.value = "0.03937";
      }
    }, [window.FOSS.dom.el("span", { text: "mm -> inch" })]);

    var scaleResultHost = window.FOSS.dom.el("div", {
      className: "hidden mt-xs",
      "data-testid": "model3d-scale-result"
    });

    function showScaleResult(path) {
      scaleResultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "model3d-scale-result-card",
        title: "Model Scaled Successfully",
        outputPath: path
      });
      scaleResultHost.appendChild(card);
      scaleResultHost.classList.remove("hidden");
    }

    var applyScaleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "model3d-apply-scale-btn",
      "aria-label": "apply scale",
      title: "apply scale",
      style: "min-height: 34px;",
      onClick: function () {
        if (!currentModelPath) {
          showError("Open a model first to apply scaling.");
          return;
        }
        var factor = parseFloat(factorInput.value || "1.0");
        window.FOSS.api("select_save_path", { title: "Save Scaled Model", default_name: "scaled.stl" }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          statusBar.textContent = "Applying scale factor " + factor + "...";
          window.FOSS.api("model3d_scale", {
            file_path: currentModelPath,
            factor: factor,
            output_path: outP
          }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "Scaled model saved to " + res.output_path;
              showScaleResult(res.output_path);
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "apply scale" })]);

    var scaleCard = window.FOSS.dom.el("div", {
      className: "card mb-sm",
      "data-testid": "model3d-scale-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-xs", text: "Scale Model Dimensions" }),
      scalePicker.el,
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-xs mt-xs" }, [
        factorInput,
        inchToMmBtn,
        mmToInchBtn,
        applyScaleBtn
      ]),
      scaleResultHost
    ]);

    // Measure Section Card
    var p1x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A X", title: "Point A X", value: "0", style: "width: 65px;" });
    var p1y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Y", title: "Point A Y", value: "0", style: "width: 65px;" });
    var p1z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point A Z", title: "Point A Z", value: "0", style: "width: 65px;" });

    var p2x = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B X", title: "Point B X", value: "10", style: "width: 65px;" });
    var p2y = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Y", title: "Point B Y", value: "10", style: "width: 65px;" });
    var p2z = window.FOSS.dom.el("input", { type: "number", className: "input", "aria-label": "Point B Z", title: "Point B Z", value: "10", style: "width: 65px;" });

    var pickPointABtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-pick-a-btn",
      "aria-label": "pick point a on model",
      title: "pick point a on model",
      onClick: function () {
        viewport.setPickMode("point_a");
        window.FOSS.toast.show({ message: "Click in viewport to set Point A.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point a on model" })]);

    var pickPointBBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-pick-b-btn",
      "aria-label": "pick point b on model",
      title: "pick point b on model",
      onClick: function () {
        viewport.setPickMode("point_b");
        window.FOSS.toast.show({ message: "Click in viewport to set Point B.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point b on model" })]);

    var distanceDisplay = window.FOSS.dom.el("div", {
      className: "card text-center p-sm mt-xs",
      "data-testid": "model3d-distance-display"
    }, [
      window.FOSS.dom.el("div", { className: "text-xs text-muted mb-xs", text: "Measured Euclidean Distance" }),
      window.FOSS.dom.el("div", { className: "text-xl font-bold font-mono", "data-testid": "model3d-distance-value", text: "--" })
    ]);

    var calcDistanceBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "model3d-calc-distance-btn",
      "aria-label": "Calculate distance",
      title: "Calculate distance",
      style: "min-height: 34px;",
      onClick: function () {
        var ptA = [parseFloat(p1x.value || "0"), parseFloat(p1y.value || "0"), parseFloat(p1z.value || "0")];
        var ptB = [parseFloat(p2x.value || "0"), parseFloat(p2y.value || "0"), parseFloat(p2z.value || "0")];
        measurePoints.a = ptA;
        measurePoints.b = ptB;
        statusBar.textContent = "Calculating distance...";
        window.FOSS.api("model3d_measure", { p1: ptA, p2: ptB }).then(function (res) {
          if (res && res.distance !== undefined) {
            statusBar.textContent = "Measured distance: " + res.distance;
            var valEl = panel.querySelector("[data-testid='model3d-distance-value']");
            if (valEl) valEl.textContent = String(res.distance) + " units";
            viewport.render();
          }
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Calculate distance" })]);

    var measureCard = window.FOSS.dom.el("div", {
      className: "card mb-sm",
      "data-testid": "model3d-measure-card"
    }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-xs", text: "Measure Distance" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-xs" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "A:" }), p1x, p1y, p1z,
        pickPointABtn
      ]),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-xs" }, [
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "B:" }), p2x, p2y, p2z,
        pickPointBBtn
      ]),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-xs" }, [
        calcDistanceBtn
      ]),
      distanceDisplay
    ]);

    var sidebar = window.FOSS.dom.el("div", {
      className: "flex-col gap-sm",
      style: "flex: 1 1 45%; min-width: 320px;"
    }, [
      controlsRow,
      infoCard,
      scaleCard,
      measureCard
    ]);

    var layoutRow = window.FOSS.dom.el("div", {
      className: "row gap-md items-start",
      style: "display: flex; flex-wrap: wrap; width: 100%;"
    }, [
      window.FOSS.dom.el("div", { style: "flex: 1 1 50%; min-width: 360px;" }, [viewport.el]),
      sidebar
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(layoutRow);

    if (currentVertices && currentFaces && !modelMeshBuffer) {
      modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
    }
    viewport.render();
  }

  // Cut Plane Slicer
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

    function showResult(pieces) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({
        testid: "model3d-cut-result-card",
        title: "Model Cut Successfully (" + pieces.length + " pieces)",
        outputPath: pieces[0] || ""
      });
      resultHost.appendChild(card);
      resultHost.classList.remove("hidden");
    }

    var viewport = create3DViewport({
      showCut: true,
      onPickPoint: function (mode, pt) {
        if (mode === "cut_origin") {
          origX.value = String(pt[0].toFixed(2));
          origY.value = String(pt[1].toFixed(2));
          origZ.value = String(pt[2].toFixed(2));
          updateCurrentPlane();
        }
      }
    });

    function syncInputsWithCurrentPlane() {
      var p = cuttingPlanes[selectedPlaneIdx] || cuttingPlanes[0];
      origX.value = String(p.origin[0]);
      origY.value = String(p.origin[1]);
      origZ.value = String(p.origin[2]);
      normX.value = String(p.normal[0]);
      normY.value = String(p.normal[1]);
      normZ.value = String(p.normal[2]);
    }

    function updateCurrentPlane() {
      var p = cuttingPlanes[selectedPlaneIdx];
      if (!p) return;
      p.origin = [parseFloat(origX.value || "0"), parseFloat(origY.value || "0"), parseFloat(origZ.value || "0")];
      p.normal = [parseFloat(normX.value || "0"), parseFloat(normY.value || "0"), parseFloat(normZ.value || "1")];
      updatePlanesUI();
      viewport.render();
    }

    var curP = cuttingPlanes[selectedPlaneIdx] || { origin: [0, 0, 0], normal: [0, 0, 1] };
    var origX = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-origin-x",
      "aria-label": "Plane Origin X",
      title: "Plane Origin X",
      value: String(curP.origin[0]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });
    var origY = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-origin-y",
      "aria-label": "Plane Origin Y",
      title: "Plane Origin Y",
      value: String(curP.origin[1]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });
    var origZ = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-origin-z",
      "aria-label": "Plane Origin Z",
      title: "Plane Origin Z",
      value: String(curP.origin[2]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });

    var originCard = window.FOSS.dom.el("div", { className: "card mb-sm" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-xs", text: "plane origin" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center" }, [
        window.FOSS.dom.el("span", { className: "text-xs", text: "X:" }), origX,
        window.FOSS.dom.el("span", { className: "text-xs", text: "Y:" }), origY,
        window.FOSS.dom.el("span", { className: "text-xs", text: "Z:" }), origZ
      ])
    ]);

    var normX = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-normal-x",
      "aria-label": "Plane Normal X",
      title: "Plane Normal X",
      value: String(curP.normal[0]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });
    var normY = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-normal-y",
      "aria-label": "Plane Normal Y",
      title: "Plane Normal Y",
      value: String(curP.normal[1]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });
    var normZ = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "model3d-normal-z",
      "aria-label": "Plane Normal Z",
      title: "Plane Normal Z",
      value: String(curP.normal[2]),
      style: "width: 75px;",
      onInput: updateCurrentPlane
    });

    var invertBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-invert-btn",
      title: "Invert cut normal",
      type: "button",
      onClick: function () {
        normX.value = String(-parseFloat(normX.value || "0"));
        normY.value = String(-parseFloat(normY.value || "0"));
        normZ.value = String(-parseFloat(normZ.value || "1"));
        updateCurrentPlane();
      }
    }, [window.FOSS.dom.el("span", { text: "Invert Normal" })]);

    var normalCard = window.FOSS.dom.el("div", { className: "card mb-sm" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-xs", text: "plane normal" }),
      window.FOSS.dom.el("div", { className: "row gap-xs items-center mb-xs" }, [
        window.FOSS.dom.el("span", { className: "text-xs", text: "X:" }), normX,
        window.FOSS.dom.el("span", { className: "text-xs", text: "Y:" }), normY,
        window.FOSS.dom.el("span", { className: "text-xs", text: "Z:" }), normZ
      ]),
      window.FOSS.dom.el("div", { className: "row gap-xs" }, [invertBtn])
    ]);

    var pickOriginBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-pick-origin-btn",
      "aria-label": "pick point on model",
      title: "pick point on model",
      onClick: function () {
        viewport.setPickMode("cut_origin");
        window.FOSS.toast.show({ message: "Click in viewport to place cut origin.", type: "info" });
      }
    }, [window.FOSS.dom.el("span", { text: "pick point on model" })]);

    var useViewDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-use-view-dir-btn",
      "aria-label": "use current view direction",
      title: "use current view direction",
      onClick: function () {
        var cosP = Math.cos(camera.pitch);
        var sinP = Math.sin(camera.pitch);
        var sinY = Math.sin(camera.yaw);
        var cosY = Math.cos(camera.yaw);
        normX.value = String((cosP * sinY).toFixed(3));
        normY.value = String(sinP.toFixed(3));
        normZ.value = String((cosP * cosY).toFixed(3));
        updateCurrentPlane();
      }
    }, [window.FOSS.dom.el("span", { text: "use current view direction" })]);

    var solidCapCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "data-testid": "model3d-cap-check",
      "aria-label": "fill cut cross-section (solid)",
      title: "fill cut cross-section (solid)"
    });

    var solidCapLabel = window.FOSS.dom.el("label", { className: "row items-center gap-xs text-xs mb-sm" }, [
      solidCapCheck,
      window.FOSS.dom.el("span", { text: "fill cut cross-section (solid)" })
    ]);

    var planesListEl = window.FOSS.dom.el("div", {
      className: "card mb-sm",
      "data-testid": "model3d-planes-card"
    });

    var addPlaneBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-add-plane-btn",
      "aria-label": "add plane",
      title: "add plane",
      onClick: function () {
        var prevP = cuttingPlanes[cuttingPlanes.length - 1] || { origin: [0, 0, 0], normal: [0, 0, 1] };
        var nextNormal = [0, 1, 0];
        if (Math.abs(prevP.normal[1]) > 0.8) nextNormal = [1, 0, 0];
        cuttingPlanes.push({
          origin: [prevP.origin[0], prevP.origin[1], prevP.origin[2]],
          normal: nextNormal
        });
        selectedPlaneIdx = cuttingPlanes.length - 1;
        syncInputsWithCurrentPlane();
        updatePlanesUI();
        viewport.render();
      }
    }, [window.FOSS.dom.el("span", { text: "add plane" })]);

    var removePlaneBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "model3d-remove-plane-btn",
      "aria-label": "remove selected plane",
      title: "remove selected plane",
      onClick: function () {
        if (cuttingPlanes.length > 1) {
          cuttingPlanes.splice(selectedPlaneIdx, 1);
          selectedPlaneIdx = Math.max(0, selectedPlaneIdx - 1);
          syncInputsWithCurrentPlane();
          updatePlanesUI();
          viewport.render();
        }
      }
    }, [window.FOSS.dom.el("span", { text: "remove selected plane" })]);

    function updatePlanesUI() {
      planesListEl.innerHTML = "";
      var cardTitle = window.FOSS.dom.el("div", {
        className: "card-title text-sm font-semibold mb-xs",
        text: "cutting planes (add more than one to split into multiple pieces)"
      });
      planesListEl.appendChild(cardTitle);

      var actionsRow = window.FOSS.dom.el("div", { className: "row gap-xs mb-sm" }, [
        addPlaneBtn,
        removePlaneBtn
      ]);
      planesListEl.appendChild(actionsRow);

      var listContainer = window.FOSS.dom.el("div", {
        className: "flex-col gap-xs",
        style: "max-height: 160px; overflow-y: auto;"
      });

      cuttingPlanes.forEach(function (plane, idx) {
        var isSel = (idx === selectedPlaneIdx);
        var item = window.FOSS.dom.el("div", {
          className: "model3d-plane-item" + (isSel ? " active" : ""),
          "data-testid": "model3d-plane-item-" + idx,
          onClick: function () {
            selectedPlaneIdx = idx;
            syncInputsWithCurrentPlane();
            updatePlanesUI();
            viewport.render();
          }
        }, [
          window.FOSS.dom.el("span", {
            className: "text-xs",
            text: "Plane " + (idx + 1) + " (N: [" + plane.normal.map(function (n) { return Number(n).toFixed(2); }).join(", ") + "])"
          }),
          isSel ? window.FOSS.dom.el("span", { className: "badge badge-primary text-xs", text: "Active" }) : null
        ]);
        listContainer.appendChild(item);
      });

      planesListEl.appendChild(listContainer);
    }

    updatePlanesUI();

    var cutPiecesCard = window.FOSS.dom.el("div", { className: "card mb-sm" }, [
      window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-xs", text: "cut pieces (select one to highlight it in the viewport)" }),
      window.FOSS.dom.el("div", { className: "row gap-xs" }, [
        window.FOSS.dom.el("button", { className: "btn btn-secondary btn-sm", "data-testid": "model3d-export-sel-piece", "aria-label": "export selected piece", title: "export selected piece", text: "export selected piece" }),
        window.FOSS.dom.el("button", { className: "btn btn-secondary btn-sm", "data-testid": "model3d-export-all-pieces", "aria-label": "export all pieces", title: "export all pieces", text: "export all pieces" }),
        window.FOSS.dom.el("button", { className: "btn btn-secondary btn-sm", "data-testid": "model3d-cut-piece-again", "aria-label": "cut this piece again", title: "cut this piece again", text: "cut this piece again" })
      ])
    ]);

    var cutBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "model3d-cut-btn",
      "aria-label": "cut model",
      title: "cut model",
      style: "min-height: 38px; width: 100%;",
      onClick: function () {
        if (!currentModelPath) {
          showError("Please open a 3D model first.");
          return;
        }
        window.FOSS.api("select_directory", { title: "Select Output Folder for Cut Pieces" }).then(function (dirRes) {
          var outDir = (dirRes && dirRes.paths && dirRes.paths[0]) || "";
          if (!outDir) return;
          statusBar.textContent = "Slicing 3D model across plane(s)...";
          window.FOSS.api("model3d_cut", {
            file_path: currentModelPath,
            planes: cuttingPlanes,
            output_dir: outDir
          }).then(function (res) {
            if (res && res.pieces) {
              cutPieces = res.pieces;
              statusBar.textContent = "Sliced into " + res.pieces.length + " pieces.";
              showResult(res.pieces);
            }
          }).catch(function (err) {
            showError(err.message || "Cut operation failed.");
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "cut model" })]);

    var picker = window.FOSS.components.filePicker({
      testid: "model3d-cut-picker",
      accept: ".stl,.obj,.ply,.step,.stp,.iges,.igs",
      buttonText: "Open 3D Model",
      onSelect: function (path) {
        currentModelPath = path;
        statusBar.textContent = "Loading " + path;
        window.FOSS.api("model3d_load", { file_path: path }).then(function (res) {
          if (res && res.vertices && res.faces) {
            currentModelInfo = res.info;
            currentVertices = base64ToFloat32Array(res.vertices);
            currentFaces = base64ToUint32Array(res.faces);
            modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
            statusBar.textContent = "Model: " + path;
            viewport.render();
          }
        });
      }
    });

    var sidebar = window.FOSS.dom.el("div", {
      className: "flex-col gap-sm",
      style: "flex: 1 1 45%; min-width: 320px;"
    }, [
      picker.el,
      window.FOSS.dom.el("div", { className: "row gap-xs mb-sm" }, [pickOriginBtn, useViewDirBtn]),
      originCard,
      normalCard,
      solidCapLabel,
      planesListEl,
      cutBtn,
      resultHost,
      cutPiecesCard
    ]);

    var layoutRow = window.FOSS.dom.el("div", {
      className: "row gap-md items-start",
      style: "display: flex; flex-wrap: wrap; width: 100%;"
    }, [
      window.FOSS.dom.el("div", { style: "flex: 1 1 50%; min-width: 360px;" }, [viewport.el]),
      sidebar
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(layoutRow);

    if (currentVertices && currentFaces && !modelMeshBuffer) {
      modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
    }
    viewport.render();
  }

  // Export & Convert 3D Model
  function renderExport(panel, ctx) {
    panel.innerHTML = "";
    panel.setAttribute("data-testid", "tool-page-model3d");

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Export & Convert 3D Model" }),
      window.FOSS.dom.el("p", {
        className: "text-muted text-sm",
        text: "Export the active 3D model geometry to STL, OBJ, PLY, STEP, or IGES."
      })
    ]);

    var statusBar = window.FOSS.dom.el("div", {
      className: "text-xs text-muted mb-sm",
      "data-testid": "model3d-export-status",
      text: currentModelPath ? "Model: " + currentModelPath : "open an stl, obj, ply, step, or iges model to begin."
    });

    var viewport = create3DViewport();

    var formatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "model3d-export-format",
      style: "width: 140px;"
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
      title: "Export 3D Model",
      style: "min-height: 38px;",
      onClick: function () {
        if (!currentModelPath) {
          window.FOSS.toast.show({ message: "Open a model first.", type: "error" });
          return;
        }
        var ext = formatSelect.value;
        window.FOSS.api("select_save_path", { title: "Export 3D Model", default_name: "model." + ext }).then(function (saveRes) {
          var outP = (saveRes && saveRes.paths && saveRes.paths[0]) || "";
          if (!outP) return;
          statusBar.textContent = "Exporting model to " + outP + "...";
          window.FOSS.api("model3d_export", { file_path: currentModelPath, output_path: outP, format: ext }).then(function (res) {
            if (res && res.output_path) {
              statusBar.textContent = "Saved to " + res.output_path;
              window.FOSS.toast.show({ message: "Exported to " + res.output_path, type: "success" });
            }
          });
        });
      }
    }, [window.FOSS.dom.el("span", { text: "Export 3D Model" })]);

    var sidebar = window.FOSS.dom.el("div", {
      style: "flex: 1 1 45%; min-width: 300px;"
    }, [
      window.FOSS.dom.el("div", { className: "card mb-md" }, [
        window.FOSS.dom.el("div", { className: "card-title text-sm font-semibold mb-sm", text: "Export Format" }),
        window.FOSS.dom.el("div", { className: "row gap-sm items-center mb-md" }, [formatSelect]),
        exportBtn
      ])
    ]);

    var layoutRow = window.FOSS.dom.el("div", {
      className: "row gap-md items-start",
      style: "display: flex; flex-wrap: wrap; width: 100%;"
    }, [
      window.FOSS.dom.el("div", { style: "flex: 1 1 50%; min-width: 360px;" }, [viewport.el]),
      sidebar
    ]);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(layoutRow);

    if (currentVertices && currentFaces && !modelMeshBuffer) {
      modelMeshBuffer = buildMeshBuffers(currentVertices, currentFaces);
    }
    viewport.render();
  }

  window.FOSS.router.register({
    id: "model3d",
    title: "3D Model Viewer & Slicer",
    navName: "3D Models",
    category: "Visuals",
    icon: "box",
    tabs: [
      { id: "inspector", label: "Inspector & Tools", render: renderUnifiedInspector },
      { id: "cut", label: "Cut Plane", render: renderCut },
      { id: "export", label: "Export & Convert", render: renderExport }
    ]
  });
})();
