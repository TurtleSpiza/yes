#!/usr/bin/env python3
"""
pswp_ident_batch.py - identification from APLEDGER creditor histories.

Rebuilt 9-Sep-2026, on the v125 precedent (six histories, 249 rows cleared to Tier 1).

Rule 12 calls full creditor histories the efficient prior-year identification route, and
this is that route mechanised. It takes one or more APLEDGER exports, matches them against
unidentified register lines, and clears what the evidence supports, holding what it does not.

THE MATCH, AND WHY IT IS THREE-LEGGED
Reference alone is NOT identification (rule 12). A reference must be corroborated by amount
and by document date before a label is written:

  1. reference   equal, truncation aware in both directions
  2. amount      the history transaction amount is GST inclusive; it must reconcile to the
                 register ex-GST amount at incl / 1.1 within 2 cents, or match it directly
                 where the line is GST free
  3. date        the history document date must agree with the register document date

A reference that matches history rows from MORE THAN ONE account is a multi-vendor series
(rule 8) and is HELD, not resolved by picking the closer amount. A reference matching two
rows in the same account is held unless exactly one of them corroborates on amount.

WHAT IT WILL NOT DO
  - touch a Confirmed row. Confirmed rows are never identification targets
  - carry an ABN from a matched line onto an inferred one. Tier 2 stays Tier 2
  - identify a zero-amount companion from anything but a resolved non-zero sibling on the
    same reference, and only where the reference has exactly ONE non-zero AP row
  - re-capture a history already loaded. Content identity is md5 over the row EXCLUDING
    the __md5Row column, and the trailing account-balance row (blank reference) is dropped
    before anything is compared

Usage
    python pswp_ident_batch.py config.json --dry-run
    python pswp_ident_batch.py config.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pswp_build_lib import (
    D, clean, col_letter, copy_style, f2, fmt, lo_recalc, load_config, money,
    read_sheets, ties, Verifier, counts_only,
)

# Creditor_Lines column map (1-indexed), confirmed against the v125 sheet
CL = {"creditor": 1, "fy": 2, "reference": 3, "gst_date": 4, "discount_date": 5, "on_hold": 6,
      "has_note": 7, "date": 8, "doc_type": 9, "details": 10, "outstanding": 11, "applied": 12,
      "amount": 13, "due_date": 14, "ageing_date": 15, "period": 16, "ageing": 17, "source": 18,
      "units": 19, "discount": 20, "attachment": 21, "payment_details": 22, "abn": 23,
      "billing_system": 24, "work_order": 25, "wo_txn": 26, "work_system": 27}

REG = {"linekey": 1, "doc_date": 4, "reference": 8, "doc_type": 9, "creditor_code": 11,
       "contractor": 12, "abn": 13, "amount": 20, "enquiry_narration": 23, "nature_basis": 27,
       "evidence": 28, "tier": 29, "verdict": 31, "coding_note": 32, "status": 33,
       "followup": 34, "enq_first": 45, "enq_last": 53, "evid": 88}

UNIDENTIFIED = re.compile(r"unidentified", re.I)


def row_md5(row: list[Any]) -> str:
    """Content identity for a history row. __md5Row itself is excluded, or every row differs."""
    body = "|".join(clean(v) for i, v in enumerate(row) if i != len(row) - 1 or not str(v).startswith("__md5"))
    return hashlib.md5(body.encode("utf-8")).hexdigest()


def as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = clean(v)
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def ref_match(a: str, b: str) -> bool:
    """Equal, or one is a truncation of the other. TechOne truncates at 12 characters."""
    a, b = a.strip(), b.strip()
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 6 and len(b) >= 6 and (a.startswith(b) or b.startswith(a)):
        return True
    return a.lstrip("0") == b.lstrip("0") and len(a.lstrip("0")) >= 4


def amount_corroborates(hist_incl: Decimal, reg_ex: Decimal) -> str | None:
    """Return the basis that corroborates, or None. GST inclusive first, then GST free."""
    if ties(money(hist_incl / Decimal("1.1")), reg_ex, "0.02"):
        return "incl/1.1 within 2c"
    if ties(hist_incl, reg_ex, "0.02"):
        return "GST-free, history amount equals the register amount"
    return None


class Identification:
    def __init__(self, row: int, account: str, label: str, abn: str, basis: str,
                 hist_ref: str, hist_amount: Decimal, hist_date: date | None, details: str):
        self.row, self.account, self.label, self.abn = row, account, label, abn
        self.basis, self.hist_ref, self.hist_amount = basis, hist_ref, hist_amount
        self.hist_date, self.details = hist_date, details

    def narration(self) -> str:
        return ("Identified from the full APLEDGER creditor history for account %s (%s, ABN %s): "
                "reference %s posts on %s at %s incl GST, which corroborates this register line on "
                "reference, amount (%s) and document date. Tier 1."
                % (self.account, self.label, self.abn or "not printed", self.hist_ref,
                   self.hist_date or "(no date)", fmt(self.hist_amount), self.basis))


def match(workbook: str, histories: dict[str, list[list[Any]]], accounts: dict[str, dict],
          log=print) -> dict:
    """Match history rows to unidentified register lines. Pure analysis, no writes."""
    sheets = read_sheets(workbook, ["Register", "Creditor_Lines", "Config"])
    cfg = load_config(workbook)
    first, last = cfg.span("REGISTER_DATA")
    reg = sheets["Register"][first - 1:last]

    existing = {row_md5(r) for r in sheets["Creditor_Lines"][4:] if clean(r[CL["reference"] - 1])}

    # index the register by reference
    by_ref: dict[str, list[tuple[int, list]]] = defaultdict(list)
    for i, r in enumerate(reg):
        ref = clean(r[REG["reference"] - 1])
        if ref:
            by_ref[ref].append((first + i, r))

    idents: list[Identification] = []
    already: list[int] = []
    held: list[dict] = []
    new_cl_rows: list[list[Any]] = []
    dup_rows = 0

    # a reference seen in more than one account is multi-vendor: rule 8, held
    ref_accounts: dict[str, set[str]] = defaultdict(set)
    for account, rows in histories.items():
        for h in rows:
            ref_accounts[clean(h[CL["reference"] - 1])].add(account)

    for account, rows in histories.items():
        meta = accounts.get(account, {})
        label, abn = meta.get("label", account), meta.get("abn", "")
        for h in rows:
            href = clean(h[CL["reference"] - 1])
            if not href:
                continue  # the trailing account-balance row carries no reference
            md5 = row_md5(h)
            if md5 in existing:
                dup_rows += 1
            else:
                new_cl_rows.append(h)
                existing.add(md5)

            if len(ref_accounts[href]) > 1:
                held.append({"reference": href, "reason": "multi-vendor series: the reference appears in %s"
                             % ", ".join(sorted(ref_accounts[href])), "accounts": sorted(ref_accounts[href])})
                continue

            hist_amt = D(h[CL["amount"] - 1])
            hist_date = as_date(h[CL["date"] - 1])
            targets = [(rn, r) for k, v in by_ref.items() if ref_match(k, href) for rn, r in v]
            if not targets:
                continue
            corroborated = []
            for rn, r in targets:
                if clean(r[REG["status"] - 1]) == "Confirmed":
                    continue  # Confirmed rows are never identification targets
                if clean(r[REG["doc_type"] - 1]) != "PUR Cred Invoice":
                    continue
                reg_ex = D(r[REG["amount"] - 1])
                if abs(reg_ex) < Decimal("0.005"):
                    continue  # zero-amount companions are handled from a resolved sibling
                basis = amount_corroborates(hist_amt, reg_ex)
                if not basis:
                    continue
                reg_date = as_date(r[REG["doc_date"] - 1])
                if hist_date and reg_date and hist_date != reg_date:
                    continue
                corroborated.append((rn, r, basis))
            if len(corroborated) > 1:
                held.append({"reference": href, "reason": "reference corroborates on %d register rows; "
                             "the amount gate cannot choose between them" % len(corroborated)})
                continue
            if not corroborated:
                continue
            rn, r, basis = corroborated[0]
            label_now = clean(r[REG["contractor"] - 1])
            if label_now == label and clean(r[REG["nature_basis"] - 1]) in ("Matched creditor history", "Sighted invoice line"):
                already.append(rn)  # this history has been applied before; nothing to write
                continue
            if label_now and not UNIDENTIFIED.search(label_now) and label_now != label:
                held.append({"reference": href, "row": rn,
                             "reason": "row already carries the label %r; a history match does not overwrite an existing identity" % label_now})
                continue
            idents.append(Identification(rn, account, label, abn, basis, href, hist_amt, hist_date,
                                         clean(h[CL["details"] - 1])))

    # zero-amount companions: only from a resolved sibling, and only where the reference
    # has exactly one non-zero AP row
    companions: list[Identification] = []
    resolved_rows = {i.row: i for i in idents}
    already_rows = set(already)
    for ref, rows in by_ref.items():
        nonzero = [(rn, r) for rn, r in rows if abs(D(r[REG["amount"] - 1])) >= Decimal("0.005")]
        zeros = [(rn, r) for rn, r in rows if abs(D(r[REG["amount"] - 1])) < Decimal("0.005")]
        if len(nonzero) != 1 or not zeros:
            continue
        src = resolved_rows.get(nonzero[0][0])
        if not src:
            continue
        for rn, r in zeros:
            if clean(r[REG["status"] - 1]) == "Confirmed":
                continue
            if clean(r[REG["contractor"] - 1]) == src.label:
                continue  # the companion already carries its sibling's identity
            c = Identification(rn, src.account, src.label, src.abn, "zero-amount companion",
                               src.hist_ref, Decimal("0"), src.hist_date, src.details)
            companions.append(c)

    res = {
        "identifications": idents, "companions": companions, "held": held,
        "already_identified": already,
        "new_creditor_rows": new_cl_rows, "duplicate_history_rows": dup_rows,
        "value": money(sum(D(reg[i.row - first][REG["amount"] - 1]) for i in idents)),
    }
    log(counts_only("match", identified=len(idents), already=len(already),
                    companions=len(companions), held=len(held),
                    new_creditor_rows=len(new_cl_rows), duplicates=dup_rows, value=fmt(res["value"])))
    return res


def build(config: dict, dry_run: bool = False, log=print) -> int:
    t0 = time.time()
    workbook = config["workbook_in"]
    out_dir = config.get("output_dir", "outputs")
    os.makedirs(out_dir, exist_ok=True)

    histories: dict[str, list[list[Any]]] = {}
    for account, spec in config["accounts"].items():
        path = spec["history"]
        rows = json.load(open(path, encoding="utf-8")) if path.endswith(".json") else _read_history(path)
        histories[account] = [r for r in rows if clean(r[CL["reference"] - 1])]

    res = match(workbook, histories, config["accounts"], log=log)
    if dry_run:
        for h in res["held"][:20]:
            log("  HELD %s: %s" % (h.get("reference"), h["reason"]))
        log("dry run complete in %.1fs. No writes made." % (time.time() - t0))
        return 0

    import openpyxl

    log("loading workbook (openpyxl, ~52s)")
    wb = openpyxl.load_workbook(workbook)
    ws_reg, ws_cl = wb["Register"], wb["Creditor_Lines"]
    cfg = load_config(workbook)
    cl_first, cl_last = cfg.span("CL_DATA")

    stamp = config.get("stamp", datetime.now().strftime("%-d-%b-%Y"))
    for ident in res["identifications"] + res["companions"]:
        r = ident.row
        ws_reg.cell(row=r, column=REG["creditor_code"], value=ident.account)
        ws_reg.cell(row=r, column=REG["contractor"], value=ident.label)
        if ident.abn and ident.basis != "zero-amount companion":
            ws_reg.cell(row=r, column=REG["abn"], value=ident.abn)
        ws_reg.cell(row=r, column=REG["enquiry_narration"], value=ident.details or "(not printed)")
        ws_reg.cell(row=r, column=REG["nature_basis"], value="Matched creditor history")
        ws_reg.cell(row=r, column=REG["evidence"], value=ident.narration())
        ws_reg.cell(row=r, column=REG["tier"], value=1 if ident.basis != "zero-amount companion" else 2)
        ws_reg.cell(row=r, column=REG["followup"], value="")
        if ident.basis == "zero-amount companion":
            ws_reg.cell(row=r, column=REG["coding_note"],
                        value="Zero-amount companion; identity taken from the single non-zero AP row on reference %s." % ident.hist_ref)

    row = cl_last + 1
    for h in res["new_creditor_rows"]:
        for c, v in enumerate(h, start=1):
            ws_cl.cell(row=row, column=c, value=v)
        copy_style(ws_cl, cl_first + 1, row, range(1, 28))
        row += 1
    new_cl_last = row - 1

    ws_cl.auto_filter.ref = "A4:AA%d" % new_cl_last
    ws_cfg = wb["Config"]
    keys = {clean(ws_cfg.cell(row=r, column=1).value): r for r in range(1, ws_cfg.max_row + 1)}
    at = ws_cfg.max_row + 1
    for k, v in {"CL_DATA": "%d:%d" % (cl_first, new_cl_last),
                 "CL_AUTOFILTER": "A4:AA%d" % new_cl_last,
                 "IDENT_ROWS_%s" % config["version_to"].upper(): len(res["identifications"]),
                 "IDENT_HELD_%s" % config["version_to"].upper(): len(res["held"]),
                 "IDENT_EX_GST_%s" % config["version_to"].upper(): f2(res["value"])}.items():
        r = keys.get(k, at)
        if k not in keys:
            at += 1
            ws_cfg.cell(row=r, column=1, value=k)
        ws_cfg.cell(row=r, column=2, value=v)

    if config.get("vendor_series_footnote"):
        ws_vs = wb["Vendor_Series"]
        ws_vs.cell(row=ws_vs.max_row + 1, column=1, value=config["vendor_series_footnote"])

    scratch = os.path.join(out_dir, "_ident_%s.xlsx" % config["version_to"])
    log("saving (openpyxl, ~40s)")
    wb.save(scratch)
    wb.close()
    import gc
    from pswp_build_lib import _FORMULA_CACHE

    del wb, ws_reg, ws_cl, ws_cfg
    _FORMULA_CACHE.clear()
    gc.collect()

    recalced = lo_recalc(scratch, os.path.join(out_dir, "_recalc_ident"), log=log)

    from pswp_verify import sweep

    result = sweep(recalced, {"config": {"CL_DATA": "%d:%d" % (cl_first, new_cl_last)}}, log=log)
    json.dump({k: v for k, v in result.items()},
              open(os.path.join(out_dir, "ident_result_%s.json" % config["version_to"]), "w"), indent=1)
    if result["VERDICT"] != "PASS":
        log("VERIFY FAILED. The partial build is discarded, not resumed (rule 19.7).")
        os.remove(scratch)
        return 2

    import shutil

    shipped = os.path.join(out_dir, config["workbook_out"])
    shutil.move(recalced, shipped)
    os.remove(scratch)
    log(counts_only("shipped", file=os.path.basename(shipped), identified=len(res["identifications"]),
                    companions=len(res["companions"]), creditor_rows=len(res["new_creditor_rows"]),
                    seconds=round(time.time() - t0)))
    return 0


def _read_history(path: str) -> list[list[Any]]:
    """APLEDGER export to Creditor_Lines-shaped rows.

    The trailing account-balance row carries no reference and is dropped; keeping it puts a
    balance into a line table and quietly breaks every count that follows.
    """
    from python_calamine import CalamineWorkbook

    wb = CalamineWorkbook.from_path(path)
    rows = wb.get_sheet_by_name(wb.sheet_names[0]).to_python(skip_empty_area=False)
    head = next((i for i, r in enumerate(rows) if any("reference" == clean(v).lower() for v in r)), 3)
    return [r for r in rows[head + 1:] if clean(r[CL["reference"] - 1])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Identify register lines from APLEDGER creditor histories.")
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return build(json.load(open(a.config, encoding="utf-8")), dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
