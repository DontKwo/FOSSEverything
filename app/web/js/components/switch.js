// Switch component for binary toggle options.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function switchControl(opts) {
    opts = opts || {};
    var testid = opts.testid || "switch";
    var labelStr = opts.label || "";
    var checked = !!opts.checked;
    var onChange = opts.onChange || function () {};

    var input = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": testid + "-input"
    });
    input.checked = checked;

    var slider = window.FOSS.dom.el("span", { className: "switch-slider" });
    var textEl = window.FOSS.dom.el("span", { className: "switch-label", text: labelStr });

    input.addEventListener("change", function () {
      onChange(input.checked);
    });

    var wrap = window.FOSS.dom.el("label", {
      className: "switch",
      "data-testid": testid
    }, [
      input,
      slider,
      textEl
    ]);

    return {
      el: wrap,
      input: input,
      isChecked: function () {
        return input.checked;
      },
      setChecked: function (val) {
        input.checked = !!val;
        onChange(input.checked);
      },
      setLabel: function (str) {
        textEl.textContent = str;
      }
    };
  }

  window.FOSS.components.switch = switchControl;
})();
