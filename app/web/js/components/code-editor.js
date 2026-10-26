// Code editor component: monospace textarea with actions and copy support.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function codeEditor(opts) {
    opts = opts || {};
    var testid = opts.testid || "code-editor";
    var placeholder = opts.placeholder || "";
    var readOnly = !!opts.readOnly;
    var value = opts.value || "";
    var onChange = opts.onChange || function () {};

    var textarea = window.FOSS.dom.el("textarea", {
      className: "code-editor",
      placeholder: placeholder,
      "aria-label": opts.ariaLabel || opts.title || opts.placeholder || "Editor",
      "data-testid": testid + "-input",
      spellcheck: "false",
      autocomplete: "off",
      autocapitalize: "off"
    });
    if (readOnly) textarea.setAttribute("readonly", "readonly");
    textarea.value = value;

    textarea.addEventListener("input", function () {
      onChange(textarea.value);
    });

    var copyBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm btn-icon",
      "data-testid": testid + "-copy",
      "aria-label": "Copy editor contents",
      title: "Copy editor contents",
      type: "button",
      onClick: function () {
        if (!textarea.value) return;
        window.FOSS.api("copy_to_clipboard", { text: textarea.value }).then(function () {
          window.FOSS.toast.show("Copied to clipboard", "success");
        });
      }
    }, [window.FOSS.icons.el("copy", 16)]);

    var clearBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm btn-icon",
      "data-testid": testid + "-clear",
      "aria-label": "Clear editor contents",
      title: "Clear editor contents",
      type: "button",
      onClick: function () {
        setValue("");
      }
    }, [window.FOSS.icons.el("close", 16)]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "row",
      gap: "xs"
    }, [copyBtn, clearBtn]);

    var header = window.FOSS.dom.el("div", {
      className: "row",
      style: undefined
    }, [
      opts.title ? window.FOSS.dom.el("span", { className: "card-title", text: opts.title }) : window.FOSS.dom.el("span", {}),
      toolbar
    ]);

    var wrap = window.FOSS.dom.el("div", {
      className: "stack",
      gap: "xs",
      "data-testid": testid
    }, [
      header,
      textarea
    ]);

    function setValue(val) {
      textarea.value = val || "";
      onChange(textarea.value);
    }

    return {
      el: wrap,
      textarea: textarea,
      getValue: function () {
        return textarea.value;
      },
      setValue: setValue,
      clear: function () {
        setValue("");
      }
    };
  }

  window.FOSS.components.codeEditor = codeEditor;
})();
