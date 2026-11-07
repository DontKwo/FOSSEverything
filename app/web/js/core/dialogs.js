// Modal confirmation, alert, and prompt dialogs.
window.FOSS = window.FOSS || {};

(function () {
  var host = null;
  var activeCleanups = [];

  function getHost() {
    if (!host) {
      host = document.getElementById("modal-host");
    }
    return host;
  }

  function closeAll() {
    var list = activeCleanups.slice();
    activeCleanups = [];
    for (var i = 0; i < list.length; i++) {
      try {
        list[i]();
      } catch (err) {
        // Ignore cleanup errors
      }
    }
    var h = getHost();
    if (h) {
      h.classList.remove("active");
      while (h.firstChild) {
        h.removeChild(h.firstChild);
      }
    }
  }

  function alert(options) {
    var opts = typeof options === "string" ? { message: options } : (options || {});
    var title = opts.title || "Notification";
    var message = opts.message || "";
    var buttonText = opts.buttonText || "OK";

    return new Promise(function (resolve) {
      var h = getHost();
      if (!h) {
        resolve();
        return;
      }

      var scrim = window.FOSS.dom.el("div", { className: "scrim", "data-overlay": "true" });
      var titleEl = window.FOSS.dom.el("h3", { className: "card-title", text: title });
      var msgEl = window.FOSS.dom.el("p", { className: "desc", text: message });

      var okBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary",
        text: buttonText,
        "data-testid": "modal-alert-btn",
        onClick: function () {
          cleanup();
          resolve();
        }
      });

      var actionsEl = window.FOSS.dom.el("div", { className: "row end" }, [okBtn]);
      var modalEl = window.FOSS.dom.el("div", {
        className: "modal",
        role: "dialog",
        "aria-modal": "true",
        "data-testid": "alert-modal"
      }, [titleEl, msgEl, actionsEl]);

      function cleanup() {
        var idx = activeCleanups.indexOf(cleanup);
        if (idx >= 0) activeCleanups.splice(idx, 1);
        if (activeCleanups.length === 0) h.classList.remove("active");
        if (scrim.parentElement) scrim.parentElement.removeChild(scrim);
        if (modalEl.parentElement) modalEl.parentElement.removeChild(modalEl);
        document.removeEventListener("keydown", onKeyDown);
      }

      function onKeyDown(e) {
        if (e.key === "Escape" || e.key === "Enter") {
          cleanup();
          resolve();
        }
      }

      if (!opts.persistent) {
        scrim.addEventListener("click", function () {
          cleanup();
          resolve();
        });
      }

      activeCleanups.push(cleanup);
      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
      okBtn.focus();
    });
  }

  function confirm(options) {
    var opts = typeof options === "string" ? { message: options } : (options || {});
    var title = opts.title || "Confirm Action";
    var message = opts.message || "Are you sure you want to proceed?";
    var confirmText = opts.confirmText || "Confirm";
    var cancelText = opts.cancelText || "Cancel";
    var danger = opts.danger || false;

    return new Promise(function (resolve) {
      var h = getHost();
      if (!h) {
        resolve(false);
        return;
      }

      var scrim = window.FOSS.dom.el("div", { className: "scrim", "data-overlay": "true" });
      var titleEl = window.FOSS.dom.el("h3", { className: "card-title", text: title });
      var msgEl = window.FOSS.dom.el("p", { className: "desc", text: message });

      var confirmBtn = window.FOSS.dom.el("button", {
        className: "btn " + (danger ? "btn-danger" : "btn-primary"),
        text: confirmText,
        "data-testid": "modal-confirm-btn",
        onClick: function () {
          cleanup();
          resolve(true);
        }
      });

      var cancelBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary",
        text: cancelText,
        "data-testid": "modal-cancel-btn",
        onClick: function () {
          cleanup();
          resolve(false);
        }
      });

      var actionsEl = window.FOSS.dom.el("div", { className: "row end" }, [cancelBtn, confirmBtn]);
      var modalEl = window.FOSS.dom.el("div", {
        className: "modal",
        role: "dialog",
        "aria-modal": "true",
        "data-testid": "confirm-modal"
      }, [titleEl, msgEl, actionsEl]);

      function cleanup() {
        var idx = activeCleanups.indexOf(cleanup);
        if (idx >= 0) activeCleanups.splice(idx, 1);
        if (activeCleanups.length === 0) h.classList.remove("active");
        if (scrim.parentElement) scrim.parentElement.removeChild(scrim);
        if (modalEl.parentElement) modalEl.parentElement.removeChild(modalEl);
        document.removeEventListener("keydown", onKeyDown);
      }

      function onKeyDown(e) {
        if (e.key === "Escape") {
          cleanup();
          resolve(false);
        }
      }

      if (!opts.persistent) {
        scrim.addEventListener("click", function () {
          cleanup();
          resolve(false);
        });
      }

      activeCleanups.push(cleanup);
      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
      confirmBtn.focus();
    });
  }


  function prompt(options) {
    var opts = typeof options === "string" ? { message: options } : (options || {});
    var title = opts.title || "Input Required";
    var message = opts.message || "";
    var defaultValue = opts.defaultValue || "";
    var confirmText = opts.confirmText || "OK";
    var cancelText = opts.cancelText || "Cancel";

    return new Promise(function (resolve) {
      var h = getHost();
      if (!h) {
        resolve(null);
        return;
      }

      var scrim = window.FOSS.dom.el("div", { className: "scrim", "data-overlay": "true" });
      var titleEl = window.FOSS.dom.el("h3", { className: "card-title", text: title });
      var msgEl = window.FOSS.dom.el("p", { className: "desc", text: message });

      var inputEl = window.FOSS.dom.el("input", {
        type: "text",
        className: "input",
        value: defaultValue,
        "data-testid": "modal-prompt-input"
      });
      inputEl.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
          e.stopPropagation();
          cleanup();
          resolve(inputEl.value);
        } else if (e.key === "Escape") {
          e.stopPropagation();
          cleanup();
          resolve(null);
        } else {
          e.stopPropagation();
        }
      });

      var confirmBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary",
        text: confirmText,
        "data-testid": "modal-prompt-confirm-btn",
        onClick: function () {
          cleanup();
          resolve(inputEl.value);
        }
      });

      var cancelBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary",
        text: cancelText,
        "data-testid": "modal-prompt-cancel-btn",
        onClick: function () {
          cleanup();
          resolve(null);
        }
      });

      var actionsEl = window.FOSS.dom.el("div", { className: "row end" }, [cancelBtn, confirmBtn]);
      var modalEl = window.FOSS.dom.el("div", {
        className: "modal",
        role: "dialog",
        "aria-modal": "true",
        "data-testid": "prompt-modal"
      }, [titleEl, msgEl, inputEl, actionsEl]);

      function cleanup() {
        var idx = activeCleanups.indexOf(cleanup);
        if (idx >= 0) activeCleanups.splice(idx, 1);
        if (activeCleanups.length === 0) h.classList.remove("active");
        if (scrim.parentElement) scrim.parentElement.removeChild(scrim);
        if (modalEl.parentElement) modalEl.parentElement.removeChild(modalEl);
        document.removeEventListener("keydown", onKeyDown);
      }

      function onKeyDown(e) {
        if (e.key === "Escape") {
          cleanup();
          resolve(null);
        } else if (e.key === "Enter") {
          cleanup();
          resolve(inputEl.value);
        }
      }

      activeCleanups.push(cleanup);
      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
      inputEl.focus();
    });
  }

  function custom(options) {
    var opts = options || {};
    var confirmText = opts.confirmText || "Save";
    var cancelText = opts.cancelText || "Cancel";
    var testid = opts.testid || "custom-modal";

    return new Promise(function (resolve) {
      var h = getHost();
      if (!h) {
        resolve(false);
        return;
      }

      var scrim = window.FOSS.dom.el("div", { className: "scrim", "data-overlay": "true" });
      var titleEl = window.FOSS.dom.el("h3", { className: "card-title", text: opts.title || "" });
      var bodyEl = window.FOSS.dom.el("div", { className: "modal-body stack" }, [opts.content]);

      var confirmBtn = window.FOSS.dom.el("button", {
        className: "btn btn-primary",
        text: confirmText,
        "data-testid": testid + "-confirm",
        onClick: function () {
          if (opts.onConfirm) opts.onConfirm();
          cleanup();
          resolve(true);
        }
      });
      var cancelBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary",
        text: cancelText,
        "data-testid": testid + "-cancel",
        onClick: function () {
          cleanup();
          resolve(false);
        }
      });

      var actionsEl = window.FOSS.dom.el("div", { className: "row end" }, [cancelBtn, confirmBtn]);
      var modalEl = window.FOSS.dom.el("div", {
        className: "modal",
        role: "dialog",
        "aria-modal": "true",
        "data-testid": testid
      }, [titleEl, bodyEl, actionsEl]);

      function cleanup() {
        var idx = activeCleanups.indexOf(cleanup);
        if (idx >= 0) activeCleanups.splice(idx, 1);
        if (activeCleanups.length === 0) h.classList.remove("active");
        if (scrim.parentElement) scrim.parentElement.removeChild(scrim);
        if (modalEl.parentElement) modalEl.parentElement.removeChild(modalEl);
        document.removeEventListener("keydown", onKeyDown);
      }

      function onKeyDown(e) {
        if (e.key === "Escape") {
          cleanup();
          resolve(false);
        }
      }

      scrim.addEventListener("click", function () {
        cleanup();
        resolve(false);
      });

      activeCleanups.push(cleanup);
      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
      confirmBtn.focus();
    });
  }

  window.FOSS.dialogs = {
    confirm: confirm,
    alert: alert,
    prompt: prompt,
    custom: custom,
    toast: function (msg, type) {
      if (window.FOSS.toast && window.FOSS.toast.show) {
        window.FOSS.toast.show(msg, type);
      }
    },
    closeAll: closeAll
  };
  window.FOSS.confirm = confirm;
})();
