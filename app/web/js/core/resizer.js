// Universal box resizer allowing panels and splits to be dragged and resized at will.
window.FOSS = window.FOSS || {};

(function () {
  var activeDrag = null;
  var M = 8;

  function init() {
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);
  }

  function getTarget(e) {
    var raw = e.target;
    if (!raw) return null;
    if (raw.closest("button, input, textarea, select, a, label, [role='button'], [role='tab']")) {
      return null;
    }
    return raw.closest(".split > *, .workbench > *, .sidebar, .panel, .tool-sidebar, .model3d-sidebar, .resizable, .resize-handle-e");
  }

  function detectEdge(el, e) {
    if (!el) return null;
    var rect = el.getBoundingClientRect();
    var x = e.clientX;
    var y = e.clientY;

    if (el.classList.contains("sidebar") || el.classList.contains("resize-handle-e")) {
      if (Math.abs(x - rect.right) <= M) return "sidebar";
      return null;
    }

    var parent = el.parentElement;
    if (parent && parent.classList.contains("split")) {
      var isMainFirst = parent.classList.contains("split-main-first");
      if (el === parent.firstElementChild) {
        if (Math.abs(x - rect.right) <= M) {
          return isMainFirst ? "split-right" : "split-left";
        }
      } else if (el === parent.lastElementChild) {
        if (Math.abs(x - rect.left) <= M) {
          return isMainFirst ? "split-right" : "split-left";
        }
      }
    }

    var nearL = Math.abs(x - rect.left) <= M;
    var nearR = Math.abs(x - rect.right) <= M;
    var nearT = Math.abs(y - rect.top) <= M;
    var nearB = Math.abs(y - rect.bottom) <= M;

    if (nearT && nearL) return "nw";
    if (nearT && nearR) return "ne";
    if (nearB && nearL) return "sw";
    if (nearB && nearR) return "se";
    if (nearL) return "w";
    if (nearR) return "e";
    if (nearT) return "n";
    if (nearB) return "s";
    return null;
  }

  function getCursor(edge) {
    if (!edge) return "";
    if (edge === "sidebar" || edge === "split-left" || edge === "split-right" || edge === "e" || edge === "w") return "ew-resize";
    if (edge === "n" || edge === "s") return "ns-resize";
    if (edge === "nw" || edge === "se") return "nwse-resize";
    if (edge === "ne" || edge === "sw") return "nesw-resize";
    return "";
  }

  function handleMouseMove(e) {
    if (activeDrag) {
      var dx = e.clientX - activeDrag.startX;
      var dy = e.clientY - activeDrag.startY;
      var el = activeDrag.el;
      var edge = activeDrag.edge;

      if (edge === "sidebar") {
        var w = Math.max(160, Math.min(window.innerWidth - 240, activeDrag.startW + dx));
        document.documentElement.style.setProperty("--sidebar-w", w + "px");
        return;
      }

      if (edge === "split-left") {
        var parentEl = el.parentElement;
        if (parentEl) {
          var parentRect = parentEl.getBoundingClientRect();
          var sw = Math.max(180, Math.min(parentRect.width - 200, e.clientX - parentRect.left));
          parentEl.style.setProperty("--split-left", sw + "px");
        }
        return;
      }

      if (edge === "split-right") {
        var parentEl2 = el.parentElement;
        if (parentEl2) {
          var parentRect2 = parentEl2.getBoundingClientRect();
          var rw = Math.max(180, Math.min(parentRect2.width - 200, parentRect2.right - e.clientX));
          parentEl2.style.setProperty("--split-right", rw + "px");
        }
        return;
      }

      var parentW = el.parentElement ? el.parentElement.clientWidth : window.innerWidth;
      var maxW = Math.max(180, parentW - 24);
      var parentH = el.parentElement ? el.parentElement.clientHeight : window.innerHeight;
      var maxH = Math.max(120, Math.max(parentH, 400));

      if (edge.indexOf("e") !== -1) {
        var nw = Math.min(maxW, Math.max(140, activeDrag.startW + dx));
        el.style.setProperty("width", nw + "px");
        el.style.setProperty("max-width", "none");
        el.style.setProperty("flex", "0 0 " + nw + "px");
      } else if (edge.indexOf("w") !== -1) {
        var nw2 = Math.min(maxW, Math.max(140, activeDrag.startW - dx));
        el.style.setProperty("width", nw2 + "px");
        el.style.setProperty("max-width", "none");
        el.style.setProperty("flex", "0 0 " + nw2 + "px");
      }

      if (edge.indexOf("s") !== -1) {
        var nh = Math.min(maxH, Math.max(60, activeDrag.startH + dy));
        el.style.setProperty("height", nh + "px");
        el.style.setProperty("min-height", nh + "px");
      } else if (edge.indexOf("n") !== -1) {
        var nh2 = Math.min(maxH, Math.max(60, activeDrag.startH - dy));
        el.style.setProperty("height", nh2 + "px");
        el.style.setProperty("min-height", nh2 + "px");
      }
      return;
    }

    var target = getTarget(e);
    if (!target) {
      document.body.style.removeProperty("cursor");
      return;
    }

    var detected = detectEdge(target, e);
    if (detected) {
      document.body.style.setProperty("cursor", getCursor(detected));
    } else {
      document.body.style.removeProperty("cursor");
    }
  }

  function handleMouseDown(e) {
    if (e.button !== 0) return;
    var target = getTarget(e);
    if (!target) return;
    var edge = null;
    if (target.classList.contains("resize-handle-e")) { edge = "sidebar"; target = target.closest(".sidebar"); } else { edge = detectEdge(target, e); }
    if (!edge) return;

    e.preventDefault();
    var rect = target.getBoundingClientRect();
    activeDrag = {
      el: target,
      edge: edge,
      startX: e.clientX,
      startY: e.clientY,
      startW: rect.width,
      startH: rect.height
    };

    document.body.style.setProperty("user-select", "none");
    document.documentElement.classList.add("is-resizing");
    target.classList.add("is-resizing");
  }

  function handleMouseUp() {
    if (activeDrag) {
      activeDrag.el.classList.remove("is-resizing");
      document.documentElement.classList.remove("is-resizing");
      activeDrag = null;
      document.body.style.removeProperty("user-select");
      document.body.style.removeProperty("cursor");
    }
  }

  window.FOSS.resizer = {
    init: init
  };
})();
