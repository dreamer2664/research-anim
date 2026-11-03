"""Build every REEL page and its docs appendix, or verify they are current.

    python3 tools/build.py            # write reels/*.html + docs/MEASUREMENTS.md
    python3 tools/build.py --check    # exit 1 if any generated file differs

`--check` also runs the purity rules that make a reel self-contained: inline
CSS/JS only, no <link>, no remote <script src>, no @import, no remote images
or fonts. The generated files are the artefact, so drift between a generator
and its output is a bug, not a convenience.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure  # noqa: E402
import reelkit  # noqa: E402

GENERATORS = [
    ("gen_index", "index.html"),
    ("gen_reel_01", "01-easing-curves.html"),
    ("gen_reel_02", "02-spring-vs-tween.html"),
    ("gen_reel_03", "03-keyframe-spacing.html"),
]

# Strings that look like URLs but are not fetches.
ALLOWED_URLS = ("http://www.w3.org/2000/svg",)

PURITY_RULES = [
    (re.compile(r"<link\b", re.I), "<link> element (external stylesheet/font)"),
    (re.compile(r"<script[^>]+\bsrc\s*=", re.I), "<script src=...> (external script)"),
    (re.compile(r"@import", re.I), "@import rule"),
    (re.compile(r"url\(\s*['\"]?(?:https?:)?//", re.I), "url(...) pointing off-document"),
    (re.compile(r"<img\b", re.I), "<img> element"),
    (re.compile(r"<iframe\b", re.I), "<iframe> element"),
]


def purity_problems(html: str) -> list[str]:
    problems = [label for rx, label in PURITY_RULES if rx.search(html)]
    stripped = html
    for allowed in ALLOWED_URLS:
        stripped = stripped.replace(allowed, "")
    for m in re.finditer(r"\bhttps?://[^\s\"'<>)]+", stripped):
        problems.append(f"remote URL {m.group(0)}")
    if "<style>" not in html or "<script>" not in html:
        problems.append("expected inline <style> and <script>")
    return problems


def digest(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def sync(target: Path, content: str, check: bool, failures: list[str], label: str) -> tuple[str, int, str]:
    """Write `content` to `target`, or verify it already matches. Returns a report row."""
    current = target.read_text(encoding="utf-8") if target.exists() else None
    if current == content:
        state = "same"
    elif current is None:
        state = "new"
        if check:
            failures.append(f"{label}: missing (run tools/build.py)")
    else:
        state = "stale"
        if check:
            failures.append(f"{label}: stale — regenerating changed it")
    if not check:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return label, len(content.encode("utf-8")), state


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify instead of write")
    args = ap.parse_args(argv)

    reelkit.REELS.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    rows: list[tuple[str, str, int, str]] = []

    for module_name, filename in GENERATORS:
        html = importlib.import_module(module_name).render()
        for problem in purity_problems(html):
            failures.append(f"{filename}: not self-contained: {problem}")
        label, size, state = sync(reelkit.REELS / filename, html, args.check, failures, filename)
        rows.append((label, digest(html), size, state))

    md = measure.render()
    label, size, state = sync(measure.OUT, md, args.check, failures, "docs/MEASUREMENTS.md")
    rows.append((label, digest(md), size, state))

    width = max(len(r[0]) for r in rows)
    for label, sha, size, state in rows:
        print(f"  {label:<{width}}  {sha}  {size:>7,} B  {state}")

    if failures:
        print("\nFAILED", file=sys.stderr)
        for f in failures:
            print("  - " + f, file=sys.stderr)
        return 1

    print("\nall reels self-contained; generated files match their generators" if args.check
          else f"\nwrote {len(rows)} generated files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
