"""
pswp_build_lib.py - foundation library for the PS/WP Transaction Register toolkit.

Rebuilt 9-Sep-2026 against PS_WP_Transaction_Register_3FY_v125_HANDOVER.xlsx.
Everything here is derived from the workbook as it actually is, not from memory of an
earlier toolkit. Positions are never hardcoded: they come from Config (rule 19.6).

What lives here
  - Decimal money arithmetic that matches Excel (ROUND_HALF_UP, never banker's)
  - Config reader with LAST-KEY-WINS semantics (Config carries duplicate keys)
  - calamine value reads (rule 19.8: never a second openpyxl open just to look)
  - the LibreOffice convert-route recalc with the OOXMLRecalcMode=0 assertion (v125 trap)
  - a citation scanner + row-insert planner that mechanically enforces rule 19.11
  - verify helpers that require the literal string "TRUE"
  - style copying, column letters, md5

Rule 18/19.7: the caller runs build -> recalc -> verify -> ship as ONE script.
A partial run is discarded and re-run from the top, never resumed (rule 19.7 as amended v11).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

# ----------------------------------------------------------------------------------
# 1. Money and rounding
# ----------------------------------------------------------------------------------

CENT = Decimal("0.01")


def D(x: Any) -> Decimal:
    """Decimal from anything numeric or numeric-ish. Strips $ and thousands separators."""
    if x is None or x == "":
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    if isinstance(x, (int, float)):
        return Decimal(str(x))
    s = str(x).strip().replace("$", "").replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    return Decimal(s or "0")


def money(x: Any) -> Decimal:
    """Round to cents the way Excel does: half away from zero, never banker's.

    TRAP (schema section 4): Python round() is banker's rounding. A printed GST of
    $150.54 on a $1,505.35 subtotal falsely flags if you use it.
    """
    return D(x).quantize(CENT, rounding=ROUND_HALF_UP)


def gst_of(subtotal: Any) -> Decimal:
    """10 per cent of a subtotal, computed the way the check-3 formula computes it."""
    return money(D(subtotal) / Decimal("10"))


def ties(a: Any, b: Any, tol: str = "0.02") -> bool:
    """ROUND(ABS(a-b),2) <= tol. Never a bare float comparison (schema section 4 trap)."""
    return money(abs(D(a) - D(b))) <= Decimal(tol)


def f2(x: Any) -> float:
    """Two-decimal float for writing into a cell."""
    return float(money(x))


def fmt(x: Any) -> str:
    """$X,XXX.XX for reports."""
    v = money(x)
    return ("-" if v < 0 else "") + "${:,.2f}".format(abs(v))


# ----------------------------------------------------------------------------------
# 2. Column letters
# ----------------------------------------------------------------------------------


def col_letter(n: int) -> str:
    """1-indexed column number to letter. 88 -> CJ, 121 -> DQ, 127 -> DW."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_number(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


# ----------------------------------------------------------------------------------
# 3. Reads (calamine only - rule 19.8)
# ----------------------------------------------------------------------------------


def read_sheet(path: str, name: str) -> list[list[Any]]:
    """Values of one sheet. ~3.5s for the whole 24MB workbook; openpyxl costs ~52s."""
    from python_calamine import CalamineWorkbook

    wb = CalamineWorkbook.from_path(path)
    return wb.get_sheet_by_name(name).to_python(skip_empty_area=False)


def read_sheets(path: str, names: Iterable[str]) -> dict[str, list[list[Any]]]:
    from python_calamine import CalamineWorkbook

    wb = CalamineWorkbook.from_path(path)
    return {n: wb.get_sheet_by_name(n).to_python(skip_empty_area=False) for n in names}


