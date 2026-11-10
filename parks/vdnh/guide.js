"use strict";

const { places, routes } = window.vdnhGuide;
const byId = new Map(places.map(place => [place.id, place]));
const categories = {
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
const map = window.L ? L.map("map", { scrollWheelZoom: false }) : null;
const bounds = [[55.824, 37.608], [55.844, 37.648]];
const routeBanner = get("selected-route");
let category = "all";
let activeRoute = null;
let watch = null;
let userLayer = null;
let firstFix = true;
const markers = new Map();

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
  map.fitBounds(bounds, { padding: [12, 12] });
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  tiles.on("tileerror", () => {
    if (!status.textContent) status.textContent = "Подложка временно недоступна. Маршруты и точки можно посмотреть на карте или в списке.";
  });
  L.control.scale({ imperial: false }).addTo(map);
  for (const place of places) {
    const [, letter, color] = categories[place.category];
    const pin = element("span", letter);
    const icon = L.divIcon({ className: "poi-icon", html: pin, iconSize: [25, 25] });
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

function renderPlaces() {
  const query = normalize(get("search").value);
  const filtered = places.filter(place => (category === "all" || place.category === category
    || (category === "pavilion" && place.name.startsWith("Павильон")))
    && (normalize(place.name).includes(query) || (place.aliases || []).some(alias => normalize(alias).includes(query))));
  const showContext = !activeRoute || category !== "all" || Boolean(query);
  const visible = new Set(showContext ? filtered.map(place => place.id) : []);
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
    const button = element("button", place.name);
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
  const button = element("button", label);
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
  route.stops.forEach((id, index) => {
    if (!trackOverview && index !== legIndex && index !== legIndex + 1) return;
    const place = byId.get(id);
    const icon = L.divIcon({ className: "poi-icon route-pin", html: String(index + 1), iconSize: [29, 29] });
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

if (map) map.on("zoomend", drawArrows);
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

get("botanical-link").addEventListener("click", () => {
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
    : "Вы находитесь за пределами карты ВДНХ.";
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
