// UI Audit script running in browser context.
window.__audit = function () {
  var findings = [];

  function getSelector(el) {
    if (!el || el.nodeType !== 1) return "";
    var testId = el.getAttribute("data-testid");
    if (testId) return '[data-testid="' + testId + '"]';
    var path = [];
    var curr = el;
    while (curr && curr.nodeType === 1 && path.length < 4) {
      var name = curr.tagName.toLowerCase();
      if (curr.id) {
        path.unshift("#" + curr.id);
        break;
      }
      var cls = curr.className && typeof curr.className === "string"
        ? "." + curr.className.trim().split(/\s+/).slice(0, 2).join(".")
        : "";
      var parent = curr.parentElement;
      if (parent) {
        var index = Array.prototype.indexOf.call(parent.children, curr) + 1;
        path.unshift(name + cls + ":nth-child(" + index + ")");
      } else {
        path.unshift(name + cls);
      }
      curr = parent;
    }
    return path.join(" > ");
  }

  function isVisible(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.hasAttribute("hidden")) return false;
    var style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility !== "visible") return false;
    if (parseFloat(style.opacity || "1") <= 0.05) return false;
    var rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    return true;
  }

  function addFinding(id, severity, el, message) {
    var rect = el && el.getBoundingClientRect ? el.getBoundingClientRect() : { top: 0, left: 0, width: 0, height: 0 };
    findings.push({
      id: id,
      severity: severity,
      selector: getSelector(el),
      message: message,
      rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height }
    });
  }

  // A1: Window / document scrolling
  var root = document.documentElement;
  if (root.scrollWidth > window.innerWidth + 1) {
    addFinding("A1", "error", root, "Root element horizontal scrollbar active (" + root.scrollWidth + " > " + window.innerWidth + ")");
  }
  if (root.scrollHeight > window.innerHeight + 1) {
    addFinding("A1", "error", root, "Root element vertical scrollbar active (" + root.scrollHeight + " > " + window.innerHeight + ")");
  }

  var allElements = Array.prototype.slice.call(document.querySelectorAll("*"));
  var visibleElements = allElements.filter(isVisible);

  // Collect border rects for pixel checks
  var borderRects = [];
  visibleElements.forEach(function (el) {
    var style = window.getComputedStyle(el);
    var bw = parseFloat(style.borderTopWidth || "0");
    if (bw > 0 && style.borderTopStyle !== "none") {
      var r = el.getBoundingClientRect();
      borderRects.push({ top: r.top, left: r.left, width: r.width, height: r.height });
    }
  });
  document.body.dataset.borderRects = JSON.stringify(borderRects);

  var rootFontSize = parseFloat(window.getComputedStyle(document.documentElement).fontSize || "16");

  // Check interactive elements
  var modalHost = document.getElementById("modal-host");
  var paletteHost = document.getElementById("palette-host");
  var modalActive = modalHost && modalHost.classList.contains("active");
  var paletteActive = paletteHost && paletteHost.children.length > 0;

  var interactiveSelector = 'button, a[href], input, select, textarea, summary, [role="button"], [role="tab"], [tabindex="0"]';
  var interactiveElements = visibleElements.filter(function (el) {
    if (!el.matches(interactiveSelector) || el.disabled) return false;
    if (modalActive && !modalHost.contains(el)) return false;
    if (paletteActive && !paletteHost.contains(el)) return false;
    return true;
  });

  // A2: Overflow-x visible spillage
  visibleElements.forEach(function (el) {
    var style = window.getComputedStyle(el);
    if (style.overflowX === "visible" && (el.children.length > 0 || (el.textContent && el.textContent.trim().length > 0))) {
      if (el.scrollWidth > el.clientWidth + 1) {
        addFinding("A2", "error", el, "Content spills horizontally out of element (" + el.scrollWidth + " > " + el.clientWidth + ")");
      }
    }
  });

  // A4: Containment in bordered/background cards
  visibleElements.forEach(function (parent) {
    if (parent.tagName === "BODY" || parent.tagName === "HTML" || parent.classList.contains("app")) return;
    var style = window.getComputedStyle(parent);
    var hasBorder = parseFloat(style.borderTopWidth || "0") > 0 && style.borderTopStyle !== "none";
    var hasBg = style.backgroundColor && style.backgroundColor !== "rgba(0, 0, 0, 0)" && style.backgroundColor !== "transparent";
    if (hasBorder || hasBg) {
      var pRect = parent.getBoundingClientRect();
      for (var i = 0; i < parent.children.length; i++) {
        var child = parent.children[i];
        if (!isVisible(child) || child.hasAttribute("data-overlay")) continue;
        var cStyle = window.getComputedStyle(child);
        if (cStyle.position === "static" || cStyle.position === "relative") {
          var cRect = child.getBoundingClientRect();
          if (cRect.left < pRect.left - 2 || cRect.right > pRect.right + 2 || cRect.top < pRect.top - 2 || cRect.bottom > pRect.bottom + 2) {
            addFinding("A4", "error", child, "child spills out of card");
          }
        }
      }
    }
  });

  // A5: Sibling overlap
  var checkedSiblingPairs = new Set();
  visibleElements.forEach(function (el) {
    var parent = el.parentElement;
    if (!parent) return;
    for (var i = 0; i < parent.children.length; i++) {
      var s1 = parent.children[i];
      if (!isVisible(s1) || s1.hasAttribute("data-overlay")) continue;
      var style1 = window.getComputedStyle(s1);
      if (style1.position !== "static" && style1.position !== "relative") continue;
      var r1 = s1.getBoundingClientRect();
      if (r1.width <= 0 || r1.height <= 0) continue;

      for (var j = i + 1; j < parent.children.length; j++) {
        var s2 = parent.children[j];
        if (!isVisible(s2) || s2.hasAttribute("data-overlay")) continue;
        var style2 = window.getComputedStyle(s2);
        if (style2.position !== "static" && style2.position !== "relative") continue;
        var r2 = s2.getBoundingClientRect();
        if (r2.width <= 0 || r2.height <= 0) continue;

        var key = s1 === s2 ? "" : (s1.dataset.testid || "") + ":" + (s2.dataset.testid || "");
        if (checkedSiblingPairs.has(key)) continue;
        checkedSiblingPairs.add(key);

        var xOverlap = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left));
        var yOverlap = Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
        var area = xOverlap * yOverlap;
        if (area > 4) {
          addFinding("A5", "error", s1, "In-flow siblings overlap with area " + Math.round(area) + "px^2");
        }
      }
    }
  });

  // A6: Interactive overlap
  for (var i = 0; i < interactiveElements.length; i++) {
    var el1 = interactiveElements[i];
    var r1 = el1.getBoundingClientRect();
    for (var j = i + 1; j < interactiveElements.length; j++) {
      var el2 = interactiveElements[j];
      if (el1.contains(el2) || el2.contains(el1)) continue;
      var r2 = el2.getBoundingClientRect();
      var xOverlap = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left));
      var yOverlap = Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
      var area = xOverlap * yOverlap;
      if (area > 2) {
        addFinding("A6", "error", el1, "Interactive elements intersect by " + Math.round(area) + "px^2 with " + getSelector(el2));
      }
    }
  }

  // A7: Obscured control
  interactiveElements.forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.right <= 0 || r.left >= window.innerWidth || r.bottom <= 0 || r.top >= window.innerHeight) return;
    var cx = Math.floor(r.left + r.width / 2);
    var cy = Math.floor(r.top + r.height / 2);
    if (cx < 0 || cx >= window.innerWidth || cy < 0 || cy >= window.innerHeight) return;
    var hit = document.elementFromPoint(cx, cy);
    if (hit && !el.contains(hit) && hit !== el && !el.hasAttribute("data-obscure-ok")) {
      addFinding("A7", "error", el, "Interactive element obscured at center by " + getSelector(hit));
    }
  });

  // A8: Viewport escape for fixed elements
  visibleElements.forEach(function (el) {
    var style = window.getComputedStyle(el);
    if (style.position === "fixed") {
      var r = el.getBoundingClientRect();
      if (r.left < -1 || r.top < -1 || r.right > window.innerWidth + 1 || r.bottom > window.innerHeight + 1) {
        addFinding("A8", "error", el, "Fixed element escapes viewport bounds");
      }
    }
  });

  // A9: Text truncation
  visibleElements.forEach(function (el) {
    var style = window.getComputedStyle(el);
    var overflowX = style.overflowX;
    var textOverflow = style.textOverflow;
    var isClipped = overflowX === "hidden" || overflowX === "clip" || textOverflow === "ellipsis";
    if (isClipped && el.scrollWidth > el.clientWidth + 1) {
      if (!el.hasAttribute("data-truncate-ok") || !el.getAttribute("title")) {
        addFinding("A9", "error", el, "Text truncated without data-truncate-ok and title attribute");
      }
    }
  });

  // A10: Label wrap
  var labelCandidates = visibleElements.filter(function (el) {
    return el.matches('button, [role="tab"], .nav-item, .chip, .badge, th, label');
  });
  labelCandidates.forEach(function (el) {
    if (el.hasAttribute("data-wrap-ok")) return;
    for (var i = 0; i < el.childNodes.length; i++) {
      var node = el.childNodes[i];
      if (node.nodeType === 3 && node.textContent.trim().length > 0) {
        var range = document.createRange();
        range.selectNodeContents(node);
        var rects = range.getClientRects();
        var tops = new Set();
        for (var k = 0; k < rects.length; k++) {
          tops.add(Math.round(rects[k].top));
        }
        if (tops.size > 1) {
          addFinding("A10", "error", el, "Label text wraps onto multiple lines (" + tops.size + " lines)");
          break;
        }
      }
    }
  });

  // A12: Minimum target size
  interactiveElements.forEach(function (el) {
    if (el.tagName === "A" && el.className.indexOf("btn") === -1) return;
    if (el.type === "checkbox" || el.type === "radio") return;
    var minSize = el.hasAttribute("data-dense") ? rootFontSize * 1.25 : rootFontSize * 2.0;
    var r = el.getBoundingClientRect();
    if (r.width < minSize - 1 || r.height < minSize - 1) {
      addFinding("A12", "error", el, "Interactive element size (" + Math.round(r.width) + "x" + Math.round(r.height) + ") below minimum " + Math.round(minSize) + "px");
    }
  });

  // A13: Spacing between interactive siblings
  visibleElements.forEach(function (parent) {
    if (parent.classList.contains("btn-group") || parent.classList.contains("segmented")) return;
    var buttons = [];
    for (var i = 0; i < parent.children.length; i++) {
      var c = parent.children[i];
      if (c.matches("button, .btn") && isVisible(c)) buttons.push(c);
    }
    for (var i = 0; i < buttons.length - 1; i++) {
      var b1 = buttons[i].getBoundingClientRect();
      var b2 = buttons[i + 1].getBoundingClientRect();
      var sameRow = Math.abs(b1.top - b2.top) < 6;
      if (sameRow) {
        var gap = b2.left - b1.right;
        if (gap < 4 && gap >= -1) {
          addFinding("A13", "error", buttons[i], "Adjacent interactive buttons have gap " + Math.round(gap) + "px (< 4px)");
        }
      }
    }
  });

  // Helper for color parsing and contrast
  function parseRgba(str) {
    if (!str) return [0, 0, 0, 1];
    var mColor = str.match(/color\(srgb\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)(?:\s*\/\s*([0-9.]+))?\)/);
    if (mColor) {
      return [
        parseFloat(mColor[1]) * 255.0,
        parseFloat(mColor[2]) * 255.0,
        parseFloat(mColor[3]) * 255.0,
        mColor[4] !== undefined ? parseFloat(mColor[4]) : 1
      ];
    }
    var m = str.match(/rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)/);
    if (!m) return [0, 0, 0, 1];
    return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), m[4] !== undefined ? parseFloat(m[4]) : 1];
  }

  function getLuminance(rgb) {
    var a = rgb.slice(0, 3).map(function (v) {
      v = v / 255.0;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
  }

  function getContrast(fg, bg) {
    var l1 = getLuminance(fg);
    var l2 = getLuminance(bg);
    var lighter = Math.max(l1, l2);
    var darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  // A15 & A16: Text size and contrast
  visibleElements.forEach(function (el) {
    if (el.hasAttribute("data-decorative") || el.disabled) return;
    var hasOwnText = false;
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3 && el.childNodes[i].textContent.trim().length > 0) {
        hasOwnText = true;
        break;
      }
    }
    if (!hasOwnText) return;

    var style = window.getComputedStyle(el);
    var fontSize = parseFloat(style.fontSize || "16");
    if (fontSize < 11) {
      addFinding("A15", "error", el, "Text font-size " + fontSize + "px is under 11px");
    }

    var fgColor = parseRgba(style.color);
    var curr = el;
    var bg = [255, 255, 255, 1];
    var bgFound = false;
    while (curr && curr.nodeType === 1) {
      var cStyle = window.getComputedStyle(curr);
      if (cStyle.backgroundImage && cStyle.backgroundImage !== "none") {
        bgFound = true;
        break;
      }
      var cBg = parseRgba(cStyle.backgroundColor);
      if (cBg[3] > 0.9) {
        bg = cBg;
        bgFound = true;
        break;
      }
      curr = curr.parentElement;
    }

    if (bgFound && fgColor[3] >= 0.5) {
      var ratio = getContrast(fgColor, bg);
      var fontWeight = parseInt(style.fontWeight || "400", 10);
      var isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
      var requiredRatio = isLarge ? 3.0 : 4.5;
      if (ratio < requiredRatio - 0.1) {
        addFinding("A16", "error", el, "Text contrast ratio " + ratio.toFixed(2) + " below required " + requiredRatio);
      }
    }
  });

  // A17: Zero-size control
  interactiveElements.forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) {
      addFinding("A17", "error", el, "Interactive element has zero width or height");
    }
  });

  // A18: Broken media
  visibleElements.forEach(function (el) {
    if (el.tagName === "IMG") {
      if (el.complete && el.naturalWidth === 0 && !el.hasAttribute("data-lazy")) {
        addFinding("A18", "error", el, "Image failed to load or has 0 natural width");
      }
    } else if (el.tagName === "CANVAS") {
      var r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) {
        addFinding("A18", "error", el, "Canvas element has zero rendered dimensions");
      }
    }
  });

  // A19: Missing test id inside view root
  var viewRoot = document.getElementById("view-root");
  if (viewRoot) {
    interactiveElements.forEach(function (el) {
      if (viewRoot.contains(el) && !el.hasAttribute("data-testid") && !el.closest("[data-testid]")) {
        addFinding("A19", "error", el, "Interactive element inside view root missing data-testid");
      }
    });
  }

  // A20: Missing accessible name
  interactiveElements.forEach(function (el) {
    var text = el.textContent ? el.textContent.trim() : "";
    var ariaLabel = el.getAttribute("aria-label");
    var ariaLabelledby = el.getAttribute("aria-labelledby");
    var title = el.getAttribute("title");
    var hasLabel = false;
    if (el.id) {
      hasLabel = !!document.querySelector('label[for="' + el.id + '"]');
    }
    if (!text && !ariaLabel && !ariaLabelledby && !title && !hasLabel) {
      addFinding("A20", "error", el, "Interactive element has no accessible name");
    }
  });

  // A22: Unintended horizontal scrollbar
  visibleElements.forEach(function (el) {
    var style = window.getComputedStyle(el);
    if ((style.overflowX === "auto" || style.overflowX === "scroll") && el.scrollWidth > el.clientWidth + 1) {
      if (!el.classList.contains("scroll-x") && !el.classList.contains("table-wrap") && !el.classList.contains("tabs")) {
        addFinding("A22", "error", el, "Inner horizontal scrollbar on element without .scroll-x or .table-wrap");
      }
    }
  });

  return findings;
};

