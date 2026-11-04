// Field component: label, control, and hint text.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  var fieldCounter = 0;

  function field(labelStr, controlEl, hintStr, isInvalid, testid) {
    if (labelStr && typeof labelStr === "object" && !labelStr.tagName) {
      var opts = labelStr;
      labelStr = opts.label || "";
      controlEl = opts.control || null;
      hintStr = opts.hint || "";
      isInvalid = opts.isInvalid || false;
      testid = opts.testid || "";
    }
    var children = [];
    var controlId = "";

    if (controlEl) {
      if (controlEl.id) {
        controlId = controlEl.id;
      } else {
        fieldCounter++;
        controlId = (testid || "field") + "-ctrl-" + fieldCounter;
        controlEl.id = controlId;
      }
    }

    if (labelStr) {
      var labelAttrs = { text: labelStr };
      if (controlId) {
        labelAttrs.htmlFor = controlId;
      }
      children.push(window.FOSS.dom.el("label", labelAttrs));
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
