"""REEL 02 — spring vs tween settling.

Generator for reels/02-spring-vs-tween.html. Run via `python3 tools/build.py`.

Same rail, same target, same visual weight: the left dot is driven by a
damped spring integrated at 2 kHz, the right dot by a cubic-bezier tween over
a fixed 700 ms. The reel exists to make three differences measurable rather
than rhetorical: overshoot, the length of the settling tail, and what happens
to velocity when the target moves mid-flight.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reelkit  # noqa: E402

EXTRA_CSS = """
.tr{display:grid;grid-template-columns:212px 1fr 190px;gap:14px;align-items:center;padding:9px 0}
.tr + .tr{border-top:1px solid #1b232d}
.tr .name{display:flex;gap:9px;align-items:flex-start;font-size:13px}
.tr .name b{font-weight:640}
.tr .swatch{margin-top:5px}
.stack small{font:11px/1.35 var(--mono);color:var(--faint);white-space:nowrap}
.stack small b{color:var(--ink);font-weight:600}
.chip{display:inline-block;font:600 10px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;
  padding:3px 6px;border-radius:4px;border:1px solid #35424f;color:var(--dim)}
.chip.hot{color:var(--c3);border-color:#5a3a1c}
.chip.cold{color:var(--c2);border-color:#1f4d2e}
.rows.measured .cell{padding:11px 0;font-size:12.5px}
.rows.measured .label{font-size:13px}
.band{fill:#58a6ff;opacity:.07}
@media (max-width:640px){ .tr{grid-template-columns:1fr} }
""".strip()

BODY = """
<div class="controls">
  <button id="play">Pause</button>
  <button id="flip" class="secondary">Flip the target mid-flight</button>
  <input id="scrub" type="range" min="0" max="1000" value="0" step="1"
         aria-label="scrub the 2000 ms cycle">
  <span class="hint" id="clock">t = 0.000 &middot; 0 / 2000 ms</span>
</div>

<section class="panel">
  <div id="stage"></div>
  <div class="legend">
    <span>spring: m = 1, k = 120, c = 14 &nbsp;&rarr;&nbsp; &omega;&#8320; = 10.95 rad/s, &zeta; = 0.639, f<sub>d</sub> = 1.34 Hz</span>
    <span>tween: cubic-bezier(.22,1,.36,1) over 700 ms</span>
  </div>
</section>

<h2>Measured, not asserted</h2>
<section class="panel tight">
  <div class="rows measured" id="metrics">
    <div class="head">driver</div>
    <div class="head">settles</div>
    <div class="head">overshoot</div>
    <div class="head">peak speed</div>
    <div class="head">after the end</div>
  </div>
  <p class="hint" id="metric-note" style="margin:12px 0 0"></p>
</section>

<h2>Position against time</h2>
<figure class="panel tight" style="margin:0">
  <svg id="plot" viewBox="0 0 720 240" width="100%" role="img"
       aria-label="position against time for the spring and the tween"></svg>
  <figcaption>nominal run: rest at 0, target at 1 &nbsp;&middot;&nbsp; shaded band = &plusmn;0.5%
    of the rail &nbsp;&middot;&nbsp; dashed vertical = the moment each driver is inside it for good</figcaption>
</figure>

<h2>What to watch</h2>
<ul class="watch">
  <li><b>Overshoot is quantified, not tuned.</b> &zeta; = 0.64 predicts an overshoot of
      exp(&minus;&zeta;&pi;/&radic;(1&minus;&zeta;&sup2;)) = 7.35%; the closed form reports 7.354%
      at 373&nbsp;ms &mdash; the two agree to three decimals, which is what an exact solution
      of a linear oscillator should do. The bezier tween cannot overshoot at all &mdash; its control points are
      pinned inside the box &mdash; so "springy" and "tweened" are distinguishable by
      measurement, not by taste.</li>
  <li><b>The tails differ in kind.</b> Every half cycle the spring keeps 7.35% of the previous
      deviation: +7.3%, then &minus;0.54%, then +0.04%. It is inside &plusmn;0.5% at 785&nbsp;ms
      and inside &plusmn;0.1% at 943&nbsp;ms &mdash; and to be inside &plusmn;0.01% takes
      1299&nbsp;ms. Any stricter definition just buys another half cycle. The tween is done at 700&nbsp;ms, exactly, forever.
      A spring has no end; a tween has nothing but an end.</li>
  <li><b>Flip the target mid-flight.</b> Press the button while both dots are moving. The spring
      keeps its velocity through the retarget and turns around on a curve; the tween has no
      velocity to keep &mdash; it restarts its timing function from wherever it is, so its speed
      drops to zero in one frame. The restart counter under the right track counts that
      discontinuity. This is the difference that shows up in real UI and is invisible in a
      single-run demo.</li>
  <li><b>Peak speeds are closer than the feel suggests.</b> Spring peaks at 5.28 track/s at 104&nbsp;ms, the
      tween at 6.49 &mdash; yet the tween reads as the faster of the two, because speed at the
      end and at the start is what the eye integrates, and the tween spends 700&nbsp;ms
      accelerating then falling to a dead stop.</li>
</ul>

<div class="note warn">
  <b>Where this is not your engine.</b> The spring here is the exact solution of a linear
  damped oscillator, with no clamping, no rest threshold and no velocity cap. Production
  spring libraries (iOS <code>UISpringTimingParameters</code>, Framer Motion, react-spring)
  integrate numerically and add a rest threshold and a maximum duration; those change the
  settle time you measure, not the shape. <code>tools/measure.py</code> runs the same
  parameters through a 2&nbsp;kHz semi-implicit Euler and reports where it lands &mdash; up to
  0.21% of the rail off, and 5&nbsp;ms early on the &plusmn;0.5% crossing. The tween assumes
  a re-target resets the timing function and drops velocity &mdash; true of CSS transitions
  and of most JS tweeners, false of engines that blend velocities across retargets.
</div>
"""

SCRIPT = r"""
// ---- model -------------------------------------------------------------
const M = 1, K = 120, C = 14;      // mass, stiffness, damping
const TW = 700;                    // tween duration, ms
const TB = [0.22, 1, 0.36, 1];     // tween control points
const BAND = 0.005;                // "settled" = inside 0.5% of the rail
const CYCLE = 2000, HOLD = 400;    // replay length, ms of rest before looping
const PAD = 72, DOT = 22;

const SP = REEL.spring(M, K, C);         // exact solution, see tools/reelkit.py
const springAt = (x0, v0, target, ms) => SP.at(x0, v0, target, ms);
const tweenAt = (from, to, ms) => {
  const f = Math.max(0, Math.min(1, ms / TW));
  const b = REEL.bezier(f, TB[0], TB[1], TB[2], TB[3]);
  return {x: from + (to - from) * b.y, v: b.slope * (to - from) / (TW / 1000)};
};

// ---- nominal run, measured once ----------------------------------------
// Sampled every 1 ms so the printed metrics are a property of (m, k, c) and
// not of the sampling: at 2 kHz+ the same table comes out to 3 decimals.
const NOM = {pos:[], vel:[]};
for (let i = 0; i <= 2400; i++){ const p = springAt(0, 0, 1, i); NOM.pos.push(p.x); NOM.vel.push(p.v); }
(function measure(){
  let peak = 0, peakAt = 0;
  for (let i = 0; i <= 2400; i++) if (NOM.pos[i] > peak){ peak = NOM.pos[i]; peakAt = i; }
  let lastOut = 0, speed = 0;
  for (let i = 0; i <= 2400; i++){
    if (Math.abs(NOM.pos[i] - 1) > BAND) lastOut = i;
    speed = Math.max(speed, Math.abs(NOM.vel[i]));
  }
  let lastOutTight = 0;
  for (let i = 0; i <= 2400; i++) if (Math.abs(NOM.pos[i] - 1) > 0.001) lastOutTight = i;

  let tspeed = 0;
  for (let i = 0; i <= 200; i++) tspeed = Math.max(tspeed, Math.abs(tweenAt(0, 1, i / 200 * TW).v));

  window.MEASURED = {
    spring: {peak:peak, peakAt:peakAt, settle:lastOut + 1, settleTight:lastOutTight + 1, speed:speed,
             endSpeed:NOM.vel[2400], endPos:NOM.pos[2400]},
    tween:  {peak:1, peakAt:TW, settle:TW, settleTight:TW, speed:tspeed, endSpeed:0, endPos:1},
  };

  const m = window.MEASURED;
  const row = (name, colour, a, b, c, d) =>
    '<div class="cell label"><span class="swatch" style="background:' + colour + '"></span>' + name + '</div>' +
    '<div class="cell">' + a + '</div><div class="cell">' + b + '</div>' +
    '<div class="cell">' + c + '</div><div class="cell">' + d + '</div>';
  const box = REEL.byId('metrics');
  box.insertAdjacentHTML('beforeend',
    row('spring', '#3fb950',
        m.spring.settle + ' ms',
        '+' + REEL.nf((m.spring.peak - 1) * 100, 2) + '%',
        REEL.nf(m.spring.speed, 2) + ' tr/s',
        'asymptote, never exactly 1') +
    row('tween', '#58a6ff',
        TW + ' ms, exact',
        '0.00%',
        REEL.nf(m.tween.speed, 2) + ' tr/s',
        'exactly 1, speed 0'));
  REEL.byId('metric-note').textContent =
    'closed-form solution, sampled at 1 ms · spring is inside ±0.1% at ' +
    m.spring.settleTight + ' ms · peak overshoot at ' + m.spring.peakAt +
    ' ms · peak speed at 104 ms';
})();

// ---- stage -------------------------------------------------------------
const stage = REEL.byId('stage');
function makeTrack(name, spec, colour){
  const row = document.createElement('div');
  row.className = 'tr';
  row.innerHTML =
    '<div class="name"><span class="swatch" style="background:' + colour + '"></span>' +
      '<span><b>' + name + '</b><br><span class="code">' + spec + '</span></span></div>' +
    '<div class="track"><div class="rail"></div><div class="goal"></div>' +
      '<div class="dot" style="background:' + colour + '"></div></div>' +
    '<div class="stack">' +
      '<small>position <b class="pv">0.0%</b> <span class="chip cold st">rest</span></small>' +
      '<div class="bar"><i style="background:' + colour + '"></i></div>' +
      '<small>speed <b class="sv">0.00</b> tr/s <span class="x"></span></small>' +
    '</div>';
  stage.appendChild(row);
  return {
    dot: row.querySelector('.dot'), goal: row.querySelector('.goal'),
    pv: row.querySelector('.pv'), sv: row.querySelector('.sv'),
    bar: row.querySelector('.bar > i'), chip: row.querySelector('.chip'),
    extra: row.querySelector('.x'), track: row.querySelector('.track'),
    travel: 100,
  };
}
const S = makeTrack('spring', 'm1 · k120 · c14 · exact', '#3fb950');
const T = makeTrack('tween', 'cubic-bezier(.22,1,.36,1)', '#58a6ff');

const vScale = Math.max(window.MEASURED.spring.speed, window.MEASURED.tween.speed);

function geometry(){
  [S, T].forEach(r => {
    r.travel = Math.max(60, r.track.clientWidth - DOT - 2 * PAD);
    r.dot.style.left = PAD + 'px';
    r.goal.style.left = (PAD + r.travel + DOT / 2) + 'px';
  });
}

// ---- plot --------------------------------------------------------------
const plot = REEL.byId('plot');
const L = 64, R = 700, TOP = 20, BOT = 196, VMIN = -0.03, VMAX = 1.12;
const PX = ms => L + (ms / CYCLE) * (R - L);
const PY = v => BOT - (v - VMIN) / (VMAX - VMIN) * (BOT - TOP);
const svg = (n, a) => { const e = document.createElementNS('http://www.w3.org/2000/svg', n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };
(function axes(){
  plot.appendChild(svg('rect', {x:L, y:PY(1 + BAND), width:R - L,
    height:Math.max(1.5, PY(1 - BAND) - PY(1 + BAND)), class:'band'}));
  plot.appendChild(svg('line', {x1:L, y1:BOT, x2:R, y2:BOT, stroke:'#26303b'}));
  plot.appendChild(svg('line', {x1:L, y1:TOP, x2:L, y2:BOT, stroke:'#26303b'}));
  plot.appendChild(svg('line', {x1:L, y1:PY(1), x2:R, y2:PY(1), stroke:'#3a4756', 'stroke-dasharray':'4 4'}));
  [[0,'0'],[0.5,'0.5'],[1,'1']].forEach(([v, t]) => {
    const e = svg('text', {x:L - 8, y:PY(v) + 4, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'end', 'font-family':'ui-monospace,monospace'});
    e.textContent = t; plot.appendChild(e);
  });
  [[0,'0'],[1000,'1.0s'],[2000,'2.0s']].forEach(([ms, t]) => {
    const e = svg('text', {x:PX(ms), y:BOT + 16, fill:'#5b6673', 'font-size':'10',
      'text-anchor':'middle', 'font-family':'ui-monospace,monospace'});
    e.textContent = t; plot.appendChild(e);
  });
  [[window.MEASURED.spring.settle, '#3fb950'], [window.MEASURED.tween.settle, '#58a6ff']]
    .forEach(([ms, colour]) => plot.appendChild(svg('line', {x1:PX(ms), y1:TOP, x2:PX(ms),
      y2:BOT, stroke:colour, 'stroke-dasharray':'3 4', opacity:0.55})));
})();

const springPts = [];
for (let i = 0; i <= CYCLE; i += 2) springPts.push([i, NOM.pos[i]]);
const tweenPts  = [];
for (let i = 0; i <= CYCLE; i += 2) tweenPts.push([i, tweenAt(0, 1, Math.min(i, TW)).x]);
[[springPts, '#00693f00', '#3fb950'], [tweenPts, '#0057a300', '#58a6ff']].forEach(([pts, _, colour]) => {
  const d = pts.map((q, i) => (i ? 'L' : 'M') + PX(q[0]).toFixed(1) + ' ' + PY(q[1]).toFixed(1)).join(' ');
  plot.appendChild(svg('path', {d, fill:'none', stroke:colour, 'stroke-width':1.9, 'stroke-linecap':'round'}));
});
const mSpring = svg('circle', {r:4.5, fill:'#3fb950', stroke:'#0b0f14', 'stroke-width':1.5});
const mTween  = svg('circle', {r:4.5, fill:'#58a6ff', stroke:'#0b0f14', 'stroke-width':1.5});
plot.appendChild(mSpring); plot.appendChild(mTween);

// ---- run state ---------------------------------------------------------
// spr describes the *current leg* of the spring: it is re-based on retarget,
// which is exactly how a real spring keeps its velocity.
let spr = {x0:0, v0:0, target:1, t0:0};
let tw  = {from:0, to:1, t0:0, restarts:0};
let runT = 0, target = 1, playing = false, clock = 0, last = null, raf = null;

function resetRun(){
  spr = {x0:0, v0:0, target:1, t0:0};
  tw = {from:0, to:1, t0:0, restarts:0};
  target = 1; runT = 0;
}
function springNow(t){ return springAt(spr.x0, spr.v0, spr.target, t - spr.t0); }
function tweenNow(t){ return tweenAt(tw.from, tw.to, t - tw.t0); }

function flip(){
  const s = springNow(runT), wv = tweenNow(runT);
  target = target === 1 ? 0 : 1;
  spr = {x0:s.x, v0:s.v, target:target, t0:runT};   // velocity carried over
  tw  = {from:wv.x, to:target, t0:runT, restarts:tw.restarts + 1}; // velocity dropped
  draw(runT);
}

// ---- render ------------------------------------------------------------
function draw(t){
  runT = t;
  const s = springNow(t), w = tweenNow(t);

  S.dot.style.transform = 'translateX(' + (s.x * S.travel).toFixed(1) + 'px)';
  S.goal.style.transform = 'translateX(' + ((target - 1) * S.travel).toFixed(1) + 'px)';
  S.pv.textContent = REEL.pct(s.x);
  S.sv.textContent = REEL.nf(s.v, 2);
  S.bar.style.width = Math.min(100, Math.abs(s.v) / vScale * 100).toFixed(1) + '%';
  const sDone = Math.abs(s.x - target) < BAND && Math.abs(s.v) < 0.05;
  S.chip.textContent = sDone ? 'settled' : (Math.abs(s.v) < 0.15 ? 'creeping' : 'moving');
  S.chip.className = 'chip ' + (sDone ? 'cold' : 'hot') + ' st';

  T.dot.style.transform = 'translateX(' + (w.x * T.travel).toFixed(1) + 'px)';
  T.goal.style.transform = 'translateX(' + ((target - 1) * T.travel).toFixed(1) + 'px)';
  T.pv.textContent = REEL.pct(w.x);
  T.sv.textContent = REEL.nf(Math.abs(w.v) < 5e-4 ? 0 : w.v, 2);
  T.bar.style.width = Math.min(100, Math.abs(w.v) / vScale * 100).toFixed(1) + '%';
  const tDone = Math.abs(w.x - target) < 1e-6;
  T.chip.textContent = tDone ? 'arrived' : 'timing';
  T.chip.className = 'chip ' + (tDone ? 'cold' : 'hot') + ' st';
  T.extra.textContent = tw.restarts ? '· ' + tw.restarts + ' retarget' + (tw.restarts > 1 ? 's' : '') : '';

  mSpring.setAttribute('cx', PX(t).toFixed(1)); mSpring.setAttribute('cy', PY(s.x).toFixed(1));
  mTween.setAttribute('cx', PX(t).toFixed(1));  mTween.setAttribute('cy', PY(w.x).toFixed(1));
  REEL.byId('clock').textContent = 't = ' + (t / CYCLE).toFixed(3) + ' \u00b7 ' + Math.round(t) + ' / ' + CYCLE + ' ms';
}

// ---- clock -------------------------------------------------------------
const btn = REEL.byId('play'), scrub = REEL.byId('scrub');
let prevCyc = 0;
function tick(now){
  if (last === null) last = now;
  const dt = Math.min(now - last, 100);
  last = now;
  if (playing){
    clock += dt;
    const cyc = clock % (CYCLE + HOLD);
    if (cyc < prevCyc) resetRun();          // the replay wrapped: back to rest
    prevCyc = cyc;
    draw(Math.min(CYCLE, cyc));
    scrub.value = Math.round(Math.min(1, cyc / CYCLE) * 1000);
  }
  raf = requestAnimationFrame(tick);
}
function play(){ playing = true; btn.textContent = 'Pause'; if (raf === null){ last = null; raf = requestAnimationFrame(tick); } }
function pause(){ playing = false; btn.textContent = 'Play'; }

btn.addEventListener('click', () => (playing ? pause() : play()));
REEL.byId('flip').addEventListener('click', () => { if (runT >= CYCLE) { resetRun(); draw(0); } flip(); });
scrub.addEventListener('input', () => {
  pause(); resetRun();
  const t = Math.min(CYCLE, scrub.value / 1000 * CYCLE);
  clock = t; prevCyc = t;
  draw(t);
});
addEventListener('keydown', e => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT'){ e.preventDefault(); playing ? pause() : play(); }
  if (e.code === 'KeyF' && e.target.tagName !== 'INPUT'){ e.preventDefault(); flip(); }
});
addEventListener('resize', () => { geometry(); draw(runT); });

geometry(); resetRun();
if (REEL.still || REEL.reduceMotion){
  pause(); draw(REEL.stillT * CYCLE);
  scrub.value = Math.round(REEL.stillT * 1000);
} else {
  play();
}
"""


def render() -> str:
    return reelkit.page(
        reel_id="02-spring-vs-tween",
        number="02",
        title="Spring vs tween, same target",
        lede="A damped spring, solved in closed form, against a fixed 700&nbsp;ms bezier tween, "
             "pulling the same dot across the same rail. Same target, same weight; different "
             "answer to &ldquo;what happens after it arrives&rdquo;.",
        body=BODY,
        script=SCRIPT,
        extra_css=EXTRA_CSS,
        footer_note="REEL 02 · spring vs tween · generated by tools/gen_reel_02.py",
    )


if __name__ == "__main__":
    out = reelkit.REELS / "02-spring-vs-tween.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print("wrote", out.relative_to(reelkit.ROOT))
