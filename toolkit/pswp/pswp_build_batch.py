"""
pswp_build_batch.py - the rule 20 brief-driven capture build.

Rebuilt 9-Sep-2026 against PS_WP_Transaction_Register_3FY_v125_HANDOVER.xlsx.

A session AUTHORS A BRIEF, not a script (rule 20). The brief carries the batch facts:
which corpora, which register rows, which categories, which ratified check variants, which
rows are held, what goes into Handover, Method, Data_Acquisition and Open_Items. This
driver carries the mechanics, and a mechanic the brief cannot express is added HERE and
shipped (rule 19.1), never written ad hoc in a session.

    python pswp_build_batch.py brief.json --dry-run     every pre-write gate, no writes
    python pswp_build_batch.py brief.json               the full rule 19.7 chain

RULE 19.7, AS AMENDED v11. build -> recalc -> verify -> ship is ONE script that runs the
whole chain unattended. No stage is run by hand, no stage is re-ordered, and a partial run
is DISCARDED and re-run from the top rather than resumed. This module enforces that: the
working file is written to a scratch name and only promoted to the shipped name after a
clean verify. A crashed run leaves no half-built workbook to be tempted by.

WHAT IT WILL NOT DO
  - build from a corpus whose gate is not GREEN (rule 19.2)
  - write column T, or anything that could move the control total (rule 10)
  - upgrade a row to Confirmed on an empty or generic Nature Detail (rule 17 Amendment 1)
  - green-block a zero-amount companion row, or a journal row (rule 17, rule 6)
  - shift a formula that cites a moved block: every such citation is rewritten explicitly
    from the plan, and an unplanned citation ABORTS the build (rule 19.11)
"""

from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pswp_build_lib import (
    D, money, gst_of, ties, f2, fmt, col_letter, read_sheet, read_sheets, clean,
    Config, load_config, lo_recalc, Verifier, scan_citations, InsertPlan, apply_insert,
    copy_style, repoint_defined_name, condense, md5_file, counts_only,
)
from pswp_json_repair import repair_and_gate, rule16_check, captured

# Register column positions (1-indexed). Confirmed against the v125 header row 4.
REG = {
    "linekey": 1, "amount": 20, "nature_cat": 24, "nature_detail": 25, "theme": 26,
    "nature_basis": 27, "evidence": 28, "tier": 29, "attachment": 30, "verdict": 31,
    "coding_note": 32, "status": 33, "followup": 34, "doc_type": 9, "reference": 8,
    "green_first": 88, "green_last": 127,
}
G = {  # green block, 1-indexed absolute columns
    "evid": 88, "vendor": 89, "abn": 90, "acn": 91, "address": 92, "phone": 93,
    "inv_date": 94, "due_date": 95, "po": 96, "contract": 97, "bill_to": 98, "ship_to": 99,
    "req_officer": 100, "req_date": 101, "req_via": 102, "crwo": 103, "pk_printed": 104,
    "pk_norm": 105, "site": 106, "site_contact": 107, "work_desc": 108, "technician": 109,
    "line_count": 110, "line_items": 111, "works": 112, "sub": 113, "gst": 114, "incl": 115,
    "payments": 116, "balance": 117, "payment_details": 118, "terms": 119, "pages": 120,
    "lines_sum": 121, "chk1": 122, "chk2": 123, "chk3": 124, "source_file": 125,
    "captured": 126, "anomalies": 127,
}
NOT_PRINTED = "(not printed)"
BLANK_AS_PRINTED = "(blank as printed)"
VARIANT_TAG = "[check variant]"


# ----------------------------------------------------------------------------------
# Brief
# ----------------------------------------------------------------------------------


class Brief:
    def __init__(self, path: str):
        self.path = path
        self.raw = json.load(open(path, encoding="utf-8"))
        self.dir = os.path.dirname(os.path.abspath(path))

    def __getitem__(self, k):
        return self.raw[k]

    def get(self, k, default=None):
        return self.raw.get(k, default)

    def resolve(self, p: str) -> str:
        return p if os.path.isabs(p) else os.path.join(self.dir, p)

    def doc_facts(self, ref: str) -> dict:
        return self.raw.get("documents", {}).get(ref, {})


# ----------------------------------------------------------------------------------
# Gate failures
# ----------------------------------------------------------------------------------


class GateFailure(Exception):
    pass


class Gates:
    def __init__(self):
        self.failures: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, message: str) -> bool:
        if not ok:
            self.failures.append(message)
        return ok

    def raise_if_failed(self) -> None:
        if self.failures:
            raise GateFailure("%d pre-write gate(s) failed:\n  - %s" % (len(self.failures), "\n  - ".join(self.failures)))


# ----------------------------------------------------------------------------------
# Pre-write gates
# ----------------------------------------------------------------------------------


def load_corpora(brief: Brief) -> list[dict]:
    out = []
    for p in brief["corpora"]:
        out.append(json.load(open(brief.resolve(p), encoding="utf-8")))
    return out


def gate_corpora(brief: Brief, corpora: list[dict], g: Gates) -> list[dict]:
    """G1/G2. A corpus that fails ANY of its own gates is logged, held and not built from."""
    docs: list[dict] = []
    for c in corpora:
        bid = c.get("manifest", {}).get("batch_id", "?")
        res = repair_and_gate(c)  # idempotent on an already-clean corpus
        g.check(res.gate == "GREEN", "corpus %s gates %s, not GREEN (rule 19.2)" % (bid, res.gate))
        for line in rule16_check(c):
            g.check(False, "rule 16 reconciliation, %s: %s" % (bid, line))
        if res.repairs:
            g.notes.append("corpus %s: %d repair(s) applied at gate time; the repaired corpus must be the one shipped" % (bid, len(res.repairs)))
        docs += c.get("documents", [])
    # RULE 12 WITHIN THE BATCH. A binder re-supplied under a later batch carries documents an earlier corpus in this
    # same build already holds, so the same invoice arrives twice. A re-supply is AUDITED, not captured twice: the two
    # copies must agree on the printed money to the cent, and then the first is kept. Copies that disagree are a gate
    # failure, because one of the two extractions is wrong and nothing here can say which.
    seen: dict[str, dict] = {}
    unique: list[dict] = []
    for d in docs:
        ref = str(d.get("doc_ref"))
        prev = seen.get(ref)
        if prev is None:
            seen[ref] = d
            unique.append(d)
            continue
        same = all(ties(prev.get(k), d.get(k), "0.00")
                   for k in ("printed_subtotal_ex_gst", "printed_gst", "printed_total_incl_gst"))
        g.check(same, "%s is supplied by two corpora in this batch and the printed totals differ; one extraction is "
                      "wrong and the batch is held (rule 12)" % ref)
        if same:
            g.notes.append("%s supplied by two corpora in this batch, identical printed totals: audited and captured "
                           "once (rule 12)" % ref)
    return unique


