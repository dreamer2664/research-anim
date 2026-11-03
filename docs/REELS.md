# REEL — three studies in timing

Short, honest animation studies. Each reel isolates **one variable** on a shared
rail, prints the numbers it is asking you to judge, and says what it does not
cover. Three reels this shift:

| # | file | question |
|---|---|---|
| 01 | [`reels/01-easing-curves.html`](../reels/01-easing-curves.html) | What does a timing function actually change, if duration and distance are fixed? |
| 02 | [`reels/02-spring-vs-tween.html`](../reels/02-spring-vs-tween.html) | What is the difference between a spring and a tween once the target is reached — or moved? |
| 03 | [`reels/03-keyframe-spacing.html`](../reels/03-keyframe-spacing.html) | How much of a move's timing comes from keyframe spacing before any easing is applied? |

`reels/index.html` is the hub. Every page is a single self-contained file: inline
CSS, inline JS, no CDN, no fonts, no images, no network. It opens from `file://`
with the wifi off.

## Opening and freezing

Open `reels/index.html` in any current browser. Space toggles play/pause; the
scrubber takes over the clock.

Appending **`?still=1&t=<0..1>`** freezes one frame at that fraction of the
cycle and starts no clock. This exists so a screenshot is a statement about the
reel rather than a race with `requestAnimationFrame` — and so any claim below
can be checked at a specific instant:

```
reels/01-easing-curves.html?still=1&t=0.25
reels/02-spring-vs-tween.html?still=1&t=0.55
reels/03-keyframe-spacing.html?still=1&t=1
```

## Notation and units

- **track** — the length of the rail. All positions are fractions of one track.
- **track/s** — track widths per second. Because speed is distance over the
  reel's own duration, speeds are comparable across reels with different rails.
- **t** — normalised time through the cycle, 0..1. **ms** is wall time.
- Every printed value is measured from the same functions that draw the dots.
  `tools/measure.py` re-derives them independently in Python and
  `tools/verify.py` asserts the two agree (17/17 readouts at the time of
  writing).

---

# 01 · Easing curves, one clock

Three dots, one rail, one duration (**1400 ms**), one distance (the full rail).
The only difference is the timing function:

| track | function | control points |
|---|---|---|
| linear | `linear` | (0, 0) (1, 1) |
| ease-in-out | CSS keyword | (0.42, 0) (0.58, 1) |
| ease-out-back | `cubic-bezier(.34,1.56,.64,1)` | (0.34, 1.56) (0.64, 1) |

## The maths

A CSS timing function is a cubic Bézier with the endpoints pinned:

```
P0 = (0,0)   P1 = (x1,y1)   P2 = (x2,y2)   P3 = (1,1)
x(u) = 3(1-u)²u·x1 + 3(1-u)u²·x2 + u³
y(u) = 3(1-u)²u·y1 + 3(1-u)u²·y2 + u³
```

`u` is the curve parameter, **not** progress. To get "how far along am I at
progress x" you must invert `x(u) = x` and evaluate `y` at that `u`. The reels
do exactly that, Newton–Raphson (8 iterations, tolerance 1e-7) with a bisection
fallback, and the speed printed on screen is the parametric derivative:

```
dy/dx = (dy/du) / (dx/du)
dx/du = 3A·u² + 2B·u + C   with A = 1 − 3x2 + 3x1, B = 3x2 − 6x1, C = 3x1
```

With x = 0.42/0.58 the curve is symmetric and 0.5 progress is exactly half way;
with x1 = 0.34, x2 = 0.64 it is not, and the printed y(0.5) = **1.0874** is not
half — the dot is already past the target.

## Measured (at 1400 ms, one track)

| curve | y(0.25) | y(0.5) | peak y | max dy/dx | at x | min dy/dx |
|---|---|---|---|---|---|---|
| linear | 0.2500 | 0.5000 | 1.0000 | 1.000 | 0.000 | 0.000 |
| ease-in-out | 0.1292 | 0.5000 | 1.0000 | 1.724 | 0.500 | 0.000 |
| ease-out-back | 0.8163 | 1.0874 | 1.0978 | 4.588 | 0.000 | −0.345 |