def clean(v: Any) -> str:
    """calamine returns numeric strings carrying '.0' (rule 19.8). Strip it."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return "" if s == "None" else s


# ----------------------------------------------------------------------------------
# 4. Config (rule 19.6)
# ----------------------------------------------------------------------------------

_RANGE = re.compile(r"(\d+)\s*:\s*(\d+)")


class Config:
    """Key/value block on the Config sheet.

    LAST KEY WINS. Config carries the same key more than once where a block grew
    (CL_DATA appears at row 23 as 5:22937 and again at row 937 as 5:27198). A reader
    that takes the first hit silently addresses 4,261 fewer rows than exist.
    """

    def __init__(self, rows: list[list[Any]]):
        self.raw: dict[str, Any] = {}
        self.rows: dict[str, int] = {}
        for i, r in enumerate(rows, start=1):
            if not r:
                continue
            k = clean(r[0])
            if not k or len(r) < 2:
                continue
            v = r[1]
            if v is None or str(v).strip() in ("", "None"):
                continue
            self.raw[k] = v
            self.rows[k] = i

    def __contains__(self, k: str) -> bool:
        return k in self.raw

    def get(self, k: str, default: Any = None) -> Any:
        return self.raw.get(k, default)

    def text(self, k: str) -> str:
        return clean(self.raw[k])

    def num(self, k: str) -> Decimal:
        return D(self.raw[k])

    def int_(self, k: str) -> int:
        return int(D(self.raw[k]))

    def span(self, k: str) -> tuple[int, int]:
        """First 'a:b' pair inside the value. 'EIL_Controls!5:3766 (relocated v123)' -> (5,3766)."""
        m = _RANGE.search(clean(self.raw[k]))
        if not m:
            raise KeyError("Config key %s does not carry a row range: %r" % (k, self.raw[k]))
        return int(m.group(1)), int(m.group(2))

    def require(self, **expected: Any) -> None:
        """Hard pre-write assertion. Every build states what it believes before it writes."""
        bad = []
        for k, want in expected.items():
            if k not in self.raw:
                bad.append("%s missing from Config" % k)
                continue
            got = clean(self.raw[k])
            if str(want) != got:
                bad.append("%s: Config says %r, build expected %r" % (k, got, str(want)))
        if bad:
            raise AssertionError("Config assertion failed:\n  " + "\n  ".join(bad))


def load_config(path: str) -> Config:
    return Config(read_sheet(path, "Config"))


# ----------------------------------------------------------------------------------
# 5. LibreOffice convert-route recalc
# ----------------------------------------------------------------------------------

RECALC_ITEM = (
    '<item oor:path="/org.openoffice.Office.Calc/Formula/Load">'
    '<prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>'
)

_XCU_SHELL = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{items}
</oor:items>
"""


def _write_profile(profile: str) -> str:
    """Create an isolated LibreOffice profile carrying OOXMLRecalcMode=0.

    THE RECALC TRAP (v125). A fresh profile has no such setting, LibreOffice loads the
    cached values, and the converted file ships with every formula stale. A cached-value
    pass is indistinguishable from a real one unless a control is expected to CHANGE, so
    every verify pass must also pin at least one figure the build is supposed to move.
    """
    user = os.path.join(profile, "user")
    os.makedirs(user, exist_ok=True)
    xcu = os.path.join(user, "registrymodifications.xcu")
    with open(xcu, "w", encoding="utf-8") as fh:
        fh.write(_XCU_SHELL.format(items=RECALC_ITEM))
    return xcu


def assert_recalc_profile(xcu: str) -> None:
    with open(xcu, encoding="utf-8") as fh:
        body = fh.read()
    if "OOXMLRecalcMode" not in body or "<value>0</value>" not in body:
        raise AssertionError("recalc profile does not carry OOXMLRecalcMode=0: %s" % xcu)


def lo_recalc(src: str, outdir: str, timeout: int = 900, log=print) -> str:
    """soffice --headless --convert-to xlsx with an isolated, asserted profile.

    Foreground with a timeout, never backgrounded (accumulated trap). recalc.py, the
    macro route, is BANNED: it hangs in the container.
    Returns the path of the recalculated file, which is what verify must read.
    """
    src = os.path.abspath(src)
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)  # the output directory must pre-exist
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    xcu = _write_profile(profile)
    assert_recalc_profile(xcu)
    cmd = [
        "soffice",
        "-env:UserInstallation=file://%s" % profile,
        "--headless",
        "--norestore",
        "--convert-to",
        "xlsx",
        "--outdir",
        outdir,
        src,
    ]
    t0 = time.time()
    log("recalc: converting %s" % os.path.basename(src))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = os.path.join(outdir, os.path.basename(src))
    if not os.path.exists(out):
        raise RuntimeError(
            "recalc produced no file.\nstdout: %s\nstderr: %s" % (proc.stdout, proc.stderr)
        )
    log("recalc: %.1fs" % (time.time() - t0))
    shutil.rmtree(profile, ignore_errors=True)
    return out


