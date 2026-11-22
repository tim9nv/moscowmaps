// Индекс загружается при обращении к поиску, запросы остаются в браузере.
const TYPES = /^(?:улица|ул|проспект|просп|пркт|переулок|пер|проезд|прд|шоссе|ш|набережная|наб|бульвар|бул|бр|площадь|пл|аллея|тупик)$/;
// Сверка адресов Олонецкой: городские документы, Ginfo и адресные точки OSM.
// https://ginfo.ru/ulicy/oloneckaya_ulica/
// https://www.mos.ru/upload/documents/files/1934/Prilojenie_4.pdf
// https://www.mos.ru/upload/documents/files/1430/5_Prilojenie5.pdf
// https://www.mos.ru/upload/documents/files/5045/5_Prilojenie5.pdf
// https://www.mos.ru/upload/documents/files/9380/Tom1Kniga19PrilojenieA.pdf
export const addresses = [{
  name: 'Олонецкая улица',
  districts: {
    ostankinskiy: ['2', '2А', '4', '4А', '6', '14', '14вл1', '14с1', '14с2', '14с3', '24'],
    otradnoe: ['13', '13с1', '15', '15А', '15Б', '15с1', '17', '17А', '19', '21', '21А', '21Ас1',
      '21Ас2', '21Б', '21В', '21с1', '23', '25', '25А', '25Ас1', '25Ас2', '27']
  }
}];
export function normalize(value) {
  return String(value).toLowerCase().replace(/ё/g, 'е')
    .replace(/пр\s*[-–—]\s*(?:кт|т)/g, 'проспект').replace(/пр\s*[-–—]\s*д/g, 'проезд')
    .replace(/б\s*[-–—]\s*р/g, 'бульвар')
    .replace(/(\d+)\s*[-–—]?\s*(?:я|й|ая|ый)(?=\s|$)/g, '$1')
    .replace(/[^а-яa-z0-9]+/g, ' ').trim().split(/\s+/).filter(w => w && !TYPES.test(w)).join(' ');
}

export function streetType(value) {
  const tokens = String(value).toLowerCase().replace(/пр\s*[-–—]\s*(?:кт|т)/g, 'проспект').replace(/пр\s*[-–—]\s*д/g, 'проезд').replace(/б\s*[-–—]\s*р/g, 'бульвар').replace(/[^а-яa-z0-9]+/g, ' ').split(/\s+/);
  const aliases = {улица:'улица',ул:'улица',проспект:'проспект',просп:'проспект',пркт:'проспект',переулок:'переулок',пер:'переулок',проезд:'проезд',прд:'проезд',шоссе:'шоссе',ш:'шоссе',набережная:'набережная',наб:'набережная',бульвар:'бульвар',бул:'бульвар',бр:'бульвар',площадь:'площадь',пл:'площадь',аллея:'аллея',тупик:'тупик'};
  return tokens.map(t => aliases[t]).find(Boolean);
}

export function findStreets(rows, query, limit = 12) {
  const text = normalize(query);
  if (text.length < 2) return [];
  const words = text.split(' '), hits = [], kind = streetType(query);
  for (const row of rows) {
    let rank = Infinity;
    for (const name of [row[0], ...(row[2] || [])]) {
      if (kind && streetType(name) !== kind) continue;
      const n = normalize(name);
      if (!words.every(w => n.includes(w))) continue;
      rank = Math.min(rank, n === text ? 0 : n.startsWith(text) ? 1 : words.every(w => n.split(' ').some(t => t.startsWith(w))) ? 2 : 3);
    }
    if (rank < Infinity) hits.push({row, rank});
  }
  return hits.sort((a, b) => a.rank - b.rank || a.row[0].localeCompare(b.row[0], 'ru')).slice(0, limit).map(h => h.row);
}

