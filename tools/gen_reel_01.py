"""REEL 01 — easing curve comparison on identical motion.

Generator for reels/01-easing-curves.html. Run via `python3 tools/build.py`.

The study: three dots, one clock, one distance (the full rail), one duration
(1400 ms). The only difference is the timing function. That isolates one
variable, which is the only reason the comparison is worth filming: people
routinely report "ease-in-out feels faster than linear" when the durations
are identical, and this reel makes the falsification visible in one loop.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reelkit  # noqa: E402

EXTRA_CSS = """
.tr{display:grid;grid-template-columns:212px 1fr 176px;gap:14px;align-items:center;padding:9px 0}
.tr + .tr{border-top:1px solid #1b232d}
.tr .name{display:flex;gap:9px;align-items:flex-start;font-size:13px}
.tr .name b{font-weight:640}
.tr .swatch{margin-top:5px}
.stack small{font:11px/1.35 var(--mono);color:var(--faint);white-space:nowrap}
.stack small b{color:var(--ink);font-weight:600}
@media (max-width:640px){
  .tr{grid-template-columns:1fr}
}
""".strip()

BODY = """
<div class="controls">
  <button id="play">Pause</button>
  <input id="scrub" type="range" min="0" max="1000" value="0" step="1"
         aria-label="scrub the 1400 ms">
  <span class="hint" id="clock">t = 0.000 &middot; 0 / 1400 ms</span>
</div>

<section class="panel">
  <div id="stage"></div>
  <div class="legend">
    <span>one clock</span><span>one distance</span><span>one duration (1400&nbsp;ms)</span>
    <span>three timing functions</span>
  </div>
</section>

<h2>Progress against time</h2>
<figure class="panel tight" style="margin:0">
  <svg id="plot" viewBox="0 0 720 240" width="100%" role="img"
       aria-label="progress against time for the three timing curves"></svg>
  <figcaption>x = time through the 1400 ms &nbsp;&middot;&nbsp; y = distance travelled
    &nbsp;&middot;&nbsp; dashed line = the target</figcaption>
</figure>

<h2>What to watch</h2>
<ul class="watch">
  <li><b>The quarter mark splits them.</b> At t = 0.25 the linear dot is a quarter of the
      way, <code>ease-in-out</code> has covered 12.9%, and the back-out curve is already at
      81.6% of the rail. Same clock, same rail, same 1400 ms.</li>
  <li><b>Only the third dot crosses the line.</b> Overshoot is a property of the curve's
      control points (y&#8321; = 1.56 &gt; 1), not of the engine. It peaks at 109.8% around
      t = 0.42, then comes back — a spring-free overshoot, and the reason back-out reads
      as "snappy" while physically nothing is bouncing.</li>
  <li><b>Speed, not distance, is what the eye judges.</b> In dy/dx units, where linear
      is 1.00 by definition: <code>ease-in-out</code> peaks at 1.72, back-out peaks at
      4.59 at t &rarr; 0 and is still <i>negative</i> (&minus;0.35) just before the end.
      The bar under each track is that same dy/dx, scaled to the fastest instant in the
      frame (4.59), which is why the linear bar never fills.</li>
  <li><b>All three arrive at the same instant.</b> Hold the scrubber at 1.000: every dot
      is on the line, because a timing function redistributes progress; it does not
      change the duration.</li>
</ul>

<div class="note">
  <b>Honest footnote.</b> These are the CSS timing keywords' exact control points, so a
  CSS <code>transition-timing-function</code> would produce the same positions. The reel
  computes them in JS anyway so the printed speed is the same derivative the graph is
  drawn from — a screenshot of this page at <code>?still=1&amp;t=0.42</code> is a
  reproducible claim, not a frame from whichever rAF tick won the race.
</div>
"""

SCRIPT = r"""
// ---- constants ---------------------------------------------------------
const DUR  = 1400;   // ms — identical for all three tracks
const HOLD = 600;    // ms of rest at the target before the loop restarts
const PAD  = 72;     // px of slack each side so the overshoot stays on-screen
const DOT  = 22;

const CURVES = [
  {name:'linear',       spec:'linear',                    p:[0, 0, 1, 1],           colour:'#58a6ff'},
  {name:'ease-in-out',  spec:'cubic-bezier(.42,0,.58,1)', p:[0.42, 0, 0.58, 1],  colour:'#3fb950'},
  {name:'ease-out-back',spec:'cubic-bezier(.34,1.56,.64,1)', p:[0.34, 1.56, 0.64, 1], colour:'#f0883e'},
];

// ---- build the tracks --------------------------------------------------
const stage = REEL.byId('stage');
const rows = CURVES.map(c => {
  const row = document.createElement('div');
  row.className = 'tr';
  row.innerHTML =
    '<div class="name"><span class="swatch" style="background:' + c.colour + '"></span>' +
      '<span><b>' + c.name + '</b><br><span class="code">' + c.spec + '</span></span></div>' +
    '<div class="track"><div class="rail"></div><div class="goal"></div>' +
      '<div class="dot" style="background:' + c.colour + '"></div></div>' +
    '<div class="stack">' +
      '<small>progress <b class="pv">0.0%</b></small>' +
      '<div class="bar"><i style="background:' + c.colour + '"></i></div>' +
      '<small>speed <b class="sv">0.00</b> track/s</small>' +
    '</div>';
  stage.appendChild(row);
  return {
    c, row,
    dot:  row.querySelector('.dot'),
    goal: row.querySelector('.goal'),
    pv:   row.querySelector('.pv'),
    sv:   row.querySelector('.sv'),
    bar:  row.querySelector('.bar > i'),
    track: row.querySelector('.track'),
    travel: 100, pad: PAD,
  };
});

// shared vertical scale for the speed bars = fastest instant on screen
const vMax = Math.max.apply(null, CURVES.map(c => REEL.maxSlope(c.p[0], c.p[1], c.p[2], c.p[3])));

function geometry(){
  rows.forEach(r => {
    const w = r.track.clientWidth;
    r.travel = Math.max(60, w - DOT - 2 * PAD);
    r.dot.style.left = PAD + 'px';
    r.goal.style.left = (PAD + r.travel + DOT / 2) + 'px';
  });
}

// ---- the timing graph --------------------------------------------------
const plot = REEL.byId('plot');
const L = 64, R = 700, TOP = 20, BOT = 196;
const VMIN = -0.06, VMAX = 1.16;
const PX = x => L + x * (R - L);
const PY = v => BOT - (v - VMIN) / (VMAX - VMIN) * (BOT - TOP);
const svg = (n, attrs) => {
  const e = document.createElementNS('http://www.w3.org/2000/svg', n);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
(function drawAxes(){
  plot.appendChild(svg('line', {x1:L, y1:BOT, x2:R, y2:BOT, stroke:'#26303b'}));
  plot.appendChild(svg('line', {x1:L, y1:TOP, x2:L,  y2:BOT, stroke:'#26303b'}));
  plot.appendChild(svg('line', {x1:L, y1:PY(1), x2:R, y2:PY(1),
      stroke:'#3a4756', 'stroke-dasharray':'4 4'}));
  [[0,'0'],[0.5,'0.5'],[1,'1']].forEach(([v,t]) => {
    const label = svg('text', {x:L-8, y:PY(v)+4, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'end', 'font-family':'ui-monospace,monospace'});
    label.textContent = t;
    plot.appendChild(label);
  });
  [[0,'0'],[1,'t=1']].forEach(([x,t]) => {
    const label = svg('text', {x:PX(x), y:BOT+16, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'middle', 'font-family':'ui-monospace,monospace'});
    label.textContent = t;
    plot.appendChild(label);
  });
})();

rows.forEach(r => {
  const pts = REEL.samples(r.c.p[0], r.c.p[1], r.c.p[2], r.c.p[3], 160);
  const d = pts.map((q, i) => (i ? 'L' : 'M') + PX(q[0]).toFixed(1) + ' ' + PY(q[1]).toFixed(1)).join(' ');
  plot.appendChild(svg('path', {d, fill:'none', stroke:r.c.colour, 'stroke-width':1.75,
    'stroke-linecap':'round', opacity:0.9}));
  r.marker = svg('circle', {r:4.5, fill:r.c.colour, stroke:'#0b0f14', 'stroke-width':1.5});
  plot.appendChild(r.marker);
});

// ---- render one instant ------------------------------------------------
function draw(tau){
  rows.forEach(r => {
    const b = REEL.bezier(tau, r.c.p[0], r.c.p[1], r.c.p[2], r.c.p[3]);
    r.dot.style.transform = 'translateX(' + (b.y * r.travel).toFixed(1) + 'px)';
    r.pv.textContent = REEL.pct(b.y);
    r.sv.textContent = REEL.nf(b.slope / (DUR / 1000), 2);   // track widths per second
    r.bar.style.width = Math.min(100, Math.abs(b.slope) / vMax * 100).toFixed(1) + '%';
    r.marker.setAttribute('cx', PX(tau).toFixed(1));
    r.marker.setAttribute('cy', PY(b.y).toFixed(1));
  });
  REEL.byId('clock').textContent = 't = ' + tau.toFixed(3) + ' \u00b7 ' +
      Math.round(tau * DUR) + ' / ' + DUR + ' ms';
}

// ---- clock -------------------------------------------------------------
const btn = REEL.byId('play');
const scrub = REEL.byId('scrub');
let playing = false, clock = 0, last = null, raf = null;

function tick(now){
  if (last === null) last = now;
  const dt = Math.min(now - last, 100);   // tab-switch guard
  last = now;
  if (playing) clock += dt;
  const tau = Math.min(1, (clock % (DUR + HOLD)) / DUR);
  draw(tau);
  scrub.value = Math.round(tau * 1000);
  raf = requestAnimationFrame(tick);
}

function play(){
  playing = true; btn.textContent = 'Pause';
  if (raf === null){ last = null; raf = requestAnimationFrame(tick); }
}
function pause(){ playing = false; btn.textContent = 'Play'; }

btn.addEventListener('click', () => (playing ? pause() : play()));
scrub.addEventListener('input', () => {
  pause();
  clock = scrub.value / 1000 * DUR;
  draw(scrub.value / 1000);
});
addEventListener('keydown', e => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT'){ e.preventDefault(); playing ? pause() : play(); }
});
addEventListener('resize', () => { geometry(); draw(Math.min(1, (clock % (DUR + HOLD)) / DUR)); });

geometry();
if (REEL.still || REEL.reduceMotion){
  pause();
  clock = REEL.stillT * DUR;
  draw(REEL.stillT);
  scrub.value = Math.round(REEL.stillT * 1000);
  if (!REEL.still) btn.textContent = 'Play';
} else {
  play();
}
"""


def render() -> str:
    return reelkit.page(
        reel_id="01-easing-curves",
        number="01",
        title="Easing curves, one clock",
        lede="Linear, CSS <code>ease-in-out</code> and <code>cubic-bezier(.34,1.56,.64,1)</code> "
             "driving the same 1400 ms of the same distance. Nothing else varies, so anything "
             "you see is the timing function's doing.",
        body=BODY,
        script=SCRIPT,
        extra_css=EXTRA_CSS,
        footer_note="REEL 01 · easing curves · generated by tools/gen_reel_01.py",
    )


if __name__ == "__main__":
    out = reelkit.REELS / "01-easing-curves.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print("wrote", out.relative_to(reelkit.ROOT))
