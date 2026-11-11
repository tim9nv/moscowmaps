"use strict";

const { places, routes, parkBounds, parkName } = window.parkGuide || window.vdnhGuide;
const byId = new Map(places.map(place => [place.id, place]));
const categories = (window.parkGuide && window.parkGuide.categories) || {
  all: ["Все", "", ""],
  pavilion: ["Павильоны", "П", "#305a49"],
  museum: ["Музеи и развлечения", "М", "#694477"],
  fountain: ["Фонтаны", "Ф", "#245f91"],
  entrance: ["Входы", "В", "#87491f"],
  service: ["Удобства", "i", "#4d5a5a"],
  green: ["Зелёные зоны", "З", "#406428"],
  transport: ["Транспорт", "Т", "#843e4e"],
};
const get = id => document.getElementById(id);
const normalize = text => text.toLocaleLowerCase("ru").replace(/ё/g, "е").replace(/[№\s]+/g, "");
const status = get("status");
const locate = get("locate");
const map = window.L ? L.map("map", { scrollWheelZoom: false, zoomSnap: 0.25 }) : null;
// В углу карты только «© OpenStreetMap»: её требует лицензия карты. Упоминание Leaflet убрано по просьбе владельца (лицензия Leaflet подписи на карте не требует).
if (map) map.attributionControl.setPrefix(false);
const bounds = parkBounds || [[55.824, 37.608], [55.844, 37.648]];
const routeBanner = get("selected-route");
let category = "all";
let activeRoute = null;
let watch = null;
let userLayer = null;
let firstFix = true;
const markers = new Map();
const MINOR = new Set(["food", "wc", "water", "play", "art"]);
const MINOR_ZOOM = 17;

// Значки вместо букв: простые контуры 24×24 в одну толщину линии, рисуются белым на цветном кружке.
const ICONS = {
  sight: "M12 3.5l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z",
  museum: "M3 20h18M5 20v-9M9.7 20v-9M14.3 20v-9M19 20v-9M2.5 10.5 12 4l9.5 6.5z",
  view: "M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12zM12 9.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6z",
  art: "M12 3.5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM7 16c0-3 2.2-5 5-5s5 2 5 5M6 20.5h12M8 20.5V16h8v4.5",
  food: "M4 9h12v4.5A4.5 4.5 0 0 1 11.5 18h-3A4.5 4.5 0 0 1 4 13.5zM16 10.5h1.8a2 2 0 0 1 0 4H16M7 3.5c-.8 1 .8 2 0 3M11 3.5c-.8 1 .8 2 0 3M3 21h14",
  play: "M3.5 21 7 4h10l3.5 17M5.8 11h12.4M10 11v6.5M14 11v6.5M9 17.5h6",
  water: "M12 3.5s6 6.8 6 10.8a6 6 0 0 1-12 0c0-4 6-10.8 6-10.8z",
  pavilion: "M3 11 12 4l9 7M5.5 9.5V20h13V9.5M10 20v-5h4v5",
  fountain: "M12 13V5M12 5c-2.5 0-4.5 1.5-5 4M12 5c2.5 0 4.5 1.5 5 4M4 15h16M5.5 15v4.5h13V15",
  entrance: "M11 3.5h8v17h-8M3 12h11M10.5 8.5 14 12l-3.5 3.5",
  service: "M12 10.5v7M12 6.5v.5",
  green: "M12 21v-4.5M12 3 6.5 10h3L5 16.5h14L14.5 10h3z",
  stop: "M6 21V4M6 4.5h11l-2.2 4 2.2 4H6",
  transport: "M5.5 4h13a1 1 0 0 1 1 1v12h-15V5a1 1 0 0 1 1-1zM4.5 11.5h15M7.5 20v-3M16.5 20v-3M8 14.2v.1M16 14.2v.1",
};
function iconSvg(key, size) {
  const d = ICONS[key];
  if (!d) return null;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("width", size); svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d); path.setAttribute("fill", "none"); path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "2"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}
