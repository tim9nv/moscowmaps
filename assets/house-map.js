import {normalize, splitAddress, streetType} from './street-search.js?v=20261122-house-map';

const ui = Object.fromEntries(['search', 'address', 'status', 'matches', 'card', 'title', 'year',
  'detail', 'source', 'district', 'map', 'reset', 'legend', 'close'].map(name =>
  [name, document.getElementById('house-' + name)]));
const neighborhoodMode = ui.map.hasAttribute('data-neighborhood');
const periods = [[1956, 'до 1957', '#b08cff'], [1968, '1957–1968', '#f2a65a'],
  [1980, '1969–1980', '#e8e08a'], [1991, '1981–1991', '#9fd8a0'],
  [2010, '1992–2010', '#5cc8d6'], [Infinity, 'с 2011', '#ff7fb0']];
const unknown = '#69779c';
const assets = new URL('./house-map/', import.meta.url);
const zoomForHouses = 16;
const tileCache = new Map();
let sequence = 0;
let visibleRun = 0;
let selected = null;
let review;
let map, info, layer, highlight, choiceMarkers, available;
const nearby = new Map();

function json(url) {
  return fetch(url).then(response => {
    if (!response.ok) throw new Error('Не удалось загрузить данные');
    return response.json();
  });
}

function data(name) {
  return json(new URL(name + '.json?v=20261122', assets));
}

function getTile(cell) {
  let request = tileCache.get(cell);
  if (!request) {
    request = data('t' + cell).catch(error => {
      tileCache.delete(cell);
      throw error;
    });
  }
  tileCache.delete(cell);
  tileCache.set(cell, request);
  if (tileCache.size > 80) tileCache.delete(tileCache.keys().next().value);
  return request;
}

function sortedWords(street) {
  return normalize(street).split(' ').sort().join(' ');
}

function bucket(street) {
  let hash = 0;
  for (const char of sortedWords(street)) hash = (hash * 31 + char.charCodeAt(0)) % 128;
  return hash;
}

function formatNumber(number) {
  return number.replace(/(\d)(вл|к|с)(?=\d)/g, '$1 $2. ');
}

function label(name, number) {
  return name + ', ' + formatNumber(number);
}

function displayAddress(raw) {
  const query = raw.replace(/(зеленоград[ ,]+)(?:корпус|корп|к)\.?\s*(?=\d)/i, '$1');
  return splitAddress(query);
}

function decode(encoded) {
  return encoded.map(polygon => polygon.map(ring => {
    let lon = 0;
    let lat = 0;
    const points = [];
    for (let i = 0; i < ring.length; i += 2) {
      lon += ring[i];
      lat += ring[i + 1];
      points.push([lat / 100000, lon / 100000]);
    }
    return points;
  }));
}

function houseShape(feature, options) {
  return L.polygon(decode(feature[1]), options);
}

function clearSelection() {
  selected = null;
  highlight.clearLayers();
  ui.card.hidden = true;
  if (neighborhoodMode) ui.map.dispatchEvent(new Event('atlas-house-cleared'));
}

function clearChoices() {
  ui.matches.replaceChildren();
  ui.matches.hidden = true;
  choiceMarkers.clearLayers();
}

function showCard(feature, title, districtId, point) {
  const current = {};
  selected = current;
  highlight.clearLayers();
  const [slug, district] = info.districts[districtId];
  const year = feature?.[2];
  const floors = feature?.[3];
  const citation = feature?.[4];
  const details = [district, floors ? 'Этажей: ' + floors : '', !feature ? 'Адресная точка' : ''].filter(Boolean);
  ui.title.textContent = title;
  ui.year.textContent = year ? 'Год постройки ' + year : 'Год постройки неизвестен';
  ui.detail.textContent = details.join(' · ');
  ui.source.hidden = !year;
  ui.source.textContent = citation < 0 ? 'Поадресная сверка' : citation > 0 ? 'Дом.МинЖКХ' : 'OpenStreetMap';
  ui.source.href = citation ? 'https://dom.mingkh.ru/moskva/' : 'https://www.openstreetmap.org/copyright';
  ui.district.hidden = !slug;
  if (slug) ui.district.href = 'rayon/' + slug + '/#dm';
  ui.card.hidden = false;
  map.invalidateSize({pan: false});
  const shape = feature
    ? houseShape(feature, {pane: 'house-selection', color: '#fff', weight: 3, fillColor: '#ffd86b', fillOpacity: .88, interactive: false})
    : L.circleMarker(point, {pane: 'house-selection', radius: 10, color: '#fff', weight: 3, fillColor: '#ffd86b', fillOpacity: 1, interactive: false});
  highlight.addLayer(shape);
  if (neighborhoodMode) {
    ui.map.dispatchEvent(new CustomEvent('atlas-house-selected', {detail: {map, point}}));
  }
  if (citation < 0) {
    review ??= json(new URL('../tools/data/house_year_review.json?v=20261122-house-tap', import.meta.url)).catch(() => null);
    review.then(records => {
      const record = records?.[-citation];
      if (selected !== current || !record) return;
      if (record.reconstruction_year) ui.detail.textContent = [...details, 'Реконструкция ' + record.reconstruction_year].join(' · ');
      const source = record.sources?.find(url => url.startsWith('https://dompassport.ru/'))
        || record.sources?.find(url => url.startsWith('https://'));
      if (source) ui.source.href = source;
    });
  }
}

