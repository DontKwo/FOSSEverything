// Python bridge and background job runner.
window.FOSS = window.FOSS || {};

(function () {
  var readyPromise = null;

  function waitForReady() {
    if (window.pywebview && window.pywebview.api) {
      return Promise.resolve();
    }
    if (!readyPromise) {
      readyPromise = new Promise(function (resolve) {
        window.addEventListener("pywebviewready", function () {
          resolve();
        }, { once: true });
        // Fallback check
        var checkInterval = setInterval(function () {
          if (window.pywebview && window.pywebview.api) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 50);
      });
    }
    return readyPromise;
  }

  function api(name, params) {
    var p = params || {};
    return waitForReady().then(function () {
      if (!window.pywebview || !window.pywebview.api || typeof window.pywebview.api[name] !== "function") {
        var err = "API method not available: " + name;
        if (window.FOSS.toast) window.FOSS.toast.show(err, "error");
        return { ok: false, error: err };
      }
      return window.pywebview.api[name](p).then(function (res) {
        if (res && res.ok === false && res.error) {
          if (window.FOSS.toast) window.FOSS.toast.show(res.error, "error");
        }
        return res;
      }).catch(function (exc) {
        var msg = exc && exc.message ? exc.message : String(exc);
        if (window.FOSS.toast) window.FOSS.toast.show(msg, "error");
        return { ok: false, error: msg };
      });
    });
  }

  function job(method, params, options) {
    var opts = options || {};
    var onProgress = opts.onProgress || function () {};
    var pollInterval = null;

    return new Promise(function (resolve, reject) {
      api("job_start", { method: method, params: params || {} }).then(function (startRes) {
        if (!startRes.ok) {
          resolve(startRes);
          return;
        }
        var jobId = startRes.id;

        function check() {
          api("job_poll", { id: jobId }).then(function (pollRes) {
            if (!pollRes.ok) {
              clearInterval(pollInterval);
              resolve(pollRes);
              return;
            }
            onProgress(pollRes.progress || 0.0, pollRes.message || "");

            if (pollRes.state === "done") {
              clearInterval(pollInterval);
              resolve(pollRes.result || { ok: true });
            } else if (pollRes.state === "failed") {
              clearInterval(pollInterval);
              resolve({ ok: false, error: pollRes.error || pollRes.message });
            } else if (pollRes.state === "cancelled") {
              clearInterval(pollInterval);
              resolve({ ok: false, cancelled: true, error: "Cancelled" });
            }
          }).catch(function (err) {
            clearInterval(pollInterval);
            resolve({ ok: false, error: String(err) });
          });
        }

        pollInterval = setInterval(check, 250);
      });
    });
  }

  window.FOSS.api = api;
  window.FOSS.job = job;
})();

