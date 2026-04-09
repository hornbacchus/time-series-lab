#!/usr/bin/env python3
"""
generate_user_guide.py - Build Word User Guide (.docx) from technique + UDF registries.

Reads:
  - resources/catalog/techniques_catalog.json
  - resources/catalog/udf_catalog.json
  - resources/techniques_md/*.md

Outputs:
  - docs/UserGuide_Source.md (generated markdown)
  - docs/TimeSeriesLab_UserGuide.docx (Word document)
"""

import json
import os
import sys
from pathlib import Path

def find_repo_root():
    """Find repo root by looking for TimeSeriesLab.sln."""
    p = Path(__file__).resolve().parent.parent
    if (p / "TimeSeriesLab.sln").exists():
        return p
    p = Path.cwd()
    while p != p.parent:
        if (p / "TimeSeriesLab.sln").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parent.parent

REPO = find_repo_root()
CATALOG_PATH = REPO / "resources" / "catalog" / "techniques_catalog.json"
UDF_CATALOG_PATH = REPO / "resources" / "catalog" / "udf_catalog.json"
TECHNIQUES_MD_DIR = REPO / "resources" / "techniques_md"
OUTPUT_MD = REPO / "docs" / "UserGuide_Source.md"
OUTPUT_DOCX = REPO / "docs" / "TimeSeriesLab_UserGuide.docx"
OUTPUT_HTML = REPO / "docs" / "TimeSeriesLab_UserGuide.html"


def load_catalog():
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"techniques": []}


