// FOSSEverything Web Application Logic
let allApps = [];
let currentFilter = 'all';
let pinnedTools = ['pdf', 'images', 'model3d', 'media', 'converter', 'qr', 'renamer', 'markdown', 'hash', 'data'];

const apiProxy = new Proxy({}, {
  get(target, prop) {
    if (window.pywebview && window.pywebview.api) {
      const val = window.pywebview.api[prop];
      if (typeof val === 'function') {
        return val.bind(window.pywebview.api);
      }
      return val;
    }
    return async (...args) => {
      const start = Date.now();
      while (!window.pywebview || !window.pywebview.api) {
        if (Date.now() - start > 3000) break;
        await new Promise(r => setTimeout(r, 40));
      }
      if (window.pywebview && window.pywebview.api) {
        const fn = window.pywebview.api[prop];
        if (typeof fn === 'function') {
          return fn.apply(window.pywebview.api, args);
        }
        return fn;
      }
      console.warn(`pywebview.api.${String(prop)} is unavailable`);
      return { error: 'API bridge unavailable' };
    };
  }
});

function getApi() {
  return apiProxy;
}

const api = apiProxy;
window.api = apiProxy;

window.addEventListener('pywebviewready', async () => {
  try {
    if (!allApps || allApps.length === 0) {
      allApps = await api.get_apps();
      if (Array.isArray(allApps)) {
        renderApps(allApps);
        renderPinnedTools();
      }
    }
  } catch (err) {
    console.error('pywebviewready app loading error:', err);
  }
});

document.addEventListener('DOMContentLoaded', () => {
  init();
});

async function init() {
  setupNavigation();
  setupFilters();
  setupCommandPalette();
  setupSettingsHub();
  setupSubtabs();
  setupPdfStudio();
  setupImageStudio();
  setupModel3D();
  setupMediaStudio();
  setupConverterStudio();
  setupWordCounter();
  setupOcrStudio();
  setupMarkdownStudio();
  setupPaletteStudio();
  setupCollageStudio();
  setupRenamerStudio();
  setupMetadataStudio();
  setupArchiveStudio();
  setupOfficeStudio();
  setupScreenshotStudio();
  setupNetworkMonitor();
  setupPlaylistPorter();
  setupResumeBuilder();
  setupQRStudio();
  setupHashStudio();
  setupJsonStudio();
  setupTextTools();
  setupEncodingStudio();

  // Load apps from backend
  try {
    const api = getApi();
    if (api && api.get_apps) {
      allApps = await api.get_apps();
      renderApps(allApps);
      renderPinnedTools();
    } else {
      setTimeout(async () => {
        const lateApi = getApi();
        if (lateApi && lateApi.get_apps) {
          allApps = await lateApi.get_apps();
          renderApps(allApps);
          renderPinnedTools();
        }
      }, 300);
    }
  } catch (err) {
    console.error('Failed to load apps:', err);
  }
}

// Navigation between views
function setupNavigation() {
  // Sidebar items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const viewId = item.getAttribute('data-view');
      switchView(viewId);
    });
  });

  // Home top bar button
  document.getElementById('nav-home-btn')?.addEventListener('click', () => {
    switchView('home');
  });

  // Quick workspace select
  const quickSelect = document.getElementById('workspace-quick-select');
  if (quickSelect) {
    quickSelect.addEventListener('change', (e) => {
      switchView(e.target.value);
    });
  }

  // Quick theme select
  const themeSelect = document.getElementById('theme-quick-select');
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      applyTheme(e.target.value);
    });
  }
}

function applyTheme(themeName) {
  document.body.classList.remove('theme-light', 'theme-solarized', 'theme-monokai', 'theme-cyberpunk');
  if (themeName !== 'dark') {
    document.body.classList.add(`theme-${themeName}`);
  }
  const themeSelect = document.getElementById('theme-quick-select');
  if (themeSelect && themeSelect.value !== themeName) {
    themeSelect.value = themeName;
  }
  const settingsTheme = document.getElementById('settings-theme-preset');
  if (settingsTheme && settingsTheme.value !== themeName) {
    settingsTheme.value = themeName;
  }
}

function switchView(viewId) {
  document.querySelectorAll('.nav-item').forEach(el => {
    if (el.getAttribute('data-view') === viewId) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });

  document.querySelectorAll('.content-view > section').forEach(sec => {
    sec.style.display = 'none';
  });

  const activeSection = document.getElementById(`view-${viewId}`);
  if (activeSection) {
    activeSection.style.display = 'block';
    window.dispatchEvent(new Event('resize'));
  }

  const titles = {
    'home': 'All Tools',
    'pdf': 'PDF Studio & Editor',
    'images': 'Image Canvas & Editor',
    'model3d': '3D Model & STL Studio',
    'media': 'Video & Audio Studio',
    'converter': 'File Converter',
    'word_counter': 'Word Counter',
    'ocr': 'OCR & Text',
    'markdown': 'Markdown Studio',
    'palette': 'Color Palette',
    'collage': 'Photo Collage',
    'renamer': 'Batch Renamer',
    'metadata': 'Metadata Tools',
    'archive': 'Archive Manager',
    'office': 'Office Extractor',
    'screenshot': 'Screen Capture',
    'network_monitor': 'Network Monitor',
    'playlist': 'Playlist Porter',
    'resume': 'Resume & ATS',
    'qr': 'QR Codes & Barcodes',
    'hash': 'Hash & Checksum',
    'data': 'JSON & Data Tools',
    'text_tools': 'Text Tools',
    'encoding': 'Encoding / Decoding'
  };
  const titleText = titles[viewId] || 'Workspace';
  document.getElementById('current-view-title').textContent = titleText;

  const quickSelect = document.getElementById('workspace-quick-select');
  if (quickSelect && quickSelect.value !== viewId) {
    quickSelect.value = viewId;
  }

  // Update pinned toolbar highlight
  document.querySelectorAll('.quick-fav-item').forEach(fav => {
    if (fav.getAttribute('data-tool-id') === viewId) {
      fav.classList.add('active');
    } else {
      fav.classList.remove('active');
    }
  });
}

function renderPinnedTools() {
  const bar = document.getElementById('quick-favorites-bar');
  if (!bar) return;
  bar.innerHTML = '';

  const labels = {
    'pdf': 'PDF',
    'images': 'Images',
    'model3d': '3D STL',
    'media': 'Media',
    'converter': 'Convert',
    'qr': 'QR / Barcode',
    'renamer': 'Renamer',
    'markdown': 'Markdown',
    'hash': 'Hash',
    'data': 'Data',
    'palette': 'Palette',
    'resume': 'Resume'
  };

  pinnedTools.forEach(toolId => {
    const btn = document.createElement('div');
    btn.className = 'quick-fav-item';
    btn.setAttribute('data-tool-id', toolId);
    btn.textContent = labels[toolId] || toolId;
    btn.addEventListener('click', () => switchView(toolId));
    bar.appendChild(btn);
  });
}

// Subtabs switching
function setupSubtabs() {
  document.querySelectorAll('.tool-tabs').forEach(tabGroup => {
    const tabs = tabGroup.querySelectorAll('.tool-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Check for renmode
        const renmode = tab.getAttribute('data-renmode');
        if (renmode) {
          document.querySelectorAll('.ren-panel').forEach(p => p.style.display = 'none');
          const panel = document.getElementById(`renpanel-${renmode}`);
          if (panel) panel.style.display = 'block';
          return;
        }

        // Check for qrpreset
        const qrpreset = tab.getAttribute('data-qrpreset');
        if (qrpreset) {
          ['text', 'wifi', 'contact', 'email', 'sms'].forEach(p => {
            const el = document.getElementById(`qrpanel-${p}`);
            if (el) el.style.display = (p === qrpreset) ? 'block' : 'none';
          });
          return;
        }

        // Check for restab
        const restab = tab.getAttribute('data-restab');
        if (restab) {
          ['editor', 'ats', 'json'].forEach(r => {
            const el = document.getElementById(`restab-${r}`);
            if (el) el.style.display = (r === restab) ? 'block' : 'none';
          });
          return;
        }

        const targetId = tab.getAttribute('data-subtab');
        if (targetId) {
          const container = tabGroup.closest('.tool-container') || document;
          container.querySelectorAll('.subtab-content').forEach(content => {
            content.style.display = (content.id === `subtab-${targetId}` || content.id === targetId) ? 'block' : 'none';
          });
        }
      });
    });
  });
}

// Category filter buttons
function setupFilters() {
  const chips = document.querySelectorAll('.filter-chips .filter-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentFilter = chip.getAttribute('data-filter');
      filterAndRenderApps();
    });
  });
}

function filterAndRenderApps() {
  if (currentFilter === 'all') {
    renderApps(allApps);
  } else {
    const filtered = allApps.filter(app => app.category === currentFilter);
    renderApps(filtered);
  }
}

function renderApps(apps) {
  const container = document.getElementById('apps-container');
  if (!container) return;
  container.innerHTML = '';

  apps.forEach(app => {
    const card = document.createElement('div');
    card.className = 'app-card';
    card.innerHTML = `
      <div class="app-card-header">
        <span class="app-cat-tag">${app.category}</span>
      </div>
      <h3 class="app-card-title">${app.name}</h3>
      <p class="app-card-desc">${app.description}</p>
      <div class="app-card-footer">
        <span class="open-btn">Open Workspace &rarr;</span>
      </div>
    `;

    card.addEventListener('click', () => {
      switchView(app.id);
    });

    container.appendChild(card);
  });
}

// Command Palette (Ctrl+K and Ctrl+P)
function setupCommandPalette() {
  const modal = document.getElementById('palette-modal');
  const input = document.getElementById('palette-input');
  const results = document.getElementById('palette-results');
  const openBtn = document.getElementById('open-palette-btn');
  let selectedIdx = 0;

  function openPalette() {
    modal.style.display = 'flex';
    input.value = '';
    selectedIdx = 0;
    input.focus();
    renderPaletteResults('');
  }

  function closePalette() {
    modal.style.display = 'none';
  }

  if (openBtn) openBtn.addEventListener('click', openPalette);

  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'k' || e.key.toLowerCase() === 'p')) {
      e.preventDefault();
      if (modal.style.display === 'flex') closePalette();
      else openPalette();
    }
    if (e.key === 'Escape' && modal.style.display === 'flex') {
      closePalette();
    }
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closePalette();
  });

  input.addEventListener('input', () => {
    selectedIdx = 0;
    renderPaletteResults(input.value.trim());
  });

  input.addEventListener('keydown', (e) => {
    const items = results.querySelectorAll('.palette-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIdx = (selectedIdx + 1) % items.length;
      updatePaletteHighlight(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIdx = (selectedIdx - 1 + items.length) % items.length;
      updatePaletteHighlight(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[selectedIdx]) {
        items[selectedIdx].click();
      }
    }
  });

  function updatePaletteHighlight(items) {
    items.forEach((item, idx) => {
      if (idx === selectedIdx) item.classList.add('selected');
      else item.classList.remove('selected');
    });
  }

  function renderPaletteResults(query) {
    results.innerHTML = '';
    const q = query.toLowerCase();
    const matches = allApps.filter(a =>
      a.name.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      (a.keywords && a.keywords.some(k => k.toLowerCase().includes(q)))
    );

    matches.slice(0, 10).forEach((app, idx) => {
      const row = document.createElement('div');
      row.className = `palette-item ${idx === selectedIdx ? 'selected' : ''}`;
      row.innerHTML = `
        <div>
          <strong style="display: block; font-size: 14px;">${app.name}</strong>
          <span style="font-size: 12px; color: var(--text-muted);">${app.description}</span>
        </div>
        <span class="app-cat-tag">${app.category}</span>
      `;
      row.addEventListener('click', () => {
        closePalette();
        switchView(app.id);
      });
      results.appendChild(row);
    });
  }
}

// Settings Hub Modal
function setupSettingsHub() {
  const modal = document.getElementById('settings-modal');
  const openBtn = document.getElementById('open-settings-btn');
  const closeBtn = document.getElementById('close-settings-btn');

  function openSettings() {
    modal.style.display = 'flex';
    populatePinnedCheckboxes();
  }

  function closeSettings() {
    modal.style.display = 'none';
  }

  if (openBtn) openBtn.addEventListener('click', openSettings);
  if (closeBtn) closeBtn.addEventListener('click', closeSettings);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeSettings();
  });

  // Settings tabs
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.getAttribute('data-settab');
      ['appearance', 'shell', 'workspace'].forEach(p => {
        const panel = document.getElementById(`settab-${p}`);
        if (panel) panel.style.display = (p === target) ? 'block' : 'none';
      });
    });
  });

  // Appearance controls
  const themePreset = document.getElementById('settings-theme-preset');
  const accentColor = document.getElementById('settings-accent-color');
  const accentHex = document.getElementById('settings-accent-hex');
  const fontScale = document.getElementById('settings-font-scale');
  const fontVal = document.getElementById('settings-font-val');
  const borderRadius = document.getElementById('settings-border-radius');
  const radiusVal = document.getElementById('settings-radius-val');

  accentColor?.addEventListener('input', (e) => {
    accentHex.textContent = e.target.value;
    document.documentElement.style.setProperty('--accent', e.target.value);
  });

  fontScale?.addEventListener('input', (e) => {
    fontVal.textContent = `${e.target.value}px`;
    document.documentElement.style.setProperty('--font-base', `${e.target.value}px`);
  });

  borderRadius?.addEventListener('input', (e) => {
    radiusVal.textContent = `${e.target.value}px`;
    document.documentElement.style.setProperty('--radius-md', `${e.target.value}px`);
  });

  document.getElementById('settings-save-appearance-btn')?.addEventListener('click', () => {
    if (themePreset) applyTheme(themePreset.value);
    closeSettings();
  });

  // Shell integration
  document.getElementById('shell-save-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const ctxMenu = document.getElementById('shell-context-menu-chk')?.checked;
    if (ctxMenu) {
      await api.shell_register_context_menu();
    } else {
      await api.shell_unregister_context_menu();
    }

    const exts = [];
    if (document.getElementById('assoc-pdf')?.checked) exts.push('.pdf');
    if (document.getElementById('assoc-img')?.checked) exts.push('.png', '.jpg', '.jpeg', '.webp', '.svg');
    if (document.getElementById('assoc-media')?.checked) exts.push('.mp4', '.mkv', '.mp3', '.wav');
    if (document.getElementById('assoc-3d')?.checked) exts.push('.stl', '.obj', '.ply');
    if (document.getElementById('assoc-archive')?.checked) exts.push('.zip', '.tar', '.gz');
    if (document.getElementById('assoc-office')?.checked) exts.push('.docx', '.pptx', '.xlsx');

    await api.shell_set_file_associations(exts);
    alert('Shell integration applied successfully.');
    closeSettings();
  });

  // Workspace customization
  function populatePinnedCheckboxes() {
    const container = document.getElementById('pinned-tools-checkboxes');
    if (!container) return;
    container.innerHTML = '';

    allApps.forEach(app => {
      const lbl = document.createElement('label');
      lbl.style.display = 'flex';
      lbl.style.alignItems = 'center';
      lbl.style.gap = '6px';
      lbl.style.cursor = 'pointer';
      const isChecked = pinnedTools.includes(app.id);
      lbl.innerHTML = `<input type="checkbox" value="${app.id}" ${isChecked ? 'checked' : ''}> <span>${app.name}</span>`;
      container.appendChild(lbl);
    });
  }

  document.getElementById('settings-save-workspace-btn')?.addEventListener('click', () => {
    const checked = [];
    document.querySelectorAll('#pinned-tools-checkboxes input:checked').forEach(chk => {
      checked.push(chk.value);
    });
    pinnedTools = checked;
    renderPinnedTools();
    closeSettings();
  });
}

function showStatus(boxId, message, isError = false) {
  const box = document.getElementById(boxId);
  if (!box) return;
  box.style.display = 'block';
  box.className = `tool-card status-box ${isError ? 'error' : 'success'}`;
  box.textContent = message;
}