def gate_duplicates(brief: Brief, docs: list[dict], sheets: dict, g: Gates) -> None:
    """G3/G4. Duplicate screening is a GATE, not a courtesy (rule 12).

    md5 every upload against Data_Acquisition, and screen every corpus id, prefix aware,
    against Evidence_Invoices column A. A re-sighting is NOT re-captured.
    """
    da_text = "\n".join(clean(r[0]) for r in sheets["Data_Acquisition"] if r)
    for p in brief["corpora"] + brief.get("source_files", []):
        fp = brief.resolve(p)
        if not os.path.exists(fp):
            continue
        h = md5_file(fp)
        g.check(h not in da_text, "md5 %s (%s) already appears in Data_Acquisition: this upload has been processed" % (h[:12], os.path.basename(fp)))

    existing = {clean(r[0]) for r in sheets["Evidence_Invoices"][4:] if r and clean(r[0])}
    held = set(brief.get("held", []))
    for doc in docs:
        if str(doc["doc_ref"]) in held:
            continue
        evid = evid_for(brief, doc)
        g.check(evid not in existing, "EvID %s already on Evidence_Invoices: a re-sighting is not re-captured (rule 12)" % evid)
        bare = str(doc["doc_ref"])
        collide = [e for e in existing if e.endswith(bare) and len(e) - len(bare) <= 5]
        if collide and evid not in existing:
            g.notes.append("doc_ref %s resembles existing EvID(s) %s; screened as a different id" % (bare, ", ".join(sorted(collide)[:3])))


def gate_match_table(brief: Brief, docs: list[dict], match: dict, sheets: dict, g: Gates) -> dict[str, dict]:
    """G5. One target AP row per document, tied on amount, not already Confirmed."""
    reg = sheets["Register"]
    targets: dict[str, dict] = {}
    flat: dict[str, dict] = {}
    for batch in match.get("batches", {}).values():
        for rec in batch:
            flat[str(rec["doc_ref"])] = rec
    for doc in docs:
        ref = str(doc["doc_ref"])
        if ref in brief.get("held", []):
            continue
        rec = flat.get(ref)
        if not g.check(rec is not None, "no match-table entry for %s" % ref):
            continue
        row = rec.get("target_row")
        if not g.check(rec.get("target_count") == 1 and row, "%s does not resolve to exactly one register row" % ref):
            continue
        r = reg[row - 1]
        variants = brief.doc_facts(ref).get("variants", [])
        amt_ok = ties(r[REG["amount"] - 1], doc["printed_subtotal_ex_gst"], "0.00") or bool(variants)
        g.check(amt_ok, "%s: register row %d holds %s against a printed subtotal of %s and the brief declares no check variant"
                % (ref, row, fmt(r[REG["amount"] - 1]), fmt(doc["printed_subtotal_ex_gst"])))
        # Rule 17 green-blocks AP lines only. A credit note posts as 'Creditor credit
        # note' and is still a sighted printed face, so the BRIEF may declare it document
        # by document. The driver never relaxes the rule on its own: the exception has to
        # be stated, and it is reported as a note so it appears in the session record.
        doc_type = clean(r[REG["doc_type"] - 1])
        allowed = brief.doc_facts(ref).get("doc_type_allowed")
        if doc_type != "PUR Cred Invoice" and allowed == doc_type:
            g.notes.append("%s: register row %d is %r, green-blocked on a declared brief exception" % (ref, row, doc_type))
        else:
            g.check(doc_type == "PUR Cred Invoice",
                    "%s: register row %d is %r, and only AP lines are green-blocked (rule 17). Declare doc_type_allowed in the brief if this is intended."
                    % (ref, row, doc_type))
        g.check(not clean(r[G["evid"] - 1]), "%s: register row %d already carries EvID %r" % (ref, row, clean(r[G["evid"] - 1])))
        g.check(abs(D(r[REG["amount"] - 1])) > Decimal("0.005"),
                "%s: register row %d is a zero-amount companion and is never green-blocked (rule 17)" % (ref, row))
        targets[ref] = {"row": row, "record": rec}
    # ONE DOCUMENT PER ROW. The doc_ref screen above cannot catch a binder re-supplied under a later batch that names
    # the same invoice differently ("INV-8550" against "INV-8550/pages30-32"): two different refs, one register line.
    # Left alone, the second capture overwrites the first's green block and the sighted-line count comes up short by
    # exactly the number of collisions, which is a failed verify with a cause that is hard to see.
    by_row: dict[int, list[str]] = {}
    for ref, t in targets.items():
        by_row.setdefault(t["row"], []).append(ref)
    for row_, refs in sorted(by_row.items()):
        g.check(len(refs) == 1, "register row %d is claimed by %d documents (%s): a row carries one capture (rule 17)"
                % (row_, len(refs), ", ".join(sorted(refs))))
    return targets


def gate_taxonomy(brief: Brief, docs: list[dict], sheets: dict, g: Gates) -> None:
    """G6/G7/G8. Labels written to COUNTIF-keyed columns come from one canonical map.

    COUNTIF is case-insensitive in Excel, so a label that differs only in case still counts
    but reads wrong; a label that differs in substance counts nowhere. Both are caught here
    by requiring an EXACT match against the sheet.
    """
    cats = {clean(r[0]) for r in sheets["Theme_Map"][4:31] if r and clean(r[0])}
    series = {clean(r[0]) for r in sheets["Vendor_Series"][4:] if r and clean(r[0])}
    bp = {clean(r[0]) for r in sheets["Vendor_Boilerplate"][4:] if r and clean(r[0])}
    # A key this build is ADDING is available to this build. The sheet is written at write time, so checking only what
    # is already stored would refuse every vendor the register has not carried before, which is the case this batch is.
    bp |= {clean(it.get("key")) for it in brief.get("vendor_boilerplate", []) if it.get("key")}
    held = set(brief.get("held", []))
    for doc in docs:
        ref = str(doc["doc_ref"])
        if ref in held:
            continue
        f = brief.doc_facts(ref)
        cat = f.get("nature_category")
        g.check(bool(cat), "%s: the brief states no Nature Category" % ref)
        if cat:
            g.check(cat in cats, "%s: Nature Category %r is not in Theme_Map A5:A31 (rule 4)" % (ref, cat))
        detail = (f.get("nature_detail") or "").strip()
        g.check(len(detail) >= 12, "%s: Nature Detail is empty or generic, so the row stays Partial (rule 17 Amendment 1)" % ref)
        label = f.get("series_label")
        if label:
            g.check(label in series, "%s: contractor label %r is not on Vendor_Series (rule 8)" % (ref, label))
        for key in f.get("boilerplate_keys", []):
            g.check(key in bp, "%s: boilerplate key %r is not on Vendor_Boilerplate (rule 17 Amendment 2)" % (ref, key))