def load_udf_catalog():
    if UDF_CATALOG_PATH.exists():
        with open(UDF_CATALOG_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {"udfs": []}


def load_technique_md(technique_id):
    md_path = TECHNIQUES_MD_DIR / f"{technique_id}.md"
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")
    return "(No detailed description available.)"


def generate_markdown(catalog, udf_catalog):
    """Generate the full UserGuide_Source.md."""
    lines = []

    def h1(text): lines.append(f"# {text}\n")
    def h2(text): lines.append(f"## {text}\n")
    def h3(text): lines.append(f"### {text}\n")
    def p(text): lines.append(f"{text}\n")
    def blank(): lines.append("")

    h1("Time Series Lab - User Guide")
    blank()
    p("Version 1.0 | Generated automatically from technique and UDF registries.")
    blank()

    # Table of Contents
    h2("Table of Contents")
    p("1. Quick Start")
    p("2. Ribbon Reference")
    p("3. How Selection Works")
    p("4. Time Index Detection")
    p("5. Frequency and Resampling")
    p("6. Presets: Fast / Balanced / Thorough")
    p("7. AUTO vs THOROUGH Formulas")
    p("8. Common Workflows")
    p("9. Audit Log and Reproducibility")
    p("10. Technique Catalog")
    p("11. UDF Reference")
    p("12. Troubleshooting")
    blank()

    # Quick Start
    h2("1. Quick Start (3 Minutes)")
    p("1. Open Excel. The **Time Series Lab** tab appears in the ribbon.")
    p("2. Select your data columns (dates in the leftmost column, values in adjacent columns).")
    p("3. Click a **Quick Action** button (e.g., Seasonal Adjustment, Forecast).")
    p("4. The Task Pane opens with your data pre-loaded. Click **Run**.")
    p("5. Results appear in a new worksheet, along with an Audit sheet for governance.")
    blank()
    p("**Tip:** You can also use worksheet formulas (UDFs) like `=TSL_FORECAST(A2:A100, B2:B100, 12)` directly in cells.")
    blank()

    # Ribbon Reference
    h2("2. Ribbon Reference")
    p("The **Time Series Lab** ribbon tab is organized into four groups:")
    blank()
    h3("Quick Actions")
    p("One-click access to the most common analyses:")
    p("- **Seasonal Adjustment** - Decompose a series into trend, seasonal, and remainder (STL)")
    p("- **Granger Causality** - Test whether one series helps predict another")
    p("- **Lead-Lag Finder** - Find the optimal time delay between two series")
    p("- **Forecast** - Generate forecasts with prediction intervals (Auto ARIMA)")
    p("- **Anomaly Scan** - Detect outliers and anomalous observations")
    blank()
    h3("Explore")
    p("Three ways to discover and choose techniques:")
    p("- **Technique Explorer** (split button) - Browse all techniques. "
      "Click the dropdown arrow to jump directly to one of the 13 technique categories: "
      "Decomposition, Forecasting, Stationarity, Multivariate, State Space, Regimes, "
      "Volatility, Frequency Domain, Change Points, Causality, Evaluation, Missing Data, or ML/Deep Learning.")
    p("- **Recommender** (dropdown menu) - Choose an analysis goal from the dropdown "
      "(Forecast, Describe/Decompose, Detect Anomalies, Test Causality, Explore Relationships, "
      "or Statistical Testing) to start the recommendation wizard with that goal pre-selected. "
      "Or select 'Open full wizard' to walk through all 7 questions.")
    p("- **Data Readiness** - Score your selected data for quality issues before analysis.")
    blank()
    h3("Run")
    p("- **Preset** dropdown - Switch between Fast, Balanced (default), and Thorough presets")
    p("- **Run** - Execute the current technique from the Task Pane")
    p("- **Cancel** - Stop a running computation immediately")
    p("- **Re-run Thorough** - Recompute all THOROUGH formulas in the workbook")
    p("- **Settings** - Open the settings panel (presets, seed, fill method, etc.)")
    blank()
    h3("Help")
    p("- **UDF Formula Guide** - Browse all worksheet functions with examples and a formula builder")
    p("- **User Guide** - Open this document")
    p("- **About** - Version information, engine status, and diagnostics")
    blank()

    # Selection
    h2("3. How Selection Works")
    p("Time Series Lab supports **non-adjacent selections** (hold Ctrl and click multiple columns).")
    p("**Default behavior:** Each selected column is treated as one time series.")
    p("**Row mode:** Available as an override in the Task Pane for panel/cross-sectional data.")
    blank()
    p("**Headers:** The cell directly above your first selected row is used as the series name. "
      "If it looks numeric or is missing, a fallback name like `Col_B` is used.")
    blank()
    p("**Numeric coercion:** By default, string values that look like numbers are coerced. "
      "Non-numeric values become NA. This is configurable in Settings.")
    blank()
    h3("Selecting Non-Adjacent Columns (Multi-Series Techniques)")
    p("Many techniques require two or more data columns that may not be next to each other. "
      "For example, PCA, VAR, VECM, Johansen Cointegration, and Dynamic Factor Model all "
      "need multiple series as input. Time Series Lab fully supports non-adjacent column selection:")
    blank()
    p("**From the Task Pane (recommended):**")
    p("1. Click the first data column (e.g., B2:B100).")
    p("2. Hold **Ctrl** and click additional columns (e.g., D2:D100, F2:F100).")
    p("3. The selection status bar in the Task Pane will show \"3 series, 99 pts\".")
    p("4. Choose a multivariate technique (e.g., PCA, VAR) and click **Run**.")
    p("5. All selected columns are sent to the engine as separate series.")
    blank()
    p("**From a THOROUGH formula:**")
    p("The `TSL_RUN_THR` function accepts up to 5 additional data range parameters "
      "(`data_range_2` through `data_range_5`) after the `options_json` parameter:")
    blank()
    p("```")
    p("=TSL_RUN_THR(\"pca\", A2:A100, B2:B100, TSL_TRIGGER(), \"{}\", D2:D100, F2:F100, H2:H100)")
    p("```")
    blank()
    p("In this example, columns B, D, F, and H are passed as four separate series to the "
      "PCA technique. The primary `data_range` (B2:B100) can also be multi-column if "
      "some columns are adjacent.")
    blank()
    p("**Techniques that benefit from multi-series input:**")
    p("- PCA, Dynamic Factor Model (3+ series recommended)")
    p("- VAR, VECM, Bayesian VAR, Johansen Cointegration (2+ series)")
    p("- Granger Causality, Cross-Correlation, DTW, Wavelet Coherence (exactly 2 series)")
    p("- ARIMAX/SARIMAX, Transfer Function (1 target + exogenous series)")
    p("- Gradient Boosting, XGBoost, Random Forest, LSTM (optional exogenous features)")
    p("- Forecast Reconciliation (hierarchical multi-series)")
    blank()

    # Time Index
    h2("4. Time Index Detection")
    p("Time Series Lab automatically detects the date/time column by scoring candidates on:")
    p("- **Parseability:** What fraction of values are valid dates?")
    p("- **Monotonicity:** Are dates in increasing order?")
    p("- **Uniqueness:** Are there duplicate dates?")
    p("- **Regularity:** Are intervals consistent (with weekend-gap handling)?")
    blank()
    p("The best candidate above a confidence threshold is selected automatically. "
      "If no candidate scores high enough, you'll be prompted to select the date column.")
    blank()
    p("**Date-only policy:** Timestamps are floored to dates. This is recorded in the audit log.")
    p("**Duplicates:** If duplicate dates exist, they are aggregated using the series aggregation rule.")
    blank()

    # Frequency
    h2("5. Frequency and Resampling")
    p("After detecting the time index, Time Series Lab suggests a frequency:")
    p("- **Business Daily:** Weekends are non-existent (not created as timestamps)")
    p("- **Calendar Daily:** Every calendar day")
    p("- **Weekly:** Uses ISO week numbering")
    p("- **Monthly, Quarterly, Annual**")
    blank()
    p("You confirm the frequency before running. If irregular/missing dates exist, "
      "confirmation is required.")
    blank()
    h3("Resampling Aggregation (per series)")
    p("- **Flow variables** (e.g., sales): SUM")
    p("- **Rate variables** (e.g., prices): MEAN")
    p("- **Stock variables** (e.g., inventory): LAST")
    blank()
    h3("Missing Data Filling")
    p("Default: **Kalman smoothing** after resampling.")
    p("- Filled points are always flagged in the output.")
    p("- If missingness > 15% or max gap > 10 periods: strong warning + user confirmation required.")
    blank()

    # Presets
    h2("6. Presets: Fast / Balanced / Thorough")
    p("| Preset | Speed | Diagnostics | Model Search | CV Folds | Use Case |")
    p("|--------|-------|-------------|-------------|----------|----------|")
    p("| **Fast** | Fastest | Minimal | Safe defaults | None | Interactive exploration |")
    p("| **Balanced** | Moderate | Standard | Moderate candidates | 3-fold | General use (default) |")
    p("| **Thorough** | Slowest | Full | Wide search | 5-fold | Publication / audit |")
    blank()
    p("**Thorough** is always manual (handle-based) in formulas. It never surprises you with long recalculation.")
    blank()

    # AUTO vs THOROUGH
    h2("7. AUTO vs THOROUGH Formulas")
    p("Time Series Lab provides two lanes of worksheet formulas:")
    blank()
    p("| Feature | AUTO | THOROUGH |")
    p("|---------|------|----------|")
    p("| Function prefix | `TSL_*` | `TSL_*_THR` or `TSL_RUN_THR` |")
    p("| Category | \"AUTO (recomputes)\" | \"THOROUGH (manual handles)\" |")
    p("| Description | Starts with \"AUTO:\" | Starts with \"THOROUGH:\" |")
    p("| Presets | Fast or Balanced only | Thorough only |")
    p("| Output | Numbers/arrays (spill) | Handle string (TSL.THR.*) |")
    p("| Recalculation | Normal Excel recalc | Only when trigger changes |")
    p("| Trigger | Not needed | REQUIRED: `TSL_TRIGGER()` |")
    blank()
    h3("Worked Example: AUTO Forecast")
    p("```")
    p("=TSL_FORECAST(A2:A100, B2:B100, 12, \"Balanced\", \"Auto\")")
    p("```")
    p("This spills 12 rows of forecasts directly. It recomputes whenever inputs change.")
    blank()
    h3("Worked Example: THOROUGH Forecast")
    p("```")
    p("Cell D1: =TSL_FORECAST_THR(A2:A100, B2:B100, 12, TSL_TRIGGER(), \"Auto\")")
    p("Cell E1: =TSL_STATUS(D1)")
    p("Cell F1: =TSL_WARNINGS(D1)")
    p("```")
    p("D1 returns a handle like `TSL.THR.auto_arima.20260216143022.a1b2c3d4`.")
    p("Use `=TSL_TABLE(D1, \"forecasts\")` to extract the forecast table.")
    p("Click **Re-run Thorough** in the ribbon to recompute.")
    blank()

    # Common Workflows
    h2("8. Common Workflows")
    h3("Seasonal Adjustment")
    p("1. Select date + value columns")
    p("2. Click **Seasonal Adjustment** in Quick Actions")
    p("3. Choose method (STL recommended), confirm frequency")
    p("4. Click Run. Review trend, seasonal, and remainder components.")
    blank()
    h3("Granger Causality")
    p("1. Select two series (potential cause and effect)")
    p("2. Click **Granger Causality**")
    p("3. Set max lags (default 12)")
    p("4. Review F-statistics and p-values by lag")
    blank()
    h3("Lead-Lag Finder")
    p("1. Select two series")
    p("2. Click **Lead-Lag Finder**")
    p("3. Choose method (Prewhitened CCF recommended)")
    p("4. Review best lag and correlation strength")
    blank()
    h3("Forecasting")
    p("1. Select date + value column")
    p("2. Click **Forecast**")
    p("3. Set horizon, choose model (Auto recommended)")
    p("4. Review forecasts with prediction intervals")
    blank()

    # Audit
    h2("9. Audit Log and Reproducibility")
    p("Every run creates:")
    p("- **Results sheet:** Plain-English summary, diagnostics, output tables, charting suggestions")
    p("- **Audit sheet:** Full record of inputs, parameters, transforms, diagnostics, versions, seed")
    p("- **Embedded JSON:** Machine-readable record in hidden sheet `_TSL_RUNS`")
    blank()
    p("The JSON record contains everything needed to reproduce a run: input ranges, resolved "
      "parameters, seed, and version information. Use **Re-run this analysis** from the Task Pane.")
    blank()

    # Technique Catalog
    h2("10. Technique Catalog")
    techniques = catalog.get("techniques", [])
    categories = {}
    for t in techniques:
        cat = t.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)

    for cat in sorted(categories.keys()):
        h3(cat)
        for t in categories[cat]:
            tid = t.get("id", "?")
            name = t.get("name", tid)
            summary = t.get("summary", "")
            lines.append(f"#### {name}\n")
            blank()
            p(f"`{tid}`: {summary}")
            blank()

            # Load markdown description — downgrade headings so they nest
            # under the technique H4 (# -> #####, ## -> #####)
            desc = load_technique_md(tid)
            if desc and desc != "(No detailed description available.)":
                for dl in desc.split("\n"):
                    if dl.startswith("## "):
                        lines.append(f"##### {dl[3:]}\n")
                    elif dl.startswith("# "):
                        lines.append(f"##### {dl[2:]}\n")
                    else:
                        lines.append(f"{dl}\n")
                blank()

            # Parameters
            params = t.get("parameters", [])
            if params:
                lines.append("##### Parameters\n")
                for param in params:
                    pname = param.get("name", "?")
                    plabel = param.get("label", pname)
                    pdef = param.get("default", "")
                    pdesc = param.get("description", "")
                    adv = " *(advanced)*" if param.get("advanced", False) else ""
                    p(f"- `{pname}` ({plabel}): {pdesc} Default: {pdef}{adv}")
                blank()

    # UDF Reference
    h2("11. UDF Reference")
    udfs = udf_catalog.get("udfs", [])
    if udfs:
        for udf in udfs:
            name = udf.get("name", "?")
            desc = udf.get("description", "")
            lane = udf.get("lane", "?")
            h3(f"`{name}` [{lane}]")
            p(desc)
            blank()
            args = udf.get("arguments", [])
            if args:
                p("Arguments:")
                for arg in args:
                    aname = arg.get("name", "?")
                    adesc = arg.get("description", "")
                    p(f"- `{aname}`: {adesc}")
                blank()
    else:
        p("*(UDF catalog not yet generated. Run `generate_udf_catalog.ps1` first.)*")
    blank()

    # Troubleshooting
    h2("12. Troubleshooting")
    p("Time Series Lab follows a **fail loudly** policy. Errors include plain-English "
      "explanations and suggested fixes.")
    blank()
    p("**Common issues:**")
    p("- **\"No range selected\"**: Select data columns before clicking Run.")
    p("- **\"Could not detect time index\"**: Ensure dates are in a column adjacent to your data.")
    p("- **\"Engine not found\"**: Reinstall the add-in or check the Python runtime at "
      "`%LOCALAPPDATA%\\TimeSeriesLab\\engine\\runtime\\`.")
    p("- **\"Thorough preset not allowed in AUTO\"**: Use `TSL_RUN_THR()` or the Task Pane for Thorough.")
    p("- **\"MISSING (Click Re-run Thorough)\"**: The handle result is not in cache. "
      "Click Re-run Thorough in the ribbon.")
    p("- **Missing data warning**: If >15% missing or gap >10 periods, confirm before proceeding.")
    blank()

    return "\n".join(lines)


