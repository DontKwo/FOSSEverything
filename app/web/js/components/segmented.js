// Segmented control component for mutually exclusive option buttons.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function segmented(opts) {
    opts = opts || {};
    var testid = opts.testid || "segmented";
    var items = opts.items || [];
    var value = opts.value !== undefined ? opts.value : (items[0] ? items[0].id : "");
    var onChange = opts.onChange || function () {};
    var buttons = [];

    var container = window.FOSS.dom.el("div", {
      className: "segmented",
      "data-testid": testid,
      role: "radiogroup"
    });

    items.forEach(function (it) {
      var isChecked = it.id === value;
      var btn = window.FOSS.dom.el("button", {
        type: "button",
        role: "radio",
        "aria-checked": isChecked ? "true" : "false",
        className: isChecked ? "active" : "",
        "data-testid": testid + "-" + it.id,
        "aria-label": it.label || it.id,
        title: it.title || it.label || it.id,
        onClick: function () {
          setValue(it.id);
        }
      }, [
        it.icon ? window.FOSS.icons.el(it.icon, 16) : null,
        window.FOSS.dom.el("span", { text: it.label || it.id })
      ]);
      buttons.push({ id: it.id, btn: btn });
      container.appendChild(btn);
    });

    function setValue(newVal) {
      value = newVal;
      buttons.forEach(function (b) {
        var chk = b.id === value;
        b.btn.setAttribute("aria-checked", chk ? "true" : "false");
        if (chk) {
          b.btn.classList.add("active");
        } else {
          b.btn.classList.remove("active");
        }
      });
      onChange(value);
    }

    return {
      el: container,
      getValue: function () {
        return value;
      },
      setValue: setValue
    };
  }

  window.FOSS.components.segmented = segmented;
})();
