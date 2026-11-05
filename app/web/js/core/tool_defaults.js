// Per-tool default preferences: schema registry, persisted values, and editor modal.
window.FOSS = window.FOSS || {};

(function () {
  var schemas = {};

  function storeKey(toolId) {
    return "tool_defaults." + toolId;
  }

  function define(toolId, fields) {
    schemas[toolId] = fields || [];
  }

  function getFields(toolId) {
    return schemas[toolId] || [];
  }

  function saved(toolId) {
    var raw = window.FOSS.store.get(storeKey(toolId), {});
    return raw && typeof raw === "object" ? raw : {};
  }

  function all(toolId) {
    var values = {};
    var stored = saved(toolId);
    getFields(toolId).forEach(function (field) {
      values[field.key] = stored[field.key] !== undefined ? stored[field.key] : field.default;
    });
    return values;
  }

  function get(toolId, key, fallback) {
    var values = all(toolId);
    if (values[key] !== undefined) return values[key];
    return fallback;
  }

  function save(toolId, values) {
    var merged = Object.assign({}, saved(toolId), values);
    window.FOSS.store.set(storeKey(toolId), merged);
    window.dispatchEvent(new CustomEvent("foss:tool-defaults-changed", {
      detail: { toolId: toolId, values: all(toolId) }
    }));
  }

  function normalizeOptions(field) {
    return (field.options || []).map(function (opt) {
      return typeof opt === "object" ? opt : { value: opt, label: String(opt) };
    });
  }

  function buildControl(toolId, field, current, collected) {
    var testid = toolId + "-defaults-" + field.key;
    var kind = field.type || "text";

    if (kind === "toggle") {
      var toggle = window.FOSS.components.switch({
        testid: testid,
        label: field.label,
        checked: !!current,
        onChange: function (val) { collected[field.key] = val; }
      });
      return toggle.el;
    }

    var input;
    if (kind === "select") {
      input = window.FOSS.dom.el("select", {
        className: "select",
        "data-testid": testid,
        "aria-label": field.label,
        onChange: function (e) { collected[field.key] = e.target.value; }
      }, normalizeOptions(field).map(function (opt) {
        return window.FOSS.dom.el("option", {
          value: String(opt.value),
          text: opt.label,
          selected: String(opt.value) === String(current)
        });
      }));
    } else if (kind === "number") {
      input = window.FOSS.dom.el("input", {
        type: "number",
        className: "input",
        value: String(current),
        min: field.min !== undefined ? String(field.min) : null,
        max: field.max !== undefined ? String(field.max) : null,
        step: field.step !== undefined ? String(field.step) : "1",
        "data-testid": testid,
        "aria-label": field.label,
        onChange: function (e) {
          var num = parseFloat(e.target.value);
          if (!isNaN(num)) collected[field.key] = num;
        }
      });
    } else {
      input = window.FOSS.dom.el("input", {
        type: kind === "color" ? "color" : "text",
        className: "input",
        value: String(current),
        "data-testid": testid,
        "aria-label": field.label,
        onChange: function (e) { collected[field.key] = e.target.value; }
      });
    }
    return window.FOSS.dom.el("div", { className: "field" }, [
      window.FOSS.dom.el("label", { text: field.label }),
      input,
      field.hint ? window.FOSS.dom.el("span", { className: "hint", text: field.hint }) : null
    ]);
  }

  function buildForm(toolId, collected) {
    var current = all(toolId);
    var form = window.FOSS.dom.el("div", { className: "stack", "data-testid": toolId + "-defaults-form" });
    var fields = getFields(toolId);
    if (fields.length === 0) {
      form.appendChild(window.FOSS.dom.el("p", { className: "desc", text: "This tool has no configurable defaults." }));
    }
    fields.forEach(function (field) {
      form.appendChild(buildControl(toolId, field, current[field.key], collected));
    });
    return form;
  }

  function openEditor(toolId, title) {
    var collected = {};
    return window.FOSS.dialogs.custom({
      title: (title || toolId) + " Defaults",
      testid: toolId + "-defaults-modal",
      confirmText: "Save Defaults",
      content: buildForm(toolId, collected),
      onConfirm: function () {
        save(toolId, collected);
        window.FOSS.toast.show("Defaults saved", "success");
      }
    });
  }

  window.FOSS.toolDefaults = {
    define: define,
    getFields: getFields,
    all: all,
    get: get,
    save: save,
    buildForm: buildForm,
    openEditor: openEditor
  };
})();
