// chart.js: hover values and drag-to-zoom for the charts on a batch page.
//
// HOW IT FITS TOGETHER
//   The server (ui.py, svg_chart) has already drawn each chart as a picture, and attached the
//   same readings to it as text in a `data-chart` attribute. This script reads that text and
//   takes over the drawing, so it can redraw whenever the mouse moves or a zoom is chosen.
//   If JavaScript is off, this file simply never runs and the server's picture stays.
//   It uses no libraries and loads nothing from the internet.
//
// THE IDEA
//   There are three pieces of "state" shared by every chart on the page:
//       range   the stretch of time currently shown   [start, end]
//       cursor  the time under the mouse pointer      (or null)
//       drag    a zoom selection in progress          (or null)
//   Every mouse event changes that state and then redraws ALL the charts from it. Because the
//   state is shared, gravity, pH and temperature always show the same time window and the
//   cursor lines up across them.
//
// The whole file is wrapped in (() => { ... })() so its names stay private to this file.
(() => {
  // The drawing area, in the same units ui.py uses: 640 wide, 220 tall, with margins
  // Left, Right, Top and Bottom leaving room for the axis labels.
  const W = 640, H = 220, L = 52, R = 8, T = 10, B = 22;

  // Find every chart on the page and decode its data.
  // Each entry: { el: the chart's HTML element, data: { digits, series: [{label, color, points}] } }
  // A point is [time in seconds since 1970, value].
  const plots = [...document.querySelectorAll('.plot[data-chart]')].map(el => ({ el, data: JSON.parse(el.dataset.chart) }));
  if (!plots.length) return;   // no charts on this page: nothing to do

  // The full time range: the earliest and latest reading across every chart.
  let t0 = Infinity, t1 = -Infinity;
  for (const p of plots) for (const s of p.data.series) for (const [t] of s.points) { if (t < t0) t0 = t; if (t > t1) t1 = t; }
  const full = [t0, t1];

  // The shared state described above.
  let range = full.slice(), cursor = null, drag = null;

  // --- small helpers ----------------------------------------------------------------------------
  // A time as text in the viewer's own time zone, e.g. "Nov 12, 02:30 PM".
  const time = t => new Date(t * 1000).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  // Time -> horizontal position: where in the current range, stretched across the plot width.
  const x = t => L + (t - range[0]) / ((range[1] - range[0]) || 1) * (W - L - R);
  // The reverse: horizontal position -> time. The position is first kept inside the plot area.
  const tAt = px => range[0] + (Math.min(W - R, Math.max(L, px)) - L) / (W - L - R) * (range[1] - range[0]);
  // Make text safe to place inside HTML (a device name could contain < or &).
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Find the reading closest in time to `t`.
  // The points are in time order, so this uses a binary search: look at the middle point,
  // throw away the half that can't contain the answer, repeat. For 2000 points that takes
  // about 11 steps instead of 2000.
  function nearest(points, t) {
    let lo = 0, hi = points.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (points[mid][0] < t) lo = mid; else hi = mid; }
    return Math.abs(points[lo][0] - t) <= Math.abs(points[hi][0] - t) ? points[lo] : points[hi];
  }

  // --- drawing one chart from the current state ----------------------------------------------
  function draw(p) {
    // Keep only the readings inside the visible time range.
    const visible = p.data.series.map(s => s.points.filter(pt => pt[0] >= range[0] && pt[0] <= range[1]));

    // Lowest and highest visible value: the vertical scale adjusts to what is on screen,
    // so zooming in on a flat stretch still shows detail.
    let lo = Infinity, hi = -Infinity;
    for (const pts of visible) for (const [, v] of pts) { if (v < lo) lo = v; if (v > hi) hi = v; }

    let svg = `<svg viewBox="0 0 ${W} ${H}">`;
    if (lo === Infinity) {
      svg += `<text class="tick" x="${W / 2}" y="${H / 2}" text-anchor="middle">No readings in this range</text>`;
    } else {
      // A little space above and below; the `||` chain handles a perfectly flat line.
      const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.01 || 1;
      lo -= pad; hi += pad;
      // Value -> vertical position. SVG counts downward, so a high value gets a small y.
      const y = v => T + (hi - v) / (hi - lo) * (H - T - B);

      // Five horizontal grid lines with their values.
      for (let i = 0; i < 5; i++) {
        const v = lo + (hi - lo) * i / 4;
        svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>` +
               `<text class="tick" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v.toFixed(p.data.digits)}</text>`;
      }
      // The start and end of the visible time range.
      svg += `<text class="tick" x="${L}" y="${H - 5}">${esc(time(range[0]))}</text>` +
             `<text class="tick" x="${W - R}" y="${H - 5}" text-anchor="end">${esc(time(range[1]))}</text>`;

      // One line per device (a dot if there is only a single reading).
      p.data.series.forEach((s, i) => {
        const pts = visible[i];
        if (pts.length === 1) svg += `<circle cx="${x(pts[0][0]).toFixed(1)}" cy="${y(pts[0][1]).toFixed(1)}" r="3" fill="${s.color}"/>`;
        else if (pts.length) svg += `<polyline fill="none" stroke="${s.color}" stroke-width="2" points="${pts.map(pt => x(pt[0]).toFixed(1) + ',' + y(pt[1]).toFixed(1)).join(' ')}"/>`;
      });

      // The hover cursor: a dashed vertical line, and a dot on each line at the nearest reading.
      if (cursor !== null && !drag) {
        svg += `<line class="cursor" x1="${x(cursor).toFixed(1)}" x2="${x(cursor).toFixed(1)}" y1="${T}" y2="${H - B}"/>`;
        p.data.series.forEach((s, i) => {
          if (!visible[i].length) return;
          const pt = nearest(visible[i], cursor);
          svg += `<circle cx="${x(pt[0]).toFixed(1)}" cy="${y(pt[1]).toFixed(1)}" r="4" fill="${s.color}" stroke="var(--surface)" stroke-width="1.5"/>`;
        });
      }
    }
    // The shaded box showing the stretch being selected for zoom.
    if (drag) {
      const a = Math.min(drag.from, drag.to), b = Math.max(drag.from, drag.to);
      svg += `<rect class="select" x="${a.toFixed(1)}" y="${T}" width="${(b - a).toFixed(1)}" height="${H - T - B}"/>`;
    }
    p.canvas.innerHTML = svg + '</svg>';

    // The line of text under the chart: the time and each device's value at the cursor.
    if (cursor !== null && !drag) {
      const parts = p.data.series.map((s, i) => visible[i].length
        ? `<span><i style="background:${s.color}"></i>${esc(s.label)} <b>${nearest(visible[i], cursor)[1].toFixed(p.data.digits)}</b></span>` : '');
      p.tip.innerHTML = `<span>${esc(time(cursor))}</span>` + parts.join('');
    } else {
      p.tip.textContent = 'Hover for values. Drag across to zoom.';
    }
    // Show the "Reset zoom" button only while zoomed in.
    p.reset.hidden = range[0] === full[0] && range[1] === full[1];
  }
  const drawAll = () => plots.forEach(draw);

  // --- setting up each chart and listening for the mouse (or a finger) -------------------------
  for (const p of plots) {
    // Replace the server's picture with an empty drawing area, a text line and a reset button.
    p.el.innerHTML = '<div class="canvas"></div><div class="tipbar"><div class="tip"></div><button type="button" class="reset" hidden>Reset zoom</button></div>';
    p.canvas = p.el.querySelector('.canvas');
    p.tip = p.el.querySelector('.tip');
    p.reset = p.el.querySelector('.reset');

    // Convert a pointer's screen position into the chart's 0..640 units. The chart is stretched
    // to fit the page, so its on-screen width is measured each time.
    const px = e => { const r = p.canvas.getBoundingClientRect(); return (e.clientX - r.left) / r.width * W; };

    // "Pointer" events cover a mouse, a finger and a stylus with one set of code.
    // Button or finger goes down: start a zoom selection at this position.
    p.canvas.addEventListener('pointerdown', e => {
      drag = { from: Math.min(W - R, Math.max(L, px(e))), to: px(e) };
      p.canvas.setPointerCapture(e.pointerId);   // keep receiving movement even if the pointer leaves the chart
    });
    // Pointer moves: the cursor follows it, and a selection in progress stretches to it.
    p.canvas.addEventListener('pointermove', e => {
      cursor = tAt(px(e));
      if (drag) drag.to = Math.min(W - R, Math.max(L, px(e)));
      drawAll();
    });
    // Released: if it moved more than 8 units it was a drag, so zoom to the selected stretch.
    // Less than that was just a click, and is ignored.
    p.canvas.addEventListener('pointerup', () => {
      if (drag && Math.abs(drag.to - drag.from) > 8) range = [tAt(drag.from), tAt(drag.to)].sort((a, b) => a - b);
      drag = null;
      drawAll();
    });
    // The browser took the gesture over (for example to scroll the page): abandon the selection.
    p.canvas.addEventListener('pointercancel', () => { drag = null; drawAll(); });
    // Pointer left the chart: hide the cursor.
    p.canvas.addEventListener('pointerleave', () => { if (!drag) { cursor = null; drawAll(); } });
    // Double-click, or the button, goes back to the full range.
    const resetZoom = () => { range = full.slice(); drawAll(); };
    p.canvas.addEventListener('dblclick', resetZoom);
    p.reset.addEventListener('click', resetZoom);
  }
  drawAll();   // first drawing, with the full range and no cursor
})();
