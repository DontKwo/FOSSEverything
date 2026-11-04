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

  window.FOSS.dialogs = {
    confirm: confirm,
    alert: alert,
    toast: function (msg, type) {
      if (window.FOSS.toast && window.FOSS.toast.show) {
        window.FOSS.toast.show(msg, type);
      }
    },
    closeAll: closeAll
  };
  window.FOSS.confirm = confirm;
})();
