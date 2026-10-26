// Toast notifications manager.
window.FOSS = window.FOSS || {};

(function () {
  var host = null;
  var MAX_TOASTS = 4;

  function getHost() {
    if (!host) {
      host = document.getElementById("toast-host");
    }
    return host;
  }

  function show(message, type, action) {
    var h = getHost();
    if (!h) return;

    while (h.children.length >= MAX_TOASTS) {
      h.removeChild(h.firstElementChild);
    }

    var tType = type || "info";
    var iconName = tType === "error" || tType === "warning" ? "alert" : (tType === "success" ? "check" : "file");
    var duration = tType === "error" ? 10000 : 5000;

    var iconNode = window.FOSS.dom.el("span", { className: "toast-icon" }, [window.FOSS.icons.el(iconName, 18)]);
    var textNode = window.FOSS.dom.el("span", { className: "toast-message", text: message });

    var children = [iconNode, textNode];
    if (action && action.label && action.onClick) {
      var actBtn = window.FOSS.dom.el("button", {
        className: "btn btn-sm btn-secondary",
        text: action.label,
        onClick: action.onClick,
        "data-testid": "toast-action-btn"
      });
      children.push(actBtn);
    }

    var closeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-sm btn-ghost",
      "aria-label": "Close notification",
      title: "Close",
      "data-testid": "toast-close-btn",
      onClick: function () {
        if (toastEl.parentElement) toastEl.parentElement.removeChild(toastEl);
      }
    }, [window.FOSS.icons.el("close", 14)]);
    children.push(closeBtn);

    var toastEl = window.FOSS.dom.el("div", {
      className: "toast " + tType,
      role: "alert",
      "data-testid": "toast-item"
    }, children);

    h.appendChild(toastEl);

    setTimeout(function () {
      if (toastEl.parentElement) {
        toastEl.parentElement.removeChild(toastEl);
      }
    }, duration);
  }

  window.FOSS.toast = {
    show: show
  };
})();