# ----------------------------------------------------------------------------------
# 6. Verify helpers
# ----------------------------------------------------------------------------------


@dataclass
class VerifyResult:
    name: str
    ok: bool
    got: Any
    want: Any

    def line(self) -> str:
        return "%-4s %-58s got %r want %r" % ("PASS" if self.ok else "FAIL", self.name, self.got, self.want)


class Verifier:
    """Every limb must return the LITERAL string 'TRUE' or an exact expected value.

    The verify sweep costs ~4 seconds against a ~175 second chain. There is no
    efficiency argument for a partial verify, ever (settled decision, v122).
    """

    def __init__(self):
        self.results: list[VerifyResult] = []

    def true(self, name: str, value: Any) -> None:
        self.results.append(VerifyResult(name, clean(value) == "TRUE", clean(value), "TRUE"))

    def equals(self, name: str, got: Any, want: Any) -> None:
        self.results.append(VerifyResult(name, clean(got) == clean(want), clean(got), clean(want)))

    def amount(self, name: str, got: Any, want: Any, tol: str = "0.00") -> None:
        self.results.append(VerifyResult(name, ties(got, want, tol), f2(got), f2(want)))

    def moved(self, name: str, before: Any, after: Any) -> None:
        """Pin at least one figure the build is SUPPOSED to move.

        A cached-value recalc pass is indistinguishable from a real one otherwise
        (v125 recalc trap). Every build must call this at least once.
        """
        self.results.append(
            VerifyResult(name + " (moved)", clean(before) != clean(after), clean(after), "!= %s" % clean(before))
        )

    @property
    def failures(self) -> list[VerifyResult]:
        return [r for r in self.results if not r.ok]

    @property
    def clean_pass(self) -> bool:
        return bool(self.results) and not self.failures

    def report(self) -> str:
        return "\n".join(r.line() for r in self.results)


# ----------------------------------------------------------------------------------
# 7. Citation scanning and row-insert planning (rule 19.11, enforced mechanically)
# ----------------------------------------------------------------------------------

_CELLREF = re.compile(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_.]*))?!?\$?([A-Z]{1,3})\$?(\d+)")


@dataclass
class Citation:
    sheet: str
    cell: str
    formula: str
    target_sheet: str
    rows: tuple[int, int]


_FORMULA_CACHE: dict[int, list[tuple[str, str, str]]] = {}


def _all_formulas(wb) -> list[tuple[str, str, str]]:
    """Every formula in the workbook, collected once per workbook object.

    The Register alone is 31,360 rows by 146 columns, so a per-question sweep is minutes.
    One pass, cached, keeps the rule 19.11 citation audit affordable enough that it is
    always run rather than sometimes skipped.
    """
    key = id(wb)
    if key not in _FORMULA_CACHE:
        out: list[tuple[str, str, str]] = []
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    v = c.value
                    if isinstance(v, str) and v.startswith("="):
                        out.append((ws.title, c.coordinate, v))
        _FORMULA_CACHE[key] = out
    return _FORMULA_CACHE[key]


def scan_citations(wb, target_sheet: str, low: int, high: int) -> list[Citation]:
    """Every formula anywhere in the workbook that cites rows [low, high] of target_sheet.

    This is what makes rule 19.11 mechanical rather than remembered. The v123 build found
    exactly one such citation (Evidence_Invoices!C3788 pointing at a relocated control
    block); a build that moves a block without this sweep ships a silent FALSE.

    wb must be an openpyxl workbook opened WITHOUT data_only, so formulas are visible.
    """
    hits: list[Citation] = []
    pat_local = re.compile(r"\$?([A-Z]{1,3})\$?(\d+)")
    ext = re.compile(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))!(\$?[A-Z]{1,3}\$?\d+)")
    for sheet_title, coord, v in _all_formulas(wb):
        found = False
        for m in ext.finditer(v):
            sheet = m.group(1) or m.group(2)
            if sheet != target_sheet:
                continue
            mm = pat_local.search(m.group(3))
            if mm and low <= int(mm.group(2)) <= high:
                hits.append(Citation(sheet_title, coord, v, target_sheet, (low, high)))
                found = True
                break
        if not found and sheet_title == target_sheet:
            for mm in pat_local.finditer(v):
                if low <= int(mm.group(2)) <= high:
                    hits.append(Citation(sheet_title, coord, v, target_sheet, (low, high)))
                    break
    return hits


