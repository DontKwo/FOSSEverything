// Command palette modal and quick tool search.
window.FOSS = window.FOSS || {};

(function () {
  var host = null;
  var isOpen = false;
  var selectedIndex = 0;
  var currentResults = [];

  function getHost() {
    if (!host) {
      host = document.getElementById("palette-host");
    }
    return host;
  }

  function open() {
    if (isOpen) return;
    isOpen = true;
    var h = getHost();
    if (!h) return;
    h.innerHTML = "";

    var scrim = window.FOSS.dom.el("div", {
      className: "scrim",
      "data-overlay": "true",
      onClick: close
    });

    var input = window.FOSS.dom.el("input", {
      type: "text",
      className: "palette-input",
      placeholder: "Search tools, categories, actions... (Esc to close)",
      "data-testid": "palette-search-input",
      "aria-label": "Search tools",
      onInput: function (e) {
        performSearch(e.target.value);
      },
      onKeyDown: handleKeyDown
    });

    var resultsList = window.FOSS.dom.el("div", {
      className: "palette-results scroll-y",
      "data-testid": "palette-results-list"
    });

    var modal = window.FOSS.dom.el("div", {
      className: "modal palette-modal",
      role: "dialog",
      "aria-modal": "true",
      "data-testid": "command-palette-modal"
    }, [input, resultsList]);

    h.appendChild(scrim);
    h.appendChild(modal);

    selectedIndex = 0;
    performSearch("");
    setTimeout(function () { input.focus(); }, 50);
  }

  function close() {
    var h = getHost();
    if (h) h.innerHTML = "";
    isOpen = false;
  }

  function performSearch(query) {
    window.FOSS.api("search_tools", { query: query }).then(function (res) {
      currentResults = (res && res.ok && res.results) || [];
      renderResults();
    });
  }

  function renderResults() {
    var resultsList = document.querySelector(".palette-results");
    if (!resultsList) return;
    resultsList.innerHTML = "";

    if (currentResults.length === 0) {
      var emptyEl = window.FOSS.dom.el("div", {
        className: "palette-empty",
        text: "No matching tools or actions found."
      });
      resultsList.appendChild(emptyEl);
      return;
    }

    currentResults.forEach(function (r, idx) {
      var isSel = idx === selectedIndex;
      var itemEl = window.FOSS.dom.el("div", {
        className: "palette-item " + (isSel ? "selected" : ""),
        role: "button",
        tabindex: "0",
        "data-testid": "palette-result-" + r.id,
        onClick: function () {
          selectItem(r);
        }
      }, [
        window.FOSS.dom.el("div", { className: "palette-item-left" }, [
          window.FOSS.icons.el("file", 18),
          window.FOSS.dom.el("div", { className: "stack-sm" }, [
            window.FOSS.dom.el("span", { className: "palette-item-title", text: r.title }),
            window.FOSS.dom.el("span", { className: "palette-item-desc", text: r.description || "" })
          ])
        ]),
        window.FOSS.dom.el("span", { className: "badge", text: r.category })
      ]);
      resultsList.appendChild(itemEl);
    });
  }

  function handleKeyDown(e) {
    if (e.key === "Escape") {
      close();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (currentResults.length > 0) {
        selectedIndex = (selectedIndex + 1) % currentResults.length;
        renderResults();
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (currentResults.length > 0) {
        selectedIndex = (selectedIndex - 1 + currentResults.length) % currentResults.length;
        renderResults();
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (currentResults[selectedIndex]) {
        selectItem(currentResults[selectedIndex]);
      }
    }
  }

  function selectItem(r) {
    close();
    window.FOSS.router.open(r.id);
  }

  window.FOSS.palette = {
    open: open,
    close: close,
    isOpen: function () { return isOpen; }
  };
})();

