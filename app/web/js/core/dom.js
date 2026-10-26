// DOM helper utilities and element creation functions.
window.FOSS = window.FOSS || {};

(function () {
  function el(tag, attrs, children) {
    var element = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) {
          var v = attrs[k];
          if (k === "className") {
            element.className = v;
          } else if (k === "text") {
            element.textContent = v;
          } else if (k === "html") {
            element.innerHTML = v;
          } else if (k.indexOf("on") === 0 && typeof v === "function") {
            element.addEventListener(k.substring(2).toLowerCase(), v);
          } else if (v !== null && v !== undefined && v !== false) {
            element.setAttribute(k, v === true ? "" : v);
          }
        }
      }
    }
    if (children) {
      if (!Array.isArray(children)) children = [children];
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (!child) continue;
        if (typeof child === "string" || typeof child === "number") {
          element.appendChild(document.createTextNode(String(child)));
        } else if (child.nodeType) {
          element.appendChild(child);
        }
      }
    }
    return element;
  }

  function qs(selector, parent) {
    return (parent || document).querySelector(selector);
  }

  function qsa(selector, parent) {
    return Array.prototype.slice.call((parent || document).querySelectorAll(selector));
  }

  function on(target, event, handler) {
    if (target) {
      target.addEventListener(event, handler);
    }
  }

  // Prevent mouse wheel from inadvertently altering number inputs
  document.addEventListener("wheel", function (e) {
    if (document.activeElement && document.activeElement.type === "number") {
      document.activeElement.blur();
    }
  }, { passive: true });

  window.FOSS.dom = {
    el: el,
    qs: qs,
    qsa: qsa,
    on: on
  };
})();

