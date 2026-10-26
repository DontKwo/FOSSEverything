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

  function handleDragEnter(e) {
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
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      var ov = getOverlay();
      if (ov.parentElement) {
        ov.parentElement.removeChild(ov);
      }
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDrop(e) {
    e.preventDefault();
    dragCounter = 0;
    var ov = getOverlay();
    if (ov.parentElement) {
      ov.parentElement.removeChild(ov);
    }

    var files = e.dataTransfer ? e.dataTransfer.files : [];
    if (!files || files.length === 0) return;

    var paths = [];
    for (var i = 0; i < files.length; i++) {
      if (files[i].path) {
        paths.push(files[i].path);
      }
    }

    if (paths.length > 0 && window.FOSS.router) {
      window.FOSS.router.routeFiles(paths);
    }
  }

  window.FOSS.dropzone = {
    init: init
  };
})();