def gate_stems(brief: Brief, docs: list[dict], sheets: dict, g: Gates) -> None:
    """G9. Evidence stems, 40 characters, amount never trimmed, unique in and beyond the batch."""
    seen: dict[str, str] = {}
    held = set(brief.get("held", []))
    for doc in docs:
        ref = str(doc["doc_ref"])
        if ref in held:
            continue          # held, so never captured, so it writes no stem
        stem = str(doc.get("evidence_stem") or "")
        amt = "%.2f" % D(doc.get("printed_total_incl_gst") or 0)
        g.check(len(stem) <= 40, "%s: evidence stem is %d characters" % (ref, len(stem)))
        g.check(stem.endswith(amt), "%s: evidence stem does not end in the incl-GST amount %s (section 12 never trims the amount)" % (ref, amt))
        g.check(stem not in seen, "%s: evidence stem collides with %s" % (ref, seen.get(stem)))
        seen[stem] = ref


def gate_positions(brief: Brief, cfg: Config, g: Gates) -> None:
    """G10. Every build states what it believes about the workbook before it writes."""
    pins = brief.get("config_pins", {})
    for k, want in pins.items():
        got = clean(cfg.get(k))
        g.check(got == str(want), "Config %s reads %r, the brief expects %r" % (k, got, str(want)))


# ----------------------------------------------------------------------------------
# Field assembly
# ----------------------------------------------------------------------------------


def evid_for(brief: Brief, doc: dict) -> str:
    prefixes = brief.get("evid_prefixes", {})
    pref = brief.doc_facts(str(doc["doc_ref"])).get("evid_prefix") or prefixes.get(doc.get("supplier"), "")
    return "%s%s" % (pref, doc["doc_ref"])


def printed_or(value: Any, blank_marker: str = NOT_PRINTED) -> Any:
    if value is None:
        return blank_marker
    s = str(value).strip()
    if s == "":
        return BLANK_AS_PRINTED
    return value


def line_items_text(doc: dict) -> str:
    """Verbatim item string for green-block column 111. Never a paraphrase."""
    parts = []
    n = 0
    for l in doc["lines"]:
        if l.get("line_type") != "PRICED":
            continue
        n += 1
        desc = " ".join((l.get("line_text") or "").split())
        qty = l.get("qty")
        unit = l.get("unit_price_ex_gst")
        amt = l.get("line_ex_gst") if l.get("line_ex_gst") is not None else l.get("stated_amt")
        bits = "%s" % desc
        if qty is not None or unit is not None:
            bits += " | %s @ %s" % (qty if qty is not None else "(qty not printed)",
                                    fmt(unit) if unit is not None else "(unit price not printed)")
        bits += " = %s" % fmt(amt)
        parts.append("%d. %s" % (n, bits))
    return " ".join(parts)


def anomalies_text(brief: Brief, doc: dict) -> str:
    f = brief.doc_facts(str(doc["doc_ref"]))
    bits = list(f.get("anomalies", []))
    for finding in doc.get("findings", []):
        # A finding is a {code, detail} record in the corpora this driver was written against and a plain sentence in
        # the branch corpora built later. Both are the document's own recorded finding and both are carried verbatim.
        if isinstance(finding, dict):
            bits.append("Finding %s: %s" % (finding.get("code"), finding.get("detail")))
        else:
            bits.append("Finding: %s" % finding)
    if f.get("variants"):
        bits.append("%s %s" % (VARIANT_TAG, "; ".join(f["variants"])))
    if doc.get("line_amount_basis") == "incl_gst":
        bits.append("%s Check 1 incl-GST basis: the template prints line amounts GST inclusive" % VARIANT_TAG)
    return condense(" ".join(bits))[0] or "No anomalies noted on capture."


# ----------------------------------------------------------------------------------
# Check formulas, standard and ratified variants (Method 11.0)
# ----------------------------------------------------------------------------------


def chk_formulas(row: int, variants: list[str], sibling_rows: list[int] | None = None) -> dict[str, str]:
    dq, di, dj, dk, cj = "DQ%d" % row, "DI%d" % row, "DJ%d" % row, "DK%d" % row, "CJ%d" % row
    c1 = '=IF(%s=%s,"TRUE","FALSE")' % (dq, di)
    c2 = '=IF(ROUND(T%d,2)=%s,"TRUE","FALSE")' % (row, di)
    c3 = '=IF(%s=ROUND(%s*0.1,2),"TRUE","FALSE")' % (dj, di)
    if "check1 inclB" in variants:
        c1 = '=IF(OR(%s=%s,%s=%s),"TRUE","FALSE")' % (dq, di, dq, dk)
    if "check2 tol1c" in variants:
        c2 = '=IF(ROUND(ABS(ROUND(T%d,2)-%s),2)<=0.01,"TRUE","FALSE")' % (row, di)
    if "check2 deriv" in variants:
        c2 = '=IF(OR(ROUND(T%d,2)=%s,ROUND(T%d,2)=ROUND(%s/1.1,2)),"TRUE","FALSE")' % (row, di, row, dk)
    if "check2 split" in variants:
        c2 = ('=IF(ROUND(T%d,2)=ROUND(SUMIFS(EIL_Amount,EIL_Invoice,%s,EIL_LineKey,A%d),2),"TRUE","FALSE")'
              % (row, cj, row))
    if "check2 sumtie" in variants and sibling_rows:
        terms = "+".join("T%d" % r for r in sibling_rows)
        c2 = '=IF(ROUND(%s,2)=%s,"TRUE","FALSE")' % (terms, di)
    if "check3 gstfree" in variants:
        c3 = '=IF(OR(%s=ROUND(%s*0.1,2),%s=0),"TRUE","FALSE")' % (dj, di, dj)
    if "check3 tol1cgst" in variants:
        c3 = '=IF(ROUND(ABS(%s-ROUND(%s*0.1,2)),2)<=0.01,"TRUE","FALSE")' % (dj, di)
    if "check3 tol2c" in variants:
        c3 = '=IF(ROUND(ABS(%s-ROUND(%s*0.1,2)),2)<=0.02,"TRUE","FALSE")' % (dj, di)
    return {"lines_sum": '=ROUND(SUMIF(EIL_Invoice,%s,EIL_Amount),2)' % cj, "chk1": c1, "chk2": c2, "chk3": c3}



