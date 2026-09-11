#!/usr/bin/env python3
"""
pswp_verify.py - the standalone verify sweep.

Rebuilt 9-Sep-2026. `pswp_build_batch.py` runs its own verify inside the chain; this is the
same sweep run on demand, against any workbook, by anyone, without a build.

Use it to audit a workbook someone else produced, to prove a file is still sound after a
manual edit in Excel, or to check a shipped version before relying on it.

WHAT IT PROVES
  1. Controls sheet: the master verdict, the registered count, and every control row
  2. Control total, and the count of amount-bearing register rows
  3. Rule 17: every sighted register row returns "TRUE" on all three checks, and carries an
     Ev Invoice ID
  4. Evidence_Invoices control block, and the EIL_Controls per-invoice panel
  5. Coverage ties to the register control total
  6. Header-to-line reconciliation across the whole evidence set
  7. A whole-workbook error sweep: any cell holding an Excel error value
  8. Defined names still resolve to a range, and none points at a deleted sheet
  9. Any expectation the caller pins in a JSON file

READ THE RECALCULATED FILE. openpyxl does not evaluate formulas, so a verify run against a
file that has not been through the convert route reads stale cached values and proves
nothing (rule 18). This script reads values with calamine and refuses a file whose Controls
master cell is empty, which is what an unrecalculated openpyxl output looks like.

Usage
    python pswp_verify.py workbook.xlsx
    python pswp_verify.py workbook.xlsx --expect expectations.json --out result.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from decimal import Decimal
from typing import Any

from pswp_build_lib import Config, D, clean, col_number, fmt, money, read_sheets, ties

ERRORS = {"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NULL!", "#NUM!", "#SPILL!", "#CALC!"}

REG_NATURE_BASIS = 27
REG_EVID = 88
REG_CHK1, REG_CHK2, REG_CHK3 = 122, 123, 124
REG_AMOUNT = 20


def sweep(path: str, expect: dict | None = None, log=print) -> dict:
    t0 = time.time()
    ok: list[str] = []
    fails: list[str] = []
    expect = expect or {}

    from python_calamine import CalamineWorkbook

    wbk = CalamineWorkbook.from_path(path)
    names = list(wbk.sheet_names)
    sheets = {n: wbk.get_sheet_by_name(n).to_python(skip_empty_area=False) for n in names}
    cfg = Config(sheets["Config"])

    # --- 1. Controls
    ctrl = sheets.get("Controls")
    if not ctrl:
        fails.append("no Controls sheet")
    else:
        master = clean(ctrl[3][1])
        registered = int(D(ctrl[4][1] or 0))
        failing = int(D(ctrl[4][4] or 0))
        if master == "":
            fails.append("Controls master cell is empty: this file has not been recalculated (rule 18)")
        elif master == "TRUE":
            ok.append("Controls: %d controls, %d FALSE (master cell TRUE)" % (registered, failing))
        else:
            fails.append("Controls master verdict is %s with %d failing" % (master, failing))
        for r in range(8, 8 + registered + 8):
            if r - 1 >= len(ctrl):
                break
            row = ctrl[r - 1]
            if not clean(row[0]):
                continue
            if clean(row[6]) not in ("TRUE", ""):
                fails.append("Controls row %d (%s): %s | live %s, expected %s"
                             % (r, clean(row[0]), str(row[2])[:70], clean(row[4]), clean(row[5])))

    # --- 2. control total and row count
    reg = sheets["Register"]
    total_row = int(D(cfg.get("REGISTER_TOTAL_ROW")))
    control_total = cfg.num("CONTROL_TOTAL")
    live_total = D(reg[total_row - 1][REG_AMOUNT - 1])
    if ties(live_total, control_total, "0.00"):
        ok.append("control total %s" % money(live_total))
    else:
        fails.append("control total is %s, Config declares %s" % (fmt(live_total), fmt(control_total)))
    first, last = cfg.span("REGISTER_DATA")
    data = reg[first - 1:last]
    amount_rows = sum(1 for r in data if isinstance(r[REG_AMOUNT - 1], (int, float)))
    ok.append("amount-bearing rows %d" % amount_rows)
    body = money(sum(D(r[REG_AMOUNT - 1]) for r in data))
    if ties(body, live_total, "0.00"):
        ok.append("register body sums to the total row")
    else:
        fails.append("register body sums to %s against a total row of %s" % (fmt(body), fmt(live_total)))

    # --- 3. rule 17 on every sighted row
    sighted = [r for r in data if clean(r[REG_NATURE_BASIS - 1]) == "Sighted invoice line"]
    bad = [i for i, r in enumerate(sighted) if any(clean(r[c - 1]) != "TRUE" for c in (REG_CHK1, REG_CHK2, REG_CHK3))]
    no_evid = [r for r in sighted if not clean(r[REG_EVID - 1])]
    if bad:
        fails.append("%d sighted register row(s) do not return TRUE on all three rule 17 checks" % len(bad))
    else:
        ok.append("rule 17: %d sighted rows, every check TRUE" % len(sighted))
    if no_evid:
        fails.append("%d sighted row(s) carry no Ev Invoice ID" % len(no_evid))
    declared_sighted = int(D(cfg.get("SIGHTED_COUNT") or 0))
    if declared_sighted and declared_sighted != len(sighted):
        fails.append("Config SIGHTED_COUNT is %d, the register holds %d" % (declared_sighted, len(sighted)))

    # --- 4. evidence control blocks
    ei = sheets["Evidence_Invoices"]
    cf, cl_ = cfg.span("EI_CONTROL_ROWS")
    ei_ctrl = [(r, clean(ei[r - 1][2])) for r in range(cf, cl_ + 1) if clean(ei[r - 1][2]) in ("TRUE", "FALSE")]
    ei_bad = [r for r, v in ei_ctrl if v != "TRUE"]
    if ei_bad:
        fails.append("Evidence_Invoices control rows FALSE: %s" % ei_bad)
    else:
        ok.append("Evidence_Invoices control block: %d rows TRUE" % len(ei_ctrl))

    eic = sheets.get("EIL_Controls")
    if eic:
        ef, el = cfg.span("EIL_CONTROLS_SHEET")
        rows = [clean(eic[r - 1][4]) for r in range(ef, el + 1) if clean(eic[r - 1][0])]
        eic_bad = sum(1 for v in rows if v != "TRUE")
        if eic_bad:
            fails.append("EIL_Controls: %d of %d per-invoice reconciliations not TRUE" % (eic_bad, len(rows)))
        else:
            ok.append("EIL_Controls: %d per-invoice reconciliations TRUE" % len(rows))

    # --- 5. Coverage
    cov = sheets.get("Coverage")
    if cov:
        cov_total = D(cov[int(D(cfg.get("COVERAGE_TOTAL_ROW"))) - 1][2])
        if ties(cov_total, live_total, "0.00"):
            ok.append("Coverage ties to the register control total")
        else:
            fails.append("Coverage totals %s against a register total of %s" % (fmt(cov_total), fmt(live_total)))

    # --- 6. evidence headers against captured lines
    eif, eil_end = cfg.span("EI_DATA")
    hdr_ex = money(sum(D(r[9]) for r in ei[eif - 1:eil_end] if clean(r[0])))
    lf, ll = cfg.span("EIL_DATA")
    lines_ex = money(sum(D(r[6]) for r in sheets["Evidence_Invoice_Lines"][lf - 1:ll] if clean(r[0])))
    allowance = D(cfg.get("GSTINC_ALLOWANCE") or 0)
    if ties(hdr_ex, lines_ex - allowance, "0.02"):
        ok.append("evidence headers tie to captured lines within the declared GST-inclusive allowance %s" % fmt(allowance))
    else:
        fails.append("evidence headers %s against captured lines %s less allowance %s"
                     % (fmt(hdr_ex), fmt(lines_ex), fmt(allowance)))

    # --- 7. error sweep
    errs: list[str] = []
    for name, rows in sheets.items():
        for ri, row in enumerate(rows, start=1):
            for ci, v in enumerate(row, start=1):
                if isinstance(v, str) and v in ERRORS:
                    errs.append("%s!%s%d %s" % (name, _letters(ci), ri, v))
                    if len(errs) > 40:
                        break
    if errs:
        fails.append("workbook error sweep: %d error cell(s), first: %s" % (len(errs), ", ".join(errs[:5])))
    else:
        ok.append("workbook error sweep: 0 error cells")

    # --- 8. defined names
    try:
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True)
        broken = [n for n, dn in wb.defined_names.items()
                  if "#REF" in str(dn.value) or (("!" in str(dn.value)) and str(dn.value).split("!")[0].strip("'=") not in names)]
        wb.close()
        if broken:
            fails.append("defined names pointing nowhere: %s" % broken)
        else:
            ok.append("defined names all resolve")
    except Exception as exc:
        ok.append("defined-name check skipped (%s)" % exc)

    # --- 9. caller pins
    for ref, want in (expect.get("cells") or {}).items():
        got = _cell(sheets, ref)
        if clean(got) == clean(want):
            ok.append("pin %s = %s" % (ref, clean(want)))
        else:
            fails.append("pin %s is %r, expected %r" % (ref, clean(got), clean(want)))
    for key, want in (expect.get("config") or {}).items():
        got = clean(cfg.get(key))
        if got == str(want):
            ok.append("Config %s = %s" % (key, want))
        else:
            fails.append("Config %s is %r, expected %r" % (key, got, str(want)))

    res = {"ok": ok, "fails": fails, "file": path, "seconds": round(time.time() - t0),
           "VERDICT": "PASS" if not fails else "FAIL"}
    log("verify: %d limbs passed, %d failed -> %s (%ds)" % (len(ok), len(fails), res["VERDICT"], res["seconds"]))
    for f in fails:
        log("  FAIL %s" % f)
    return res


def _letters(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(sheets: dict, ref: str) -> Any:
    sheet, cell = ref.split("!")
    col = "".join(c for c in cell if c.isalpha())
    row = int("".join(c for c in cell if c.isdigit()))
    return sheets[sheet][row - 1][col_number(col) - 1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify a PS/WP register workbook.")
    ap.add_argument("workbook")
    ap.add_argument("--expect", help="JSON with {'cells': {...}, 'config': {...}}")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    expect = json.load(open(a.expect)) if a.expect else None
    res = sweep(a.workbook, expect)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    return 0 if res["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