// -------------------------------------------------------------
// 1. PDF Studio & Visual Editor
// -------------------------------------------------------------
function setupPdfStudio() {
  const api = getApi();
  let currentPdfPath = '';
  let currentPdfPage = 0;
  let totalPdfPages = 0;
  let currentTool = 'select';
  let annotations = []; // {type, x, y, w, h, text, color, width, opacity}
  let isDrawing = false;
  let startX = 0, startY = 0;
  let zoomLevel = 1.0;

  const canvas = document.getElementById('pdf-annotation-canvas');
  const ctx = canvas?.getContext('2d');
  const pageImg = document.getElementById('pdf-page-img');
  const placeholder = document.getElementById('pdf-placeholder-msg');

  // Tool buttons
  document.querySelectorAll('#pdf-tool-group .tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#pdf-tool-group .tool-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTool = btn.getAttribute('data-tool');
    });
  });

  // Open PDF
  document.getElementById('pdf-view-open-btn')?.addEventListener('click', async () => {
    try {
      const files = await api.select_file(['PDF Files (*.pdf)'], false);
      if (files && files.length > 0) {
        await loadPdf(files[0]);
      }
    } catch (err) {
      console.error('Error opening PDF file dialog:', err);
      showStatus('pdf-status-box', `Failed to open PDF: ${err.message || err}`, true);
    }
  });

  const pdfStage = document.getElementById('pdf-stage');
  if (pdfStage) {
    pdfStage.addEventListener('dragover', (e) => {
      e.preventDefault();
      pdfStage.style.outline = '2px dashed var(--accent)';
    });
    pdfStage.addEventListener('dragleave', () => {
      pdfStage.style.outline = 'none';
    });
    pdfStage.addEventListener('drop', async (e) => {
      e.preventDefault();
      pdfStage.style.outline = 'none';
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.path) {
          await loadPdf(file.path);
        }
      }
    });
  }

  async function loadPdf(path) {
    if (!path) return;
    currentPdfPath = path;
    const docInfo = await api.pdf_open_doc(path);
    if (!docInfo || docInfo.error) {
      return showStatus('pdf-status-box', `Error opening PDF: ${docInfo?.error || 'Unknown error'}`, true);
    }
    totalPdfPages = docInfo.page_count;
    currentPdfPage = 0;
    showStatus('pdf-status-box', `Loaded: ${path} (${totalPdfPages} pages)`, false);
    await renderCurrentPage();
  }

  async function renderCurrentPage() {
    if (!currentPdfPath) return;
    const res = await api.pdf_render_page(currentPdfPath, currentPdfPage, Math.round(150 * zoomLevel));
    if (!res || res.error) {
      return showStatus('pdf-status-box', `Error rendering page: ${res?.error || 'Unknown error'}`, true);
    }

    placeholder.style.display = 'none';
    pageImg.style.display = 'block';

    const onImageLoaded = () => {
      canvas.width = res.width || pageImg.naturalWidth || 800;
      canvas.height = res.height || pageImg.naturalHeight || 1100;
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      redrawAnnotations();
    };

    pageImg.onload = onImageLoaded;
    pageImg.src = res.data_url;
    if (pageImg.complete && pageImg.naturalWidth) {
      onImageLoaded();
    }

    const indicator = document.getElementById('pdf-page-indicator');
    if (indicator) indicator.textContent = `Page ${currentPdfPage + 1} of ${totalPdfPages}`;
    const jumpInput = document.getElementById('pdf-jump-input');
    if (jumpInput) jumpInput.value = currentPdfPage + 1;
    const zoomVal = document.getElementById('pdf-zoom-val');
    if (zoomVal) zoomVal.textContent = `${Math.round(zoomLevel * 100)}%`;
  }

  function redrawAnnotations() {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    annotations.forEach(item => {
      ctx.save();
      ctx.globalAlpha = item.opacity || 1.0;
      ctx.lineWidth = item.width || 4;
      ctx.strokeStyle = item.color || '#ef4444';
      ctx.fillStyle = item.color || '#ef4444';

      if (item.type === 'rect') {
        ctx.strokeRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'highlight') {
        ctx.fillStyle = 'rgba(250, 204, 21, 0.4)';
        ctx.fillRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'redact') {
        ctx.fillStyle = '#000000';
        ctx.fillRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'text') {
        ctx.font = '16px sans-serif';
        ctx.fillText(item.text, item.x, item.y);
      } else if (item.type === 'draw' && item.points) {
        ctx.beginPath();
        item.points.forEach((pt, i) => {
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
      } else if (item.type === 'line') {
        ctx.beginPath();
        ctx.moveTo(item.x1, item.y1);
        ctx.lineTo(item.x2, item.y2);
        ctx.stroke();
      } else if (item.type === 'arrow') {
        drawArrow(ctx, item.x1, item.y1, item.x2, item.y2);
      }
      ctx.restore();
    });
  }

  function drawArrow(context, fromx, fromy, tox, toy) {
    const headlen = 10;
    const angle = Math.atan2(toy - fromy, tox - fromx);
    context.beginPath();
    context.moveTo(fromx, fromy);
    context.lineTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle - Math.PI / 6), toy - headlen * Math.sin(angle - Math.PI / 6));
    context.moveTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle + Math.PI / 6), toy - headlen * Math.sin(angle + Math.PI / 6));
    context.stroke();
  }

  // Navigation handlers
  document.getElementById('pdf-prev-page-btn')?.addEventListener('click', () => {
    if (currentPdfPage > 0) {
      currentPdfPage--;
      annotations = [];
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-next-page-btn')?.addEventListener('click', () => {
    if (currentPdfPage < totalPdfPages - 1) {
      currentPdfPage++;
      annotations = [];
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-first-page-btn')?.addEventListener('click', () => {
    if (currentPdfPage !== 0) {
      currentPdfPage = 0;
      annotations = [];
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-last-page-btn')?.addEventListener('click', () => {
    if (currentPdfPage !== totalPdfPages - 1 && totalPdfPages > 0) {
      currentPdfPage = totalPdfPages - 1;
      annotations = [];
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-jump-input')?.addEventListener('change', (e) => {
    const val = parseInt(e.target.value) - 1;
    if (val >= 0 && val < totalPdfPages) {
      currentPdfPage = val;
      annotations = [];
      renderCurrentPage();
    }
  });

  // Zoom handlers
  document.getElementById('pdf-zoom-in-btn')?.addEventListener('click', () => {
    if (zoomLevel < 3.0) {
      zoomLevel += 0.25;
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-zoom-out-btn')?.addEventListener('click', () => {
    if (zoomLevel > 0.5) {
      zoomLevel -= 0.25;
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-fit-width-btn')?.addEventListener('click', () => {
    zoomLevel = 1.25;
    renderCurrentPage();
  });

  document.getElementById('pdf-fit-page-btn')?.addEventListener('click', () => {
    zoomLevel = 1.0;
    renderCurrentPage();
  });

  // Page operations
  document.getElementById('pdf-rotate-cw-btn')?.addEventListener('click', async () => {
    if (!currentPdfPath) return;
    const res = await api.pdf_rotate_page(currentPdfPath, currentPdfPage, 90);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else renderCurrentPage();
  });

  document.getElementById('pdf-rotate-ccw-btn')?.addEventListener('click', async () => {
    if (!currentPdfPath) return;
    const res = await api.pdf_rotate_page(currentPdfPath, currentPdfPage, 270);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else renderCurrentPage();
  });

  document.getElementById('pdf-delete-curr-page-btn')?.addEventListener('click', async () => {
    if (!currentPdfPath || totalPdfPages <= 1) return alert('Cannot delete the only page in document.');
    const res = await api.pdf_delete_page(currentPdfPath, currentPdfPage);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else {
      totalPdfPages--;
      if (currentPdfPage >= totalPdfPages) currentPdfPage = totalPdfPages - 1;
      renderCurrentPage();
    }
  });

  document.getElementById('pdf-extract-curr-page-btn')?.addEventListener('click', async () => {
    if (!currentPdfPath) return;
    const out = await api.select_save_file('extracted_page.pdf', ['PDF Files (*.pdf)']);
    if (out) {
      const res = await api.pdf_extract_single_page(currentPdfPath, currentPdfPage, out);
      if (res.error) showStatus('pdf-status-box', res.error, true);
      else showStatus('pdf-status-box', `Page extracted to ${out}`);
    }
  });

  // Canvas Mouse Interactions
  let currentStroke = [];
  canvas?.addEventListener('mousedown', (e) => {
    if (currentTool === 'select') return;
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
    const color = document.getElementById('pdf-draw-color').value;
    const width = parseInt(document.getElementById('pdf-draw-size').value) || 4;
    const opacity = parseFloat(document.getElementById('pdf-draw-opacity').value) || 1.0;

    if (currentTool === 'draw') {
      currentStroke = [{ x: startX, y: startY }];
    } else if (currentTool === 'text') {
      const text = prompt('Enter annotation text:');
      if (text) {
        annotations.push({ type: 'text', text, x: startX, y: startY, color, opacity });
        redrawAnnotations();
      }
      isDrawing = false;
    } else if (currentTool === 'erase') {
      // Find and remove clicked annotation
      annotations.pop();
      redrawAnnotations();
      isDrawing = false;
    }
  });

  canvas?.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const currX = e.clientX - rect.left;
    const currY = e.clientY - rect.top;
    const color = document.getElementById('pdf-draw-color').value;
    const width = parseInt(document.getElementById('pdf-draw-size').value) || 4;
    const opacity = parseFloat(document.getElementById('pdf-draw-opacity').value) || 1.0;

    if (currentTool === 'draw') {
      currentStroke.push({ x: currX, y: currY });
      redrawAnnotations();
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.beginPath();
      currentStroke.forEach((pt, i) => {
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
      ctx.restore();
    } else if (currentTool === 'rect' || currentTool === 'highlight' || currentTool === 'redact') {
      redrawAnnotations();
      ctx.save();
      ctx.globalAlpha = opacity;
      if (currentTool === 'highlight') {
        ctx.fillStyle = 'rgba(250, 204, 21, 0.4)';
        ctx.fillRect(startX, startY, currX - startX, currY - startY);
      } else if (currentTool === 'redact') {
        ctx.fillStyle = '#000000';
        ctx.fillRect(startX, startY, currX - startX, currY - startY);
      } else {
        ctx.lineWidth = width;
        ctx.strokeStyle = color;
        ctx.strokeRect(startX, startY, currX - startX, currY - startY);
      }
      ctx.restore();
    } else if (currentTool === 'line') {
      redrawAnnotations();
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(currX, currY);
      ctx.stroke();
      ctx.restore();
    } else if (currentTool === 'arrow') {
      redrawAnnotations();
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      drawArrow(ctx, startX, startY, currX, currY);
      ctx.restore();
    }
  });

  canvas?.addEventListener('mouseup', (e) => {
    if (!isDrawing) return;
    isDrawing = false;
    const rect = canvas.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;
    const color = document.getElementById('pdf-draw-color').value;
    const width = parseInt(document.getElementById('pdf-draw-size').value) || 4;
    const opacity = parseFloat(document.getElementById('pdf-draw-opacity').value) || 1.0;

    if (currentTool === 'draw') {
      annotations.push({ type: 'draw', points: currentStroke, color, width, opacity });
    } else if (currentTool === 'rect') {
      annotations.push({ type: 'rect', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY), color, width, opacity });
    } else if (currentTool === 'highlight') {
      annotations.push({ type: 'highlight', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY), color, opacity });
    } else if (currentTool === 'redact') {
      annotations.push({ type: 'redact', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY), color, opacity });
    } else if (currentTool === 'line') {
      annotations.push({ type: 'line', x1: startX, y1: startY, x2: endX, y2: endY, color, width, opacity });
    } else if (currentTool === 'arrow') {
      annotations.push({ type: 'arrow', x1: startX, y1: startY, x2: endX, y2: endY, color, width, opacity });
    }
    redrawAnnotations();
  });

  document.getElementById('pdf-undo-btn')?.addEventListener('click', () => {
    annotations.pop();
    redrawAnnotations();
  });

  document.getElementById('pdf-clear-btn')?.addEventListener('click', () => {
    annotations = [];
    redrawAnnotations();
  });

  // Save annotated PDF
  document.getElementById('pdf-save-annotated-btn')?.addEventListener('click', async () => {
    if (!currentPdfPath) return;
    const out = await api.select_save_file('annotated_doc.pdf', ['PDF Files (*.pdf)']);
    if (out) {
      const res = await api.pdf_save_annotated_page(currentPdfPath, currentPdfPage, annotations, out, 150);
      if (res.error) showStatus('pdf-status-box', res.error, true);
      else showStatus('pdf-status-box', `Annotated PDF saved to ${out}`);
    }
  });

  // Subtab: Merge
  document.getElementById('pdf-merge-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], true);
    if (files) document.getElementById('pdf-merge-paths').value = files.join('; ');
  });

  document.getElementById('pdf-merge-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('merged.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-merge-output').value = dest;
  });

  document.getElementById('pdf-merge-run-btn')?.addEventListener('click', async () => {
    const rawPaths = document.getElementById('pdf-merge-paths').value;
    const out = document.getElementById('pdf-merge-output').value;
    if (!rawPaths || !out) return alert('Select files and output destination.');
    const files = rawPaths.split(';').map(s => s.trim()).filter(Boolean);
    const res = await api.pdf_merge(files, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Successfully merged ${files.length} PDFs into ${out}`);
  });

  // Subtab: Split
  document.getElementById('pdf-split-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-split-input').value = files[0];
  });

  document.getElementById('pdf-split-folder-btn')?.addEventListener('click', async () => {
    const dir = await api.select_directory();
    if (dir) document.getElementById('pdf-split-output-dir').value = dir;
  });

  document.getElementById('pdf-split-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-split-input').value;
    const outDir = document.getElementById('pdf-split-output-dir').value;
    const ranges = document.getElementById('pdf-split-ranges').value;
    if (!input || !outDir) return alert('Select input PDF and output folder.');
    const res = await api.pdf_split(input, ranges, outDir);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Split complete: ${res.files.length} files generated.`);
  });

  // Subtab: Compress
  document.getElementById('pdf-compress-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-compress-input').value = files[0];
  });

  document.getElementById('pdf-compress-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('compressed.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-compress-output').value = dest;
  });

  document.getElementById('pdf-compress-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-compress-input').value;
    const out = document.getElementById('pdf-compress-output').value;
    const level = document.getElementById('pdf-compress-level').value;
    if (!input || !out) return alert('Select input and output path.');
    const res = await api.pdf_compress(input, level, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `PDF compressed. New size: ${(res.new_size / 1024).toFixed(1)} KB`);
  });

  // Subtab: Watermark
  document.getElementById('pdf-wm-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-wm-input').value = files[0];
  });

  document.getElementById('pdf-wm-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('watermarked.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-wm-output').value = dest;
  });

  document.getElementById('pdf-wm-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-wm-input').value;
    const text = document.getElementById('pdf-wm-text').value;
    const out = document.getElementById('pdf-wm-output').value;
    const size = parseInt(document.getElementById('pdf-wm-size').value) || 48;
    const opacity = parseFloat(document.getElementById('pdf-wm-opacity').value) || 0.3;
    const angle = parseInt(document.getElementById('pdf-wm-angle').value) || 45;
    if (!input || !text || !out) return alert('Fill in input, watermark text, and output path.');
    const res = await api.pdf_watermark(input, text, out, opacity, size, angle);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Watermarked PDF saved to ${out}`);
  });

  // Subtab: Protect
  document.getElementById('pdf-prot-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-prot-input').value = files[0];
  });

  document.getElementById('pdf-prot-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('protected.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-prot-output').value = dest;
  });

  document.getElementById('pdf-prot-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-prot-input').value;
    const pass = document.getElementById('pdf-prot-password').value;
    const out = document.getElementById('pdf-prot-output').value;
    if (!input || !pass || !out) return alert('Select file, enter password, and select output.');
    const res = await api.pdf_protect(input, pass, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `PDF encrypted and protected.`);
  });

  // Subtab: Unlock
  document.getElementById('pdf-unlock-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-unlock-input').value = files[0];
  });

  document.getElementById('pdf-unlock-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('unlocked.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-unlock-output').value = dest;
  });

  document.getElementById('pdf-unlock-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-unlock-input').value;
    const pass = document.getElementById('pdf-unlock-password').value;
    const out = document.getElementById('pdf-unlock-output').value;
    if (!input || !out) return alert('Select encrypted PDF and output path.');
    const res = await api.pdf_unlock(input, pass, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `PDF unlocked successfully.`);
  });

  // Subtab: Page Numbers
  document.getElementById('pdf-pagenums-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-pagenums-input').value = files[0];
  });

  document.getElementById('pdf-pagenums-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('numbered.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-pagenums-output').value = dest;
  });

  document.getElementById('pdf-pagenums-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-pagenums-input').value;
    const out = document.getElementById('pdf-pagenums-output').value;
    const fmt = document.getElementById('pdf-pagenums-fmt').value;
    const pos = document.getElementById('pdf-pagenums-pos').value;
    if (!input || !out) return alert('Select input and output path.');
    const res = await api.pdf_stamp_numbers(input, fmt, pos, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Page numbers stamped to ${out}`);
  });

  // Subtab: Reorder Pages
  document.getElementById('pdf-reorder-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-reorder-input').value = files[0];
  });

  document.getElementById('pdf-reorder-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('reordered.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-reorder-output').value = dest;
  });

  document.getElementById('pdf-reorder-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-reorder-input').value;
    const orderStr = document.getElementById('pdf-reorder-order').value;
    const out = document.getElementById('pdf-reorder-output').value;
    if (!input || !orderStr || !out) return alert('Select input, order, and destination.');
    const pages = orderStr.split(',').map(s => parseInt(s.trim()) - 1).filter(n => !isNaN(n));
    const res = await api.pdf_reorder_pages(input, pages, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Pages reorganized into ${out}`);
  });

  // Subtab: Searchable PDF (OCR)
  document.getElementById('pdf-ocr-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-ocr-input').value = files[0];
  });

  document.getElementById('pdf-ocr-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('searchable.pdf', ['PDF Files (*.pdf)']);
    if (dest) document.getElementById('pdf-ocr-output').value = dest;
  });

  document.getElementById('pdf-ocr-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-ocr-input').value;
    const lang = document.getElementById('pdf-ocr-lang').value;
    const out = document.getElementById('pdf-ocr-output').value;
    if (!input || !out) return alert('Select input and output path.');
    showStatus('pdf-status-box', 'Running OCR engine on PDF pages...');
    const res = await api.pdf_create_searchable_pdf(input, out, lang);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `Searchable PDF created at ${out}`);
  });

  // Subtab: DOCX conversion
  document.getElementById('pdf-docx-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-docx-input').value = files[0];
  });

  document.getElementById('pdf-docx-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('converted.docx', ['Word Document (*.docx)']);
    if (dest) document.getElementById('pdf-docx-output').value = dest;
  });

  document.getElementById('pdf-docx-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-docx-input').value;
    const out = document.getElementById('pdf-docx-output').value;
    if (!input || !out) return alert('Select PDF and DOCX output destination.');
    const res = await api.pdf_to_docx(input, out);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else showStatus('pdf-status-box', `PDF converted to Word document at ${out}`);
  });

  // Subtab: Extract Text
  document.getElementById('pdf-ext-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['PDF Files (*.pdf)'], false);
    if (files) document.getElementById('pdf-ext-input').value = files[0];
  });

  document.getElementById('pdf-ext-run-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('pdf-ext-input').value;
    if (!input) return alert('Select a PDF to extract text.');
    const res = await api.pdf_extract_text(input);
    if (res.error) showStatus('pdf-status-box', res.error, true);
    else {
      document.getElementById('pdf-ext-card').style.display = 'block';
      document.getElementById('pdf-ext-output').value = res.text;
    }
  });

  document.getElementById('pdf-ext-copy-btn')?.addEventListener('click', () => {
    const txt = document.getElementById('pdf-ext-output').value;
    navigator.clipboard.writeText(txt);
    alert('Extracted text copied to clipboard.');
  });
}

// -------------------------------------------------------------
// 2. Image Studio & Interactive Canvas Editor
// -------------------------------------------------------------
function setupImageStudio() {
  const api = getApi();
  let currentImgPath = '';
  let imgObj = null;
  let currentImgTool = 'select';
  let isImgDrawing = false;
  let startX = 0, startY = 0;
  let imgAnnotations = []; // {type, x, y, w, h, text, color, size}
  let currentAngle = 0;

  const canvas = document.getElementById('image-editor-canvas');
  const ctx = canvas?.getContext('2d');
  const placeholder = document.getElementById('img-placeholder-msg');
  const cropBox = document.getElementById('img-crop-box');

  // Tool buttons
  document.querySelectorAll('#img-tool-group .tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#img-tool-group .tool-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentImgTool = btn.getAttribute('data-imgtool');
      if (currentImgTool === 'crop') {
        cropBox.style.display = 'block';
        document.getElementById('img-apply-crop-btn').style.display = 'inline-block';
        initCropBox();
      } else {
        cropBox.style.display = 'none';
        document.getElementById('img-apply-crop-btn').style.display = 'none';
      }
    });
  });

  function initCropBox() {
    if (!canvas) return;
    const aspect = document.getElementById('img-crop-aspect').value;
    let w = canvas.width * 0.7;
    let h = canvas.height * 0.7;
    if (aspect === '1:1' || aspect === 'circle') {
      const s = Math.min(w, h);
      w = s; h = s;
    } else if (aspect === '16:9') {
      h = w * 9 / 16;
    } else if (aspect === '4:3') {
      h = w * 3 / 4;
    } else if (aspect === '4:5') {
      w = h * 4 / 5;
    }
    cropBox.style.width = `${w}px`;
    cropBox.style.height = `${h}px`;
    cropBox.style.left = `${(canvas.width - w) / 2}px`;
    cropBox.style.top = `${(canvas.height - h) / 2}px`;
    if (aspect === 'circle') {
      cropBox.style.borderRadius = '50%';
    } else {
      cropBox.style.borderRadius = '0';
    }
  }

  document.getElementById('img-crop-aspect')?.addEventListener('change', initCropBox);

  // Open Image
  document.getElementById('img-open-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Image Files (*.png;*.jpg;*.jpeg;*.webp;*.bmp)'], false);
    if (files && files.length > 0) {
      loadImage(files[0]);
    }
  });

  async function loadImage(path) {
    currentImgPath = path;
    const res = await api.image_load_preview(path);
    if (res.error) return showStatus('img-status-box', res.error, true);

    imgObj = new Image();
    imgObj.onload = () => {
      placeholder.style.display = 'none';
      canvas.width = imgObj.width;
      canvas.height = imgObj.height;
      redrawImageCanvas();
    };
    imgObj.src = res.data_url;
  }

  function redrawImageCanvas() {
    if (!ctx || !imgObj) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply CSS filters from sliders
    const bright = document.getElementById('img-filter-bright').value;
    const contrast = document.getElementById('img-filter-contrast').value;
    const saturate = document.getElementById('img-filter-saturate').value;
    const blur = document.getElementById('img-filter-blur').value;
    ctx.filter = `brightness(${bright}) contrast(${contrast}) saturate(${saturate}) blur(${blur}px)`;

    ctx.drawImage(imgObj, 0, 0, canvas.width, canvas.height);
    ctx.filter = 'none';

    // Redraw markup annotations
    imgAnnotations.forEach(item => {
      ctx.lineWidth = item.size || 4;
      ctx.strokeStyle = item.color || '#3b82f6';
      ctx.fillStyle = item.color || '#3b82f6';

      if (item.type === 'rect') {
        ctx.strokeRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'line') {
        ctx.beginPath();
        ctx.moveTo(item.x1, item.y1);
        ctx.lineTo(item.x2, item.y2);
        ctx.stroke();
      } else if (item.type === 'arrow') {
        drawImgArrow(ctx, item.x1, item.y1, item.x2, item.y2);
      } else if (item.type === 'blur') {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'pixelate') {
        ctx.fillStyle = '#64748b';
        ctx.fillRect(item.x, item.y, item.w, item.h);
      } else if (item.type === 'text') {
        ctx.font = '20px sans-serif';
        ctx.fillText(item.text, item.x, item.y);
      } else if (item.type === 'draw' && item.points) {
        ctx.beginPath();
        item.points.forEach((pt, i) => {
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
      }
    });
  }

  function drawImgArrow(context, fromx, fromy, tox, toy) {
    const headlen = 12;
    const angle = Math.atan2(toy - fromy, tox - fromx);
    context.beginPath();
    context.moveTo(fromx, fromy);
    context.lineTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle - Math.PI / 6), toy - headlen * Math.sin(angle - Math.PI / 6));
    context.moveTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle + Math.PI / 6), toy - headlen * Math.sin(angle + Math.PI / 6));
    context.stroke();
  }

  // Filter Sliders
  ['img-filter-bright', 'img-filter-contrast', 'img-filter-saturate', 'img-filter-blur'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', redrawImageCanvas);
  });

  // Filter Presets
  document.getElementById('img-preset-auto')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const res = await api.image_auto_enhance(currentImgPath);
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  document.getElementById('img-preset-vivid')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '1.1';
    document.getElementById('img-filter-contrast').value = '1.3';
    document.getElementById('img-filter-saturate').value = '1.6';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-warm')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '1.05';
    document.getElementById('img-filter-contrast').value = '1.1';
    document.getElementById('img-filter-saturate').value = '1.3';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-cool')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '0.95';
    document.getElementById('img-filter-contrast').value = '1.15';
    document.getElementById('img-filter-saturate').value = '0.8';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-grayscale')?.addEventListener('click', () => {
    document.getElementById('img-filter-saturate').value = '0.0';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-bw')?.addEventListener('click', () => {
    document.getElementById('img-filter-saturate').value = '0.0';
    document.getElementById('img-filter-contrast').value = '2.0';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-sepia')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '0.9';
    document.getElementById('img-filter-contrast').value = '1.2';
    document.getElementById('img-filter-saturate').value = '0.5';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-vintage')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '1.1';
    document.getElementById('img-filter-contrast').value = '0.9';
    document.getElementById('img-filter-saturate').value = '0.7';
    redrawImageCanvas();
  });

  document.getElementById('img-preset-invert')?.addEventListener('click', () => {
    ctx.filter = 'invert(1)';
    ctx.drawImage(imgObj, 0, 0);
    ctx.filter = 'none';
  });

  document.getElementById('img-reset-filters')?.addEventListener('click', () => {
    document.getElementById('img-filter-bright').value = '1.0';
    document.getElementById('img-filter-contrast').value = '1.0';
    document.getElementById('img-filter-saturate').value = '1.0';
    document.getElementById('img-filter-blur').value = '0';
    redrawImageCanvas();
  });

  // Rotation & Flip
  document.getElementById('img-rotate-right-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const res = await api.image_rotate(currentImgPath, -90);
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  document.getElementById('img-rotate-left-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const res = await api.image_rotate(currentImgPath, 90);
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  document.getElementById('img-rotate-angle')?.addEventListener('input', (e) => {
    document.getElementById('img-rotate-angle-val').textContent = `${e.target.value}°`;
  });

  document.getElementById('img-apply-angle-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const angle = parseFloat(document.getElementById('img-rotate-angle').value);
    const res = await api.image_rotate(currentImgPath, angle);
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  document.getElementById('img-flip-horiz-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const res = await api.image_flip(currentImgPath, 'horizontal');
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  document.getElementById('img-flip-vert-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const res = await api.image_flip(currentImgPath, 'vertical');
    if (res.data_url) {
      imgObj.src = res.data_url;
    }
  });

  // Background tools
  document.getElementById('img-rmbg-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const model = document.getElementById('img-rmbg-model').value;
    showStatus('img-status-box', 'Running background removal model...');
    const res = await api.image_remove_background(currentImgPath, model);
    if (res.data_url) {
      imgObj.src = res.data_url;
      showStatus('img-status-box', 'Background removed successfully.');
    } else if (res.error) {
      showStatus('img-status-box', res.error, true);
    }
  });

  document.getElementById('img-replace-bg-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const color = document.getElementById('img-bg-color').value;
    const res = await api.image_replace_background_color(currentImgPath, color);
    if (res.data_url) {
      imgObj.src = res.data_url;
      showStatus('img-status-box', 'Background color replaced.');
    }
  });

  // Border & Polaroid
  document.getElementById('img-apply-border-btn')?.addEventListener('click', async () => {
    if (!currentImgPath) return;
    const width = parseInt(document.getElementById('img-border-width').value) || 12;
    const color = document.getElementById('img-border-color').value;
    const isPolaroid = document.getElementById('img-polaroid-chk').checked;
    const res = await api.image_add_border(currentImgPath, width, color, isPolaroid);
    if (res.data_url) {
      imgObj.src = res.data_url;
      showStatus('img-status-box', 'Border applied.');
    }
  });

  // Apply Crop
  document.getElementById('img-apply-crop-btn')?.addEventListener('click', async () => {
    if (!currentImgPath || !canvas) return;
    const aspect = document.getElementById('img-crop-aspect').value;
    const boxX = parseInt(cropBox.style.left) || 0;
    const boxY = parseInt(cropBox.style.top) || 0;
    const boxW = parseInt(cropBox.style.width) || canvas.width;
    const boxH = parseInt(cropBox.style.height) || canvas.height;

    if (aspect === 'circle') {
      const res = await api.image_circle_crop(currentImgPath);
      if (res.data_url) imgObj.src = res.data_url;
    } else {
      const res = await api.image_crop(currentImgPath, [boxX, boxY, boxX + boxW, boxY + boxH]);
      if (res.data_url) imgObj.src = res.data_url;
    }
    cropBox.style.display = 'none';
    document.getElementById('img-apply-crop-btn').style.display = 'none';
  });

  // Canvas markup
  let currentImgStroke = [];
  canvas?.addEventListener('mousedown', (e) => {
    if (currentImgTool === 'select' || currentImgTool === 'crop') return;
    isImgDrawing = true;
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
    const color = document.getElementById('img-draw-color').value;
    const size = parseInt(document.getElementById('img-draw-size').value) || 4;

    if (currentImgTool === 'draw') {
      currentImgStroke = [{ x: startX, y: startY }];
    } else if (currentImgTool === 'text') {
      const text = prompt('Enter annotation text:');
      if (text) {
        imgAnnotations.push({ type: 'text', text, x: startX, y: startY, color });
        redrawImageCanvas();
      }
      isImgDrawing = false;
    }
  });

  canvas?.addEventListener('mousemove', (e) => {
    if (!isImgDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const currX = e.clientX - rect.left;
    const currY = e.clientY - rect.top;
    const color = document.getElementById('img-draw-color').value;
    const size = parseInt(document.getElementById('img-draw-size').value) || 4;

    if (currentImgTool === 'draw') {
      currentImgStroke.push({ x: currX, y: currY });
      redrawImageCanvas();
      ctx.lineWidth = size;
      ctx.strokeStyle = color;
      ctx.beginPath();
      currentImgStroke.forEach((pt, i) => {
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
    } else if (currentImgTool === 'rect' || currentImgTool === 'blur' || currentImgTool === 'pixelate') {
      redrawImageCanvas();
      if (currentImgTool === 'blur') {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(startX, startY, currX - startX, currY - startY);
      } else if (currentImgTool === 'pixelate') {
        ctx.fillStyle = '#64748b';
        ctx.fillRect(startX, startY, currX - startX, currY - startY);
      } else {
        ctx.lineWidth = size;
        ctx.strokeStyle = color;
        ctx.strokeRect(startX, startY, currX - startX, currY - startY);
      }
    } else if (currentImgTool === 'line') {
      redrawImageCanvas();
      ctx.lineWidth = size;
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(currX, currY);
      ctx.stroke();
    } else if (currentImgTool === 'arrow') {
      redrawImageCanvas();
      ctx.lineWidth = size;
      ctx.strokeStyle = color;
      drawImgArrow(ctx, startX, startY, currX, currY);
    }
  });

  canvas?.addEventListener('mouseup', (e) => {
    if (!isImgDrawing) return;
    isImgDrawing = false;
    const rect = canvas.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;
    const color = document.getElementById('img-draw-color').value;
    const size = parseInt(document.getElementById('img-draw-size').value) || 4;

    if (currentImgTool === 'draw') {
      imgAnnotations.push({ type: 'draw', points: currentImgStroke, color, size });
    } else if (currentImgTool === 'rect') {
      imgAnnotations.push({ type: 'rect', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY), color, size });
    } else if (currentImgTool === 'blur') {
      imgAnnotations.push({ type: 'blur', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY) });
    } else if (currentImgTool === 'pixelate') {
      imgAnnotations.push({ type: 'pixelate', x: Math.min(startX, endX), y: Math.min(startY, endY), w: Math.abs(endX - startX), h: Math.abs(endY - startY) });
    } else if (currentImgTool === 'line') {
      imgAnnotations.push({ type: 'line', x1: startX, y1: startY, x2: endX, y2: endY, color, size });
    } else if (currentImgTool === 'arrow') {
      imgAnnotations.push({ type: 'arrow', x1: startX, y1: startY, x2: endX, y2: endY, color, size });
    }
    redrawImageCanvas();
  });

  document.getElementById('img-canvas-undo-btn')?.addEventListener('click', () => {
    imgAnnotations.pop();
    redrawImageCanvas();
  });

  // Save Canvas Image
  document.getElementById('img-save-canvas-btn')?.addEventListener('click', async () => {
    if (!canvas) return;
    const dest = await api.select_save_file('edited_image.png', ['PNG Image (*.png)', 'JPEG Image (*.jpg)', 'WebP Image (*.webp)']);
    if (dest) {
      const dataUrl = canvas.toDataURL('image/png');
      const base64Data = dataUrl.split(',')[1];
      const res = await api.image_save_canvas(base64Data, dest);
      if (res.error) showStatus('img-status-box', res.error, true);
      else showStatus('img-status-box', `Image saved to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 3. 3D Model & STL Studio (Interactive WebGL Viewport)
// -------------------------------------------------------------
function setupModel3D() {
  const api = getApi();
  let currentModelPath = '';
  let meshData = null;
  let isOrbiting = false;
  let isPanning = false;
  let isMeasuring = false;
  let measurePtA = null;
  let measurePtB = null;
  let lastMouseX = 0, lastMouseY = 0;
  let clickStartX = 0, clickStartY = 0;
  let rotX = 25, rotY = 45;
  let panX = 0, panY = 0;
  let zoomDist = 200;
  let renderMode = 'solid';
  let cachedProjVerts = [];

  const canvas = document.getElementById('model3d-webgl-canvas');
  const ctx = canvas?.getContext('2d');
  const placeholder = document.getElementById('m3d-placeholder');

  document.getElementById('m3d-render-mode')?.addEventListener('change', (e) => {
    renderMode = e.target.value;
    render3DViewport();
  });

  document.getElementById('m3d-reset-cam-btn')?.addEventListener('click', () => {
    rotX = 25; rotY = 45;
    panX = 0; panY = 0;
    zoomDist = 200;
    render3DViewport();
  });

  document.getElementById('m3d-measure-btn')?.addEventListener('click', () => {
    isMeasuring = !isMeasuring;
    const btn = document.getElementById('m3d-measure-btn');
    if (isMeasuring) {
      if (btn) {
        btn.classList.add('active');
        btn.style.background = '#2563eb';
        btn.style.color = '#ffffff';
      }
      measurePtA = null;
      measurePtB = null;
      showStatus('m3d-status-box', 'Measure Mode: Click first point on model.');
    } else {
      if (btn) {
        btn.classList.remove('active');
        btn.style.background = '';
        btn.style.color = '';
      }
      showStatus('m3d-status-box', 'Measure Mode deactivated.');
    }
    render3DViewport();
  });

  document.getElementById('m3d-open-file-btn')?.addEventListener('click', async () => {
    const files = await api.select_file([
      '3D Models (*.stl;*.obj;*.ply;*.step;*.stp;*.iges;*.igs)',
      'Mesh Files (*.stl;*.obj;*.ply)',
      'CAD Files (*.step;*.stp;*.iges;*.igs)',
      'All Files (*.*)'
    ], false);
    if (files && files.length > 0) {
      load3DModel(files[0]);
    }
  });

  async function load3DModel(path) {
    currentModelPath = path;
    const res = await api.model3d_load_mesh(path);
    if (res.error) return showStatus('m3d-status-box', res.error, true);

    meshData = res;
    measurePtA = null;
    measurePtB = null;
    const measureStat = document.getElementById('m3d-stat-measure');
    if (measureStat) measureStat.textContent = '-';
    if (placeholder) placeholder.style.display = 'none';

    document.getElementById('m3d-stat-faces').textContent = res.faces_count?.toLocaleString() || '0';
    document.getElementById('m3d-stat-verts').textContent = res.vertices_count?.toLocaleString() || '0';
    document.getElementById('m3d-stat-watertight').textContent = res.is_watertight ? 'Yes' : 'No';
    document.getElementById('m3d-stat-volume').textContent = res.volume ? `${res.volume.toFixed(1)}` : 'N/A';
    document.getElementById('m3d-stat-area').textContent = res.surface_area ? `${res.surface_area.toFixed(1)}` : 'N/A';
    if (res.dimensions) {
      document.getElementById('m3d-stat-dims').textContent = `${res.dimensions[0].toFixed(1)} × ${res.dimensions[1].toFixed(1)} × ${res.dimensions[2].toFixed(1)}`;
    }

    resizeCanvas();
    render3DViewport();
  }

  function resizeCanvas() {
    if (!canvas || !canvas.parentElement) return;
    canvas.width = canvas.parentElement.clientWidth || 800;
    canvas.height = Math.max(520, canvas.parentElement.clientHeight || 520);
  }

  window.addEventListener('resize', () => {
    if (canvas) {
      resizeCanvas();
      render3DViewport();
    }
  });

  canvas?.addEventListener('mousedown', (e) => {
    clickStartX = e.clientX;
    clickStartY = e.clientY;
    if (e.button === 0 && !isMeasuring) isOrbiting = true;
    else if (e.button === 2) isPanning = true;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isOrbiting && !isPanning) return;
    const dx = e.clientX - lastMouseX;
    const dy = e.clientY - lastMouseY;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;

    if (isOrbiting) {
      rotY += dx * 0.5;
      rotX += dy * 0.5;
      rotX = Math.max(-89, Math.min(89, rotX));
    } else if (isPanning) {
      panX += dx;
      panY += dy;
    }
    render3DViewport();
  });

  window.addEventListener('mouseup', async (e) => {
    const distMoved = Math.hypot(e.clientX - clickStartX, e.clientY - clickStartY);
    if (isMeasuring && e.button === 0 && distMoved < 5 && meshData && meshData.vertices) {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const picked = pickClosestVertex(mx, my);
      if (picked) {
        if (!measurePtA) {
          measurePtA = picked;
          showStatus('m3d-status-box', `Point A: [${picked.coords[0].toFixed(1)}, ${picked.coords[1].toFixed(1)}, ${picked.coords[2].toFixed(1)}]. Click Point B.`);
        } else {
          measurePtB = picked;
          const distRes = await api.model3d_measure(measurePtA.coords, measurePtB.coords);
          const dist = distRes.distance !== undefined ? distRes.distance : Math.hypot(
            measurePtA.coords[0] - measurePtB.coords[0],
            measurePtA.coords[1] - measurePtB.coords[1],
            measurePtA.coords[2] - measurePtB.coords[2]
          );
          const measureStat = document.getElementById('m3d-stat-measure');
          if (measureStat) measureStat.textContent = `${dist.toFixed(2)} mm`;
          showStatus('m3d-status-box', `Distance: ${dist.toFixed(2)} mm (Point A to Point B). Click to measure again.`);
        }
        render3DViewport();
      }
    }
    isOrbiting = false;
    isPanning = false;
  });

  function pickClosestVertex(mx, my) {
    if (!meshData || !meshData.vertices || !cachedProjVerts.length) return null;
    let bestIdx = -1;
    let bestDist = 35;
    for (let i = 0; i < cachedProjVerts.length; i++) {
      const p = cachedProjVerts[i];
      if (!p) continue;
      const d = Math.hypot(p.x - mx, p.y - my);
      if (d < bestDist) {
        bestDist = d;
        bestIdx = i;
      }
    }
    if (bestIdx < 0) return null;
    const raw = meshData.vertices;
    const nx = raw[bestIdx * 3];
    const ny = raw[bestIdx * 3 + 1];
    const nz = raw[bestIdx * 3 + 2];
    const dims = meshData.dimensions || [10, 10, 10];
    const bmin = meshData.bounds_min || [0, 0, 0];
    return {
      norm: [nx, ny, nz],
      coords: [
        bmin[0] + (nx + 1) * 0.5 * dims[0],
        bmin[1] + (ny + 1) * 0.5 * dims[1],
        bmin[2] + (nz + 1) * 0.5 * dims[2]
      ]
    };
  }

  canvas?.addEventListener('wheel', (e) => {
    e.preventDefault();
    zoomDist += e.deltaY * 0.2;
    zoomDist = Math.max(30, Math.min(600, zoomDist));
    render3DViewport();
  });

  canvas?.addEventListener('contextmenu', (e) => e.preventDefault());

  function project3D(x, y, z, rx, ry, cx, cy, zoom) {
    const x1 = x * Math.cos(ry) + z * Math.sin(ry);
    const z1 = -x * Math.sin(ry) + z * Math.cos(ry);
    const y2 = y * Math.cos(rx) - z1 * Math.sin(rx);
    const z2 = y * Math.sin(rx) + z1 * Math.cos(rx);

    const fov = 350;
    const scale = fov / (fov + z2 + zoom);
    return {
      x: cx + x1 * scale,
      y: cy - y2 * scale,
      z: z2
    };
  }

  function render3DViewport() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
    grad.addColorStop(0, '#0a0f1d');
    grad.addColorStop(1, '#050811');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const cx = canvas.width / 2 + panX;
    const cy = canvas.height / 2 + panY;
    const radX = (rotX * Math.PI) / 180;
    const radY = (rotY * Math.PI) / 180;

    // Draw coordinate grid floor
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 1;
    for (let i = -100; i <= 100; i += 20) {
      const p1 = project3D(i, -60, -100, radX, radY, cx, cy, zoomDist);
      const p2 = project3D(i, -60, 100, radX, radY, cx, cy, zoomDist);
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }

    if (!meshData || !meshData.vertices || meshData.vertices.length === 0) return;

    const rawVerts = meshData.vertices;
    const numVerts = (rawVerts.length / 3) | 0;
    const modelScale = 80;

    cachedProjVerts = new Array(numVerts);
    for (let i = 0; i < numVerts; i++) {
      const vx = rawVerts[i * 3] * modelScale;
      const vy = rawVerts[i * 3 + 1] * modelScale;
      const vz = rawVerts[i * 3 + 2] * modelScale;
      cachedProjVerts[i] = project3D(vx, vy, vz, radX, radY, cx, cy, zoomDist);
    }

    if (renderMode === 'bounds') {
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      const dims = meshData.dimensions || [1, 1, 1];
      const maxDim = Math.max(...dims) || 1;
      const bx = ((dims[0] / maxDim) * modelScale);
      const by = ((dims[1] / maxDim) * modelScale);
      const bz = ((dims[2] / maxDim) * modelScale);
      const corners = [
        [-bx, -by, -bz], [bx, -by, -bz], [bx, by, -bz], [-bx, by, -bz],
        [-bx, -by, bz], [bx, -by, bz], [bx, by, bz], [-bx, by, bz]
      ];
      const proj = corners.map(c => project3D(c[0], c[1], c[2], radX, radY, cx, cy, zoomDist));
      const edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
      ];
      ctx.beginPath();
      edges.forEach(e => {
        ctx.moveTo(proj[e[0]].x, proj[e[0]].y);
        ctx.lineTo(proj[e[1]].x, proj[e[1]].y);
      });
      ctx.stroke();
    } else {
      const faces = meshData.faces;
      const numFaces = (faces.length / 3) | 0;
      const step = numFaces > 3000 ? Math.ceil(numFaces / 3000) : 1;

      if (renderMode === 'wireframe') {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let f = 0; f < numFaces; f += step) {
          const i0 = faces[f * 3];
          const i1 = faces[f * 3 + 1];
          const i2 = faces[f * 3 + 2];
          const p0 = cachedProjVerts[i0];
          const p1 = cachedProjVerts[i1];
          const p2 = cachedProjVerts[i2];
          if (!p0 || !p1 || !p2) continue;
          ctx.moveTo(p0.x, p0.y);
          ctx.lineTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.lineTo(p0.x, p0.y);
        }
        ctx.stroke();
      } else {
        const visibleFaces = [];
        const lx = 0.577, ly = 0.577, lz = 0.577;

        for (let f = 0; f < numFaces; f += step) {
          const i0 = faces[f * 3];
          const i1 = faces[f * 3 + 1];
          const i2 = faces[f * 3 + 2];
          const p0 = cachedProjVerts[i0];
          const p1 = cachedProjVerts[i1];
          const p2 = cachedProjVerts[i2];
          if (!p0 || !p1 || !p2) continue;

          const depth = (p0.z + p1.z + p2.z) / 3;
          const v0x = rawVerts[i0 * 3], v0y = rawVerts[i0 * 3 + 1], v0z = rawVerts[i0 * 3 + 2];
          const v1x = rawVerts[i1 * 3], v1y = rawVerts[i1 * 3 + 1], v1z = rawVerts[i1 * 3 + 2];
          const v2x = rawVerts[i2 * 3], v2y = rawVerts[i2 * 3 + 1], v2z = rawVerts[i2 * 3 + 2];
          const e1x = v1x - v0x, e1y = v1y - v0y, e1z = v1z - v0z;
          const e2x = v2x - v0x, e2y = v2y - v0y, e2z = v2z - v0z;
          let nx = e1y * e2z - e1z * e2y;
          let ny = e1z * e2x - e1x * e2z;
          let nz = e1x * e2y - e1y * e2x;
          const nlen = Math.hypot(nx, ny, nz) || 1;
          nx /= nlen; ny /= nlen; nz /= nlen;

          const nx1 = nx * Math.cos(radY) + nz * Math.sin(radY);
          const nz1 = -nx * Math.sin(radY) + nz * Math.cos(radY);
          const ny2 = ny * Math.cos(radX) - nz1 * Math.sin(radX);
          const nz2 = ny * Math.sin(radX) + nz1 * Math.cos(radX);

          if (nz2 < -0.1) continue;
          visibleFaces.push({ p0, p1, p2, depth, nx: nx1, ny: ny2, nz: nz2 });
        }

        visibleFaces.sort((a, b) => b.depth - a.depth);

        for (let i = 0; i < visibleFaces.length; i++) {
          const tri = visibleFaces[i];
          ctx.beginPath();
          ctx.moveTo(tri.p0.x, tri.p0.y);
          ctx.lineTo(tri.p1.x, tri.p1.y);
          ctx.lineTo(tri.p2.x, tri.p2.y);
          ctx.closePath();

          if (renderMode === 'normals') {
            const nr = Math.round(128 + 127 * tri.nx);
            const ng = Math.round(128 + 127 * tri.ny);
            const nb = Math.round(128 + 127 * tri.nz);
            ctx.fillStyle = `rgb(${nr}, ${ng}, ${nb})`;
          } else {
            const dot = tri.nx * lx + tri.ny * ly + tri.nz * lz;
            const brightness = Math.max(0.2, Math.min(1.0, 0.4 + 0.6 * dot));
            const r = Math.round(59 * brightness);
            const g = Math.round(130 * brightness);
            const b = Math.round(246 * brightness);
            ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
          }
          ctx.fill();
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    // Cutting plane visualization
    const cutSlider = document.getElementById('m3d-cut-slider');
    const cutAxis = document.getElementById('m3d-cut-axis');
    if (cutSlider && cutAxis) {
      const cutRatio = (parseInt(cutSlider.value, 10) || 50) / 100.0;
      const axis = cutAxis.value;
      const cutPos = (-1.0 + 2.0 * cutRatio) * modelScale;
      const b = modelScale * 1.1;
      let pCorners = [];
      if (axis === 'z') {
        pCorners = [[-b, -b, cutPos], [b, -b, cutPos], [b, b, cutPos], [-b, b, cutPos]];
      } else if (axis === 'x') {
        pCorners = [[cutPos, -b, -b], [cutPos, b, -b], [cutPos, b, b], [cutPos, -b, b]];
      } else {
        pCorners = [[-b, cutPos, -b], [b, cutPos, -b], [b, cutPos, b], [-b, cutPos, b]];
      }
      const projCut = pCorners.map(c => project3D(c[0], c[1], c[2], radX, radY, cx, cy, zoomDist));
      ctx.beginPath();
      ctx.moveTo(projCut[0].x, projCut[0].y);
      for (let i = 1; i < projCut.length; i++) ctx.lineTo(projCut[i].x, projCut[i].y);
      ctx.closePath();
      ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
      ctx.fill();
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Measurement points and connecting line
    if (measurePtA) {
      const pa = project3D(measurePtA.norm[0] * modelScale, measurePtA.norm[1] * modelScale, measurePtA.norm[2] * modelScale, radX, radY, cx, cy, zoomDist);
      ctx.beginPath();
      ctx.arc(pa.x, pa.y, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#f59e0b';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 12px sans-serif';
      ctx.fillText('A', pa.x + 8, pa.y - 8);

      if (measurePtB) {
        const pb = project3D(measurePtB.norm[0] * modelScale, measurePtB.norm[1] * modelScale, measurePtB.norm[2] * modelScale, radX, radY, cx, cy, zoomDist);
        ctx.beginPath();
        ctx.arc(pb.x, pb.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#10b981';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#ffffff';
        ctx.fillText('B', pb.x + 8, pb.y - 8);

        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.lineTo(pb.x, pb.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }
  }

  // Cutting plane
  document.getElementById('m3d-cut-slider')?.addEventListener('input', (e) => {
    document.getElementById('m3d-cut-ratio-val').textContent = `${e.target.value}%`;
    render3DViewport();
  });
  document.getElementById('m3d-cut-axis')?.addEventListener('change', () => {
    render3DViewport();
  });

  document.getElementById('m3d-apply-cut-btn')?.addEventListener('click', async () => {
    if (!currentModelPath) return;
    const axis = document.getElementById('m3d-cut-axis').value;
    const ratio = parseInt(document.getElementById('m3d-cut-slider').value, 10) / 100.0;
    const cap = document.getElementById('m3d-cut-cap').checked;
    const out = await api.select_save_file('sliced_model.stl', ['STL Mesh (*.stl)']);
    if (out) {
      showStatus('m3d-status-box', 'Computing cross-section mesh slice...');
      const res = await api.model3d_cut_mesh(currentModelPath, axis, ratio, out, cap);
      if (res.error) showStatus('m3d-status-box', res.error, true);
      else {
        showStatus('m3d-status-box', `Mesh sliced and saved to ${out}`);
        load3DModel(out);
      }
    }
  });

  // Repair Mesh
  document.getElementById('m3d-repair-btn')?.addEventListener('click', async () => {
    if (!currentModelPath) return;
    showStatus('m3d-status-box', 'Repairing non-manifold geometry and filling holes...');
    const out = await api.select_save_file('repaired_model.stl', ['STL Mesh (*.stl)']);
    if (out) {
      const res = await api.model3d_repair_mesh(currentModelPath, out);
      if (res.error) showStatus('m3d-status-box', res.error, true);
      else {
        showStatus('m3d-status-box', `Mesh repaired and saved to ${out}`);
        load3DModel(out);
      }
    }
  });

  // Scaling
  document.getElementById('m3d-scale-half')?.addEventListener('click', () => applyScale(0.5));
  document.getElementById('m3d-scale-double')?.addEventListener('click', () => applyScale(2.0));
  document.getElementById('m3d-scale-apply-btn')?.addEventListener('click', () => {
    const s = parseFloat(document.getElementById('m3d-scale-val').value) || 1.0;
    applyScale(s);
  });

  async function applyScale(factor) {
    if (!currentModelPath) return;
    const out = await api.select_save_file('scaled_model.stl', ['STL Mesh (*.stl)']);
    if (out) {
      const res = await api.model3d_scale_mesh(currentModelPath, factor, out);
      if (res.error) showStatus('m3d-status-box', res.error, true);
      else {
        showStatus('m3d-status-box', `Mesh scaled by ${factor}x and saved to ${out}`);
        load3DModel(out);
      }
    }
  }

  // Export Mesh
  document.getElementById('m3d-export-btn')?.addEventListener('click', async () => {
    if (!currentModelPath) return;
    const fmt = document.getElementById('m3d-export-fmt').value;
    const out = await api.select_save_file(`model.${fmt}`, [`${fmt.toUpperCase()} Mesh (*.${fmt})`]);
    if (out) {
      const res = await api.model3d_export(currentModelPath, out, fmt);
      if (res.error) showStatus('m3d-status-box', res.error, true);
      else showStatus('m3d-status-box', `Exported to ${out}`);
    }
  });
}

// -------------------------------------------------------------
// 4. Video & Audio Studio
// -------------------------------------------------------------
function setupMediaStudio() {
  const api = getApi();
  let currentMediaPath = '';
  let inTimeSec = 0;
  let outTimeSec = 0;

  const player = document.getElementById('media-player');
  const placeholder = document.getElementById('media-placeholder');

  document.getElementById('media-open-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Media Files (*.mp4;*.mkv;*.mov;*.mp3;*.wav;*.webm)'], false);
    if (files && files.length > 0) {
      loadMedia(files[0]);
    }
  });

  async function loadMedia(path) {
    currentMediaPath = path;
    placeholder.style.display = 'none';
    player.style.display = 'block';

    const urlRes = await api.media_get_file_url(path);
    if (urlRes && urlRes.url) {
      player.src = urlRes.url;
    }

    const info = await api.media_info(path);
    if (info && !info.error) {
      document.getElementById('media-info-card').style.display = 'block';
      const grid = document.getElementById('media-info-grid');
      grid.innerHTML = `
        <div class="stat-tile" style="padding: 8px;"><div class="stat-num" style="font-size: 15px;">${info.codec || 'N/A'}</div><div class="stat-lbl">Codec</div></div>
        <div class="stat-tile" style="padding: 8px;"><div class="stat-num" style="font-size: 15px;">${info.resolution || 'N/A'}</div><div class="stat-lbl">Resolution</div></div>
        <div class="stat-tile" style="padding: 8px;"><div class="stat-num" style="font-size: 15px;">${info.duration ? `${info.duration.toFixed(1)}s` : 'N/A'}</div><div class="stat-lbl">Duration</div></div>
        <div class="stat-tile" style="padding: 8px;"><div class="stat-num" style="font-size: 15px;">${info.bitrate || 'N/A'}</div><div class="stat-lbl">Bitrate</div></div>
      `;
      outTimeSec = info.duration || 0;
      updateTimecodeDisplay();
    }
  }

  function formatTimecode(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function updateTimecodeDisplay() {
    document.getElementById('media-in-time-input').value = formatTimecode(inTimeSec);
    document.getElementById('media-out-time-input').value = formatTimecode(outTimeSec);
    const diff = Math.max(0, outTimeSec - inTimeSec);
    document.getElementById('media-clip-duration').textContent = `${diff.toFixed(1)}s`;
  }

  document.getElementById('media-set-in-btn')?.addEventListener('click', () => {
    inTimeSec = player.currentTime || 0;
    updateTimecodeDisplay();
  });

  document.getElementById('media-set-out-btn')?.addEventListener('click', () => {
    outTimeSec = player.currentTime || 0;
    updateTimecodeDisplay();
  });

  // Trim Action
  document.getElementById('media-trim-action-btn')?.addEventListener('click', async () => {
    if (!currentMediaPath) return;
    const fastCopy = document.getElementById('media-fast-copy-chk').checked;
    const dest = await api.select_save_file('trimmed_clip.mp4', ['MP4 Video (*.mp4)', 'Audio File (*.mp3)']);
    if (dest) {
      showStatus('media-status-box', 'Trimming media segment...');
      const res = await api.media_trim(currentMediaPath, inTimeSec, outTimeSec, dest, fastCopy);
      if (res.error) showStatus('media-status-box', res.error, true);
      else showStatus('media-status-box', `Trimmed media saved to ${dest}`);
    }
  });

  // Snapshot frame capture
  document.getElementById('media-snap-frame-btn')?.addEventListener('click', async () => {
    if (!currentMediaPath) return;
    const time = player.currentTime || 0;
    const res = await api.media_capture_frame(currentMediaPath, time);
    if (res.data_url) {
      document.getElementById('media-snapshot-card').style.display = 'block';
      const canvas = document.getElementById('media-snapshot-canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
      };
      img.src = res.data_url;
    }
  });

  document.getElementById('media-save-snap-btn')?.addEventListener('click', async () => {
    const canvas = document.getElementById('media-snapshot-canvas');
    if (!canvas) return;
    const dest = await api.select_save_file('frame_snapshot.png', ['PNG Image (*.png)']);
    if (dest) {
      const dataUrl = canvas.toDataURL('image/png');
      const base64Data = dataUrl.split(',')[1];
      await api.image_save_canvas(base64Data, dest);
      alert(`Snapshot saved to ${dest}`);
    }
  });

  // Extract Audio
  document.getElementById('media-extract-audio-quick-btn')?.addEventListener('click', async () => {
    if (!currentMediaPath) return;
    const fmt = document.getElementById('media-audio-fmt').value;
    const bitrate = document.getElementById('media-audio-bitrate').value;
    const dest = await api.select_save_file(`audio_track.${fmt}`, [`Audio (*.${fmt})`]);
    if (dest) {
      showStatus('media-status-box', `Extracting audio track as ${fmt.toUpperCase()}...`);
      const res = await api.media_extract_audio(currentMediaPath, dest, fmt, bitrate);
      if (res.error) showStatus('media-status-box', res.error, true);
      else showStatus('media-status-box', `Audio track saved to ${dest}`);
    }
  });

  // Mute Video
  document.getElementById('media-mute-action-btn')?.addEventListener('click', async () => {
    if (!currentMediaPath) return;
    const dest = await api.select_save_file('muted_video.mp4', ['MP4 Video (*.mp4)']);
    if (dest) {
      showStatus('media-status-box', 'Removing audio tracks...');
      const res = await api.media_mute(currentMediaPath, dest);
      if (res.error) showStatus('media-status-box', res.error, true);
      else showStatus('media-status-box', `Muted video saved to ${dest}`);
    }
  });

  // Compress Media
  document.getElementById('media-compress-crf')?.addEventListener('input', (e) => {
    document.getElementById('media-crf-val').textContent = e.target.value;
  });

  document.getElementById('media-compress-quick-btn')?.addEventListener('click', async () => {
    if (!currentMediaPath) return;
    const crf = parseInt(document.getElementById('media-compress-crf').value) || 23;
    const preset = document.getElementById('media-compress-preset').value;
    const dest = await api.select_save_file('compressed_video.mp4', ['MP4 Video (*.mp4)']);
    if (dest) {
      showStatus('media-status-box', `Compressing media (CRF ${crf}, ${preset})...`);
      const res = await api.media_compress(currentMediaPath, dest, crf, preset);
      if (res.error) showStatus('media-status-box', res.error, true);
      else showStatus('media-status-box', `Compressed media saved to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 5. Universal File Converter
// -------------------------------------------------------------
function setupConverterStudio() {
  let queueFiles = [];

  document.getElementById('conv-browse-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const files = await api.select_file(['All Files (*.*)'], true);
    if (files) {
      const globalTarget = document.getElementById('conv-target-format')?.value || 'pdf';
      files.forEach(f => {
        if (!queueFiles.some(item => item.path === f)) {
          const name = f.split(/[\/\\]/).pop();
          const ext = name.split('.').pop().toLowerCase();
          queueFiles.push({ path: f, name, ext, target: globalTarget, status: 'Ready' });
        }
      });
      renderConvQueue();
    }
  });

  document.getElementById('conv-clear-queue-btn')?.addEventListener('click', () => {
    queueFiles = [];
    renderConvQueue();
  });

  document.getElementById('conv-folder-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const dir = await api.select_directory();
    if (dir) document.getElementById('conv-output-dir').value = dir;
  });

  document.getElementById('conv-open-folder-btn')?.addEventListener('click', async () => {
    const dir = document.getElementById('conv-output-dir').value;
    if (!dir) {
      alert('Select or specify an output directory first.');
      return;
    }
    const api = getApi();
    if (api) api.open_folder(dir);
  });

  function renderConvQueue() {
    const tbody = document.querySelector('#conv-queue-table tbody');
    if (!tbody) return;
    if (queueFiles.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">No files in conversion queue. Click "+ Add Files" above to get started.</td></tr>';
      return;
    }

    tbody.innerHTML = '';

    queueFiles.forEach((item, idx) => {
      const tr = document.createElement('tr');
      const badgeClass = item.status === 'Done' ? 'badge-done' : (item.status === 'Converting' ? 'badge-converting' : (item.status === 'Error' ? 'badge-error' : 'badge-ready'));
      const statusTitle = item.error ? item.error.replace(/"/g, '&quot;') : item.status;
      tr.innerHTML = `
        <td><strong>${item.name}</strong></td>
        <td>.${item.ext}</td>
        <td>
          <select class="conv-row-target" data-idx="${idx}" style="width: 100px; padding: 4px 8px;">
            <option value="pdf" ${item.target === 'pdf' ? 'selected' : ''}>PDF</option>
            <option value="docx" ${item.target === 'docx' ? 'selected' : ''}>DOCX</option>
            <option value="png" ${item.target === 'png' ? 'selected' : ''}>PNG</option>
            <option value="jpg" ${item.target === 'jpg' ? 'selected' : ''}>JPG</option>
            <option value="webp" ${item.target === 'webp' ? 'selected' : ''}>WebP</option>
            <option value="mp3" ${item.target === 'mp3' ? 'selected' : ''}>MP3</option>
            <option value="mp4" ${item.target === 'mp4' ? 'selected' : ''}>MP4</option>
            <option value="csv" ${item.target === 'csv' ? 'selected' : ''}>CSV</option>
            <option value="json" ${item.target === 'json' ? 'selected' : ''}>JSON</option>
          </select>
        </td>
        <td><span class="badge ${badgeClass}" title="${statusTitle}">${item.status}</span></td>
      `;
      tbody.appendChild(tr);
    });

    document.querySelectorAll('.conv-row-target').forEach(sel => {
      sel.addEventListener('change', (e) => {
        const i = parseInt(e.target.getAttribute('data-idx'));
        if (queueFiles[i]) queueFiles[i].target = e.target.value;
      });
    });
  }

  document.getElementById('conv-target-format')?.addEventListener('change', (e) => {
    queueFiles.forEach(f => f.target = e.target.value);
    renderConvQueue();
  });

  document.getElementById('conv-run-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    if (queueFiles.length === 0) return alert('Queue is empty.');
    const outDir = document.getElementById('conv-output-dir').value;
    if (!outDir) return alert('Select destination folder.');

    showStatus('conv-status-box', `Converting ${queueFiles.length} file(s)...`);

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < queueFiles.length; i++) {
      queueFiles[i].status = 'Converting';
      renderConvQueue();
      const item = queueFiles[i];
      const res = await api.convert_file(item.path, item.target, outDir);
      if (res && res.error) {
        queueFiles[i].status = 'Error';
        queueFiles[i].error = res.error;
        failCount++;
      } else {
        queueFiles[i].status = 'Done';
        queueFiles[i].error = null;
        successCount++;
      }
      renderConvQueue();
    }

    if (failCount === 0) {
      showStatus('conv-status-box', `Batch conversion complete: ${successCount} file(s) converted successfully.`);
    } else {
      showStatus('conv-status-box', `Batch conversion finished: ${successCount} succeeded, ${failCount} failed.`, true);
    }
  });
}

// -------------------------------------------------------------
// 6. Word Counter & Analytics
// -------------------------------------------------------------
function setupWordCounter() {
  const api = getApi();
  const input = document.getElementById('wc-input');
  const densityCard = document.getElementById('wc-density-card');
  const densityTbody = document.getElementById('wc-density-tbody');

  let debounceTimer = null;
  let lastStats = null;

  function resetStats() {
    lastStats = null;
    const ids = [
      'wc-words', 'wc-chars', 'wc-chars-nospace', 'wc-sentences',
      'wc-paragraphs', 'wc-reading-time', 'wc-speaking-time', 'wc-pages',
      'wc-avg-word-len', 'wc-avg-sent-len'
    ];
    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = id.includes('time') ? '0 min' : '0';
    });
    const easeEl = document.getElementById('wc-readability');
    if (easeEl) easeEl.textContent = '-';
    const lvlEl = document.getElementById('wc-reading-level');
    if (lvlEl) lvlEl.textContent = '-';

    if (densityTbody) {
      densityTbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 18px;">Enter text and click Analyze to view keyword density.</td></tr>';
    }
  }

  function applyStats(stats) {
    if (!stats) return;
    lastStats = stats;
    const words = stats.words || 0;
    const chars = stats.characters || 0;
    const charsNoSpace = stats.characters_no_spaces || 0;
    const sentences = stats.sentences || 0;
    const paragraphs = stats.paragraphs || 0;

    const readSecs = stats.reading_time_secs || 0;
    const speakSecs = stats.speaking_time_secs || 0;
    const readStr = readSecs >= 60 ? `${Math.floor(readSecs / 60)}m ${readSecs % 60}s` : `${readSecs}s`;
    const speakStr = speakSecs >= 60 ? `${Math.floor(speakSecs / 60)}m ${speakSecs % 60}s` : `${speakSecs}s`;

    document.getElementById('wc-words').textContent = words.toLocaleString();
    document.getElementById('wc-chars').textContent = chars.toLocaleString();
    document.getElementById('wc-chars-nospace').textContent = charsNoSpace.toLocaleString();
    document.getElementById('wc-sentences').textContent = sentences;
    document.getElementById('wc-paragraphs').textContent = paragraphs;
    document.getElementById('wc-reading-time').textContent = readStr;
    document.getElementById('wc-speaking-time').textContent = speakStr;
    document.getElementById('wc-pages').textContent = stats.pages_est !== undefined ? stats.pages_est : '0';

    const ease = stats.flesch_reading_ease !== undefined ? stats.flesch_reading_ease : 100;
    const grade = stats.flesch_kincaid_grade !== undefined ? stats.flesch_kincaid_grade : 0;
    const label = stats.readability_label || 'Standard';
    document.getElementById('wc-readability').textContent = `${ease} / 100`;
    document.getElementById('wc-reading-level').textContent = words > 0 ? `Grade ${grade} (${label})` : '-';

    document.getElementById('wc-avg-word-len').textContent = `${stats.avg_word_length !== undefined ? stats.avg_word_length : 0} chars`;
    document.getElementById('wc-avg-sent-len').textContent = `${stats.avg_sentence_length !== undefined ? stats.avg_sentence_length : 0} words`;

    if (densityTbody) {
      densityTbody.innerHTML = '';
      const kws = stats.top_keywords || [];
      if (kws.length === 0) {
        densityTbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 18px;">No recurring keywords found.</td></tr>';
      } else {
        kws.forEach(item => {
          const row = document.createElement('tr');
          const tdWord = document.createElement('td');
          tdWord.textContent = item.word;
          const tdCount = document.createElement('td');
          tdCount.style.textAlign = 'right';
          tdCount.textContent = item.count;
          const tdDensity = document.createElement('td');
          tdDensity.style.textAlign = 'right';
          tdDensity.textContent = `${item.density_pct}%`;
          row.appendChild(tdWord);
          row.appendChild(tdCount);
          row.appendChild(tdDensity);
          densityTbody.appendChild(row);
        });
      }
    }
  }

  async function runFullAnalysis() {
    const text = input ? input.value : '';
    if (!text.trim()) {
      resetStats();
      return null;
    }
    const res = await api.word_counter_analyze(text);
    if (res && !res.error) {
      applyStats(res);
      return res;
    }
    return null;
  }

  input?.addEventListener('input', () => {
    const text = input.value;
    if (!text.trim()) {
      resetStats();
      return;
    }
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    const charsNoSpace = text.replace(/\s/g, '').length;
    const sentences = text.trim() ? (text.match(/[.!?]+(\s|$)/g) || []).length + 1 : 0;
    const paragraphs = text.trim() ? text.split(/\n+/).filter(Boolean).length : 0;
    const readTimeSec = Math.round((words / 225) * 60);

    document.getElementById('wc-words').textContent = words.toLocaleString();
    document.getElementById('wc-chars').textContent = chars.toLocaleString();
    document.getElementById('wc-chars-nospace').textContent = charsNoSpace.toLocaleString();
    document.getElementById('wc-sentences').textContent = sentences;
    document.getElementById('wc-paragraphs').textContent = paragraphs;
    document.getElementById('wc-reading-time').textContent = readTimeSec >= 60 ? `${Math.floor(readTimeSec / 60)}m ${readTimeSec % 60}s` : `${readTimeSec}s`;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runFullAnalysis, 350);
  });

  // 1. Analyze Text
  document.getElementById('wc-analyze-btn')?.addEventListener('click', async () => {
    const text = input?.value || '';
    if (!text.trim()) {
      showStatus('wc-status-box', 'Please enter or paste text to analyze.', true);
      return;
    }
    showStatus('wc-status-box', 'Computing text analytics...');
    const stats = await runFullAnalysis();
    if (stats) {
      showStatus('wc-status-box', `Analysis complete: ${stats.words} words, ${stats.characters} characters analyzed.`);
    } else {
      showStatus('wc-status-box', 'Analysis completed with default statistics.');
    }
  });

  // 2. Load from File
  document.getElementById('wc-file-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file([
      'Documents (*.txt;*.md;*.docx;*.pdf;*.odt;*.rtf;*.csv;*.json;*.yaml;*.py;*.html)',
      'Office Documents (*.docx;*.pptx;*.xlsx;*.odt;*.ods;*.odp)',
      'PDF Documents (*.pdf)',
      'Text & Markdown (*.txt;*.md;*.html)',
      'All Files (*.*)'
    ], false);
    if (files && files.length > 0) {
      showStatus('wc-status-box', `Reading and extracting text from ${files[0]}...`);
      const res = await api.word_counter_analyze_file(files[0]);
      if (res && res.error) {
        showStatus('wc-status-box', `Failed to read document: ${res.error}`, true);
        return;
      }
      if (res && res.text !== undefined) {
        input.value = res.text;
        applyStats(res);
        showStatus('wc-status-box', `Loaded document: ${files[0]} (${res.words} words).`);
      }
    }
  });

  // 3. Clear Input
  document.getElementById('wc-clear-btn')?.addEventListener('click', () => {
    if (input) input.value = '';
    resetStats();
    showStatus('wc-status-box', 'Editor and statistics cleared.');
  });

  // 4. Copy Stats
  document.getElementById('wc-copy-stats-btn')?.addEventListener('click', () => {
    const words = document.getElementById('wc-words').textContent;
    const chars = document.getElementById('wc-chars').textContent;
    const charsNoSpace = document.getElementById('wc-chars-nospace').textContent;
    const sentences = document.getElementById('wc-sentences').textContent;
    const paragraphs = document.getElementById('wc-paragraphs').textContent;
    const readTime = document.getElementById('wc-reading-time').textContent;
    const speakTime = document.getElementById('wc-speaking-time').textContent;
    const pages = document.getElementById('wc-pages').textContent;
    const readability = document.getElementById('wc-readability').textContent;
    const readingLevel = document.getElementById('wc-reading-level').textContent;
    const avgWord = document.getElementById('wc-avg-word-len').textContent;
    const avgSent = document.getElementById('wc-avg-sent-len').textContent;

    const summary = [
      '--- Word Counter & Text Analytics Summary ---',
      `Words:                  ${words}`,
      `Characters:             ${chars}`,
      `Characters (no spaces): ${charsNoSpace}`,
      `Sentences:              ${sentences}`,
      `Paragraphs:             ${paragraphs}`,
      `Reading Time:           ${readTime}`,
      `Speaking Time:          ${speakTime}`,
      `Estimated Pages:        ${pages}`,
      `Flesch Reading Ease:    ${readability}`,
      `Reading Level:          ${readingLevel}`,
      `Avg Word Length:        ${avgWord}`,
      `Avg Sentence Length:    ${avgSent}`
    ].join('\n');

    navigator.clipboard.writeText(summary);
    showStatus('wc-status-box', 'Statistics summary copied to clipboard.');
  });

  // 5. Export Report
  document.getElementById('wc-export-report-btn')?.addEventListener('click', async () => {
    const text = input ? input.value : '';
    if (!text.trim()) {
      showStatus('wc-status-box', 'Cannot export report: text editor is empty.', true);
      return;
    }
    const dest = await api.select_save_file('word_count_report.txt', ['Text Report (*.txt)', 'Markdown (*.md)', 'All Files (*.*)']);
    if (dest) {
      showStatus('wc-status-box', 'Generating analytics report...');
      const repRes = await api.word_counter_generate_report(text);
      if (repRes && repRes.report) {
        const saveRes = await api.save_file(repRes.report, dest);
        if (saveRes && saveRes.error) {
          showStatus('wc-status-box', `Export error: ${saveRes.error}`, true);
        } else {
          showStatus('wc-status-box', `Report exported successfully to ${dest}`);
        }
      } else {
        showStatus('wc-status-box', 'Failed to generate report.', true);
      }
    }
  });

  // 6. Word Density Trigger
  document.getElementById('wc-density-toggle-btn')?.addEventListener('click', async () => {
    if (!densityCard) return;
    densityCard.style.display = 'block';
    densityCard.scrollIntoView({ behavior: 'smooth' });
    if (!lastStats && input && input.value.trim()) {
      await runFullAnalysis();
    }
    showStatus('wc-status-box', 'Keyword density section displayed.');
  });
}

// -------------------------------------------------------------
// 7. OCR & Text Extraction
// -------------------------------------------------------------
function setupOcrStudio() {
  const api = getApi();

  document.getElementById('ocr-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Scan / Image (*.png;*.jpg;*.pdf)'], false);
    if (files) document.getElementById('ocr-input-path').value = files[0];
  });

  // Populate languages
  api?.ocr_languages?.().then(langs => {
    if (langs && langs.length) {
      const sel = document.getElementById('ocr-language-select');
      sel.innerHTML = '';
      langs.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l;
        opt.textContent = l;
        sel.appendChild(opt);
      });
    }
  });

  document.getElementById('ocr-run-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('ocr-input-path').value;
    const lang = document.getElementById('ocr-language-select').value;
    if (!path) return alert('Select image or scanned document.');

    showStatus('ocr-status-box', 'Running local Tesseract OCR engine...');
    const res = await api.ocr_image(path, lang);
    if (res.error) showStatus('ocr-status-box', res.error, true);
    else {
      document.getElementById('ocr-status-box').style.display = 'none';
      document.getElementById('ocr-result-card').style.display = 'block';
      document.getElementById('ocr-result-text').value = res.text;
      const words = res.text.trim().split(/\s+/).filter(Boolean).length;
      document.getElementById('ocr-stats-badge').textContent = `Extracted ${words} words`;
    }
  });

  document.getElementById('ocr-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('ocr-result-text').value);
    alert('Extracted text copied to clipboard.');
  });

  document.getElementById('ocr-save-txt-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('ocr_extracted.txt', ['Text File (*.txt)']);
    if (dest) {
      await api.save_file(document.getElementById('ocr-result-text').value, dest);
      alert(`Saved to ${dest}`);
    }
  });

  document.getElementById('ocr-save-md-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('ocr_extracted.md', ['Markdown File (*.md)']);
    if (dest) {
      await api.save_file(document.getElementById('ocr-result-text').value, dest);
      alert(`Saved to ${dest}`);
    }
  });

  document.getElementById('ocr-save-pdf-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('ocr-input-path').value;
    const lang = document.getElementById('ocr-language-select').value;
    if (!path) return alert('Select image or scanned document.');
    const dest = await api.select_save_file('searchable.pdf', ['PDF Document (*.pdf)']);
    if (dest) {
      showStatus('ocr-status-box', 'Generating searchable PDF...');
      const res = await api.ocr_create_searchable_pdf(path, dest, lang);
      if (res && res.error) showStatus('ocr-status-box', res.error, true);
      else showStatus('ocr-status-box', `Searchable PDF saved to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 8. Markdown Studio
// -------------------------------------------------------------
function setupMarkdownStudio() {
  const input = document.getElementById('md-input');
  const preview = document.getElementById('md-preview');
  const previewCard = document.getElementById('md-preview-card');
  const grid = document.getElementById('md-workspace-grid');
  const toggleBtn = document.getElementById('md-toggle-preview-btn');

  async function updatePreview() {
    if (!input || !preview) return;
    const api = getApi();
    if (!api || !api.render_markdown) return;
    const res = await api.render_markdown(input.value);
    if (res && res.html !== undefined) {
      preview.innerHTML = res.html;
    }
  }

  input?.addEventListener('input', updatePreview);
  updatePreview();
  window.addEventListener('pywebviewready', updatePreview);
  setTimeout(updatePreview, 300);

  function insertFormat(before, after = '') {
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const sel = input.value.substring(start, end);
    const rep = `${before}${sel}${after}`;
    input.value = input.value.substring(0, start) + rep + input.value.substring(end);
    input.focus();
    input.setSelectionRange(start + before.length, end + before.length);
    updatePreview();
  }

  document.getElementById('md-bold-btn')?.addEventListener('click', () => insertFormat('**', '**'));
  document.getElementById('md-italic-btn')?.addEventListener('click', () => insertFormat('*', '*'));
  document.getElementById('md-strike-btn')?.addEventListener('click', () => insertFormat('~~', '~~'));
  document.getElementById('md-h1-btn')?.addEventListener('click', () => insertFormat('# '));
  document.getElementById('md-h2-btn')?.addEventListener('click', () => insertFormat('## '));
  document.getElementById('md-h3-btn')?.addEventListener('click', () => insertFormat('### '));
  document.getElementById('md-code-btn')?.addEventListener('click', () => insertFormat('```\n', '\n```'));
  document.getElementById('md-quote-btn')?.addEventListener('click', () => insertFormat('> '));
  document.getElementById('md-list-btn')?.addEventListener('click', () => insertFormat('- '));
  document.getElementById('md-table-btn')?.addEventListener('click', () => insertFormat('\n| Column 1 | Column 2 |\n|---|---|\n| Item 1 | Item 2 |\n'));
  document.getElementById('md-link-btn')?.addEventListener('click', () => insertFormat('[Link Title](', ')'));
  document.getElementById('md-img-btn')?.addEventListener('click', () => insertFormat('![Alt Text](', ')'));
  document.getElementById('md-hr-btn')?.addEventListener('click', () => insertFormat('\n---\n'));
  document.getElementById('md-inline-code-btn')?.addEventListener('click', () => insertFormat('`', '`'));
  document.getElementById('md-numlist-btn')?.addEventListener('click', () => insertFormat('1. '));

  document.getElementById('md-open-file-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const files = await api.select_file(['Markdown / Text (*.md;*.txt;*.markdown)'], false);
    if (files && files.length > 0) {
      const content = await api.read_file(files[0]);
      if (content !== null && content !== undefined) {
        input.value = content;
        updatePreview();
      }
    }
  });

  async function saveOrExportMarkdown() {
    const api = getApi();
    if (!api) return;
    const dest = await api.select_save_file('document.md', ['Markdown File (*.md)']);
    if (dest) {
      await api.save_file(input.value, dest);
      alert(`Saved to ${dest}`);
    }
  }

  document.getElementById('md-save-file-btn')?.addEventListener('click', saveOrExportMarkdown);
  document.getElementById('md-export-md-btn')?.addEventListener('click', saveOrExportMarkdown);

  document.getElementById('md-sample-btn')?.addEventListener('click', () => {
    input.value = `# FOSSEverything Markdown Studio\n\nFast, beautiful, offline Markdown writing environment.\n\n- Live preview as you type\n- Table formatting\n- Code blocks\n- Zero cloud tracking\n\n| Feature | Status | Offline |\n|---|---|---|\n| Real-time Render | Active | Yes |\n| HTML / PDF Export | Active | Yes |\n\n> "Local-first software gives users ownership over their data."\n\n\`\`\`python\ndef offline_power():\n    return "100% Local"\n\`\`\`\n`;
    updatePreview();
  });

  document.getElementById('md-clear-btn')?.addEventListener('click', () => {
    input.value = '';
    updatePreview();
  });

  toggleBtn?.addEventListener('click', () => {
    if (!previewCard || !grid) return;
    const isHidden = previewCard.style.display === 'none';
    if (isHidden) {
      previewCard.style.display = 'flex';
      grid.style.gridTemplateColumns = '1fr 1fr';
      toggleBtn.textContent = 'Hide Preview';
    } else {
      previewCard.style.display = 'none';
      grid.style.gridTemplateColumns = '1fr';
      toggleBtn.textContent = 'Show Preview';
    }
  });

  document.getElementById('md-copy-html-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(preview.innerHTML);
    alert('Rendered HTML copied to clipboard.');
  });

  document.getElementById('md-export-html-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const dest = await api.select_save_file('document.html', ['HTML Document (*.html)']);
    if (dest) {
      const res = await api.markdown_export_html(input.value, dest);
      if (res && res.error) {
        alert(`Error: ${res.error}`);
      } else {
        alert(`Exported HTML to ${dest}`);
      }
    }
  });

  document.getElementById('md-export-pdf-btn')?.addEventListener('click', async () => {
    const api = getApi();
    if (!api) return;
    const dest = await api.select_save_file('document.pdf', ['PDF Document (*.pdf)']);
    if (dest) {
      const res = await api.markdown_export_pdf(input.value, dest);
      if (res && res.error) alert(`Error: ${res.error}`);
      else alert(`Exported PDF to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 9. Color Palette Studio
// -------------------------------------------------------------
function setupPaletteStudio() {
  const api = getApi();
  let currentColors = [];

  document.getElementById('pal-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Image Files (*.png;*.jpg;*.jpeg;*.webp)'], false);
    if (files && files.length > 0) {
      document.getElementById('pal-input-path').value = files[0];
      loadEyedropperImage(files[0]);
    }
  });

  document.getElementById('pal-num-colors')?.addEventListener('input', (e) => {
    document.getElementById('pal-num-label').textContent = e.target.value;
  });

  function loadEyedropperImage(path) {
    const canvas = document.getElementById('pal-eyedropper-canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
      document.getElementById('pal-image-card').style.display = 'block';
      canvas.width = Math.min(600, img.width);
      canvas.height = (canvas.width / img.width) * img.height;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    api.image_load_preview(path).then(res => {
      if (res.data_url) img.src = res.data_url;
    });
  }

  // Eyedropper hover loupe
  const eyedropperCanvas = document.getElementById('pal-eyedropper-canvas');
  const loupe = document.getElementById('eyedropper-loupe');
  const eyedropperInfo = document.getElementById('pal-eyedropper-info');

  eyedropperCanvas?.addEventListener('mousemove', (e) => {
    const rect = eyedropperCanvas.getBoundingClientRect();
    const x = Math.floor(e.clientX - rect.left);
    const y = Math.floor(e.clientY - rect.top);
    const ctx = eyedropperCanvas.getContext('2d');
    const pixel = ctx.getImageData(x, y, 1, 1).data;
    const hex = `#${((1 << 24) + (pixel[0] << 16) + (pixel[1] << 8) + pixel[2]).toString(16).slice(1)}`;

    loupe.style.display = 'block';
    loupe.style.left = `${x}px`;
    loupe.style.top = `${y}px`;
    loupe.style.backgroundColor = hex;
    eyedropperInfo.textContent = `Pixel at (${x}, ${y}): ${hex} | RGB(${pixel[0]}, ${pixel[1]}, ${pixel[2]})`;
  });

  eyedropperCanvas?.addEventListener('mouseleave', () => {
    loupe.style.display = 'none';
  });

  eyedropperCanvas?.addEventListener('click', (e) => {
    const rect = eyedropperCanvas.getBoundingClientRect();
    const x = Math.floor(e.clientX - rect.left);
    const y = Math.floor(e.clientY - rect.top);
    const ctx = eyedropperCanvas.getContext('2d');
    const pixel = ctx.getImageData(x, y, 1, 1).data;
    const hex = `#${((1 << 24) + (pixel[0] << 16) + (pixel[1] << 8) + pixel[2]).toString(16).slice(1)}`;
    navigator.clipboard.writeText(hex);
    alert(`Copied ${hex} to clipboard.`);
  });

  document.getElementById('pal-run-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('pal-input-path').value;
    const n = parseInt(document.getElementById('pal-num-colors').value) || 6;
    if (!path) return alert('Select an image file.');

    showStatus('pal-status-box', 'Extracting dominant color swatches...');
    const res = await api.palette_extract(path, n);
    if (res.error) showStatus('pal-status-box', res.error, true);
    else {
      document.getElementById('pal-status-box').style.display = 'none';
      document.getElementById('pal-result-card').style.display = 'block';
      currentColors = res.colors;
      renderSwatches(res.colors);
    }
  });

  function renderSwatches(colors) {
    const container = document.getElementById('pal-swatches-container');
    container.innerHTML = '';
    colors.forEach(c => {
      const swatch = document.createElement('div');
      swatch.className = 'pal-swatch';
      const rgbStr = c.rgb ? `rgb(${c.rgb.join(', ')})` : '';
      swatch.innerHTML = `
        <div class="pal-color-block" style="background-color: ${c.hex};" title="Click to copy ${c.hex}"></div>
        <div class="pal-info">
          <div>
            <strong class="copy-hex-btn" title="Copy Hex code" style="cursor: pointer;">${c.hex}</strong>
            <div class="copy-rgb-btn" title="Copy RGB values" style="font-size: 10px; color: var(--text-muted); cursor: pointer;">${rgbStr}</div>
          </div>
          <span style="font-size: 11px; color: var(--text-muted);">${c.percentage ? `${c.percentage}%` : ''}</span>
        </div>
      `;
      swatch.querySelector('.pal-color-block')?.addEventListener('click', () => {
        navigator.clipboard.writeText(c.hex);
        alert(`Copied ${c.hex} to clipboard.`);
      });
      swatch.querySelector('.copy-hex-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(c.hex);
        alert(`Copied ${c.hex} to clipboard.`);
      });
      swatch.querySelector('.copy-rgb-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (rgbStr) {
          navigator.clipboard.writeText(rgbStr);
          alert(`Copied ${rgbStr} to clipboard.`);
        }
      });
      container.appendChild(swatch);
    });
  }

  document.getElementById('pal-export-json-btn')?.addEventListener('click', async () => {
    if (!currentColors || currentColors.length === 0) return alert('Extract colors first.');
    const dest = await api.select_save_file('palette.json', ['JSON File (*.json)']);
    if (dest) {
      const res = await api.save_file(JSON.stringify(currentColors, null, 2), dest);
      if (res && res.error) alert(`Error: ${res.error}`);
      else alert(`Palette exported to ${dest}`);
    }
  });

  document.getElementById('pal-export-css-btn')?.addEventListener('click', async () => {
    if (!currentColors || currentColors.length === 0) return alert('Extract colors first.');
    const dest = await api.select_save_file('palette.css', ['CSS File (*.css)']);
    if (dest) {
      let css = ':root {\n';
      currentColors.forEach((c, i) => {
        css += `  --color-${i + 1}: ${c.hex};\n`;
      });
      css += '}\n';
      const res = await api.save_file(css, dest);
      if (res && res.error) alert(`Error: ${res.error}`);
      else alert(`CSS variables exported to ${dest}`);
    }
  });

  document.getElementById('pal-export-gpl-btn')?.addEventListener('click', async () => {
    if (!currentColors || currentColors.length === 0) return alert('Extract colors first.');
    const dest = await api.select_save_file('palette.gpl', ['GIMP Palette (*.gpl)']);
    if (dest) {
      const res = await api.palette_export_gpl(currentColors, dest);
      if (res && res.error) alert(`Error: ${res.error}`);
      else alert(`GIMP palette exported to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 10. Photo Collage Studio
// -------------------------------------------------------------
function setupCollageStudio() {
  const api = getApi();
  let collageImages = [];

  document.getElementById('col-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Image Files (*.png;*.jpg;*.jpeg;*.webp)'], true);
    if (files) {
      collageImages = [...collageImages, ...files];
      document.getElementById('col-input-paths').value = `${collageImages.length} images selected`;
      renderCollageQueue();
    }
  });

  document.getElementById('col-save-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('collage.png', ['PNG Image (*.png)', 'JPEG Image (*.jpg)']);
    if (dest) document.getElementById('col-output-path').value = dest;
  });

  function renderCollageQueue() {
    const container = document.getElementById('col-queue-container');
    const list = document.getElementById('col-queue-list');
    if (!container || !list) return;
    if (collageImages.length === 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'block';
    list.innerHTML = '';

    collageImages.forEach((img, idx) => {
      const name = img.split(/[\/\\]/).pop();
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.style.padding = '4px 8px';
      row.style.fontSize = '12px';
      row.innerHTML = `
        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px;">${idx + 1}. ${name}</span>
        <div style="display: flex; gap: 4px;">
          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px;" onclick="moveCollageImg(${idx}, -1)">&uarr;</button>
          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px;" onclick="moveCollageImg(${idx}, 1)">&darr;</button>
          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px; color: #ef4444;" onclick="removeCollageImg(${idx})">&times;</button>
        </div>
      `;
      list.appendChild(row);
    });
  }

  window.moveCollageImg = (idx, dir) => {
    const newIdx = idx + dir;
    if (newIdx >= 0 && newIdx < collageImages.length) {
      const temp = collageImages[idx];
      collageImages[idx] = collageImages[newIdx];
      collageImages[newIdx] = temp;
      renderCollageQueue();
    }
  };

  window.removeCollageImg = (idx) => {
    collageImages.splice(idx, 1);
    document.getElementById('col-input-paths').value = `${collageImages.length} images selected`;
    renderCollageQueue();
  };

  document.querySelectorAll('.col-preset-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cols = btn.getAttribute('data-cols');
      const input = document.getElementById('col-columns');
      if (input && cols) input.value = cols;
    });
  });

  document.getElementById('col-run-btn')?.addEventListener('click', async () => {
    if (collageImages.length === 0) return alert('Select images for collage.');
    const out = document.getElementById('col-output-path').value;
    if (!out) return alert('Select destination output path.');
    const cols = parseInt(document.getElementById('col-columns').value) || 3;
    const spacing = parseInt(document.getElementById('col-spacing').value) || 12;
    const radius = parseInt(document.getElementById('col-radius').value) || 8;
    const bg = document.getElementById('col-bg').value;
    const aspect = document.getElementById('col-aspect').value;

    showStatus('col-status-box', 'Generating composition collage...');
    const res = await api.collage_create(collageImages, out, cols, spacing, bg, radius, aspect);
    if (res.error) {
      showStatus('col-status-box', res.error, true);
    } else {
      showStatus('col-status-box', `Collage generated successfully at ${out}`);
      if (res.data_url) {
        const previewCard = document.getElementById('col-preview-card');
        const previewImg = document.getElementById('col-preview-img');
        if (previewCard && previewImg) {
          previewImg.src = res.data_url;
          previewCard.style.display = 'block';
        }
      }
    }
  });
}

// -------------------------------------------------------------
// 11. Batch File Renamer
// -------------------------------------------------------------
function setupRenamerStudio() {
  const api = getApi();
  let targetFiles = [];

  document.getElementById('ren-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['All Files (*.*)'], true);
    if (files && files.length > 0) {
      targetFiles = files;
      document.getElementById('ren-input-paths').value = `${files.length} files selected`;
    }
  });

  document.getElementById('ren-preview-btn')?.addEventListener('click', async () => {
    if (targetFiles.length === 0) return alert('Select files to rename.');
    const find = document.getElementById('ren-find').value;
    const replace = document.getElementById('ren-replace').value;
    const prefix = document.getElementById('ren-prefix').value;
    const suffix = document.getElementById('ren-suffix').value;
    const startNum = parseInt(document.getElementById('ren-start-num').value) || 1;
    const step = parseInt(document.getElementById('ren-step-num').value) || 1;
    const pad = parseInt(document.getElementById('ren-pad-num').value) || 3;
    const numStyle = document.getElementById('ren-num-style').value;
    const matchCase = document.getElementById('ren-case-chk').checked;
    const isRegex = document.getElementById('ren-regex-chk').checked;
    const includeExt = document.getElementById('ren-ext-chk').checked;
    const caseSelect = document.getElementById('ren-case-select').value;
    const newExt = document.getElementById('ren-new-ext').value;

    const activeTab = document.querySelector('[data-renmode].active')?.getAttribute('data-renmode') || 'replace';

    const res = await api.renamer_preview(targetFiles, {
      mode: activeTab,
      find, replace, prefix, suffix,
      start_num: startNum, step, pad, num_style: numStyle,
      case_sensitive: matchCase, is_regex: isRegex, include_ext: includeExt,
      case_transform: caseSelect, new_ext: newExt
    });

    if (res.error) return showStatus('ren-status-box', res.error, true);

    document.getElementById('ren-preview-card').style.display = 'block';
    const tbody = document.querySelector('#ren-table tbody');
    tbody.innerHTML = '';
    res.preview.forEach(p => {
      const tr = document.createElement('tr');
      const badge = p.status === 'valid' ? 'badge-done' : (p.status === 'collision' ? 'badge-error' : 'badge-ready');
      tr.innerHTML = `
        <td>${p.original}</td>
        <td><strong>${p.target}</strong></td>
        <td><span class="badge ${badge}">${p.status}</span></td>
      `;
      tbody.appendChild(tr);
    });
  });

  document.getElementById('ren-apply-btn')?.addEventListener('click', async () => {
    showStatus('ren-status-box', 'Applying batch rename changes...');
    const res = await api.renamer_apply();
    if (res.error) {
      showStatus('ren-status-box', res.error, true);
    } else {
      if (res.results) {
        targetFiles = res.results.filter(r => r.success).map(r => r.dst);
        document.getElementById('ren-input-paths').value = `${targetFiles.length} files selected`;
      }
      showStatus('ren-status-box', `Renamed ${res.count} files successfully.`);
    }
  });

  document.getElementById('ren-undo-btn')?.addEventListener('click', async () => {
    const res = await api.renamer_undo();
    if (res.error) {
      showStatus('ren-status-box', res.error, true);
    } else {
      if (res.results) {
        targetFiles = res.results.filter(r => r.success).map(r => r.dst);
        document.getElementById('ren-input-paths').value = `${targetFiles.length} files selected`;
      }
      showStatus('ren-status-box', `Rolled back ${res.count} file rename(s).`);
    }
  });
}

// -------------------------------------------------------------
// 12. Metadata Tools
// -------------------------------------------------------------
function setupMetadataStudio() {
  const api = getApi();

  document.getElementById('meta-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['All Files (*.*)'], false);
    if (files) document.getElementById('meta-input-path').value = files[0];
  });

  document.getElementById('meta-inspect-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('meta-input-path').value;
    if (!path) return alert('Select file to inspect.');
    const res = await api.metadata_inspect(path);
    if (res.error) showStatus('meta-status-box', res.error, true);
    else {
      document.getElementById('meta-result-card').style.display = 'block';
      const tbody = document.querySelector('#meta-table tbody');
      tbody.innerHTML = '';
      Object.entries(res.fields || {}).forEach(([k, v]) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td><strong>${k}</strong></td><td>${v}</td>`;
        tbody.appendChild(tr);
      });
    }
  });

  document.getElementById('meta-strip-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('meta-input-path').value;
    if (!path) return alert('Select file to sanitize.');
    const dest = await api.select_save_file('sanitized_file', ['All Files (*.*)']);
    if (dest) {
      const res = await api.metadata_strip(path, dest);
      if (res.error) showStatus('meta-status-box', res.error, true);
      else showStatus('meta-status-box', `Metadata stripped and saved to ${dest}`);
    }
  });

  document.getElementById('meta-export-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('meta-input-path').value;
    if (!path) return alert('Select file to export metadata.');
    const dest = await api.select_save_file('metadata.json', ['JSON Files (*.json)', 'All Files (*.*)']);
    if (dest) {
      const res = await api.metadata_export(path, dest);
      if (res.error) showStatus('meta-status-box', res.error, true);
      else showStatus('meta-status-box', `Metadata exported to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 13. Archive Manager
// -------------------------------------------------------------
function setupArchiveStudio() {
  const api = getApi();

  // Extract
  document.getElementById('arc-ext-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Archive Files (*.zip;*.tar;*.gz)'], false);
    if (files) document.getElementById('arc-ext-file').value = files[0];
  });

  document.getElementById('arc-ext-dest-btn')?.addEventListener('click', async () => {
    const dir = await api.select_directory();
    if (dir) document.getElementById('arc-ext-dest').value = dir;
  });

  document.getElementById('arc-ext-run-btn')?.addEventListener('click', async () => {
    const file = document.getElementById('arc-ext-file').value;
    const dest = document.getElementById('arc-ext-dest').value;
    if (!file || !dest) return alert('Select archive and destination folder.');
    const res = await api.archive_extract(file, dest);
    if (res.error) showStatus('arc-status-box', res.error, true);
    else showStatus('arc-status-box', `Archive extracted to ${dest}`);
  });

  // Create
  document.getElementById('arc-create-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['All Files (*.*)'], true);
    if (files) document.getElementById('arc-create-files').value = files.join('; ');
  });

  document.getElementById('arc-create-save-btn')?.addEventListener('click', async () => {
    const fmt = document.getElementById('arc-create-fmt').value;
    const dest = await api.select_save_file(`bundle.${fmt}`, [`Archive (*.${fmt})`]);
    if (dest) document.getElementById('arc-create-output').value = dest;
  });

  document.getElementById('arc-create-run-btn')?.addEventListener('click', async () => {
    const raw = document.getElementById('arc-create-files').value;
    const out = document.getElementById('arc-create-output').value;
    const fmt = document.getElementById('arc-create-fmt').value;
    if (!raw || !out) return alert('Select files and output archive path.');
    const files = raw.split(';').map(s => s.trim()).filter(Boolean);
    const res = await api.archive_create(files, out, fmt);
    if (res.error) showStatus('arc-status-box', res.error, true);
    else showStatus('arc-status-box', `Archive created at ${out}`);
  });

  // List
  document.getElementById('arc-list-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Archive Files (*.zip;*.tar;*.gz)'], false);
    if (files) document.getElementById('arc-list-file').value = files[0];
  });

  document.getElementById('arc-list-run-btn')?.addEventListener('click', async () => {
    const file = document.getElementById('arc-list-file').value;
    if (!file) return alert('Select archive to inspect.');
    const res = await api.archive_list(file);
    if (res.error) showStatus('arc-status-box', res.error, true);
    else {
      document.getElementById('arc-list-result-card').style.display = 'block';
      const tbody = document.querySelector('#arc-list-table tbody');
      tbody.innerHTML = '';
      res.items.forEach(it => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${it.path}</td><td>${(it.size / 1024).toFixed(1)} KB</td>`;
        tbody.appendChild(tr);
      });
    }
  });

  document.getElementById('arc-test-btn')?.addEventListener('click', async () => {
    const file = document.getElementById('arc-list-file').value;
    if (!file) return alert('Select archive to test.');
    showStatus('arc-status-box', 'Verifying archive integrity...');
    const res = await api.archive_test(file);
    if (res.error) showStatus('arc-status-box', res.error, true);
    else showStatus('arc-status-box', res.message || 'Archive integrity verified.');
  });
}

