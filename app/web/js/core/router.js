// View router, tab manager, and application shell navigation.
window.FOSS = window.FOSS || {};

(function () {
  var registry = {};
  var activeView = null;
  var activeTab = null;
  var toolStates = {};

  var DEFAULT_SECTIONS = [
    {
      id: "sec_favorites",
      name: "Favorites",
      collapsed: false,
      items: []
    },
    {
      id: "sec_documents",
      name: "Documents",
      collapsed: false,
      items: [
        { id: "pdf", visible: true },
        { id: "ocr", visible: true },
        { id: "markdown", visible: true },
        { id: "resume", visible: true }
      ]
    },
    {
      id: "sec_visuals",
      name: "Visuals",
      collapsed: false,
      items: [
        { id: "images", visible: true },
        { id: "collage", visible: true },
        { id: "palette", visible: true },
        { id: "model3d", visible: true }
      ]
    },
    {
      id: "sec_media",
      name: "Media",
      collapsed: false,
      items: [
        { id: "media", visible: true },
        { id: "playlist", visible: true }
      ]
    },
    {
      id: "sec_files",
      name: "Files & Storage",
      collapsed: false,
      items: [
        { id: "converter", visible: true },
        { id: "compressor", visible: true },
        { id: "archive", visible: true },
        { id: "renamer", visible: true }
      ]
    },
    {
      id: "sec_data",
      name: "Data & Text",
      collapsed: false,
      items: [
        { id: "data", visible: true },
        { id: "text_tools", visible: true },
        { id: "encoding", visible: true },
        { id: "unit_converter", visible: true }
      ]
    },
    {
      id: "sec_security",
      name: "Security & Network",
      collapsed: false,
      items: [
        { id: "network_monitor", visible: true },
        { id: "sherlock", visible: true },
        { id: "metadata", visible: true }
      ]
    },
    {
      id: "sec_utilities",
      name: "Utilities",
      collapsed: false,
      items: [
        { id: "qr", visible: true }
      ]
    }
  ];

  var TOOL_MANIFESTS = [
    {
      id: "pdf",
      title: "PDF Tools",
      navName: "PDF",
      category: "Documents",
      icon: "pdf",
      workbench: true,
      description: "Merge, reorder, split, extract text, and password protect PDFs.",
      defaults: [
        { key: "group_behavior", label: "Document grouping", type: "select", options: ["tabbed", "stacked"], default: "tabbed" }
      ],
      tabs: [
        { id: "merge", label: "Combine & Organize" },
        { id: "split", label: "Split PDF" },
        { id: "security", label: "Protect & Unlock" }
      ]
    },
    {
      id: "ocr",
      title: "OCR Studio",
      navName: "OCR",
      category: "Documents",
      icon: "ocr",
      workbench: true,
      description: "Extract text from scans and images; create searchable PDFs completely offline.",
      defaults: [
        { key: "language", label: "Language", type: "select", options: ["eng", "spa", "fra", "deu"], default: "eng" },
        { key: "format", label: "Default Export Format", type: "select", options: ["txt", "pdf", "tsv"], default: "txt" }
      ],
      tabs: [
        { id: "document", label: "Document OCR" },
        { id: "batch", label: "Batch OCR" }
      ]
    },
    {
      id: "markdown",
      title: "Markdown Studio",
      navName: "Markdown",
      category: "Documents",
      icon: "markdown",
      workbench: true,
      description: "Side-by-side Markdown editor and live renderer with GitHub GFM, CommonMark, and HTML/PDF export.",
      defaults: [
        { key: "flavor", label: "Parser flavor", type: "select", options: ["gfm", "commonmark"], default: "gfm" }
      ],
      tabs: [
        { id: "main", label: "Markdown Studio" }
      ]
    },
    {
      id: "resume",
      title: "Resume Studio",
      navName: "Resume",
      category: "Documents",
      icon: "resume",
      workbench: true,
      description: "Engineering resume builder with exact UT Austin Engineering Theme formatting and live PDF preview.",
      defaults: [
        { key: "theme", label: "Default theme", type: "select", options: [{ value: "gnc", label: "UT Austin Engineering Theme" }], default: "gnc" },
        { key: "date_format", label: "Default date format", type: "select", options: ["MM/YYYY", "Month YYYY"], default: "Month YYYY" },
        { key: "font_scale", label: "Default font scale", type: "select", options: [{ value: "11.0", label: "11.0 pt (Standard)" }, { value: "10.5", label: "10.5 pt (Compact)" }, { value: "10.0", label: "10.0 pt (Dense)" }], default: "11.0" },
        { key: "include_summary", label: "Include professional summary by default", type: "toggle", default: true }
      ],
      tabs: [
        { id: "personal", label: "Contact & Bio" },
        { id: "sections", label: "Sections" },
        { id: "profiles", label: "Tailor & ATS" },
        { id: "preview", label: "Preview & Export" }
      ]
    },
    {
      id: "images",
      title: "Image Studio",
      navName: "Images",
      category: "Visuals",
      icon: "images",
      workbench: true,
      description: "Background remover model manager, crop, resize, adjust, and creative ASCII/GIF tools.",
      defaults: [
        { key: "rembg_model", label: "Default background model", type: "select", options: ["u2net", "u2netp", "isnet-general-use"], default: "u2netp" },
        { key: "jpeg_quality", label: "Default JPEG quality", type: "number", min: 10, max: 100, step: 5, default: 90 }
      ],
      tabs: [
        { id: "background", label: "Background" },
        { id: "transform", label: "Transform" },
        { id: "creative", label: "Creative" }
      ]
    },
    {
      id: "collage",
      title: "Collage & Layers Studio",
      navName: "Collage",
      category: "Visuals",
      icon: "collage",
      workbench: true,
      description: "Freeform multi-layer canvas with Z-ordering, transforms, grid collages, and layered PSD/ORA/ZIP export.",
      defaults: [
        { key: "transparent_bg", label: "Transparent background by default", type: "toggle", default: false },
        { key: "columns", label: "Default grid columns", type: "number", min: 1, max: 5, step: 1, default: 2 },
        { key: "flat_format", label: "Default flattened export format", type: "select", options: ["png", "jpeg"], default: "png" }
      ],
      tabs: [
        { id: "main", label: "Collage Builder" }
      ]
    },
    {
      id: "palette",
      title: "Color Palette Studio",
      navName: "Palette",
      category: "Visuals",
      icon: "palette",
      workbench: true,
      description: "Extract color palettes, live eyedropper pixel loupe, and WCAG contrast checker.",
      defaults: [
        { key: "swatch_count", label: "Default swatch count", type: "number", min: 3, max: 12, step: 1, default: 6 },
        { key: "export_format", label: "Default export format", type: "select", options: ["json", "css", "gpl", "ase"], default: "json" }
      ],
      tabs: [
        { id: "main", label: "Dominant Color Palette" }
      ]
    },
    {
      id: "model3d",
      title: "3D Model Studio",
      navName: "3D Models",
      category: "Visuals",
      icon: "model3d",
      workbench: true,
      description: "Cut with planes, inspect geometry, repair mesh, scale, measure, and convert STL/OBJ/STEP.",
      defaults: [
        { key: "render_mode", label: "Default render mode", type: "select", options: ["shaded", "wireframe", "points"], default: "shaded" }
      ],
      tabs: [
        { id: "inspector", label: "Inspector & Tools" },
        { id: "cut", label: "Cut Plane" },
        { id: "export", label: "Export & Convert" }
      ]
    },
    {
      id: "media",
      title: "Audio & Video Studio",
      navName: "Audio & Video",
      category: "Media",
      icon: "media",
      workbench: true,
      description: "Trim, extract audio, generate Whisper subtitles, adjust speed, and convert video to GIF.",
      defaults: [
        { key: "audio_format", label: "Default audio export format", type: "select", options: ["mp3", "wav", "flac", "aac"], default: "mp3" },
        { key: "transcribe_model", label: "Whisper model size", type: "select", options: ["tiny", "base", "small"], default: "base" }
      ],
      tabs: [
        { id: "trim", label: "Trim & Cut" },
        { id: "audio", label: "Audio & Subtitles" },
        { id: "effects", label: "Frames, Speed & GIF" },
        { id: "timeline", label: "Multi-Clip Joiner" }
      ]
    },
    {
      id: "playlist",
      title: "Playlist Porter",
      navName: "Playlist Porter",
      category: "Media",
      icon: "playlist",
      workbench: false,
      description: "Convert playlists between Spotify, YouTube, and YouTube Music with M3U8/CSV export.",
      defaults: [
        { key: "export_format", label: "Default export format", type: "select", options: [{ value: "m3u8", label: "M3U8" }, { value: "csv", label: "CSV" }, { value: "json", label: "JSON" }], default: "m3u8" }
      ],
      tabs: [
        { id: "import", label: "Import / Fetch" },
        { id: "paste", label: "Paste Text" },
        { id: "output", label: "Tracklist & Output" }
      ]
    },
    {
      id: "converter",
      title: "File Format Converter",
      navName: "Converter",
      category: "Files & Storage",
      icon: "converter",
      workbench: true,
      description: "Universal file converter for documents, office, images, media, data, and 3D models.",
      defaults: [
        { key: "image_format", label: "Default image target format", type: "select", options: ["png", "jpeg", "webp", "bmp", "tiff"], default: "png" },
        { key: "document_format", label: "Default document target format", type: "select", options: ["pdf", "txt", "md", "html", "csv"], default: "pdf" },
        { key: "quality", label: "Default quality", type: "number", min: 10, max: 100, step: 5, default: 90 }
      ],
      tabs: [
        { id: "single", label: "Converter" }
      ]
    },
    {
      id: "compressor",
      title: "File Compressor",
      navName: "Compressor",
      category: "Files & Storage",
      icon: "compressor",
      workbench: true,
      description: "Centralized compression for PDF documents, images, video, audio, and archives.",
      defaults: [
        { key: "profile", label: "Default compression profile", type: "select", options: [{ value: "light", label: "Low (Fast)" }, { value: "balanced", label: "Medium (Balanced)" }, { value: "aggressive", label: "High (Maximum)" }], default: "balanced" }
      ],
      tabs: [
        { id: "main", label: "File Compressor" }
      ]
    },
    {
      id: "archive",
      title: "Archive Studio",
      navName: "Archive",
      category: "Files & Storage",
      icon: "archive",
      workbench: true,
      description: "Create, inspect, extract, and password-protect ZIP, TAR.GZ, TAR.XZ, and TAR.BZ2 archives.",
      defaults: [
        { key: "format", label: "Default archive format", type: "select", options: ["zip", "tar.gz"], default: "zip" },
        { key: "level", label: "Default compression level", type: "number", min: 0, max: 9, step: 1, default: 6 }
      ],
      tabs: [
        { id: "create", label: "Create Archive" },
        { id: "extract", label: "Extract Archive" },
        { id: "inspect", label: "Inspect Contents" }
      ]
    },
    {
      id: "renamer",
      title: "Batch File Renamer",
      navName: "Renamer",
      category: "Files & Storage",
      icon: "renamer",
      workbench: true,
      description: "Zero-regex visual step renaming with live before-and-after preview and instant undo.",
      defaults: [
        { key: "number_padding", label: "Default numbering padding", type: "number", min: 1, max: 6, step: 1, default: 2 },
        { key: "case_mode", label: "Default case transformation", type: "select", options: ["title", "lower", "upper", "sentence", "snake", "kebab"], default: "title" }
      ],
      tabs: [
        { id: "rules", label: "Rules & Preview" }
      ]
    },
    {
      id: "metadata",
      title: "Metadata Tools",
      navName: "Metadata",
      category: "Security & Network",
      icon: "metadata",
      workbench: true,
      description: "Inspect, edit, or remove metadata from images, PDFs, office docs, and media before sharing.",
      defaults: [
        { key: "create_backup", label: "Create backup of original file", type: "toggle", default: true }
      ],
      tabs: [
        { id: "inspect", label: "Inspect, Edit & Strip" },
        { id: "batch", label: "Batch Folder Scrub" }
      ]
    },
    {
      id: "qr",
      title: "QR Code Generator",
      navName: "QR & Barcodes",
      category: "Utilities",
      icon: "qr",
      workbench: true,
      description: "Generate custom QR codes and 1D barcodes, and scan codes from images or clipboard.",
      defaults: [
        { key: "default_type", label: "Default generator type", type: "select", options: ["text", "url", "wifi", "email"], default: "text" },
        { key: "export_resolution", label: "Default export resolution (px)", type: "number", default: 512, min: 64, max: 4096, step: 64 }
      ],
      tabs: [
        { id: "qr", label: "QR Generator" },
        { id: "barcode", label: "1D Barcodes" },
        { id: "scan", label: "Scan & Decode" }
      ]
    },
    {
      id: "network_monitor",
      title: "Network Traffic Monitor",
      navName: "Network Monitor",
      category: "Security & Network",
      icon: "network_monitor",
      workbench: false,
      description: "Watch live outbound connections by process, flag unknown destinations, and query history.",
      defaults: [
        { key: "auto_start", label: "Auto-start live scanning", type: "toggle", default: false }
      ],
      tabs: [
        { id: "live", label: "Live Connections" },
        { id: "history", label: "History" },
        { id: "stats", label: "Stats" },
        { id: "apps", label: "Per-App Summary" }
      ]
    },
    {
      id: "sherlock",
      title: "Sherlock Username Search",
      navName: "Sherlock",
      category: "Security & Network",
      icon: "sherlock",
      workbench: false,
      description: "Find social media and online accounts by username across hundreds of networks.",
      defaults: [
        { key: "default_mode", label: "Default scan mode", type: "select", default: "popular", options: [{ value: "popular", label: "Popular Sites" }, { value: "all", label: "All Sites" }] },
        { key: "timeout", label: "Per-request timeout (seconds)", type: "number", default: 10, min: 2, max: 60, step: 1 },
        { key: "include_nsfw", label: "Include adult/NSFW platforms", type: "boolean", default: false }
      ],
      tabs: [
        { id: "search", label: "Username Search" },
        { id: "catalog", label: "Sites Catalog" }
      ]
    },
    {
      id: "unit_converter",
      title: "Unit Converter",
      navName: "Unit Converter",
      category: "Data & Text",
      icon: "unit_converter",
      workbench: true,
      description: "Scientific unit converter supporting 30 categories and compound dimensional expressions.",
      defaults: [],
      tabs: [
        { id: "standard", label: "Standard & All Units" },
        { id: "expression", label: "Compound Expressions" }
      ]
    },
    {
      id: "data",
      title: "Data Studio",
      navName: "Data",
      category: "Data & Text",
      icon: "data",
      workbench: true,
      description: "Format, minify, validate, convert, and query JSON, YAML, TOML, CSV, XML, and SQL.",
      defaults: [
        { key: "indent", label: "Indent spacing", type: "select", options: [{ value: "2", label: "2 spaces" }, { value: "4", label: "4 spaces" }, { value: "8", label: "8 spaces" }], default: "2" }
      ],
      tabs: [
        { id: "editor", label: "Format & Convert" },
        { id: "structure", label: "HDF5" },
        { id: "tables", label: "Tables" },
        { id: "query", label: "JSONPath & Schema" },
        { id: "utilities", label: "Utilities" }
      ]
    },
    {
      id: "text_tools",
      title: "Text Tools",
      navName: "Text Tools",
      category: "Data & Text",
      icon: "text_tools",
      workbench: true,
      description: "Text transforms, side-by-side diff, readability analytics, grammar inspection, and citations.",
      defaults: [
        { key: "case_mode", label: "Default case mode", type: "select", options: ["titlecase", "lowercase", "uppercase"], default: "titlecase" }
      ],
      tabs: [
        { id: "transforms", label: "Text Transforms" },
        { id: "diff", label: "Side-by-Side Diff" },
        { id: "counter", label: "Word Counter" },
        { id: "writing", label: "Grammar & Citations" }
      ]
    },
    {
      id: "encoding",
      title: "Encoding & Decoding",
      navName: "Encoding",
      category: "Data & Text",
      icon: "encoding",
      workbench: true,
      description: "Encode and decode text and files between Base64, URL, HTML entities, hex, and binary.",
      defaults: [
        { key: "scheme", label: "Default text scheme", type: "select", options: ["Base64", "URL Encode", "Hexadecimal", "Binary"], default: "Base64" }
      ],
      tabs: [
        { id: "text", label: "Text Ciphers & Encodings" },
        { id: "file", label: "Binary File Encoding" }
      ]
    }
  ];

  var loadedTools = {};
  var loadingPromises = {};

  TOOL_MANIFESTS.forEach(function (m) {
    registry[m.id] = Object.assign({}, m, { _loaded: false });
    toolStates[m.id] = {};
    if (m.defaults && window.FOSS.toolDefaults) {
      window.FOSS.toolDefaults.define(m.id, m.defaults);
    }
  });

  function isToolLoaded(toolId) {
    var tool = registry[toolId];
    if (!tool) return false;
    if (tool._loaded) return true;
    if (tool.tabs && tool.tabs.length > 0 && typeof tool.tabs[0].render === "function") {
      return true;
    }
    return false;
  }

  function loadTool(toolId) {
    if (isToolLoaded(toolId)) {
      return Promise.resolve(registry[toolId]);
    }
    if (loadingPromises[toolId]) {
      return loadingPromises[toolId];
    }
    var scriptPath = "js/tools/" + toolId + ".js";
    var p = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = scriptPath;
      script.async = true;
      script.onload = function () {
        loadedTools[toolId] = true;
        if (registry[toolId]) {
          registry[toolId]._loaded = true;
        }
        resolve(registry[toolId]);
      };
      script.onerror = function (err) {
        delete loadingPromises[toolId];
        reject(new Error("Failed to load tool module: " + toolId));
      };
      document.head.appendChild(script);
    });
    loadingPromises[toolId] = p;
    return p;
  }

  function register(toolDef) {
    var existing = registry[toolDef.id] || {};
    var merged = Object.assign({}, existing, toolDef);
    merged._loaded = true;
    registry[toolDef.id] = merged;
    loadedTools[toolDef.id] = true;
    if (toolDef.defaults && window.FOSS.toolDefaults) {
      window.FOSS.toolDefaults.define(toolDef.id, toolDef.defaults);
    }
    toolStates[toolDef.id] = toolStates[toolDef.id] || {};
  }

  function getRegisteredTools() {
    return Object.values(registry);
  }

  function cloneLayout(layout) {
    return JSON.parse(JSON.stringify(layout));
  }

  function resolveSidebarLayout() {
    var saved = window.FOSS.store ? window.FOSS.store.get("sidebar_layout", null) : null;
    var sections;
    if (saved && Array.isArray(saved.sections) && saved.sections.length > 0) {
      sections = cloneLayout(saved.sections);
    } else {
      sections = cloneLayout(DEFAULT_SECTIONS);
    }

    // Keep only registered tools
    sections.forEach(function (sec) {
      sec.items = (sec.items || []).filter(function (it) {
        if (!registry[it.id]) return false;
        return true;
      });
    });

    // Append newly registered tools to their default section if not present
    var registered = getRegisteredTools();
    registered.forEach(function (t) {
      var cat = (t.category || "Utilities").trim();
      var catLower = cat.toLowerCase();
      var targetSec = sections.find(function (s) {
        var sName = (s.name || "").toLowerCase();
        return sName === catLower || s.id === "sec_" + catLower ||
          (catLower === "utilities" && (s.id === "sec_files" || s.id === "sec_utilities")) ||
          (catLower === "data" && (s.id === "sec_system" || s.id === "sec_data"));
      });
      if (!targetSec) {
        targetSec = {
          id: "sec_" + catLower.replace(/[^a-z0-9]/g, "_"),
          name: cat,
          collapsed: false,
          items: []
        };
        sections.push(targetSec);
      }
      var isAlreadyInTarget = false;
      targetSec.items.forEach(function (it) {
        if (it.id === t.id) isAlreadyInTarget = true;
      });
      if (!isAlreadyInTarget) {
        targetSec.items.push({ id: t.id, visible: true });
      }
    });

    var favIds = window.FOSS.store ? window.FOSS.store.get("favorites", []) : [];
    var favSec = sections.find(function (s) { return s.id === "sec_favorites"; });
    if (favSec) {
      favSec.items = (Array.isArray(favIds) ? favIds : []).filter(function (id) {
        return registry[id];
      }).map(function (id) {
        return { id: id, visible: true };
      });
    }

    return { version: 1, sections: sections };
  }

  function renderSidebar() {
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) return;

    var navEl = sidebar.querySelector(".sidebar-nav");
    var prevScroll = navEl ? navEl.scrollTop : 0;
    sidebar.innerHTML = "";

    // Brand header
    var brand = window.FOSS.dom.el("div", { className: "row" }, [
      window.FOSS.icons.el("home", 20),
      window.FOSS.dom.el("span", { className: "brand-name", text: "FOSSEverything" })
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

    // Scrollable navigation list
    var navList = window.FOSS.dom.el("nav", { className: "sidebar-nav scroll-y" });

    // Home item
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

    // Dynamic categorized sections
    var layout = resolveSidebarLayout();
    var seenNavIds = {};
    layout.sections.forEach(function (sec) {
      var visibleItems = (sec.items || []).filter(function (it) {
        return it.visible && registry[it.id];
      });
      if (visibleItems.length === 0) return;

      var catHeading = window.FOSS.dom.el("div", { className: "nav-category", text: sec.name });
      navList.appendChild(catHeading);

      visibleItems.forEach(function (it) {
        var t = registry[it.id];
        var isAct = activeView === t.id;
        var navTestId = "nav-" + t.id;
        if (sec.id === "sec_favorites") {
          navTestId = "nav-fav-" + t.id;
        } else if (seenNavIds[t.id]) {
          navTestId = "nav-" + t.id + "-" + sec.id;
        } else {
          seenNavIds[t.id] = true;
        }
        var btn = window.FOSS.dom.el("button", {
          className: "nav-item " + (isAct ? "active" : ""),
          "data-testid": navTestId,
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

    // Sidebar resizer handle
    var resizer = window.FOSS.dom.el("div", {
      className: "sidebar-resizer",
      "data-decorative": "true"
    });
    sidebar.appendChild(resizer);

    if (navList) {
      navList.scrollTop = prevScroll;
    }
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
      window.FOSS.dom.el("span", {
        text: viewTitle,
        className: "breadcrumb-current",
        title: viewTitle,
        "data-truncate-ok": "true"
      })
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
    var themesList = ["ut_austin_dark", "dark", "light", "solarized", "monokai", "cyberpunk", "ut_austin"];
    var currentTheme = window.FOSS.store.get("theme", "ut_austin_dark");
    var themeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-icon btn-ghost btn-sm",
      "data-testid": "topbar-theme-toggle",
      "aria-label": "Switch theme",
      title: "Switch theme (" + currentTheme + ")",
      onClick: function () {
        var idx = themesList.indexOf(currentTheme);
        var nextTheme = themesList[(idx + 1) % themesList.length];
        window.FOSS.theme.setTheme(nextTheme);
      }
    }, [window.FOSS.icons.el(currentTheme === "light" ? "sun" : "moon", 16)]);

    if (window.FOSS.store && window.FOSS.store.subscribe) {
      window.FOSS.store.subscribe("theme", function (newTheme) {
        currentTheme = newTheme;
        themeBtn.setAttribute("title", "Switch theme (" + currentTheme + ")");
        themeBtn.innerHTML = window.FOSS.icons.svg(currentTheme === "light" ? "sun" : "moon", 16);
      });
    }

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

    var rightItems = [searchBtn, favBar];
    if (registry[activeView]) {
      var starTool = registry[activeView];
      var starFav = window.FOSS.store.isFavorite(starTool.id);
      rightItems.push(window.FOSS.dom.el("button", {
        className: "btn btn-icon btn-ghost btn-sm",
        "data-testid": "topbar-star-btn",
        "aria-label": starFav ? "Remove " + starTool.title + " from favorites" : "Add " + starTool.title + " to favorites",
        "aria-pressed": starFav ? "true" : "false",
        title: starFav ? "Remove favorite" : "Add to favorites",
        onClick: function () {
          window.FOSS.store.toggleFavorite(starTool.id);
        }
      }, [window.FOSS.icons.el(starFav ? "star_filled" : "star", 18)]));
    }
    rightItems.push(themeBtn, settingsBtn);
    var rightGroup = window.FOSS.dom.el("div", { className: "row end" }, rightItems);
    topbar.appendChild(rightGroup);
  }

  function renderToolView(tool, targetTabId) {
    var viewRoot = document.getElementById("view-root");
    if (!viewRoot) return;
    viewRoot.innerHTML = "";

    var ctx = createContext(tool.id);
    var pageClass = tool.workbench ? "workbench" : "page";
    var pageEl = window.FOSS.dom.el("div", {
      className: pageClass,
      "data-testid": "tool-page-" + tool.id,
      id: tool.id + "-page"
    });

    // Page Header
    var headActions = [];
    if (window.FOSS.toolDefaults && window.FOSS.toolDefaults.getFields(tool.id).length > 0) {
      headActions.push(window.FOSS.dom.el("button", {
        className: "btn btn-icon btn-ghost btn-sm",
        "data-testid": tool.id + "-defaults-btn",
        "aria-label": tool.title + " defaults",
        title: "Configure " + tool.title + " defaults",
        onClick: function () {
          window.FOSS.toolDefaults.openEditor(tool.id, tool.title);
        }
      }, [window.FOSS.icons.el("sliders", 18)]));
    }

    var headEl = window.FOSS.dom.el("div", { className: "page-head" }, [
      window.FOSS.dom.el("div", { className: "stack-sm" }, [
        window.FOSS.dom.el("h1", { className: "title", text: tool.title }),
        window.FOSS.dom.el("p", { className: "desc", text: tool.description || "" })
      ]),
      window.FOSS.dom.el("div", { className: "row" }, headActions)
    ]);
    pageEl.appendChild(headEl);

    // Tabs
    var toolTabs = tool.tabs || [];
    var initialTabMatch = toolTabs.find(function (t) { return t.id === targetTabId || (t.aliases && t.aliases.indexOf(targetTabId) !== -1); });
    var currentTabId = initialTabMatch ? initialTabMatch.id : (toolTabs.length > 0 ? toolTabs[0].id : null);
    activeTab = currentTabId;
    var panelContainer = window.FOSS.dom.el("div", { className: "tool-panel-container grow" });

    if (toolTabs.length > 1) {
      var tabButtonsList = toolTabs.map(function (tDef) {
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
      var tabsHeader = window.FOSS.dom.el("div", { className: "tabs scroll-x", role: "tablist" }, tabButtonsList);
      pageEl.appendChild(tabsHeader);
    }

    // Render active tab panel
    var activeTabDef = toolTabs.find(function (t) { return t.id === currentTabId; }) || toolTabs[0];
    if (activeTabDef && activeTabDef.render) {
      activeTabDef.render(panelContainer, ctx);
    } else if (tool.render) {
      tool.render(panelContainer, ctx);
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

  function open(viewId, tabId) {
    if (window.FOSS.dialogs && window.FOSS.dialogs.closeAll) {
      window.FOSS.dialogs.closeAll();
    }
    if (window.FOSS.palette && window.FOSS.palette.close) {
      window.FOSS.palette.close();
    }

    if (viewId === "home" || viewId === "settings") {
      activeView = viewId;
      activeTab = tabId || null;
      renderSidebar();
      renderTopbar();
      var viewRoot = document.getElementById("view-root");
      if (!viewRoot) return Promise.resolve();
      viewRoot.innerHTML = "";
      if (viewId === "home") {
        if (window.FOSS.home && window.FOSS.home.render) {
          window.FOSS.home.render(viewRoot);
        }
      } else {
        if (window.FOSS.settings && window.FOSS.settings.render) {
          window.FOSS.settings.render(viewRoot, tabId);
        }
      }
      return Promise.resolve();
    }

    var tool = registry[viewId];
    if (!tool) {
      activeView = viewId;
      activeTab = tabId || null;
      renderSidebar();
      renderTopbar();
      var emptyRoot = document.getElementById("view-root");
      if (emptyRoot) {
        emptyRoot.innerHTML = "";
        emptyRoot.appendChild(window.FOSS.dom.el("div", {
          className: "empty",
          text: "Tool not found: " + viewId
        }));
      }
      return Promise.resolve();
    }

    // In-place tab switch optimization when already on this view and loaded
    if (activeView === viewId && isToolLoaded(viewId)) {
      var tabs = tool.tabs || [];
      var targetTabId = tabId || (tabs.length > 0 ? tabs[0].id : null);
      var tabDef = tabs.find(function (t) { return t.id === targetTabId || (t.aliases && t.aliases.indexOf(targetTabId) !== -1); }) || tabs[0];
      if (tabDef && tabDef.id !== activeTab) {
        activeTab = tabDef.id;
        var tabButtons = document.querySelectorAll(".tabs [role='tab']");
        tabButtons.forEach(function (btn) {
          var isCurrent = btn.getAttribute("data-testid") === tool.id + "-tab-" + activeTab;
          btn.className = isCurrent ? "active" : "";
          btn.setAttribute("aria-selected", isCurrent ? "true" : "false");
        });
        var container = document.querySelector(".tool-panel-container");
        if (container) {
          container.innerHTML = "";
          if (tabDef.render) {
            tabDef.render(container, createContext(viewId));
          }
        }
      }
      return Promise.resolve(tool);
    }

    if (activeView && registry[activeView] && registry[activeView].onHide) {
      try {
        registry[activeView].onHide(createContext(activeView));
      } catch (e) {
        console.warn(e);
      }
    }

    activeView = viewId;
    if (tool.tabs && tool.tabs.length > 0) {
      activeTab = tabId || tool.tabs[0].id;
    } else {
      activeTab = tabId || null;
    }

    renderSidebar();
    renderTopbar();

    if (!isToolLoaded(viewId)) {
      var loadingRoot = document.getElementById("view-root");
      if (loadingRoot) {
        loadingRoot.innerHTML = "";
        loadingRoot.appendChild(window.FOSS.dom.el("div", {
          className: (tool.workbench ? "workbench" : "page") + " row items-center justify-center p-6 text-muted gap-2",
          "data-testid": tool.id + "-loading"
        }, [
          window.FOSS.icons.el("tool", 24),
          window.FOSS.dom.el("span", { text: "Loading " + tool.title + "..." })
        ]));
      }
      return loadTool(viewId).then(function (loadedTool) {
        if (activeView === viewId) {
          renderToolView(loadedTool, activeTab);
        }
        return loadedTool;
      });
    }

    renderToolView(tool, activeTab);
    return Promise.resolve(tool);
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
      loadTool(targetId).then(function (tool) {
        open(targetId);
        if (tool && tool.onFiles) {
          tool.onFiles(paths, createContext(targetId));
        }
      });
    });
  }

  window.addEventListener("foss:favorites-changed", function () {
    renderSidebar();
    renderTopbar();
  });

  window.FOSS.router = {
    register: register,
    open: open,
    loadTool: loadTool,
    isToolLoaded: isToolLoaded,
    getTool: function (id) { return registry[id]; },
    getRegisteredTools: getRegisteredTools,
    resolveSidebarLayout: resolveSidebarLayout,
    renderSidebar: renderSidebar,
    renderTopbar: renderTopbar,
    routeFiles: routeFiles,
    createContext: createContext,
    getActiveView: function () { return activeView; },
    getActiveTab: function () { return activeTab; }
  };
})();
