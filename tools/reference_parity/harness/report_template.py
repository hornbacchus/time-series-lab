"""Standardized markdown audit-report emission template.

Phase 3 Session 5 abstraction: factor the per-wrapper
report-emission boilerplate from the 10 manually-written
Batch 1 reports under ``tools/reference_parity/reports/
p3_*_audit.md``. Provides a single ``render_audit_report``
function that produces a consistent markdown structure
across Phase 3 wrappers.

**Use is OPTIONAL.** Batch 1 reports were hand-written and
remain so (sentinel cases, not regenerated). Future batches
may use this template to reduce per-report boilerplate; per-
wrapper sections (Documented divergences, Notes) remain
hand-written when the audit surfaces wrapper-specific
findings.

Per master plan §16.3: per-wrapper reports live at
``tools/reference_parity/reports/p3_<wrapper>_audit.md``;
per-batch summaries at ``p3_batch_<N>_summary.md``.

Public surface
--------------

``render_audit_report(metadata: AuditMetadata) -> str``
    Returns the full markdown body. Caller writes to disk.

``AuditMetadata`` dataclass
    Carries all per-audit fields the template needs.
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class AuditMetadata:
    """Carrier for ``render_audit_report``. Every field is
    required; report sections are conditional on field
    contents (e.g., empty divergences list → omit the
    section)."""

    # Header
    wrapper_path: str  # e.g. "engine/techniques/garch_model.py"
    audit_id: str  # e.g. "p3_garch"
    batch: int  # 1-10
    session: int  # session number
    date: str  # ISO YYYY-MM-DD
    verdict: str  # PASS / CAVEAT / BLOCK / DOCUMENTED-DIVERGENCE / NO-REFERENCE

    # §1 Reference
    primary_reference: str  # description of R or Python ref
    cross_check_reference: str  # or "None" / "N/A"
    methodology_note: str  # brief equivalence/divergence sketch

    # §2 Fixture
    fixture_summary: dict[str, Any]
    fixture_notes: str  # multi-line; appended verbatim

    # §3 Output-tier mapping
    primary_outputs: list[str]
    secondary_outputs: list[str]
    diagnostic_outputs: list[str]

    # §4 Tolerance ladder summary
    tolerance_class: str  # e.g. "MLE-fit" / "closed-form"
    tolerance_table_rows: list[tuple[str, float, float, float, float]]
    # rows = [(tier, abs_tol, rel_tol, block_abs_tol, block_rel_tol), ...]

    # §5 Achieved metrics — each entry is a metric name + its
    # status + abs_diff + rel_diff (free-form for vector vs
    # scalar; caller formats values appropriately)
    primary_metric_rows: list[tuple[str, str, str, str, str]]
    # rows = [(metric, tsl_str, ref_str, abs_diff, rel_diff_or_status), ...]
    secondary_metric_rows: list[tuple[str, str, str, str, str]]

    # §6 Documented divergences (empty list → "None.")
    divergences: list[str]

    # §7 Runtime
    runtime_seconds: str  # e.g. "1.5–4.0s"

    # §8 Reference version snapshot
    version_snapshot: dict[str, str]

    # §10 Notes (free-form paragraph)
    notes: str


def render_audit_report(metadata: AuditMetadata) -> str:
    """Render the markdown body for an audit report.

    The structure mirrors Batch 1's hand-written reports
    (sections 1–10). Empty fields trigger graceful section
    omission rather than empty headings.
    """
    md = metadata
    lines: list[str] = []

    # Header
    lines.append(f"# P3 — `{md.wrapper_path.split('/')[-1]}` reference parity audit")
    lines.append("")
    lines.append(f"**Wrapper:** `{md.wrapper_path}`")
    lines.append(f"**Audit ID:** `{md.audit_id}`")
    lines.append(f"**Batch / Session:** Phase 3 Batch {md.batch} / Session {md.session}")
    lines.append(f"**Date:** {md.date}")
    lines.append(f"**Verdict:** **{md.verdict}**")
    lines.append("")

    # §1 Reference
    lines.append("## 1. Reference")
    lines.append("")
    lines.append(f"- **Primary:** {md.primary_reference}")
    lines.append(f"- **Cross-check:** {md.cross_check_reference}")
    lines.append("")
    if md.methodology_note:
        lines.append(md.methodology_note)
        lines.append("")

    # §2 Fixture
    lines.append("## 2. Fixture")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    for k, v in md.fixture_summary.items():
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    if md.fixture_notes:
        lines.append(md.fixture_notes)
        lines.append("")

    # §3 Output-tier mapping
    lines.append("## 3. Output-tier mapping")
    lines.append("")
    lines.append("| Tier | Outputs |")
    lines.append("|---|---|")
    if md.primary_outputs:
        lines.append(f"| **Primary** | {', '.join(md.primary_outputs)} |")
    if md.secondary_outputs:
        lines.append(f"| **Secondary** | {', '.join(md.secondary_outputs)} |")
    if md.diagnostic_outputs:
        lines.append(f"| **Diagnostic** | {', '.join(md.diagnostic_outputs)} |")
    lines.append("")

    # §4 Tolerance ladder
    lines.append("## 4. Tolerance ladder")
    lines.append("")
    lines.append(f"Tolerance class: **{md.tolerance_class}**.")
    lines.append("")
    lines.append("| Tier | abs_tol | rel_tol | block_abs_tol | block_rel_tol |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in md.tolerance_table_rows:
        tier_n, abs_t, rel_t, b_abs, b_rel = row
        lines.append(f"| {tier_n} | {abs_t} | {rel_t} | {b_abs} | {b_rel} |")
    lines.append("")

    # §5 Achieved metrics
    lines.append("## 5. Achieved metrics")
    lines.append("")
    if md.primary_metric_rows:
        lines.append("### Primary")
        lines.append("")
        lines.append("| Metric | TSL | Reference | abs_diff | rel_diff | Status |")
        lines.append("|---|---|---|---:|---:|---|")
        for row in md.primary_metric_rows:
            metric, tsl, ref, abs_d, rel_or_status = row
            lines.append(f"| {metric} | {tsl} | {ref} | {abs_d} | {rel_or_status} |")
        lines.append("")
    if md.secondary_metric_rows:
        lines.append("### Secondary")
        lines.append("")
        lines.append("| Metric | TSL | Reference | abs_diff | rel_diff | Status |")
        lines.append("|---|---|---|---:|---:|---|")
        for row in md.secondary_metric_rows:
            metric, tsl, ref, abs_d, rel_or_status = row
            lines.append(f"| {metric} | {tsl} | {ref} | {abs_d} | {rel_or_status} |")
        lines.append("")

    # §6 Documented divergences
    lines.append("## 6. Documented divergences")
    lines.append("")
    if md.divergences:
        for i, div in enumerate(md.divergences, 1):
            lines.append(f"**{i}.** {div}")
            lines.append("")
    else:
        lines.append("**None.**")
        lines.append("")

    # §7 Runtime
    lines.append("## 7. Runtime")
    lines.append("")
    lines.append(md.runtime_seconds)
    lines.append("")

    # §8 Reference version snapshot
    lines.append("## 8. Reference version snapshot")
    lines.append("")
    for pkg, ver in md.version_snapshot.items():
        lines.append(f"- {pkg}: {ver}")
    lines.append("")

    # §9 Outcome (derived from verdict + divergences)
    lines.append("## 9. Outcome")
    lines.append("")
    lines.append(
        f"**{md.verdict}.** "
        f"{'See §6 for documented divergences.' if md.divergences else 'No divergences observed beyond stated tolerances.'}"
    )
    lines.append("")

    # §10 Notes
    if md.notes:
        lines.append("## 10. Notes")
        lines.append("")
        lines.append(md.notes)
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "AuditMetadata",
    "render_audit_report",
]