// -------------------------------------------------------------
// 14. Office Extractor & Converter
// -------------------------------------------------------------
function setupOfficeStudio() {
  const api = getApi();

  document.getElementById('off-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Office Documents (*.docx;*.pptx;*.xlsx)'], false);
    if (files) document.getElementById('off-input-path').value = files[0];
  });

  document.getElementById('off-run-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('off-input-path').value;
    if (!path) return alert('Select Office document.');
    const res = await api.office_extract(path);
    if (res.error) showStatus('off-status-box', res.error, true);
    else {
      document.getElementById('off-result-card').style.display = 'block';
      document.getElementById('off-output').value = res.text;
    }
  });

  document.getElementById('off-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('off-output').value);
    alert('Copied text to clipboard.');
  });

  document.getElementById('off-docx-to-pdf-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('off-input-path').value;
    if (!path) return alert('Select DOCX file.');
    const dest = await api.select_save_file('converted.pdf', ['PDF (*.pdf)']);
    if (dest) {
      const res = await api.office_docx_to_pdf(path, dest);
      if (res.error) showStatus('off-status-box', res.error, true);
      else showStatus('off-status-box', `PDF saved to ${dest}`);
    }
  });

  document.getElementById('off-docx-to-md-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('off-input-path').value;
    if (!path) return alert('Select DOCX file.');
    const dest = await api.select_save_file('converted.md', ['Markdown (*.md)']);
    if (dest) {
      const res = await api.office_docx_to_markdown(path, dest);
      if (res.error) showStatus('off-status-box', res.error, true);
      else showStatus('off-status-box', `Markdown saved to ${dest}`);
    }
  });

  document.getElementById('off-pptx-to-md-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('off-input-path').value;
    if (!path) return alert('Select PPTX file.');
    const dest = await api.select_save_file('slides.md', ['Markdown (*.md)']);
    if (dest) {
      const res = await api.office_pptx_to_markdown(path, dest);
      if (res.error) showStatus('off-status-box', res.error, true);
      else showStatus('off-status-box', `Slides markdown saved to ${dest}`);
    }
  });

  document.getElementById('off-xlsx-to-csv-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('off-input-path').value;
    if (!path) return alert('Select XLSX file.');
    const dest = await api.select_save_file('sheet.csv', ['CSV (*.csv)']);
    if (dest) {
      const res = await api.office_xlsx_to_csv(path, dest);
      if (res.error) showStatus('off-status-box', res.error, true);
      else showStatus('off-status-box', `CSV saved to ${dest}`);
    }
  });
}

