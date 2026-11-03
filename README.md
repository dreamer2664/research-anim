# research-anim

Animation research: easing/tween/keyframe studies and playable reels.

REEL is the animation-reel lane. Three self-contained studies live in
[`reels/`](reels), the generators that produce them in [`tools/`](tools), and the
maths plus "what to watch" in [`docs/REELS.md`](docs/REELS.md).

| reel | what it isolates |
|---|---|
| [01 · easing curves](reels/01-easing-curves.html) | linear vs `ease-in-out` vs `cubic-bezier(.34,1.56,.64,1)` on one clock, one distance, one duration |
| [02 · spring vs tween](reels/02-spring-vs-tween.html) | overshoot, settling tails and mid-flight retargeting |
| [03 · keyframe spacing](reels/03-keyframe-spacing.html) | slow-in / slow-out from spacing alone, with linear in-betweens everywhere |

Open [`reels/index.html`](reels/index.html) in a browser. No build step is needed
to *use* a reel: each page is one file, inline CSS and JS, no CDN, no network.
`?still=1&t=0.42` freezes a frame.

## Working on it

```bash
python3 tools/build.py           # regenerate reels/ and docs/MEASUREMENTS.md
python3 tools/build.py --check   # fail on stale output or any external resource
python3 tools/measure.py         # independent Python maths → docs/MEASUREMENTS.md
python3 tools/verify.py          # page readouts == measure.py (needs playwright)
python3 tools/shoot.py           # one headless screenshot per reel
```

The HTML in `reels/` is **generated**. Edit `tools/gen_reel_*.py`, then run
`tools/build.py`; `--check` in CI is what keeps that honest.

The screenshot and verify steps need a browser. If none is available they report
`DEFERRED` (and write `build/shots/DEFERRED.md`) instead of passing quietly.
