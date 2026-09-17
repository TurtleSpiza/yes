#!/usr/bin/env python3
"""pswp_corpus_gate.py, v3 (17-Sep-2026)

Machine gate for a PSWP extraction corpus produced under PSWP_Extraction_Prompt_v7.md (v7.1).
Runs every pathology in section 13.1 that is computable from the corpus alone, applies
the 13.0 gate truth table, and prints the verdict. Read-only: it never edits a corpus.

Usage:  python3 pswp_corpus_gate.py corpus_<batch_id>.json [--json]
Exit:   0 GREEN, 1 AMBER, 2 RED, 3 unreadable corpus.

It does not, and cannot, check what is not in the corpus: verbatim fidelity against the
PDF, whether a band matches the printed page, or whether a NARRATIVE row outside the
residue window carries money. Those stay with the extractor and the build session.
"""
import json, sys
from decimal import Decimal, ROUND_HALF_UP

LINE_TYPES = {"PRICED","ATTACHMENT","NARRATIVE","TABLE_HEADER","TOTALS","FOOTER","TERMS","BLANK",
              "PAYMENT_ADVICE","OCR_DUPLICATE","IMAGE_TEXT","ANNOTATION","DUPLICATE_COPY"}
# An ATTACHMENT row prints an amount and is scoped to a DIFFERENT document (prompt v7.1 section 9,
# register rule 16d), so it carries money legitimately and stays out of the tie. Every other
# non-PRICED type carrying money is P2.
AMOUNT_BEARING = {"PRICED", "ATTACHMENT"}
LCC_ABN_DIGITS = "21627796435"

def d(x):
    """Tolerant of a P8 defect so the gate reports it rather than crashing on it."""
    if x is None:
        x = 0
    if isinstance(x, str):
        x = x.replace("$", "").replace(",", "").strip() or "0"
    try:
        return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")

def gap(a, b):
    return abs(d(a) - d(b))

def codes(doc):
    """v7 mandates findings as objects carrying a code (schema, section 9). A corpus written
    under v6 emits them as plain strings, and reading .get on one used to raise AttributeError,
    which the caller reported as 'corpus unreadable' - the one verdict that means a file nobody
    can parse. A non-v7 shape is a finding about the corpus, not a reason to misreport it."""
    out = []
    for f in doc.get("findings", []) or []:
        if isinstance(f, dict):
            out.append(f.get("code"))
        else:
            out.append(None)
    return out

def source_name(entry):
    """Manifests in this repository key the source file as 'name' (v7 conformance, savco_new)
    or as 'file' (attach_1). Both are in use; neither is wrong."""
    if isinstance(entry, dict):
        return entry.get("name") or entry.get("file")
    return entry

