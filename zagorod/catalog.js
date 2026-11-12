(function () {
  'use strict';
  const grid = document.querySelector('.zc-grid');
  const search = document.getElementById('zc-search');
  if (!grid || !search) return;
  const cards = Array.from(grid.querySelectorAll('.zc'));
  const buttons = Array.from(document.querySelectorAll('.zs-f'));
  const distances = Array.from(document.querySelectorAll('.zc-d'));
  const points = Array.from(document.querySelectorAll('.zp'));
  const reset = document.getElementById('zc-reset');
  const sort = document.getElementById('zc-sort');
  const enabled = new Set(cards.map(c => c.dataset.t));
  const types = new Set(enabled);
  const normalize = text => text.toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const texts = new Map(cards.map(c => [c, normalize(c.textContent)]));
  let range = 'all';

  function update() {
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
    points.forEach(point => point.classList.toggle('off', !visible.has(point.getAttribute('href'))));
    buttons.forEach(button => button.setAttribute('aria-pressed', String(enabled.has(button.dataset.t))));
    distances.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.r === range)));
    document.getElementById('zc-n').textContent = count;
    document.querySelector('.zc-empty').hidden = count > 0;
    reset.hidden = !search.value && range === 'all' && enabled.size === types.size && sort.value === 'km';
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    const type = button.dataset.t;
    if (enabled.has(type)) enabled.delete(type); else enabled.add(type);
    update();
  }));
  distances.forEach(button => button.addEventListener('click', () => { range = button.dataset.r; update(); }));
  search.addEventListener('input', update);
  function reorder() {
    cards.slice().sort((a, b) => sort.value === 'n'
      ? a.dataset.n.localeCompare(b.dataset.n, 'ru')
      : Number(a.dataset.km) - Number(b.dataset.km)).forEach(card => grid.appendChild(card));
    update();
  }
  sort.addEventListener('change', reorder);
  reset.addEventListener('click', () => {
    search.value = ''; range = 'all'; sort.value = 'km';
    types.forEach(type => enabled.add(type));
    reorder(); search.focus();
  });
  update();
})();