async function openResult(result) {
  const request = ++sequence;
  const {name, number, hit} = result;
  const [lat, lon, districtId, cell, featureId] = hit;
  clearChoices();
  ui.status.textContent = cell ? 'Загружаем контур дома…' : '';
  let feature;
  if (cell) {
    try {
      feature = (await getTile(cell)).find(row => row[0] === featureId);
    } catch {
      if (!neighborhoodMode) {
        if (request === sequence) ui.status.textContent = 'Не удалось загрузить контур. Повторите поиск.';
        return;
      }
    }
  }
  if (request !== sequence) return;
  ui.status.textContent = '';
  ui.address.value = label(name, number);
  map.setView([lat, lon], 18, {animate: false});
  showCard(feature, ui.address.value, districtId, [lat, lon]);
}

function choices(results, message = 'Найдено несколько совпадений. Выберите адрес.') {
  ui.status.textContent = message;
  const positions = [];
  for (const [index, result] of results.entries()) {
    const position = result.hit.slice(0, 2);
    positions.push(position);
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const district = document.createElement('small');
    district.textContent = info.districts[result.hit[2]][1];
    if (!result.hit[3]) district.textContent += ' · адресная точка';
    button.append((index + 1) + '. ' + label(result.name, result.number), district);
    button.onclick = () => openResult(result);
    item.append(button);
    ui.matches.append(item);
    L.marker(position, {
      icon: L.divIcon({className: 'house-choice-marker', html: String(index + 1), iconSize: [28, 28]}),
      title: button.textContent
    }).on('click', button.onclick).addTo(choiceMarkers);
  }
  ui.matches.hidden = false;
  map.invalidateSize({pan: false});
  map.fitBounds(positions, {padding: [35, 35], maxZoom: 17, animate: false});
  ui.matches.querySelector('button').focus({preventScroll: true});
}

async function search(event) {
  event.preventDefault();
  if (!info) return;
  const request = ++sequence;
  clearSelection();
  clearChoices();
  const address = displayAddress(ui.address.value.trim());
  if (!address) {
    ui.status.textContent = 'Введите название улицы и номер дома.';
    return;
  }
  ui.address.blur();
  ui.status.textContent = 'Ищем адрес…';
  try {
    const rows = await data('a' + bucket(address.street));
    if (request !== sequence) return;
    const key = sortedWords(address.street);
    const type = streetType(address.street);
    const found = new Map();
    const variants = new Map();
    const collect = (target, name, number, hits) => {
      for (const hit of hits) {
        const id = hit[4] || hit.slice(0, 2).join(',');
        if (!target.has(id)) target.set(id, {name, number, hit});
      }
    };
    for (const [name, alias, numbers] of rows) {
      const kind = streetType(alias) || streetType(name);
      if (sortedWords(alias) !== key || (type && kind && type !== kind)) continue;
      collect(found, name, address.number, numbers[address.number] || []);
      if (/^\d+$/.test(address.number)) {
        for (const [number, hits] of Object.entries(numbers)) {
          if (number.startsWith(address.number) && /^[а-я]/.test(number.slice(address.number.length))) {
            collect(variants, name, number, hits);
          }
        }
      }
    }
    const results = [...found.values()];
    if (results.length === 1) openResult(results[0]);
    else if (results.length) choices(results);
    else if (variants.size) {
      const ordered = [...variants.values()].sort((a, b) => a.number.localeCompare(b.number, 'ru', {numeric: true}));
      choices(ordered, 'Точного совпадения нет. Выберите корпус, строение или номер с буквой.');
    } else ui.status.textContent = 'Адрес не найден. Проверьте улицу, номер, корпус или строение.';
  } catch {
    if (request === sequence) ui.status.textContent = 'Не удалось загрузить адреса. Повторите поиск.';
  }
}

