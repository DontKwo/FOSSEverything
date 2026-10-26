// Field component: label, control, and hint text.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function field(labelStr, controlEl, hintStr, isInvalid, testid) {
    var children = [];
    if (labelStr) {
      children.push(window.FOSS.dom.el("label", { text: labelStr }));
    }
    if (controlEl) {
      children.push(controlEl);
    }
    if (hintStr) {
      children.push(window.FOSS.dom.el("span", { className: "hint", text: hintStr }));
    }
    var cls = "field" + (isInvalid ? " invalid" : "");
    var attrs = { className: cls };
    if (testid) attrs["data-testid"] = testid;
    return window.FOSS.dom.el("div", attrs, children);
  }

  window.FOSS.components.field = field;
})();