Divide dy/dx by 1.4 s for track/s: linear is a flat 0.71, ease-in-out peaks at
1.23, back-out peaks at 3.28 and goes to −0.25 on the way back.

## What to watch

1. **At t = 0.25 the three dots are at 25.0%, 12.9% and 81.6%.** Identical
   clocks. Any feeling that one "is faster" at that instant is a statement
   about speed, not about duration.
2. **Only the third dot crosses the line.** Overshoot here is arithmetic: y1 =
   1.56 > 1 pushes the curve above 1, so the dot reaches 109.8% at t ≈ 0.42 and
   comes back. No physics, no bounce, and no way for a curve with both control
   points inside [0, 1] to do the same.
3. **The speed bar is dy/dx.** Linear's is a constant bar; ease-in-out's swells
   to 1.72× linear at the midpoint; back-out's is 4.59× linear at t → 0 and
   still negative before the end. That asymmetry — violent start, creeping
   return — is the whole character of "back out".
4. **All three arrive at t = 1.** A timing function redistributes progress
   inside a fixed duration; it cannot change the duration.

## Honest limits

- The positions match what a CSS `transition-timing-function` would produce,
  but the movement is computed in JS rather than by the compositor. The reel
  says nothing about how a real engine samples it (60 Hz vs 120 Hz vs variable),
  only about the underlying curve.
- Everything is 1-D along a rail. Rotation, path length and property-specific
  timing behave differently and are not covered here.
- "Feels snappy" is not measured. Only positions, speeds and overshoot are.

---

# 02 · Spring vs tween, same target

Two dots, one rail, one target. Left: a damped spring. Right: a 700 ms
`cubic-bezier(.22,1,.36,1)` tween. Both are given the same job, and the reel
measures where they differ.

## The maths

The spring solves

```
m·x″ + c·x′ + k·(x − T) = 0        m = 1, k = 120, c = 14, T = 1
ω₀ = √(k/m)          = 10.954 rad/s
ζ  = c / (2√(km))    = 0.6390
ω_d = ω₀√(1 − ζ²)    = 8.426 rad/s      (f_d = 1.341 Hz, period 745.7 ms)
```

Underdamped, so the closed form applies and the reel uses it directly — no
step size, no drift:

```
x(t) = T + e^(−ζω₀t)·(A·cos ω_d t + B·sin ω_d t)
A = x₀ − T          B = (v₀ + ζω₀A) / ω_d
v(t) = e^(−ζω₀t)·[(Bω_d − ζω₀A)·cos ω_d t − (Aω_d + ζω₀B)·sin ω_d t]
```

The overshoot follows from ζ alone:

```
overshoot = exp(−ζπ / √(1−ζ²)) = exp(−0.6390π / 0.7692) = 7.354%
```

and so does the decay between successive extremes — the *same* factor, which
is why the ring-out reads as a geometric series: **+7.354%, −0.541%, +0.040%,
−0.003%** at 373, 746, 1119 and 1492 ms.

The tween is a curve, not an ODE: `y = bezier(t/700)` with the control points
in [0,1], so overshoot is impossible by construction and the move ends at
exactly 700 ms.

## Measured (sampled every 1 ms over 2.4 s)

| | spring | tween |
|---|---|---|
| settles (inside ±0.5% of the rail) | 785 ms | 700 ms, exactly |
| peak overshoot | +7.354% at 373 ms | 0.000% |
| peak speed | 5.284 track/s at 104 ms | 6.493 track/s |
| crossings of the target | 6 | 1 |
| state after the nominal end | asymptote; never exactly 1 | exactly 1, speed exactly 0 |

Settling is a definition, not a fact, so here is the whole ladder: ±2% at
548 ms, ±1% at 585 ms, ±0.5% at 785 ms, ±0.1% at 943 ms, ±0.01% at 1299 ms. A
spring has no end; a tween has nothing but an end.

## What to watch

1. **Overshoot is derived, not tuned.** ζ = 0.639 predicts 7.354%; the solution
   reports 7.354%. If a designer asks for "a bit more bounce", the answer is a
   smaller ζ (less damping) and the numbers move predictably.