# ----------------------------------------------------------------------------------
# Reserved-row rewrites (rule 19.11)
# ----------------------------------------------------------------------------------

import re as _re

_REF = _re.compile(
    r"(?:'(?P<q>[^']+)'|(?P<s>[A-Za-z_][A-Za-z0-9_]*))?(?P<bang>!)?"
    r"(?P<dc>\$?)(?P<col>[A-Z]{1,3})(?P<dr>\$?)(?P<row>\d+)(?![\d(])")


def remap_formula(formula: str, own_sheet: str, shifts: dict[str, tuple[int, int]], literals: dict[str, str]) -> str:
    """Rewrite one reserved-row formula for blocks that grew.

    `shifts` maps SHEET NAME to (insert_at, rows_added). A row reference moves only when
    it points at a sheet that actually moved: an unqualified reference belongs to
    `own_sheet`, and a qualified one to the sheet it names.

    This is the fix for the defect the first v126 candidate shipped: a sheet-blind remap
    turned `Register!$T$31366`, the control total cell, into `Register!$T$31414`, so the
    control-total check read FALSE on a build that had not touched the register total at
    all. Rule 19.11 asks for an explicit rewrite; an explicit rewrite still has to know
    which sheet each reference is on.
    """
    # In 'Register!$DW$5:$DW$31364' the SECOND endpoint carries no sheet prefix but is
    # still on Register. Treating it as local was the defect that stretched two
    # Evidence_Invoices controls 48 rows past the register data block: the counts stayed
    # right, so nothing failed, and only the bounds audit saw it.
    inherited: dict[int, str] = {}
    for rm in _re.finditer(
            r"(?:'(?P<q>[^']+)'|(?P<s>[A-Za-z_][A-Za-z0-9_]*))!\$?[A-Z]{1,3}\$?\d+\s*:\s*(?P<pos>)",
            formula):
        inherited[rm.end("pos")] = rm.group("q") or rm.group("s")

    def sub(m):
        sheet = m.group("q") or m.group("s")
        prefix = ""
        if m.group("bang"):
            prefix = ("'%s'" % m.group("q") if m.group("q") else m.group("s")) + "!"
        target = sheet if m.group("bang") else inherited.get(m.start(), own_sheet)
        r = int(m.group("row"))
        if target in shifts:
            at, n = shifts[target]
            if r >= at:
                r += n
        return "%s%s%s%s%s%d" % (prefix, m.group("dc"), m.group("col"), m.group("dr"), "", r)

    out = _REF.sub(sub, formula)
    for old, new in literals.items():
        out = _re.sub(r"(?<![\d.])%s(?![\d.])" % _re.escape(old), new, out)
    return out


def capture_reserved(ws, rows: range, cols: range) -> dict[tuple[int, int], str]:
    """Snapshot the formulas of a reserved block BEFORE it is moved."""
    out = {}
    for r in rows:
        for c in cols:
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and v.startswith("="):
                out[(r, c)] = v
    return out


# ----------------------------------------------------------------------------------
# The build
# ----------------------------------------------------------------------------------


