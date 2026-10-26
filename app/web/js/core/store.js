// Client-side settings cache and persistent storage manager.
window.FOSS = window.FOSS || {};

(function () {
  var cache = {};
  var listeners = {};

  function loadAll() {
    return window.FOSS.api("get_settings_all", {}).then(function (res) {
      if (res && res.ok && res.settings) {
        cache = res.settings;
      }
      return cache;
    });
  }

  function get(key, defaultValue) {
    if (cache[key] !== undefined) {
      return cache[key];
    }
    return defaultValue;
  }

  function set(key, value) {
    cache[key] = value;
    window.FOSS.api("set_setting", { key: key, value: value });
    if (listeners[key]) {
      listeners[key].forEach(function (cb) {
        cb(value);
      });
    }
  }

  function isFavorite(toolId) {
    var favs = get("favorites", []);
    return Array.isArray(favs) && favs.indexOf(toolId) !== -1;
  }

  function toggleFavorite(toolId) {
    var favs = get("favorites", []);
    if (!Array.isArray(favs)) favs = [];
    var idx = favs.indexOf(toolId);
    if (idx === -1) {
      favs.push(toolId);
    } else {
      favs.splice(idx, 1);
    }
    set("favorites", favs);
    return idx === -1;
  }

  function subscribe(key, callback) {
    listeners[key] = listeners[key] || [];
    listeners[key].push(callback);
  }

  window.FOSS.store = {
    loadAll: loadAll,
    get: get,
    set: set,
    isFavorite: isFavorite,
    toggleFavorite: toggleFavorite,
    subscribe: subscribe
  };
})();