function cellAt(location) {
  const pixel = map.project(location, info.zoom);
  return [Math.floor(pixel.x / 256), Math.floor(pixel.y / 256)];
}

async function drawVisible() {
  const run = ++visibleRun;
  if (map.getZoom() < zoomForHouses) {
    layer.clearLayers();
    nearby.clear();
    return;
  }
  const bounds = map.getBounds();
  const [left, top] = cellAt(bounds.getNorthWest());
  const [right, bottom] = cellAt(bounds.getSouthEast());
  const cells = [];
  for (let x = left; x <= right; x++) {
    for (let y = top; y <= bottom; y++) {
      const cell = x + '-' + y;
      if (available.has(cell)) cells.push(getTile(cell));
    }
  }
  const responses = await Promise.allSettled(cells);
  if (run !== visibleRun) return;
  const features = new Map();
  for (const result of responses) {
    if (result.status === 'fulfilled') for (const row of result.value) features.set(row[0], row);
  }
  for (const [id, polygon] of nearby) {
    if (features.has(id)) continue;
    layer.removeLayer(polygon);
    nearby.delete(id);
  }
  for (const [id, row] of features) {
    if (nearby.has(id)) continue;
    const color = row[2] ? periods.find(period => row[2] <= period[0])[2] : unknown;
    const polygon = houseShape(row, {color: '#263656', weight: 1, fillColor: color, fillOpacity: .78});
    polygon.on('click', () => {
      sequence++;
      clearChoices();
      ui.status.textContent = '';
      const names = row[5].map(([name, number]) => label(name, number));
      showCard(row, names.join(' · ') || 'Дом на карте', row[6]);
    });
    layer.addLayer(polygon);
    nearby.set(id, polygon);
  }
}

function legend() {
  for (const [, title, color] of [...periods, [0, 'год неизвестен', unknown]]) {
    const item = document.createElement('span');
    const swatch = document.createElement('i');
    swatch.style.setProperty('--swatch', color);
    swatch.setAttribute('aria-hidden', 'true');
    item.append(swatch, title);
    ui.legend.append(item);
  }
}

function init(index) {
  info = index;
  available = new Set(info.tiles);
  map = L.map(ui.map, {zoomControl: false, scrollWheelZoom: false, touchZoom: true, zoomAnimation: false, minZoom: 8, maxZoom: 20});
  L.control.zoom({zoomInTitle: 'Приблизить', zoomOutTitle: 'Отдалить'}).addTo(map);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxNativeZoom: 19, maxZoom: 20
  }).addTo(map);
  L.control.scale({imperial: false}).addTo(map);
  const selectionPane = map.createPane('house-selection');
  selectionPane.style.zIndex = '450';
  selectionPane.style.pointerEvents = 'none';
  const boundary = L.geoJSON(info.boundary, {color: '#9ab4eb', weight: 2, fillOpacity: 0, interactive: false}).addTo(map);
  layer = L.layerGroup().addTo(map);
  map.options.renderer = L.canvas({padding: .25});
  highlight = L.layerGroup().addTo(map);
  choiceMarkers = L.layerGroup().addTo(map);
  ui.close.onclick = clearSelection;
  ui.card.addEventListener('keydown', event => { if (event.key === 'Escape') clearSelection(); });
  const reset = () => map.fitBounds(boundary.getBounds(), {padding: [14, 14], animate: false});
  reset();
  if (!neighborhoodMode) map.on('moveend', drawVisible);
  ui.reset.disabled = false;
  ui.reset.onclick = () => {
    sequence++;
    ui.status.textContent = '';
    ui.address.value = '';
    clearChoices();
    clearSelection();
    reset();
  };
  ui.status.textContent = '';
  ui.search.addEventListener('submit', search);
  ui.address.addEventListener('input', () => {
    sequence++;
    clearChoices();
    ui.status.textContent = '';
  });
  if (!neighborhoodMode) legend();
}

ui.search.addEventListener('submit', event => event.preventDefault());
ui.status.textContent = 'Загружаем карту…';
data('index').then(index => {
  if (!window.L) throw new Error('Leaflet');
  init(index);
}).catch(() => {
  ui.status.textContent = 'Не удалось загрузить карту. Обновите страницу.';
});