def check(path):
    raw = open(path, encoding="utf-8").read()
    corpus = json.loads(raw)
    man = corpus.get("manifest", {})
    docs = corpus.get("documents", [])
    P, amber = [], []

    def flag(code, doc, page, detail):
        P.append({"code": code, "doc_ref": doc, "page": page, "detail": detail})

    # P8: numbers emitted as strings or carrying $ / thousands separators.
    def scan_numeric(node, ref, keys=("line_ex_gst","gst","stated_amt","unit_price_ex_gst",
                                      "printed_subtotal_ex_gst","printed_gst",
                                      "printed_total_incl_gst","captured_ex_gst","amount")):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in keys and isinstance(v, str):
                    flag("P8", ref, None, f"{k} emitted as string {v!r}")
                scan_numeric(v, ref, keys)
        elif isinstance(node, list):
            for v in node:
                scan_numeric(v, ref, keys)

    stems, refs, covered = {}, {}, {}
    for doc in docs:
        ref = doc.get("doc_ref")
        scan_numeric(doc, ref)
        lines = doc.get("lines", [])
        priced = [l for l in lines if l.get("line_type") == "PRICED"]
        pr = doc.get("page_range") or [None, None]

        # P13 closed list, and P2 the 4.4 invariant, both ways.
        for l in lines:
            lt = l.get("line_type")
            if lt not in LINE_TYPES:
                flag("P13", ref, l.get("page"), f"line_type {lt!r} outside the closed list")
            amt = l.get("line_ex_gst") if l.get("line_ex_gst") is not None else l.get("stated_amt")
            if lt == "PRICED" and amt is None:
                flag("P2", ref, l.get("page"), f"PRICED row {l.get('line_no')} carries no amount")
            if lt not in AMOUNT_BEARING and amt is not None and lt in LINE_TYPES:
                flag("P2", ref, l.get("page"), f"{lt} row {l.get('line_no')} carries an amount")

        # P1 nothing parsed.
        if d(doc.get("printed_subtotal_ex_gst")) != 0 and not priced:
            flag("P1", ref, pr[0], "printed subtotal non-zero and zero PRICED lines")

        # P3 every page in range carries a record. Page numbers are scoped to the document's own
        # source file: a binder that arrives as twenty-five one-page PDFs has twenty-five page 1s.
        if all(isinstance(x, int) for x in pr):
            pages_in_range = set(range(pr[0], pr[1] + 1))
            seen = {l.get("page") for l in lines}
            covered.setdefault(doc.get("source_file"), set()).update(seen)
            missing = sorted(pages_in_range - seen)
            if missing and not man.get("resume_point"):
                flag("P3", ref, missing[0], f"pages with no line record: {missing}")

        # P4 supplier ABN is not LCC's.
        abn = "".join(ch for ch in str(doc.get("supplier_abn") or "") if ch.isdigit())
        if abn == LCC_ABN_DIGITS:
            flag("P4", ref, pr[0], "supplier_abn is the LCC bill-to ABN")

        # P5 total missing.
        if doc.get("printed_total_incl_gst") in (None, "") and doc.get("doc_kind") != "CORRESPONDENCE":
            flag("P5", ref, pr[0], "printed_total_incl_gst is null")

        # P10 header block adds up.
        hs, hg, ht = doc.get("printed_subtotal_ex_gst"), doc.get("printed_gst"), doc.get("printed_total_incl_gst")
        if None not in (hs, hg, ht):
            g = gap(d(hs) + d(hg), ht)
            explained = "F1" in codes(doc)
            if g > Decimal("0.02") and not explained:
                flag("P10", ref, pr[0], f"subtotal + GST less total = {g}, no F1 explaining it")
            elif g > Decimal("0.02"):
                amber.append(f"{ref}: header block out by {g}, recorded as F1")

        # P11 bands present and calibrated.
        if priced:
            items = [t for t in doc.get("table_headers", []) if t.get("is_item_table")] or doc.get("table_headers", [])
            if not items or not items[0].get("bands"):
                flag("P11", ref, pr[0], "PRICED lines with no bands recorded")
            elif not items[0].get("bands_calibrated_on"):
                flag("P11", ref, pr[0], "bands recorded but never calibrated against a priced row")

        # P12 residue emitted and empty; rung 1 evidenced on OUT.
        if "residue_rows" not in doc:
            flag("P12", ref, pr[0], "residue_rows absent: the 4.5 test cannot be shown to have run")
        elif doc["residue_rows"]:
            flag("P12", ref, pr[0], f"residue non-empty: {doc['residue_rows']}")
        if doc.get("self_tie") == "OUT":
            r1 = [r for r in doc.get("retry_log", []) if r.get("rung") == 1]
            if not r1 or "rows" not in r1[0]:
                flag("P12", ref, pr[0], "OUT document with no rung 1 rows list")
            if len(doc.get("retry_log", [])) < 4:
                flag("P12", ref, pr[0], "OUT document with fewer than four rungs recorded")
            amber.append(f"{ref}: at OUT after the ladder")

        # P14 credit-note sign.
        if doc.get("doc_kind") == "CREDIT_NOTE" and d(ht) > 0:
            flag("P14", ref, pr[0], "CREDIT_NOTE with a positive printed total")
        if doc.get("doc_kind") == "TAX_INVOICE" and ht is not None and d(ht) < 0:
            flag("P14", ref, pr[0], "TAX_INVOICE with a negative printed total")

        # Tie, at 1c, with the 2c band going AMBER (6.0).
        # Rule 16d: an ATTACHMENT row is excluded from the tie by construction, since the tie sums
        # PRICED only. Recorded so the report can show the exclusion rather than leave it implied.
        att = [l for l in lines if l.get("line_type") == "ATTACHMENT"]
        if att:
            amber.append(f"{ref}: {len(att)} ATTACHMENT row(s) excluded from the tie (rule 16d); "
                         f"basis must be stated in notes")

        target = ht if doc.get("tie_basis") == "incl_gst" else hs
        if priced and target is not None:
            captured = sum((d(l.get("line_ex_gst") if l.get("line_ex_gst") is not None else l.get("stated_amt"))
                            for l in priced), Decimal("0.00"))
            g = gap(captured, target)
            if g > Decimal("0.02") and doc.get("self_tie") != "OUT":
                flag("P12", ref, pr[0], f"captured {captured} against target {d(target)}, gap {g}, but self_tie is TIE")
            elif Decimal("0.01") < g <= Decimal("0.02"):
                amber.append(f"{ref}: tie in the 1c to 2c band, gap {g}")
                if "F7" not in codes(doc):
                    amber.append(f"{ref}: 2c tie not recorded as F7")

        # A finding that carries no code cannot satisfy P10's F1 escape or 6.0's F7 record.
        if any(not isinstance(f, dict) for f in doc.get("findings", []) or []):
            amber.append(f"{ref}: findings emitted as plain strings, not the v7 {{code, detail, amount}} objects")

        # P7 doc_ref uniqueness, P15 stem uniqueness.
        refs.setdefault(ref, []).append(doc)
        stem = doc.get("evidence_stem")
        if stem:
            stems.setdefault(stem, []).append(ref)
            if len(stem) > 40:
                amber.append(f"{ref}: evidence_stem is {len(stem)} characters, over the 40 cap")

    for ref, group in refs.items():
        if len(group) > 1 and not any(g.get("duplicate_of") for g in group):
            flag("P7", ref, None, f"{len(group)} documents share this doc_ref, none marked duplicate_of")
    for stem, owners in stems.items():
        if len(owners) > 1:
            flag("P15", owners[0], None, f"evidence_stem {stem!r} shared by {owners}")

    # P9 page coverage, per source file. Summing every source file's page count and then
    # expecting pages 1..total to be covered assumes the whole binder shares one page space.
    # It does not: each PDF is numbered from 1, so on a 25-file binder that test reported
    # pages 2 to 25 missing on a corpus that in fact covered every page of every file.
    if not man.get("resume_point"):
        for entry in man.get("source_files", []):
            name = source_name(entry)
            pages = entry.get("pages", 0) if isinstance(entry, dict) else 0
            if not pages:
                continue
            seen = covered.get(name, set())
            if not seen and None in covered:
                seen = covered[None]  # documents that never named a source_file
            missing = sorted(set(range(1, pages + 1)) - seen)
            if missing:
                flag("P9", None, missing[0], f"{name}: pages in no document range: {missing}")

    # P6 OCR, runtime A only.
    if man.get("runtime") == "A" and man.get("ocr_pages_outstanding", 0) > 0:
        flag("P6", None, None, f"ocr_pages_outstanding = {man['ocr_pages_outstanding']}")

    # Runtime B fidelity honesty (10), AMBER not RED.
    if man.get("runtime") == "B" and man.get("shingle_checks_run", 0) == 0 and docs:
        amber.append("runtime B with shingle_checks_run = 0: state it as an omission in the report")

    if man.get("resume_point"):
        amber.append(f"partial run, resume at {man['resume_point']}")

    gate = "RED" if P else ("AMBER" if amber else "GREEN")
    return {"gate": gate, "declared_gate": man.get("gate"), "pathologies": P,
            "amber_reasons": sorted(set(amber)), "documents": len(docs),
            "lines": sum(len(x.get("lines", [])) for x in docs)}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(3)
    try:
        r = check(args[0])
    except Exception as e:
        print(f"RED, corpus unreadable: {type(e).__name__}: {e}"); sys.exit(3)
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1))
    else:
        print(f"Gate: {r['gate']}")
        if r["declared_gate"] and r["declared_gate"] != r["gate"]:
            print(f"  declared {r['declared_gate']}, computed {r['gate']}, the computed gate stands")
        print(f"  {r['documents']} documents, {r['lines']} line records")
        for p in r["pathologies"]:
            print(f"  {p['code']}  {p['doc_ref']}  p{p['page']}  {p['detail']}")
        for a in r["amber_reasons"]:
            print(f"  AMBER  {a}")
    sys.exit({"GREEN": 0, "AMBER": 1, "RED": 2}[r["gate"]])