2. **The tween is done; the spring is still moving.** At 700 ms the tween's dot
   is frozen and its speed is zero — from there nothing can happen except a
   retarget. At 700 ms the spring is at 99.54%, still moving (0.04 track/s), and
   on its way *through* the target to −0.54%. Watch the tail after the second
   dot has stopped.
3. **Retarget mid-flight (press the button or `F`).** The spring carries its
   velocity into the new target and turns around on a curve with no corner: the
   position and the velocity are both continuous. The tween has no velocity to
   carry — it restarts its timing function from the current value, so its speed
   drops to zero in one frame and re-accelerates. The counter under the right
   track counts those discontinuities. This is the difference that shows up in
   real interfaces (a sheet dismissed while still opening) and is invisible in a
   single-run demo.
4. **Peak speeds are closer than the feel.** 5.28 vs 6.49 track/s, yet the
   spring reads as the calmer of the two, because what the eye integrates is
   the start and the end: the spring starts at 0 speed and *keeps moving after
   it arrives*, the tween starts at full speed (dy/dx = 4.55 at x → 0) and
   stops dead.

## Honest limits

- **The spring here is exact; your engine is not.** A production engine steps
  the ODE. `tools/measure.py` runs the same parameters through a 2 kHz
  semi-implicit Euler: up to **0.207% of the rail** of deviation, a peak of
  1.07298 instead of 1.07354, and the ±0.5% crossing 5 ms early (780 vs 785 ms).
  That is the size of the "not your engine" caveat — small, but larger than the
  differences designers usually argue about.
- No rest threshold, no clamping, no maximum duration, no velocity cap. Real
  libraries (iOS `UISpringTimingParameters`, Framer Motion, react-spring) add
  these and they change the settle time you would measure in the product.
- The spring is linear. Real springy UI sometimes wants drag, friction or a
  nonlinear stiffness; none of that is modelled.
- The tween's retarget behaviour (reset the timing function, drop velocity) is
  what CSS transitions and most JS tweeners do. Engines that blend velocities
  across retargets will not show the discontinuity.
- Visual weight is matched crudely: same dot size, same rail. Perceived speed
  is also affected by distance, and the rail length is a choice.

---

# 03 · Keyframe spacing is the timing

One 1800 ms move, one rail, three key sets. **Every in-between in every row is
straight-line interpolation** — no easing curve is applied anywhere. If a row
appears to accelerate, the cause is where the keys sit.

| row | keys |
|---|---|
| A · even spacing | 9 keys, times k/8, values k/8 |
| B · slow-in / slow-out | 9 keys, times k/8, values `easeInOut(k/8)` |
| C · three keys | keys at t = 0, 0.25, 1 with values 0, 0.5, 1 |

## The maths

Between keys the value is a lerp, so the speed inside a segment is constant and
set entirely by the endpoints:

```
value(t) = v_i + (v_i+1 − v_i)·(t − t_i)/(t_i+1 − t_i)
speed    = (v_i+1 − v_i)/(t_i+1 − t_i) / DUR          [track/s]
```

