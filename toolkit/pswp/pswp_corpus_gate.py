#!/usr/bin/env python3
"""pswp_corpus_gate.py, v10 (18-Sep-2026)

Machine gate for a PSWP extraction corpus produced under PSWP_Extraction_Prompt_v7.md (v7.6).
Runs every pathology in section 13.1 that is computable from the corpus alone (P1 to P17), applies
the 13.0 gate truth table, and prints the verdict. Read-only: it never edits a corpus.

Usage:  python3 pswp_corpus_gate.py corpus_<batch_id>.json [--json]
Exit:   0 GREEN, 1 AMBER, 2 RED, 3 unreadable corpus.

It does not, and cannot, check what is not in the corpus: verbatim fidelity against the
PDF, whether a band matches the printed page, or whether a NARRATIVE row outside the
residue window carries money. Those stay with the extractor and the build session.
"""
import json, re, sys
from decimal import Decimal, ROUND_HALF_UP

LINE_TYPES = {"PRICED","ATTACHMENT","NARRATIVE","TABLE_HEADER","TOTALS","FOOTER","TERMS","BLANK",
              "PAYMENT_ADVICE","OCR_DUPLICATE","IMAGE_TEXT","ANNOTATION","DUPLICATE_COPY"}
# An ATTACHMENT row prints an amount and is scoped to a DIFFERENT document (prompt v7.1 section 9,
# register rule 16d), so it carries money legitimately and stays out of the tie. Every other
# non-PRICED type carrying money is P2.
AMOUNT_BEARING = {"PRICED", "ATTACHMENT"}
LCC_ABN_DIGITS = "21627796435"


# ---------------------------------------------------------------------------------------------------------
# Which checks apply to which prompt version.
#
# A RED verdict stops carrying information the moment it fires on a field that did not exist when the corpus
# was extracted. Run unscoped, 31 of the 34 corpora in this repository read RED, almost all of them on P11 and
# P12 alone, because NO corpus predating v7 carries bands_calibrated_on or residue_rows: neither field is in
# the v5 or the v6 prompt. Those are a schema gap and say nothing about capture quality, yet at the gate they
# are indistinguishable from a real failure.
#
# So every check is tagged with the version that introduced it and is skipped on an older corpus, and the
# report says which set it applied. What each version actually required, read off the prompts themselves:
#   v5   no P11 and no P12: neither existed.
#   v6   P11 is bands ABSENT. P12 is the residue NON-EMPTY, or a rung 1 entry with no rows. P1 to P13.
#   v7   P11 gains the calibration limb, P12 gains "residue_rows absent", P14 and P15 arrive.
#   v7.2 P16, P17, and P1 amended to fire whatever subtotal is recorded.
#   v7.3 P1 exempted where the document carries duplicate_of. A relaxation, so it applies to every version.
# Scoped on the FIELD a check needs, not on the version that introduced the check. Scoping by version alone is
# a loophole: a corpus declaring v6 would escape P14, P15, P16 and P17, none of which needs a field that v6
# lacks, so an extraction could dodge four checks by understating its own version. A check is skipped only
# where the corpus could not have carried the evidence it reads.
#
#   bands_calibrated_on   v7   -> the P11 calibration limb only
#   residue_rows (key)    v7   -> the P12 "absent" limb only; a NON-EMPTY residue is v6
#   bands                 v6   -> P11 proper
#   header_sources        v6   but the ROW CONVENTION it cites is v7 (9.1: line_no, 1-based within its page),
#                              and every v6 corpus here writes "row": 0 as a placeholder, so P17 is v7
#   doc_kind              v5   -> P14, and the P1 doc-kind guard
#   evidence_stem         v5   -> P15
#   printed_gst/subtotal  v5   -> P16
#
# P1's v7.2 amendment and P16's sign test read fields every version has, so they apply to every corpus: a
# document that parsed nothing was a parse failure under v5 too, whatever the prompt then said.
NEEDS_FIELD_FROM = {'P11_calibrated': 'v7', 'P12_absent': 'v7', 'P11': 'v6', 'P12': 'v6', 'P17': 'v7'}


def corpus_version(man):
    """The prompt version the corpus was extracted under, as the manifest records it. The field is free text
    here ('v6', 'v5 (raw-text fallback)', 'PSWP Extraction Prompt v5'), so take the first version token."""
    raw = str(man.get('prompt_version') or '')
    m = re.search(r'v(\d+(?:\.\d+)?)', raw)
    return f'v{m.group(1)}' if m else 'v7.3'      # unstated means current, which is the strict reading


def _vkey(v):
    parts = str(v).lstrip('v').split('.')
    return tuple(int(x) for x in (parts + ['0'])[:2])


