// Global drag-and-drop routing overlay.
window.FOSS = window.FOSS || {};

(function () {
  var overlay = null;
  var dragCounter = 0;

  function init() {
    window.addEventListener("dragenter", handleDragEnter);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("drop", handleDrop);
    window.addEventListener("dragend", resetDrag);
    window.addEventListener("blur", resetDrag);
    window.addEventListener("keydown", function (e) {
      if (e.key === "Escape") resetDrag();
    });
  }

  function resetDrag() {
    dragCounter = 0;
    if (overlay && overlay.parentElement) {
      overlay.parentElement.removeChild(overlay);
    }
  }

  function getOverlay() {
    if (!overlay) {
      overlay = window.FOSS.dom.el("div", {
        className: "drop-overlay",
        "data-overlay": "true",
        "data-testid": "global-dropzone"
      }, [
        window.FOSS.dom.el("div", { className: "drop-overlay-card card" }, [
          window.FOSS.icons.el("upload", 32),
          window.FOSS.dom.el("h3", { className: "title", text: "Drop files to open in FOSSEverything" })
        ])
      ]);
    }
    return overlay;
  }

  function isFileDrag(e) {
    if (!e || !e.dataTransfer || !e.dataTransfer.types) return false;
    var types = e.dataTransfer.types;
    for (var i = 0; i < types.length; i++) {
      if (types[i] === "Files") return true;
    }
    return false;
  }

  function handleDragEnter(e) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragCounter++;
    if (dragCounter === 1) {
      var ov = getOverlay();
      if (!ov.parentElement) {
        document.body.appendChild(ov);
      }
    }
  }

  function handleDragLeave(e) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      resetDrag();
    }
  }

  function handleDragOver(e) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
  }

  function handleDrop(e) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    resetDrag();

    var files = e.dataTransfer ? e.dataTransfer.files : [];
    if (!files || files.length === 0) return;

    // In pywebview, bare filenames without paths are handled via pywebviewFullPath
    if (window.pywebview && !files[0].path) {
      return;
    }

    var paths = [];
    for (var i = 0; i < files.length; i++) {
      var p = files[i].path || files[i].name;
      if (p) {
        paths.push(p);
      }
    }

    if (paths.length > 0 && window.FOSS.router) {
      window.FOSS.router.routeFiles(paths);
    }
  }

  window.FOSS.dropzone = {
    init: init,
    reset: resetDrag
  };
})();
