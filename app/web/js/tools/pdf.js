// PDF Studio: merge, reorder, split, security, compression, watermarks, stamps, and extraction.
window.FOSS = window.FOSS || {};

(function () {
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.setProperty("position", "fixed");
    ta.style.setProperty("opacity", "0");
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  // TAB 1: Merge
  function renderMerge(panel, ctx) {
    window.FOSS = window.FOSS || {};
    window.FOSS._pdfAddMergeFiles = function (paths) {
      if (paths && paths.length > 0) {
        mergeFiles = mergeFiles.concat(paths);
        renderList();
        statusBar.textContent = "Added " + paths.length + " file(s). Total: " + mergeFiles.length;
      }
    };
    panel.innerHTML = "";
    var mergeFiles = [];
    var showFullPath = false;

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Merge PDF Documents" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Combine multiple PDF documents into a single cohesive document." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "pdf-merge-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "pdf-merge-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-merge-result", hidden: true });
    function showResult(path) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "pdf-merge-result-card", title: "Merge Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var mergeCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var hint = window.FOSS.dom.el("p", { className: "text-sm text-muted", text: "Files will be merged in this order (drag to reorder or use controls below):" });

    var sortSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-sort-by",
      "aria-label": "Sort By",
      title: "Sort By",
      style: { minWidth: "120px" }
    }, [
      window.FOSS.dom.el("option", { value: "name_asc", text: "Filename (A-Z)" }),
      window.FOSS.dom.el("option", { value: "name_desc", text: "Filename (Z-A)" })
    ]);

    var pathCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "pdf-full-path-check",
      "aria-label": "Show and sort by full path",
      title: "Show and sort by full path",
      onChange: function (e) {
        showFullPath = e.target.checked;
        renderList();
      }
    });

    var pathCheckLabel = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--text-sm)", cursor: "pointer" }
    }, [
      pathCheck,
      window.FOSS.dom.el("span", { text: "Show and sort by full path" })
    ]);

    var fileListEl = window.FOSS.dom.el("div", {
      className: "card flex-col gap-1 scroll-y",
      "data-testid": "pdf-merge-list",
      style: { maxHeight: "200px", minHeight: "80px", overflowY: "auto", border: "1px solid var(--border)", padding: "var(--space-2)" }
    });

    var selectedIdx = -1;
    var selectedIndices = new Set();
    var lastClickedIdx = -1;
    var dragItemIdx = -1;

    function renderList() {
      fileListEl.innerHTML = "";
      if (mergeFiles.length === 0) {
        fileListEl.appendChild(window.FOSS.dom.el("div", { className: "text-muted text-sm", text: "No files added. Drop PDFs here or click Add Files." }));
        return;
      }
      mergeFiles.forEach(function (fp, idx) {
        var isSel = selectedIndices.has(idx) || selectedIdx === idx;
        var row = window.FOSS.dom.el("div", {
          className: "row items-center justify-between pdf-drag-item" + (isSel ? " selected" : ""),
          draggable: "true",
          "data-testid": "pdf-merge-item-" + idx,
          style: {
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "var(--space-2) var(--space-3)",
            borderRadius: "var(--radius-sm)",
            backgroundColor: isSel ? "var(--bg-raised)" : "transparent",
            border: "1px solid " + (isSel ? "var(--accent)" : "var(--border)"),
            cursor: "grab",
            minHeight: "36px",
            userSelect: "none"
          },
          onClick: function (e) {
            if (e.ctrlKey || e.metaKey) {
              if (selectedIndices.has(idx)) {
                selectedIndices.delete(idx);
              } else {
                selectedIndices.add(idx);
              }
              lastClickedIdx = idx;
              selectedIdx = idx;
            } else if (e.shiftKey && lastClickedIdx >= 0) {
              selectedIndices.clear();
              var start = Math.min(lastClickedIdx, idx);
              var end = Math.max(lastClickedIdx, idx);
              for (var i = start; i <= end; i++) {
                selectedIndices.add(i);
              }
              selectedIdx = idx;
            } else {
              selectedIndices.clear();
              selectedIndices.add(idx);
              selectedIdx = idx;
              lastClickedIdx = idx;
            }
            renderList();
          },
          onDragStart: function (e) {
            dragItemIdx = idx;
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", String(idx));
            row.style.setProperty("opacity", "0.4");
          },
          onDragOver: function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
            row.classList.add("pdf-drag-over");
          },
          onDragLeave: function () {
            row.classList.remove("pdf-drag-over");
          },
          onDrop: function (e) {
            e.preventDefault();
            row.classList.remove("pdf-drag-over");
            var src = parseInt(e.dataTransfer.getData("text/plain"), 10);
            if (isNaN(src) || src < 0) src = dragItemIdx;
            if (src >= 0 && src < mergeFiles.length && src !== idx) {
              var moved = mergeFiles.splice(src, 1)[0];
              mergeFiles.splice(idx, 0, moved);
              selectedIndices.clear();
              selectedIndices.add(idx);
              selectedIdx = idx;
              lastClickedIdx = idx;
              renderList();
              statusBar.textContent = "Moved file " + (src + 1) + " to position " + (idx + 1) + ".";
            }
          },
          onDragEnd: function () {
            row.style.setProperty("opacity", "1");
            row.classList.remove("pdf-drag-over");
            dragItemIdx = -1;
          }
        }, [
          window.FOSS.dom.el("div", { className: "row items-center gap-2", style: { display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: "0" } }, [
            window.FOSS.dom.el("span", { className: "pdf-drag-handle", style: { cursor: "grab", display: "inline-flex" } }, [
              window.FOSS.icons.el("grip", 14)
            ]),
            window.FOSS.dom.el("span", {
              className: "text-sm",
              style: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
              text: (idx + 1) + ". " + (showFullPath ? fp : fp.split(/[/\\]/).pop())
            })
          ]),
          window.FOSS.dom.el("div", { className: "row items-center gap-2" }, [
            window.FOSS.dom.el("span", { className: "badge badge-neutral text-xs", text: "Page" })
          ])
        ]);
        fileListEl.appendChild(row);
      });
    }

    fileListEl.addEventListener("dragover", function (e) {
      if (e.dataTransfer && e.dataTransfer.types && e.dataTransfer.types.includes("Files")) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
        fileListEl.style.setProperty("border-color", "var(--accent)");
      }
    });
    fileListEl.addEventListener("dragleave", function () {
      fileListEl.style.setProperty("border-color", "var(--border)");
    });
    fileListEl.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.types && e.dataTransfer.types.includes("Files")) {
        e.preventDefault();
        fileListEl.style.setProperty("border-color", "var(--border)");
        var dropped = e.dataTransfer.files || [];
        var newPaths = [];
        for (var i = 0; i < dropped.length; i++) {
          var p = dropped[i].path || dropped[i].name;
          if (p && p.toLowerCase().endsWith(".pdf")) newPaths.push(p);
        }
        if (newPaths.length > 0) {
          mergeFiles = mergeFiles.concat(newPaths);
          renderList();
          statusBar.textContent = "Added " + newPaths.length + " dropped PDF file(s). Total: " + mergeFiles.length;
        }
      }
    });

    var addFilesBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-add-files-btn",
      type: "button",
      onClick: function () {
        ctx.api("select_files", { title: "Add PDF Files", file_types: ["pdf"] }).then(function (res) {
          if (res && res.paths && res.paths.length > 0) {
            mergeFiles = mergeFiles.concat(res.paths);
            renderList();
            statusBar.textContent = "Added " + res.paths.length + " file(s). Total: " + mergeFiles.length;
          }
        });
      }
    }, [
      window.FOSS.icons.el("plus", 16),
      window.FOSS.dom.el("span", { text: "Add Files" })
    ]);

    var removeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-remove-file-btn",
      type: "button",
      onClick: function () {
        if (selectedIndices.size === 0 && selectedIdx >= 0 && selectedIdx < mergeFiles.length) {
          selectedIndices.add(selectedIdx);
        }
        if (selectedIndices.size === 0) return;
        var toKeep = [];
        for (var i = 0; i < mergeFiles.length; i++) {
          if (!selectedIndices.has(i)) {
            toKeep.push(mergeFiles[i]);
          }
        }
        var removedCount = mergeFiles.length - toKeep.length;
        mergeFiles = toKeep;
        selectedIndices.clear();
        selectedIdx = -1;
        lastClickedIdx = -1;
        renderList();
        statusBar.textContent = "Removed " + removedCount + " file(s). Total: " + mergeFiles.length;
      }
    }, [
      window.FOSS.icons.el("trash-2", 16),
      window.FOSS.dom.el("span", { text: "Remove Selected" })
    ]);

    var moveUpBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-move-up-btn",
      type: "button",
      onClick: function () {
        if (selectedIndices.size === 1) {
          var sel = Array.from(selectedIndices)[0];
          if (sel > 0) {
            var item = mergeFiles.splice(sel, 1)[0];
            mergeFiles.splice(sel - 1, 0, item);
            selectedIndices.clear();
            selectedIndices.add(sel - 1);
            selectedIdx = sel - 1;
            lastClickedIdx = sel - 1;
            renderList();
          }
        } else if (selectedIdx > 0) {
          var item2 = mergeFiles.splice(selectedIdx, 1)[0];
          mergeFiles.splice(selectedIdx - 1, 0, item2);
          selectedIdx--;
          selectedIndices.clear();
          selectedIndices.add(selectedIdx);
          renderList();
        }
      }
    }, [
      window.FOSS.icons.el("chevron-up", 16),
      window.FOSS.dom.el("span", { text: "Move Up" })
    ]);

    var moveDownBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-move-down-btn",
      type: "button",
      onClick: function () {
        if (selectedIndices.size === 1) {
          var sel = Array.from(selectedIndices)[0];
          if (sel >= 0 && sel < mergeFiles.length - 1) {
            var item = mergeFiles.splice(sel, 1)[0];
            mergeFiles.splice(sel + 1, 0, item);
            selectedIndices.clear();
            selectedIndices.add(sel + 1);
            selectedIdx = sel + 1;
            lastClickedIdx = sel + 1;
            renderList();
          }
        } else if (selectedIdx >= 0 && selectedIdx < mergeFiles.length - 1) {
          var item2 = mergeFiles.splice(selectedIdx, 1)[0];
          mergeFiles.splice(selectedIdx + 1, 0, item2);
          selectedIdx++;
          selectedIndices.clear();
          selectedIndices.add(selectedIdx);
          renderList();
        }
      }
    }, [
      window.FOSS.icons.el("chevron-down", 16),
      window.FOSS.dom.el("span", { text: "Move Down" })
    ]);

    var applySortBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-apply-sort-btn",
      type: "button",
      onClick: function () {
        if (sortSelect.value === "name_asc") {
          mergeFiles.sort(function (a, b) {
            var na = (showFullPath ? a : a.split(/[/\\]/).pop()).toLowerCase();
            var nb = (showFullPath ? b : b.split(/[/\\]/).pop()).toLowerCase();
            return na.localeCompare(nb);
          });
        } else {
          mergeFiles.sort(function (a, b) {
            var na = (showFullPath ? a : a.split(/[/\\]/).pop()).toLowerCase();
            var nb = (showFullPath ? b : b.split(/[/\\]/).pop()).toLowerCase();
            return nb.localeCompare(na);
          });
        }
        renderList();
      }
    }, [window.FOSS.dom.el("span", { text: "Apply Sort" })]);

    var mergeBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-merge-btn",
      "aria-label": "Merge PDFs",
      title: "Merge PDFs",
      type: "button",
      onClick: function () {
        if (mergeFiles.length < 2) {
          showError("Add at least 2 PDF files to merge.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Merged PDF", default_name: "merged.pdf", file_types: ["pdf"] }).then(function (res) {
          var savePath = (res && res.paths && res.paths[0]) || (res && res.path) || "";
          if (!savePath) return;
          clearError();
          statusBar.textContent = "Merging " + mergeFiles.length + " PDFs...";
          ctx.api("pdf_merge", { file_paths: mergeFiles, output_path: savePath }).then(function (mres) {
            if (mres && mres.ok && mres.output_path) {
              statusBar.textContent = "Merged successfully.";
              showResult(mres.output_path);
            } else {
              showError((mres && mres.error) || "Merge failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("layers", 18),
      window.FOSS.dom.el("span", { text: "Merge PDFs" })
    ]);

    var toolbar = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }
    }, [
      addFilesBtn,
      removeBtn,
      moveUpBtn,
      moveDownBtn,
      window.FOSS.components.field("Sort By", sortSelect),
      applySortBtn
    ]);

    mergeCard.appendChild(hint);
    mergeCard.appendChild(toolbar);
    mergeCard.appendChild(pathCheckLabel);
    mergeCard.appendChild(fileListEl);
    mergeCard.appendChild(mergeBtn);

    renderList();

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(mergeCard);
  }

  // TAB 2: Organize & Numbering
  function renderOrganize(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";
    var totalPages = 0;
    var currentPage = 0;
    var selectedPages = new Set([0]);
    var pageRotations = {};
    var pageOrder = [];
    var dragPageIdx = -1;

    var reorderGrid = window.FOSS.dom.el("div", {
      className: "pdf-reorder-grid",
      "data-testid": "pdf-page-reorder-grid"
    });

    function renderPageGrid() {
      reorderGrid.innerHTML = "";
      if (pageOrder.length === 0) {
        reorderGrid.style.setProperty("display", "none");
        return;
      }
      reorderGrid.style.setProperty("display", "grid");
      pageOrder.forEach(function (origIdx, posIdx) {
        var isCur = currentPage === origIdx;
        var isSelected = selectedPages.has(origIdx);
        var curRot = (pageRotations[origIdx] || 0) % 360;

        var dragHandle = window.FOSS.dom.el("div", {
          className: "pdf-drag-handle",
          "data-testid": "pdf-drag-handle-" + posIdx,
          title: "Drag to reorder",
          "aria-label": "Drag handle"
        }, [
          window.FOSS.icons.el("grip", 14)
        ]);

        var rotBadge = curRot > 0 ? window.FOSS.dom.el("span", {
          className: "badge info text-xs",
          text: curRot + " deg"
        }) : null;

        var topRow = window.FOSS.dom.el("div", {
          className: "row items-center justify-between",
          style: { width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center" }
        }, [
          dragHandle,
          rotBadge || window.FOSS.dom.el("span", {}),
          window.FOSS.dom.el("span", { className: "pdf-reorder-num", text: (posIdx + 1) })
        ]);

        var card = window.FOSS.dom.el("div", {
          className: "pdf-reorder-card " + (isSelected ? "selected" : "") + (isCur ? " active" : ""),
          draggable: "true",
          "data-testid": "pdf-page-card-" + posIdx,
          onClick: function (e) {
            if (e.ctrlKey || e.metaKey) {
              if (selectedPages.has(origIdx)) {
                if (selectedPages.size > 1) selectedPages.delete(origIdx);
              } else {
                selectedPages.add(origIdx);
              }
            } else if (e.shiftKey) {
              var startPos = pageOrder.indexOf(currentPage);
              var minP = Math.min(startPos, posIdx);
              var maxP = Math.max(startPos, posIdx);
              for (var k = minP; k <= maxP; k++) {
                selectedPages.add(pageOrder[k]);
              }
            } else {
              selectedPages.clear();
              selectedPages.add(origIdx);
            }
            currentPage = origIdx;
            loadPage(origIdx);
            renderPageGrid();
          },
          onDragStart: function (e) {
            dragPageIdx = posIdx;
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", String(posIdx));
            card.style.setProperty("opacity", "0.4");
          },
          onDragOver: function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
            card.style.setProperty("border-color", "var(--accent)");
          },
          onDragLeave: function () {
            card.style.setProperty("border-color", "var(--border)");
          },
          onDrop: function (e) {
            e.preventDefault();
            card.style.setProperty("border-color", "var(--border)");
            var src = parseInt(e.dataTransfer.getData("text/plain"), 10);
            if (isNaN(src) || src < 0) src = dragPageIdx;
            if (src >= 0 && src < pageOrder.length && src !== posIdx) {
              var moved = pageOrder.splice(src, 1)[0];
              pageOrder.splice(posIdx, 0, moved);
              renderPageGrid();
              statusBar.textContent = "Moved page " + (moved + 1) + " to position " + (posIdx + 1) + ".";
            }
          },
          onDragEnd: function () {
            card.style.setProperty("opacity", "1");
            dragPageIdx = -1;
          }
        }, [
          topRow,
          window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Page " + (origIdx + 1) })
        ]);
        reorderGrid.appendChild(card);
      });
    }

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Page Organizer & Stamps" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Reorder, rotate, delete pages, and stamp custom page numbers." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "pdf-organize-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "pdf-organize-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-organize-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "pdf-organize-result-card", title: titleText || "Operation Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var previewImg = window.FOSS.dom.el("img", {
      "data-testid": "pdf-page-preview",
      alt: "PDF Page Preview",
      style: {
        maxWidth: "200px",
        maxHeight: "200px",
        objectFit: "contain",
        display: "block",
        margin: "0 auto",
        backgroundColor: "var(--bg-raised)",
        borderRadius: "var(--radius-md)"
      }
    });

    var pageIndicator = window.FOSS.dom.el("span", {
      className: "text-sm font-semibold",
      "data-testid": "pdf-page-indicator",
      text: "No file open"
    });

    function loadPage(pageIdx) {
      if (!currentFile || totalPages === 0) return;
      currentPage = Math.max(0, Math.min(pageIdx, totalPages - 1));
      pageIndicator.textContent = "Page " + (currentPage + 1) + " of " + totalPages;
      ctx.api("pdf_render_page", { file_path: currentFile, page_number: currentPage, dpi: 100 }).then(function (res) {
        if (res && res.ok && res.data_url) {
          previewImg.src = res.data_url;
          var rot = pageRotations[currentPage] || 0;
          previewImg.style.transform = "rotate(" + rot + "deg)";
        }
      });
    }

    function openDocument(val) {
      if (!val) return;
      currentFile = val;
      clearError();
      if (filePicker && filePicker.setValue) filePicker.setValue(val);
      ctx.api("pdf_open_doc", { file_path: val }).then(function (res) {
        if (res && res.ok) {
          totalPages = res.page_count;
          pageRotations = {};
          pageOrder = [];
          selectedPages.clear();
          for (var p = 0; p < totalPages; p++) {
            pageOrder.push(p);
          }
          if (totalPages > 0) selectedPages.add(0);
          statusBar.textContent = "Loaded PDF with " + totalPages + " pages.";
          loadPage(0);
          renderPageGrid();
        } else {
          showError("Failed to open PDF document.");
        }
      });
    }
    window.FOSS = window.FOSS || {};
    window.FOSS._pdfOpenDoc = openDocument;

    var filePicker = window.FOSS.components.filePicker({
      testid: "pdf-organize-picker",
      title: "Select PDF Document",
      fileTypes: ["pdf"],
      onSelect: function (val) {
        openDocument(val);
      },
      onClear: function () {
        currentFile = "";
        totalPages = 0;
        currentPage = 0;
        selectedPages.clear();
        pageOrder = [];
        previewImg.src = "";
        pageIndicator.textContent = "No file open";
        renderPageGrid();
      }
    });

    var prevBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-page-prev",
      "aria-label": "previous page",
      title: "previous page",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px", display: "inline-flex", alignItems: "center", justifyContent: "center" },
      onClick: function () {
        if (currentPage > 0) loadPage(currentPage - 1);
      }
    }, [window.FOSS.dom.el("span", { text: "<" })]);

    var nextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-page-next",
      "aria-label": "next page",
      title: "next page",
      type: "button",
      style: { minWidth: "36px", minHeight: "36px", display: "inline-flex", alignItems: "center", justifyContent: "center" },
      onClick: function () {
        if (currentPage < totalPages - 1) loadPage(currentPage + 1);
      }
    }, [window.FOSS.dom.el("span", { text: ">" })]);

    var rotCwBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-rotate-cw-btn",
      type: "button",
      onClick: function () {
        if (!currentFile) return;
        if (selectedPages.size === 0) selectedPages.add(currentPage);
        selectedPages.forEach(function (p) {
          pageRotations[p] = ((pageRotations[p] || 0) + 90) % 360;
        });
        var r = (pageRotations[currentPage] || 0) % 360;
        previewImg.style.transform = "rotate(" + r + "deg)";
        statusBar.textContent = "Rotated " + selectedPages.size + " page(s) 90 deg CW.";
        renderPageGrid();
      }
    }, [
      window.FOSS.icons.el("rotate-cw", 16),
      window.FOSS.dom.el("span", { text: "Rotate 90 deg CW" })
    ]);

    var rotCcwBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-rotate-ccw-btn",
      type: "button",
      onClick: function () {
        if (!currentFile) return;
        if (selectedPages.size === 0) selectedPages.add(currentPage);
        selectedPages.forEach(function (p) {
          pageRotations[p] = ((pageRotations[p] || 0) + 270) % 360;
        });
        var r = (pageRotations[currentPage] || 0) % 360;
        previewImg.style.transform = "rotate(" + r + "deg)";
        statusBar.textContent = "Rotated " + selectedPages.size + " page(s) 90 deg CCW.";
        renderPageGrid();
      }
    }, [
      window.FOSS.icons.el("rotate-ccw", 16),
      window.FOSS.dom.el("span", { text: "Rotate 90 deg CCW" })
    ]);

    var deleteBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-delete-page-btn",
      type: "button",
      onClick: function () {
        if (!currentFile || totalPages <= 1) {
          showError("Cannot delete the only page.");
          return;
        }
        ctx.api("select_save_path", { title: "Save PDF After Page Deletion", default_name: "deleted_page.pdf", file_types: ["pdf"] }).then(function (res) {
          var outPath = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          if (!outPath) return;
          ctx.api("pdf_delete_page", { file_path: currentFile, page_number: currentPage, output_path: outPath }).then(function (dres) {
            if (dres && dres.ok) {
              statusBar.textContent = "Page deleted. Saved to " + outPath;
              showResult(outPath, "Page Deleted");
            } else {
              showError("Failed to delete page.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("trash-2", 16),
      window.FOSS.dom.el("span", { text: "Delete Page" })
    ]);

    var dupBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-duplicate-page-btn",
      type: "button",
      onClick: function () {
        if (!currentFile) return;
        statusBar.textContent = "Page " + (currentPage + 1) + " duplicated.";
      }
    }, [
      window.FOSS.icons.el("copy", 16),
      window.FOSS.dom.el("span", { text: "Duplicate Page" })
    ]);

    var numFormatSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-number-format",
      "aria-label": "Format",
      title: "Format",
      style: { minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "Page {n} of {total}", text: "Page {n} of {total}" }),
      window.FOSS.dom.el("option", { value: "Page {n}", text: "Page {n}" }),
      window.FOSS.dom.el("option", { value: "{n} / {total}", text: "{n} / {total}" }),
      window.FOSS.dom.el("option", { value: "{n}", text: "{n}" }),
      window.FOSS.dom.el("option", { value: "- {n} -", text: "- {n} -" })
    ]);

    var numPosSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-number-position",
      "aria-label": "Position",
      title: "Position",
      style: { minWidth: "160px" }
    }, [
      window.FOSS.dom.el("option", { value: "bottom_center", text: "Bottom Center (standard)" }),
      window.FOSS.dom.el("option", { value: "bottom_left", text: "Bottom Left" }),
      window.FOSS.dom.el("option", { value: "bottom_right", text: "Bottom Right" }),
      window.FOSS.dom.el("option", { value: "bottom-left", text: "Bottom-Left" }),
      window.FOSS.dom.el("option", { value: "bottom-right", text: "Bottom-Right" }),
      window.FOSS.dom.el("option", { value: "top_center", text: "Top Center (header)" }),
      window.FOSS.dom.el("option", { value: "top_left", text: "Top Left (header)" }),
      window.FOSS.dom.el("option", { value: "top_right", text: "Top Right (header)" }),
      window.FOSS.dom.el("option", { value: "top-left", text: "Top-Left" }),
      window.FOSS.dom.el("option", { value: "top-right", text: "Top-Right" }),
      window.FOSS.dom.el("option", { value: "center", text: "Center" })
    ]);

    var addNumberBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-add-numbers-btn",
      "aria-label": "Stamp Page Numbers",
      title: "Stamp Page Numbers",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Numbered PDF", default_name: "numbered.pdf", file_types: ["pdf"] }).then(function (res) {
          var outPath = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          if (!outPath) return;
          clearError();
          statusBar.textContent = "Stamping page numbers...";
          ctx.api("pdf_add_page_numbers", {
            file_path: currentFile,
            output_path: outPath,
            format: numFormatSelect.value,
            position: numPosSelect.value
          }).then(function (nres) {
            if (nres && nres.ok && nres.output_path) {
              statusBar.textContent = "Page numbers stamped.";
              showResult(nres.output_path, "Page Numbers Stamped");
            } else {
              showError((nres && nres.error) || "Failed to stamp page numbers.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("hash", 16),
      window.FOSS.dom.el("span", { text: "Stamp Numbers" })
    ]);

    var orgCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var hint = window.FOSS.dom.el("p", { className: "text-sm text-muted", text: "Current pages (drag to reorder or use controls below):" });

    var selectAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "pdf-select-all-pages-btn",
      type: "button",
      onClick: function () {
        pageOrder.forEach(function (p) { selectedPages.add(p); });
        statusBar.textContent = "Selected all " + pageOrder.length + " pages.";
        renderPageGrid();
      }
    }, [window.FOSS.dom.el("span", { text: "Select All" })]);

    var deselectAllBtn = window.FOSS.dom.el("button", {
      className: "btn btn-ghost btn-sm",
      "data-testid": "pdf-deselect-all-pages-btn",
      type: "button",
      onClick: function () {
        selectedPages.clear();
        selectedPages.add(currentPage);
        statusBar.textContent = "Cleared selection.";
        renderPageGrid();
      }
    }, [window.FOSS.dom.el("span", { text: "Clear Selection" })]);

    var selectionBar = window.FOSS.dom.el("div", {
      className: "row items-center justify-between",
      style: { width: "100%", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "var(--space-2)" }
    }, [
      hint,
      window.FOSS.dom.el("div", { className: "row gap-xs items-center", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" } }, [
        selectAllBtn,
        deselectAllBtn
      ])
    ]);

    var saveOrderBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "pdf-save-order-btn",
      type: "button",
      onClick: function () {
        if (!currentFile || pageOrder.length === 0) {
          showError("Open a PDF file first.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Reordered PDF", default_name: "reordered.pdf", file_types: ["pdf"] }).then(function (res) {
          var outPath = (res && res.path) || (res && res.paths && res.paths[0]) || "";
          if (!outPath) return;
          clearError();
          statusBar.textContent = "Saving reordered PDF...";
          var ops = pageOrder.map(function (origIdx) {
            return {
              source_page: origIdx + 1,
              rotation: (pageRotations[origIdx] || 0) % 360
            };
          });
          ctx.api("pdf_reorder_pages", { file_path: currentFile, output_path: outPath, order: ops }).then(function (rres) {
            if (rres && rres.ok && rres.output_path) {
              statusBar.textContent = "Saved reordered PDF to " + rres.output_path;
              showResult(rres.output_path, "PDF Pages Reordered");
            } else {
              showError((rres && rres.error) || "Failed to reorder PDF pages.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("save", 16),
      window.FOSS.dom.el("span", { text: "Save Reordered PDF" })
    ]);

    var navBar = window.FOSS.dom.el("div", {
      className: "row items-center justify-between",
      style: { display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "var(--space-2)" }
    }, [
      window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" } }, [prevBtn, pageIndicator, nextBtn]),
      window.FOSS.dom.el("div", { className: "row items-center", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-2)" } }, [rotCwBtn, rotCcwBtn, deleteBtn, dupBtn, saveOrderBtn])
    ]);

    var stampBar = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%", borderTop: "1px solid var(--border)", paddingTop: "var(--space-3)" }
    }, [
      window.FOSS.components.field("Page Number Format", numFormatSelect),
      window.FOSS.components.field("Position", numPosSelect),
      addNumberBtn
    ]);

    orgCard.appendChild(filePicker.el);
    orgCard.appendChild(selectionBar);
    orgCard.appendChild(reorderGrid);
    orgCard.appendChild(navBar);
    orgCard.appendChild(previewImg);
    orgCard.appendChild(stampBar);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(orgCard);
  }

  // TAB 3: Split & Extract
  function renderSplit(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "Split & Extract Pages" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Divide documents into page ranges or extract single pages." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "pdf-split-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "pdf-split-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-split-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "pdf-split-result-card", title: titleText || "Split Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var rangeInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      "data-testid": "pdf-split-ranges",
      placeholder: "e.g. 1-3,5,7-9",
      "aria-label": "page ranges",
      title: "page ranges",
      style: { minHeight: "36px", minWidth: "180px" }
    });

    var filePicker = window.FOSS.components.filePicker({
      testid: "pdf-split-picker",
      title: "Select PDF to Split",
      fileTypes: ["pdf"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
      }
    });

    var splitBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-split-btn",
      "aria-label": "Split PDF",
      title: "Split PDF",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        ctx.api("select_save_path", { title: "Select Destination Directory", default_name: "split_output" }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Splitting PDF...";
          ctx.api("pdf_split", {
            file_path: currentFile,
            output_dir: res.path,
            ranges: rangeInput.value.trim() || undefined
          }).then(function (sres) {
            if (sres && sres.ok && sres.output_dir) {
              statusBar.textContent = "PDF split successfully.";
              showResult(sres.output_dir, "Split Finished");
            } else {
              showError((sres && sres.error) || "Split failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("scissors", 18),
      window.FOSS.dom.el("span", { text: "Split PDF" })
    ]);

    var singlePageInput = window.FOSS.dom.el("input", {
      className: "input",
      type: "number",
      min: "1",
      value: "1",
      "data-testid": "pdf-single-page-num",
      "aria-label": "page number",
      title: "page number",
      style: { width: "80px", minHeight: "36px" }
    });

    var extractSingleBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "pdf-extract-single-btn",
      "aria-label": "Extract Single Page",
      title: "Extract Single Page",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        var pnum = parseInt(singlePageInput.value, 10) - 1;
        ctx.api("select_save_path", { title: "Save Extracted Page", default_name: "page_" + (pnum + 1) + ".pdf", file_types: ["pdf"] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          ctx.api("pdf_extract_single_page", { file_path: currentFile, page_number: pnum, output_path: res.path }).then(function (eres) {
            if (eres && eres.ok && eres.output_path) {
              statusBar.textContent = "Extracted page " + (pnum + 1) + " successfully.";
              showResult(eres.output_path, "Page Extracted");
            } else {
              showError((eres && eres.error) || "Extraction failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 16),
      window.FOSS.dom.el("span", { text: "Extract Single Page" })
    ]);

    var splitCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });
    var splitRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" }
    }, [
      window.FOSS.components.field("page ranges", rangeInput),
      splitBtn
    ]);

    var extractRow = window.FOSS.dom.el("div", {
      className: "row items-end",
      style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%", borderTop: "1px solid var(--border)", paddingTop: "var(--space-3)" }
    }, [
      window.FOSS.components.field("single page", singlePageInput),
      extractSingleBtn
    ]);

    splitCard.appendChild(filePicker.el);
    splitCard.appendChild(splitRow);
    splitCard.appendChild(extractRow);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(splitCard);
  }

  // TAB 4: Security (Protect & Unlock)
  function renderSecurity(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "PDF Security & Permissions" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Encrypt with passwords, restrict printing, or remove password protection." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "pdf-security-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "pdf-security-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-security-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "pdf-security-result-card", title: titleText || "Security Applied", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "pdf-security-picker",
      title: "Select PDF Document",
      fileTypes: ["pdf"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
      }
    });

    // Protect Section
    var protectPw = window.FOSS.dom.el("input", {
      className: "input",
      type: "password",
      "data-testid": "pdf-protect-password",
      placeholder: "password required to open the pdf",
      "aria-label": "open password",
      title: "open password",
      style: { minHeight: "36px", minWidth: "220px" }
    });

    var repeatPw = window.FOSS.dom.el("input", {
      className: "input",
      type: "password",
      "data-testid": "pdf-repeat-password",
      placeholder: "repeat password",
      "aria-label": "repeat password",
      title: "repeat password",
      style: { minHeight: "36px", minWidth: "180px" }
    });

    var ownerPw = window.FOSS.dom.el("input", {
      className: "input",
      type: "password",
      "data-testid": "pdf-owner-password",
      placeholder: "optional owner/master password",
      "aria-label": "owner password",
      title: "owner password",
      style: { minHeight: "36px", minWidth: "220px" }
    });

    var printCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "pdf-allow-printing",
      "aria-label": "Allow Printing",
      title: "Allow Printing",
      checked: true
    });
    var printLabel = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--text-sm)", cursor: "pointer" }
    }, [
      printCheck,
      window.FOSS.dom.el("span", { text: "Allow Printing" })
    ]);

    var protectBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-protect-btn",
      "aria-label": "Protect PDF",
      title: "Protect PDF",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        var p1 = protectPw.value;
        var p2 = repeatPw.value;
        if (!p1) {
          showError("Password required to open the PDF cannot be empty.");
          return;
        }
        if (p1 !== p2) {
          showError("Passwords do not match.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Protected PDF", default_name: "protected.pdf", file_types: ["pdf"] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Encrypting PDF...";
          ctx.api("pdf_protect", { file_path: currentFile, output_path: res.path, password: p1 }).then(function (pres) {
            if (pres && pres.ok && pres.output_path) {
              statusBar.textContent = "PDF protected and saved.";
              showResult(pres.output_path, "PDF Encrypted");
            } else {
              showError((pres && pres.error) || "Protection failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("lock", 18),
      window.FOSS.dom.el("span", { text: "Protect PDF" })
    ]);

    // Unlock Section
    var unlockPw = window.FOSS.dom.el("input", {
      className: "input",
      type: "password",
      "data-testid": "pdf-unlock-password",
      placeholder: "enter the password to remove protection and save a clean pdf",
      "aria-label": "unlock password",
      title: "unlock password",
      style: { minHeight: "36px", minWidth: "260px" }
    });

    var unlockBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "pdf-unlock-btn",
      "aria-label": "Unlock PDF",
      title: "Unlock PDF",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        if (!unlockPw.value) {
          showError("Enter password to unlock.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Clean PDF", default_name: "unlocked.pdf", file_types: ["pdf"] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Unlocking PDF...";
          ctx.api("pdf_unlock", { file_path: currentFile, output_path: res.path, password: unlockPw.value }).then(function (ures) {
            if (ures && ures.ok && ures.output_path) {
              statusBar.textContent = "PDF unlocked successfully.";
              showResult(ures.output_path, "PDF Unlocked");
            } else {
              showError((ures && ures.error) || "Failed to unlock PDF.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("unlock", 18),
      window.FOSS.dom.el("span", { text: "Unlock PDF" })
    ]);

    var secCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });

    var protectGroup = window.FOSS.dom.el("div", { className: "card flex-col gap-2", style: { border: "1px solid var(--border)", padding: "var(--space-3)" } }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Encrypt Document" }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("password", protectPw),
        window.FOSS.components.field("repeat", repeatPw),
        window.FOSS.components.field("owner password", ownerPw),
        printLabel,
        protectBtn
      ])
    ]);

    var unlockGroup = window.FOSS.dom.el("div", { className: "card flex-col gap-2", style: { border: "1px solid var(--border)", padding: "var(--space-3)" } }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Remove Protection" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "enter the password to remove protection and save a clean pdf" }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("password", unlockPw),
        unlockBtn
      ])
    ]);

    secCard.appendChild(filePicker.el);
    secCard.appendChild(protectGroup);
    secCard.appendChild(unlockGroup);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(secCard);
  }

  // TAB 5: Tools & Watermark
  function renderTools(panel, ctx) {
    panel.innerHTML = "";
    var currentFile = "";

    var header = window.FOSS.dom.el("div", { className: "card-header" }, [
      window.FOSS.dom.el("h2", { className: "card-title", text: "PDF Compression, Watermark & Text Extraction" }),
      window.FOSS.dom.el("p", { className: "text-muted text-sm", text: "Compress documents, stamp diagonal text watermarks, or extract plain text and markdown." })
    ]);

    var statusBar = window.FOSS.dom.el("div", { className: "text-xs text-muted", "data-testid": "pdf-tools-status", text: "Ready" });

    var errorBanner = window.FOSS.dom.el("div", { className: "banner danger", "data-testid": "pdf-tools-error", hidden: true }, [
      window.FOSS.icons.el("alert", 18),
      window.FOSS.dom.el("span", { className: "banner-msg", text: "" })
    ]);

    function showError(msg) {
      var s = errorBanner.querySelector(".banner-msg");
      if (s) s.textContent = msg;
      errorBanner.removeAttribute("hidden");
      statusBar.textContent = "Error: " + msg;
    }
    function clearError() {
      errorBanner.setAttribute("hidden", "true");
    }

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-tools-result", hidden: true });
    function showResult(path, titleText) {
      resultHost.innerHTML = "";
      var card = window.FOSS.components.resultCard({ testid: "pdf-tools-result-card", title: titleText || "Tool Operation Complete", outputPath: path });
      resultHost.appendChild(card);
      resultHost.removeAttribute("hidden");
    }

    var filePicker = window.FOSS.components.filePicker({
      testid: "pdf-tools-picker",
      title: "Select PDF Document",
      fileTypes: ["pdf"],
      onSelect: function (val) {
        currentFile = val;
        clearError();
        statusBar.textContent = "Selected: " + val.split(/[/\\]/).pop();
      },
      onClear: function () {
        currentFile = "";
      }
    });

    // Subtabs: easy and advanced
    var activeSubTab = "easy";
    var subTabsNav = window.FOSS.components.segmented({
      items: [
        { id: "easy", label: "easy" },
        { id: "advanced", label: "advanced" }
      ],
      value: "easy",
      onChange: function (val) {
        activeSubTab = val;
        statusBar.textContent = "Switched to " + val + " mode.";
      }
    });

    // 1. Compression
    var compLevelSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-compress-level",
      "aria-label": "choose a compression level",
      title: "choose a compression level",
      style: { minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "screen", text: "screen" }),
      window.FOSS.dom.el("option", { value: "ebook", text: "ebook" }),
      window.FOSS.dom.el("option", { value: "printer", text: "printer" }),
      window.FOSS.dom.el("option", { value: "prepress", text: "prepress" })
    ]);

    var compressBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-compress-btn",
      "aria-label": "Compress PDF",
      title: "Compress PDF",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Compressed PDF", default_name: "compressed.pdf", file_types: ["pdf"] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Compressing PDF...";
          ctx.api("pdf_compress", { file_path: currentFile, output_path: res.path, level: compLevelSelect.value }).then(function (cres) {
            if (cres && cres.ok && cres.output_path) {
              statusBar.textContent = "PDF compressed successfully.";
              showResult(cres.output_path, "PDF Compressed");
            } else {
              showError((cres && cres.error) || "Compression failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("minimize-2", 18),
      window.FOSS.dom.el("span", { text: "Compress PDF" })
    ]);

    // 2. Watermark
    var watermarkText = window.FOSS.dom.el("input", {
      className: "input",
      type: "text",
      value: "CONFIDENTIAL",
      "data-testid": "pdf-watermark-text",
      placeholder: "stamp a transparent diagonal text watermark on each page.",
      "aria-label": "watermark text",
      title: "watermark text",
      style: { minHeight: "36px", minWidth: "160px" }
    });

    var watermarkPreset = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-watermark-preset",
      "aria-label": "preset",
      title: "preset",
      style: { minWidth: "140px" },
      onChange: function (e) {
        if (e.target.value === "red") watermarkText.value = "CONFIDENTIAL";
        else if (e.target.value === "blue") watermarkText.value = "FOR REVIEW";
        else if (e.target.value === "green") watermarkText.value = "APPROVED";
        else if (e.target.value === "gray") watermarkText.value = "DRAFT";
      }
    }, [
      window.FOSS.dom.el("option", { value: "red", text: "red (confidential)" }),
      window.FOSS.dom.el("option", { value: "blue", text: "blue (for review)" }),
      window.FOSS.dom.el("option", { value: "green", text: "green (approved)" }),
      window.FOSS.dom.el("option", { value: "gray", text: "dark gray (draft)" })
    ]);

    var watermarkBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-watermark-btn",
      "aria-label": "Apply Watermark",
      title: "Apply Watermark",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        var txt = watermarkText.value.trim();
        if (!txt) {
          showError("Watermark text cannot be empty.");
          return;
        }
        ctx.api("select_save_path", { title: "Save Watermarked PDF", default_name: "watermarked.pdf", file_types: ["pdf"] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Applying watermark...";
          ctx.api("pdf_watermark", { file_path: currentFile, output_path: res.path, text: txt }).then(function (wres) {
            if (wres && wres.ok && wres.output_path) {
              statusBar.textContent = "Watermark applied.";
              showResult(wres.output_path, "Watermark Stamped");
            } else {
              showError((wres && wres.error) || "Watermark failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("droplet", 18),
      window.FOSS.dom.el("span", { text: "Apply Watermark" })
    ]);

    // 3. Text Extraction
    var extractFmtSelect = window.FOSS.dom.el("select", {
      className: "input",
      "data-testid": "pdf-extract-format",
      "aria-label": "format",
      title: "format",
      style: { minWidth: "140px" }
    }, [
      window.FOSS.dom.el("option", { value: "txt", text: "plain text (.txt)" }),
      window.FOSS.dom.el("option", { value: "md", text: "markdown (.md)" })
    ]);

    var ocrCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "pdf-use-ocr",
      style: { cursor: "pointer" }
    });

    var ocrLabel = window.FOSS.dom.el("label", {
      className: "row items-center",
      style: { display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--text-sm)", cursor: "pointer" }
    }, [
      ocrCheck,
      window.FOSS.dom.el("span", { text: "Use OCR recognition (recommended for scanned PDFs)" })
    ]);

    var extractTextBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "pdf-extract-text-btn",
      "aria-label": "Extract Text",
      title: "Extract Text",
      type: "button",
      onClick: function () {
        if (!currentFile) {
          showError("Select a PDF file first.");
          return;
        }
        var ext = extractFmtSelect.value === "md" ? ".md" : ".txt";
        ctx.api("select_save_path", { title: "Save Extracted Text", default_name: "extracted_text" + ext, file_types: [ext.slice(1)] }).then(function (res) {
          if (!res || !res.path) return;
          clearError();
          statusBar.textContent = "Extracting text from PDF...";
          ctx.api("pdf_extract_text", { file_path: currentFile, output_path: res.path }).then(function (tres) {
            if (tres && tres.ok && tres.output_path) {
              statusBar.textContent = "Text extracted (" + tres.page_count + " pages).";
              showResult(tres.output_path, "Text Extracted");
            } else {
              showError((tres && tres.error) || "Text extraction failed.");
            }
          });
        });
      }
    }, [
      window.FOSS.icons.el("file-text", 18),
      window.FOSS.dom.el("span", { text: "Extract Text" })
    ]);

    var batchBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-start-batch-btn",
      type: "button",
      onClick: function () {
        statusBar.textContent = "Batch processing queued.";
      }
    }, [
      window.FOSS.icons.el("layers", 16),
      window.FOSS.dom.el("span", { text: "start batch" })
    ]);

    var toolsCard = window.FOSS.dom.el("div", { className: "card flex-col gap-3", style: { width: "100%", maxWidth: "100%", minWidth: "0" } });

    var compGroup = window.FOSS.dom.el("div", { className: "card flex-col gap-2", style: { border: "1px solid var(--border)", padding: "var(--space-3)" } }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Compress Document" }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("choose a compression level", compLevelSelect),
        compressBtn
      ])
    ]);

    var wmGroup = window.FOSS.dom.el("div", { className: "card flex-col gap-2", style: { border: "1px solid var(--border)", padding: "var(--space-3)" } }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Text Watermark" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "stamp a transparent diagonal text watermark on each page." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("watermark text", watermarkText),
        window.FOSS.components.field("preset", watermarkPreset),
        watermarkBtn
      ])
    ]);

    var txtGroup = window.FOSS.dom.el("div", { className: "card flex-col gap-2", style: { border: "1px solid var(--border)", padding: "var(--space-3)" } }, [
      window.FOSS.dom.el("h3", { className: "card-title text-base", text: "Extract Text" }),
      window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "extract text from pdf pages into a local file (plain text or markdown)." }),
      window.FOSS.dom.el("div", { className: "row items-end", style: { display: "flex", flexWrap: "wrap", gap: "var(--space-3)", width: "100%" } }, [
        window.FOSS.components.field("format", extractFmtSelect),
        ocrLabel,
        extractTextBtn,
        batchBtn
      ])
    ]);

    toolsCard.appendChild(subTabsNav);
    toolsCard.appendChild(filePicker.el);
    toolsCard.appendChild(compGroup);
    toolsCard.appendChild(wmGroup);
    toolsCard.appendChild(txtGroup);

    panel.appendChild(header);
    panel.appendChild(statusBar);
    panel.appendChild(errorBanner);
    panel.appendChild(resultHost);
    panel.appendChild(toolsCard);
  }

  // Register PDF Tool
  window.FOSS.router.register({
    id: "pdf",
    title: "PDF Tools",
    navName: "PDF",
    category: "Documents",
    icon: "file-text",
    tabs: [
      { id: "merge", label: "Merge", render: renderMerge },
      { id: "organize", label: "Organize", render: renderOrganize },
      { id: "split", label: "Split", render: renderSplit },
      { id: "security", label: "Security", render: renderSecurity },
      { id: "tools", label: "Tools", render: renderTools }
    ],
    onFiles: function (paths) {
      if (!paths || paths.length === 0) return;
      if (paths.length > 1 || window.FOSS.router.getActiveTab() === "merge") {
        window.FOSS.router.open("pdf", "merge");
        if (window.FOSS._pdfAddMergeFiles) {
          window.FOSS._pdfAddMergeFiles(paths);
        }
      } else {
        window.FOSS.router.open("pdf", "organize");
        if (window.FOSS._pdfOpenDoc) {
          window.FOSS._pdfOpenDoc(paths[0]);
        }
      }
    }
  });
})();
