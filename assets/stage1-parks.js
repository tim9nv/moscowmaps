"use strict";
// This asset is loaded only by the two editorial pilots.
(() => {
  const pilot = window.PARK_STAGE1;
  if (!pilot || !((pilot.id === "134" && pilot.slug === "park-otradnoe")
    || (pilot.id === "85" && pilot.slug === "petrovskiy-park")) || !window.L) return;
  // A long cafe description must fit inside the mobile map before Leaflet pans it.
  L.Popup.addInitHook(function () {
    const map = document.getElementById("map");
    const width = map && map.getBoundingClientRect().width || window.innerWidth - 32;
    this.options.maxWidth = Math.max(120, Math.min(300, width - 124));
    this.options.autoPan = true;
    this.options.autoPanPadding = [16, 16];
    // Reserve the upper-left corner for zoom controls, including their focus ring.
    this.options.autoPanPaddingTopLeft = [56, 100];
    this.options.autoPanPaddingBottomRight = [16, 16];
    this.options.keepInView = true;
  });
})();