def generate_docx(markdown_text):
    """Generate Word document from markdown text using python-docx."""
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("WARNING: python-docx not installed. Skipping .docx generation.")
        print("  Install with: pip install python-docx")
        return False

    doc = Document()

    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Process markdown line by line
    lines = markdown_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("# ") and not line.startswith("## "):
            # Title
            heading = doc.add_heading(line[2:].strip(), level=0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=2)
        elif line.startswith("```"):
            # Code block
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            p = doc.add_paragraph()
            run = p.add_run(code_text)
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            p.style = doc.styles['Normal']
        elif line.startswith("| ") and "---" not in line:
            # Table row - collect all table rows
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                if "---" not in lines[i]:
                    table_lines.append(lines[i])
                i += 1
            i -= 1  # Will be incremented at end of loop

            if len(table_lines) > 1:
                # Parse table
                headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                rows = []
                for tl in table_lines[1:]:
                    cells = [c.strip() for c in tl.split("|")[1:-1]]
                    rows.append(cells)

                ncols = len(headers)
                table = doc.add_table(rows=1 + len(rows), cols=ncols)
                table.style = 'Table Grid'

                # Headers
                for j, h in enumerate(headers):
                    cell = table.rows[0].cells[j]
                    cell.text = h.replace("**", "")
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True

                # Data rows
                for r_idx, row_data in enumerate(rows):
                    for c_idx, cell_text in enumerate(row_data):
                        if c_idx < ncols:
                            table.rows[r_idx + 1].cells[c_idx].text = cell_text.replace("**", "").replace("`", "")

        elif line.startswith("- "):
            # Bullet list
            text = line[2:].strip()
            # Remove markdown bold/code formatting
            text = text.replace("**", "").replace("`", "")
            doc.add_paragraph(text, style='List Bullet')
        elif line.strip() and not line.startswith("|"):
            # Regular paragraph
            text = line.replace("**", "").replace("`", "")
            doc.add_paragraph(text)

        i += 1

    # Save
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX))
    return True


