// PDF Studio: Combine & Organize, Split, and Security with visual page workspace.
window.FOSS = window.FOSS || {};

(function () {
  var sources = {};
  var workspaceItems = [];
  var selectedPageIds = new Set();
  var undoStack = [];
  var idCounter = 1;
  var dragState = null;

  function pdfDefault(key, fallback) {
    return window.FOSS.toolDefaults.get("pdf", key, fallback);
  }

  function rotationStep() {
    return parseInt(pdfDefault("rotation_step", "90"), 10) || 90;
  }

  function stemOf(filePath) {
    var name = String(filePath || "").split(/[\\/]/).pop();
    return name.replace(/\.[^.]*$/, "");
  }

  function pushUndo() {
    undoStack.push(JSON.stringify(workspaceItems));
    if (undoStack.length > 25) {
      undoStack.shift();
    }
  }

  function performUndo(rerenderFn) {
    if (undoStack.length > 0) {
      var prev = undoStack.pop();
      workspaceItems = JSON.parse(prev);
      selectedPageIds.clear();
      rerenderFn();
    }
  }

  function getAllFlatPages() {
    var flat = [];
    workspaceItems.forEach(function (item) {
      if (item.kind === "group") {
        (item.pages || []).forEach(function (page) {
          flat.push(page);
        });
      } else if (item.kind === "page") {
        flat.push(item);
      }
    });
    return flat;
  }

  // TAB 1: Combine & Organize
  function renderCombineOrganize(panel, ctx) {
    panel.innerHTML = "";
    var currentCombinedPath = "";

    // Export Controls setup
    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-merge-result", hidden: true });

    var stampNumbersCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      "data-testid": "pdf-stamp-numbers-check",
      "aria-label": "Add Page Numbers",
      title: "Add Page Numbers",
      onchange: function () {
        numberConfigWrap.hidden = !stampNumbersCheck.checked;
      }
    });

    var defaultStampFormat = String(pdfDefault("stamp_format", "Page {n} of {total}"));
    var formatSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs",
      "data-testid": "pdf-stamp-format",
      "aria-label": "Page Number Format",
      title: "Page Number Format"
    }, [
      window.FOSS.dom.el("option", { value: "Page {n} of {total}", text: "Page {n} of {total}" }),
      window.FOSS.dom.el("option", { value: "{n} / {total}", text: "{n} / {total}" }),
      window.FOSS.dom.el("option", { value: "{n}", text: "{n}" })
    ]);
    formatSelect.value = defaultStampFormat;

    var defaultStampPosition = String(pdfDefault("stamp_position", "bottom_center"));
    var positionSelect = window.FOSS.dom.el("select", {
      className: "select select-sm text-xs",
      "data-testid": "pdf-stamp-position",
      "aria-label": "Page Number Position",
      title: "Page Number Position"
    }, [
      window.FOSS.dom.el("option", { value: "bottom_center", text: "Bottom Center" }),
      window.FOSS.dom.el("option", { value: "bottom_right", text: "Bottom Right" }),
      window.FOSS.dom.el("option", { value: "bottom_left", text: "Bottom Left" }),
      window.FOSS.dom.el("option", { value: "top_center", text: "Top Center" }),
      window.FOSS.dom.el("option", { value: "top_right", text: "Top Right" }),
      window.FOSS.dom.el("option", { value: "top_left", text: "Top Left" })
    ]);
    positionSelect.value = defaultStampPosition;

    var startNumInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input input-sm text-xs",
      value: "1",
      min: "1",
      style: "width: 4rem;",
      "aria-label": "Starting Page Number",
      title: "Starting Page Number"
    });

    var numberConfigWrap = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-1);", hidden: true }, [
      formatSelect,
      positionSelect,
      startNumInput
    ]);

    var exportGroupsBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      "data-testid": "pdf-export-groups-btn",
      title: "Export groups as separate PDFs",
      onclick: function () {
        exportGroups();
      }
    }, [
      window.FOSS.icons.el("archive", 14),
      window.FOSS.dom.el("span", { text: "Export Groups" })
    ]);

    var exportCombinedBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary btn-sm",
      "data-testid": "pdf-merge-btn",
      title: "Export Combined PDF",
      onclick: function () {
        exportCombined();
      }
    }, [
      window.FOSS.icons.el("check", 14),
      window.FOSS.dom.el("span", { text: "Export Combined" })
    ]);

    var exportCombinedBtnAlias = window.FOSS.dom.el("button", {
      className: "btn btn-success btn-sm",
      "data-testid": "pdf-merge-save-btn",
      title: "Export Combined PDF",
      style: "display: none;",
      onclick: function () {
        exportCombined();
      }
    });

    var exportPanelRight = window.FOSS.dom.el("div", {
      className: "row items-center",
      style: "gap: var(--space-2); margin-left: auto; flex-wrap: wrap;"
    }, [
      window.FOSS.dom.el("label", { className: "row items-center text-xs", style: "gap: var(--space-1); cursor: pointer;" }, [
        stampNumbersCheck,
        window.FOSS.dom.el("span", { text: "Page #s" })
      ]),
      numberConfigWrap,
      exportGroupsBtn,
      exportCombinedBtn,
      exportCombinedBtnAlias
    ]);

    var headerRow = window.FOSS.dom.el("div", { className: "row-between", style: "gap: var(--space-2); flex-wrap: wrap;" }, [
      window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2); flex-wrap: wrap;" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-primary btn-sm",
          "data-testid": "pdf-add-files-btn",
          onclick: function () {
            window.FOSS.api("select_files", { title: "Select PDF Documents", file_types: ["pdf"] })
              .then(function (res) {
                var pList = (res && (res.file_paths || res.paths)) || [];
                if (pList.length > 0) {
                  addSourcePdfs(pList);
                }
              })
              .catch(function () {});
          }
        }, [
          window.FOSS.icons.el("plus", 14),
          window.FOSS.dom.el("span", { text: "Add PDFs" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-select-all-btn",
          onclick: function () {
            getAllFlatPages().forEach(function (page) {
              selectedPageIds.add(page.id);
            });
            renderWorkspace();
          }
        }, [window.FOSS.dom.el("span", { text: "Select All" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-deselect-btn",
          onclick: function () {
            selectedPageIds.clear();
            renderWorkspace();
          }
        }, [window.FOSS.dom.el("span", { text: "Deselect" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-secondary btn-sm",
          "data-testid": "pdf-group-selected-btn",
          title: "Group selected pages together",
          onclick: function () {
            if (selectedPageIds.size === 0) {
              window.FOSS.dialogs.toast("Select one or more pages to group.");
              return;
            }
            window.FOSS.dialogs.prompt({
              title: "Name Document Group",
              message: "Enter a name for the new document group:",
              defaultValue: "Group " + (workspaceItems.filter(function(i){return i.kind === 'group'}).length + 1)
            }).then(function(groupName) {
              if (groupName === null) return;
              if (!groupName.trim()) groupName = "Group " + (workspaceItems.filter(function(i){return i.kind === 'group'}).length + 1);

              pushUndo();
              var extracted = [];
              var firstIndex = -1;
              workspaceItems.forEach(function (item, idx) {
                if (item.kind === "page" && selectedPageIds.has(item.id)) {
                  if (firstIndex === -1) firstIndex = idx;
                  extracted.push(item);
                } else if (item.kind === "group") {
                  var remaining = [];
                  (item.pages || []).forEach(function (page) {
                    if (selectedPageIds.has(page.id)) {
                      if (firstIndex === -1) firstIndex = idx;
                      extracted.push(page);
                    } else {
                      remaining.push(page);
                    }
                  });
                  item.pages = remaining;
                }
              });

              var newItems = [];
              workspaceItems.forEach(function (item) {
                if (item.kind === "page" && selectedPageIds.has(item.id)) {
                  return;
                }
                if (item.kind === "group" && (!item.pages || item.pages.length === 0)) {
                  return;
                }
                newItems.push(item);
              });

              var newGroup = {
                kind: "group",
                id: "grp_" + (idCounter++),
                name: groupName.trim(),
                collapsed: false,
                pages: extracted
              };
              var insertPos = firstIndex >= 0 ? Math.min(firstIndex, newItems.length) : newItems.length;
              newItems.splice(insertPos, 0, newGroup);
              workspaceItems = newItems;
              selectedPageIds.clear();
              renderWorkspace();
            });
          }
        }, [
          window.FOSS.icons.el("folder", 14),
          window.FOSS.dom.el("span", { text: "Group Selected" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-ungroup-btn",
          title: "Ungroup selected groups into individual pages",
          onclick: function () {
            pushUndo();
            var newItems = [];
            workspaceItems.forEach(function (item) {
              if (item.kind === "group") {
                var hasSelected = (item.pages || []).some(function (page) {
                  return selectedPageIds.has(page.id);
                });
                if (hasSelected || selectedPageIds.size === 0) {
                  (item.pages || []).forEach(function (page) {
                    newItems.push(page);
                  });
                  return;
                }
              }
              newItems.push(item);
            });
            workspaceItems = newItems;
            renderWorkspace();
          }
        }, [
          window.FOSS.icons.el("layers", 14),
          window.FOSS.dom.el("span", { text: "Ungroup" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-rotate-ccw-btn",
          title: "Rotate selected pages " + rotationStep() + " degrees CCW",
          onclick: function () {
            rotateSelected(-rotationStep());
          }
        }, [
          window.FOSS.icons.el("rotate-ccw", 14),
          window.FOSS.dom.el("span", { text: "Rotate CCW" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-rotate-cw-btn",
          title: "Rotate selected pages " + rotationStep() + " degrees CW",
          onclick: function () {
            rotateSelected(rotationStep());
          }
        }, [
          window.FOSS.icons.el("rotate-cw", 14),
          window.FOSS.dom.el("span", { text: "Rotate CW" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-duplicate-page-btn",
          title: "Duplicate selected pages",
          onclick: function () {
            if (selectedPageIds.size === 0) return;
            pushUndo();
            var withClones = [];
            workspaceItems.forEach(function (item) {
              if (item.kind === "group") {
                var updated = [];
                (item.pages || []).forEach(function (page) {
                  updated.push(page);
                  if (selectedPageIds.has(page.id)) {
                    updated.push(Object.assign({}, page, { id: "pg_" + (idCounter++) }));
                  }
                });
                item.pages = updated;
                withClones.push(item);
              } else {
                withClones.push(item);
                if (selectedPageIds.has(item.id)) {
                  withClones.push(Object.assign({}, item, { id: "pg_" + (idCounter++) }));
                }
              }
            });
            workspaceItems = withClones;
            renderWorkspace();
          }
        }, [
          window.FOSS.icons.el("copy", 14),
          window.FOSS.dom.el("span", { text: "Duplicate" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm text-danger",
          "data-testid": "pdf-delete-page-btn",
          title: "Delete selected pages",
          onclick: function () {
            if (selectedPageIds.size === 0) return;
            pushUndo();
            var newItems = [];
            workspaceItems.forEach(function (item) {
              if (item.kind === "page") {
                if (!selectedPageIds.has(item.id)) newItems.push(item);
              } else if (item.kind === "group") {
                var remaining = (item.pages || []).filter(function (page) {
                  return !selectedPageIds.has(page.id);
                });
                if (remaining.length > 0) {
                  item.pages = remaining;
                  newItems.push(item);
                }
              }
            });
            workspaceItems = newItems;
            selectedPageIds.clear();
            renderWorkspace();
          }
        }, [
          window.FOSS.icons.el("trash", 14),
          window.FOSS.dom.el("span", { text: "Delete" })
        ]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-undo-btn",
          title: "Undo last layout change",
          onclick: function () {
            performUndo(renderWorkspace);
          }
        }, [
          window.FOSS.icons.el("corner-up-left", 14),
          window.FOSS.dom.el("span", { text: "Undo" })
        ])
      ]),
      exportPanelRight
    ]);

    var workspaceArea = window.FOSS.dom.el("div", { className: "pdf-workspace", "data-testid": "pdf-workspace" });

    function handleAutoScroll(e, container) {
      var rect = container.getBoundingClientRect();
      var edgeZone = 80;
      var scrollSpeed = 20;
      if (e.clientY < rect.top + edgeZone) {
        container.scrollTop -= scrollSpeed;
        window.scrollBy(0, -scrollSpeed);
      } else if (e.clientY > rect.bottom - edgeZone || e.clientY > window.innerHeight - edgeZone) {
        container.scrollTop += scrollSpeed;
        window.scrollBy(0, scrollSpeed);
      }
    }

    window.addEventListener("dragover", function (e) {
      if (dragState && workspaceArea) {
        handleAutoScroll(e, workspaceArea);
      }
    });

    workspaceArea.ondragover = function (e) {
      if (dragState) {
        e.preventDefault();
        handleAutoScroll(e, workspaceArea);
      }
    };
    workspaceArea.ondrop = function (e) {
      e.preventDefault();
      if (!dragState) return;
      var data = dragState;
      dragState = null;
      if (data.type === "group") {
        var lastItem = workspaceItems[workspaceItems.length - 1];
        if (lastItem) moveTopLevelItem(data.id, lastItem.id, "after");
      } else if (data.type === "page") {
        pushUndo();
        var movedPage = removePageById(data.id);
        if (movedPage) {
          workspaceItems.push(movedPage);
          renderWorkspace();
        }
      }
    };

    function rotateSelected(degrees) {
      pushUndo();
      var targetPages = [];
      if (selectedPageIds.size > 0) {
        getAllFlatPages().forEach(function (page) {
          if (selectedPageIds.has(page.id)) targetPages.push(page);
        });
      } else {
        targetPages = getAllFlatPages();
      }
      targetPages.forEach(function (page) {
        page.rotation = ((page.rotation || 0) + degrees + 360) % 360;
      });
      renderWorkspace();
    }

    function rotateGroup(group, degrees) {
      pushUndo();
      (group.pages || []).forEach(function (page) {
        page.rotation = ((page.rotation || 0) + degrees + 360) % 360;
      });
      renderWorkspace();
    }

    function dropEdge(e, el, axis) {
      var rect = el.getBoundingClientRect();
      if (axis === "y") return e.clientY > rect.top + rect.height / 2 ? "after" : "before";
      return e.clientX > rect.left + rect.width / 2 ? "after" : "before";
    }

    function addSourcePdfs(paths) {
      var promises = paths.map(function (filePath) {
        var sourceId = "src_" + (idCounter++);
        var fileName = filePath.split(/[\\/]/).pop();
        var stem = fileName.replace(/\.pdf$/i, "");
        return Promise.all([
          window.FOSS.api("pdf_open_doc", { file_path: filePath }),
          window.FOSS.api("pdf_thumbnails", { file_path: filePath, max_dim: 240 })
        ]).then(function (results) {
          var openRes = results[0];
          var thumbRes = results[1];
          sources[sourceId] = {
            id: sourceId,
            path: filePath,
            name: fileName,
            pageCount: openRes.page_count
          };
          var pageItems = (thumbRes.thumbnails || []).map(function (t) {
            return {
              kind: "page",
              id: "pg_" + (idCounter++),
              sourceId: sourceId,
              sourceName: fileName,
              pageNum: t.page,
              rotation: 0,
              thumbUrl: t.data_url
            };
          });
          return {
            kind: "group",
            id: "grp_" + (idCounter++),
            name: stem,
            collapsed: pdfDefault("group_behavior", "expanded") === "collapsed",
            pages: pageItems
          };
        });
      });

      Promise.all(promises).then(function (groups) {
        pushUndo();
        workspaceItems = workspaceItems.concat(groups);
        renderWorkspace();
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Failed to load PDF: " + (err.message || err));
      });
    }

    window.FOSS._pdfAddSources = function (paths) {
      if (paths && paths.length > 0) addSourcePdfs(paths);
    };
    window.FOSS._pdfAddMergeFiles = function (paths) {
      if (paths && paths.length > 0) addSourcePdfs(paths);
    };

    function renderWorkspace() {
      workspaceArea.innerHTML = "";
      if (workspaceItems.length === 0) {
        var empty = window.FOSS.dom.el("div", {
          className: "dropzone",
          style: "min-height: 20rem; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-3);",
          onclick: function () {
            window.FOSS.api("select_files", { title: "Select PDF Documents", file_types: ["pdf"] })
              .then(function (res) {
                if (res && res.file_paths && res.file_paths.length > 0) addSourcePdfs(res.file_paths);
              });
          }
        }, [
          window.FOSS.icons.el("file-text", 40),
          window.FOSS.dom.el("p", { className: "text-base font-semibold", text: "No PDF files loaded" }),
          window.FOSS.dom.el("p", { className: "text-xs text-muted", text: "Click 'Add PDFs' or drop PDF files here to combine and organize." })
        ]);
        workspaceArea.appendChild(empty);
        return;
      }

      var globalPageIndex = 1;
      workspaceItems.forEach(function (item, groupIndex) {
        if (item.kind === "group") {
          var groupCard = renderGroupCard(item, groupIndex, function () { return globalPageIndex++; });
          workspaceArea.appendChild(groupCard);
        } else if (item.kind === "page") {
          var pageCard = renderPageCard(item, globalPageIndex++, null);
          workspaceArea.appendChild(pageCard);
        }
      });
    }

    function renderGroupCard(group, groupIndex, getGlobalPageNum) {
      var card = window.FOSS.dom.el("div", {
        className: "pdf-group-card" + (group.collapsed ? " collapsed" : ""),
        "data-testid": "pdf-group-" + groupIndex
      });

      function clearGroupMarks() {
        card.classList.remove("pdf-drop-into", "pdf-drop-before", "pdf-drop-after");
      }

      card.ondragstart = function (e) {
        if (card.getAttribute("draggable") !== "true") return;
        dragState = { type: "group", id: group.id };
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("application/json", JSON.stringify(dragState));
      };
      card.ondragend = function () {
        card.setAttribute("draggable", "false");
        dragState = null;
      };
      card.ondragover = function (e) {
        e.preventDefault();
        clearGroupMarks();
        if (dragState && dragState.type === "group") {
          card.classList.add(dropEdge(e, card, "y") === "after" ? "pdf-drop-after" : "pdf-drop-before");
        } else {
          card.classList.add("pdf-drop-into");
        }
      };
      card.ondragleave = clearGroupMarks;
      card.ondrop = function (e) {
        e.preventDefault();
        var edge = dropEdge(e, card, "y");
        clearGroupMarks();
        try {
          var data = JSON.parse(e.dataTransfer.getData("application/json"));
          handleDropOntoGroup(data, group, edge);
        } catch (err) {}
      };

      var header = window.FOSS.dom.el("div", { className: "pdf-group-header" });
      var titleWrap = window.FOSS.dom.el("div", { className: "pdf-group-title-wrap" });

      var grip = window.FOSS.dom.el("span", {
        className: "pdf-group-grip",
        title: "Drag to reorder group",
        "aria-label": "Drag to reorder group",
        onmousedown: function () {
          card.setAttribute("draggable", "true");
        },
        onmouseup: function () {
          card.setAttribute("draggable", "false");
        }
      }, [window.FOSS.icons.el("grip", 16)]);

      var collapseBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-icon",
        "aria-label": group.collapsed ? "Expand group" : "Collapse group",
        title: group.collapsed ? "Expand group" : "Collapse group",
        onclick: function () {
          group.collapsed = !group.collapsed;
          renderWorkspace();
        }
      }, [
        window.FOSS.icons.el(group.collapsed ? "chevron-right" : "chevron-down", 14)
      ]);

      var checkAll = window.FOSS.dom.el("input", {
        type: "checkbox",
        "aria-label": "Select all in group",
        title: "Select all in group",
        onchange: function () {
          (group.pages || []).forEach(function (page) {
            if (checkAll.checked) selectedPageIds.add(page.id);
            else selectedPageIds.delete(page.id);
          });
          renderWorkspace();
        }
      });
      var allChecked = (group.pages || []).length > 0 && (group.pages || []).every(function (page) {
        return selectedPageIds.has(page.id);
      });
      checkAll.checked = allChecked;

      var nameInput = window.FOSS.dom.el("input", {
        className: "pdf-group-name-input",
        "aria-label": "Group name",
        title: "Group name",
        "data-testid": "pdf-group-name-" + groupIndex,
        value: group.name || ("Group " + (groupIndex + 1)),
        onchange: function () {
          group.name = nameInput.value.trim() || ("Group " + (groupIndex + 1));
        }
      });

      var countBadge = window.FOSS.dom.el("span", {
        className: "badge badge-neutral text-xs",
        text: (group.pages || []).length + " pages"
      });

      titleWrap.appendChild(grip);
      titleWrap.appendChild(collapseBtn);
      titleWrap.appendChild(checkAll);
      titleWrap.appendChild(nameInput);
      titleWrap.appendChild(countBadge);

      var actionsWrap = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm btn-icon",
          "data-testid": "pdf-group-rot-ccw-" + groupIndex,
          "aria-label": "Rotate group counter-clockwise",
          title: "Rotate all pages in group " + rotationStep() + " degrees CCW",
          onclick: function () {
            rotateGroup(group, -rotationStep());
          }
        }, [window.FOSS.icons.el("rotate-ccw", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm btn-icon",
          "data-testid": "pdf-group-rot-cw-" + groupIndex,
          "aria-label": "Rotate group clockwise",
          title: "Rotate all pages in group " + rotationStep() + " degrees CW",
          onclick: function () {
            rotateGroup(group, rotationStep());
          }
        }, [window.FOSS.icons.el("rotate-cw", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "data-testid": "pdf-group-ungroup-" + groupIndex,
          title: "Ungroup into Pages",
          onclick: function () {
            pushUndo();
            var newItems = [];
            workspaceItems.forEach(function (it) {
              if (it.id === group.id) {
                (it.pages || []).forEach(function (p) { newItems.push(p); });
              } else {
                newItems.push(it);
              }
            });
            workspaceItems = newItems;
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("layers", 12), window.FOSS.dom.el("span", { text: "Ungroup into Pages" })]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm text-danger",
          "data-testid": "pdf-group-del-" + groupIndex,
          title: "Delete group",
          onclick: function () {
            pushUndo();
            workspaceItems = workspaceItems.filter(function (it) { return it.id !== group.id; });
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("trash", 12)])
      ]);

      header.appendChild(titleWrap);
      header.appendChild(actionsWrap);
      card.appendChild(header);

      if (!group.collapsed) {
        var grid = window.FOSS.dom.el("div", { className: "pdf-thumbnails-grid" });
        (group.pages || []).forEach(function (page, pageIdx) {
          var pCard = renderPageCard(page, getGlobalPageNum(), group, pageIdx);
          grid.appendChild(pCard);
        });
        card.appendChild(grid);
      }

      return card;
    }

    function openPageViewer(page, globalIdx, parentGroup, indexInGroup) {
      var h = document.getElementById("modal-host");
      if (!h) return;

      var scrim = window.FOSS.dom.el("div", { className: "scrim", "data-overlay": "true" });
      var titleEl = window.FOSS.dom.el("h3", { className: "card-title", text: "Page Viewer - " + page.sourceName + " p." + page.pageNum });

      var img = window.FOSS.dom.el("img", {
        className: "pdf-viewer-img",
        "data-testid": "pdf-viewer-img",
        alt: "Page " + page.pageNum,
        src: page.thumbUrl || ""
      });
      img.style.transform = "rotate(" + (page.rotation || 0) + "deg)";
      var sourceInfo = sources[page.sourceId];
      if (sourceInfo) {
        window.FOSS.api("pdf_render_page", {
          file_path: sourceInfo.path,
          page_number: page.pageNum - 1,
          dpi: parseInt(pdfDefault("output_dpi", 150), 10) || 150
        }).then(function (res) {
          if (res && res.data_url) img.src = res.data_url;
        }).catch(function () {});
      }

      var rotateBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary",
        "data-testid": "pdf-viewer-rotate-btn",
        onclick: function () {
          pushUndo();
          page.rotation = ((page.rotation || 0) + rotationStep() + 360) % 360;
          img.style.transform = "rotate(" + page.rotation + "deg)";
          renderWorkspace();
        }
      }, [window.FOSS.icons.el("rotate-cw", 14), window.FOSS.dom.el("span", { text: "Rotate " + rotationStep() + " deg" })]);

      var duplicateBtn = window.FOSS.dom.el("button", {
        className: "btn btn-secondary",
        "data-testid": "pdf-viewer-duplicate-btn",
        onclick: function () {
          pushUndo();
          var clone = Object.assign({}, page, { id: "pg_" + (idCounter++) });
          if (parentGroup) {
            parentGroup.pages.splice(indexInGroup + 1, 0, clone);
          } else {
            var idx = workspaceItems.indexOf(page);
            workspaceItems.splice(idx + 1, 0, clone);
          }
          renderWorkspace();
          window.FOSS.dialogs.toast("Page duplicated.");
        }
      }, [window.FOSS.icons.el("copy", 14), window.FOSS.dom.el("span", { text: "Duplicate Page" })]);

      var deleteBtn = window.FOSS.dom.el("button", {
        className: "btn btn-danger",
        "data-testid": "pdf-viewer-delete-btn",
        onclick: function () {
          pushUndo();
          selectedPageIds.delete(page.id);
          if (parentGroup) {
            parentGroup.pages = parentGroup.pages.filter(function (p) { return p.id !== page.id; });
          } else {
            workspaceItems = workspaceItems.filter(function (it) { return it.id !== page.id; });
          }
          renderWorkspace();
          cleanup();
          window.FOSS.dialogs.toast("Page deleted.");
        }
      }, [window.FOSS.icons.el("trash", 14), window.FOSS.dom.el("span", { text: "Delete Page" })]);

      var closeBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost",
        onclick: cleanup
      }, [window.FOSS.dom.el("span", { text: "Close" })]);

      var actionsEl = window.FOSS.dom.el("div", { className: "row end", style: "gap: var(--space-2); margin-top: var(--space-3);" }, [
        rotateBtn, duplicateBtn, deleteBtn, closeBtn
      ]);

      var contentEl = window.FOSS.dom.el("div", { className: "pdf-viewer-stage" }, [img]);

      var modalEl = window.FOSS.dom.el("div", {
        className: "modal pdf-viewer-modal",
        role: "dialog",
        "aria-modal": "true"
      }, [titleEl, contentEl, actionsEl]);

      function cleanup() {
        if (scrim.parentElement) scrim.parentElement.removeChild(scrim);
        if (modalEl.parentElement) modalEl.parentElement.removeChild(modalEl);
        h.classList.remove("active");
        document.removeEventListener("keydown", onKeyDown);
      }

      function onKeyDown(e) {
        if (e.key === "Escape") {
          cleanup();
        }
      }

      scrim.onclick = cleanup;
      document.addEventListener("keydown", onKeyDown);
      h.appendChild(scrim);
      h.appendChild(modalEl);
      h.classList.add("active");
    }

    function renderPageCard(page, globalIdx, parentGroup, indexInGroup) {
      var isSelected = selectedPageIds.has(page.id);
      var card = window.FOSS.dom.el("div", {
        className: "pdf-page-card" + (isSelected ? " selected" : ""),
        "data-testid": "pdf-page-card-" + (globalIdx - 1),
        draggable: "true"
      });

      function clearPageMarks() {
        card.classList.remove("pdf-drop-before", "pdf-drop-after");
      }

      card.ondragstart = function (e) {
        e.stopPropagation();
        dragState = { type: "page", id: page.id };
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("application/json", JSON.stringify(dragState));
      };
      card.ondragend = function () {
        dragState = null;
      };
      card.ondragover = function (e) {
        e.preventDefault();
        e.stopPropagation();
        clearPageMarks();
        card.classList.add(dropEdge(e, card, "x") === "after" ? "pdf-drop-after" : "pdf-drop-before");
      };
      card.ondragleave = clearPageMarks;
      card.ondrop = function (e) {
        e.preventDefault();
        e.stopPropagation();
        var edge = dropEdge(e, card, "x");
        clearPageMarks();
        try {
          var data = JSON.parse(e.dataTransfer.getData("application/json"));
          handleDropOntoPage(data, page, parentGroup, edge);
        } catch (err) {}
      };

      var header = window.FOSS.dom.el("div", { className: "pdf-page-header" });
      var grip = window.FOSS.icons.el("grip", 14);
      var check = window.FOSS.dom.el("input", {
        type: "checkbox",
        checked: isSelected,
        "aria-label": "Select page " + globalIdx,
        title: "Select page " + globalIdx,
        onchange: function (e) {
          e.stopPropagation();
          if (check.checked) selectedPageIds.add(page.id);
          else selectedPageIds.delete(page.id);
          card.classList.toggle("selected", check.checked);
        }
      });
      var pageNumBadge = window.FOSS.dom.el("span", {
        className: "badge badge-primary text-xs",
        text: "#" + globalIdx
      });
      header.appendChild(grip);
      header.appendChild(check);
      header.appendChild(pageNumBadge);

      var previewBox = window.FOSS.dom.el("div", {
        className: "pdf-page-preview-box",
        title: "Page preview",
        "data-truncate-ok": "true"
      });
      var img = window.FOSS.dom.el("img", {
        className: "pdf-page-preview",
        src: page.thumbUrl || "",
        alt: "Page " + page.pageNum
      });
      img.style.setProperty("transform", "rotate(" + (page.rotation || 0) + "deg)");
      previewBox.appendChild(img);

      var label = window.FOSS.dom.el("div", {
        className: "text-xs text-muted truncate text-center",
        style: "width: 100%; max-width: 8rem;",
        title: page.sourceName + " (p." + page.pageNum + ")",
        text: page.sourceName + " p." + page.pageNum + (page.rotation ? " (" + page.rotation + " deg)" : "")
      });

      var footer = window.FOSS.dom.el("div", { className: "pdf-page-footer" }, [
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-icon btn-sm",
          "data-testid": "pdf-card-ccw-" + (globalIdx - 1),
          "aria-label": "Rotate counter-clockwise",
          title: "Rotate " + rotationStep() + " deg counter-clockwise",
          onclick: function (e) {
            e.stopPropagation();
            pushUndo();
            page.rotation = ((page.rotation || 0) - rotationStep() + 360) % 360;
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("rotate-ccw", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-icon btn-sm",
          "data-testid": "pdf-page-rotate",
          "data-card-cw": String(globalIdx - 1),
          "aria-label": "Rotate clockwise",
          title: "Rotate " + rotationStep() + " deg clockwise",
          onclick: function (e) {
            e.stopPropagation();
            pushUndo();
            page.rotation = ((page.rotation || 0) + rotationStep() + 360) % 360;
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("rotate-cw", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-icon btn-sm",
          "data-testid": "pdf-page-duplicate",
          "data-card-dup": String(globalIdx - 1),
          "aria-label": "Duplicate page",
          title: "Duplicate page",
          onclick: function (e) {
            e.stopPropagation();
            pushUndo();
            var clone = Object.assign({}, page, { id: "pg_" + (idCounter++) });
            if (parentGroup) {
              parentGroup.pages.splice(indexInGroup + 1, 0, clone);
            } else {
              var idx = workspaceItems.indexOf(page);
              workspaceItems.splice(idx + 1, 0, clone);
            }
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("copy", 12)]),
        window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-icon btn-sm text-danger",
          "data-testid": "pdf-page-delete",
          "data-card-del": String(globalIdx - 1),
          "aria-label": "Delete page",
          title: "Delete page",
          onclick: function (e) {
            e.stopPropagation();
            pushUndo();
            selectedPageIds.delete(page.id);
            if (parentGroup) {
              parentGroup.pages = parentGroup.pages.filter(function (p) { return p.id !== page.id; });
            } else {
              workspaceItems = workspaceItems.filter(function (it) { return it.id !== page.id; });
            }
            renderWorkspace();
          }
        }, [window.FOSS.icons.el("trash", 12)])
      ]);

      card.appendChild(header);
      card.appendChild(previewBox);
      card.appendChild(label);
      card.appendChild(footer);

      card.onclick = function () {
        if (selectedPageIds.has(page.id)) selectedPageIds.delete(page.id);
        else selectedPageIds.add(page.id);
        renderWorkspace();
      };

      card.ondblclick = function (e) {
        e.stopPropagation();
        openPageViewer(page, globalIdx, parentGroup, indexInGroup);
      };

      return card;
    }

    function moveTopLevelItem(itemId, targetId, edge) {
      var fromIdx = workspaceItems.findIndex(function (it) { return it.id === itemId; });
      if (fromIdx < 0 || itemId === targetId) return;
      pushUndo();
      var moved = workspaceItems.splice(fromIdx, 1)[0];
      var toIdx = workspaceItems.findIndex(function (it) { return it.id === targetId; });
      if (toIdx < 0) {
        workspaceItems.push(moved);
      } else {
        workspaceItems.splice(edge === "after" ? toIdx + 1 : toIdx, 0, moved);
      }
      renderWorkspace();
    }

    function handleDropOntoGroup(data, targetGroup, edge) {
      if (data.type === "group") {
        moveTopLevelItem(data.id, targetGroup.id, edge);
      } else if (data.type === "page") {
        pushUndo();
        var movedPage = removePageById(data.id);
        if (movedPage) {
          targetGroup.pages.push(movedPage);
          renderWorkspace();
        }
      }
    }

    function handleDropOntoPage(data, targetPage, targetGroup, edge) {
      if (data.type === "group") {
        moveTopLevelItem(data.id, targetGroup ? targetGroup.id : targetPage.id, edge);
      } else if (data.type === "page" && data.id !== targetPage.id) {
        pushUndo();
        var movedPage = removePageById(data.id);
        if (movedPage) {
          var siblings = targetGroup ? targetGroup.pages : workspaceItems;
          var targetIdx = siblings.indexOf(targetPage);
          siblings.splice(edge === "after" ? targetIdx + 1 : targetIdx, 0, movedPage);
          renderWorkspace();
        }
      }
    }

    function removePageById(pageId) {
      var found = null;
      var newItems = [];
      workspaceItems.forEach(function (item) {
        if (item.kind === "page") {
          if (item.id === pageId) found = item;
          else newItems.push(item);
        } else if (item.kind === "group") {
          var remaining = [];
          (item.pages || []).forEach(function (p) {
            if (p.id === pageId) found = p;
            else remaining.push(p);
          });
          item.pages = remaining;
          if (remaining.length > 0) newItems.push(item);
        }
      });
      workspaceItems = newItems;
      return found;
    }


    function exportCombined() {
      var flat = getAllFlatPages();
      if (flat.length === 0) {
        window.FOSS.dialogs.toast("Please add at least one PDF page.");
        return;
      }
      var flatPages = flat.map(function (page) {
        return {
          source_path: (sources[page.sourceId] ? sources[page.sourceId].path : ""),
          page_number: page.pageNum,
          rotation: page.rotation || 0
        };
      });

      window.FOSS.api("select_save_path", {
        title: "Save Combined PDF",
        default_name: "combined",
        file_types: [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }]
      }).then(function (res) {
        var savePath = res && (res.path || res.file_path || res.output_path);
        if (!savePath) return;
        var pageNumbersConfig = stampNumbersCheck && stampNumbersCheck.checked ? {
          enabled: true,
          format: formatSelect.value,
          position: positionSelect.value,
          start_num: parseInt(startNumInput.value, 10) || 1
        } : null;

        return window.FOSS.api("pdf_merge_pages", {
          pages: flatPages,
          output_path: savePath,
          page_numbers: pageNumbersConfig
        }).then(function (assembleRes) {
          currentCombinedPath = (assembleRes && assembleRes.output_path) || savePath;
          resultHost.innerHTML = "";
          resultHost.removeAttribute("hidden");
          var card = window.FOSS.components.resultCard({
            testid: "pdf-merge-result-card",
            title: "Combined PDF Exported",
            outputPath: currentCombinedPath
          });
          resultHost.appendChild(card);
          window.FOSS.dialogs.toast("Combined PDF saved successfully.");
        });
      }).catch(function (err) {
        window.FOSS.dialogs.toast("Export failed: " + (err.message || err));
      });
    }

    function exportGroups() {
      var groups = [];
      workspaceItems.forEach(function (item) {
        if (item.kind === "group" && (item.pages || []).length > 0) {
          groups.push({
            name: item.name,
            pages: item.pages.map(function (page) {
              return {
                source_id: page.sourceId,
                page: page.pageNum,
                rotation: page.rotation || 0
              };
            })
          });
        }
      });

      if (groups.length === 0) {
        window.FOSS.dialogs.toast("No groups to export. Group pages first.");
        return;
      }

      var sourceMap = {};
      Object.keys(sources).forEach(function (sid) {
        sourceMap[sid] = sources[sid].path;
      });

      window.FOSS.api("select_folder", { title: "Select Export Folder" })
        .then(function (res) {
          if (!res || !res.folder_path) return;
          var pageNumbersConfig = stampNumbersCheck.checked ? {
            enabled: true,
            format: formatSelect.value,
            position: positionSelect.value,
            start_num: parseInt(startNumInput.value, 10) || 1
          } : null;

          return window.FOSS.api("pdf_export_groups", {
            sources: sourceMap,
            groups: groups,
            output_dir: res.folder_path,
            page_numbers: pageNumbersConfig
          }).then(function (expRes) {
            resultHost.innerHTML = "";
            resultHost.removeAttribute("hidden");
            var card = window.FOSS.components.resultCard({
              testid: "pdf-merge-result-card",
              title: "Exported " + (expRes.files || []).length + " PDF Groups",
              outputPath: res.folder_path
            });
            resultHost.appendChild(card);
            window.FOSS.dialogs.toast("Groups exported successfully.");
          });
        }).catch(function (err) {
          window.FOSS.dialogs.toast("Group export failed: " + (err.message || err));
        });
    }

    panel.appendChild(headerRow);
    panel.appendChild(workspaceArea);
    panel.appendChild(resultHost);

    renderWorkspace();
  }

  // TAB 2: Split PDF
  function renderSplit(panel, ctx) {
    panel.innerHTML = "";
    panel.classList.add("scroll-y");

    var currentPdf = "";
    var totalPages = 0;

    var picker = window.FOSS.components.filePicker({
      testid: "pdf-split-picker",
      title: "Select PDF Document",
      fileTypes: ["pdf"],
      onChange: function (filePath) {
        currentPdf = filePath;
        if (filePath) {
          window.FOSS.api("pdf_open_doc", { file_path: filePath })
            .then(function (res) {
              totalPages = res.page_count;
              statusMsg.textContent = "Loaded: " + totalPages + " pages.";
              loadThumbnails(filePath);
            }).catch(function (err) {
              statusMsg.textContent = "Failed to inspect PDF: " + (err.message || err);
            });
        }
      }
    });

    var statusMsg = window.FOSS.dom.el("div", { className: "text-xs text-muted", text: "Select a PDF to split." });
    var stripContainer = window.FOSS.dom.el("div", { className: "pdf-strip", hidden: true });

    function loadThumbnails(filePath) {
      window.FOSS.api("pdf_thumbnails", { file_path: filePath, max_dim: 120 })
        .then(function (res) {
          stripContainer.innerHTML = "";
          stripContainer.removeAttribute("hidden");
          (res.thumbnails || []).forEach(function (t) {
            var thumb = window.FOSS.dom.el("img", {
              className: "pdf-strip-thumb",
              src: t.data_url,
              title: "Page " + t.page,
              alt: "Page " + t.page
            });
            stripContainer.appendChild(thumb);
          });
        }).catch(function () {});
    }

    var modeSegmented = window.FOSS.components.segmented({
      testid: "pdf-split-mode",
      items: [
        { id: "ranges", label: "By Page Ranges / List" },
        { id: "every_n", label: "Every N Pages" }
      ],
      value: "ranges",
      onChange: function (val) {
        rangesField.hidden = (val !== "ranges");
        everyNField.hidden = (val !== "every_n");
      }
    });

    var rangesInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "data-testid": "pdf-split-range-input",
      "data-split-ranges": "true",
      placeholder: "e.g. 1, 2-5, 8-10 (type a single number like 3 for one page)"
    });
    var rangesField = window.FOSS.components.field({
      label: "Page Ranges",
      testid: "pdf-split-ranges-field",
      control: rangesInput
    });

    var everyNInput = window.FOSS.dom.el("input", {
      type: "number",
      className: "input",
      "data-testid": "pdf-split-every-n",
      value: "1",
      min: "1"
    });
    var everyNField = window.FOSS.components.field({
      label: "Pages Per File",
      testid: "pdf-split-every-n-field",
      control: everyNInput
    });
    everyNField.hidden = true;

    var outDirInput = window.FOSS.dom.el("input", {
      type: "text",
      className: "input",
      "aria-label": "Destination directory",
      title: "Destination directory",
      "data-testid": "pdf-split-out-dir",
      placeholder: "Destination directory (leave blank for source directory)"
    });
    var browseDirBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "pdf-split-browse-dir",
      onclick: function () {
        window.FOSS.api("select_folder", { title: "Select Destination Directory" })
          .then(function (res) {
            if (res && res.folder_path) outDirInput.value = res.folder_path;
          });
      }
    }, [window.FOSS.dom.el("span", { text: "Browse..." })]);

    var dirRow = window.FOSS.dom.el("div", { className: "row", style: "gap: var(--space-2);" }, [
      outDirInput,
      browseDirBtn
    ]);
    var dirField = window.FOSS.components.field({
      label: "Destination Folder",
      testid: "pdf-split-dir-field",
      control: dirRow
    });

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-split-result", hidden: true });

    var splitBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-split-btn",
      onclick: function () {
        if (!currentPdf) {
          window.FOSS.dialogs.toast("Select a PDF document first.");
          return;
        }
        var destDir = outDirInput.value.trim();
        if (!destDir) {
          var slashIdx = Math.max(currentPdf.lastIndexOf("/"), currentPdf.lastIndexOf("\\"));
          destDir = slashIdx >= 0 ? currentPdf.substring(0, slashIdx) : ".";
        }
        var mode = modeSegmented.getValue();
        var params = {
          file_path: currentPdf,
          output_dir: destDir
        };
        if (mode === "every_n") {
          params.every_n = parseInt(everyNInput.value, 10) || 1;
        } else {
          params.ranges = rangesInput.value.trim() || "all";
        }

        window.FOSS.api("pdf_split", params)
          .then(function (res) {
            resultHost.innerHTML = "";
            resultHost.removeAttribute("hidden");
            var card = window.FOSS.components.resultCard({
              testid: "pdf-split-result-card",
              title: "Split Complete (" + (res.files || []).length + " files created)",
              outputPath: destDir
            });
            resultHost.appendChild(card);
            window.FOSS.dialogs.toast("PDF split into " + (res.files || []).length + " files.");
          }).catch(function (err) {
            window.FOSS.dialogs.toast("Split failed: " + (err.message || err));
          });
      }
    }, [
      window.FOSS.icons.el("scissors", 14),
      window.FOSS.dom.el("span", { text: "Split PDF" })
    ]);

    panel.appendChild(picker.el);
    panel.appendChild(statusMsg);
    panel.appendChild(stripContainer);
    panel.appendChild(modeSegmented.el);
    panel.appendChild(rangesField);
    panel.appendChild(everyNField);
    panel.appendChild(dirField);
    panel.appendChild(window.FOSS.dom.el("div", { className: "row", style: "margin-top: var(--space-3);" }, [splitBtn]));
    panel.appendChild(resultHost);
  }

  // TAB 3: Protect & Unlock
  function renderSecurity(panel, ctx) {
    panel.innerHTML = "";
    panel.classList.add("scroll-y");

    var resultHost = window.FOSS.dom.el("div", { "data-testid": "pdf-security-result", hidden: true, style: "flex-shrink: 0;" });

    // Left card: Protect
    var protectFile = "";
    var protectPicker = window.FOSS.components.filePicker({
      testid: "pdf-security-picker",
      title: "Select PDF to Encrypt",
      fileTypes: ["pdf"],
      onChange: function (fp) { protectFile = fp; }
    });
    var protectPw = window.FOSS.dom.el("input", {
      type: "password",
      className: "input",
      "data-testid": "pdf-protect-password",
      placeholder: "Password"
    });
    var repeatPw = window.FOSS.dom.el("input", {
      type: "password",
      className: "input",
      "data-testid": "pdf-repeat-password",
      placeholder: "Repeat Password"
    });
    var allowPrintCheck = window.FOSS.dom.el("input", {
      type: "checkbox",
      checked: true,
      "aria-label": "Allow Printing",
      title: "Allow Printing"
    });

    var protectBtn = window.FOSS.dom.el("button", {
      className: "btn btn-primary",
      "data-testid": "pdf-protect-btn",
      onclick: function () {
        if (!protectFile) {
          window.FOSS.dialogs.toast("Select a PDF file first.");
          return;
        }
        if (!protectPw.value) {
          window.FOSS.dialogs.toast("Enter a password.");
          return;
        }
        if (protectPw.value !== repeatPw.value) {
          window.FOSS.dialogs.toast("Passwords do not match.");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Encrypted PDF",
          default_name: stemOf(protectFile) + "_protected",
          file_types: [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }]
        }).then(function (res) {
          if (!res || !res.file_path) return;
          return window.FOSS.api("pdf_protect", {
            file_path: protectFile,
            output_path: res.file_path,
            password: protectPw.value,
            allow_printing: allowPrintCheck.checked
          }).then(function (protRes) {
            resultHost.innerHTML = "";
            resultHost.removeAttribute("hidden");
            var card = window.FOSS.components.resultCard({
              testid: "pdf-security-result-card",
              title: "PDF Protected",
              outputPath: protRes.output_path || res.file_path
            });
            resultHost.appendChild(card);
            window.FOSS.dialogs.toast("PDF successfully encrypted.");
          });
        }).catch(function (err) {
          window.FOSS.dialogs.toast("Protect failed: " + (err.message || err));
        });
      }
    }, [
      window.FOSS.icons.el("lock", 14),
      window.FOSS.dom.el("span", { text: "Encrypt PDF" })
    ]);

    var protectCard = window.FOSS.dom.el("div", { className: "card", style: "display: flex; flex-direction: column; gap: var(--space-3);" }, [
      window.FOSS.dom.el("h3", { className: "card-title", text: "Encrypt PDF with Password" }),
      protectPicker.el,
      window.FOSS.components.field({ label: "Password", testid: "pdf-protect-pw-field", control: protectPw }),
      window.FOSS.components.field({ label: "Confirm Password", testid: "pdf-repeat-pw-field", control: repeatPw }),
      window.FOSS.dom.el("label", { className: "row", style: "gap: var(--space-2); cursor: pointer;" }, [
        allowPrintCheck,
        window.FOSS.dom.el("span", { className: "text-xs text-muted", text: "Allow Printing" })
      ]),
      window.FOSS.dom.el("div", { className: "row", style: "margin-top: var(--space-2);" }, [protectBtn])
    ]);

    // Right card: Unlock
    var unlockFile = "";
    var unlockPicker = window.FOSS.components.filePicker({
      testid: "pdf-unlock-picker",
      title: "Select Encrypted PDF",
      fileTypes: ["pdf"],
      onChange: function (fp) { unlockFile = fp; }
    });
    var unlockPw = window.FOSS.dom.el("input", {
      type: "password",
      className: "input",
      "data-testid": "pdf-unlock-password",
      placeholder: "Current Password"
    });

    var unlockBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary",
      "data-testid": "pdf-unlock-btn",
      onclick: function () {
        if (!unlockFile) {
          window.FOSS.dialogs.toast("Select an encrypted PDF file.");
          return;
        }
        window.FOSS.api("select_save_path", {
          title: "Save Unlocked PDF",
          default_name: stemOf(unlockFile) + "_unlocked",
          file_types: [{ name: "PDF Document (*.pdf)", extensions: ["pdf"] }]
        }).then(function (res) {
          if (!res || !res.file_path) return;
          return window.FOSS.api("pdf_unlock", {
            file_path: unlockFile,
            output_path: res.file_path,
            password: unlockPw.value
          }).then(function (unlRes) {
            resultHost.innerHTML = "";
            resultHost.removeAttribute("hidden");
            var card = window.FOSS.components.resultCard({
              testid: "pdf-unlock-result-card",
              title: "PDF Password Removed",
              outputPath: unlRes.output_path || res.file_path
            });
            resultHost.appendChild(card);
            window.FOSS.dialogs.toast("PDF successfully unlocked.");
          });
        }).catch(function (err) {
          window.FOSS.dialogs.toast("Unlock failed: " + (err.message || err));
        });
      }
    }, [
      window.FOSS.icons.el("unlock", 14),
      window.FOSS.dom.el("span", { text: "Remove PDF Password" })
    ]);

    var unlockCard = window.FOSS.dom.el("div", { className: "card", style: "display: flex; flex-direction: column; gap: var(--space-3);" }, [
      window.FOSS.dom.el("h3", { className: "card-title", text: "Remove PDF Password" }),
      unlockPicker.el,
      window.FOSS.components.field({ label: "Password", testid: "pdf-unlock-pw-field", control: unlockPw }),
      window.FOSS.dom.el("div", { className: "row", style: "margin-top: var(--space-2);" }, [unlockBtn])
    ]);

    var splitGrid = window.FOSS.dom.el("div", { className: "split even", style: "min-height: 0; flex-shrink: 0;" }, [
      protectCard,
      unlockCard
    ]);

    panel.appendChild(splitGrid);
    panel.appendChild(resultHost);
  }

  // Register Router
  window.FOSS.router.register({
    id: "pdf",
    title: "PDF Tools",
    navName: "PDF",
    category: "Documents",
    icon: "pdf",
    workbench: true,
    defaults: [
      {
        key: "group_behavior",
        label: "Document groups on import",
        type: "select",
        options: [
          { value: "expanded", label: "Expanded" },
          { value: "collapsed", label: "Collapsed" }
        ],
        default: "expanded"
      },
      {
        key: "rotation_step",
        label: "Rotation step",
        type: "select",
        options: [
          { value: "90", label: "90 deg" },
          { value: "180", label: "180 deg" },
          { value: "270", label: "270 deg" }
        ],
        default: "90"
      },
      {
        key: "output_dpi",
        label: "Page viewer output DPI",
        type: "number",
        min: 72,
        max: 600,
        step: 1,
        default: 150,
        hint: "Resolution used when rendering a page in the viewer."
      },
      {
        key: "stamp_format",
        label: "Default page number stamp format",
        type: "select",
        options: [
          { value: "Page {n} of {total}", label: "Page {n} of {total}" },
          { value: "{n} / {total}", label: "{n} / {total}" },
          { value: "{n}", label: "{n}" }
        ],
        default: "Page {n} of {total}"
      },
      {
        key: "stamp_position",
        label: "Default page number stamp position",
        type: "select",
        options: [
          { value: "bottom_center", label: "Bottom Center" },
          { value: "bottom_right", label: "Bottom Right" },
          { value: "bottom_left", label: "Bottom Left" },
          { value: "top_center", label: "Top Center" },
          { value: "top_right", label: "Top Right" },
          { value: "top_left", label: "Top Left" }
        ],
        default: "bottom_center"
      }
    ],
    description: "Combine, organize, split, and protect PDF documents with visual page grid.",
    tabs: [
      { id: "merge", label: "Combine & Organize", render: renderCombineOrganize },
      { id: "split", label: "Split PDF", render: renderSplit },
      { id: "security", label: "Protect & Unlock", render: renderSecurity }
    ],
    onFiles: function (paths) {
      if (!paths || paths.length === 0) return;
      window.FOSS.router.open("pdf", "merge");
      if (window.FOSS._pdfAddSources) {
        window.FOSS._pdfAddSources(paths);
      }
    }
  });
})();