// Кружок со значком: на карте, в кнопках фильтров и в списке.
function badge(key, size) {
  const [, letter, color] = categories[key] || ["", "", "#295b49"];
  const span = element("span", null, "cat-badge");
  span.style.setProperty("--pin", color || "#295b49");
  const svg = iconSvg(key, size);
  if (svg) span.append(svg); else span.textContent = letter;
  return span;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function popup(place, isApproach = false) {
  const box = element("div");
  box.append(element("strong", place.name));
  if (isApproach) box.append(element("p", "Остановка на дорожке у объекта."));
  if (place.description) box.append(element("p", place.description));
  if (place.url) {
    const link = element("a", "Официальная информация ↗");
    link.href = place.url;
    box.append(link);
  }
  return box;
}

if (map) {
  map.fitBounds(bounds, { padding: [12, 12] }); farClass();
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  tiles.on("tileerror", () => {
    if (!status.textContent) status.textContent = "Подложка временно недоступна. Маршруты и точки можно посмотреть на карте или в списке.";
  });
  L.control.scale({ imperial: false }).addTo(map);
  for (const place of places) {
    const color = categories[place.category][2];
    const pin = badge(place.category, 15);
    const icon = L.divIcon({ className: "poi-icon", html: pin, iconSize: [28, 28] });
    const marker = L.marker([place.lat, place.lon], { icon, title: place.name, alt: place.name })
      .bindPopup(popup(place));
    marker.on("add", () => {
      marker.getElement().style.setProperty("--pin", color);
      marker.getElement().setAttribute("aria-label", place.name);
    });
    markers.set(place.id, marker);
  }
} else {
  status.textContent = "Карта не загрузилась. Воспользуйтесь списком объектов и ссылками ниже.";
  get("map").hidden = true;
  locate.disabled = true;
}

function farClass() { if (map) map.getContainer().classList.toggle("far", map.getZoom() < 16); }
function renderPlaces() {
  const query = normalize(get("search").value);
  const filtered = places.filter(place => (category === "all" || place.category === category
    || (category === "pavilion" && place.name.startsWith("Павильон")))
    && (normalize(place.name).includes(query) || (place.aliases || []).some(alias => normalize(alias).includes(query))));
  const showContext = !activeRoute || category !== "all" || Boolean(query);
  // На общем виде парка мелочь (кафе, туалеты, вода, площадки, скульптуры) не показываем: значки слипаются в кучу.
  // Она появляется при приближении, при выборе своего фильтра или в поиске; в списке ниже есть всегда.
  const close = map && map.getZoom() >= MINOR_ZOOM;
  const onMap = filtered.filter(place => close || category !== "all" || query || !MINOR.has(place.category));
  const visible = new Set(showContext ? onMap.map(place => place.id) : []);
  for (const [id, marker] of markers) {
    if (visible.has(id)) marker.addTo(map);
    else marker.remove();
  }
  get("count").textContent = `(${filtered.length})`;
  const items = filtered.map(place => {
    const li = element("li");
    if (!map) {
      const link = element("a", place.name);
      link.href = place.url || `https://www.openstreetmap.org/?mlat=${place.lat}&mlon=${place.lon}#map=18/${place.lat}/${place.lon}`;
      li.append(link);
      return li;
    }
    const button = element("button");
    button.append(badge(place.category, 12), place.name);
    button.type = "button";
    button.addEventListener("click", () => {
      map.setView([place.lat, place.lon], Math.max(17, map.getZoom()));
      markers.get(place.id).addTo(map).openPopup();
      get("map-section").scrollIntoView({ block: "start" });
    });
    li.append(button);
    return li;
  });
  get("place-list").replaceChildren(...(items.length ? items : [element("li", "Ничего не найдено. Попробуйте другое название или сбросьте категорию.")]));
}

for (const [key, [label]] of Object.entries(categories)) {
  const button = element("button");
  if (key !== "all") button.append(badge(key, 13));
  button.append(label);
  button.type = "button";
  button.dataset.category = key;
  button.setAttribute("aria-pressed", String(key === category));
  button.addEventListener("click", () => {
    category = key;
    for (const chip of get("filters").children) {
      chip.setAttribute("aria-pressed", String(chip.dataset.category === key));
    }
    renderPlaces();
  });
  get("filters").append(button);
}
get("search").addEventListener("input", () => {
  renderPlaces();
  const search = normalize(get("search").value);
  if (search) get("places").open = true;
});
renderPlaces();

const routeLayer = map ? L.layerGroup().addTo(map) : null;
const arrowLayer = map ? L.layerGroup().addTo(map) : null;
const routeLeg = get("route-leg");
let displayedTrack = [];
let trackOverview = false;

function getLegs(route) {
  let offset = 0;
  return route.approaches.slice(1).map(point => {
    const end = route.track.findIndex((vertex, index) => index > offset
      && vertex[0] === point[0] && vertex[1] === point[1]);
    const leg = route.track.slice(offset, end + 1);
    offset = end;
    return leg;
  });
}

function drawArrows() {
  arrowLayer.clearLayers();
  const points = displayedTrack.map(point => map.project(point, map.getZoom()));
  const edge = index => [displayedTrack[index - 1].join(), displayedTrack[index].join()].sort().join("|");
  const counts = new Map();
  for (let i = 1; i < points.length; i++) counts.set(edge(i), (counts.get(edge(i)) || 0) + 1);

  const total = points.slice(1).reduce((length, point, index) => length + point.distanceTo(points[index]), 0);
  const spacing = Math.max(54, total / 32);
  let next = Math.min(spacing * 0.65, total / 2);
  let travelled = 0;
  for (let i = 1; i < points.length; i++) {
    const from = points[i - 1];
    const delta = points[i].subtract(from);
    const length = points[i].distanceTo(from);
    while (length && next < travelled + length) {
      if (!trackOverview || counts.get(edge(i)) === 1) {
        const point = map.unproject(from.add(delta.multiplyBy((next - travelled) / length)), map.getZoom());
        const angle = Math.atan2(delta.y, delta.x) * 180 / Math.PI;
        const arrow = element("span", "➜", "route-chevron");
        arrow.setAttribute("aria-hidden", "true");
        arrow.style.transform = `rotate(${angle}deg)`;
        const icon = L.divIcon({ className: "route-arrow", html: arrow, iconSize: [21, 21] });
        L.marker(point, { icon, interactive: false, keyboard: false, zIndexOffset: 600 }).addTo(arrowLayer);
      }
      next += spacing;
    }
    travelled += length;
  }
}

function drawRoute(route) {
  routeLayer.clearLayers();
  const legIndex = Number(routeLeg.value);
  trackOverview = legIndex < 0;
  displayedTrack = trackOverview ? route.track : getLegs(route)[legIndex];
  map.closePopup();
  L.polyline(displayedTrack, { color: "#fff", weight: 10, interactive: false }).addTo(routeLayer);
  const line = L.polyline(displayedTrack, { color: "#713887", weight: 6, interactive: false }).addTo(routeLayer);
  const last = route.stops.length - 1;
  const loop = route.stops[0] === route.stops[last] && route.approaches[0].join() === route.approaches[last].join();
  route.stops.forEach((id, index) => {
    if (trackOverview && loop && index === last) return;
    if (!trackOverview && index !== legIndex && index !== legIndex + 1) return;
    const place = byId.get(id);
    const label = trackOverview && loop && index === 0 ? `1·${last + 1}` : String(index + 1);
    const icon = L.divIcon({ className: "poi-icon route-pin", html: label, iconSize: [29, 29] });
    L.marker(route.approaches[index], { icon, title: place.name, alt: place.name, zIndexOffset: 800 })
      .bindPopup(popup(place, true)).addTo(routeLayer);
  });
  map.fitBounds(line.getBounds(), { padding: [32, 32], maxZoom: 18 });
  drawArrows();
}

function showRoute(route) {
  activeRoute = activeRoute === route.id ? null : route.id;
  routeLayer.clearLayers();
  arrowLayer.clearLayers();
  displayedTrack = [];
  for (const button of document.querySelectorAll("[data-route]")) {
    const selected = button.dataset.route === activeRoute;
    button.setAttribute("aria-pressed", String(selected));
    button.textContent = selected ? "Скрыть маршрут" : "Показать маршрут";
  }
  routeBanner.hidden = get("route-tools").hidden = !activeRoute;
  get("map").classList.toggle("walking", Boolean(activeRoute));
  renderPlaces();
  if (!activeRoute) return;
  get("selected-route-name").textContent = route.name;
  const overview = element("option", "Весь маршрут");
  overview.value = "-1";
  const options = route.stops.slice(1).map((id, index) => {
    const option = element("option", `${index + 1} → ${index + 2} · ${byId.get(id).name}`);
    option.value = String(index);
    return option;
  });
  routeLeg.replaceChildren(overview, ...options);
  drawRoute(route);
  get("map-section").scrollIntoView({ block: "start" });
  get("clear-route").focus({ preventScroll: true });
}

if (map) map.on("zoomend", () => { drawArrows(); renderPlaces(); farClass(); });
routeLeg.addEventListener("change", () => {
  if (activeRoute) drawRoute(routes.find(route => route.id === activeRoute));
});

get("clear-route").addEventListener("click", () => {
  if (activeRoute) {
    showRoute(routes.find(route => route.id === activeRoute));
    get("map-title").focus();
  }
});

for (const route of routes) {
  const article = element("article", "", "route");
  const km = new Intl.NumberFormat("ru", { maximumFractionDigits: 1 }).format(route.metres / 1000);
  const minutes = Math.ceil(route.metres / (4000 / 60) / 5) * 5;
  article.append(element("h3", route.name), element("p", `${km} км · около ${minutes} мин`, "muted"),
    element("p", route.description),
    element("p", route.stops.map(id => byId.get(id).name).join(" → "), "muted"));
  if (map) {
    const button = element("button", "Показать маршрут");
    button.type = "button";
    button.dataset.route = route.id;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => showRoute(route));
    article.append(button);
  }
  get("routes").append(article);
}