// -------------------------------------------------------------
// 15. Screen Capture
// -------------------------------------------------------------
function setupScreenshotStudio() {
  const api = getApi();

  document.getElementById('snip-run-btn')?.addEventListener('click', async () => {
    showStatus('snip-status-box', 'Capturing full screen...');
    const res = await api.capture_screen();
    if (res.data_url) {
      document.getElementById('snip-status-box').style.display = 'none';
      document.getElementById('snip-result-card').style.display = 'block';
      const img = document.getElementById('snip-preview-img');
      img.src = res.data_url;
      const dl = document.getElementById('snip-download-btn');
      dl.href = res.data_url;
    } else if (res.error) {
      showStatus('snip-status-box', res.error, true);
    }
  });
}

// -------------------------------------------------------------
// 16. Live Network Monitor
// -------------------------------------------------------------
function setupNetworkMonitor() {
  const api = getApi();
  let netData = [];

  async function refreshNet() {
    const res = await api.get_network_connections();
    if (res.connections) {
      netData = res.connections;
      renderNetTable(netData);
      document.getElementById('net-count-total').textContent = netData.length;
    }
  }

  function renderNetTable(connections) {
    const tbody = document.querySelector('#net-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    connections.slice(0, 100).forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${c.pid || '-'}</td>
        <td><strong>${c.process_name || 'System'}</strong></td>
        <td>${c.local_address}:${c.local_port}</td>
        <td>${c.remote_address ? `${c.remote_address}:${c.remote_port}` : '*'}</td>
        <td>${c.protocol}</td>
        <td><span class="badge ${c.status === 'ESTABLISHED' ? 'badge-done' : 'badge-ready'}">${c.status}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('net-refresh-btn')?.addEventListener('click', refreshNet);

  document.getElementById('net-filter-input')?.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = netData.filter(c =>
      (c.process_name && c.process_name.toLowerCase().includes(q)) ||
      (c.remote_address && c.remote_address.includes(q)) ||
      (c.local_address && c.local_address.includes(q))
    );
    renderNetTable(filtered);
  });
}

