"""Ground-truth numbers behind the reels — and the appendix they generate.

    python3 tools/measure.py            # write docs/MEASUREMENTS.md
    python3 tools/measure.py --print    # print the tables to stdout

Nothing here imports the reels; this is an independent implementation of the
same maths in Python, so `tools/verify.py` can cross-check the numbers the
pages print against a second opinion. If a number in docs/REELS.md is not in
this file or in MEASUREMENTS.md, it was typed by hand and should be treated
with suspicion.

The one place the two implementations are allowed to differ is documented on
purpose: the reels solve the spring in closed form, while a production engine
integrates it. Section 3 quantifies that gap instead of hand-waving it.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "MEASUREMENTS.md"

# --------------------------------------------------------------------------
# cubic-bezier timing functions
# --------------------------------------------------------------------------


def _abc(a1: float, a2: float) -> tuple[float, float, float]:
    return 1 - 3 * a2 + 3 * a1, 3 * a2 - 6 * a1, 3 * a1


def _calc(u: float, a1: float, a2: float) -> float:
    a, b, c = _abc(a1, a2)
    return ((a * u + b) * u + c) * u


def _slope(u: float, a1: float, a2: float) -> float:
    a, b, c = _abc(a1, a2)
    return 3 * a * u * u + 2 * b * u + c


def solve_u(x: float, x1: float, x2: float) -> float:
    """Invert x(u) = x by bisection (the reels use Newton first; same root)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lo, hi = 0.0, 1.0
    u = x
    for _ in range(90):
        v = _calc(u, x1, x2)
        if abs(v - x) < 1e-13:
            break
        if v < x:
            lo = u
        else:
            hi = u
        u = (lo + hi) / 2
    return u