get("botanical-link")?.addEventListener("click", () => {
  if (activeRoute) showRoute(routes.find(route => route.id === activeRoute));
  get("filters").querySelector('[data-category="all"]').click();
  get("search").value = "подход со стороны ВДНХ";
  get("places").open = true;
  renderPlaces();
  if (!map) return;
  const place = byId.get("botanical-approach");
  map.setView([place.lat, place.lon], 17);
  markers.get(place.id).openPopup();
});

for (const link of document.querySelectorAll("[data-place]")) {
  link.addEventListener("click", () => {
    const place = byId.get(link.dataset.place);
    if (!place || !map) return;
    if (activeRoute) showRoute(routes.find(route => route.id === activeRoute));
    map.setView([place.lat, place.lon], 17);
    markers.get(place.id).addTo(map).openPopup();
  });
}

function stopLocation() {
  if (watch !== null) navigator.geolocation.clearWatch(watch);
  watch = null;
  if (userLayer) userLayer.remove();
  userLayer = null;
  locate.setAttribute("aria-pressed", "false");
  locate.textContent = "◎ Я на карте";
}

function showLocation({ coords }) {
  const point = [coords.latitude, coords.longitude];
  if (userLayer) userLayer.remove();
  userLayer = L.layerGroup([
    L.circle(point, { radius: coords.accuracy, color: "#1766cf", weight: 1, fillOpacity: 0.13, interactive: false }),
    L.circleMarker(point, { radius: 8, color: "#fff", weight: 3, fillColor: "#1766cf", fillOpacity: 1 })
      .bindTooltip("Вы здесь"),
  ]).addTo(map);
  const nearby = L.latLngBounds(bounds).pad(0.4).contains(point);
  if (nearby && firstFix) map.setView(point, Math.max(16, map.getZoom()));
  firstFix = false;
  locate.textContent = "Скрыть позицию";
  status.textContent = nearby
    ? `Вы на карте. Точность около ${Math.round(coords.accuracy)} м.`
    : `Вы находитесь за пределами карты: ${parkName || "ВДНХ"}.`;
}

