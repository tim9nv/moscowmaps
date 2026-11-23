
const svgMap = document.getElementById('house-map');
const results = document.getElementById('nearby-results');
const list = document.getElementById('nearby-list');
const status = document.getElementById('nearby-status');
const radiusInput = document.getElementById('nearby-radius');
const legend = document.getElementById('house-legend');
const groups = {
  station: {name: 'Метро, МЦК и МЦД', color: '#589eff'},
  park: {name: 'Парки и скверы', color: '#4dbe89'},
  ecology: {name: 'Объекты экокарты', color: '#f5ad65'}
};
const stationLabels = {metro: 'Метро', mcc: 'МЦК', mcd: 'МЦД'};
let request;
let selected;
let mapLayers;

async function json(name) {
  const response = await fetch(new URL(name, import.meta.url));
  if (!response.ok) throw new Error('Не удалось загрузить данные');
  return response.json();
}

function loadPlaces() {
  request ??= Promise.all([
    json('./nearby-home.json?v=20261123'),
    json('./district-parks.json?v=20261122')
  ]).catch(error => {
    request = undefined;
    throw error;
  });
  return request;
}

function closestBoundary(rings, [lat, lon]) {
  const cos = Math.cos(lat * Math.PI / 180);
  let nearest;
  let best = Infinity;
  for (const ring of rings) {
    for (let i = 0; i < ring.length; i++) {
      const [x, y] = ring[i];
      const [nextX, nextY] = ring[(i + 1) % ring.length];
      const dx = (nextX - x) * cos;
      const dy = nextY - y;
      const length = dx * dx + dy * dy;
      if (!length) continue;
      const ratio = Math.max(0, Math.min(1, ((lon - x) * cos * dx + (lat - y) * dy) / length));
      const target = [y + dy * ratio, x + (nextX - x) * ratio];
      const score = ((target[1] - lon) * cos) ** 2 + (target[0] - lat) ** 2;
      if (score < best) {
        best = score;
        nearest = target;
      }
    }
  }
  return nearest;
}

function nearestDistinct(places, placeKey, limit, meters, home, map) {
  const within = places.map(place => ({...place, distance: map.distance(home, place.point)}))
    .filter(place => place.distance <= meters)
    .sort((a, b) => a.distance - b.distance);
  const keys = new Set();
  return within.filter(place => {
    const key = placeKey(place);
    if (keys.has(key)) return false;
    keys.add(key);
    return true;
  }).slice(0, limit);
}

function aroundHome(index, parks, home, map, meters) {
  const stations = index.stations.map(([lon, lat, kind, name]) => ({
    name, point: [lat, lon], kind, label: stationLabels[kind]
  }));
  const green = parks.flatMap(([name, slug, , rings]) => {
    const point = closestBoundary(rings, home);
    return point ? [{name, point, url: 'parks/' + slug, label: 'Ближайшая граница парка'}] : [];
  });
  const sites = [...index.ecology, neva, ...ECO_ADDITIONAL_SITES].map(site => ({
    name: site.n,
    point: [site.lat, site.lon],
    record: objectRecords[site.n],
    label: site.t === 'market' ? 'Оптовая торговля и логистика' : 'Площадка из экокарты'
  }));
  return {
    station: nearestDistinct(stations, place => place.kind + ':' + place.name, 3, meters, home, map),
    park: nearestDistinct(green, place => place.url, 3, meters, home, map),
    ecology: nearestDistinct(sites, place => place.name, 5, meters, home, map)
  };
}

function distanceLabel(meters) {
  return meters < 1000 ? Math.max(1, Math.round(meters)) + ' м'
    : new Intl.NumberFormat('ru', {maximumFractionDigits: 1}).format(meters / 1000) + ' км';
}