def bezier(x: float, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """(y, dy/dx) at progress x — the second value is the curve's speed."""
    u = solve_u(x, x1, x2)
    dx = _slope(u, x1, x2)
    dy = _slope(u, y1, y2)
    return _calc(u, y1, y2), (dy / dx if abs(dx) > 1e-9 else 0.0)


def curve_stats(points: tuple[float, float, float, float], n: int = 4000) -> dict:
    x1, y1, x2, y2 = points
    vals = [bezier(i / n, x1, y1, x2, y2) for i in range(n + 1)]
    slopes = [s for _, s in vals]
    ys = [y for y, _ in vals]
    peak_i = max(range(n + 1), key=lambda i: ys[i])
    fast_i = max(range(n + 1), key=lambda i: abs(slopes[i]))
    return {
        "y25": bezier(0.25, x1, y1, x2, y2)[0],
        "y50": bezier(0.5, x1, y1, x2, y2)[0],
        "peak": ys[peak_i],
        "peak_x": peak_i / n,
        "max_slope": abs(slopes[fast_i]),
        "max_slope_x": fast_i / n,
        "min_slope": min(slopes),
    }


# --------------------------------------------------------------------------
# damped spring: closed form and a small numerical integrator
# --------------------------------------------------------------------------

M, K, C = 1.0, 120.0, 14.0


def spring_params(m: float = M, k: float = K, c: float = C) -> dict:
    w0 = math.sqrt(k / m)
    zeta = c / (2 * math.sqrt(k * m))
    wd = w0 * math.sqrt(1 - zeta * zeta)
    return {"m": m, "k": k, "c": c, "w0": w0, "zeta": zeta, "wd": wd, "lam": zeta * w0,
            "fd": wd / (2 * math.pi)}


def spring_at(x0: float, v0: float, target: float, ms: float, sp: dict | None = None) -> tuple[float, float]:
    sp = sp or spring_params()
    t = max(0.0, ms) / 1000.0
    e = math.exp(-sp["lam"] * t)
    A = x0 - target
    B = (v0 + sp["lam"] * A) / sp["wd"]
    cos, sin = math.cos(sp["wd"] * t), math.sin(sp["wd"] * t)
    x = target + e * (A * cos + B * sin)
    v = e * ((B * sp["wd"] - sp["lam"] * A) * cos - (A * sp["wd"] + sp["lam"] * B) * sin)
    return x, v


def euler_run(ms_max: int = 2400, step_ms: float = 0.5, x0: float = 0.0, target: float = 1.0,
              sp: dict | None = None) -> tuple[list[float], list[float]]:
    """Semi-implicit Euler at `step_ms` — what an engine without a closed form does."""
    sp = sp or spring_params()
    h = step_ms / 1000.0
    per_ms = int(round(1 / step_ms))
    x, v = x0, 0.0
    xs, vs = [x], [v]
    for _ in range(ms_max):
        for _ in range(per_ms):
            a = (-sp["k"] * (x - target) - sp["c"] * v) / sp["m"]
            v += a * h
            x += v * h
        xs.append(x)
        vs.append(v)
    return xs, vs


def spring_metrics(xs: list[float], vs: list[float], bands=(0.02, 0.01, 0.005, 0.001, 0.0001)) -> dict:
    peak = max(xs)
    out = {
        "peak": peak,
        "peak_ms": xs.index(peak),
        "peak_speed": max(abs(v) for v in vs),
        "peak_speed_ms": max(range(len(vs)), key=lambda i: abs(vs[i])),
        "crossings": sum(1 for i in range(1, len(xs)) if (xs[i - 1] - 1) * (xs[i] - 1) < 0),
        "bands": {},
    }
    for b in bands:
        last = max(i for i, x in enumerate(xs) if abs(x - 1) > b)
        out["bands"][b] = last + 1
    return out


# --------------------------------------------------------------------------
# keyframe sets (reel 03)
# --------------------------------------------------------------------------


def ease_in_out(x: float) -> float:
    return bezier(x, 0.42, 0.0, 0.58, 1.0)[0]


KEY_SETS = [
    ("even spacing", "9 keys, value = k/8", [(k / 8, k / 8) for k in range(9)]),
    ("slow-in / slow-out", "9 keys, value = easeInOut(k/8)", [(k / 8, ease_in_out(k / 8)) for k in range(9)]),
    ("three keys", "3 keys at t = 0, 0.25, 1", [(0.0, 0.0), (0.25, 0.5), (1.0, 1.0)]),
]


def key_stats(keys: list[tuple[float, float]], dur_s: float = 1.8) -> dict:
    segs = []
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        slope = (v1 - v0) / (t1 - t0)
        segs.append({"t0": t0, "t1": t1, "dv": v1 - v0, "speed": slope / dur_s})
    speeds = [s["speed"] for s in segs]
    step = 0.0
    for a, b in zip(speeds, speeds[1:]):
        if abs(b - a) > abs(step):
            step = b - a
    mean = 1 / dur_s
    return {"segs": segs, "min": min(speeds), "max": max(speeds), "mean": mean,
            "peak_over_mean": max(speeds) / mean, "step": step}


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------

CURVES = [
    ("linear", (0.0, 0.0, 1.0, 1.0)),
    ("ease-in-out", (0.42, 0.0, 0.58, 1.0)),
    ("ease-out-back", (0.34, 1.56, 0.64, 1.0)),
]
TWEEN = (0.22, 1.0, 0.36, 1.0)
TWEEN_MS = 700


def render() -> str:
    sp = spring_params()
    xs, vs = [spring_at(0, 0, 1, i, sp)[0] for i in range(2401)], [spring_at(0, 0, 1, i, sp)[1] for i in range(2401)]
    smet = spring_metrics(xs, vs)

    ex, ev = euler_run()
    emet = spring_metrics(ex, ev)
    dev = max(abs(a - b) for a, b in zip(xs, ex))

    L: list[str] = []
    add = L.append

    add("# Measurements\n")
    add("Generated by `python3 tools/measure.py`. Do not edit by hand — the reels are built from")
    add("the same formulas, and `tools/build.py --check` fails if this file drifts from the code.")
    add("")
    add("Units: one **track** = the length of the rail in a reel. Speeds are track widths per")
    add("second, so they are comparable across reels with different rails and durations.")
    add("")

    # 1
    add("## 1 · Timing curves (reel 01)\n")
    add("Duration 1400 ms, distance 1 track. `dy/dx` is the curve's speed at that instant,")
    add("in track widths per unit of progress; multiplying by 1/1.4 s gives track/s.")
    add("")
    add("| curve | control points | y(0.25) | y(0.5) | peak y | max dy/dx | at x | min dy/dx |")
    add("|---|---|---|---|---|---|---|---|")
    for name, pts in CURVES:
        s = curve_stats(pts)
        add(f"| {name} | `cubic-bezier({pts[0]:g}, {pts[1]:g}, {pts[2]:g}, {pts[3]:g})` "
            f"| {s['y25']:.4f} | {s['y50']:.4f} | {s['peak']:.4f} | {s['max_slope']:.3f} "
            f"| {s['max_slope_x']:.3f} | {s['min_slope']:.3f} |")
    add("")
    add("Speed in track/s = dy/dx ÷ 1.4 s, so the frame's fastest instant is "
        f"{max(curve_stats(p)['max_slope'] for _, p in CURVES) / 1.4:.2f} track/s "
        "(the back-out curve, at x → 0).")
    add("")

    # 2
    add("## 2 · Damped spring (reel 02)\n")
    add(f"m = {sp['m']:g}, k = {sp['k']:g}, c = {sp['c']:g} → "
        f"ω₀ = {sp['w0']:.3f} rad/s, ζ = {sp['zeta']:.4f}, "
        f"ω_d = {sp['wd']:.3f} rad/s (f_d = {sp['fd']:.3f} Hz, period {1000 / sp['fd']:.1f} ms).")
    add("")
    add("Closed form: x(t) = T + e^(−ζω₀t)·(A cos ω_d t + B sin ω_d t), "
        "A = x₀ − T, B = (v₀ + ζω₀A)/ω_d.")
    add("")
    add(f"- Analytic overshoot exp(−ζπ/√(1−ζ²)) = "
        f"{math.exp(-sp['zeta'] * math.pi / math.sqrt(1 - sp['zeta'] ** 2)) * 100:.3f}%")
    add(f"- Measured peak {smet['peak']:.5f} at {smet['peak_ms']} ms")
    add(f"- Peak speed {smet['peak_speed']:.3f} track/s at {smet['peak_speed_ms']} ms")
    add(f"- Crossings of the target: {smet['crossings']}")
    add("- Decay per half cycle (same factor as the overshoot): "
        f"{math.exp(-sp['zeta'] * math.pi / math.sqrt(1 - sp['zeta'] ** 2)):.4f} — "
        "so the swings run +7.354%, −0.541%, +0.040%, −0.003%")
    add("")
    add("| settled within | time (closed form) |")
    add("|---|---|")
    for b, t in smet["bands"].items():
        add(f"| ±{b * 100:g}% | {t} ms |")
    add("")

    # 3
    add("## 3 · Closed form vs a numerical integrator (reel 02 caveat)\n")
    add("The reels evaluate the exact solution. A production engine steps the ODE instead;")
    add("this is how far a plain semi-implicit Euler at 2 kHz lands from the truth, which is")
    add("the honest size of the 'not your engine' caveat.")
    add("")
    add("| quantity | closed form | Euler @ 2 kHz | difference |")
    add("|---|---|---|---|")
    add(f"| max abs deviation | — | — | {dev:.2e} ({dev * 100:.3f}% of the track) |")
    add(f"| peak position | {smet['peak']:.5f} | {emet['peak']:.5f} | {(emet['peak'] - smet['peak']) * 1e3:+.2f}e-3 |")
    add(f"| settled ±0.5% | {smet['bands'][0.005]} ms | {emet['bands'][0.005]} ms "
        f"| {emet['bands'][0.005] - smet['bands'][0.005]:+d} ms |")
    add(f"| settled ±0.1% | {smet['bands'][0.001]} ms | {emet['bands'][0.001]} ms "
        f"| {emet['bands'][0.001] - smet['bands'][0.001]:+d} ms |")
    add(f"| peak speed | {smet['peak_speed']:.3f} | {emet['peak_speed']:.3f} "
        f"| {emet['peak_speed'] - smet['peak_speed']:+.3f} track/s |")
    add("")

    # 4
    add("## 4 · The tween (reel 02)\n")
    ts = curve_stats(TWEEN)
    peak_speed = ts["max_slope"] / (TWEEN_MS / 1000)
    add(f"`cubic-bezier({TWEEN[0]:g}, {TWEEN[1]:g}, {TWEEN[2]:g}, {TWEEN[3]:g})` over {TWEEN_MS} ms:")
    add("")
    add(f"- max dy/dx = {ts['max_slope']:.3f} at x = {ts['max_slope_x']:.3f} "
        f"→ peak speed {peak_speed:.2f} track/s")
    half_x = next(i for i in range(1001) if bezier(i / 1000, *TWEEN)[0] >= 0.5) / 1000
    add(f"- half the distance is covered in {half_x * 100:.1f}% of the duration "
        f"(y(0.5) = {ts['y50']:.4f}): front-loaded by construction, since y\u2081 = 1")
    add(f"- peak y = {ts['peak']:.4f}: no overshoot, by construction (control points stay in [0, 1])")
    add(f"- speed at x = 1 is exactly 0, reached at exactly {TWEEN_MS} ms")
    add("")

    # 5
    add("## 5 · Keyframe sets (reel 03)\n")
    add("One 1800 ms move, total distance 1 track, linear in-betweens in every set. Speed is")
    add("constant inside a segment, so a set is fully described by its segment speeds.")
    add("")
    add("| key set | keys | speed range (track/s) | peak ÷ mean | worst step |")
    add("|---|---|---|---|---|")
    for name, desc, keys in KEY_SETS:
        st = key_stats(keys)
        step = "none" if abs(st["step"]) < 1e-9 else f"{st['step']:+.3f} track/s"
        add(f"| {name} | {desc} | {st['min']:.3f} – {st['max']:.3f} | "
            f"{st['peak_over_mean']:.2f}× | {step} |")
    add("")
    add("Segment speeds, in order:")
    add("")
    for name, _, keys in KEY_SETS:
        st = key_stats(keys)
        add(f"- **{name}**: " + ", ".join(f"{s['speed']:.3f}" for s in st["segs"]))
    add("")
    add("Key values for the middle set (the spacing chart, as numbers):")
    add("")
    add("| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    add("| t = k/8 | " + " | ".join(f"{k / 8:.3f}" for k in range(9)) + " |")
    add("| value | " + " | ".join(f"{ease_in_out(k / 8):.4f}" for k in range(9)) + " |")
    add("")
    add("---")
    add("")
    add("Reproduce any row by hand: `tools/measure.py --print` prints these tables to stdout,")
    add("and every formula used is written out in `docs/REELS.md`.")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="print instead of writing docs/MEASUREMENTS.md")
    args = ap.parse_args(argv)
    text = render()
    if args.print:
        sys.stdout.write(text)
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text.encode('utf-8')):,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