locate.addEventListener("click", () => {
  if (watch !== null) {
    stopLocation();
    status.textContent = "";
    return;
  }
  if (!window.isSecureContext || !navigator.geolocation) {
    status.textContent = "Браузер не поддерживает геолокацию на этой странице.";
    return;
  }
  firstFix = true;
  locate.setAttribute("aria-pressed", "true");
  locate.textContent = "Отменить поиск";
  status.textContent = "Определяем местоположение…";
  watch = navigator.geolocation.watchPosition(showLocation, error => {
    stopLocation();
    status.textContent = error.code === 1
      ? "Геолокация отключена. Разрешите доступ в настройках браузера или продолжайте смотреть карту."
      : "Местоположение пока недоступно. Попробуйте ещё раз.";
  }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 });
});
window.addEventListener("pagehide", stopLocation);


const expandMap = get("map-expand");
const mapShell = get("map-shell");
if (expandMap && map) {
  let expanded = false;
  function setExpanded(value) {
    expanded = value;
    mapShell.classList.toggle("map-expanded", expanded);
    document.body.classList.toggle("map-view-open", expanded);
    expandMap.setAttribute("aria-pressed", String(expanded));
    expandMap.textContent = expanded ? "⤡ Свернуть карту" : "⛶ На весь экран";
    requestAnimationFrame(() => map.invalidateSize({ animate: false }));
  }

  expandMap.addEventListener("click", async () => {
    if (expanded) {
      if (document.fullscreenElement === mapShell) await document.exitFullscreen();
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (mapShell.requestFullscreen) {
      try {
        await mapShell.requestFullscreen();
      } catch {
        // The fixed layout also works where the browser restricts fullscreen.
      }
    }
  });
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) setExpanded(false);
    else if (document.fullscreenElement === mapShell) setExpanded(true);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && expanded && !document.fullscreenElement) {
      setExpanded(false);
      expandMap.focus();
    }
  });
} else if (expandMap) {
  expandMap.disabled = true;
}

