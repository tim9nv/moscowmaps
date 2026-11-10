"use strict";

const getCatalogElement = id => document.getElementById(id);
const displayName = name => name[0].toLocaleUpperCase("ru") + name.slice(1);
// Страница парка parks/<slug>/ задаёт window.PARK_ID и window.PARK_BASE ("../catalog/"); старый адрес ?park=<id> переадресуется на неё.
const queryPark = window.PARK_ID || new URLSearchParams(location.search).get("park");
const BASE = window.PARK_BASE || "";

// Рисунок в шапке, как у ВДНХ: свой у десяти главных парков, у остальных — по типу места.
const HERO_SUN = '<circle cx="242" cy="55" r="37" fill="#e6bc71"/>';
const HERO_GROUND = '<path d="M0 175h320M22 193h270" stroke="currentColor" stroke-width="3"/>';
const HERO_ART = {
  trees: '<circle cx="78" cy="108" r="34"/><path d="M78 142v33"/><circle cx="158" cy="92" r="46"/><path d="M158 138v37M158 150l-14-14m14 4 12-12"/><path d="M212 160h62M218 160v15m50-15v15M212 147h62"/>',
  forest: '<path d="M70 62 42 107h14l-22 35h72l-22-35h14zM70 142v33M158 34l-34 54h17l-27 42h88l-27-42h17zM158 130v45M246 76l-24 38h12l-19 30h62l-19-30h12zM246 144v31"/>',
  manor: '<path d="M70 175v-65h180v65M58 110h204L160 62zM95 110v65m32-65v65m66-65v65m32-65v65M145 175v-38h30v38"/><path d="M22 167v-43m-9 18 9-22 9 22m267 25v-43m-9 18 9-22 9 22" stroke-width="2"/>',
  palace: '<path d="M50 175V95h40v80M50 95l20-42 20 42M230 175V95h40v80M230 95l20-42 20 42M90 120h140M105 175v-30a12 12 0 0 1 24 0v30m19 0v-30a12 12 0 0 1 24 0v30m19 0v-30a12 12 0 0 1 24 0v30M70 53V38m180 15V38M62 120v18m16-18v18m164-18v18m16-18v18"/>',
  church: '<path d="M130 175v-55h60v55M118 120h84M130 120l30-84 30 84M160 36V14m-8 9h16M96 175v-32h34m60 0h34v32M150 175v-24a10 10 0 0 1 20 0v24M143 92h34M137 106h46"/><path d="M30 167v-43m-9 18 9-22 9 22" stroke-width="2"/>',
  gate: '<path d="M50 175V85h220v90M40 85h240M50 70h220v15M78 85v90m30-90v90m104-90v90m30-90v90M130 175v-48a30 30 0 0 1 60 0v48M118 70V56h84v14"/>',
  wheel: '<circle cx="150" cy="100" r="62"/><circle cx="150" cy="100" r="7"/><path d="M150 38v124M88 100h124M106 56l88 88m0-88-88 88M150 100l-38 75m38-75 38 75"/><path d="M252 167v-43m-9 18 9-22 9 22" stroke-width="2"/>',
  fountain: '<path d="M88 175h144M100 175c0-20 120-20 120 0M160 158V92M160 92c-22-12-38 10-42 44M160 92c22-12 38 10 42 44M160 112c-11-6-19 6-22 26m22-26c11-6 19 6 22 26"/><circle cx="52" cy="118" r="26"/><path d="M52 144v31"/><path d="M276 167v-43m-9 18 9-22 9 22" stroke-width="2"/>',
  hill: '<path d="M0 175c58-66 118-88 188-88h132M188 87V70h132M210 87V70m30 17V70m30 17V70m30 17V70M40 150c20 4 36-4 52-16"/><path d="M0 196c40-10 80 10 120 0s80-10 120 0 60 6 80 0" stroke-width="2"/><path d="M96 118v-34m-8 14 8-18 8 18" stroke-width="2"/>',
  bridge: '<path d="M14 150 160 92l146 58M14 163l146-58 146 58M52 135v14m36-28v14m36-28v14m72 0v14m36 0v14m36 0v14M160 92v13"/><path d="M0 190c40-10 80 10 120 0s80-10 120 0 60 6 80 0" stroke-width="2"/>',
  pond: '<ellipse cx="170" cy="166" rx="118" ry="20"/><path d="M62 160v-50m10 50v-66m10 66v-44M58 110h8m2-16h8m2 22h8M120 166h40m-28 8h44"/><circle cx="262" cy="104" r="30"/><path d="M262 134v24"/>'
};
const HERO_BY_ID = { "48": "gate", "7": "fountain", "8": "palace", "19": "church", "5": "wheel", "1": "forest", "41": "hill", "135": "bridge" };
function heroKind(park) {
  if (!park) return "trees";
  if (HERO_BY_ID[park.id]) return HERO_BY_ID[park.id];
  const n = park.name.toLocaleLowerCase("ru");
  if (/усадьб|музей|заповедник «|дворц/.test(n)) return "manor";
  if (/лес|заказник|остров|роща|бор\b/.test(n)) return "forest";
  if (/пруд|рек|долин|пойм|озер|набереж|водохранил|канал/.test(n)) return "pond";
  return "trees";
}
function drawHero(park) {
  const hero = document.querySelector("header.hero");
  if (!hero || hero.querySelector(".hero-art")) return;
  hero.classList.add("has-art");
  hero.insertAdjacentHTML("beforeend", `<svg class="hero-art" viewBox="0 0 320 210" aria-hidden="true" fill="none">${HERO_SUN}${HERO_GROUND}<g stroke="currentColor" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">${HERO_ART[heroKind(park)]}</g></svg>`);
}

async function read(url, format) {
  const response = await fetch(BASE + url);
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
      link.href = park.url || `?park=${park.id}`;
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
  if (!window.PARK_ID) {
    document.title = `${displayName(park.name)}: карта троп — Атлас Москвы`;
    getCatalogElement("title").textContent = displayName(park.name);
  }
  if (!window.PARK_ID) getCatalogElement("intro").textContent = park.count
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
  const LABELS = { sight: ["Достопримечательности", "★", "#8a3b2e"], museum: ["Музеи", "М", "#694477"], view: ["Смотровые", "◉", "#245f91"], art: ["Скульптуры", "С", "#7a5a2e"],
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
    if (!window.PARK_ID) getCatalogElement("intro").textContent = "Что посмотреть, где поесть и куда идти: достопримечательности, кафе, площадки и тропы на одной карте.";
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
  script.src = BASE + "../vdnh/guide.js";
  script.addEventListener("error", () => { getCatalogElement("load-error").hidden = false; getCatalogElement("load-error").textContent = "Карта не загрузилась."; });
  document.body.append(script);
  window.addEventListener("pagehide", () => URL.revokeObjectURL(trailUrl), { once: true });
}

read("parks.json", "json").then(parks => {
  const park = parks.find(p => p.id === queryPark);
  if (park && park.url && !window.PARK_ID) { location.replace(park.url); return; }
  drawHero(park);
  if (park) return renderPark(park);
  renderCatalog(parks);
}).catch(() => {
  const error = getCatalogElement("load-error");
  error.hidden = false;
  error.textContent = "Карта не загрузилась. Попробуйте обновить страницу или вернуться к списку парков.";
});
