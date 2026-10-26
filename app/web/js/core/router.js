// View router, tab manager, and application shell navigation.
window.FOSS = window.FOSS || {};

(function () {
  var registry = {};
  var activeView = null;
  var activeTab = null;
  var toolStates = {};

  function register(toolDef) {
    registry[toolDef.id] = toolDef;
    toolStates[toolDef.id] = toolStates[toolDef.id] || {};
  }

  function getRegisteredTools() {
    return Object.values(registry);
  }

  function renderSidebar() {
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) return;
    sidebar.innerHTML = "";

    // Brand
    var brand = window.FOSS.dom.el("div", { className: "row", style: undefined }, [
      window.FOSS.icons.el("home", 20),
      window.FOSS.dom.el("span", { className: "brand-name", text: "FOSSEverything", style: undefined })
    ]);
    var brandWrapper = window.FOSS.dom.el("div", {
      className: "sidebar-brand",
      role: "button",
      tabindex: "0",
      "data-testid": "nav-brand",
      "aria-label": "FOSSEverything Home",
      title: "FOSSEverything Home",
      onClick: function () {
        open("home");
      }
    }, [brand]);
    sidebar.appendChild(brandWrapper);

    // Nav items
    var navList = window.FOSS.dom.el("nav", { className: "sidebar-nav scroll-y" });

    // Home nav item
    var homeActive = activeView === "home";
    var homeItem = window.FOSS.dom.el("button", {
      className: "nav-item " + (homeActive ? "active" : ""),
      "data-testid": "nav-home",
      "aria-label": "All tools (Home)",
      title: "All tools (Home)",
      onClick: function () {
        open("home");
      }
    }, [
      window.FOSS.icons.el("home", 18),
      window.FOSS.dom.el("span", { className: "nav-label", text: "All Tools" })
    ]);
    navList.appendChild(homeItem);

    // Categories
    var categories = ["Documents", "Visuals", "Media", "Utilities", "Data"];
    categories.forEach(function (cat) {
      var toolsInCat = Object.values(registry).filter(function (t) {
        return t.category === cat;
      });
      if (toolsInCat.length === 0) return;

      var catHeading = window.FOSS.dom.el("div", { className: "nav-category", text: cat });
      navList.appendChild(catHeading);

      toolsInCat.forEach(function (t) {
        var isAct = activeView === t.id;
        var btn = window.FOSS.dom.el("button", {
          className: "nav-item " + (isAct ? "active" : ""),
          "data-testid": "nav-" + t.id,
          "aria-label": t.title,
          title: t.title,
          onClick: function () {
            open(t.id);
          }
        }, [
          window.FOSS.icons.el(t.icon || "file", 18),
          window.FOSS.dom.el("span", { className: "nav-label", text: t.navName || t.title })
        ]);
        navList.appendChild(btn);
      });
    });

    sidebar.appendChild(navList);

    // Bottom settings item
    var settingsActive = activeView === "settings";
    var settingsItem = window.FOSS.dom.el("button", {
      className: "nav-item sidebar-bottom " + (settingsActive ? "active" : ""),
      "data-testid": "nav-settings",
      "aria-label": "Settings",
      title: "Settings",
      onClick: function () {
        open("settings");
      }
    }, [
      window.FOSS.icons.el("settings", 18),
      window.FOSS.dom.el("span", { className: "nav-label", text: "Settings" })
    ]);
    sidebar.appendChild(settingsItem);
  }

  function renderTopbar() {
    var topbar = document.querySelector(".topbar");
    if (!topbar) return;
    topbar.innerHTML = "";

    // Left: Sidebar toggle and breadcrumb
    var toggleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-ghost btn-sm",
      "data-testid": "topbar-toggle-sidebar",
      "aria-label": "Toggle sidebar",
      title: "Toggle sidebar",
      onClick: function () {
        var appEl = document.querySelector(".app");
        if (appEl) {
          appEl.classList.toggle("sidebar-rail");
          var collapsed = appEl.classList.contains("sidebar-rail");
          window.FOSS.store.set("sidebar_collapsed", collapsed);
        }
      }
    }, [window.FOSS.icons.el("menu", 18)]);

    var viewTitle = "Home";
    if (activeView === "settings") {
      viewTitle = "Settings";
    } else if (registry[activeView]) {
      viewTitle = registry[activeView].title;
    }

    var breadcrumb = window.FOSS.dom.el("div", { className: "breadcrumb row" }, [
      window.FOSS.dom.el("span", { text: "FOSSEverything", className: "breadcrumb-root" }),
      window.FOSS.dom.el("span", { text: "/", className: "breadcrumb-sep" }),
      window.FOSS.dom.el("span", { text: viewTitle, className: "breadcrumb-current", title: viewTitle, "data-truncate-ok": "true" })
    ]);

    var leftGroup = window.FOSS.dom.el("div", { className: "row" }, [toggleBtn, breadcrumb]);
    topbar.appendChild(leftGroup);

    // Center / Right actions: Search button, Favorites bar, Theme switcher, Settings
    var searchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm topbar-search",
      "data-testid": "topbar-search-btn",
      "aria-label": "Search tools (Ctrl+K)",
      title: "Search tools (Ctrl+K)",
      onClick: function () {
        if (window.FOSS.palette) window.FOSS.palette.open();
      }
    }, [
      window.FOSS.icons.el("search", 16),
      window.FOSS.dom.el("span", { text: "Search tools... (Ctrl+K)" })
    ]);

    // Favorites bar
    var favs = window.FOSS.store.get("favorites", []);
    var favBtns = [];
    favs.slice(0, 6).forEach(function (fid) {
      var t = registry[fid];
      if (!t) return;
      var fBtn = window.FOSS.dom.el("button", {
        className: "btn btn-icon btn-ghost btn-sm",
        "data-testid": "fav-pin-" + fid,
        "aria-label": t.title,
        title: t.title,
        onClick: function () {
          open(fid);
        }
      }, [window.FOSS.icons.el(t.icon || "file", 16)]);
      favBtns.push(fBtn);
    });
    var favBar = window.FOSS.dom.el("div", { className: "row favorites-bar" }, favBtns);

    // Theme selector button
    var themesList = ["dark", "light", "solarized", "monokai", "cyberpunk"];
    var currentTheme = window.FOSS.store.get("theme", "dark");
    var themeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-ghost btn-sm",
      "data-testid": "topbar-theme-toggle",
      "aria-label": "Switch theme",
      title: "Switch theme (" + currentTheme + ")",
      onClick: function () {
        var idx = themesList.indexOf(currentTheme);
        var nextTheme = themesList[(idx + 1) % themesList.length];
        window.FOSS.theme.setTheme(nextTheme);
        currentTheme = nextTheme;
        themeBtn.setAttribute("title", "Switch theme (" + currentTheme + ")");
      }
    }, [window.FOSS.icons.el(currentTheme === "light" ? "sun" : "moon", 16)]);

    // Settings shortcut button
    var settingsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-ghost btn-sm",
      "data-testid": "topbar-settings-btn",
      "aria-label": "Settings",
      title: "Settings",
      onClick: function () {
        open("settings");
      }
    }, [window.FOSS.icons.el("settings", 16)]);

    var rightGroup = window.FOSS.dom.el("div", { className: "row end" }, [searchBtn, favBar, themeBtn, settingsBtn]);
    topbar.appendChild(rightGroup);
  }

  function open(viewId, tabId) {
    if (activeView && registry[activeView] && registry[activeView].onHide) {
      try {
        registry[activeView].onHide(createContext(activeView));
      } catch (e) {
        console.warn(e);
      }
    }

    activeView = viewId;
    activeTab = tabId || null;

    renderSidebar();
    renderTopbar();

    var viewRoot = document.getElementById("view-root");
    if (!viewRoot) return;
    viewRoot.innerHTML = "";

    if (viewId === "home") {
      if (window.FOSS.home && window.FOSS.home.render) {
        window.FOSS.home.render(viewRoot);
      }
      return;
    }

    if (viewId === "settings") {
      if (window.FOSS.settings && window.FOSS.settings.render) {
        window.FOSS.settings.render(viewRoot, tabId);
      }
      return;
    }

    var tool = registry[viewId];
    if (!tool) {
      viewRoot.appendChild(window.FOSS.dom.el("div", {
        className: "empty",
        text: "Tool not found: " + viewId
      }));
      return;
    }

    var ctx = createContext(viewId);
    var pageClass = tool.workbench ? "workbench" : "page";
    var pageEl = window.FOSS.dom.el("div", { className: pageClass, "data-testid": "tool-page-" + tool.id });

    // Page Header
    var isFav = window.FOSS.store.isFavorite(tool.id);
    var favToggleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-ghost btn-sm",
      "data-testid": tool.id + "-favorite-toggle",
      "aria-label": isFav ? "Remove favorite" : "Add to favorites",
      title: isFav ? "Remove favorite" : "Add to favorites",
      onClick: function () {
        var nowFav = window.FOSS.store.toggleFavorite(tool.id);
        favToggleBtn.innerHTML = window.FOSS.icons.svg(nowFav ? "star_filled" : "star", 18);
        renderTopbar();
      }
    }, [window.FOSS.icons.el(isFav ? "star_filled" : "star", 18)]);

    var headEl = window.FOSS.dom.el("div", { className: "page-head" }, [
      window.FOSS.dom.el("div", { className: "stack-sm" }, [
        window.FOSS.dom.el("h1", { className: "title", text: tool.title }),
        window.FOSS.dom.el("p", { className: "desc", text: tool.description || "" })
      ]),
      favToggleBtn
    ]);
    pageEl.appendChild(headEl);

    // Tabs
    var tabs = tool.tabs || [];
    var currentTabId = tabId || (tabs.length > 0 ? tabs[0].id : null);
    var panelContainer = window.FOSS.dom.el("div", { className: "tool-panel-container grow" });

    if (tabs.length > 1) {
      var tabButtons = tabs.map(function (tDef) {
        var isSelected = tDef.id === currentTabId;
        return window.FOSS.dom.el("button", {
          role: "tab",
          className: isSelected ? "active" : "",
          "aria-selected": isSelected ? "true" : "false",
          "data-testid": tool.id + "-tab-" + tDef.id,
          "data-obscure-ok": "true",
          text: tDef.label,
          onClick: function () {
            open(tool.id, tDef.id);
          }
        });
      });
      var tabsHeader = window.FOSS.dom.el("div", { className: "tabs scroll-x", role: "tablist" }, tabButtons);
      pageEl.appendChild(tabsHeader);
    }

    // Render active tab panel
    var activeTabDef = tabs.find(function (t) { return t.id === currentTabId; }) || tabs[0];
    if (activeTabDef && activeTabDef.render) {
      activeTabDef.render(panelContainer, ctx);
    }
    pageEl.appendChild(panelContainer);

    viewRoot.appendChild(pageEl);

    if (tool.onShow) {
      try {
        tool.onShow(ctx);
      } catch (e) {
        console.warn(e);
      }
    }
  }

  function createContext(toolId) {
    return {
      api: window.FOSS.api,
      job: window.FOSS.job,
      toast: window.FOSS.toast ? window.FOSS.toast.show : function () {},
      confirm: window.FOSS.confirm,
      state: toolStates[toolId]
    };
  }

  function routeFiles(paths) {
    if (!paths || paths.length === 0) return;
    window.FOSS.api("route_file", { path: paths[0] }).then(function (res) {
      var targetId = (res && res.ok && res.tool_id) || "converter";
      open(targetId);
      var tool = registry[targetId];
      if (tool && tool.onFiles) {
        tool.onFiles(paths, createContext(targetId));
      }
    });
  }

  window.FOSS.router = {
    register: register,
    open: open,
    getRegisteredTools: getRegisteredTools,
    renderSidebar: renderSidebar,
    renderTopbar: renderTopbar,
    routeFiles: routeFiles,
    getActiveView: function () { return activeView; },
    getActiveTab: function () { return activeTab; }
  };
})();