// -------------------------------------------------------------
// 17. Playlist Porter
// -------------------------------------------------------------
function setupPlaylistPorter() {
  const api = getApi();

  document.getElementById('pl-clean-btn')?.addEventListener('click', async () => {
    const raw = document.getElementById('pl-title-input').value;
    if (!raw) return alert('Enter music title or video name.');
    const res = await api.playlist_fetch(raw);
    if (res.title) {
      document.getElementById('pl-result-card').style.display = 'block';
      const parts = res.title.split(' - ');
      if (parts.length >= 2) {
        document.getElementById('pl-res-artist').value = parts[0].trim();
        document.getElementById('pl-res-title').value = parts.slice(1).join(' - ').trim();
      } else {
        document.getElementById('pl-res-artist').value = 'Unknown';
        document.getElementById('pl-res-title').value = res.title;
      }
    }
  });
}

// -------------------------------------------------------------
// 18. Resume Builder & ATS Matcher
// -------------------------------------------------------------
function setupResumeBuilder() {
  const api = getApi();
  let masterResume = null;

  document.getElementById('res-sample-btn')?.addEventListener('click', async () => {
    const res = await api.resume_sample();
    masterResume = res;
    populateResumeFields(res);
    renderResumePreview();
  });

  document.getElementById('res-open-file-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['JSON Resume (*.json)', 'All Files (*.*)'], false);
    if (files && files.length > 0) {
      const res = await api.resume_load_file(files[0]);
      if (res && res.resume) {
        masterResume = res.resume;
        populateResumeFields(masterResume);
        renderResumePreview();
      }
    }
  });

  document.getElementById('res-save-file-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('resume_profile.json', ['JSON Resume (*.json)']);
    if (dest) {
      const data = gatherResumeFields();
      await api.resume_save_file(data, dest);
      alert(`Resume saved to ${dest}`);
    }
  });

  function populateResumeFields(data) {
    if (data.contact) {
      document.getElementById('res-name').value = data.contact.name || '';
      document.getElementById('res-email').value = data.contact.email || '';
      document.getElementById('res-phone').value = data.contact.phone || '';
    }
    document.getElementById('res-summary').value = data.summary || '';
    document.getElementById('res-skills').value = (data.skills || []).join(', ');
    document.getElementById('res-json').value = JSON.stringify(data, null, 2);
  }

  function gatherResumeFields() {
    if (!masterResume) masterResume = {};
    masterResume.contact = {
      name: document.getElementById('res-name').value,
      email: document.getElementById('res-email').value,
      phone: document.getElementById('res-phone').value
    };
    masterResume.summary = document.getElementById('res-summary').value;
    masterResume.skills = document.getElementById('res-skills').value.split(',').map(s => s.trim()).filter(Boolean);
    return masterResume;
  }

  async function renderResumePreview() {
    const data = gatherResumeFields();
    const res = await api.resume_render_html(data);
    if (res.html) {
      document.getElementById('res-preview-pane').innerHTML = res.html;
    }
  }

  document.getElementById('res-update-preview-btn')?.addEventListener('click', renderResumePreview);

  document.getElementById('res-run-ats-btn')?.addEventListener('click', async () => {
    const job = document.getElementById('res-job-desc').value;
    if (!job) return alert('Paste a job description.');
    const data = gatherResumeFields();
    const res = await api.resume_analyze_ats(data, job);
    if (res) {
      document.getElementById('res-ats-results').style.display = 'block';
      const pct = res.score <= 1.0 ? Math.round(res.score * 100) : Math.round(res.score);
      document.getElementById('res-ats-score').textContent = `${pct}%`;
      const matched = res.matched_keywords || res.matched || [];
      const missing = res.missing_keywords || res.missing || [];
      document.getElementById('res-ats-matched').textContent = matched.join(', ') || 'None';
      document.getElementById('res-ats-missing').textContent = missing.join(', ') || 'None';
    }
  });

  document.getElementById('res-export-pdf-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('resume.pdf', ['PDF (*.pdf)']);
    if (dest) {
      const data = gatherResumeFields();
      await api.resume_export_pdf(data, dest);
      alert(`Resume PDF exported to ${dest}`);
    }
  });

  document.getElementById('res-export-docx-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('resume.docx', ['Word Document (*.docx)']);
    if (dest) {
      const data = gatherResumeFields();
      await api.resume_export_docx(data, dest);
      alert(`Resume DOCX exported to ${dest}`);
    }
  });

  document.getElementById('res-export-md-btn')?.addEventListener('click', async () => {
    const dest = await api.select_save_file('resume.md', ['Markdown (*.md)']);
    if (dest) {
      const data = gatherResumeFields();
      const res = await api.resume_export_markdown(data);
      if (res.markdown) {
        await api.save_file(res.markdown, dest);
        alert(`Resume Markdown saved to ${dest}`);
      }
    }
  });
}