def generate_html(markdown_text):
    """Generate a self-contained HTML file with sidebar nav and OkabeIto styling."""
    import re

    # --- First pass: collect headings for sidebar nav ---
    # Sidebar shows only H2 (main sections) and H3 (technique categories).
    # Individual techniques and sub-headings stay in content only.
    sections = []  # list of (level, slug, title)
    lines = markdown_text.split("\n")
    in_catalog = False
    for line in lines:
        if line.startswith("## "):
            title = line[3:].strip()
            in_catalog = 'technique catalog' in title.lower()
            sections.append((2, _slugify(title), title))
        elif line.startswith("### ") and in_catalog:
            title = line[4:].strip()
            sections.append((3, _slugify(title), title))

    sidebar_html = []
    sidebar_html.append('<nav>')
    sidebar_html.append('  <div class="logo">')
    sidebar_html.append('    <h1>Time Series Lab</h1>')
    sidebar_html.append('    <span>User Guide v1.0</span>')
    sidebar_html.append('  </div>')
    for level, slug, title in sections:
        if level == 2:
            short = re.sub(r'^\d+\.\s*', '', title)
            sidebar_html.append(f'  <a href="#{slug}" class="section-head">{_esc(short)}</a>')
        elif level == 3:
            sidebar_html.append(f'  <a href="#{slug}">&nbsp;&nbsp;{_esc(title)}</a>')
    sidebar_html.append('</nav>')

    # --- Second pass: render content ---
    content = []
    i = 0
    in_list = False
    while i < len(lines):
        line = lines[i]

        # Close list if leaving bullet items
        if in_list and not line.startswith("- "):
            content.append("</ul>")
            in_list = False

        if line.startswith("##### "):
            title = line[6:].strip()
            content.append(f'<h5>{_md_inline(title)}</h5>')
        elif line.startswith("#### "):
            title = line[5:].strip()
            slug = _slugify(title)
            content.append(f'<h4 id="{slug}">{_md_inline(title)}</h4>')
        elif line.startswith("### "):
            title = line[4:].strip()
            slug = _slugify(title)
            content.append(f'<h3 id="{slug}">{_md_inline(title)}</h3>')
        elif line.startswith("## "):
            title = line[3:].strip()
            slug = _slugify(title)
            content.append(f'<h2 id="{slug}">{_md_inline(title)}</h2>')
        elif line.startswith("# ") and not line.startswith("## "):
            # Skip the H1 title — it's in the sidebar logo
            pass
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_html = "\n".join(_esc(cl) for cl in code_lines)
            content.append(f"<pre>{code_html}</pre>")
        elif line.startswith("| ") and "---" not in line:
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                if "---" not in lines[i]:
                    table_lines.append(lines[i])
                i += 1
            i -= 1
            if len(table_lines) > 1:
                headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                content.append("<table><tr>")
                for h in headers:
                    content.append(f"<th>{_md_inline(h)}</th>")
                content.append("</tr>")
                for tl in table_lines[1:]:
                    cells = [c.strip() for c in tl.split("|")[1:-1]]
                    content.append("<tr>")
                    for c in cells:
                        content.append(f"<td>{_md_inline(c)}</td>")
                    content.append("</tr>")
                content.append("</table>")
        elif line.startswith("- "):
            if not in_list:
                content.append("<ul>")
                in_list = True
            content.append(f"<li>{_md_inline(line[2:].strip())}</li>")
        elif line.strip():
            text = line.strip()
            # Detect tip/warning patterns
            if text.startswith("**Tip:**") or text.startswith("**Tip**:"):
                content.append(f'<div class="tip">{_md_inline(text)}</div>')
            elif text.startswith("**Warning:**") or text.startswith("**Warning**:"):
                content.append(f'<div class="warn">{_md_inline(text)}</div>')
            else:
                content.append(f"<p>{_md_inline(text)}</p>")

        i += 1

    if in_list:
        content.append("</ul>")

    # --- Assemble full HTML ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Time Series Lab - User Guide</title>
