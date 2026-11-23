const svgMap = document.getElementById('house-map');
const results = document.getElementById('nearby-results');
const list = document.getElementById('nearby-list');
const status = document.getElementById('nearby-status');
const filters = document.getElementById('nearby-filters');
const category = document.getElementById('nearby-category');
const serviceSource = document.getElementById('nearby-service-source');
const method = document.getElementById('nearby-method');
const ecologyNote = document.getElementById('nearby-eco-note');
const radiusInput = document.getElementById('nearby-radius');
const legend = document.getElementById('house-legend');
const groups = {
  station: {name: 'Метро, МЦК и МЦД', color: '#589eff'},
  park: {name: 'Парки и скверы', color: '#4dbe89'},
  ecology: {name: 'Объекты экокарты', color: '#f5ad65'}
};
const services = {
  schools: {name: 'Школы', color: '#b59aff', label: 'Школа'},
  kindergartens: {name: 'Детские сады', color: '#f5ad65', label: 'Детский сад'},
  clinics: {name: 'Клиники и больницы', color: '#66d6e7', label: 'Клиника или больница'}
};
const stationLabels = {metro: 'Метро', mcc: 'МЦК', mcd: 'МЦД'};
let request;
let serviceRequest;
let renderSequence = 0;
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

function loadServices() {
  serviceRequest ??= json('./nearby-services.json?v=20261123').catch(error => {
    serviceRequest = undefined;
    throw error;
  });
  return serviceRequest;
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

function walkingRoute(home, destination) {
  const url = new URL('https://yandex.ru/maps/');
  url.searchParams.set('rtext', home.join(',') + '~' + destination.join(','));
  url.searchParams.set('rtt', 'pd');
  return url.href;
}

function popupContent(place, kind, home) {
  const content = document.createElement('div');
  const name = document.createElement('strong');
  name.textContent = place.name;
  content.append(name);
  const description = document.createElement('p');
  description.textContent = place.label + ' · ' + distanceLabel(place.distance) + ' по прямой';
  content.append(description);
  if (place.address) {
    const address = document.createElement('p');
    address.textContent = place.address;
    content.append(address);
  }
  if (kind === 'station' || services[kind]) {
    content.append(link('Пеший маршрут в Яндекс Картах', walkingRoute(home, place.point)));
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
  const group = groups[kind] || services[kind];
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
    if (place.address) {
      const address = document.createElement('small');
      address.textContent = place.address;
      name.append(address);
    }
    const distance = document.createElement('small');
    distance.textContent = distanceLabel(place.distance);
    button.append(name, distance);
    button.onclick = () => {
      svgMap.scrollIntoView({block: 'nearest'});
      marker.openPopup();
    };
    item.append(button);
    if (kind === 'station' || services[kind]) {
      const action = link('Пеший маршрут', walkingRoute(home, place.point));
      action.className = 'nearby-action';
      action.setAttribute('aria-label', 'Пеший маршрут: ' + place.name);
      item.append(action);
    }
    items.append(item);
  }
  section.append(items);
  return section;
}

function setLegend(view) {
  const entries = services[view] ? [services[view]] : Object.values(groups);
  const items = entries.map(group => {
    const item = document.createElement('span');
    const swatch = document.createElement('i');
    swatch.style.setProperty('--swatch', group.color);
    swatch.setAttribute('aria-hidden', 'true');
    item.append(swatch, group.name);
    return item;
  });
  legend.replaceChildren(...items);
}

async function render() {
  const current = selected;
  if (!current) return;
  const run = ++renderSequence;
  const {map, point} = current;
  const view = category.value;
  filters.hidden = false;
  results.hidden = false;
  serviceSource.hidden = true;
  ecologyNote.hidden = view !== 'overview';
  method.textContent = view === 'overview'
    ? 'Расстояния по прямой. Для парков показана ближайшая граница.'
    : 'Расстояния по прямой. По ссылке можно построить пеший маршрут в Яндекс Картах.';
  status.textContent = 'Подбираем места рядом…';
  list.replaceChildren();
  mapLayers?.clearLayers();
  mapLayers ??= L.layerGroup().addTo(map);
  const meters = Number(radiusInput.value) * 1000;
  setLegend(view);
  try {
    let places;
    if (services[view]) {
      const data = await loadServices();
      if (run !== renderSequence) return;
      const candidates = data[view].map(([lon, lat, name, address]) => ({
        name, address, label: services[view].label, point: [lat, lon]
      }));
      places = {[view]: nearestDistinct(candidates,
        place => (place.address ? place.name + ':' + place.address : place.name + ':' + place.point.join(',')),
        5, meters, point, map)};
      serviceSource.textContent = 'Источник: OpenStreetMap, для Отрадного — сверенные городские списки. Набор для 125 районов сформирован ' +
        data.dates.join(', ') + '. Список может быть неполным. В нём есть частные учреждения.';
      serviceSource.hidden = false;
    } else {
      const [index, parks] = await loadPlaces();
      if (run !== renderSequence) return;
      places = aroundHome(index, parks, point, map, meters);
    }
    list.replaceChildren(...Object.entries(places).map(([kind, items]) => renderGroup(kind, items, point)));
    const bounds = L.latLngBounds([point, ...Object.values(places).flat().map(place => place.point)]);
    map.invalidateSize({pan: false});
    map.fitBounds(bounds, {maxZoom: 16, padding: [40, 40], animate: false});
    status.textContent = '';
  } catch {
    if (run === renderSequence) status.textContent = 'Не удалось загрузить места рядом. Переключите категорию или повторите поиск.';
  }
}

setLegend(category.value);

svgMap.addEventListener('atlas-house-selected', event => {
  selected = event.detail;
  render();
});
svgMap.addEventListener('atlas-house-cleared', () => {
  selected = null;
  renderSequence++;
  filters.hidden = true;
  results.hidden = true;
  mapLayers?.clearLayers();
});
radiusInput.addEventListener('change', render);
category.addEventListener('change', render);
