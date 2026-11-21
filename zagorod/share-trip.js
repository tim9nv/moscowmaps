(() => {
  const canonical = document.querySelector('link[rel="canonical"]').href;
  const status = document.getElementById('share-trip-status');
  const field = document.getElementById('share-trip-link');
  for (const button of document.querySelectorAll('[data-share-trip]')) {
    button.hidden = false;
    button.addEventListener('click', async () => {
      button.after(status, field);
      status.textContent = '';
      field.hidden = true;
      const url = new URL(canonical);
      url.searchParams.set('utm_source', 'atlas_share');
      url.searchParams.set('utm_medium', 'referral');
      url.searchParams.set('utm_campaign', 'trips_without_car');
      url.hash = button.dataset.shareTrip;
      try {
        if (navigator.share) {
          await navigator.share({ title: button.dataset.shareTitle, url: url.href });
          return;
        }
        await navigator.clipboard.writeText(url.href);
        status.textContent = 'Ссылка скопирована';
      } catch (error) {
        if (error.name === 'AbortError') return;
        field.hidden = false;
        field.value = url.href;
        field.focus();
        field.select();
        status.textContent = 'Скопируйте выделенную ссылку';
      }
    });
  }
})();