export function splitAddress(query) {
  const match = query.trim().toLowerCase().replace(/ё/g, 'е').replace(/^(?:г\.?\s*)?москва\s*,\s*/u, '').match(
    /^(.+?)[\s,]+(?:(?:дом|д|владение|влд?)\.?\s*)?(\d+\s*[а-я]?(?:\s*\/\s*\d+[а-я]?)?(?:[\s,–—-]*(?:корпус|корп|к|строение|стр|с|владение|влд?)\.?\s*\d+[а-я]?)*\s*)$/u);
  if (!match || normalize(match[1]).length < 2) return null;
  const number = match[2].replace(/[\s,.–—-]+/gu, '').replace(/корпус|корп/gu, 'к')
    .replace(/строение|стр/gu, 'с').replace(/владение|влд/gu, 'вл');
  return {street: match[1], number};
}

export function findAddress(index, address) {
  const entry = index.find(street => normalize(street.name) === normalize(address.street)
    && (!streetType(address.street) || streetType(address.street) === streetType(street.name)));
  if (!entry) return null;
  for (const [slug, numbers] of Object.entries(entry.districts)) {
    const number = numbers.find(value => value.toLowerCase() === address.number);
    if (number) return {name: entry.name, slug, number};
  }
  return {name: entry.name};
}

export function findMappedAddresses(index, address) {
  const street = normalize(address.street), kind = streetType(address.street);
  const matches = [];
  for (const [name, aliases, numbers] of index.streets) {
    const districts = numbers[address.number];
    if (!districts || ![name, ...aliases].some(label => normalize(label) === street && (!kind || streetType(label) === kind))) continue;
    for (const id of districts) matches.push({name, slug: index.districts[id][0], number: address.number});
  }
  return matches;
}

