// Slider component: numeric range input with synchronized text output.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function slider(opts) {
    opts = opts || {};
    var testid = opts.testid || "slider";
    var min = opts.min !== undefined ? opts.min : 0;
    var max = opts.max !== undefined ? opts.max : 100;
    var step = opts.step !== undefined ? opts.step : 1;
    var unit = opts.unit || "";
    var value = opts.value !== undefined ? opts.value : min;
    var onChange = opts.onChange || function () {};

    var output = window.FOSS.dom.el("output", {
      text: value + (unit ? " " + unit : "")
    });

    var range = window.FOSS.dom.el("input", {
      type: "range",
      min: String(min),
      max: String(max),
      step: String(step),
      value: String(value),
      "data-testid": testid + "-range"
    });

    range.addEventListener("input", function () {
      var val = Number(range.value);
      output.textContent = val + (unit ? " " + unit : "");
      onChange(val);
    });

    var wrap = window.FOSS.dom.el("div", {
      className: "slider-field",
      "data-testid": testid
    }, [range, output]);

    return {
      el: wrap,
      getValue: function () {
        return Number(range.value);
      },
      setValue: function (val) {
        range.value = String(val);
        output.textContent = val + (unit ? " " + unit : "");
        onChange(Number(val));
      }
    };
  }

  window.FOSS.components.slider = slider;
})();