@dataclass
class InsertPlan:
    """An append into a data block that sits ABOVE reserved totals/control rows.

    openpyxl.insert_rows moves cells but does NOT adjust formulas, and a blanket regex
    is forbidden (rule 19.10). So every citing formula is rewritten EXPLICITLY from a
    declared rewrite map, and any citation found by the scanner that is not in the map
    aborts the build.
    """

    sheet: str
    data_first: int
    data_last: int
    n_new: int
    reserved: list[tuple[int, int]] = field(default_factory=list)
    rewrites: dict[str, str] = field(default_factory=dict)   # "Sheet!Cell" -> new formula
    unhandled: list[Citation] = field(default_factory=list)

    @property
    def insert_at(self) -> int:
        return self.data_last + 1

    @property
    def new_last(self) -> int:
        return self.data_last + self.n_new

    def shifted(self, row: int) -> int:
        return row + self.n_new if row > self.data_last else row


def apply_insert(ws, plan: InsertPlan, style_row: int | None = None, cols: int = 40) -> None:
    """Insert the rows and carry the template style across (openpyxl keeps stale styles)."""
    import copy as _copy

    if plan.n_new <= 0:
        return
    ws.insert_rows(plan.insert_at, plan.n_new)
    if style_row is None:
        return
    for r in range(plan.insert_at, plan.insert_at + plan.n_new):
        for c in range(1, cols + 1):
            ws.cell(row=r, column=c)._style = _copy.copy(ws.cell(row=style_row, column=c)._style)


def copy_style(ws, src_row: int, dst_row: int, cols: Iterable[int]) -> None:
    """Overwritten regions keep stale styles unless every written cell gets the template."""
    import copy as _copy

    for c in cols:
        ws.cell(row=dst_row, column=c)._style = _copy.copy(ws.cell(row=src_row, column=c)._style)


def repoint_defined_name(wb, name: str, new_last: int) -> str:
    """Extend a row-bounded defined name to a new last row. Returns the new destination."""
    dn = wb.defined_names.get(name) if hasattr(wb.defined_names, "get") else wb.defined_names[name]
    dest = dn.value
    new = re.sub(r"(\$\d+):(\$?[A-Z]{1,3}\$?)(\d+)", lambda m: "%s:%s%d" % (m.group(1), m.group(2), new_last), dest)
    new = re.sub(r"\$(\d+)\s*$", "$%d" % new_last, new)
    dn.value = new
    return new


# ----------------------------------------------------------------------------------
# 8. Text hygiene
# ----------------------------------------------------------------------------------

CELL_CAP = 32767


def condense(text: str, note_if_trimmed: bool = True) -> tuple[str, str | None]:
    """Excel caps a cell at 32,767 characters.

    Condense layout padding only: three-plus spaces to two, three-plus newlines to two.
    The printed text survives; only padding goes. Returns (text, note-or-None).
    """
    if text is None:
        return "", None
    out = re.sub(r"[ \t]{3,}", "  ", str(text))
    out = re.sub(r"\n{3,}", "\n\n", out)
    note = None
    if len(out) > CELL_CAP:
        out = out[: CELL_CAP - 40].rstrip() + " ... [truncated at the 32,767 cell cap]"
        if note_if_trimmed:
            note = "Cell cap forced truncation of this field."
    return out, note


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def counts_only(label: str, **counts: Any) -> str:
    """Rule 19.5: counts-only console. Work files go to outputs, not to stdout."""
    return "%s: %s" % (label, ", ".join("%s %s" % (k, v) for k, v in counts.items()))


__all__ = [
    "D", "money", "gst_of", "ties", "f2", "fmt", "col_letter", "col_number",
    "read_sheet", "read_sheets", "clean", "Config", "load_config",
    "lo_recalc", "assert_recalc_profile", "RECALC_ITEM",
    "Verifier", "VerifyResult", "scan_citations", "Citation", "InsertPlan",
    "apply_insert", "copy_style", "repoint_defined_name", "condense", "md5_file",
    "counts_only", "CELL_CAP",
]