export function mount({input, results, features, onFilter, urlForDistrict}) {
  const css = document.createElement('link');
  css.rel = 'stylesheet'; css.href = new URL('./street-search.css?v=20261116', import.meta.url).href;
  if (!document.querySelector('link[data-street-search]')) { css.dataset.streetSearch = ''; document.head.append(css); }
  const controller = new AbortController();
  const districts = features.map(f => f.properties);
  let data = null, pending = null, failed = false, dismissed = false, version = 0, rendering = false;
  let addressData = null, addressPending = null, addressFailed = false;
  const load = () => {
    if (data) return Promise.resolve(data);
    if (!pending) pending = fetch(new URL('./streets.json?v=20261122', import.meta.url))
      .then(r => { if (!r.ok) throw new Error('street index'); return r.json(); })
      .then(d => {
        if (!Array.isArray(d.streets) || !Array.isArray(d.districts)) throw new Error('street index format');
        data = d; failed = false; return d;
      }).catch(() => { failed = true; return null; }).finally(() => { pending = null; });
    return pending;
  };
  const loadAddresses = () => {
    if (addressData) return Promise.resolve();
    if (!addressPending) {
      addressPending = fetch(new URL('./street-addresses.json?v=20261122', import.meta.url))
        .then(r => { if (!r.ok) throw new Error('address index'); return r.json(); })
        .then(index => {
          if (!Array.isArray(index.streets) || !Array.isArray(index.districts)) throw new Error('address index format');
          addressData = index; addressFailed = false;
        })
        .catch(() => { addressFailed = true; }).finally(() => { addressPending = null; });
    }
    return addressPending;
  };
  function link(slug, text, detail) {
    const a = document.createElement('a'); a.href = urlForDistrict(slug);
    const title = document.createElement('span'); title.textContent = text; a.append(title);
    if (detail) { const small = document.createElement('small'); small.textContent = detail; a.append(small); }
    return a;
  }
  function message(text, announce = false) { const p = document.createElement('p'); p.className = 'search-note'; if (announce) p.setAttribute('role', 'status'); p.textContent = text; results.append(p); }
  function group(title) {
    const h = document.createElement('p'); h.className = 'search-group'; h.textContent = title;
    const ul = document.createElement('ul'); results.append(h, ul); return ul;
  }
  const item = (list, child) => { const li = document.createElement('li'); li.append(child); list.append(li); };
  function render() {
    const raw = input.value.trim(), text = normalize(raw);
    const focused = results.contains(document.activeElement) ? {href:document.activeElement.href, text:document.activeElement.textContent} : null;
    const scrollTop = results.scrollTop;
    rendering = true;
    results.replaceChildren();
    if (!raw) { results.hidden = true; onFilter(null); rendering = false; return; }
    const address = splitAddress(raw);
    const checkedHouse = address && findAddress(addresses, address);
    const houses = checkedHouse?.slug ? [checkedHouse] : address && addressData ? findMappedAddresses(addressData, address) : [];
    const districtHits = address ? [] : districts.filter(d => normalize(d.n).includes(text) && text);
    const streets = data && !address ? findStreets(data.streets, raw) : [];
    const slugs = new Set(districtHits.map(d => d.slug));
    if (houses.length) {
      const ul = group(houses.length === 1 ? 'Адрес' : 'Найдено несколько совпадений');
      for (const house of houses) {
        const district = districts.find(d => d.slug === house.slug);
        if (!district) continue;
        slugs.add(house.slug);
        item(ul, link(house.slug, district.n, `${house.name}, ${house.number.toUpperCase()} · ${district.o}`));
      }
    }
    for (const row of streets) for (const id of row[1]) slugs.add(data.districts[id][0]);
    onFilter(slugs);
    if (districtHits.length) {
      const ul = group('Районы');
      for (const d of districtHits.slice(0, 6)) item(ul, link(d.slug, d.n, d.o));
      if (districtHits.length > 6) message('Остальные районы — в списке ниже.');
    }
    if (streets.length) {
      const ul = group('Улицы');
      for (const [name, ids] of streets) {
        const box = document.createElement('div'); box.className = 'street-hit';
        const title = document.createElement('strong'); title.textContent = name; box.append(title);
        if (ids.length > 1) { const hint = document.createElement('small'); hint.textContent = 'Несколько районов — выберите нужный'; box.append(hint); }
        for (const id of ids) { const [slug, district, area] = data.districts[id]; box.append(link(slug, district, area)); }
        item(ul, box);
      }
      if (streets.length === 12) message('Показаны первые 12 улиц. Уточните название, если нужной нет.');
    }
    if ((address && !houses.length && addressFailed) || (!address && failed && text.length >= 2)) {
      message(address ? 'Не удалось загрузить адреса.' : 'Не удалось загрузить улицы. Поиск районов работает.', true);
      const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = 'Попробовать ещё раз';
      retry.onclick = () => { dismissed = false; update(); }; results.append(retry);
    } else if (address && !houses.length) {
      message(addressData ? 'Адрес не найден в индексе. Уточните номер дома или поищите улицу отдельно.' : 'Загружаем адреса…', true);
    } else if (!address && !data && text.length >= 2) message('Загружаем улицы…', true);
    else if (!address && !districtHits.length && !streets.length) message(text.length < 2 ? 'Введите хотя бы две буквы названия.' : 'Ничего не найдено. Уточните название улицы или района.', true);
    const osm = streets.length ? data : houses.length && !checkedHouse?.slug ? addressData : null;
    if (osm) {
      if (streets.length) message('По данным OpenStreetMap; список районов может быть неполным. Уточните номер дома для поиска по адресу.');
      const p = document.createElement('p'); p.className = 'search-source';
      const a = document.createElement('a'); a.href = 'https://www.openstreetmap.org/copyright'; a.textContent = '© OpenStreetMap';
      p.append(a, ` · ${osm.date.split('-').reverse().join('.')}`); results.append(p);
    }
    results.hidden = dismissed;
    if (focused && !dismissed) {
      const target = [...results.querySelectorAll('a,button')].find(a => a.href === focused.href && a.textContent === focused.text);
      if (target) target.focus({preventScroll:true});
    }
    results.scrollTop = scrollTop;
    rendering = false;
  }
  async function update() {
    const current = ++version;
    render();
    const address = splitAddress(input.value);
    if (address && !addressData && !findAddress(addresses, address)?.slug) await loadAddresses();
    else if (!address && normalize(input.value).length >= 2 && !data) await load();
    else return;
    if (current === version && input.isConnected) render();
  }
  input.addEventListener('input', () => { dismissed = false; update(); });
  input.addEventListener('focus', () => { dismissed = false; update(); });
  input.addEventListener('keydown', e => {
    if (e.isComposing) return;
    if (e.key === 'Escape') { dismissed = true; results.hidden = true; }
    if (e.key === 'ArrowDown') { e.preventDefault(); dismissed = false; render(); results.querySelector('a')?.focus(); }
    if (e.key === 'Enter') {
      e.preventDefault();
      const links = [...results.querySelectorAll('li a')];
      const destinations = new Set(links.map(a => a.href));
      if (destinations.size === 1 && (splitAddress(input.value) || data || failed || normalize(input.value).length < 2)) links[0].click();
      else { dismissed = false; update(); }
    }
  });
  results.addEventListener('keydown', e => {
    const links = [...results.querySelectorAll('li a')], index = links.indexOf(document.activeElement);
    if (e.key === 'Escape') { input.focus(); dismissed = true; results.hidden = true; }
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && index >= 0) {
      e.preventDefault();
      const next = index + (e.key === 'ArrowDown' ? 1 : -1);
      if (next < 0) input.focus(); else links[Math.min(next, links.length - 1)]?.focus();
    }
  });
  document.addEventListener('pointerdown', e => {
    if (!input.isConnected) { controller.abort(); return; }
    if (!input.parentElement.contains(e.target)) { dismissed = true; results.hidden = true; }
  }, {signal:controller.signal});
  input.parentElement.addEventListener('focusout', e => {
    if (rendering) return;
    if (!input.parentElement.contains(e.relatedTarget)) { dismissed = true; results.hidden = true; }
  });
  // Индекс подгружается только при фокусе/вводе, не задерживает карту.
  update();
  return () => controller.abort();
}

