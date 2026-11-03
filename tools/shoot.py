"""Headless screenshot per reel — the CI "device step", with an honest fallback.

    python3 tools/shoot.py [--out build/shots] [--t 0.42]

Each reel is loaded through its deterministic frame URL
(`file://...?still=1&t=0.42`), so the PNG is a fact about the reel rather than
whichever requestAnimationFrame tick happened to be painted.

Order of attempts:
  1. Playwright + Chromium, if `playwright` imports and a browser is installed.
  2. A `chromium` / `chromium-browser` / `google-chrome` binary on PATH.
  3. Nothing → write DEFERRED.md next to the (absent) shots and exit 0.

Exit code 0 in the deferred case is deliberate: the workflow should not go red
because a CI image lacks a browser, but it must say so in the artefact and in
the job log, not pretend a screenshot exists.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REELS = ROOT / "reels"

REEL_FILES = [
    "index.html",
    "01-easing-curves.html",
    "02-spring-vs-tween.html",
    "03-keyframe-spacing.html",
]

CHROME_CANDIDATES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")


def url_for(path: Path, t: float) -> str:
    return f"{path.as_uri()}?still=1&t={t}"


def shoot_playwright(targets: list[tuple[Path, Path]], t: float, scale: int) -> str | None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", f"--force-device-scale-factor={scale}"])
            page = browser.new_page(viewport={"width": 1100, "height": 900},
                                    device_scale_factor=scale)
            for src, out in targets:
                page.goto(url_for(src, t), wait_until="load")
                page.wait_for_timeout(250)
                page.screenshot(path=str(out), full_page=True)
                print(f"  shot {out.name}  ({url_for(src, t).split('/')[-1]})")
            browser.close()
        return "playwright/chromium"
    except Exception as exc:  # browser missing even though the package is installed
        print(f"  playwright present but unusable: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        return None


def shoot_binary(binary: str, targets: list[tuple[Path, Path]], t: float, scale: int = 2) -> str | None:
    for src, out in targets:
        cmd = [binary, "--headless=new", "--no-sandbox", "--hide-scrollbars",
               f"--force-device-scale-factor={scale}", "--window-size=1100,1500",
               f"--screenshot={out}", url_for(src, t)]
        run = subprocess.run(cmd, capture_output=True, text=True)
        if run.returncode != 0 or not out.exists():
            print(f"  {binary} failed on {src.name}: {run.stderr.strip().splitlines()[:1]}")
            return None
        print(f"  shot {out.name} via {binary}")
    return f"{binary} --headless"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="build/shots")
    ap.add_argument("--t", type=float, default=0.42, help="frozen frame, 0..1 of the cycle")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor (2 = retina)")
    args = ap.parse_args(argv)

    outdir = (ROOT / args.out) if not os.path.isabs(args.out) else Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    targets = [(REELS / name, outdir / (Path(name).stem + ".png")) for name in REEL_FILES]
    missing = [src.name for src, _ in targets if not src.exists()]
    if missing:
        print(f"FAILED: missing reels: {', '.join(missing)} (run tools/build.py)", file=sys.stderr)
        return 1

    engine = shoot_playwright(targets, args.t, args.scale)
    if engine is None:
        for candidate in CHROME_CANDIDATES:
            binary = shutil.which(candidate)
            if binary:
                engine = shoot_binary(binary, targets, args.t, args.scale)
                if engine:
                    break

    if engine is None:
        note = outdir / "DEFERRED.md"
        note.write_text(
            "# Screenshot step deferred\n\n"
            f"Run at {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} (UTC) "
            "by `tools/shoot.py`.\n\n"
            "No headless browser was available to this runner: `playwright` is not importable\n"
            "(or has no browser installed) and no `chromium`/`chrome` binary is on PATH.\n\n"
            "**So there are no screenshots in this run.** That is a missing artefact, not a\n"
            "passing step. Nothing about the reels was verified visually here.\n\n"
            "To close the gap, on any machine with a browser:\n\n"
            "```\n"
            "python3 -m pip install playwright\n"
            "python3 -m playwright install --with-deps chromium\n"
            "python3 tools/build.py          # regenerate reels\n"
            "python3 tools/shoot.py          # writes build/shots/*.png\n"
            "```\n\n"
            f"Frames were to be frozen at t = {args.t} of each cycle via `?still=1&t=`,\n"
            "so the output is reproducible once a browser exists.\n",
            encoding="utf-8",
        )
        try:
            shown = note.relative_to(ROOT)
        except ValueError:
            shown = note
        print(f"\nDEFERRED — no browser available; wrote {shown}")
        print("::warning::screenshot step deferred: no headless browser on this runner")
        return 0

    sizes = ", ".join(f"{p.name} {p.stat().st_size // 1024} KB" for _, p in targets if p.exists())
    print(f"\n{len([1 for _, p in targets if p.exists()])} screenshots via {engine} at t={args.t}")
    print("  " + sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
