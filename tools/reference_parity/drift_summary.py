"""Drift canary summary (H1): what changes when the fast tier runs against
the LATEST unpinned packages instead of the validated (pinned) ones.

    python tools/reference_parity/drift_summary.py \
        --pinned parity-fast.json --canary parity-canary.json \
        [--pinned-env env-pinned.txt --canary-env env-canary.txt]

Compares the two runs check by check (outcome, and the first line of the
error) and, when given the environment listings the jobs record, lists every
package whose version differs. Writes Markdown to $GITHUB_STEP_SUMMARY when
set (else stdout) and one GitHub warning annotation per changed check.

Never gates: exits 0 whatever it finds (a missing or unreadable input is
reported, not raised). The canary warns about the next lock refresh; the
pinned job is the gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def load_results(path: str) -> tuple[dict[str, dict], str]:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        start = text.find("[")
        data = json.loads(text[start:]) if start >= 0 else []
        return {r["technique_id"]: r for r in data if isinstance(r, dict) and "technique_id" in r}, ""
    except Exception as e:  # reported, never raised: the canary must not gate
        return {}, f"{path}: {type(e).__name__}: {e}"


def load_env(path: str | None) -> dict[str, str]:
    """``name==version`` (pip freeze) and ``R:name==version`` lines."""
    if not path or not Path(path).is_file():
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*((?:R:)?[A-Za-z0-9][A-Za-z0-9_.\-]*)\s*==\s*(\S+)", line)
        if m:
            key = m.group(1)
            out[key if key.startswith("R:") else re.sub(r"[-_.]+", "-", key).lower()] = m.group(2)
    return out


def first_line(s: str | None) -> str:
    return (s or "").strip().splitlines()[0][:200] if (s or "").strip() else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", required=True)
    ap.add_argument("--canary", required=True)
    ap.add_argument("--pinned-env")
    ap.add_argument("--canary-env")
    args = ap.parse_args()

    pinned, perr = load_results(args.pinned)
    canary, cerr = load_results(args.canary)
    in_actions = "GITHUB_ACTIONS" in os.environ
    lines = ["## Drift canary: fast tier, latest unpinned packages vs the validated pins", ""]
    if perr or cerr or not pinned or not canary:
        lines += [f"Could not compare: {perr or ''} {cerr or ''} "
                  f"(pinned results: {len(pinned)}, canary results: {len(canary)})".strip()]
    changed = []
    for tid in sorted(set(pinned) | set(canary)):
        p, c = pinned.get(tid), canary.get(tid)
        po = p["outcome"] if p else "(absent)"
        co = c["outcome"] if c else "(absent)"
        pe, ce = first_line(p and p.get("error")), first_line(c and c.get("error"))
        if po != co or pe != ce:
            changed.append((tid, po, co, ce or pe))
    if pinned and canary:
        lines.append(f"{len(changed)} of {len(set(pinned) | set(canary))} checks change "
                     "under the latest packages.")
        lines.append("")
        if changed:
            lines += ["| Check | Pinned | Latest | Latest error (first line) |", "|---|---|---|---|"]
            for tid, po, co, err in changed:
                lines.append(f"| {tid} | {po} | {co} | {err.replace('|', '/')} |")
                msg = f"{tid}: {po} (pinned) -> {co} (latest)" + (f" - {err}" if err else "")
                print(f"::warning title=Drift canary::{msg}" if in_actions else f"WARNING: {msg}")
    pe_env, ce_env = load_env(args.pinned_env), load_env(args.canary_env)
    if pe_env and ce_env:
        diffs = sorted(
            (k, pe_env.get(k, "-"), ce_env.get(k, "-"))
            for k in set(pe_env) | set(ce_env)
            if pe_env.get(k) != ce_env.get(k)
        )
        lines += ["", f"### {len(diffs)} package versions differ (pinned -> latest)", ""]
        if diffs:
            lines += ["| Package | Pinned | Latest |", "|---|---|---|"]
            lines += [f"| {k} | {a} | {b} |" for k, a, b in diffs]
    text = "\n".join(lines) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