// -------------------------------------------------------------
// 19. QR Codes & Barcodes
// -------------------------------------------------------------
function setupQRStudio() {
  const api = getApi();

  function getActiveQrText() {
    const activeTab = document.querySelector('[data-qrpreset].active')?.getAttribute('data-qrpreset') || 'text';
    let text = document.getElementById('qr-input').value;

    if (activeTab === 'wifi') {
      const ssid = document.getElementById('qr-wifi-ssid').value;
      const pass = document.getElementById('qr-wifi-pass').value;
      const sec = document.getElementById('qr-wifi-sec').value;
      text = `WIFI:T:${sec};S:${ssid};P:${pass};;`;
    } else if (activeTab === 'contact') {
      const name = document.getElementById('qr-vc-name').value;
      const phone = document.getElementById('qr-vc-phone').value;
      const email = document.getElementById('qr-vc-email').value;
      const org = document.getElementById('qr-vc-org').value;
      text = `BEGIN:VCARD\nVERSION:3.0\nN:${name}\nFN:${name}\nORG:${org}\nTEL:${phone}\nEMAIL:${email}\nEND:VCARD`;
    } else if (activeTab === 'email') {
      const email = document.getElementById('qr-email-addr').value;
      const sub = document.getElementById('qr-email-sub').value;
      text = `mailto:${email}?subject=${encodeURIComponent(sub)}`;
    } else if (activeTab === 'sms') {
      const phone = document.getElementById('qr-sms-phone').value;
      const msg = document.getElementById('qr-sms-msg').value;
      text = `smsto:${phone}:${msg}`;
    }
    return text;
  }

  document.getElementById('qr-generate-btn')?.addEventListener('click', async () => {
    const text = getActiveQrText();
    const level = document.getElementById('qr-level').value;
    const boxSize = parseInt(document.getElementById('qr-box-size').value) || 10;
    const fg = document.getElementById('qr-fg').value;
    const bg = document.getElementById('qr-bg').value;

    const res = await api.generate_qr(text, level, boxSize, 2, fg, bg);
    if (res.data_url) {
      document.getElementById('qr-output-card').style.display = 'block';
      const img = document.getElementById('qr-preview-img');
      img.src = res.data_url;
      document.getElementById('qr-download-link').href = res.data_url;
    }
  });

  document.getElementById('qr-download-svg-btn')?.addEventListener('click', async () => {
    const text = getActiveQrText();
    const level = document.getElementById('qr-level').value;
    const boxSize = parseInt(document.getElementById('qr-box-size').value) || 10;
    const fg = document.getElementById('qr-fg').value;
    const bg = document.getElementById('qr-bg').value;
    const dest = await api.select_save_file('qrcode.svg', ['Vector SVG (*.svg)']);
    if (dest) {
      const res = await api.generate_qr_svg(text, level, boxSize, 2, fg, bg);
      if (res.svg) {
        await api.save_file(res.svg, dest);
        alert(`SVG QR Code saved to ${dest}`);
      }
    }
  });

  document.getElementById('qr-copy-btn')?.addEventListener('click', async () => {
    const img = document.getElementById('qr-preview-img');
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || 250;
    canvas.height = img.naturalHeight || 250;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    canvas.toBlob(blob => {
      navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      alert('QR Code image copied to clipboard.');
    });
  });

  // Barcode
  document.getElementById('bc-generate-btn')?.addEventListener('click', async () => {
    const val = document.getElementById('bc-input').value;
    const type = document.getElementById('bc-type').value;
    if (!val) return alert('Enter barcode data.');
    const res = await api.generate_barcode(val, type);
    if (res.data_url) {
      document.getElementById('bc-output-card').style.display = 'block';
      const img = document.getElementById('bc-preview-img');
      img.src = res.data_url;
      document.getElementById('bc-download-link').href = res.data_url;
    }
  });

  // Decode
  document.getElementById('qr-decode-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['Image Files (*.png;*.jpg;*.webp;*.bmp)'], false);
    if (files) document.getElementById('qr-decode-path').value = files[0];
  });

  document.getElementById('qr-decode-run-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('qr-decode-path').value;
    if (!path) return alert('Select image file containing code.');
    const res = await api.decode_qr(path);
    if (res.codes && res.codes.length > 0) {
      document.getElementById('qr-decode-result-card').style.display = 'block';
      document.getElementById('qr-decode-output').value = res.codes.map(c => `[${c.type}] ${c.payload}`).join('\n\n');
    } else {
      alert('No barcode or QR code detected in image.');
    }
  });

  document.getElementById('qr-decode-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('qr-decode-output').value);
    alert('Decoded payload copied to clipboard.');
  });
}

