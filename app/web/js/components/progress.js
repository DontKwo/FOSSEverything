// Progress bar component for asynchronous job tracking.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function progress(opts) {
    opts = opts || {};
    var testid = opts.testid || "progress";
    var percent = opts.percent || 0;
    var message = opts.message || "";
    var onCancel = opts.onCancel;

    var bar = window.FOSS.dom.el("div", {
      className: "progress-bar",
      "data-testid": testid + "-bar"
    });
    bar.style.setProperty("--progress-pct", percent + "%");

    var track = window.FOSS.dom.el("div", { className: "progress-track" }, [bar]);

    var msgEl = window.FOSS.dom.el("span", { text: message });
    var pctEl = window.FOSS.dom.el("span", { text: Math.round(percent) + "%" });
    var textLine = window.FOSS.dom.el("div", { className: "progress-text" }, [msgEl, pctEl]);

    var children = [track, textLine];

    if (onCancel) {
      var cancelBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        text: "Cancel",
        type: "button",
        "data-testid": testid + "-cancel",
        onClick: onCancel
      });
      children.push(cancelBtn);
    }

    var wrap = window.FOSS.dom.el("div", {
      className: "progress",
      "data-testid": testid,
      role: "progressbar",
      "aria-valuenow": String(percent),
      "aria-valuemin": "0",
      "aria-valuemax": "100"
    }, children);

    function update(newPct, newMsg) {
      percent = Math.max(0, Math.min(100, newPct || 0));
      bar.style.setProperty("--progress-pct", percent + "%");
      wrap.setAttribute("aria-valuenow", String(percent));
      pctEl.textContent = Math.round(percent) + "%";
      if (newMsg !== undefined) {
        message = newMsg;
        msgEl.textContent = message;
      }
    }

    return {
      el: wrap,
      update: update
    };
  }

  window.FOSS.components.progress = progress;
})();