function popupContent(place, kind, home) {
  const content = document.createElement('div');
  const name = document.createElement('strong');
  name.textContent = place.name;
  content.append(name);
  const description = document.createElement('p');
  description.textContent = place.label + ' · ' + distanceLabel(place.distance) + ' по прямой';
  content.append(description);
  if (kind === 'station') {
    const url = new URL('https://yandex.ru/maps/');
    url.searchParams.set('rtext', home.join(',') + '~' + place.point.join(','));
    url.searchParams.set('rtt', 'pd');
    content.append(link('Пеший маршрут в Яндекс Картах', url.href));
  } else if (place.url) {
    content.append(link('Карта и сведения о парке', place.url));
  } else if (place.record) {
    for (const [heading, value] of [['Объект', place.record.status], ['Обращения', place.record.appeal],
      ['Отзывы', place.record.reports], ['Проверки', place.record.check], ['Транспорт', place.record.neighborhood]]) {
      if (!value) continue;
      const paragraph = document.createElement('p');
      paragraph.textContent = heading + ' — ' + value;
      content.append(paragraph);
    }
    const source = place.record.links?.[0];
    if (source) content.append(link(source[0], source[1]));
  }
  return content;
}

function link(text, href) {
  const anchor = document.createElement('a');
  anchor.textContent = text;
  anchor.href = href;
  return anchor;
}

function renderGroup(kind, places, home) {
  const group = groups[kind];
  const section = document.createElement('section');
  section.className = 'nearby-group';
  const heading = document.createElement('h3');
  heading.textContent = group.name;
  section.append(heading);
  if (!places.length) {
    const empty = document.createElement('p');
    empty.className = 'house-note';
    empty.textContent = 'В этом радиусе нет объектов из набора Атласа.';
    section.append(empty);
    return section;
  }
  const items = document.createElement('ul');
  for (const place of places) {
    const marker = L.circleMarker(place.point, {radius: 8, color: '#fff', weight: 2,
      fillColor: group.color, fillOpacity: 1}).bindPopup(popupContent(place, kind, home), {maxHeight: 230});
    mapLayers.addLayer(marker);
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'nearby-item';
    const name = document.createElement('span');
    name.textContent = place.name;
    const distance = document.createElement('small');
    distance.textContent = distanceLabel(place.distance);
    button.append(name, distance);
    button.onclick = () => {
      svgMap.scrollIntoView({block: 'nearest'});
      marker.openPopup();
    };
    item.append(button);
    items.append(item);
  }
  section.append(items);
  return section;
}

async function render() {
  const current = selected;
  if (!current) return;
  const {map, point} = current;
  results.hidden = false;
  status.textContent = 'Подбираем места рядом…';
  list.replaceChildren();
  mapLayers?.clearLayers();
  mapLayers ??= L.layerGroup().addTo(map);
  const meters = Number(radiusInput.value) * 1000;
  try {
    const [index, parks] = await loadPlaces();
    if (current !== selected || meters !== Number(radiusInput.value) * 1000) return;
    const places = aroundHome(index, parks, point, map, meters);
    list.replaceChildren(...Object.entries(places).map(([kind, items]) => renderGroup(kind, items, point)));
    const bounds = L.latLngBounds([point, ...Object.values(places).flat().map(place => place.point)]);
    map.invalidateSize({pan: false});
    map.fitBounds(bounds, {maxZoom: 16, padding: [40, 40], animate: false});
    status.textContent = '';
  } catch {
    if (current === selected) status.textContent = 'Не удалось загрузить места рядом. Выберите радиус или повторите поиск.';
  }
}

for (const group of Object.values(groups)) {
  const item = document.createElement('span');
  const swatch = document.createElement('i');
  swatch.style.setProperty('--swatch', group.color);
  item.append(swatch, group.name);
  legend.append(item);
}

svgMap.addEventListener('atlas-house-selected', event => {
  selected = event.detail;
  render();
});
svgMap.addEventListener('atlas-house-cleared', () => {
  selected = null;
  results.hidden = true;
  mapLayers?.clearLayers();
});
radiusInput.addEventListener('change', render);