// Отдельное подключение только на главной. Копия поля сохраняет исходный
// поиск районов при недоступности модуля и снимает старые обработчики при
// включении нового поиска. Большой общий atlas.js не требуется пересобирать.
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  let dispose = null;
  function bootstrap() {
    const original = document.getElementById('q');
    if (!original || original.dataset.streetSearch || typeof F === 'undefined') return;
    dispose?.();
    const wasFocused = document.activeElement === original;
    const earlyQuery = original.value;
    // Восстанавливаем полный список, если пользователь начал вводить
    // название до загрузки модуля и старый поиск уже сократил #dl.
    if (earlyQuery) { original.value = ''; original.dispatchEvent(new Event('input', {bubbles:true})); }
    const input = original.cloneNode(true);
    input.value = earlyQuery;
    input.dataset.streetSearch = 'ready';
    input.placeholder = 'Марьино или Тверская, 15';
    input.setAttribute('aria-controls', 'district-search-results');
    input.setAttribute('aria-describedby', 'district-search-help');
    original.replaceWith(input);
    document.querySelector('label[for="q"]').textContent = 'Найти район, улицу или дом';
    const help = document.createElement('p'); help.className = 'search-help'; help.id = 'district-search-help';
    help.textContent = 'Введите район, улицу или адрес с номером дома. Адреса — по данным OpenStreetMap.';
    const results = document.createElement('div'); results.id = 'district-search-results';
    results.className = 'district-search-results'; results.setAttribute('aria-label', 'Результаты поиска'); results.hidden = true;
    input.after(help, results);
    const districtLinks = [...document.querySelectorAll('#dl .hl a')];
    const supported = new Set(districtLinks.map(a => new URL(a.href).pathname.split('/').filter(Boolean).pop()));
    const onFilter = slugs => {
      let count = 0;
      for (const a of districtLinks) {
        const slug = new URL(a.href).pathname.split('/').filter(Boolean).pop();
        a.hidden = slugs !== null && !slugs.has(slug);
        if (!a.hidden) count++;
      }
      for (const group of document.querySelectorAll('#dl .hl')) {
        group.hidden = ![...group.children].some(a => !a.hidden);
        if (group.previousElementSibling?.matches('.okh')) group.previousElementSibling.hidden = group.hidden;
      }
      document.getElementById('list-count').textContent = input.value.trim() ? count ? `Найдено районов: ${count}` : 'Районы не найдены — проверьте название' : '';
      d3.select('#hm').selectAll('path.d').style('opacity', f => slugs === null || slugs.has(f.properties.slug) ? 1 : .18);
    };
    dispose = mount({input, results, features:F.filter(f => supported.has(f.properties.slug)), onFilter, urlForDistrict:dUrl});
    if (wasFocused) input.focus({preventScroll:true});
  }
  bootstrap();
  window.addEventListener('hashchange', bootstrap);
}
