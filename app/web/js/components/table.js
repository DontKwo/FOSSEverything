// Table component: sticky header, tabular numbers, and pagination.
window.FOSS = window.FOSS || {};
window.FOSS.components = window.FOSS.components || {};

(function () {
  function table(opts) {
    opts = opts || {};
    var testid = opts.testid || "table";
    var columns = opts.columns || [];
    var rows = opts.rows || [];
    var maxInitial = opts.maxInitial || 500;
    var displayedLimit = maxInitial;

    var thead = window.FOSS.dom.el("thead", {}, [
      window.FOSS.dom.el("tr", {}, columns.map(function (col) {
        return window.FOSS.dom.el("th", { text: col.title || col.key });
      }))
    ]);

    var tbody = window.FOSS.dom.el("tbody", {});

    var tableEl = window.FOSS.dom.el("table", {
      className: "table",
      "data-testid": testid
    }, [thead, tbody]);

    var showMoreBtn = window.FOSS.dom.el("button", {
      className: "btn btn-secondary btn-sm",
      text: "Show more",
      type: "button",
      onClick: function () {
        displayedLimit += maxInitial;
        renderRows();
      }
    });

    var wrap = window.FOSS.dom.el("div", {
      className: "table-wrap scroll-x"
    }, [tableEl]);

    function renderRows() {
      tbody.innerHTML = "";
      var slice = rows.slice(0, displayedLimit);
      slice.forEach(function (r, idx) {
        var tr = window.FOSS.dom.el("tr", { "data-row-idx": String(idx) });
        columns.forEach(function (col) {
          var val = r[col.key];
          var cellContent;
          if (col.render) {
            cellContent = col.render(val, r, idx);
          } else {
            cellContent = String(val !== undefined && val !== null ? val : "");
          }
          var td = window.FOSS.dom.el("td", {}, [cellContent]);
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });

      if (rows.length > displayedLimit) {
        if (!showMoreBtn.parentNode) wrap.appendChild(showMoreBtn);
      } else {
        if (showMoreBtn.parentNode) showMoreBtn.parentNode.removeChild(showMoreBtn);
      }
    }

    renderRows();

    return {
      el: wrap,
      setRows: function (newRows) {
        rows = newRows || [];
        displayedLimit = maxInitial;
        renderRows();
      }
    };
  }

  window.FOSS.components.table = table;
})();
