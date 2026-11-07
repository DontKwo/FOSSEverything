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
        var checkInterval = null;
        window.addEventListener("pywebviewready", function () {
          if (checkInterval) clearInterval(checkInterval);
          resolve();
        }, { once: true });
        // Fallback check
        checkInterval = setInterval(function () {
          if (window.pywebview && window.pywebview.api) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 50);
      });
    }
    return readyPromise;
  }

  function resolveMethod(name) {
    return waitForReady().then(function () {
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[name] === "function") {
        return window.pywebview.api[name];
      }
      return new Promise(function (resolve, reject) {
        var elapsed = 0;
        var timer = setInterval(function () {
          if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[name] === "function") {
            clearInterval(timer);
            resolve(window.pywebview.api[name]);
            return;
          }
          elapsed += 40;
          if (elapsed >= 2000) {
            clearInterval(timer);
            reject(new Error("API method not available: " + name));
          }
        }, 40);
      });
    });
  }

  function api(name, params, options) {
    var p = params || {};
    var opts = options || {};
    return resolveMethod(name).then(function (fn) {
      return fn(p).then(function (res) {
        if (res && res.ok === false && res.error && !opts.silent) {
          if (window.FOSS.toast) window.FOSS.toast.show(res.error, "error");
        }
        return res;
      });
    }).catch(function (exc) {
      var msg = exc && exc.message ? exc.message : String(exc);
      if (!opts.silent && window.FOSS.toast) window.FOSS.toast.show(msg, "error");
      return { ok: false, error: msg };
    });
  }

  function job(method, params, options) {
    var opts = options || {};
    var onProgress = opts.onProgress || function () {};
    var pollInterval = null;
    var cancelFn = null;

    var jobPromise = new Promise(function (resolve, reject) {
      api("job_start", { method: method, params: params || {} }).then(function (startRes) {
        if (!startRes.ok) {
          resolve(startRes);
          return;
        }
        var jobId = startRes.id;
        cancelFn = function () {
          if (pollInterval) clearInterval(pollInterval);
          return api("job_cancel", { id: jobId });
        };
        if (typeof opts.onStart === "function") {
          opts.onStart({ jobId: jobId, cancel: cancelFn });
        }

        function check() {
          api("job_poll", { id: jobId }, { silent: true }).then(function (pollRes) {
            if (!pollRes.ok) {
              clearInterval(pollInterval);
              resolve(pollRes);
              return;
            }
            var rawProg = typeof pollRes.progress === "number" ? pollRes.progress : 0;
            var pct = rawProg;
            if (rawProg > 0 && rawProg <= 1.0) {
              pct = Math.round(rawProg * 100);
            }
            onProgress(pct, pollRes.message || "");

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

    jobPromise.cancel = function () {
      if (cancelFn) return cancelFn();
      return Promise.resolve({ ok: true });
    };

    return jobPromise;
  }

  window.FOSS.api = api;
  window.FOSS.job = job;
})();