def build(brief: Brief, dry_run: bool = False, log=print) -> int:
    t0 = time.time()
    wb_in = brief.resolve(brief["workbook_in"])
    out_dir = brief.resolve(brief.get("output_dir", "outputs"))
    os.makedirs(out_dir, exist_ok=True)

    cfg = load_config(wb_in)
    sheets = read_sheets(wb_in, [
        "Register", "Evidence_Invoices", "Evidence_Invoice_Lines", "EIL_Controls",
        "Theme_Map", "Vendor_Series", "Vendor_Boilerplate", "Data_Acquisition", "Config", "Controls",
    ])
    corpora = load_corpora(brief)
    match = json.load(open(brief.resolve(brief["match_table"]), encoding="utf-8"))

    g = Gates()
    docs = gate_corpora(brief, corpora, g)
    gate_duplicates(brief, docs, sheets, g)
    targets = gate_match_table(brief, docs, match, sheets, g)
    gate_taxonomy(brief, docs, sheets, g)
    gate_stems(brief, docs, sheets, g)
    gate_positions(brief, cfg, g)

    ei_first, ei_last = cfg.span("EI_DATA")
    eil_first, eil_last = cfg.span("EIL_DATA")
    eic_first, eic_last = cfg.span("EIL_CONTROLS_SHEET") if "EIL_CONTROLS_SHEET" in cfg else (5, 3766)
    ei_totals = cfg.int_("EI_TOTALS_ROW")
    ei_ctrl_first, ei_ctrl_last = cfg.span("EI_CONTROL_ROWS")
    control_total = cfg.num("CONTROL_TOTAL")
    sighted = cfg.int_("SIGHTED_COUNT")

    # These counts SIZE THE BUILD: they reserve the rows inserted into Evidence_Invoices and EIL_Controls and they set
    # the RECON_COUNT the verify re-proves. They must therefore count the documents this build actually CAPTURES, not
    # every document in the corpora. A held document writes nothing (rule 19.2), so counting it here would reserve
    # rows nothing fills and would put the reconciliation count out by the number held.
    captured_docs = [d for d in docs if str(d["doc_ref"]) not in set(brief.get("held", []))]
    n_docs = len(captured_docs)
    n_lines = sum(len([l for l in d["lines"] if l.get("line_type") in ("PRICED", "NARRATIVE", "TOTALS", "TABLE_HEADER", "TERMS", "FOOTER", "IMAGE_TEXT", "ANNOTATION")]) for d in captured_docs)
    n_eil = sum(len([l for l in d["lines"] if l.get("line_type") == "PRICED"]) for d in captured_docs)

    log(counts_only("gates", documents=n_docs, targets=len(targets), eil_rows=n_eil, failures=len(g.failures)))
    for n in g.notes:
        log("note: %s" % n)
    if g.failures:
        for f in g.failures:
            log("GATE FAIL: %s" % f)
    if dry_run:
        g.raise_if_failed()
        log("dry run clean in %.1fs. No writes made." % (time.time() - t0))
        return 0
    g.raise_if_failed()

    # ---------------- writes ----------------
    import openpyxl

    log("loading workbook (openpyxl, ~52s)")
    wb = openpyxl.load_workbook(wb_in)

    # rule 19.11 citation sweep BEFORE any move
    plan_ei = InsertPlan("Evidence_Invoices", ei_first, ei_last, n_docs, reserved=[(ei_totals, ei_totals), (ei_ctrl_first, ei_ctrl_last)])
    plan_eic = InsertPlan("EIL_Controls", eic_first, eic_last, n_docs, reserved=[(eic_last + 2, eic_last + 2)])
    def self_row(h) -> bool:
        """A data row citing its own row is untouched by an insert BELOW it."""
        m = re.match(r"([A-Z]+)(\d+)", h.cell)
        return bool(m) and ("%s" % m.group(2)) in h.formula and int(m.group(2)) <= plan_for(h.sheet).data_last

    def plan_for(sheet: str) -> InsertPlan:
        return plan_ei if sheet == "Evidence_Invoices" else plan_eic

    handled_rows = {
        "Evidence_Invoices": set(range(ei_ctrl_first, ei_ctrl_last + 1)) | {ei_totals},
        "EIL_Controls": {eic_last + 2},
    }
    unplanned = []
    for plan in (plan_ei, plan_eic):
        for h in scan_citations(wb, plan.sheet, plan.data_last, plan.data_last + 40):
            if "%s!%s" % (h.sheet, h.cell) in brief.get("citation_rewrites", {}):
                continue
            m = re.match(r"([A-Z]+)(\d+)", h.cell)
            citing_row = int(m.group(2)) if m else 0
            if h.sheet in handled_rows and citing_row in handled_rows[h.sheet]:
                continue  # the driver rewrites this reserved row explicitly, below
            if citing_row <= plan.data_last and self_row(h):
                continue
            if h.sheet == "Controls":
                continue  # rewritten from the control map at the end of the build
            unplanned.append(h)
    if unplanned:
        raise GateFailure(
            "rule 19.11: %d formula(s) cite a block this build moves and are not in the rewrite plan:\n  %s"
            % (len(unplanned), "\n  ".join("%s!%s %s" % (h.sheet, h.cell, h.formula[:90]) for h in unplanned[:12]))
        )

    ws_ei = wb["Evidence_Invoices"]
    ws_eil = wb["Evidence_Invoice_Lines"]
    ws_eic = wb["EIL_Controls"]
    ws_reg = wb["Register"]

    reserved_ei = capture_reserved(ws_ei, range(ei_totals, ei_ctrl_last + 1), range(1, 33))
    reserved_eic = capture_reserved(ws_eic, range(eic_last + 1, eic_last + 4), range(1, 6))

    apply_insert(ws_ei, plan_ei, style_row=ei_last, cols=32)
    apply_insert(ws_eic, plan_eic, style_row=eic_last, cols=5)

    stamp = brief.get("capture_stamp") or datetime.now(timezone.utc).strftime("%-d-%b-%Y")
    batch_label = brief.get("batch_label", brief["batch_id"])

    ei_row = ei_last + 1
    eil_row = eil_last + 1
    eic_row = eic_last + 1
    written_reg: list[int] = []
    eil_index: dict[str, list[int]] = {}

    held_refs = set(brief.get("held", []))
    for doc in docs:
        ref = str(doc["doc_ref"])
        if ref in held_refs:
            # A held document is not part-built from (rule 19.2). It previously reached this loop and was written to
            # Evidence_Invoices and Evidence_Invoice_Lines while its register row got no green block, which is the
            # half-capture the rule exists to refuse: evidence rows with nothing on the register citing them.
            continue
        evid = evid_for(brief, doc)
        f = brief.doc_facts(ref)
        tgt = targets.get(ref)
        basis_incl = doc.get("line_amount_basis") == "incl_gst"

        # --- Evidence_Invoice_Lines, one row per printed line, zero-amount rows included
        n = 0
        for l in doc["lines"]:
            if l.get("line_type") != "PRICED":
                continue
            n += 1
            amt = l.get("line_ex_gst") if l.get("line_ex_gst") is not None else l.get("stated_amt")
            vals = [
                evid, n, " ".join((l.get("line_text") or "").split()),
                l.get("qty"), l.get("unit_price_ex_gst"),
                l.get("gst") if l.get("gst") is not None else ("10%" if not basis_incl else "(incl)"),
                f2(amt),
                (l.get("note") or "") and "" or NOT_PRINTED,
                "", (tgt["record"]["target_linekey"] if tgt else ""),
                l.get("note") or ("amounts print GST inclusive on this template" if basis_incl else ""),
            ]
            for c, v in enumerate(vals, start=1):
                ws_eil.cell(row=eil_row, column=c, value=v)
            copy_style(ws_eil, eil_first + 1, eil_row, range(1, 14))
            eil_index.setdefault(evid, []).append(eil_row)
            eil_row += 1

        # --- Evidence_Invoices header row
        recon = "Lines reconcile to the printed %s to the cent; per-invoice control on EIL_Controls." % (
            "Total Inc GST" if basis_incl else "subtotal")
        ei_vals = {
            1: evid, 2: doc.get("supplier"), 3: doc.get("supplier_abn") or NOT_PRINTED,
            4: doc.get("invoice_date"), 5: f.get("due_date") or NOT_PRINTED,
            6: ref, 7: (doc.get("contract_refs") or [NOT_PRINTED])[0],
            8: f.get("sites") or NOT_PRINTED,
            9: len([l for l in doc["lines"] if l.get("line_type") == "PRICED"]),
            10: f2(doc["printed_subtotal_ex_gst"]), 11: f2(doc["printed_gst"]), 12: f2(doc["printed_total_incl_gst"]),
            13: recon, 14: "Complete on the register line (green block, columns CJ to DW)",
            32: "%s (%s, %s)" % (batch_label, doc.get("source_file"), stamp),
        }
        for c, v in ei_vals.items():
            ws_ei.cell(row=ei_row, column=c, value=v)
        ei_row += 1

        # --- EIL_Controls per-invoice check 1
        ws_eic.cell(row=eic_row, column=1, value=evid)
        ws_eic.cell(row=eic_row, column=2, value='=ROUND(SUMIF(EIL_Invoice,$A%d,EIL_Amount),2)' % eic_row)
        ws_eic.cell(row=eic_row, column=3,
                    value='=INDEX(%s,MATCH($A%d,EI_Invoice,0))' % ("EI_InclGST" if basis_incl else "EI_ExGST", eic_row))
        ws_eic.cell(row=eic_row, column=4, value="Printed total incl GST" if basis_incl else "Ex GST (printed subtotal)")
        ws_eic.cell(row=eic_row, column=5, value='=IF(B%d=C%d,"TRUE","FALSE")' % (eic_row, eic_row))
        eic_row += 1

        # --- Register green block
        if not tgt:
            continue
        r = tgt["row"]
        written_reg.append(r)
        variants = f.get("variants", [])
        fx = chk_formulas(r, variants, f.get("sibling_rows"))
        block = {
            G["evid"]: evid, G["vendor"]: doc.get("supplier"), G["abn"]: doc.get("supplier_abn") or NOT_PRINTED,
            G["acn"]: f.get("acn") or NOT_PRINTED, G["address"]: f.get("address") or NOT_PRINTED,
            G["phone"]: f.get("phone") or NOT_PRINTED, G["inv_date"]: doc.get("invoice_date"),
            G["due_date"]: f.get("due_date") or NOT_PRINTED,
            G["po"]: (doc.get("po_refs") or [NOT_PRINTED])[0],
            G["contract"]: (doc.get("contract_refs") or [NOT_PRINTED])[0],
            G["bill_to"]: f.get("bill_to") or NOT_PRINTED, G["ship_to"]: f.get("ship_to") or NOT_PRINTED,
            G["req_officer"]: f.get("requesting_officer") or NOT_PRINTED,
            G["req_date"]: f.get("request_date") or NOT_PRINTED, G["req_via"]: f.get("request_via") or NOT_PRINTED,
            G["crwo"]: (doc.get("work_orders") or [NOT_PRINTED])[0],
            G["pk_printed"]: "; ".join(doc.get("pk_refs") or []) or NOT_PRINTED,
            G["pk_norm"]: f.get("pk_normalised") or NOT_PRINTED,
            G["site"]: f.get("sites") or NOT_PRINTED, G["site_contact"]: f.get("site_contact") or NOT_PRINTED,
            G["work_desc"]: f.get("work_description") or NOT_PRINTED,
            G["technician"]: f.get("technician") or NOT_PRINTED,
            G["line_count"]: len([l for l in doc["lines"] if l.get("line_type") == "PRICED"]),
            G["line_items"]: condense(line_items_text(doc))[0],
            G["works"]: condense(f.get("works_narrative") or NOT_PRINTED)[0],
            G["sub"]: f2(doc["printed_subtotal_ex_gst"]), G["gst"]: f2(doc["printed_gst"]),
            G["incl"]: f2(doc["printed_total_incl_gst"]),
            G["payments"]: f.get("payments_made") or NOT_PRINTED, G["balance"]: f.get("balance_due") or NOT_PRINTED,
            G["payment_details"]: f.get("payment_details_key") or NOT_PRINTED,
            G["terms"]: f.get("terms_key") or NOT_PRINTED,
            G["pages"]: "pages %s to %s (%s)" % (doc["page_range"][0], doc["page_range"][1], doc.get("source_file")),
            G["lines_sum"]: fx["lines_sum"], G["chk1"]: fx["chk1"], G["chk2"]: fx["chk2"], G["chk3"]: fx["chk3"],
            G["source_file"]: "%s, %s" % (batch_label, doc.get("source_file")),
            G["captured"]: "%s, rule 17 capture (%s)" % (stamp, batch_label),
            G["anomalies"]: anomalies_text(brief, doc),
        }
        for c, v in block.items():
            ws_reg.cell(row=r, column=c, value=v)
        # analysis columns: status and verdict stay independent (rule 17)
        ws_reg.cell(row=r, column=REG["nature_cat"], value=f["nature_category"])
        ws_reg.cell(row=r, column=REG["nature_detail"], value=f["nature_detail"])
        ws_reg.cell(row=r, column=REG["nature_basis"], value="Sighted invoice line")
        ws_reg.cell(row=r, column=REG["evidence"], value="Sighted invoice %s, EIL_Controls row for %s" % (ref, evid))
        ws_reg.cell(row=r, column=REG["tier"], value=1)
        ws_reg.cell(row=r, column=REG["status"], value="Confirmed")
        if f.get("verdict"):
            ws_reg.cell(row=r, column=REG["verdict"], value=f["verdict"])
        if f.get("coding_note"):
            ws_reg.cell(row=r, column=REG["coding_note"], value=f["coding_note"])
        if f.get("series_label"):
            ws_reg.cell(row=r, column=12, value=f["series_label"])
            ws_reg.cell(row=r, column=13, value=doc.get("supplier_abn"))

    # ---------------- explicit rewrites (rule 19.11) ----------------
    new_ei_last = plan_ei.new_last
    new_eic_last = plan_eic.new_last
    new_eil_last = eil_row - 1
    ei_totals_new = plan_ei.shifted(ei_totals)
    ctrl_first_new, ctrl_last_new = plan_ei.shifted(ei_ctrl_first), plan_ei.shifted(ei_ctrl_last)
    eic_summary_new = plan_eic.shifted(eic_last + 2)

    # Every reserved-row formula is rewritten explicitly from the snapshot, with row
    # references remapped by the plan and the changed count literals substituted. The
    # audit of what was rewritten ships with the build.
    literals = {
        str(sighted): str(sighted + len(targets)),
        str(cfg.int_("RECON_COUNT")): str((eic_last - eic_first + 1) + n_docs),
        str(eil_last): str(eil_row - 1),
        str(ei_last): str(plan_ei.new_last),
        str(eic_last): str(plan_eic.new_last),
    }
    rewrite_audit = []
    shifts = {
        "Evidence_Invoices": (plan_ei.insert_at, plan_ei.n_new),
        "EIL_Controls": (plan_eic.insert_at, plan_eic.n_new),
    }
    for (r, c), formula in reserved_ei.items():
        new_r = plan_ei.shifted(r)
        new_f = remap_formula(formula, "Evidence_Invoices", shifts, literals)
        ws_ei.cell(row=new_r, column=c, value=new_f)
        rewrite_audit.append({"sheet": "Evidence_Invoices", "from": "%s%d" % (col_letter(c), r),
                              "to": "%s%d" % (col_letter(c), new_r), "was": formula, "now": new_f})
    for (r, c), formula in reserved_eic.items():
        new_r = plan_eic.shifted(r)
        new_f = remap_formula(formula, "EIL_Controls", shifts, literals)
        ws_eic.cell(row=new_r, column=c, value=new_f)
        rewrite_audit.append({"sheet": "EIL_Controls", "from": "%s%d" % (col_letter(c), r),
                              "to": "%s%d" % (col_letter(c), new_r), "was": formula, "now": new_f})

    for c in ("I", "J", "K", "L"):
        ws_ei["%s%d" % (c, ei_totals_new)] = "=SUM(%s%d:%s%d)" % (c, ei_first, c, new_ei_last)
    ws_eic["B%d" % eic_summary_new] = '=COUNTIF(E%d:E%d,"TRUE")' % (eic_first, new_eic_last)
    ws_eic["C%d" % eic_summary_new] = "=COUNTA(A%d:A%d)" % (eic_first, new_eic_last)
    ws_eic["D%d" % eic_summary_new] = '=IF(B%d=C%d,"TRUE","FALSE")' % (eic_summary_new, eic_summary_new)

    new_sighted = sighted + len(written_reg)
    new_recon = (eic_last - eic_first + 1) + n_docs
    reg_last = cfg.span("REGISTER_DATA")[1]
    ei_rewrites = {
        ctrl_first_new + 0: '=COUNTIF(Register!$AA$5:$AA$%d,"Sighted invoice line")' % reg_last,
        ctrl_first_new + 1: '=COUNTIFS(Register!$AA$5:$AA$%d,"Sighted invoice line",Reg_EvID,"<>")' % reg_last,
        ctrl_first_new + 2: '=IF(AND(C%d=%d,C%d=C%d),"TRUE","FALSE")' % (ctrl_first_new, new_sighted, ctrl_first_new, ctrl_first_new + 1),
        ctrl_first_new + 3: '=IF(SUMPRODUCT(--(Register!$DR$5:$DR$%d="TRUE"))=C%d,"TRUE","FALSE")' % (reg_last, ctrl_first_new),
        ctrl_first_new + 4: '=IF(SUMPRODUCT(--(Register!$DS$5:$DS$%d="TRUE"))=C%d,"TRUE","FALSE")' % (reg_last, ctrl_first_new),
        ctrl_first_new + 5: '=IF(SUMPRODUCT(--(Register!$DT$5:$DT$%d="TRUE"))=C%d,"TRUE","FALSE")' % (reg_last, ctrl_first_new),
        ctrl_first_new + 9: '=IF(SUMPRODUCT(--(EIL_Controls!$E$%d:$E$%d="TRUE"))=%d,"TRUE","FALSE")' % (eic_first, new_eic_last, new_recon),
    }
    for row, formula in ei_rewrites.items():
        ws_ei["C%d" % row] = formula
    gst_allow = D(cfg.get("GSTINC_ALLOWANCE") or 0) + sum(
        (D(d["printed_total_incl_gst"]) - D(d["printed_subtotal_ex_gst"])) for d in docs if d.get("line_amount_basis") == "incl_gst")
    ws_ei["C%d" % (ctrl_first_new + 7)] = (
        '=IF(ROUND(J%d,2)=ROUND(SUM(Evidence_Invoice_Lines!$G$%d:$G$%d)-%s,2),"TRUE","FALSE")'
        % (ei_totals_new, eil_first, new_eil_last, f2(gst_allow)))

    for name, last in (("EI_Invoice", new_ei_last), ("EI_ExGST", new_ei_last), ("EI_InclGST", new_ei_last)):
        try:
            repoint_defined_name(wb, name, last)
        except Exception as exc:  # a missing name is a structural surprise, not a silent pass
            raise GateFailure("defined name %s could not be repointed: %s" % (name, exc))

    # Controls sheet. Two passes, and both are needed.
    # (1) Every Controls formula is repointed through the same sheet-aware remap, because
    #     the group-6 error sweeps cite each sheet from row 1 to its last row and would
    #     otherwise stop sweeping exactly the rows this build just added. Their expected
    #     value stays 0, so only the range moves.
    # (2) The count controls then take their new expected figures.
    ws_ctrl = wb["Controls"]
    for row in range(4, 73):
        for c in (5, 7):
            v = ws_ctrl.cell(row=row, column=c).value
            if isinstance(v, str) and v.startswith("="):
                ws_ctrl.cell(row=row, column=c, value=remap_formula(v, "Controls", shifts, {}))
    for row in range(8, 73):
        what = str(ws_ctrl.cell(row=row, column=3).value or "")
        if "every sighted row TRUE" in what or "carrying an EvID" in what:
            ws_ctrl.cell(row=row, column=6, value=new_sighted)
            ws_ctrl.cell(row=row, column=7, value='=IF(E%d=%d,"TRUE","FALSE")' % (row, new_sighted))
        if "Every invoice reconciles" in what or "Panel row count" in what:
            ws_ctrl.cell(row=row, column=5, value=(
                '=SUMPRODUCT(--(EIL_Controls!$E$%d:$E$%d="TRUE"))' % (eic_first, new_eic_last)
                if "reconciles" in what else '=COUNTA(EIL_Controls!$A$%d:$A$%d)' % (eic_first, new_eic_last)))
            ws_ctrl.cell(row=row, column=6, value=new_recon)
            ws_ctrl.cell(row=row, column=7, value='=IF(E%d=%d,"TRUE","FALSE")' % (row, new_recon))
        if "Evidence_Invoices control block" in what:
            ws_ctrl.cell(row=row, column=5, value='=SUMPRODUCT(--(Evidence_Invoices!$C$%d:$C$%d="TRUE"))' % (ctrl_first_new + 2, ctrl_last_new))

    # Config, Handover, Method, Data_Acquisition, Open_Items
    ws_cfg = wb["Config"]
    updates = {
        "EI_DATA": "%d:%d" % (ei_first, new_ei_last), "EI_TOTALS_ROW": ei_totals_new,
        "EI_CONTROL_ROWS": "%d:%d" % (ctrl_first_new, ctrl_last_new),
        "EIL_DATA": "%d:%d" % (eil_first, new_eil_last), "EIL_END": new_eil_last,
        "EIL_CONTROLS_SHEET": "EIL_Controls, rows %d:%d, summary row %d" % (eic_first, new_eic_last, eic_summary_new),
        "RECON_COUNT": new_recon, "SIGHTED_COUNT": new_sighted,
        "GSTINC_ALLOWANCE": f2(gst_allow),
        "WORKBOOK_VERSION_%s" % brief["version_to"].upper(): brief["version_to"],
    }
    updates.update(brief.get("config_updates", {}))
    existing_keys = {clean(ws_cfg.cell(row=r, column=1).value): r for r in range(1, ws_cfg.max_row + 1)}
    append_at = ws_cfg.max_row + 1
    for k, v in updates.items():
        row = existing_keys.get(k)
        if row is None:
            row, append_at = append_at, append_at + 1
            ws_cfg.cell(row=row, column=1, value=k)
        ws_cfg.cell(row=row, column=2, value=v)

    _append_text(wb["Handover"], brief.get("handover"))
    _append_text(wb["Method"], brief.get("method"))
    _append_text(wb["Data_Acquisition"], brief.get("data_acquisition"))
    _append_open_items(wb["Open_Items"], brief.get("open_items", []))
    _append_boilerplate(wb["Vendor_Boilerplate"], brief.get("vendor_boilerplate", []), log)

    # ---------------- save, recalc, verify, ship ----------------
    json.dump(rewrite_audit, open(os.path.join(out_dir, "rewrite_audit_%s.json" % brief["version_to"]), "w"), indent=1)

    scratch = os.path.join(out_dir, "_building_%s.xlsx" % brief["version_to"])
    log("saving (openpyxl, ~40s)")
    wb.save(scratch)
    wb.close()
    # LibreOffice needs the RAM more than we do. On a 4GB box the recalc is OOM-killed if
    # the openpyxl object graph is still resident, and an OOM-killed recalc looks exactly
    # like a crash with no message.
    import gc
    from pswp_build_lib import _FORMULA_CACHE
    del wb, ws_ei, ws_eil, ws_eic, ws_reg, ws_ctrl, ws_cfg, sheets, reserved_ei, reserved_eic
    _FORMULA_CACHE.clear()
    gc.collect()

    recalc_dir = os.path.join(out_dir, "_recalc")
    recalced = lo_recalc(scratch, recalc_dir, log=log)

    v = verify(recalced, brief, {
        "control_total": control_total, "sighted": new_sighted, "recon": new_recon,
        "register_rows": written_reg, "ei_last": new_ei_last, "eic_last": new_eic_last,
        "ctrl_first": ctrl_first_new, "ctrl_last": ctrl_last_new, "sighted_before": sighted,
    })
    log(v.report())
    if not v.clean_pass:
        log("VERIFY FAILED. The partial build is discarded, not resumed (rule 19.7).")
        os.remove(scratch)
        return 2

    shipped = os.path.join(out_dir, brief["workbook_out"])
    shutil.move(recalced, shipped)
    os.remove(scratch)
    shutil.rmtree(recalc_dir, ignore_errors=True)
    log(counts_only("shipped", file=os.path.basename(shipped), invoices=n_docs, eil_rows=n_eil,
                    register_rows=len(written_reg), seconds=round(time.time() - t0)))
    return 0


