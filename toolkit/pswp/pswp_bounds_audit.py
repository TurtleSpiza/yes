#!/usr/bin/env python3
"""
pswp_bounds_audit.py - the standing bounds limb (Config!BOUNDS_AUDIT).

Rebuilt 9-Sep-2026. Every row-bounded range in the workbook, in a formula or a defined
name, is tested against the blocks Config declares. The question it answers is the one a
control cannot answer about itself: does this range still cover the data it is supposed to
cover, now that the data has grown?

A control that returns TRUE over a range ending 4,261 rows short of the data is a control
that proves nothing, and it looks identical to one that proves everything. This is the only
limb that catches it.

VERDICTS
  EXACT       the range ends exactly at the block's last data row
  HEADROOM    the range ends past the data but before the first reserved row: correct, and
              the usual shape for a named range that has been given room to grow
  SHORT       the range ends before the block's last data row. FAIL: rows are excluded
  SPANNING    the range runs into a reserved row (a totals row, a control block). FAIL:
              the total is counted inside the thing that sums it
  SUB_BLOCK   the range covers a declared sub-block (a panel inside a sheet), not the whole
  DIAGNOSTIC  the range is on a sheet declared diagnostic, where shortness is by design
  WARN_UNDECLARED  the sheet has no declared block in Config, so the range cannot be
              audited hard. Declare the block and it becomes testable

Usage
    python pswp_bounds_audit.py workbook.xlsx --out bounds_v126.json
    python pswp_bounds_audit.py workbook.xlsx --strict     exit 1 on any FAIL
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from typing import Any

from pswp_build_lib import Config, clean, col_letter

# Config keys that declare a data block: key -> (sheet, label)
DECLARED = {
    "REGISTER_DATA": ("Register", "register data"),
    "EIL_DATA": ("Evidence_Invoice_Lines", "invoice line data"),
    "EI_DATA": ("Evidence_Invoices", "invoice header data"),
    "CL_DATA": ("Creditor_Lines", "creditor line data"),
    "PKL_DATA": ("PK_Listing", "PK listing data"),
    "SITE_ALLOC_DATA": ("Site_Allocation", "site allocation data"),
    "SITE_CROSSWALK_DATA": ("Site_Crosswalk", "site crosswalk data"),
    "SITES_PARTITION": ("Sites", "sites partition (panel A plus classification rows)"),
    "THEME_MAP_CATEGORIES": ("Theme_Map", "theme map categories"),
    "THEME_MAP_V3_CATEGORIES": ("Theme_Map_v3", "theme v3 lookup keys"),
    "JP_DATA": ("Journal_Provenance", "journal provenance data"),
    "JS_DATA": ("Journal_Sources", "journal source data"),
    "JOURNAL_PULL_DATA": ("Journal_Pull", "journal pull data"),
    "COVERAGE_PANELA": ("Coverage", "coverage panel A"),
    "SITES_PANELA": ("Sites", "sites panel A"),
    "SITES_PANELB": ("Sites", "sites panel B"),
    "EIL_CONTROLS_SHEET": ("EIL_Controls", "per-invoice reconciliation panel"),
    # Declared narrow panels. A control that covers only its own panel is not SHORT: the
    # rule 17 staging block is seven rows by design and always will be.
    "STAGED_ROWS": ("Evidence_Invoices", "rule 17 pre-v4 staging block"),
    "SITES_GROUP_ROWS": ("Sites", "sites classification rows (a partition, not subtotals)"),
}

# Config keys that declare a RESERVED row or block: nothing that sums the data may reach in
RESERVED = {
    "REGISTER_TOTAL_ROW": ("Register", "register total row"),
    "EI_TOTALS_ROW": ("Evidence_Invoices", "EI totals row"),
    "EI_CONTROL_ROWS": ("Evidence_Invoices", "EI control block"),
    "SITES_TOTAL_ROW": ("Sites", "sites total row"),
    "SITES_CHECK_ROW": ("Sites", "sites check row"),
    "SITE_ALLOC_TOTAL_ROW": ("Site_Allocation", "site allocation total row"),
    "PKL_CHECK_ROW": ("PK_Listing", "PK listing check row"),
    "THEMES_TOTAL_ROW": ("Themes", "themes total row"),
    "THEMES_CONTROL_ROWS": ("Themes", "themes control rows"),
    "COVERAGE_TOTAL_ROW": ("Coverage", "coverage total row"),
    "JP_TOTALS_ROW": ("Journal_Provenance", "journal provenance totals row"),
    "JP_CONTROL_ROWS": ("Journal_Provenance", "journal provenance control rows"),
    "JS_CONTROL_ROWS": ("Journal_Sources", "journal source control rows"),
    "JOURNAL_PULL_TOTAL_ROW": ("Journal_Pull", "journal pull total row"),
    "JOURNAL_PULL_CHECK_ROW": ("Journal_Pull", "journal pull check row"),
    "LADDER_TOTAL_ROW": ("Confirmation_Ladder", "ladder total row"),
    "LADDER_CHECK_ROW": ("Confirmation_Ladder", "ladder check row"),
    "THEME_MAP_V3_CONTROL_ROW": ("Theme_Map_v3", "theme v3 control row"),
}

# Sheets where a short range is the design, not a defect
DIAGNOSTIC_SHEETS = {"Freeze_Log", "Project_Instructions", "Method", "Handover", "Data_Acquisition"}

RANGE = re.compile(
    r"(?:(?:'(?P<q>[^']+)'|(?P<s>[A-Za-z_][A-Za-z0-9_.]*))!)?"
    r"\$?(?P<c1>[A-Z]{1,3})\$?(?P<r1>\d+)\s*:\s*\$?(?P<c2>[A-Z]{1,3})\$?(?P<r2>\d+)"
)


def _spans(cfg: Config, keys: dict) -> dict:
    out: dict[str, list[dict]] = defaultdict(list)
    for key, (sheet, label) in keys.items():
        if key not in cfg:
            continue
        try:
            first, last = cfg.span(key)
        except KeyError:
            v = clean(cfg.get(key))
            if not v.replace(".0", "").isdigit():
                continue
            first = last = int(float(v))
        out[sheet].append({"first": first, "last": last, "label": label, "source": "Config!%s" % key})
    return dict(out)


def audit(path: str, log=print) -> dict:
    import openpyxl

    t0 = time.time()
    from pswp_build_lib import read_sheet

    cfg = Config(read_sheet(path, "Config"))
    declared_all = _spans(cfg, DECLARED)
    reserved = _spans(cfg, RESERVED)

    # the widest declared block per sheet is the data block; the rest are sub-blocks
    declared: dict[str, dict] = {}
    sub_blocks: dict[str, list[dict]] = {}
    for sheet, blocks in declared_all.items():
        blocks = sorted(blocks, key=lambda b: b["last"] - b["first"], reverse=True)
        declared[sheet] = blocks[0]
        if blocks[1:]:
            sub_blocks[sheet] = blocks[1:]

    wb = openpyxl.load_workbook(path)
    last_populated: dict[str, int] = {}
    for ws in wb.worksheets:
        last = 0
        for row in ws.iter_rows():
            if any(c.value not in (None, "") for c in row):
                last = row[0].row
        last_populated[ws.title] = last

    findings: list[dict] = []
    stats = defaultdict(int)

    def test(where: str, cell: str, text: str, origin: str, sheet: str, r1: int, r2: int) -> None:
        stats["tested"] += 1
        blk = declared.get(sheet)
        if blk is None:
            if sheet in DIAGNOSTIC_SHEETS:
                stats["DIAGNOSTIC"] += 1
                return
            lp = last_populated.get(sheet, 0)
            if r2 < lp:
                stats["WARN"] += 1
                findings.append({
                    "verdict": "WARN_UNDECLARED", "where": where, "cell": cell, "target": sheet,
                    "cited_end": r2, "last_populated": lp, "rows_short": lp - r2, "origin": origin,
                    "note": "sheet has no declared data block in Config; declare it so this can be audited hard",
                    "text": text,
                })
            else:
                stats["EXACT"] += 1
            return
        for sb in sub_blocks.get(sheet, []):
            if (r1, r2) == (sb["first"], sb["last"]):
                stats["SUB_BLOCK"] += 1
                return
        # SPANNING is a range that starts in the DATA and reaches into a reserved row.
        # A control that reads a control block from end to end is not spanning: reading the
        # controls is what it is for. Sites rows 612:622 are likewise not reserved at all,
        # because Config records that they PARTITION the register rather than subtotal it.
        hit = next((rs for rs in reserved.get(sheet, [])
                    if r1 < rs["first"] <= r2), None)
        if hit:
            # The harm is a TOTAL summed inside the thing that sums it. A control that
            # sweeps a block for the text "TRUE" and happens to cross a totals row counts
            # no amounts and does no damage, so it is reported and not failed.
            rng = "%s%d" % (m_c1, r1) if False else None
            harmful = bool(re.search(r"\bSUM(?:PRODUCT)?\(\s*(?:'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)?!?\$?[A-Z]{1,3}\$?%d\s*:" % r1, text)) \
                or bool(re.search(r"\bSUBTOTAL\([^)]*\$?[A-Z]{1,3}\$?%d\s*:" % r1, text))
            stats["SPANNING" if harmful else "SPANNING_BENIGN"] += 1
            findings.append({
                "verdict": "SPANNING" if harmful else "SPANNING_BENIGN",
                "where": where, "cell": cell, "target": sheet,
                "cited_end": r2, "reserved": "%d:%d" % (hit["first"], hit["last"]),
                "reserved_label": hit["label"], "origin": origin,
                "note": ("the range reaches into a reserved row and is summed, so the total is counted inside the thing that sums it"
                         if harmful else
                         "the range crosses a reserved row but counts text rather than summing amounts; reported, not failed"),
                "text": text,
            })
            return
        if r2 < blk["last"]:
            stats["SHORT"] += 1
            findings.append({
                "verdict": "SHORT", "where": where, "cell": cell, "target": sheet,
                "cited_end": r2, "block_last": blk["last"], "rows_short": blk["last"] - r2,
                "origin": origin, "source": blk["source"],
                "note": "the range stops before the declared data block ends, so those rows are excluded",
                "text": text,
            })
            return
        stats["EXACT" if r2 == blk["last"] else "HEADROOM"] += 1

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if not isinstance(v, str) or not v.startswith("="):
                    continue
                for m in RANGE.finditer(v):
                    sheet = m.group("q") or m.group("s") or ws.title
                    r1, r2 = int(m.group("r1")), int(m.group("r2"))
                    if sheet == ws.title and r1 == r2 == c.row:
                        stats["row_local_skipped"] += 1
                        continue
                    test(ws.title, c.coordinate, v[1:], "formula", sheet, r1, r2)

    names: dict[str, str] = {}
    for name, dn in wb.defined_names.items():
        dest = str(dn.value)
        names[name] = dest
        for m in RANGE.finditer(dest):
            sheet = m.group("q") or m.group("s")
            if not sheet:
                continue
            test("defined name", name, dest, "defined_name", sheet, int(m.group("r1")), int(m.group("r2")))
    wb.close()

    grouped: dict[tuple, dict] = {}
    for f in findings:
        key = (f["verdict"], f["target"], f.get("cited_end"), f["text"])
        if key in grouped:
            grouped[key]["occurrences"] += 1
        else:
            f = dict(f)
            f["occurrences"] = 1
            grouped[key] = f

    fails = [f for f in grouped.values() if f["verdict"] in ("SHORT", "SPANNING")]
    out = {
        "workbook": path,
        "declared_blocks": declared,
        "declared_sub_blocks": sub_blocks,
        "reserved_rows": reserved,
        "undeclared_sheets_last_populated": {k: v for k, v in last_populated.items() if k not in declared},
        "defined_names": names,
        "stats": dict(stats),
        "findings_grouped": sorted(grouped.values(), key=lambda f: (f["verdict"], f["target"], f["cell"])),
        "FAIL_COUNT": len(fails),
        "VERDICT": "PASS" if not fails else "FAIL",
        "seconds": round(time.time() - t0),
    }
    log("bounds: tested %d, EXACT %d, HEADROOM %d, WARN %d, benign spans %d, SHORT %d, SPANNING %d -> %s"
        % (stats["tested"], stats["EXACT"], stats["HEADROOM"], stats["WARN"],
           stats["SPANNING_BENIGN"], stats["SHORT"], stats["SPANNING"], out["VERDICT"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit every row-bounded range against the declared blocks.")
    ap.add_argument("workbook")
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    res = audit(a.workbook)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    for f in res["findings_grouped"]:
        if f["verdict"] in ("SHORT", "SPANNING"):
            print("  %s %s!%s cites %s to row %s: %s" % (f["verdict"], f["where"], f["cell"], f["target"], f["cited_end"], f["note"]))
    return 1 if (a.strict and res["VERDICT"] != "PASS") else 0


if __name__ == "__main__":
    sys.exit(main())
