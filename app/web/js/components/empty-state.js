// Empty state placeholder component for unoccupied views and lists.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function emptyState(opts) {
    opts = opts || {};
    var testid = opts.testid || "empty";
    var iconName = opts.icon || "file";
    var titleStr = opts.title || "No items";
    var descStr = opts.desc || "";
    var action = opts.action;

    var iconWrapper = window.FOSS.dom.el("div", { className: "empty-icon" }, [
      window.FOSS.icons.el(iconName, 36)
    ]);

    var titleEl = window.FOSS.dom.el("h3", { className: "empty-title", text: titleStr });
    var descEl = descStr ? window.FOSS.dom.el("p", { className: "empty-desc", text: descStr }) : null;

    var children = [iconWrapper, titleEl];
    if (descEl) children.push(descEl);

    if (action) {
      var actBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary btn-sm",
        text: action.label,
        type: "button",
        "data-testid": testid + "-action",
        onClick: action.onClick
      });
      children.push(actBtn);
    }

    return window.FOSS.dom.el("div", {
      className: "empty",
      "data-testid": testid
    }, children);
  }

  window.FOSS.components.emptyState = emptyState;
})();
