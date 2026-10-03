#!/usr/bin/env python3
"""check_house_dialogs.py - no native dialog outside the house dialog helper (A2 U4).

docs/HOUSE_STYLE.md: every add-in message, question and free-text prompt goes through
the house dialog (src/TSL.UI/HouseDialog.cs + HouseDialogForm.cs). This gate fails on any
other dialog call in the add-in's C# sources:

  - MessageBox, in any namespace and in any form (System.Windows.Forms or WPF
    System.Windows.MessageBox, an in-file alias or `using static`, or a global
    <Using> item in a project file);
  - a native dialog P/Invoke (user32 MessageBox*, TaskDialog*, shlwapi
    SHMessageBoxCheck*, comdlg32 GetOpenFileName / GetSaveFileName / ChooseColor /
    ChooseFont / PrintDlg, shell32 SHBrowseForFolder), also under another name via
    EntryPoint, and TaskDialog itself;
  - an input box: Interaction.InputBox / MsgBox, Excel's Application.InputBox, and the
    Excel C API's xlcAlert / xlfInput / xlfDialogBox / xlfOpenDialog;
  - Excel's built-in dialogs (.Dialogs, XlBuiltInDialog), Office's FileDialog and the
    file pickers (GetOpenFilename, GetSaveAsFilename);
  - the WinForms / WPF common dialogs (OpenFileDialog, SaveFileDialog,
    FolderBrowserDialog, ColorDialog, FontDialog, PrintDialog, ...);
  - a hand-built modal form (.ShowDialog(...));
  - Excel's Function Arguments dialog (Range.FunctionWizard). It is the one native dialog
    Time Series Lab opens on purpose (docs/HOUSE_STYLE.md, Look; A2 E2b ruling 1(b)): a
    single call site may carry the marker comment
        // HOUSE-DIALOG-EXCEPTION: Function Arguments
    on its own line or on the line above it. That call passes; an unmarked FunctionWizard
    fails, and so does every marked call after the first (in file and line order).

Scope: every .cs file under src/TSL.AddIn and src/TSL.UI except bin/ and obj/, and the
<Using> items of the project files there. Only the two helper files are exempt.
TSL.Installer is out of scope: it runs outside Excel and uses native boxes with real
icons on purpose (house style, Installer messages). Comments and string literals are
blanked before matching (line numbers kept), so a comment or a message that MENTIONS a
dialog never fires; code inside the holes of interpolated strings (regular, verbatim
and raw) is still checked. A .cs file is read as UTF-8, or as UTF-16 when it carries a
UTF-16 byte-order mark; a file that cannot be read fails the gate.

Guards against an empty pass: it fails if either scan root is missing or holds no .cs
file, or if a helper file is missing, and it always prints how many files it scanned.

    python tools/check_house_dialogs.py              # the check; exit 0 GREEN, 1 RED
    python tools/check_house_dialogs.py --self-test  # plants each case in a temp tree

Standard library only. A gate step in tools/ci_gate_local.ps1 and parity-fast.yml.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCAN_ROOTS = ("src/TSL.AddIn", "src/TSL.UI")
HELPER_FILES = ("src/TSL.UI/HouseDialog.cs", "src/TSL.UI/HouseDialogForm.cs")
EXCLUDED_DIRS = {"bin", "obj"}
PROJECT_SUFFIXES = (".csproj", ".props", ".targets")

_NATIVE = (r"(?:MessageBox|TaskDialog|ChooseColor|ChooseFont|PrintDlg|SHBrowseForFolder"
           r"|GetOpenFileName|GetSaveFileName)\w*")

# Rules on the code with comments AND string literals blanked.
CODE_RULES = [
    ("MessageBox", re.compile(r"\bMessageBox\b")),
    ("native dialog P/Invoke", re.compile(r"\bextern\b[^;{}]*?" + _NATIVE + r"\s*\(")),
    ("TaskDialog", re.compile(r"\bTaskDialog\w*")),
    ("input box", re.compile(r"\bInputBox\b|\bMsgBox\b")),
    ("Excel C API dialog", re.compile(
        r"\bxl[cf](?:Alert|Input|DialogBox|OpenDialog|GetOpenFilename|GetSaveAsFilename)\b")),
    ("Excel built-in dialog", re.compile(r"\.\s*Dialogs\b|\bget_Dialogs\b|\bXlBuiltInDialog\b")),
    ("file picker", re.compile(r"\bget(?:open|save(?:as)?)filename[aw]?\b", re.IGNORECASE)),
    ("Office file dialog", re.compile(r"\bFileDialog\b|\bget_FileDialog\b|\bMsoFileDialogType\b")),
    ("common dialog", re.compile(
        r"\b(?:OpenFileDialog|SaveFileDialog|OpenFolderDialog|FolderBrowserDialog|ColorDialog|FontDialog"
        r"|PrintDialog|PageSetupDialog|PrintPreviewDialog)\b")),
    ("modal form", re.compile(r"\.\s*ShowDialog\s*\(")),
    ("Excel Function Arguments dialog", re.compile(r"\bFunctionWizard\b")),
]
# The one native dialog opened on purpose: a FunctionWizard call marked like this (in a
# comment on the call's line or the line above) passes - the first such call only.
FUNCTION_WIZARD_RULE = "Excel Function Arguments dialog"
FUNCTION_WIZARD_MARK = "HOUSE-DIALOG-EXCEPTION: Function Arguments"
# Rules on the code with only comments blanked (string literals kept).
STRING_RULES = [
    ("native dialog P/Invoke", re.compile(r"\bEntryPoint\s*=\s*@?\"[^\"]*" + _NATIVE + "\"")),
]
# A project file's global <Using Include="..."> naming a dialog type (an alias or a static import).
_USING_ITEM = re.compile(r"<Using\b[^>]*?\bInclude\s*=\s*\"([^\"]+)\"", re.IGNORECASE)
_DIALOG_NAME = re.compile(
    r"MessageBox|TaskDialog|Interaction|InputBox|MsgBox|FileDialog|FolderBrowserDialog|ColorDialog|FontDialog"
    r"|PrintDialog|PageSetupDialog|PrintPreviewDialog|OpenFolderDialog", re.IGNORECASE)

# A string starts with: a verbatim prefix (@, $@, @$) and one quote; or optional $s and
# three or more quotes (a raw string; $s make it interpolated); or optional $ and one quote.
_STRING_START = re.compile(r'(?P<verb>\$*@\$*)"|(?P<dollars>\$*)(?P<quotes>"{3,}|")')


# ── C# lexing: blank comments and string literals, keep every newline ─────────

class _Views:
    """Two parallel views of a file: `code` (comments + strings blanked) and `keep` (comments blanked)."""

    def __init__(self) -> None:
        self.code: list[str] = []
        self.keep: list[str] = []

    @staticmethod
    def _blank(ch: str) -> str:
        return "\n" if ch == "\n" else " "

    def code_char(self, ch: str) -> None:
        self.code.append(ch)
        self.keep.append(ch)

    def string_char(self, ch: str) -> None:
        self.code.append(self._blank(ch))
        self.keep.append(ch)

    def comment_char(self, ch: str) -> None:
        b = self._blank(ch)
        self.code.append(b)
        self.keep.append(b)


def _scan_code(t: str, i: int, out: _Views, in_hole: bool) -> int:
    """Scan C# code from i. In an interpolation hole, stop at the unmatched '}' (returns its index)."""
    n = len(t)
    depth = 0
    while i < n:
        c = t[i]
        nxt = t[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and t[i] != "\n":
                out.comment_char(t[i])
                i += 1
            continue
        if c == "/" and nxt == "*":
            out.comment_char(c)
            out.comment_char(nxt)
            i += 2
            while i < n and not (t[i] == "*" and i + 1 < n and t[i + 1] == "/"):
                out.comment_char(t[i])
                i += 1
            if i < n:
                out.comment_char("*")
                out.comment_char("/")
                i += 2
            continue
        if c in '$@"':
            m = _STRING_START.match(t, i)
            if m:
                for ch in t[i:m.end()]:
                    out.string_char(ch)
                if m.group("verb") is not None:
                    i = _scan_string(t, m.end(), out, interpolated="$" in m.group("verb"), verbatim=True,
                                     raw_quotes=None, dollars=0)
                else:
                    dollars = len(m.group("dollars"))
                    quotes = m.group("quotes")
                    raw = len(quotes) >= 3
                    i = _scan_string(t, m.end(), out, interpolated=dollars > 0, verbatim=False,
                                     raw_quotes=quotes if raw else None, dollars=dollars)
                continue
        if c == "'":
            # A char literal ('"', '\'', '\\', 'a', '"'): never the start of a string.
            j = i + 1
            if j < n and t[j] == "\\":
                j += 2
            else:
                j += 1
            while j < n and t[j] != "'" and t[j] != "\n":
                j += 1
            end = min(j + 1, n)
            for ch in t[i:end]:
                out.string_char(ch)
            i = end
            continue
        if in_hole:
            if c == "{":
                depth += 1
            elif c == "}":
                if depth == 0:
                    return i
                depth -= 1
        out.code_char(c)
        i += 1
    return i


def _scan_hole(t: str, i: int, out: _Views, closers: int) -> int:
    """Scan an interpolation hole's code from i; consume up to `closers` closing braces."""
    n = len(t)
    i = _scan_code(t, i, out, in_hole=True)
    while closers > 0 and i < n and t[i] == "}":
        out.string_char("}")
        i += 1
        closers -= 1
    return i


def _scan_string(t: str, i: int, out: _Views, interpolated: bool, verbatim: bool, raw_quotes: str | None,
                 dollars: int) -> int:
    """Scan a string body from i (after the opening quote[s]); return the index after its end."""
    n = len(t)
    while i < n:
        c = t[i]
        if raw_quotes is not None:
            if t.startswith(raw_quotes, i):
                for ch in raw_quotes:
                    out.string_char(ch)
                return i + len(raw_quotes)
            if interpolated and c == "{":
                run = len(t[i:]) - len(t[i:].lstrip("{"))
                for ch in t[i:i + run]:
                    out.string_char(ch)
                i += run
                if run >= dollars:  # the last `dollars` braces open a hole
                    i = _scan_hole(t, i, out, closers=dollars)
                continue
            out.string_char(c)
            i += 1
            continue
        if not verbatim and c == "\\":
            out.string_char(c)
            if i + 1 < n:
                out.string_char(t[i + 1])
            i += 2
            continue
        if c == '"':
            if verbatim and i + 1 < n and t[i + 1] == '"':
                out.string_char(c)
                out.string_char('"')
                i += 2
                continue
            out.string_char(c)
            return i + 1
        if interpolated and c in "{}":
            if i + 1 < n and t[i + 1] == c:  # {{ or }}: a literal brace
                out.string_char(c)
                out.string_char(c)
                i += 2
                continue
            if c == "{":  # a hole: its contents are code
                out.string_char(c)
                i = _scan_hole(t, i + 1, out, closers=1)
                continue
        if not verbatim and c == "\n":  # an unterminated regular string ends at the line end
            out.string_char(c)
            return i + 1
        out.string_char(c)
        i += 1
    return i


def strip_cs(text: str) -> tuple[str, str]:
    """(code with comments and strings blanked, code with comments blanked); same length, same lines."""
    out = _Views()
    _scan_code(text, 0, out, in_hole=False)
    return "".join(out.code), "".join(out.keep)


# ── The check ───────────────────────────────────────────────────────────────

def _files(root: Path, suffixes: tuple[str, ...]) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        found[scan_root] = []
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in suffixes:
                continue
            if EXCLUDED_DIRS.intersection(part.lower() for part in p.relative_to(base).parts[:-1]):
                continue
            found[scan_root].append(p)
    return found


def _read_source(path: Path) -> str:
    """UTF-8 (BOM optional), or UTF-16 when the file starts with a UTF-16 byte-order mark."""
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    text = data.decode("utf-8-sig")
    if "\x00" in text:
        raise UnicodeError("NUL characters: an unrecognised encoding")
    return text


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan(root: Path) -> tuple[list[tuple[str, int, str, str]], int, list[str], dict[str, int]]:
    """Return (hits as (relpath, line, rule, source line), .cs files scanned, scan problems, per-root counts)."""
    problems: list[str] = []
    for helper in HELPER_FILES:
        if not (root / helper).is_file():
            problems.append(f"the house dialog helper {helper} is missing")
    helpers = {(root / h).resolve() for h in HELPER_FILES}

    sources = _files(root, (".cs",))
    counts = {r: len(files) for r, files in sources.items()}
    for scan_root, count in counts.items():
        if count == 0:
            problems.append(f"{scan_root} is missing or holds no .cs file")

    hits: list[tuple[str, int, str, str]] = []
    for path in (p for files in sources.values() for p in files):
        if path.resolve() in helpers:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            text = _read_source(path)
        except (UnicodeError, OSError) as ex:
            problems.append(f"{rel} could not be read as UTF-8 or UTF-16 ({ex})")
            continue
        code, keep = strip_cs(text)
        source_lines = text.splitlines()
        seen: set[tuple[int, str]] = set()
        for view, rules in ((code, CODE_RULES), (keep, STRING_RULES)):
            for rule, rx in rules:
                for m in rx.finditer(view):
                    line = _line_of(view, m.start())
                    if (line, rule) in seen:
                        continue
                    seen.add((line, rule))
                    src = source_lines[line - 1].strip() if line - 1 < len(source_lines) else ""
                    hits.append((rel, line, rule, src))

    for path in (p for files in _files(root, PROJECT_SUFFIXES).values() for p in files):
        rel = path.relative_to(root).as_posix()
        try:
            text = _read_source(path)
        except (UnicodeError, OSError) as ex:
            problems.append(f"{rel} could not be read as UTF-8 or UTF-16 ({ex})")
            continue
        for m in _USING_ITEM.finditer(text):
            if _DIALOG_NAME.search(m.group(1)):
                line = _line_of(text, m.start())
                hits.append((rel, line, "global using of a dialog", text.splitlines()[line - 1].strip()))

    hits.sort(key=lambda h: (h[0], h[1], h[2]))
    hits = _allow_marked_function_wizard(root, hits)
    return hits, sum(counts.values()), problems, counts


def _allow_marked_function_wizard(root: Path, hits: list[tuple[str, int, str, str]]) -> list[tuple[str, int, str, str]]:
    """Drop the first FunctionWizard hit whose line, or the line above it, carries the marker
    (the raw source is read, since the marker sits in a comment). Every later marked call
    stays a hit, renamed so the RED says why."""
    allowed_one = False
    kept: list[tuple[str, int, str, str]] = []
    for rel, line, rule, src in hits:
        if rule == FUNCTION_WIZARD_RULE:
            try:
                lines = _read_source(root / rel).splitlines()
            except (UnicodeError, OSError):
                lines = []
            near = lines[max(0, line - 2):line]
            if any(FUNCTION_WIZARD_MARK in text for text in near):
                if not allowed_one:
                    allowed_one = True
                    continue
                rule = FUNCTION_WIZARD_RULE + " (a second marked call; only one is allowed)"
        kept.append((rel, line, rule, src))
    return kept


def run_check(root: Path) -> int:
    hits, count, problems, counts = scan(root)
    per_root = ", ".join(f"{r}: {c}" for r, c in counts.items())
    scope = f"{count} .cs file(s) ({per_root}); helper: {', '.join(HELPER_FILES)}"
    for problem in problems:
        print(f"check_house_dialogs: FAIL - {problem}")
    if hits:
        print(f"check_house_dialogs: FAIL - {len(hits)} native dialog call(s) outside the house dialog helper "
              f"(docs/HOUSE_STYLE.md); use TSL.UI.HouseDialog instead:")
        for rel, line, rule, src in hits:
            print(f"  {rel}:{line}: {rule}: {src}")
    if problems or hits:
        print(f"Scanned {scope}.")
        return 1
    print(f"check_house_dialogs: OK - no native dialog call outside the house dialog helper ({scope}).")
    return 0


# ── Self-test ───────────────────────────────────────────────────────────────

_HELPER_BODY = 'namespace TSL.UI { static class H { static void F() { System.Windows.Forms.MessageBox.Show("x"); } } }\n'

# (name, file content planted in src/TSL.AddIn, expected rules hit - one entry per expected hit)
_CASES = [
    ("MessageBox.Show in an ordinary file", 'class A { void F() { MessageBox.Show("x"); } }\n', ["MessageBox"]),
    ("the same text in a comment and in strings",
     '// MessageBox.Show("x")\n/* MessageBox.Show("x")\n   Interaction.InputBox("q") */\n'
     'class A { string s = "MessageBox.Show(\\"x\\")"; string v = @"MessageBox.Show(""x"")";\n'
     '  string i = $"MessageBox.Show {1} {{x}}"; char q = \'"\';\n'
     '  string r = """MessageBox.Show("x") and .ShowDialog()"""; string e = $"""{1} MessageBox.Show("x")"""; }\n', []),
    ("Interaction.InputBox", 'class A { void F() { var s = Microsoft.VisualBasic.Interaction.InputBox("q"); } }\n',
     ["input box"]),
    ("a call inside an interpolation hole", 'class A { string s = $"a {MessageBox.Show("x")} b"; }\n', ["MessageBox"]),
    ("a call inside a raw interpolated string's hole",
     'class A { string s = $"""a {MessageBox.Show("x")} b"""; string t = $$"""{{MessageBox.Show("y")}} {x}"""; }\n',
     ["MessageBox"]),
    ("a verbatim string that starts with an escaped quote is not a raw string",
     'class A { string q = @""""; void F() { MessageBox.Show("x"); } }\n', ["MessageBox"]),
    ("an interpolated verbatim string that starts with an escaped quote",
     'class A { string p = "p"; string q = $@"""{p}"" --x";\n  void F() { MessageBox.Show("x"); } }\n',
     ["MessageBox"]),
    ("a char literal quote does not open a string", "class A { void F() { var q = '\"'; MessageBox.Show(\"x\"); } }\n",
     ["MessageBox"]),
    ("WPF MessageBox", 'class A { void F() { System.Windows.MessageBox.Show("x"); } }\n', ["MessageBox"]),
    ("an alias", 'using MB = System.Windows.Forms.MessageBox;\nclass A { void F() { MB.Show("x"); } }\n',
     ["MessageBox"]),
    ("a user32 entry point under another name",
     'class A { [DllImport("user32.dll", EntryPoint = "MessageBoxW")]\n'
     '  static extern int Box(IntPtr h, string t, string c, uint f); }\n', ["native dialog P/Invoke"]),
    ("an entry point given as a verbatim string",
     'class A { [DllImport("user32.dll", EntryPoint = @"MessageBoxW")] static extern int Box(IntPtr h, string t, string c, uint f); }\n',
     ["native dialog P/Invoke"]),
    ("a user32 MessageBoxW declaration",
     'class A { [DllImport("user32.dll")] static extern int MessageBoxW(IntPtr h, string t, string c, uint f); }\n',
     ["native dialog P/Invoke"]),
    ("comdlg32 and shlwapi declarations",
     'class A { [DllImport("comdlg32.dll")] static extern bool GetOpenFileName(ref OFN o);\n'
     '  [DllImport("shlwapi.dll")] static extern int SHMessageBoxCheckW(IntPtr h, string t, string c, uint f, int d, string r); }\n',
     ["file picker", "native dialog P/Invoke", "native dialog P/Invoke"]),
    ("Excel dialogs and pickers",
     'class A { void F(dynamic app) {\n  app.Dialogs[1].Show();\n  var f = app.GetOpenFilename();\n'
     '  var g = app.InputBox("q");\n  var d = new OpenFileDialog();\n  TaskDialog.ShowDialog(null);\n} }\n',
     ["Excel built-in dialog", "file picker", "input box", "common dialog", "TaskDialog", "modal form"]),
    ("Office FileDialog, built-in dialogs through a variable, the Excel C API",
     'class A { void F(dynamic app) {\n  var fd = app.FileDialog[3];\n  var ds = app.Dialogs; var d = ds.get_Item(1);\n'
     '  XlCall.Excel(XlCall.xlcAlert, "x");\n} }\n',
     ["Office file dialog", "Excel built-in dialog", "Excel C API dialog"]),
    ("a hand-built modal form", 'class A { void F() { new System.Windows.Forms.Form().ShowDialog(); } }\n',
     ["modal form"]),
    # Excel's Function Arguments dialog: one marked call site only (A2 E2b ruling 1(b)).
    ("an unmarked FunctionWizard",
     'class A { void F(Microsoft.Office.Interop.Excel.Range c) { c.FunctionWizard(); } }\n',
     ["Excel Function Arguments dialog"]),
    ("the marked FunctionWizard call passes",
     'class A { void F(dynamic c) {\n  // HOUSE-DIALOG-EXCEPTION: Function Arguments (docs/HOUSE_STYLE.md)\n'
     '  c.FunctionWizard();\n} }\n', []),
    ("the marker on the call's own line",
     'class A { void F(dynamic c) { c.FunctionWizard(); // HOUSE-DIALOG-EXCEPTION: Function Arguments\n} }\n', []),
    ("a second marked FunctionWizard call fails",
     'class A { void F(dynamic c) {\n  // HOUSE-DIALOG-EXCEPTION: Function Arguments\n  c.FunctionWizard();\n'
     '  // HOUSE-DIALOG-EXCEPTION: Function Arguments\n  c.FunctionWizard();\n} }\n',
     ["Excel Function Arguments dialog (a second marked call; only one is allowed)"]),
    ("the marker excuses only the FunctionWizard call",
     'class A { void F(dynamic c) {\n  // HOUSE-DIALOG-EXCEPTION: Function Arguments\n'
     '  c.FunctionWizard(); MessageBox.Show("x");\n} }\n', ["MessageBox"]),
    ("a marker two lines above does not count",
     'class A { void F(dynamic c) {\n  // HOUSE-DIALOG-EXCEPTION: Function Arguments\n\n  c.FunctionWizard();\n} }\n',
     ["Excel Function Arguments dialog"]),
    ("names that only start like a dialog",
     'class A { void F() { var b = MessageBoxButtons.OK; var f = SystemFonts.MessageBoxFont; var i = MessageBoxIcon.None;\n'
     '  ShowDialogNow(); var dialogs = 1; } }\n', []),
]


def _plant(root: Path, files: dict[str, str | bytes]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")


def run_self_test() -> int:
    failures: list[str] = []
    passed = 0

    def expect(name: str, ok: bool, detail: str) -> None:
        nonlocal passed
        if ok:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failures.append(f"{name}: {detail}")
            print(f"  FAIL  {name}: {detail}")

    helpers = {HELPER_FILES[0]: _HELPER_BODY, HELPER_FILES[1]: _HELPER_BODY}
    with tempfile.TemporaryDirectory(prefix="house_dialogs_") as tmp:
        base = Path(tmp)
        for n, (name, body, expected) in enumerate(_CASES):
            root = base / f"case{n}"
            _plant(root, {**helpers, "src/TSL.AddIn/Planted.cs": body,
                          # build output is never scanned
                          "src/TSL.AddIn/obj/Release/Generated.cs": 'class G { void F() { MessageBox.Show("x"); } }\n'})
            hits, count, problems, _ = scan(root)
            got = sorted(rule for _, _, rule, _ in hits)
            expect(name, not problems and count == 3 and got == sorted(expected),
                   f"expected {sorted(expected)}, got {got} (files {count}, problems {problems})")

        # The plan's helper case: the same calls inside the allowed helper are not hits.
        root = base / "helper"
        _plant(root, {HELPER_FILES[0]: _HELPER_BODY + 'class I { void F() { Interaction.InputBox("q"); } }\n',
                      HELPER_FILES[1]: _HELPER_BODY, "src/TSL.AddIn/Clean.cs": "class C { }\n"})
        hits, count, problems, _ = scan(root)
        expect("the same calls inside the allowed helper", not hits and not problems and count == 3,
               f"hits {hits}, problems {problems}, files {count}")

        # A UTF-16 file (PowerShell 5.1's default) is read, not skipped.
        root = base / "utf16"
        _plant(root, {**helpers, "src/TSL.AddIn/Wide.cs":
                      '\ufeffclass W { void F() { MessageBox.Show("x"); } }\n'.encode("utf-16-le")})
        hits, _, problems, _ = scan(root)
        expect("a UTF-16 file is read and its call found", [h[2] for h in hits] == ["MessageBox"] and not problems,
               f"hits {hits}, problems {problems}")

        # A global <Using> in a project file.
        root = base / "using"
        _plant(root, {**helpers, "src/TSL.AddIn/Clean.cs": "class C { }\n",
                      "src/TSL.AddIn/TSL.AddIn.csproj":
                          '<Project>\n  <ItemGroup>\n    <Using Include="System.Windows.Forms.MessageBox" Alias="MB" />\n'
                          '    <Using Include="System.Linq" />\n  </ItemGroup>\n</Project>\n'})
        hits, _, _, _ = scan(root)
        expect("a project file's global using of a dialog",
               [(h[0], h[1], h[2]) for h in hits] == [("src/TSL.AddIn/TSL.AddIn.csproj", 3, "global using of a dialog")],
               f"hits {hits}")

        # The line number is the call's line, so a RED names file:line.
        root = base / "line"
        _plant(root, {**helpers,
                      "src/TSL.AddIn/Ribbon.cs": 'class R {\n  void A() { }\n\n  void B() { MessageBox.Show("planted"); }\n}\n'})
        hits, _, _, _ = scan(root)
        expect("the hit names src/TSL.AddIn/Ribbon.cs:4",
               [(h[0], h[1]) for h in hits] == [("src/TSL.AddIn/Ribbon.cs", 4)], f"hits {hits}")

        # A RED whose source line holds a character the console cannot encode still prints
        # file:line (run as a child process with stdout piped, as the gate runs it).
        root = base / "encoding"
        _plant(root, {**helpers, "src/TSL.AddIn/Arrow.cs":
                      'class R { void B() { MessageBox.Show("P10\u2192P25"); } }\n'})
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--root", str(root)],
                               capture_output=True, env=env)
        output = child.stdout.decode("ascii", "replace") + child.stderr.decode("ascii", "replace")
        expect("a hit on a non-ASCII line prints file:line, not a traceback",
               child.returncode == 1 and "src/TSL.AddIn/Arrow.cs:1" in output and "Traceback" not in output,
               f"exit {child.returncode}: {output[-300:]!r}")

        # Guards against an empty pass.
        root = base / "empty"
        root.mkdir()
        _, count, problems, _ = scan(root)
        expect("an empty tree fails (no files, no helper)",
               count == 0 and any("holds no .cs file" in p for p in problems) and any("missing" in p for p in problems),
               f"files {count}, problems {problems}")
        root = base / "nohelper"
        _plant(root, {"src/TSL.AddIn/Clean.cs": "class C { }\n", "src/TSL.UI/Other.cs": "class O { }\n"})
        _, _, problems, _ = scan(root)
        expect("a tree without the helper fails", any("HouseDialog.cs is missing" in p for p in problems),
               f"problems {problems}")
        root = base / "oneroot"
        _plant(root, dict(helpers))
        _, _, problems, _ = scan(root)
        expect("a tree with one scan root missing fails",
               any(p.startswith("src/TSL.AddIn is missing") for p in problems), f"problems {problems}")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):  # its expected FAIL lines are not this run's verdict
            code = run_check(base / "empty")
        expect("run_check exits 1 on an empty tree and says why",
               code == 1 and "holds no .cs file" in captured.getvalue(), f"exit {code}: {captured.getvalue()!r}")

    total = passed + len(failures)
    if failures:
        print(f"check_house_dialogs --self-test: FAIL - {len(failures)} of {total} case(s) failed.")
        return 1
    print(f"check_house_dialogs --self-test: OK - {passed} of {total} cases behave as planted.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # A file:line must reach the log even when the console cannot encode a source line.
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="repository root (default: the parent of tools/)")
    parser.add_argument("--self-test", action="store_true", help="plant each case in a temp tree and check the verdicts")
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test()
    return run_check(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
