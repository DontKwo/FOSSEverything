// Home view with hero search, categorized workspace tiles, and recent files.
window.FOSS = window.FOSS || {};

(function () {
  var selectedCategory = "All";
  var favoritesOnly = false;
  var searchQuery = "";
  var allApps = [];

  function render(container) {
    container.innerHTML = "";
    var page = window.FOSS.dom.el("div", { className: "page home-page", "data-testid": "home-view" });

    // Hero section
    var heroTitle = window.FOSS.dom.el("h1", {
      className: "home-hero-title",
      text: "FOSSEverything Workbench"
    });
    var heroSub = window.FOSS.dom.el("p", {
      className: "home-hero-sub",
      text: "Free, local-first offline Swiss Army knife for documents, media, data, and daily utilities."
    });
    var hero = window.FOSS.dom.el("div", { className: "home-hero stack-sm" }, [heroTitle, heroSub]);
    page.appendChild(hero);

    // Search bar
    var searchInput = window.FOSS.dom.el("input", {
      type: "search",
      className: "home-search-input",
      placeholder: "Search tools, keywords, or format extensions...",
      "data-testid": "home-search-input",
      "aria-label": "Search tools",
      value: searchQuery,
      onInput: function (e) {
        searchQuery = e.target.value.toLowerCase().trim();
        updateGrid();
      }
    });
    page.appendChild(searchInput);

    // Filters row: Category chips and Favorites-only switch
    var cats = ["All", "Documents", "Visuals", "Media", "Utilities", "Data"];
    var chipBtns = cats.map(function (c) {
      var isAct = selectedCategory === c;
      return window.FOSS.dom.el("button", {
        className: "chip " + (isAct ? "active" : ""),
        "aria-pressed": isAct ? "true" : "false",
        "data-testid": "home-filter-" + c.toLowerCase(),
        text: c,
        onClick: function () {
          selectedCategory = c;
          chipBtns.forEach(function (btn) {
            var active = btn.textContent === c;
            btn.className = "chip " + (active ? "active" : "");
            btn.setAttribute("aria-pressed", active ? "true" : "false");
          });
          updateGrid();
        }
      });
    });

    var favCheckbox = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: favoritesOnly,
      "data-testid": "home-favorites-toggle",
      onChange: function (e) {
        favoritesOnly = e.target.checked;
        updateGrid();
      }
    });
    var favSlider = window.FOSS.dom.el("span", { className: "switch-slider" });
    var favLabel = window.FOSS.dom.el("label", { className: "switch", "data-testid": "home-fav-switch-label" }, [
      favCheckbox,
      favSlider,
      window.FOSS.dom.el("span", { text: "Favorites only" })
    ]);

    var filtersRow = window.FOSS.dom.el("div", { className: "row" }, chipBtns.concat([favLabel]));
    page.appendChild(filtersRow);

    // Grid container
    var grid = window.FOSS.dom.el("div", { className: "grid-auto home-grid", "data-testid": "home-apps-grid" });
    page.appendChild(grid);

    // Recent files and outputs section
    var recentsContainer = window.FOSS.dom.el("div", { className: "stack home-recents", "data-testid": "home-recents-section" });
    page.appendChild(recentsContainer);

    container.appendChild(page);

    // Load apps and render grid
    window.FOSS.api("get_apps", {}).then(function (res) {
      if (res && res.ok && res.apps) {
        allApps = res.apps;
        updateGrid();
      }
    });

    loadRecents(recentsContainer);
  }

  function updateGrid() {
    var grid = document.querySelector(".home-grid");
    if (!grid) return;
    grid.innerHTML = "";

    var filtered = allApps.filter(function (app) {
      if (selectedCategory !== "All" && app.category !== selectedCategory) return false;
      if (favoritesOnly && !window.FOSS.store.isFavorite(app.id)) return false;
      if (searchQuery) {
        var matchName = app.name.toLowerCase().indexOf(searchQuery) !== -1;
        var matchDesc = app.description.toLowerCase().indexOf(searchQuery) !== -1;
        var matchKw = app.keywords && app.keywords.some(function (k) { return k.toLowerCase().indexOf(searchQuery) !== -1; });
        if (!matchName && !matchDesc && !matchKw) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      grid.appendChild(window.FOSS.dom.el("div", {
        className: "empty",
        "data-testid": "home-empty-search"
      }, [
        window.FOSS.icons.el("search", 32),
        window.FOSS.dom.el("h3", { className: "empty-title", text: "No matching tools found" }),
        window.FOSS.dom.el("p", { className: "empty-desc", text: "Try clearing search filters or choosing another category." })
      ]));
      return;
    }

    filtered.forEach(function (app) {
      var isFav = window.FOSS.store.isFavorite(app.id);

      var starBtn = window.FOSS.dom.el("button", {
        className: "btn btn-icon btn-ghost btn-sm tile-fav-btn",
        "aria-label": isFav ? "Unfavorite " + app.name : "Favorite " + app.name,
        title: isFav ? "Remove favorite" : "Add to favorites",
        "data-testid": "home-fav-" + app.id,
        onClick: function (e) {
          e.stopPropagation();
          var nowFav = window.FOSS.store.toggleFavorite(app.id);
          starBtn.innerHTML = window.FOSS.icons.svg(nowFav ? "star_filled" : "star", 16);
          if (favoritesOnly) updateGrid();
          window.FOSS.router.renderTopbar();
        }
      }, [window.FOSS.icons.el(isFav ? "star_filled" : "star", 16)]);

      var imgEl = window.FOSS.dom.el("img", {
        className: "tile-img",
        src: app.artwork_url || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='90'><rect width='100%' height='100%' fill='%231a2540'/></svg>",
        alt: app.name,
        loading: "lazy"
      });

      var tileHead = window.FOSS.dom.el("div", { className: "row tile-head" }, [
        window.FOSS.dom.el("h3", { className: "tile-title", text: app.name }),
        starBtn
      ]);

      var tileDesc = window.FOSS.dom.el("p", {
        className: "tile-desc",
        text: app.description,
        title: app.description,
        "data-truncate-ok": "true"
      });

      var tile = window.FOSS.dom.el("div", {
        className: "card app-tile",
        role: "button",
        tabindex: "0",
        "data-testid": "home-tile-" + app.id,
        onClick: function () {
          window.FOSS.router.open(app.id);
        },
        onKeyDown: function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            window.FOSS.router.open(app.id);
          }
        }
      }, [imgEl, tileHead, tileDesc]);

      grid.appendChild(tile);
    });
  }

  function loadRecents(container) {
    window.FOSS.api("get_recents", {}).then(function (res) {
      if (!res || !res.ok) return;
      var files = res.recent_files || [];
      var outputs = res.recent_outputs || [];
      if (files.length === 0 && outputs.length === 0) return;

      container.innerHTML = "";
      var recentsCard = window.FOSS.dom.el("div", { className: "card home-recents-card" });
      var title = window.FOSS.dom.el("h2", { className: "card-title", text: "Recent Files & Outputs" });
      recentsCard.appendChild(title);

      var listEl = window.FOSS.dom.el("div", { className: "file-list" });
      files.slice(0, 5).forEach(function (f) {
        var openBtn = window.FOSS.dom.el("button", {
          className: "btn btn-sm btn-secondary",
          text: "Open",
          "data-testid": "recent-open-btn",
          onClick: function () {
            window.FOSS.api("open_path", { path: f.path });
          }
        });
        var item = window.FOSS.dom.el("div", { className: "file-list-item" }, [
          window.FOSS.dom.el("div", { className: "stack-sm" }, [
            window.FOSS.dom.el("span", { className: "picker-name", text: f.name, title: f.name, "data-truncate-ok": "true" }),
            window.FOSS.dom.el("span", { className: "picker-path", text: f.folder, title: f.folder, "data-truncate-ok": "true" })
          ]),
          openBtn
        ]);
        listEl.appendChild(item);
      });
      recentsCard.appendChild(listEl);
      container.appendChild(recentsCard);
    });
  }

  window.FOSS.home = {
    render: render
  };
})();