<style>
  :root {{
    --oi-blue: #0072B2;
    --oi-orange: #E69F00;
    --oi-green: #009E73;
    --oi-vermillion: #D55E00;
    --oi-skyblue: #56B4E9;
    --oi-purple: #CC79A7;
    --oi-yellow: #F0E442;
    --oi-black: #000000;
    --bg: #FAFAFA;
    --sidebar-bg: #1E293B;
    --sidebar-text: #CBD5E1;
    --sidebar-hover: #334155;
    --sidebar-active: #0072B2;
    --card-bg: #FFFFFF;
    --border: #E2E8F0;
    --text: #1E293B;
    --text-secondary: #64748B;
    --code-bg: #F1F5F9;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Verdana, Geneva, sans-serif;
    font-size: 9pt;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    display: flex;
    min-height: 100vh;
  }}
  nav {{
    width: 260px;
    min-width: 260px;
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    padding: 24px 0;
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    overflow-y: auto;
    z-index: 10;
  }}
  nav .logo {{
    padding: 0 20px 20px;
    border-bottom: 1px solid #334155;
    margin-bottom: 12px;
  }}
  nav .logo h1 {{
    font-size: 16px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.3px;
  }}
  nav .logo span {{
    font-size: 12px;
    color: var(--oi-skyblue);
    font-weight: 400;
  }}
  nav a {{
    display: block;
    padding: 7px 20px;
    color: var(--sidebar-text);
    text-decoration: none;
    font-size: 13px;
    transition: background 0.15s, color 0.15s;
  }}
  nav a:hover {{ background: var(--sidebar-hover); color: #F8FAFC; }}
  nav a.section-head {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--oi-skyblue);
    padding-top: 18px;
    padding-bottom: 4px;
    margin-top: 4px;
    border-top: 1px solid #334155;
  }}
  nav a.section-head:hover {{
    color: #FFFFFF;
  }}
  nav a.section-head:first-of-type {{
    border-top: none;
    margin-top: 0;
  }}
  main {{
    margin-left: 260px;
    flex: 1;
    padding: 40px 48px 80px;
    max-width: 900px;
  }}
  h2 {{
    font-size: 24px;
    font-weight: 700;
    margin: 48px 0 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--oi-blue);
    color: var(--text);
  }}
  h2:first-of-type {{ margin-top: 0; }}
  h3 {{
    font-size: 17px;
    font-weight: 600;
    margin: 28px 0 10px;
    color: var(--text);
  }}
  h4 {{
    font-size: 15px;
    font-weight: 700;
    margin: 32px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
    color: var(--oi-blue);
  }}
  h5 {{
    font-size: 13px;
    font-weight: 600;
    margin: 18px 0 6px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  p {{ margin-bottom: 12px; }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    margin: 16px 0;
  }}
  .card h4 {{
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 20px;
    font-size: 14px;
  }}
  th {{
    text-align: left;
    padding: 10px 12px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    font-weight: 600;
    font-size: 13px;
  }}
  td {{
    padding: 8px 12px;
    border: 1px solid var(--border);
    vertical-align: top;
  }}
  code {{
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
  }}
  pre {{
    background: var(--code-bg);
    padding: 14px 18px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
    margin: 12px 0 20px;
    line-height: 1.5;
  }}
  .tip {{
    background: #EFF6FF;
    border-left: 4px solid var(--oi-blue);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
  }}
  .tip strong {{ color: var(--oi-blue); }}
  .warn {{
    background: #FFFBEB;
    border-left: 4px solid var(--oi-orange);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
  }}
  .warn strong {{ color: var(--oi-vermillion); }}
  ul {{ margin: 8px 0 12px 20px; font-size: 14px; }}
  li {{ margin: 4px 0; }}
  footer {{
    margin-top: 60px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 13px;
    text-align: center;
  }}
  @media (max-width: 768px) {{
    nav {{ display: none; }}
    main {{ margin-left: 0; padding: 24px 20px; }}
  }}
</style>
</head>
<body>
{chr(10).join(sidebar_html)}
<main>
{chr(10).join(content)}
<footer>
  Time Series Lab v1.0 &bull; Created by Matthew T. Hornbach &bull; Generated automatically from technique and UDF registries
</footer>
</main>
</body>
</html>"""

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    return True


def _slugify(text):
    """Convert heading text to a URL-safe slug."""
    import re
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '-', text.strip())
    return text


def _esc(text):
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline(text):
    """Convert inline markdown (bold, code) to HTML."""
    import re
    text = _esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def main():
    print("=== Generating Time Series Lab User Guide ===")

    catalog = load_catalog()
    udf_catalog = load_udf_catalog()

    print(f"Loaded {len(catalog.get('techniques', []))} techniques")
    print(f"Loaded {len(udf_catalog.get('udfs', []))} UDFs")

    # Generate markdown
    md = generate_markdown(catalog, udf_catalog)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"Generated markdown: {OUTPUT_MD}")

    # Generate docx
    if generate_docx(md):
        print(f"Generated Word doc: {OUTPUT_DOCX}")
    else:
        print("Word doc generation skipped (install python-docx).")

    # Generate HTML
    if generate_html(md):
        print(f"Generated HTML: {OUTPUT_HTML}")

    print("=== Done ===")


if __name__ == "__main__":
    main()