// -------------------------------------------------------------
// 20. Hash & Checksum Studio
// -------------------------------------------------------------
function setupHashStudio() {
  const api = getApi();

  // Multi-hash
  document.getElementById('hash-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['All Files (*.*)'], false);
    if (files) document.getElementById('hash-filepath').value = files[0];
  });

  document.getElementById('hash-compute-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('hash-filepath').value;
    if (!path) return alert('Select file to compute checksums.');

    const algos = ['md5', 'sha1', 'sha256', 'sha512', 'blake2b'];
    document.getElementById('hash-multi-card').style.display = 'block';
    const tbody = document.querySelector('#hash-multi-table tbody');
    tbody.innerHTML = '';

    for (const algo of algos) {
      const res = await api.compute_hash(path, algo);
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${algo.toUpperCase()}</strong></td>
        <td style="font-family: monospace; font-size: 12px; word-break: break-all;">${res.hash || res.error}</td>
        <td><button class="btn-secondary" style="padding: 2px 8px; font-size: 11px;" onclick="navigator.clipboard.writeText('${res.hash}'); alert('Copied ${algo.toUpperCase()} hash');">Copy</button></td>
      `;
      tbody.appendChild(tr);
    }
  });

  // Text Hash
  document.getElementById('hash-text-run-btn')?.addEventListener('click', async () => {
    const txt = document.getElementById('hash-text-input').value;
    const algo = document.getElementById('hash-text-algo').value;
    const res = await api.hash_text(txt, algo);
    document.getElementById('hash-text-result-card').style.display = 'block';
    document.getElementById('hash-text-result-val').value = res.hash;
  });

  document.getElementById('hash-text-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('hash-text-result-val').value);
    alert('Hash copied to clipboard.');
  });

  // Verify Checksum
  document.getElementById('hash-vfile-browse-btn')?.addEventListener('click', async () => {
    const files = await api.select_file(['All Files (*.*)'], false);
    if (files) document.getElementById('hash-vfile-path').value = files[0];
  });

  document.getElementById('hash-vrun-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('hash-vfile-path').value;
    const expected = document.getElementById('hash-vexpected-val').value.trim();
    if (!path || !expected) return alert('Select file and enter expected hash.');

    const res = await api.verify_hash(path, expected);
    const box = document.getElementById('hash-vstatus-box');
    box.style.display = 'block';
    if (res.matches) {
      box.className = 'tool-card status-box success';
      box.textContent = `MATCH VERIFIED: Checksum matches ${res.algorithm.toUpperCase()} digest perfectly.`;
    } else {
      box.className = 'tool-card status-box error';
      box.textContent = `MISMATCH DETECTED: Computed ${res.computed} does not match expected value.`;
    }
  });

  // Manifest
  document.getElementById('hash-man-browse-btn')?.addEventListener('click', async () => {
    const dir = await api.select_directory();
    if (dir) document.getElementById('hash-man-dir').value = dir;
  });

  document.getElementById('hash-man-gen-btn')?.addEventListener('click', async () => {
    const dir = document.getElementById('hash-man-dir').value;
    if (!dir) return alert('Select folder to generate manifest.');
    const dest = await api.select_save_file('checksums.txt', ['Manifest (*.txt)']);
    if (dest) {
      showStatus('hash-man-status-box', 'Scanning folder and generating manifest...');
      const res = await api.generate_manifest(dir, dest);
      if (res.error) showStatus('hash-man-status-box', res.error, true);
      else showStatus('hash-man-status-box', `Manifest generated with ${res.file_count} files.`);
    }
  });

  document.getElementById('hash-man-verify-btn')?.addEventListener('click', async () => {
    const dir = document.getElementById('hash-man-dir').value;
    if (!dir) return alert('Select folder.');
    const files = await api.select_file(['Manifest (*.txt)'], false);
    if (files) {
      showStatus('hash-man-status-box', 'Verifying files against manifest...');
      const res = await api.verify_manifest(files[0], dir);
      if (res.error) showStatus('hash-man-status-box', res.error, true);
      else {
        const pass = res.matches ? 'ALL MATCHED' : `${res.mismatches?.length || 0} MISMATCHES`;
        showStatus('hash-man-status-box', `Verification: ${pass}`, !res.matches);
      }
    }
  });
}

// -------------------------------------------------------------
// 21. JSON & Data Tools
// -------------------------------------------------------------
function setupJsonStudio() {
  const api = getApi();
  const input = document.getElementById('json-input');
  const output = document.getElementById('json-output');

  function getIndent() {
    const val = document.getElementById('data-indent-select').value;
    return val === 'tab' ? '\t' : parseInt(val);
  }

  document.getElementById('json-format-btn')?.addEventListener('click', () => {
    try {
      const obj = JSON.parse(input.value);
      output.value = JSON.stringify(obj, null, getIndent());
    } catch (e) {
      alert(`Invalid JSON syntax: ${e.message}`);
    }
  });

  document.getElementById('json-minify-btn')?.addEventListener('click', async () => {
    const res = await api.minify_json(input.value);
    if (res.error) alert(res.error);
    else output.value = res.minified;
  });

  document.getElementById('json-validate-btn')?.addEventListener('click', () => {
    try {
      JSON.parse(input.value);
      alert('JSON Syntax is valid.');
    } catch (e) {
      alert(`Invalid JSON Syntax:\n${e.message}`);
    }
  });

  document.getElementById('json-schema-btn')?.addEventListener('click', async () => {
    const res = await api.infer_json_schema(input.value);
    if (res.error) alert(res.error);
    else output.value = JSON.stringify(res.schema, null, 2);
  });

  document.getElementById('json-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(output.value);
    alert('Output copied to clipboard.');
  });

  document.getElementById('data-convert-btn')?.addEventListener('click', async () => {
    const mode = document.getElementById('data-convert-select').value;
    const parts = mode.split('_to_');
    const res = await api.convert_data_format(input.value, parts[0], parts[1]);
    if (res.error) alert(res.error);
    else output.value = res.output;
  });

  document.getElementById('data-jsonpath-btn')?.addEventListener('click', async () => {
    const query = document.getElementById('data-jsonpath-input').value;
    const res = await api.query_jsonpath(input.value, query);
    if (res.error) alert(res.error);
    else output.value = JSON.stringify(res.result, null, 2);
  });

  document.getElementById('data-jsonpath-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      document.getElementById('data-jsonpath-btn')?.click();
    }
  });

  document.getElementById('data-fmt-sql-btn')?.addEventListener('click', async () => {
    const res = await api.format_sql(input.value);
    if (res.error) alert(res.error);
    else output.value = res.formatted;
  });

  document.getElementById('data-fmt-css-btn')?.addEventListener('click', async () => {
    const res = await api.format_css(input.value);
    if (res.error) alert(res.error);
    else output.value = res.formatted;
  });

  document.getElementById('data-fmt-js-btn')?.addEventListener('click', async () => {
    const res = await api.format_js(input.value);
    if (res.error) alert(res.error);
    else output.value = res.formatted;
  });
}

// -------------------------------------------------------------
// 22. Text Tools
// -------------------------------------------------------------
function setupTextTools() {
  const api = getApi();
  const input = document.getElementById('tt-input');
  const output = document.getElementById('tt-output');
  const card = document.getElementById('tt-result-card');

  document.querySelectorAll('[data-case]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const mode = btn.getAttribute('data-case');
      const val = input.value;
      if (api?.text_case_transform) {
        const res = await api.text_case_transform(val, mode);
        if (res.error) {
          alert(res.error);
        } else {
          card.style.display = 'block';
          output.value = res.result;
        }
        return;
      }
      let res = '';
      if (mode === 'upper') res = val.toUpperCase();
      else if (mode === 'lower') res = val.toLowerCase();
      else if (mode === 'title') res = val.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
      else if (mode === 'camel') res = val.toLowerCase().replace(/[^a-zA-Z0-9]+(.)/g, (m, chr) => chr.toUpperCase());
      else if (mode === 'snake') res = val.toLowerCase().replace(/\s+/g, '_');
      else if (mode === 'kebab') res = val.toLowerCase().replace(/\s+/g, '-');
      else if (mode === 'constant') res = val.toUpperCase().replace(/\s+/g, '_');
      card.style.display = 'block';
      output.value = res;
    });
  });

  document.querySelectorAll('[data-line]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const mode = btn.getAttribute('data-line');
      if (api?.text_line_ops) {
        const res = await api.text_line_ops(input.value, mode);
        if (res.error) {
          alert(res.error);
        } else {
          card.style.display = 'block';
          output.value = res.result;
        }
        return;
      }
      const lines = input.value.split('\n');
      let res = [];
      if (mode === 'sort') res = [...lines].sort();
      else if (mode === 'dedupe') res = [...new Set(lines)];
      else if (mode === 'reverse') res = [...lines].reverse();
      else if (mode === 'remove_blank') res = lines.filter(l => l.trim() !== '');
      else if (mode === 'number') res = lines.map((l, i) => `${i + 1}. ${l}`);
      card.style.display = 'block';
      output.value = res.join('\n');
    });
  });

  document.getElementById('tt-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(output.value);
    alert('Transformed text copied to clipboard.');
  });
}

// -------------------------------------------------------------
// 23. Encoding & Decoding
// -------------------------------------------------------------
function setupEncodingStudio() {
  const api = getApi();
  const input = document.getElementById('enc-input');
  const output = document.getElementById('enc-output');
  const card = document.getElementById('enc-result-card');
  const method = document.getElementById('enc-method');

  document.getElementById('enc-encode-btn')?.addEventListener('click', async () => {
    const m = method.value;
    const txt = input.value;
    if (api?.encoding_transform) {
      const res = await api.encoding_transform(txt, m, 'encode');
      if (res.error) {
        alert(res.error);
      } else {
        card.style.display = 'block';
        output.value = res.result;
      }
      return;
    }
    let res = '';
    try {
      if (m === 'base64') res = btoa(unescape(encodeURIComponent(txt)));
      else if (m === 'url') res = encodeURIComponent(txt);
      else if (m === 'html') res = txt.replace(/[\u00A0-\u9999<>\&]/g, (i) => `&#${i.charCodeAt(0)};`);
      else if (m === 'hex') res = Array.from(new TextEncoder().encode(txt)).map(b => b.toString(16).padStart(2, '0')).join(' ');
      else if (m === 'binary') res = Array.from(new TextEncoder().encode(txt)).map(b => b.toString(2).padStart(8, '0')).join(' ');
      card.style.display = 'block';
      output.value = res;
    } catch (e) {
      alert(`Encoding error: ${e.message}`);
    }
  });

  document.getElementById('enc-decode-btn')?.addEventListener('click', async () => {
    const m = method.value;
    const txt = input.value;
    if (api?.encoding_transform) {
      const res = await api.encoding_transform(txt, m, 'decode');
      if (res.error) {
        alert(res.error);
      } else {
        card.style.display = 'block';
        output.value = res.result;
      }
      return;
    }
    let res = '';
    try {
      if (m === 'base64') res = decodeURIComponent(escape(atob(txt)));
      else if (m === 'url') res = decodeURIComponent(txt);
      else if (m === 'html') {
        const doc = new DOMParser().parseFromString(txt, 'text/html');
        res = doc.documentElement.textContent;
      } else if (m === 'hex') {
        const matches = txt.replace(/\s+/g, '').match(/.{1,2}/g) || [];
        const bytes = matches.map(byte => parseInt(byte, 16));
        res = new TextDecoder().decode(new Uint8Array(bytes));
      } else if (m === 'binary') {
        const matches = txt.replace(/\s+/g, '').match(/.{1,8}/g) || [];
        const bytes = matches.map(byte => parseInt(byte, 2));
        res = new TextDecoder().decode(new Uint8Array(bytes));
      }
      card.style.display = 'block';
      output.value = res;
    } catch (e) {
      alert(`Decoding error: ${e.message}`);
    }
  });

  document.getElementById('enc-copy-btn')?.addEventListener('click', () => {
    navigator.clipboard.writeText(output.value);
    alert('Result copied to clipboard.');
  });
}