def _append_text(ws, text: str | None) -> None:
    if not text:
        return
    ws.cell(row=ws.max_row + 1, column=1, value=condense(text)[0])


def _append_boilerplate(ws, rows: list[dict], log) -> None:
    """Append a vendor's printed payment block and terms, once, and cite it by key (rule 17 Amendment 2).

    A green block cites its boilerplate by key rather than repeating the block on every row. A batch that brings a
    vendor this register has not carried before therefore brings a key this sheet does not have, and a citation to a
    key that is not here is a dangling one. The driver had no way to add a row, so the brief could not express it
    (rule 19.1): the mechanic belongs here and ships with the build rather than being written by hand in a session.
    Existing keys are never rewritten, because the stored text is what earlier captures cite.
    """
    if not rows:
        return
    have = {str(ws.cell(row=r, column=1).value or "").strip() for r in range(5, ws.max_row + 1)}
    row = ws.max_row + 1
    added = 0
    for it in rows:
        key = str(it.get("key") or "").strip()
        if not key or key in have:
            continue
        # Column order follows the SHEET'S OWN DATA, not its header row: every stored row carries the first-sighting
        # invoice id in column 3 and the vendor name in column 4, while the header labels those two the other way
        # round. Writing to the header would put the vendor where 131 existing rows keep the invoice id. The
        # mislabelled header is raised as an open item rather than corrected here, because relabelling a column is a
        # decision about the register, not a step in a capture build.
        for c, val in enumerate([key, it.get("field"), it.get("first_sighting"), it.get("vendor"),
                                 it.get("sightings"), it.get("text")], start=1):
            ws.cell(row=row, column=c, value=val)
        have.add(key)
        row += 1
        added += 1
    log("Vendor_Boilerplate: %d key(s) appended, %d already present" % (added, len(rows) - added))


