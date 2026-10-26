// Modal confirmation and prompt dialogs.
window.FOSS = window.FOSS || {};

(function () {
  var host = null;

  function getHost() {
    if (!host) {
      host = document.getElementById("modal-host");
    }
    return host;
  }

  function confirm(options) {
    var opts = options || {};
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
        h.classList.remove("active");
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

      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
      confirmBtn.focus();
    });
  }

  window.FOSS.dialogs = {
    confirm: confirm
  };
  window.FOSS.confirm = confirm;
})();

