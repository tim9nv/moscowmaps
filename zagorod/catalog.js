(function () {
  'use strict';
  const grid = document.querySelector('.zc-grid');
  const search = document.getElementById('zc-search');
  if (!grid || !search) return;
  const cards = Array.from(grid.querySelectorAll('.zc'));
  const buttons = Array.from(document.querySelectorAll('.zs-f'));
  const distances = Array.from(document.querySelectorAll('.zc-d'));
  const reset = document.getElementById('zc-reset');
  const sort = document.getElementById('zc-sort');
  const enabled = new Set(cards.map(c => c.dataset.t));
  const types = new Set(enabled);
  const normalize = text => text.toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const texts = new Map(cards.map(c => [c, normalize(c.textContent)]));
  const share = document.getElementById('zc-share');
  const shareStatus = document.getElementById('zc-share-status');
  const shareUrl = document.getElementById('zc-share-url');
  let range = 'all';

  function selectionUrl() {
    const url = new URL(location.href);
    ['q', 'types', 'distance', 'sort'].forEach(key => url.searchParams.delete(key));
    if (search.value.trim()) url.searchParams.set('q', search.value.trim());
    if (enabled.size !== types.size) url.searchParams.set('types', Array.from(types).filter(type => enabled.has(type)).join(','));
    if (range !== 'all') url.searchParams.set('distance', range);
    if (sort.value !== 'km') url.searchParams.set('sort', sort.value);
    return url;
  }
  function save() {
    try { history.replaceState(history.state, '', selectionUrl()); } catch (_) { /* Фильтры работают и без History API. */ }
  }
  function restore() {
    const params = new URL(location.href).searchParams;
    search.value = params.get('q') || '';
    enabled.clear();
    const selected = params.has('types') ? params.get('types').split(',') : Array.from(types);
    selected.filter(type => types.has(type)).forEach(type => enabled.add(type));
    range = distances.some(button => button.dataset.r === params.get('distance')) ? params.get('distance') : 'all';
    sort.value = params.get('sort') === 'n' ? 'n' : 'km';
    reorder(false);
  }

  function update(persist = true) {
    const words = normalize(search.value).split(' ').filter(Boolean);
    let count = 0;
    const visible = new Set();
    cards.forEach(card => {
      const km = Number(card.dataset.km);
      const within = range === 'all' || (km >= Number(range.split('-')[0]) && km < Number(range.split('-')[1]));
      const show = within && enabled.has(card.dataset.t) && words.every(word => texts.get(card).includes(word));
      card.hidden = !show;
      if (show) { count++; visible.add(card.getAttribute('href')); }
    });
    document.dispatchEvent(new CustomEvent('zagorod:filter', { detail: Array.from(visible) }));
    buttons.forEach(button => button.setAttribute('aria-pressed', String(enabled.has(button.dataset.t))));
    distances.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.r === range)));
    document.getElementById('zc-n').textContent = count;
    document.querySelector('.zc-empty').hidden = count > 0;
    reset.hidden = !search.value && range === 'all' && enabled.size === types.size && sort.value === 'km';
    if (shareStatus) shareStatus.textContent = '';
    if (shareUrl) shareUrl.hidden = true;
    if (persist) save();
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    const type = button.dataset.t;
    if (enabled.has(type)) enabled.delete(type); else enabled.add(type);
    update();
  }));
  distances.forEach(button => button.addEventListener('click', () => { range = button.dataset.r; update(); }));
  search.addEventListener('input', () => update());
  function reorder(persist = true) {
    cards.slice().sort((a, b) => sort.value === 'n'
      ? a.dataset.n.localeCompare(b.dataset.n, 'ru')
      : Number(a.dataset.km) - Number(b.dataset.km)).forEach(card => grid.appendChild(card));
    update(persist);
  }
  sort.addEventListener('change', () => reorder());
  reset.addEventListener('click', () => {
    search.value = ''; range = 'all'; sort.value = 'km';
    types.forEach(type => enabled.add(type));
    reorder(); search.focus();
  });
  // Сохраняем выбор перед переходом и при уходе со страницы.
  document.addEventListener('click', event => { if (event.target.closest('a[href]')) save(); }, true);
  addEventListener('pagehide', save);
  addEventListener('popstate', restore);
  addEventListener('pageshow', restore);
  if (share) {
    share.hidden = false;
    share.addEventListener('click', async () => {
      save();
      const url = selectionUrl(); url.hash = 'all';
      try {
        await navigator.clipboard.writeText(url.href);
        shareStatus.textContent = 'Ссылка скопирована — выбранные фильтры сохранятся.';
      } catch (_) {
        shareUrl.value = url.href; shareUrl.hidden = false; shareUrl.focus(); shareUrl.select();
        shareStatus.textContent = 'Скопируйте выделенную ссылку.';
      }
    });
  }
  restore();
})();