def _append_open_items(ws, items: list[dict]) -> None:
    if not items:
        return
    last_num = 0
    for r in range(5, ws.max_row + 1):
        v = ws.cell(row=r, column=1).value
        if isinstance(v, (int, float)):
            last_num = max(last_num, int(v))
    row = ws.max_row + 1
    for i, it in enumerate(items, start=1):
        vals = [last_num + i, it.get("fy"), it.get("status", "Open"), it.get("series"),
                it.get("lines"), it.get("amount"), it.get("action")]
        for c, val in enumerate(vals, start=1):
            ws.cell(row=row, column=c, value=val)
        row += 1


# ----------------------------------------------------------------------------------
# Verify (reads the RECALCULATED file, calamine, exact "TRUE")
# ----------------------------------------------------------------------------------


def verify(path: str, brief: Brief, state: dict) -> Verifier:
    v = Verifier()
    s = read_sheets(path, ["Register", "Evidence_Invoices", "EIL_Controls", "Controls", "Config"])
    reg, ei, eic, ctrl = s["Register"], s["Evidence_Invoices"], s["EIL_Controls"], s["Controls"]

    v.true("Controls master verdict", ctrl[3][1])
    v.equals("Controls failing count", ctrl[4][4], 0)

    for r in range(state["ctrl_first"] + 2, state["ctrl_last"] + 1):
        v.true("Evidence_Invoices control row %d" % r, ei[r - 1][2])

    for r in state["register_rows"]:
        row = reg[r - 1]
        v.true("register %d check 1" % r, row[G["chk1"] - 1])
        v.true("register %d check 2" % r, row[G["chk2"] - 1])
        v.true("register %d check 3" % r, row[G["chk3"] - 1])
        v.check = None  # no partial verify: every limb runs

    for r in range(state["eic_last"] - len(state["register_rows"]) + 1, state["eic_last"] + 1):
        v.true("EIL_Controls row %d" % r, eic[r - 1][4])

    total_row = int(D(Config(s["Config"]).get("REGISTER_TOTAL_ROW")))
    v.amount("register control total unchanged", reg[total_row - 1][19], state["control_total"])

    # The v125 recalc trap: a cached-value pass looks exactly like a real one unless a
    # figure the build is SUPPOSED to move is pinned. Sighted count is that figure here.
    v.moved("sighted-line count", state["sighted_before"], ei[state["ctrl_first"] - 1][2])
    for name, want in (brief.get("verify_pins") or {}).items():
        v.equals("brief pin %s" % name, _pin_value(s, name), want)
    return v


def _pin_value(sheets: dict, ref: str) -> Any:
    sheet, cell = ref.split("!")
    col = "".join(ch for ch in cell if ch.isalpha())
    row = int("".join(ch for ch in cell if ch.isdigit()))
    from pswp_build_lib import col_number

    return sheets[sheet][row - 1][col_number(col) - 1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rule 20 brief-driven PS/WP capture build.")
    ap.add_argument("brief")
    ap.add_argument("--dry-run", action="store_true", help="run every pre-write gate and stop")
    a = ap.parse_args(argv)
    brief = Brief(a.brief)
    try:
        return build(brief, dry_run=a.dry_run)
    except GateFailure as exc:
        print("BUILD REFUSED\n%s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
