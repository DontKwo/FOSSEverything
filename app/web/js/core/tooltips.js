// Centralized tooltips layer.
window.FOSS = window.FOSS || {};

(function () {
  var tooltipsMap = {};
  var tooltipEl = null;
  var hoverTimer = null;
  var activeTarget = null;

  function init() {
    window.FOSS.api("get_tooltips", {}).then(function (res) {
      if (res && res.ok && res.tooltips) {
        tooltipsMap = res.tooltips;
      }
    });

    document.addEventListener("mouseover", onMouseOver);
    document.addEventListener("mouseout", onMouseOut);
  }

  function getTooltipHost() {
    var host = document.getElementById("tooltip-host");
    if (!host) {
      host = document.body;
    }
    return host;
  }

  function showTooltip(target, text) {
    hideTooltip();
    var host = getTooltipHost();
    tooltipEl = window.FOSS.dom.el("div", {
      className: "tooltip",
      role: "tooltip",
      text: text,
      "data-overlay": "true"
    });
    host.appendChild(tooltipEl);

    var r = target.getBoundingClientRect();
    var tipRect = tooltipEl.getBoundingClientRect();
    var top = r.bottom + 8;
    var left = r.left + (r.width - tipRect.width) / 2;

    if (top + tipRect.height > window.innerHeight - 8) {
      top = r.top - tipRect.height - 8;
    }
    if (left < 8) left = 8;
    if (left + tipRect.width > window.innerWidth - 8) {
      left = window.innerWidth - tipRect.width - 8;
    }

    tooltipEl.style.transform = "translate(" + Math.round(left) + "px, " + Math.round(top) + "px)";
  }

  function hideTooltip() {
    if (tooltipEl && tooltipEl.parentElement) {
      tooltipEl.parentElement.removeChild(tooltipEl);
    }
    tooltipEl = null;
    activeTarget = null;
    if (hoverTimer) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
  }

  function onMouseOver(e) {
    var target = e.target.closest("[data-tip], [title]");
    if (!target || target === activeTarget) return;

    hideTooltip();
    activeTarget = target;

    var tipKey = target.getAttribute("data-tip");
    var tipText = (tipKey && tooltipsMap[tipKey]) || target.getAttribute("title");
    if (!tipText) return;

    if (target.hasAttribute("title")) {
      target.dataset.originalTitle = target.getAttribute("title");
      target.removeAttribute("title");
    }

    hoverTimer = setTimeout(function () {
      if (activeTarget === target) {
        showTooltip(target, tipText);
      }
    }, 500);
  }

  function onMouseOut(e) {
    if (activeTarget && (!e.relatedTarget || !activeTarget.contains(e.relatedTarget))) {
      if (activeTarget.dataset.originalTitle) {
        activeTarget.setAttribute("title", activeTarget.dataset.originalTitle);
      }
      hideTooltip();
    }
  }

  window.FOSS.tooltips = {
    init: init,
    hide: hideTooltip
  };
})();

