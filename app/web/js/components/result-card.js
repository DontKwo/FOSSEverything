// Result card component: file output preview, details, and filesystem actions.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function resultCard(opts) {
    opts = opts || {};
    var testid = opts.testid || "result-card";
    var titleStr = opts.title || "Operation Complete";
    var outputPath = opts.outputPath || "";
    var details = opts.details || [];
    var previewUrl = opts.previewUrl || "";

    var header = window.FOSS.dom.el("h4", { className: "result-title", text: titleStr });

    var children = [header];

    if (previewUrl) {
      var img = window.FOSS.dom.el("img", {
        src: previewUrl,
        className: "result-preview",
        alt: "Result preview"
      });
      children.push(img);
    }

    if (details.length > 0) {
      var list = window.FOSS.dom.el("div", { className: "stack", gap: "xs" }, details.map(function (d) {
        return window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [
          window.FOSS.dom.el("span", { className: "text-muted", text: d.label + ":" }),
          window.FOSS.dom.el("span", { text: String(d.value) })
        ]);
      }));
      children.push(list);
    }

    if (outputPath) {
      var pathRow = window.FOSS.dom.el("div", {
        className: "result-path text-muted font-mono",
        text: outputPath,
        title: outputPath,
        "data-truncate-ok": "true"
      });
      children.push(pathRow);

      var openFileBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": testid + "-open-file",
        type: "button",
        onClick: function () {
          window.FOSS.api("open_path", { path: outputPath });
        }
      }, [
        window.FOSS.icons.el("file", 16),
        window.FOSS.dom.el("span", { text: "Open File" })
      ]);

      var showFolderBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary btn-sm",
        "data-testid": testid + "-show-folder",
        type: "button",
        onClick: function () {
          window.FOSS.api("open_folder", { path: outputPath });
        }
      }, [
        window.FOSS.icons.el("folder", 16),
        window.FOSS.dom.el("span", { text: "Show in Folder" })
      ]);

      var actions = window.FOSS.dom.el("div", { className: "row", gap: "sm" }, [openFileBtn, showFolderBtn]);
      children.push(actions);
    }

    return window.FOSS.dom.el("div", {
      className: "result-card",
      "data-testid": testid
    }, children);
  }

  window.FOSS.components.resultCard = resultCard;
})();
