// File picker component: drop target, file selection dialogs, and clear action.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function filePicker(opts) {
    opts = opts || {};
    var testid = opts.testid || "file-picker";
    var title = opts.title || "Choose file";
    var fileTypes = opts.fileTypes || [];
    var currentPath = opts.path || "";
    var onSelect = opts.onSelect || function () {};
    var onClear = opts.onClear || function () {};

    var nameEl = window.FOSS.dom.el("div", {
      className: "picker-name",
      text: currentPath ? currentPath.split(/[/\\]/).pop() : "No file chosen",
      title: currentPath || "No file chosen",
      "data-truncate-ok": "true"
    });

    var pathEl = window.FOSS.dom.el("div", {
      className: "picker-path",
      text: currentPath || "Click to browse or drop file here",
      title: currentPath || "",
      "data-truncate-ok": "true"
    });

    var browseBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": testid + "-browse",
      type: "button",
      onClick: function (e) {
        e.stopPropagation();
        window.FOSS.api("select_file", { title: title, file_types: fileTypes }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            setPath(res.paths[0]);
            onSelect(res.paths[0]);
          }
        });
      }
    }, [
      window.FOSS.icons.el("folder", 16),
      window.FOSS.dom.el("span", { text: "Choose file" })
    ]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm btn-icon",
      "data-testid": testid + "-clear",
      "aria-label": "Clear file selection",
      title: "Clear file selection",
      type: "button",
      onClick: function (e) {
        e.stopPropagation();
        setPath("");
        onClear();
      }
    }, [window.FOSS.icons.el("close", 16)]);

    var actions = window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [browseBtn, clearBtn]);
    var info = window.FOSS.dom.el("div", { className: "stack", gap: "xs" }, [nameEl, pathEl]);

    var wrap = window.FOSS.dom.el("div", {
      className: "file-picker",
      "data-testid": testid,
      role: "region",
      "aria-label": "File drop zone",
      onClick: function () {
        browseBtn.click();
      }
    }, [
      window.FOSS.icons.el("file", 24),
      info,
      actions
    ]);

    wrap.addEventListener("dragover", function (e) {
      e.preventDefault();
      wrap.classList.add("dragover");
    });
    wrap.addEventListener("dragleave", function () {
      wrap.classList.remove("dragover");
    });
    wrap.addEventListener("drop", function (e) {
      e.preventDefault();
      wrap.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        var f = e.dataTransfer.files[0];
        var p = f.path || f.name;
        setPath(p);
        onSelect(p);
      }
    });

    function setPath(newPath) {
      currentPath = newPath || "";
      nameEl.textContent = currentPath ? currentPath.split(/[/\\]/).pop() : "No file chosen";
      nameEl.setAttribute("title", currentPath || "No file chosen");
      pathEl.textContent = currentPath || "Click to browse or drop file here";
      pathEl.setAttribute("title", currentPath || "");
    }

    return {
      el: wrap,
      getPath: function () {
        return currentPath;
      },
      setPath: setPath
    };
  }

  window.FOSS.components.filePicker = filePicker;
})();
