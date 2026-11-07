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

  function getToolbarOrder(toolbarId, defaultKeys) {
    var key = "toolbar_order." + toolbarId;
    var savedOrder = window.FOSS.store.get(key, null);
    if (Array.isArray(savedOrder) && savedOrder.length > 0) return savedOrder;
    return defaultKeys || [];
  }

  function setToolbarOrder(toolbarId, keys) {
    var key = "toolbar_order." + toolbarId;
    window.FOSS.store.set(key, keys);
    window.dispatchEvent(new CustomEvent("foss:toolbar-order-changed", {
      detail: { toolbarId: toolbarId, order: keys }
    }));
  }

  function renderCustomizableToolbar(opts) {
    opts = opts || {};
    var toolbarId = opts.id || "toolbar_" + Date.now();
    var items = opts.items || [];
    var className = opts.className || "row items-center gap-2 flex-wrap";
    var defaultKeys = items.map(function (it) { return it.id; });

    var container = window.FOSS.dom.el("div", {
      className: className,
      "data-testid": opts.testid || ("toolbar-" + toolbarId)
    });

    function rebuild() {
      container.innerHTML = "";
      var order = getToolbarOrder(toolbarId, defaultKeys);
      var itemMap = {};
      items.forEach(function (it) { itemMap[it.id] = it; });

      order.forEach(function (k) {
        if (itemMap[k] && itemMap[k].el) {
          container.appendChild(itemMap[k].el);
        }
      });

      items.forEach(function (it) {
        if (order.indexOf(it.id) === -1 && it.el) {
          container.appendChild(it.el);
        }
      });

      var editBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm btn-icon",
        title: "Customize toolbar order",
        "aria-label": "Customize toolbar order",
        onClick: function () {
          openToolbarCustomizer(toolbarId, items, rebuild);
        }
      }, [window.FOSS.icons.el("settings", 12)]);
      container.appendChild(editBtn);
    }

    rebuild();
    return { el: container, refresh: rebuild };
  }

  function openToolbarCustomizer(toolbarId, items, onSave) {
    var defaultKeys = items.map(function (it) { return it.id; });
    var currentOrder = getToolbarOrder(toolbarId, defaultKeys).slice();

    var listEl = window.FOSS.dom.el("div", { className: "stack-sm" });

    function renderList() {
      listEl.innerHTML = "";
      currentOrder.forEach(function (k, idx) {
        var it = items.find(function (i) { return i.id === k; });
        var label = (it && it.label) || k;

        var upBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          disabled: idx === 0,
          text: "\u25b2",
          onClick: function () {
            if (idx > 0) {
              var tmp = currentOrder[idx - 1];
              currentOrder[idx - 1] = currentOrder[idx];
              currentOrder[idx] = tmp;
              renderList();
            }
          }
        });

        var downBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          disabled: idx === currentOrder.length - 1,
          text: "\u25bc",
          onClick: function () {
            if (idx < currentOrder.length - 1) {
              var tmp = currentOrder[idx + 1];
              currentOrder[idx + 1] = currentOrder[idx];
              currentOrder[idx] = tmp;
              renderList();
            }
          }
        });

        var row = window.FOSS.dom.el("div", {
          className: "row-between p-2 rounded surface-hover"
        }, [
          window.FOSS.dom.el("span", { className: "text-sm font-semibold", text: label }),
          window.FOSS.dom.el("div", { className: "row gap-1" }, [upBtn, downBtn])
        ]);
        listEl.appendChild(row);
      });
    }

    renderList();

    window.FOSS.dialogs.custom({
      title: "Customize Toolbar Order",
      testid: "toolbar-customizer-modal",
      confirmText: "Save Order",
      content: listEl,
      onConfirm: function () {
        setToolbarOrder(toolbarId, currentOrder);
        if (onSave) onSave();
        window.FOSS.toast.show("Toolbar order updated", "success");
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
    openEditor: openEditor,
    getToolbarOrder: getToolbarOrder,
    setToolbarOrder: setToolbarOrder,
    renderCustomizableToolbar: renderCustomizableToolbar
  };
})();