const trailSource = get("map").dataset.trails;
if (map && trailSource) {
  const toggle = get("trail-toggle");
  const trailStatus = get("trail-status");
  const trailStyles = {
    boundary: { color: "#397460", weight: 2, opacity: 0.6, fill: false, dashArray: "5 6" },
    excluded: { color: "#807365", weight: 1, opacity: 0.5, fillColor: "#807365", fillOpacity: 0.13 },
    paved: { color: "#007466", weight: 3 },
    unpaved: { color: "#884921", weight: 3, dashArray: "7 5" },
    boardwalk: { color: "#1966a0", weight: 4, dashArray: "11 3" },
    steps: { color: "#a32646", weight: 4, dashArray: "1 5" },
    unknown: { color: "#515c63", weight: 2.5, dashArray: "2 4" },
  };
  const pane = map.createPane("park-trails");
  pane.style.zIndex = "350";
  pane.style.pointerEvents = "none";
  const renderer = L.canvas({ pane: "park-trails" });
  fetch(trailSource)
    .then(response => {
      if (!response.ok) throw new Error("Trail data unavailable");
      return response.json();
    })
    .then(data => {
      const style = feature => {
        const settings = trailStyles[feature.properties.kind];
        if (map.getZoom() >= 16 || !feature.geometry.type.includes("LineString")) return settings;
        return { ...settings, weight: settings.weight * 0.55, opacity: 0.75 };
      };
      const layer = L.geoJSON(data, {
        renderer,
        interactive: false,
        style,
      }).addTo(map);
      const kinds = new Set(data.features.map(feature => feature.properties.kind));
      for (const item of document.querySelectorAll(".trail-legend span")) {
        item.hidden = !kinds.has(item.className);
      }
      map.on("zoomend", () => layer.setStyle(style));
      toggle.disabled = false;
      toggle.addEventListener("change", () => {
        if (toggle.checked) layer.addTo(map);
        else layer.remove();
      });
    })
    .catch(() => {
      trailStatus.textContent = "Слой троп не загрузился. Обновите страницу.";
    });
}
