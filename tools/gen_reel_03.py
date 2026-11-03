"""REEL 03 — keyframe spacing, slow-in slow-out.

Generator for reels/03-keyframe-spacing.html. Run via `python3 tools/build.py`.

Three versions of one 1800 ms move. Row A: nine keys, evenly spaced in value.
Row B: the same nine keys at the same times, with the values distributed as
easeInOut(k/8) — only the *spacing* changed. Row C: three keys with linear
in-betweens, i.e. what a three-stop CSS @keyframes rule actually does.

In-betweens are computed by straight-line interpolation everywhere; no easing
curve is applied to any row. If a row appears to accelerate, it is because of
where the keys sit, which is the whole claim.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reelkit  # noqa: E402

EXTRA_CSS = """
.tr{display:grid;grid-template-columns:212px 1fr 178px;gap:14px;align-items:center;padding:10px 0}
.tr + .tr{border-top:1px solid #1b232d}
.tr .name{display:flex;gap:9px;align-items:flex-start;font-size:13px}
.tr .name b{font-weight:640}
.tr .swatch{margin-top:5px}
.stack small{font:11px/1.35 var(--mono);color:var(--faint);white-space:nowrap}
.stack small b{color:var(--ink);font-weight:600}
.tick{position:absolute;top:50%;width:1px;height:15px;margin-top:-7px;background:#4a5b6e;opacity:.85}
.tick.k{background:#7d8b99}
.dot{transition:none}
.seg{font:10px/1 var(--mono);color:var(--faint);letter-spacing:.04em}
@media (max-width:640px){ .tr{grid-template-columns:1fr} }
""".strip()

BODY = """
<div class="controls">
  <button id="play">Pause</button>
  <input id="scrub" type="range" min="0" max="1000" value="0" step="1"
         aria-label="scrub the 1800 ms move">
  <span class="hint" id="clock">t = 0.000 &middot; 0 / 1800 ms</span>
</div>

<section class="panel">
  <div id="stage"></div>
  <div class="legend">
    <span>1800 ms &nbsp;&middot;&nbsp; same rail &nbsp;&middot;&nbsp; same total distance</span>
    <span>ticks = key positions on the rail (the spacing chart)</span>
    <span>all in-betweens are straight-line interpolation</span>
  </div>
</section>

<h2>Spacing is timing</h2>
<section class="panel tight">
  <div class="rows measured" id="metrics">
    <div class="head">key set</div>
    <div class="head">speed range</div>
    <div class="head">peak : mean</div>
    <div class="head">worst step</div>
    <div class="head">reads as</div>
  </div>
  <p class="hint" id="metric-note" style="margin:12px 0 0"></p>
</section>

<h2>The same three key sets as timing graphs</h2>
<figure class="panel tight" style="margin:0">
  <svg id="plot" viewBox="0 0 720 240" width="100%" role="img"
       aria-label="position against time for the three keyframe sets"></svg>
  <figcaption>x = time &nbsp;&middot;&nbsp; y = position on the rail &nbsp;&middot;&nbsp;
    dots = keys &nbsp;&middot;&nbsp; a straight line between dots means linear in-betweens</figcaption>
</figure>

<h2>What to watch</h2>
<ul class="watch">
  <li><b>Row A is not wrong, it is unargued.</b> Nine keys, evenly spaced in value, evenly
      spaced in time, linear in-betweens: the dot crosses the rail at 0.56 track/s and never
      changes. Every in-between is correct and the move still reads as a machine, because
      nothing in the spacing says where it started or where it is going.</li>
  <li><b>Row B moved nothing but the values.</b> Same nine keys, same nine times, same total
      distance, same linear interpolation. Because the keys now bunch towards both ends of
      the rail, the speed goes 0.14 &rarr; 0.92 &rarr; 0.14 track/s: a 6.7&times; spread, and
      a 0 at both ends in the limit. This is slow-in / slow-out, and it is a statement about
      <i>spacing</i>, not about easing.</li>
  <li><b>Slow-in / slow-out is not slower.</b> It covers the same distance in the same
      1800 ms, so it must be faster somewhere: its peak is 0.92 track/s against row A's
      constant 0.56 &mdash; 1.66&times; the average. Easing redistributes speed; it cannot
      create or destroy the average.</li>
  <li><b>Row C is what three keys cost you.</b> Keys at t = 0, 0.25, 1 force speeds of 1.11
      and 0.37 track/s, so the dot hits a 3&times; corner at t = 0.25 and the eye reads a
      hitch. This is not a defect of linear interpolation: a three-stop
      <code>@keyframes</code> rule (or a three-point timeline in any editor) has exactly this
      shape, because keyframe percentages are times and the values in between are lerped.</li>
</ul>

<div class="note">
  <b>Do not ease twice.</b> An easing curve applied on top of eased spacing multiplies the
  two: <code>cubic-bezier(.42,0,.58,1)</code> over row B gives the middle ~6.7&times; speed
  spread of B <i>and</i> the 1.72&times; peak of the curve, and the start becomes static.
  If the keys already carry the timing, the curve should be linear; if the motion is one
  key pair, the curve has to carry everything.
</div>
"""

SCRIPT = r"""
// ---- the three key sets ------------------------------------------------
const DUR = 1800, HOLD = 500, PAD = 72, DOT = 22, CYCLE = DUR;
const easeInOut = x => REEL.bezier(x, 0.42, 0, 0.58, 1).y;

const SETS = [
  {name:'even spacing', spec:'9 keys · value = k/8', colour:'#58a6ff',
   keys: Array.from({length:9}, (_, k) => [k / 8, k / 8])},
  {name:'slow-in / slow-out', spec:'9 keys · value = easeInOut(k/8)', colour:'#3fb950',
   keys: Array.from({length:9}, (_, k) => [k / 8, easeInOut(k / 8)])},
  {name:'three keys', spec:'3 keys at t = 0, .25, 1', colour:'#f0883e',
   keys: [[0, 0], [0.25, 0.5], [1, 1]]},
];

// segment table per set: the velocity is constant inside a segment because
// the in-betweens are linear. Speed is in track widths per second.
SETS.forEach(s => {
  s.segs = [];
  for (let i = 1; i < s.keys.length; i++){
    const [t0, v0] = s.keys[i - 1], [t1, v1] = s.keys[i];
    const slope = (v1 - v0) / (t1 - t0);
    s.segs.push({t0, t1, v0, v1, slope, speed: slope / (DUR / 1000)});
  }
  s.speeds = s.segs.map(g => g.speed);
  s.max = Math.max.apply(null, s.speeds);
  s.min = Math.min.apply(null, s.speeds);
  const mean = 1 / (DUR / 1000);                 // 1 track per 1.8 s
  s.mean = mean;
  // the largest discontinuous step in speed between neighbouring segments —
  // piecewise-linear in-betweens can only change speed at a key, so this is
  // the size of the worst corner the eye has to accept.
  let step = 0;
  for (let i = 1; i < s.segs.length; i++){
    const a = s.segs[i - 1].speed, b = s.segs[i].speed;
    if (Math.abs(b - a) > Math.abs(step)) step = b - a;
  }
  s.step = step;
});

function segAt(s, tau){
  for (const g of s.segs) if (tau <= g.t1 + 1e-12) return g;
  return s.segs[s.segs.length - 1];
}

// ---- measured table ----------------------------------------------------
(function table(){
  const box = REEL.byId('metrics');
  const reads = ['mechanical', 'hand-drawn ease', 'hitch at each key'];
  SETS.forEach((s, i) => {
    box.insertAdjacentHTML('beforeend',
      '<div class="cell label"><span class="swatch" style="background:' + s.colour + '"></span>' +
        s.name + '</div>' +
      '<div class="cell">' + (Math.abs(s.max - s.min) < 1e-9
          ? REEL.nf(s.max, 2) + ' flat' : REEL.nf(s.min, 2) + '–' + REEL.nf(s.max, 2)) + ' tr/s</div>' +
      '<div class="cell">' + REEL.nf(s.max / s.mean, 2) + '&times;</div>' +
      '<div class="cell">' + (Math.abs(s.step) < 1e-9 ? 'none'
          : (s.step > 0 ? '+' : '−') + REEL.nf(Math.abs(s.step), 2) + ' tr/s') + '</div>' +
      '<div class="cell">' + reads[i] + '</div>');
  });
  REEL.byId('metric-note').textContent =
    'mean speed is ' + REEL.nf(SETS[0].mean, 2) + ' tr/s for all three (1 track in 1800 ms) · ' +
    'measured from the key times alone, so the numbers are checkable by hand';
})();

// ---- stage -------------------------------------------------------------
const stage = REEL.byId('stage');
const rows = SETS.map(s => {
  const row = document.createElement('div');
  row.className = 'tr';
  row.innerHTML =
    '<div class="name"><span class="swatch" style="background:' + s.colour + '"></span>' +
      '<span><b>' + s.name + '</b><br><span class="code">' + s.spec + '</span></span></div>' +
    '<div class="track"><div class="rail"></div><div class="goal"></div>' +
      '<div class="dot" style="background:' + s.colour + '"></div></div>' +
    '<div class="stack">' +
      '<small>speed <b class="sv">0.00</b> tr/s <span class="seg"></span></small>' +
      '<div class="bar"><i style="background:' + s.colour + '"></i></div>' +
      '<small>position <b class="pv">0.0%</b></small>' +
    '</div>';
  stage.appendChild(row);
  const track = row.querySelector('.track');
  // the spacing chart: one tick per key, at the key's position on the rail
  s.keys.forEach(([t, v], i) => {
    const tick = document.createElement('div');
    tick.className = 'tick' + (i === 0 || i === s.keys.length - 1 ? '' : ' k');
    tick.dataset.v = v;
    track.appendChild(tick);
  });
  return {
    s, track,
    dot: row.querySelector('.dot'),
    pv: row.querySelector('.pv'),
    sv: row.querySelector('.sv'),
    seg: row.querySelector('.seg'),
    bar: row.querySelector('.bar > i'),
    ticks: Array.from(track.querySelectorAll('.tick')),
    travel: 100,
  };
});

const vMax = Math.max.apply(null, SETS.map(s => s.max));

function geometry(){
  rows.forEach(r => {
    r.travel = Math.max(60, r.track.clientWidth - DOT - 2 * PAD);
    r.dot.style.left = PAD + 'px';
    r.ticks.forEach(t => { t.style.left = (PAD + parseFloat(t.dataset.v) * r.travel) + 'px'; });
  });
}

// ---- plot --------------------------------------------------------------
const plot = REEL.byId('plot');
const L = 64, R = 700, TOP = 20, BOT = 196;
const PX = t => L + t * (R - L);
const PY = v => BOT - (v + 0.02) / 1.06 * (BOT - TOP);
const svg = (n, a) => { const e = document.createElementNS('http://www.w3.org/2000/svg', n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };
(function axes(){
  plot.appendChild(svg('line', {x1:L, y1:BOT, x2:R, y2:BOT, stroke:'#26303b'}));
  plot.appendChild(svg('line', {x1:L, y1:TOP, x2:L, y2:BOT, stroke:'#26303b'}));
  [[0,'0'],[0.5,'0.5'],[1,'1']].forEach(([v, t]) => {
    const e = svg('text', {x:L - 8, y:PY(v) + 4, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'end', 'font-family':'ui-monospace,monospace'});
    e.textContent = t; plot.appendChild(e);
  });
  [[0,'0'],[0.5,'0.9s'],[1,'1.8s']].forEach(([t, s]) => {
    const e = svg('text', {x:PX(t), y:BOT + 16, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'middle', 'font-family':'ui-monospace,monospace'});
    e.textContent = s; plot.appendChild(e);
  });
})();

rows.forEach(r => {
  const d = r.s.keys.map(([t, v], i) => (i ? 'L' : 'M') + PX(t).toFixed(1) + ' ' + PY(v).toFixed(1)).join(' ');
  plot.appendChild(svg('path', {d, fill:'none', stroke:r.s.colour, 'stroke-width':2, 'stroke-linejoin':'round'}));
  r.s.keys.forEach(([t, v]) => plot.appendChild(
    svg('circle', {cx:PX(t).toFixed(1), cy:PY(v).toFixed(1), r:3.2, fill:'#0b0f14',
      stroke:r.s.colour, 'stroke-width':1.8})));
  r.marker = svg('circle', {r:5, fill:r.s.colour, stroke:'#0b0f14', 'stroke-width':1.5,
    opacity:0.95});
  plot.appendChild(r.marker);
});

// ---- render ------------------------------------------------------------
function draw(tau){
  const ms = tau * DUR;
  rows.forEach(r => {
    const v = REEL.polyline(r.s.keys, tau);
    const g = segAt(r.s, Math.max(1e-6, tau));
    r.dot.style.transform = 'translateX(' + (v * r.travel).toFixed(1) + 'px)';
    r.pv.textContent = REEL.pct(v);
    r.sv.textContent = REEL.nf(g.speed, 2);
    r.bar.style.width = Math.min(100, Math.abs(g.speed) / vMax * 100).toFixed(1) + '%';
    r.seg.textContent = r.s.segs.length > 1 ? 'seg ' + (r.s.segs.indexOf(g) + 1) + '/' + r.s.segs.length : 'one segment';
    r.marker.setAttribute('cx', PX(tau).toFixed(1));
    r.marker.setAttribute('cy', PY(v).toFixed(1));
  });
  REEL.byId('clock').textContent = 't = ' + tau.toFixed(3) + ' \u00b7 ' + Math.round(ms) + ' / ' + DUR + ' ms';
}

// ---- clock -------------------------------------------------------------
const btn = REEL.byId('play'), scrub = REEL.byId('scrub');
let playing = false, clock = 0, last = null, raf = null, prevCyc = 0;
function tick(now){
  if (last === null) last = now;
  const dt = Math.min(now - last, 100);
  last = now;
  if (playing){
    clock += dt;
    const cyc = clock % (DUR + HOLD);
    if (cyc < prevCyc) clock = cyc;
    prevCyc = cyc;
    const tau = Math.min(1, cyc / DUR);
    draw(tau);
    scrub.value = Math.round(tau * 1000);
  }
  raf = requestAnimationFrame(tick);
}
function play(){ playing = true; btn.textContent = 'Pause'; if (raf === null){ last = null; raf = requestAnimationFrame(tick); } }
function pause(){ playing = false; btn.textContent = 'Play'; }

btn.addEventListener('click', () => (playing ? pause() : play()));
scrub.addEventListener('input', () => {
  pause();
  clock = scrub.value / 1000 * DUR; prevCyc = clock;
  draw(scrub.value / 1000);
});
addEventListener('keydown', e => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT'){ e.preventDefault(); playing ? pause() : play(); }
});
addEventListener('resize', () => { geometry(); draw(Math.min(1, (clock % (DUR + HOLD)) / DUR)); });

geometry();
if (REEL.still || REEL.reduceMotion){
  pause(); clock = REEL.stillT * DUR;
  draw(REEL.stillT); scrub.value = Math.round(REEL.stillT * 1000);
} else {
  play();
}
"""


def render() -> str:
    return reelkit.page(
        reel_id="03-keyframe-spacing",
        number="03",
        title="Keyframe spacing is the timing",
        lede="One 1800&nbsp;ms move, three key sets, straight-line in-betweens everywhere. "
             "Only where the keys sit changes &mdash; and that alone decides whether the move "
             "reads as mechanical, hand-drawn, or broken.",
        body=BODY,
        script=SCRIPT,
        extra_css=EXTRA_CSS,
        footer_note="REEL 03 · keyframe spacing · generated by tools/gen_reel_03.py",
    )


if __name__ == "__main__":
    out = reelkit.REELS / "03-keyframe-spacing.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print("wrote", out.relative_to(reelkit.ROOT))
