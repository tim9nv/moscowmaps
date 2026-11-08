/* Shared pan, zoom and label layout for thematic maps. */
function atlasMapControls(svg, features, projection, parks = []) {
  const node = svg.node();
  const width = node.viewBox.baseVal.width;
  const height = node.viewBox.baseVal.height;
  const container = node.closest('.map');
  container.classList.add('interactive-map');
  const layers = svg.selectAll(':scope > g');
  const labels = [];
  svg.selectAll('.ov-lbl').each(function () {
    labels.push({x: +this.getAttribute('x'), y: +this.getAttribute('y'), text: this.textContent, kind: 'okr', min: 1});
  }).remove();
  svg.selectAll('.plabels').remove();
  features.forEach(feature => {
    const point = projection(d3.geoCentroid(feature));
    if (point && point.every(Number.isFinite)) labels.push({x: point[0], y: point[1], text: feature.properties.n, kind: 'district', min: 2});
  });
  parks.filter(park => park.n && !park.dup).sort((a, b) => b.a - a.a).forEach((park, index) => {
    const point = projection(park.c);
    labels.push({x: point[0], y: point[1], text: park.s || park.n, kind: 'park', min: index < 12 ? 1 : index < 40 ? 1.8 : 3});
  });
  const labelLayer = svg.append('g').attr('class', 'atlas-map-labels').attr('aria-hidden', 'true');
  const text = labelLayer.selectAll('text').data(labels).join('text')
    .attr('class', label => 'atlas-label atlas-label-' + label.kind)
    .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
    .text(label => label.text);
  let transform = d3.zoomIdentity;
  function layoutLabels() {
    const renderedWidth = node.getBoundingClientRect().width;
    if (!renderedWidth) return;
    const scale = Math.max(1, width / renderedWidth * .85);
    const boxes = [];
    text.each(function (label) {
      const candidate = d3.select(this);
      const eligible = transform.k >= label.min && !(label.kind === 'okr' && transform.k >= 2.5);
      if (!eligible) {
        candidate.attr('visibility', 'hidden');
        return;
      }
      const x = transform.applyX(label.x), y = transform.applyY(label.y);
      const size = (label.kind === 'okr' ? 13 : label.kind === 'park' ? 10 : 11) * scale;
      candidate.attr('x', x).attr('y', y).style('font-size', size + 'px');
      const box = this.getBBox();
      const collides = boxes.some(other => box.x < other.x + other.width + 5 && box.x + box.width + 5 > other.x && box.y < other.y + other.height + 4 && box.y + box.height + 4 > other.y);
      const visible = box.x >= 5 && box.x + box.width <= width - 5 && box.y >= 5 && box.y + box.height <= height - 5 && !collides;
      candidate.attr('visibility', visible ? null : 'hidden');
      if (visible) boxes.push(box);
    });
  }
  const zoom = d3.zoom().scaleExtent([1, 8]).extent([[0, 0], [width, height]])
    .translateExtent([[0, 0], [width, height]])
    .filter(event => event.type === 'wheel' ? event.ctrlKey || event.metaKey : event.type === 'touchstart' ? event.touches.length > 1 : !event.button)
    .on('zoom', event => {
      transform = event.transform;
      layers.attr('transform', transform);
      svg.selectAll('.geo-labels').attr('visibility', transform.k >= 2 ? 'hidden' : null);
      svg.selectAll('.sights .sd circle').attr('r', sight => (sight.t === 'a' ? 2.2 : 3.2) / Math.sqrt(transform.k));
      layoutLabels();
    });
  svg.call(zoom).on('dblclick.zoom', null).style('touch-action', 'pan-y');
  const controls = document.createElement('div');
  controls.className = 'atlas-zoom';
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', 'Масштаб карты');
  [['+', 'Приблизить карту', 1.6], ['−', 'Отдалить карту', 1 / 1.6], ['↺', 'Показать всю карту', 0]].forEach(([symbol, label, factor]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = symbol;
    button.setAttribute('aria-label', label);
    button.onclick = () => factor ? svg.call(zoom.scaleBy, factor) : svg.call(zoom.transform, d3.zoomIdentity);
    controls.append(button);
  });
  container.insertBefore(controls, node);
  const hint = document.createElement('p');
  hint.className = 'atlas-zoom-hint';
  hint.textContent = 'Приближайте кнопками или двумя пальцами. При увеличении появятся названия районов и небольших парков.';
  if (!parks.length) hint.textContent = 'Приближайте кнопками или двумя пальцами, чтобы увидеть названия районов.';
  container.insertAdjacentElement('afterend', hint);
  new ResizeObserver(layoutLabels).observe(node);
  document.fonts.ready.then(layoutLabels);
  layoutLabels();
}
