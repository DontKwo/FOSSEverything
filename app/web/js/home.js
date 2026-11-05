// Home view with hero search, categorized workspace tiles, and recent files.
window.FOSS = window.FOSS || {};

(function () {
  var selectedCategory = "All";
  var searchQuery = "";
  var DEFAULT_APPS = [
    { id: "pdf", name: "PDF Tools", category: "Documents", description: "Merge, reorder, split, extract text, and password protect PDFs.", artwork_url: "assets/home/pdf.png" },
    { id: "images", name: "Image Tools", category: "Visuals", description: "Convert formats, crop, resize, rotate, flip, remove background, and compress images.", artwork_url: "assets/home/images.png" },
    { id: "ocr", name: "OCR Studio", category: "Documents", description: "Extract text from scans and images; create searchable PDFs completely offline.", artwork_url: "assets/home/ocr.png" },
    { id: "resume", name: "Resume Builder", category: "Documents", description: "Build a master resume and check bullets and reorder sections to tailor per job.", artwork_url: "assets/home/resume.png" },
    { id: "playlist", name: "Playlist Porter", category: "Media", description: "Convert playlists between Spotify, YouTube, and YouTube Music with M3U8/CSV export.", artwork_url: "assets/home/playlist.png" },
    { id: "converter", name: "File Converter", category: "Utilities", description: "Universal file converter: convert any document, image, media, 3D, or data file format into any other.", artwork_url: "assets/home/converter.jpg" },
    { id: "compressor", name: "File Compressor", category: "Utilities", description: "Centralized compression for PDF documents, images, video, audio, and archives.", artwork_url: "assets/home/compressor.jpg" },
    { id: "metadata", name: "Metadata Tools", category: "Utilities", description: "Inspect, edit, or remove image/PDF/office/audio/video metadata before sharing.", artwork_url: "assets/home/metadata.png" },
    { id: "qr", name: "QR and Barcodes", category: "Utilities", description: "Generate custom offline QR codes and scan/decode barcodes from images and PDFs.", artwork_url: "assets/home/qr.png" },
    { id: "renamer", name: "Batch Renamer", category: "Utilities", description: "Rename files with search & replace, numbering, prefixes, casing, and undo safety.", artwork_url: "assets/home/renamer.png" },
    { id: "unit_converter", name: "Unit Converter", category: "Data", description: "Dimensional analysis across 30 physical categories and compound expressions.", artwork_url: "assets/home/unit_converter.svg" },
    { id: "data", name: "Data Studio", category: "Data", description: "Format, minify, validate, convert, and query JSON, YAML, TOML, CSV, XML, and SQL.", artwork_url: "assets/home/data.png" },
    { id: "markdown", name: "Markdown Preview", category: "Documents", description: "Live GitHub-flavored Markdown editor with instant side-by-side preview and HTML export.", artwork_url: "assets/home/markdown.svg" },
    { id: "palette", name: "Color Palette", category: "Visuals", description: "Extract dominant color palettes and sample exact pixel colors with mouse eyedropper.", artwork_url: "assets/home/palette.png" },
    { id: "collage", name: "Photo Collage", category: "Visuals", description: "Create customizable photo grid collages and side-by-side compositions.", artwork_url: "assets/home/collage.png" },
    { id: "model3d", name: "3D Model Studio", category: "Visuals", description: "Cut with planes, inspect geometry, repair mesh, scale, measure, and convert STL/OBJ/PLY/STEP.", artwork_url: "assets/home/model3d.png" },
    { id: "text_tools", name: "Text Tools", category: "Data", description: "Case conversion, word counter, readability analytics, grammar inspection, citations, and diff.", artwork_url: "assets/home/text_tools.png" },
    { id: "encoding", name: "Encoding / Decoding", category: "Data", description: "Encode and decode text and files between Base64, URL, HTML entities, hex, and binary.", artwork_url: "assets/home/encoding.png" },
    { id: "network_monitor", name: "Network Monitor", category: "Utilities", description: "Watch live outbound connections by process, flag unknown destinations, and query history.", artwork_url: "assets/home/network_monitor.svg" },
    { id: "archive", name: "Archive Studio", category: "Utilities", description: "Create, list, and extract ZIP, TAR, and TAR.GZ archives offline.", artwork_url: "assets/home/archive.svg" },
    { id: "media", name: "Audio & Video", category: "Media", description: "Trim clips, extract MP3 audio, generate Whisper subtitles, adjust speed, reverse, and create GIFs.", artwork_url: "assets/home/media.png" },
  ];
  var allApps = DEFAULT_APPS.slice();

  function syncApps(baseList) {
    var map = {};
    (baseList || []).forEach(function (app) {
      map[app.id] = app;
    });

    if (window.FOSS && window.FOSS.router && window.FOSS.router.getRegisteredTools) {
      var registered = window.FOSS.router.getRegisteredTools();
      registered.forEach(function (t) {
        if (!map[t.id]) {
          map[t.id] = {
            id: t.id,
            name: t.title,
            category: t.category || "Utilities",
            description: t.description || "",
            artwork_url: t.artwork_url || ("assets/home/" + t.id + ".png")
          };
        }
      });
    }

    allApps = Object.values(map);
  }


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
    var layout = window.FOSS.router.resolveSidebarLayout();
    var sectionNames = (layout.sections || [])
      .filter(function (s) {
        return s.id !== "sec_favorites" && (s.items || []).some(function (it) { return it.visible; });
      })
      .map(function (s) { return s.name; });
    var categories = ["All", "Favorites"].concat(sectionNames);

    if (categories.indexOf(selectedCategory) === -1) {
      selectedCategory = "All";
    }

    var filterRow = window.FOSS.dom.el('div', { className: 'row gap-2 flex-wrap mb-3' });
    categories.forEach(function (cat) {
      var chip = window.FOSS.dom.el('button', {
        className: 'chip ' + (selectedCategory === cat ? 'active' : ''),
        text: cat,
        "aria-pressed": selectedCategory === cat ? "true" : "false",
        "data-testid": "home-filter-" + cat.toLowerCase().replace(/[^a-z0-9]/g, "-"),
        onClick: function () {
          selectedCategory = cat;
          Array.from(filterRow.children).forEach(function (child) {
            if (child.tagName === 'BUTTON') {
              var isActive = child.textContent === cat;
              child.className = 'chip ' + (isActive ? 'active' : '');
              child.setAttribute("aria-pressed", isActive ? "true" : "false");
            }
          });
          updateGrid();
        }
      });
      filterRow.appendChild(chip);
    });

    page.appendChild(filterRow);

    // Grid container
    var grid = window.FOSS.dom.el("div", { className: "grid-auto home-grid", "data-testid": "home-apps-grid" });
    page.appendChild(grid);

    // Recent files and outputs section
    var recentsContainer = window.FOSS.dom.el("div", { className: "stack home-recents", "data-testid": "home-recents-section" });
    page.appendChild(recentsContainer);

    container.appendChild(page);

    // Load apps and render grid
    syncApps(DEFAULT_APPS);
    updateGrid();
    window.FOSS.api("get_apps", {}).then(function (res) {
      if (res && res.ok && res.apps) {
        syncApps(res.apps);
        updateGrid();
      }
    });

    loadRecents(recentsContainer);
  }

  function matchesSearch(app) {
    if (!searchQuery) return true;
    var matchName = app.name.toLowerCase().indexOf(searchQuery) !== -1;
    var matchDesc = app.description.toLowerCase().indexOf(searchQuery) !== -1;
    var matchKw = app.keywords && app.keywords.some(function (k) { return k.toLowerCase().indexOf(searchQuery) !== -1; });
    return matchName || matchDesc || matchKw;
  }

  function updateGrid() {
    var grid = document.querySelector(".home-grid");
    if (!grid) return;
    grid.innerHTML = "";

    var hideUnchecked = window.FOSS.store.get("hide_unchecked_on_home", false);
    var hiddenMap = {};
    var layout = (window.FOSS.router && window.FOSS.router.resolveSidebarLayout)
      ? window.FOSS.router.resolveSidebarLayout()
      : null;

    if (hideUnchecked && layout) {
      (layout.sections || []).forEach(function (section) {
        (section.items || []).forEach(function (item) {
          if (item.visible === false) hiddenMap[item.id] = true;
        });
      });
    }

    var isFavFilter = selectedCategory === "Favorites";
    var sectionToolIds = null;
    if (selectedCategory !== "All" && !isFavFilter && layout) {
      var targetSec = (layout.sections || []).find(function (section) {
        return section.name === selectedCategory;
      });
      if (targetSec) {
        sectionToolIds = {};
        (targetSec.items || []).forEach(function (item) {
          if (item.visible !== false) {
            sectionToolIds[item.id] = true;
          }
        });
      }
    }

    var filtered = allApps.filter(function (app) {
      if (hideUnchecked && hiddenMap[app.id]) return false;
      if (isFavFilter) return window.FOSS.store.isFavorite(app.id) && matchesSearch(app);
      if (selectedCategory !== "All") {
        if (sectionToolIds) {
          if (!sectionToolIds[app.id]) return false;
        } else if (app.category !== selectedCategory) {
          return false;
        }
      }
      return matchesSearch(app);
    });

    if (filtered.length === 0 && isFavFilter && !searchQuery) {
      grid.appendChild(window.FOSS.dom.el("div", {
        className: "empty",
        "data-testid": "home-empty-favorites"
      }, [
        window.FOSS.icons.el("star", 32),
        window.FOSS.dom.el("h3", { className: "empty-title", text: "No favorite tools yet" }),
        window.FOSS.dom.el("p", {
          className: "empty-desc",
          text: "Click the star on any tool card, or the star in the top bar while a tool is open, to pin it here."
        })
      ]));
      return;
    }

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
        "data-testid": "home-card-star-" + app.id,
        onClick: function (e) {
          e.stopPropagation();
          window.FOSS.store.toggleFavorite(app.id);
        }
      }, [window.FOSS.icons.el(isFav ? "star_filled" : "star", 16)]);

      var imgBox = window.FOSS.dom.el("div", { className: "tile-img-box" });
      var preferred = app.artwork_url || ("assets/home/" + app.id + ".png");
      var candidateExts = [preferred, "assets/home/" + app.id + ".svg", "assets/home/" + app.id + ".png", "assets/home/" + app.id + ".jpg"];
      var extIndex = 0;
      var imgEl = window.FOSS.dom.el("img", {
        className: "tile-img",
        src: candidateExts[0],
        alt: app.name,
        loading: "lazy"
      });
      imgEl.onerror = function () {
        extIndex++;
        if (extIndex < candidateExts.length) {
          imgEl.src = candidateExts[extIndex];
        } else {
          imgBox.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 135" width="100%" height="100%"><defs><linearGradient id="fallback_' + app.id + '" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#1e293b"/><stop offset="100%" stop-color="#0f172a"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#fallback_' + app.id + ')"/><text x="50%" y="54%" font-family="sans-serif" font-size="13" font-weight="700" fill="#94a3b8" text-anchor="middle" letter-spacing="1">' + app.name.toUpperCase() + '</text></svg>';
        }
      };
      imgBox.appendChild(imgEl);

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

      var tileBody = window.FOSS.dom.el("div", { className: "tile-body" }, [
        tileHead,
        tileDesc
      ]);

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
      }, [imgBox, tileBody]);

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

  window.addEventListener("foss:favorites-changed", function () {
    if (window.FOSS.router.getActiveView() === "home") updateGrid();
  });

  window.FOSS.home = {
    render: render
  };
})();

