// Карта места «За город»: точки маршрута + слой «что рядом» из OpenStreetMap (places.json) с фильтрами.
(function () {
  var ICONS = {
    sight: "M12 3.5l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z",
    museum: "M3 20h18M5 20v-9M9.7 20v-9M14.3 20v-9M19 20v-9M2.5 10.5 12 4l9.5 6.5z",
    church: "M12 2.5v5M9.8 4.6h4.4M12 7.5c-2.6 1.6-3.6 3.4-3.6 5.5h7.2c0-2.1-1-3.9-3.6-5.5zM7 20.5V13h10v7.5M4.5 20.5h15M10.5 20.5v-3a1.5 1.5 0 0 1 3 0v3",
    view: "M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12zM12 9.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6z",
    art: "M12 3.5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM7 16c0-3 2.2-5 5-5s5 2 5 5M6 20.5h12M8 20.5V16h8v4.5",
    food: "M4 9h12v4.5A4.5 4.5 0 0 1 11.5 18h-3A4.5 4.5 0 0 1 4 13.5zM16 10.5h1.8a2 2 0 0 1 0 4H16M7 3.5c-.8 1 .8 2 0 3M11 3.5c-.8 1 .8 2 0 3M3 21h14",
    hotel: "M3 19.5V6M3 15.5h18v4M21 15.5V12a2.5 2.5 0 0 0-2.5-2.5H10v6M6.5 9.8a1.7 1.7 0 1 0 0 3.4 1.7 1.7 0 0 0 0-3.4z",
    parking: "M8 20V4.5h5a4.3 4.3 0 0 1 0 8.6H8"
  };
  var CATS = { sight: ["Достопримечательности", "#a8423a"], museum: ["Музеи", "#6d4a8e"], church: ["Храмы", "#8a6a1f"], view: ["Смотровые", "#2a7a70"], art: ["Арт-объекты и скульптуры", "#8a5a2a"],
    food: ["Кафе", "#9a5a1c"], hotel: ["Где переночевать", "#33618f"], parking: ["Парковки", "#4d5a6a"], wc: ["Туалеты", "#4d5a5a"] };
  var MINOR = { food: 1, hotel: 1, parking: 1, wc: 1 };
  function badge(c, size) {
    var s = document.createElement("span"); s.className = "cat-badge"; s.style.setProperty("--pin", CATS[c][1]);
    if (ICONS[c]) { s.innerHTML = '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size + '" aria-hidden="true"><path d="' + ICONS[c] + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'; }
    else s.textContent = "WC";
    return s;
  }
  addEventListener("load", function () {
    var el = document.getElementById("zgmap"); if (!window.L || !el || !window.ZG) return;
    var m = L.map(el, { scrollWheelZoom: false, zoomSnap: 0.25 }); m.attributionControl.setPrefix(false);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(m);
    var b = [];
    ZG.points.forEach(function (p, i) {
      var lab = ZG.numbered ? (p[5] || String(i + 1)) : "★";
      var ic = L.divIcon({ className: "poi-icon route-pin", html: lab, iconSize: [lab.length > 2 ? 40 : 29, 29] });
      var d = document.createElement("div"), h = document.createElement("strong"), t = document.createElement("p"); h.textContent = p[2]; t.textContent = p[3]; d.append(h, t);
      if (p[4]) { var a = document.createElement("a"); a.href = p[4]; a.textContent = "Подробнее →"; d.append(a); }
      L.marker([p[0], p[1]], { icon: ic, title: p[2], zIndexOffset: 1000 }).addTo(m).bindPopup(d); b.push([p[0], p[1]]);
    });
    m.fitBounds(b, { padding: [40, 40], maxZoom: 16 });
    if (!ZG.places) return;
    fetch(ZG.places).then(function (r) { return r.json(); }).then(function (data) {
      var layer = L.layerGroup().addTo(m), active = "main", bar = document.getElementById("zgfilters");
      var have = {}; data.places.forEach(function (p) { have[p[2]] = (have[p[2]] || 0) + 1; });
      function draw() {
        layer.clearLayers();
        data.places.forEach(function (p) {
          var c = p[2]; if (!CATS[c]) return;
          if (active === "main" ? (MINOR[c] || m.getZoom() < 14) : active !== c) return;
          var d = document.createElement("div"), h = document.createElement("strong"), t = document.createElement("p"); h.textContent = p[3] || CATS[c][0]; t.textContent = CATS[c][0]; d.append(h, t);
          L.marker([p[0], p[1]], { icon: L.divIcon({ className: "poi-icon", html: badge(c, 15), iconSize: [28, 28] }), title: p[3] || CATS[c][0] }).addTo(layer).bindPopup(d);
        });
      }
      function chip(key, label) {
        var btn = document.createElement("button"); btn.type = "button"; btn.setAttribute("aria-pressed", key === active);
        if (CATS[key]) btn.append(badge(key, 13)); btn.append(label);
        btn.addEventListener("click", function () { active = key; [].forEach.call(bar.children, function (x) { x.setAttribute("aria-pressed", x === btn); }); draw(); });
        bar.append(btn);
      }
      if (bar) { chip("main", "Главное"); Object.keys(CATS).forEach(function (c) { if (have[c]) chip(c, CATS[c][0] + " · " + have[c]); }); bar.hidden = false; }
      m.on("zoomend", draw); draw();
    }).catch(function () {});
  });
})();
