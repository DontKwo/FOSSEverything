// Clean explicit handle resizer for sidebar and split dividers.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  var activeDrag = null;

  function getRootFontSize() {
    var fs = parseFloat(window.getComputedStyle(document.documentElement).fontSize);
    return isNaN(fs) || fs <= 0 ? 16 : fs;
  }

  function init() {
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    window.addEventListener("blur", handleMouseUp);
    document.addEventListener("keydown", handleKeyDown);

    var savedSidebar = window.FOSS.store ? window.FOSS.store.get("sidebar_width_rem", null) : null;
    if (savedSidebar) {
      var num = parseFloat(savedSidebar);
      if (!isNaN(num) && num >= 12 && num <= 24) {
        document.documentElement.style.setProperty("--sidebar-w", num + "rem");
      }
    }

    ensureSidebarHandle();
  }

  function ensureSidebarHandle() {
    var sidebar = document.querySelector(".sidebar");
    if (sidebar && !sidebar.querySelector(".sidebar-resizer")) {
      var handle = document.createElement("div");
      handle.className = "sidebar-resizer";
      handle.setAttribute("data-decorative", "true");
      sidebar.appendChild(handle);
    }
  }

  function handleKeyDown(e) {
    var divider = e.target ? e.target.closest(".split-divider") : null;
    if (!divider) return;
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

    var split = divider.closest(".split");
    if (!split) return;

    e.preventDefault();
    var side = divider.dataset.side || (split.classList.contains("split-main-first") ? "right" : "left");
    var prop = "--split-" + side;
    var rootFs = getRootFontSize();
    var rect = split.getBoundingClientRect();
    var currentRem = parseFloat(split.style.getPropertyValue(prop));

    if (isNaN(currentRem)) {
      currentRem = side === "right" ? 24 : 23;
    }

    var step = (e.key === "ArrowRight" ? 1 : -1) * (side === "right" ? -1 : 1);
    var nextRem = currentRem + step;
    var minRem = 15;
    var maxRem = (rect.width * 0.80) / rootFs;
    nextRem = Math.max(minRem, Math.min(maxRem, nextRem));

    split.style.setProperty(prop, nextRem.toFixed(2) + "rem");
  }

  function handleMouseDown(e) {
    if (e.button !== 0) return;
    var target = e.target;
    if (!target) return;

    var sidebarResizer = target.closest(".sidebar-resizer, .resize-handle-e");
    var splitDivider = target.closest(".split-divider");

    var disabledElements = [];
    var targets = document.querySelectorAll("canvas, iframe");
    for (var ti = 0; ti < targets.length; ti++) {
      var tel = targets[ti];
      disabledElements.push({ el: tel, prev: tel.style.getPropertyValue("pointer-events") });
      tel.style.setProperty("pointer-events", "none");
    }

    if (sidebarResizer) {
      e.preventDefault();
      e.stopPropagation();
      var sidebar = sidebarResizer.closest(".sidebar") || document.querySelector(".sidebar");
      if (!sidebar) {
        restorePointers(disabledElements);
        return;
      }
      var rect = sidebar.getBoundingClientRect();
      activeDrag = {
        kind: "sidebar",
        startX: e.clientX,
        startWidth: rect.width,
        disabledElements: disabledElements
      };
      document.body.style.setProperty("cursor", "col-resize");
      document.body.style.setProperty("user-select", "none");
      document.documentElement.classList.add("is-resizing");
      return;
    }

    if (splitDivider) {
      e.preventDefault();
      e.stopPropagation();
      var split = splitDivider.closest(".split");
      if (!split) {
        restorePointers(disabledElements);
        return;
      }
      var splitRect = split.getBoundingClientRect();
      var side = splitDivider.dataset.side || (split.classList.contains("split-main-first") ? "right" : "left");

      activeDrag = {
        kind: "split",
        splitEl: split,
        side: side,
        divider: splitDivider,
        splitRect: splitRect,
        disabledElements: disabledElements
      };
      splitDivider.classList.add("active");
      document.body.style.setProperty("cursor", "col-resize");
      document.body.style.setProperty("user-select", "none");
      document.documentElement.classList.add("is-resizing");
      return;
    }

    restorePointers(disabledElements);
  }

  function handleMouseMove(e) {
    if (!activeDrag) return;

    var rootFs = getRootFontSize();

    if (activeDrag.kind === "sidebar") {
      var dx = e.clientX - activeDrag.startX;
      var newPx = activeDrag.startWidth + dx;
      var rem = newPx / rootFs;
      rem = Math.max(12, Math.min(24, rem));
      document.documentElement.style.setProperty("--sidebar-w", rem.toFixed(2) + "rem");
      activeDrag.lastRem = rem;
      return;
    }

    if (activeDrag.kind === "split") {
      var sRect = activeDrag.splitEl.getBoundingClientRect();
      var pxVal = activeDrag.side === "right" ? sRect.right - e.clientX : e.clientX - sRect.left;
      var minPx = 15 * rootFs;
      var maxPx = sRect.width * 0.80;
      pxVal = Math.max(minPx, Math.min(maxPx, pxVal));
      var splitRem = pxVal / rootFs;
      activeDrag.splitEl.style.setProperty("--split-" + activeDrag.side, splitRem.toFixed(2) + "rem");
    }
  }

  function restorePointers(elements) {
    if (!elements) return;
    for (var i = 0; i < elements.length; i++) {
      var item = elements[i];
      if (item.prev) {
        item.el.style.setProperty("pointer-events", item.prev);
      } else {
        item.el.style.removeProperty("pointer-events");
      }
    }
  }

  function handleMouseUp() {
    if (!activeDrag) return;

    if (activeDrag.kind === "sidebar" && activeDrag.lastRem && window.FOSS.store) {
      window.FOSS.store.set("sidebar_width_rem", parseFloat(activeDrag.lastRem.toFixed(2)));
    }

    if (activeDrag.divider) {
      activeDrag.divider.classList.remove("active");
    }

    if (activeDrag.disabledElements) {
      restorePointers(activeDrag.disabledElements);
    }

    activeDrag = null;
    document.documentElement.classList.remove("is-resizing");
    document.body.style.removeProperty("cursor");
    document.body.style.removeProperty("user-select");
  }

  window.FOSS.components.splitDivider = function (opts) {
    opts = opts || {};
    var div = document.createElement("div");
    div.className = "split-divider" + (opts.className ? " " + opts.className : "");
    div.setAttribute("role", "separator");
    div.setAttribute("aria-orientation", "vertical");
    div.setAttribute("tabindex", "0");
    div.setAttribute("aria-label", opts.label || "Resize panels");
    div.setAttribute("data-dense", "true");
    if (opts.testid) {
      div.setAttribute("data-testid", opts.testid);
    }
    div.dataset.side = opts.side || (opts.targetSplit && opts.targetSplit.classList.contains("split-main-first") ? "right" : "left");
    return div;
  };

  window.FOSS.resizer = {
    init: init,
    ensureSidebarHandle: ensureSidebarHandle
  };
})();
