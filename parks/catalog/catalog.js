"use strict";

const getCatalogElement = id => document.getElementById(id);
const displayName = name => name[0].toLocaleUpperCase("ru") + name.slice(1);
const queryPark = new URLSearchParams(location.search).get("park");

async function read(url, format) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Не удалось загрузить ${url}`);
  return response[format]();
}

function renderCatalog(parks) {
  const search = getCatalogElement("park-search");
  const normalize = s => s.toLocaleLowerCase("ru").replace(/ё/g, "е");
  function update() {
    const term = normalize(search.value.trim());
    const matches = parks.filter(p => normalize(p.name + " " + p.short).includes(term));
    const items = matches.map(park => {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = `?park=${park.id}`;
      const sameName = parks.filter(other => other.name === park.name).length > 1;
      link.textContent = sameName ? `${displayName(park.name)} · ${park.center[1].toFixed(3)}, ${park.center[0].toFixed(3)}` : displayName(park.name);
      li.append(link);
      return li;
    });
    getCatalogElement("park-list").replaceChildren(...items);
    getCatalogElement("park-count").textContent = matches.length ? `Найдено: ${matches.length}` : "Ничего не найдено";
  }
  parks.sort((a, b) => a.name.localeCompare(b.name, "ru"));
  search.addEventListener("input", update);
  getCatalogElement("catalog").hidden = false;
  update();
}

async function renderPark(park) {
  document.title = `${displayName(park.name)}: карта троп — Атлас Москвы`;
  getCatalogElement("title").textContent = displayName(park.name);
  getCatalogElement("intro").textContent = park.count
    ? "Дорожки, тропы и граница территории на одной карте."
    : "Граница территории на карте. В выгрузке нет отдельных пешеходных дорожек.";
  const text = await read(`trails-${park.group}.txt`, "text");
  const bytes = Uint8Array.from(atob(text), char => char.charCodeAt(0));
  const decoded = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  const record = (await new Response(decoded).json())[park.id];
  const boundary = record.b.map(ring => [[...ring, ring[0]]]);
  const coords = record.b.flat();
  const ys = coords.map(point => point[1]);
  const xs = coords.map(point => point[0]);
  const parkBounds = [[Math.min(...ys), Math.min(...xs)], [Math.max(...ys), Math.max(...xs)]];
  const features = [{ type: "Feature", properties: { kind: "boundary" },
    geometry: { type: "MultiPolygon", coordinates: boundary } }];
  for (const [kind, lines] of Object.entries(record.t)) {
    features.push({ type: "Feature", properties: { kind },
      geometry: { type: "MultiLineString", coordinates: lines.map(line => line.map(([lat, lon]) => [lon, lat])) } });
  }
  // Что есть в парке: tools/extract_park_places.py -> places.json (OpenStreetMap)
  const LABELS = { sight: ["Достопримечательности", "★", "#8a3b2e"], museum: ["Музеи", "М", "#694477"], view: ["Смотровые", "◉", "#245f91"],
    food: ["Кафе", "К", "#87491f"], play: ["Детские площадки", "Д", "#406428"], wc: ["Туалеты", "WC", "#4d5a5a"], water: ["Вода", "В", "#2f6fa8"] };
  let places = [], placesDate = "";
  try {
    const all = await read("places.json", "json");
    placesDate = all.date;
    places = (all.parks[park.id] || []).map(([lat, lon, category, name], i) => ({ id: "p" + i, name, category, lat, lon }));
  } catch (error) { /* карта троп работает и без объектов */ }
  const categories = { all: ["Все", "", ""] };
  for (const key of Object.keys(LABELS)) if (places.some(place => place.category === key)) categories[key] = LABELS[key];
  if (places.length) {
    getCatalogElement("park-tools").hidden = false;
    getCatalogElement("places").hidden = false;
    getCatalogElement("places-note").textContent = `Объекты — OpenStreetMap, ${placesDate}. Нажмите на значок на карте или на название в списке.`;
  }
  window.parkGuide = { parkName: park.name, parkBounds, places, routes: [], categories };
  const trailUrl = URL.createObjectURL(new Blob([JSON.stringify({ type: "FeatureCollection", features })], { type: "application/json" }));
  getCatalogElement("map").dataset.trails = trailUrl;
  getCatalogElement("trail-status").textContent = park.count
    ? "Отмечены дорожки из OpenStreetMap. На месте сверяйтесь с указателями."
    : "В выгрузке нет отдельных троп. Показана граница.";
  getCatalogElement("map-section").hidden = false;
  const script = document.createElement("script");
  script.src = "../vdnh/guide.js";
  script.addEventListener("error", () => { getCatalogElement("load-error").hidden = false; getCatalogElement("load-error").textContent = "Карта не загрузилась."; });
  document.body.append(script);
  window.addEventListener("pagehide", () => URL.revokeObjectURL(trailUrl), { once: true });
}

read("parks.json", "json").then(parks => {
  const park = parks.find(p => p.id === queryPark);
  if (park) return renderPark(park);
  renderCatalog(parks);
}).catch(() => {
  const error = getCatalogElement("load-error");
  error.hidden = false;
  error.textContent = "Карта не загрузилась. Попробуйте обновить страницу или вернуться к списку парков.";
});