Because the in-between motion is a staircase of constant speeds,
a key set is fully described by its segment speeds (row B's key values are in
[MEASUREMENTS.md](MEASUREMENTS.md#5--keyframe-sets-reel-03)):

- **A**: 0.556 × 8 — flat, so 0% of the move's character is decided by easing.
- **B**: 0.138, 0.436, 0.727, 0.921, 0.921, 0.727, 0.436, 0.138 — a 6.7×
  spread, produced by moving nothing but the *values*.
- **C**: 1.111 then 0.370 — two speeds and a 3× corner at t = 0.25.

Worst step between neighbouring segments: **none** (A), **+0.297 track/s** (B),
**−0.741 track/s** (C). Peak ÷ mean speed: 1.00×, 1.66×, 2.00×.

## What to watch

1. **Row A is not wrong, it is unargued.** Perfectly even keys, perfectly even
   speed, and the move reads as a machine. Every in-between is "correct" and
   nothing in the spacing says where the motion came from or where it is going.
2. **Row B changed only the values.** Same nine keys, same nine times, same
   total distance, same lerp. The keys bunch towards both ends of the rail and
   the result is slow-in / slow-out.
3. **Slow-in / slow-out is not slower.** Same distance, same 1800 ms → same
   average speed (0.556 track/s). Row B's peak is 0.921 track/s, 1.66× the
   average. Easing redistributes speed; it cannot create or destroy the mean.
4. **Row C is what three keys cost.** Keys at 0, 0.25 and 1 force speeds of
   1.111 and 0.370 track/s, so the dot hits a 3× corner at t = 0.25. The eye
   reads a hitch, and the hitch is in the key times, not in the interpolation.
5. **The ticks under each rail are the spacing chart.** They mark each key's
   *position*: evenly spread in A, bunched at both ends in B. The full key
   values are in [MEASUREMENTS.md §5](MEASUREMENTS.md#5--keyframe-sets-reel-03).

## Two things this connects to

- **CSS `@keyframes` has exactly row C's shape.** Percentages are times, values
  are positions, and the browser interpolates linearly between stops. Worse (and
  worth knowing): an `animation-timing-function` declared on the animation
  applies to *each* interval, not once over the whole move — so a three-stop
  rule with `ease` is two eased segments, not one eased move, unless you
  override the function inside the keyframe blocks.
- **Do not ease twice.** An easing curve laid over eased spacing multiplies the
  derivatives: row B's ~6.7× speed spread times the curve's 1.72× peak, with a
  start that is effectively static. If the keys carry the timing, the curve
  should be `linear`; if there is a single key pair, the curve has to carry
  everything.
- A spring (reel 02) is a third answer: it carries timing *and* continuity, at
  the cost of an exact duration. Current browsers can ship a sampled spring as a
  `linear()` easing function, which is the practical bridge between that reel
  and CSS.

## Honest limits

- Spacing is measured on a 1-D rail. On a real path, spacing is arc length, and
  uneven spacing is what produces the classic arcs-and-spacing problem in
  character animation — out of scope here.
- "Mechanical / hand-drawn / hitch" in the table are my readings of the motion,
  not measured quantities. The numbers beside them are the measurement; treat
  the adjectives as a hypothesis to disagree with.
- Nine keys is not a magic number. The 6.7× spread in row B is a property of
  `easeInOut` sampled at 8 equal intervals; a different sampling gives different
  segment speeds for the same curve.

---

# How these numbers are made

Everything above is generated or checked by code in `tools/`:

| command | what it does |
|---|---|
| `python3 tools/build.py` | writes `reels/*.html` + `docs/MEASUREMENTS.md` from the generators |
| `python3 tools/build.py --check` | fails if any generated file is stale, and enforces the no-CDN purity rules |
| `python3 tools/measure.py` | independent Python implementation of all three reels' maths → `docs/MEASUREMENTS.md` |
| `python3 tools/verify.py` | loads each reel in headless Chromium and asserts the printed readouts equal `measure.py`'s values |
| `python3 tools/shoot.py` | one headless screenshot per reel at a frozen frame |

The reels are generated files: edit `tools/gen_reel_*.py`, never the HTML.
`--check` is what makes that enforceable in CI.

# Screenshots and the device step

`tools/shoot.py` captures one PNG per reel at `?still=1&t=<t>`. Reference stills
are committed under [`docs/shots/`](shots) (t = 0.42, 1× scale) and CI uploads
fresh ones as a build artefact (2× scale).

Two honest notes:

- **A screenshot is one frame.** It proves the page renders, lays out and paints
  the frame it was asked for. It cannot show motion, so it cannot confirm any
  claim about speed, overshoot or settling. Those claims rest on the numbers.
- **This machine had Chromium via Playwright**, so screenshots and the
  `verify.py` cross-check both ran. On a runner without a browser, `shoot.py`
  writes `build/shots/DEFERRED.md` saying so and exits 0 — a missing artefact
  reported as missing, never a step that silently passes.

# What would falsify this

- If a frame-rate sweep (60/120/144 Hz, plus a deliberately throttled tab) moved
  the arrival times, the reels' "positions come from the clock, not from
  accumulation" premise would be wrong for these pages.
- If `verify.py` disagreed with `measure.py` after a change, either the page or
  the maths in this document is wrong.
- Reels 01 and 02 assert differences that are *visible* at 1× on a laptop; that
  is a perception claim. A device test on real hardware, at real refresh rates,
  with real motion blur, is the deferred step and is not claimed here.