def applies(check, version):
    """True unless the corpus predates the FIELD this check reads."""
    need = NEEDS_FIELD_FROM.get(check)
    return True if need is None else _vkey(version) >= _vkey(need)


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
    ver = corpus_version(man)
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

    stems, refs, covered, dup_of = {}, {}, {}, {}
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

        # P1 (amended v7.2): zero PRICED lines on an invoice, WHATEVER subtotal is recorded. Requiring a
        # non-zero recorded subtotal let a document disarm the check by recording zero: Woodmans 6431345 on
        # Binder1666 parsed nothing at all, recorded subtotal 0.00 and total 39.99 (the first line's unit
        # price) against a printed GST Ex Total of $268.00, and P1 stayed silent.
        # A repeated copy of an invoice inside the binder carries duplicate_of, every row is typed
        # DUPLICATE_COPY and its arithmetic fields are null by 4.0 rung 2, so zero PRICED lines is correct
        # for it and not a parse failure. Without this the amended P1 returns a sound corpus: on
        # Pages_from_Binder1 it fired on five documents, all five of them duplicate copies.
        if not priced and doc.get("doc_kind") in (None, "TAX_INVOICE", "CREDIT_NOTE") and not doc.get("duplicate_of"):
            flag("P1", ref, pr[0], f"zero PRICED lines (recorded subtotal {d(doc.get('printed_subtotal_ex_gst'))})")

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

        # P16 (v7.2): where GST prints, it must be a tenth of the subtotal, and it must not oppose its sign.
        # My first cut of this guarded on `gst > 0` to skip GST-free supplies. That silently excluded every
        # NEGATIVE GST, which is the exact shape of the defect it was written for: on Binder1666 twenty-nine
        # documents recorded printed_gst as total less subtotal, twenty-eight of them negative (19795 recorded
        # -$1,887.75), and the guard let all twenty-eight through while the report called the corpus one
        # document short. Tolerance is relative, 1% of the GST or 2c whichever is larger, so a supplier
        # computing GST per line rather than on the subtotal is not flagged.
        gst_basis = str(doc.get("gst_basis") or "")
        # A MIXED SUPPLY is not a defect (5.6). Where the document prints a GST amount per line and those line
        # GSTs sum to the printed GST, the header is proved by the lines themselves and the document-level
        # ratio is explained by the mix. Woodmans 6431345 prints $268.00 ex, $22.80 GST and $290.80 inc over
        # seven rows, one of them GST-free, so a tenth of the subtotal is $26.80 and the invoice is correct.
        line_gst = [l.get("gst") for l in lines if l.get("line_type") == "PRICED" and l.get("gst") is not None]
        mixed_ok = bool(line_gst) and hg is not None and \
            abs(sum((d(x) for x in line_gst), Decimal("0.00")) - d(hg)) <= Decimal("0.02")
        if mixed_ok:
            amber.append(f"{ref}: GST is not a tenth of the subtotal and the priced lines explain it "
                         f"(mixed supply, 5.6); the line GSTs sum to the printed GST")
        if not mixed_ok and hs is not None and hg not in (None, "") and d(hg) != 0 and doc.get("doc_kind") in (None, "TAX_INVOICE", "CREDIT_NOTE"):
            expected = (d(hs) / 10).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            g16 = abs(d(hg) - expected)
            tol16 = max(Decimal("0.02"), (abs(d(hg)) * Decimal("0.01")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            if g16 > tol16:
                flag("P16", ref, pr[0], f"printed GST {d(hg)} against a tenth of the subtotal {expected}, out by {g16}")
            if (d(hs) > 0) != (d(hg) > 0) and d(hs) != 0:
                flag("P16", ref, pr[0], f"GST {d(hg)} opposes the sign of the subtotal {d(hs)}")
        if "derive" in gst_basis.lower():
            amber.append(f"{ref}: printed_gst derived, not read off a GST label")

        # P17 (v7.2): every header figure must be printed on the row its header_sources entry cites. A derived
        # GST makes the 5.4 addition check pass by construction whatever the total is, so P10 is blind by
        # design; this is what reads the citation instead of trusting it.
        by_row, f8 = {}, set()
        for field, loc in ((doc.get("header_sources") or {}) if applies("P17", ver) else {}).items():
            if not isinstance(loc, dict):
                continue
            key = (loc.get("page"), loc.get("row"))
            by_row.setdefault(key, []).append(field)
            rec = next((l for l in lines if l.get("page") == key[0] and l.get("line_no") == key[1]), None)
            if rec is None:
                flag("P17", ref, key[0], f"{field} cites row {key[1]} on page {key[0]}, which carries no line record")
                continue
            val = doc.get(field)
            basis = str(doc.get("subtotal_basis") or "") if field == "printed_subtotal_ex_gst" else gst_basis
            if val is not None and "deriv" not in basis.lower():
                printed = rec.get("line_text", "").replace(",", "").replace("$", "")
                if f"{abs(d(val)):.2f}" not in printed:
                    flag("P17", ref, key[0], f"{field} = {d(val)} is not printed on the row it cites (p{key[0]} r{key[1]})")
            if rec.get("line_type") not in ("TOTALS", "TABLE_HEADER"):
                f8.add(f"a header figure cites a row typed {rec.get('line_type')}, not TOTALS")
        for key, fields in by_row.items():
            if len(fields) > 1:
                f8.add("two header figures cite one row")
        if f8:
            amber.append(f"{ref}: F8, " + "; ".join(sorted(f8)))

        # P11 bands present and calibrated.
        if priced:
            items = [t for t in doc.get("table_headers", []) if t.get("is_item_table")] or doc.get("table_headers", [])
            if applies("P11", ver) and (not items or not items[0].get("bands")):
                flag("P11", ref, pr[0], "PRICED lines with no bands recorded")
            elif applies("P11_calibrated", ver) and items and not items[0].get("bands_calibrated_on"):
                flag("P11", ref, pr[0], "bands recorded but never calibrated against a priced row")

        # P12 residue emitted and empty; rung 1 evidenced on OUT.
        if "residue_rows" not in doc:
            if applies("P12_absent", ver):
                flag("P12", ref, pr[0], "residue_rows absent: the 4.5 test cannot be shown to have run")
        elif doc["residue_rows"]:
            if applies("P12", ver):
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
        dup_of[ref] = bool(doc.get("duplicate_of"))
        stem = doc.get("evidence_stem")
        if stem:
            stems.setdefault(stem, []).append(ref)
            if len(stem) > 40:
                amber.append(f"{ref}: evidence_stem is {len(stem)} characters, over the 40 cap")

    for ref, group in refs.items():
        if len(group) > 1 and not any(g.get("duplicate_of") for g in group):
            flag("P7", ref, None, f"{len(group)} documents share this doc_ref, none marked duplicate_of")
    for stem, owners in stems.items():
        # A repeated copy IS the same document, so it shares its original's stem by construction and nothing
        # collides on save. P15 is for two DIFFERENT documents landing on one filename. This is the fourth
        # check to need the same exemption after P1, so 11.4 now states it as a standing rule rather than
        # leaving each check to rediscover it.
        real = [o for o in owners if not dup_of.get(o)]
        if len(real) > 1:
            flag("P15", real[0], None, f"evidence_stem {stem!r} shared by {real}")

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

    # The description layer. Every check above proves amounts, coverage or citation; none of them reads a word.
    # The only verbatim test is the shingle check, and it needs a haystack the capture did not write. Where the
    # binder is not held, prep rebuilds page_text from the corpus's own line_text rows, which makes the check
    # runnable and UNFAILABLE: the haystack becomes the captured text. A corpus can then tie to the cent on
    # every invoice and carry a description the page never printed, and nothing here would know. So the state
    # is reported rather than left inside a helper script.
    # page_text_independent is the machine field and is a boolean; page_text_basis is the sentence that
    # explains it. Sniffing the prose for "rebuilt" read this repository's own honest basis line, which says
    # "not rebuilt from the corpus rows", as a rebuild.
    # The description layer is a SEPARATE AXIS and is reported as a qualifier on the gate line, not as an AMBER
    # trigger. Demoting on it took GREEN off all 35 corpora at once, including the conformance fixture, and a
    # GREEN that nothing can reach carries no more information than a RED that fires on a non-failure: the build
    # acts on the word, and every corpus arrived looking like a partial build with documents held. A corpus that
    # ties to the cent with no pathology and an unverified description layer is a different object from one that
    # stopped mid-binder, and 13.0 must not give them the same word.
    with_text = sum(1 for x in docs if x.get("page_text"))
    indep = man.get("page_text_independent")
    if not with_text:
        desc = ("UNVERIFIED", "no page text retained, so the verbatim check returns UNVERIFIABLE")
    elif indep is False:
        desc = ("UNVERIFIED", "page text was rebuilt from the corpus's own rows, so the verbatim check cannot fail")
    elif indep is True:
        desc = ("VERIFIED", "page text is an independent parse of the source PDF")
    else:
        desc = ("UNSTATED", f"{with_text} document(s) retain page text but page_text_independent is not set")

    if man.get("resume_point"):
        amber.append(f"partial run, resume at {man['resume_point']}")

    gate = "RED" if P else ("AMBER" if amber else "GREEN")
    return {"gate": gate, "description_layer": desc[0], "description_detail": desc[1],
            "declared_gate": man.get("gate"), "prompt_version": ver, "pathologies": P,
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
        q = "" if r["description_layer"] == "VERIFIED" else f"  (description layer {r['description_layer']})"
        print(f"Gate: {r['gate']}{q}")
        if r["declared_gate"] and r["declared_gate"] != r["gate"]:
            print(f"  declared {r['declared_gate']}, computed {r['gate']}, the computed gate stands")
        print(f"  {r['documents']} documents, {r['lines']} line records, checks applied for prompt {r['prompt_version']}")
        for p in r["pathologies"]:
            print(f"  {p['code']}  {p['doc_ref']}  p{p['page']}  {p['detail']}")
        for a in r["amber_reasons"]:
            print(f"  AMBER  {a}")
        if r["description_layer"] != "VERIFIED":
            print(f"  DESCRIPTION LAYER {r['description_layer']}: {r['description_detail']}")
    sys.exit({"GREEN": 0, "AMBER": 1, "RED": 2}[r["gate"]])
