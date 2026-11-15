(function () {
  'use strict';
  const header = document.querySelector('.topbar');
  if (!header) return;
  const update = () => document.documentElement.style.setProperty(
    '--zg-anchor-offset', Math.ceil(header.getBoundingClientRect().height + 20) + 'px');
  update();
  if ('ResizeObserver' in window) new ResizeObserver(update).observe(header);
  else window.addEventListener('resize', update);
})();
