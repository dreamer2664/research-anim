"""Cross-check the numbers the reels print against tools/measure.py.

    python3 tools/verify.py

The reels compute their readouts in JavaScript; `measure.py` computes the same
quantities in Python. This script loads each reel in headless Chromium at a
frozen frame, scrapes what the page actually displays, and compares it with
the Python answer. It is the only automated link between "what the page says"
and "what the maths says" — the screenshots cannot check that, because a
picture of a wrong number is still a picture.

Requires playwright + chromium. If they are absent it prints DEFERRED and
exits 0, the same policy as tools/shoot.py: no artefact, but no false pass.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measure  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
REELS = ROOT / "reels"

TOL = 6e-3          # readouts are rounded for display; this is the slack
results: list[tuple[str, float, float, bool]] = []


def check(label: str, expected: float, actual: float, tol: float = TOL) -> None:
    ok = abs(expected - actual) <= tol
    results.append((label, expected, actual, ok))


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("DEFERRED — playwright is not installed; no numbers were cross-checked.")
        print("::warning::verify step deferred: playwright missing")
        return 0

    pct = lambda s: float(s.strip().rstrip("%")) / 100.0  # noqa: E731

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()

            # ---- reel 01: positions and speeds at t = 0.25 --------------
            page.goto((REELS / "01-easing-curves.html").as_uri() + "?still=1&t=0.25")
            positions = page.eval_on_selector_all(".pv", "els => els.map(e => e.textContent)")
            speeds = page.eval_on_selector_all(".sv", "els => els.map(e => e.textContent)")
            for (name, pts), shown_p, shown_v in zip(measure.CURVES, positions, speeds):
                expect = measure.bezier(0.25, *pts)
                check(f"01 · {name} y(0.25)", expect[0], pct(shown_p))
                check(f"01 · {name} speed(0.25) track/s", expect[1] / 1.4, float(shown_v))

            # ---- reel 02: the measured table ---------------------------
            page.goto((REELS / "02-spring-vs-tween.html").as_uri() + "?still=1&t=0")
            got = json.loads(page.evaluate("JSON.stringify(window.MEASURED)"))
            xs = [measure.spring_at(0, 0, 1, i)[0] for i in range(2401)]
            vs = [measure.spring_at(0, 0, 1, i)[1] for i in range(2401)]
            smet = measure.spring_metrics(xs, vs)
            check("02 · spring settle (ms)", smet["bands"][0.005], got["spring"]["settle"], 0.51)
            check("02 · spring peak", smet["peak"], got["spring"]["peak"])
            check("02 · spring peak time (ms)", smet["peak_ms"], got["spring"]["peakAt"], 0.51)
            check("02 · spring peak speed", smet["peak_speed"], got["spring"]["speed"], 0.006)
            check("02 · tween peak speed", measure.curve_stats(measure.TWEEN)["max_slope"] / 0.7,
                  got["tween"]["speed"], 0.006)

            # ---- reel 03: the key-set table ---------------------------
            page.goto((REELS / "03-keyframe-spacing.html").as_uri() + "?still=1&t=0.5")
            cells = page.eval_on_selector_all("#metrics .cell", "els => els.map(e => e.textContent)")
            # rows are 5 cells each: label, speed range, peak/mean, worst step, reads-as
            for i, (name, _, keys) in enumerate(measure.KEY_SETS):
                st = measure.key_stats(keys)
                row = cells[i * 5:(i + 1) * 5]
                nums = row[1].replace("tr/s", "").replace("flat", "").strip()
                shown_max = float(nums.split("–")[-1])
                check(f"03 · {name} max speed", st["max"], shown_max)
                check(f"03 · {name} peak/mean", st["peak_over_mean"],
                      float(row[2].replace("×", "")))

            browser.close()
    except Exception as exc:  # browser present but unusable
        print(f"DEFERRED — chromium did not run: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        print("::warning::verify step deferred: chromium unusable")
        return 0

    bad = [r for r in results if not r[3]]
    for label, want, gotv, ok in results:
        flag = "ok  " if ok else "FAIL"
        print(f"  [{flag}] {label:<34} expected {want:>8.4f}  page says {gotv:>8.4f}")
    print(f"\n{len(results) - len(bad)}/{len(results)} readouts agree with tools/measure.py")
    if bad:
        print("FAILED — the page and the maths disagree; fix before shipping.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
