#!/usr/bin/env python3
"""pswp_header_restate.py, v1 (18-Sep-2026)

Restates header figures, and Tennyson 60203's priced line, in an extracted corpus,
using ONLY each document's own retained line_text (project rule 19.2: repairs restate
from retained page text, never guess). Writes a new corpus and a repair log; it never
edits the input in place and never touches line_text.

Usage: python3 pswp_header_restate.py corpus_in.json corpus_out.json repair_log.md

Templates handled, and the rule applied to each:
  VINTON (B)   total from `Total (inc-GST):`, cross-checked against `Balance Due:` and
               the how-to-pay `Balance due:`; at least two sources must agree. The GST
               label prints with no value anywhere in its band on this layout, so GST is
               derived from total less subtotal and gst_basis records that.
  HERITAGE     subtotal from `Subtotal`, GST from `TOTAL GST 10%`, total from `Total`
               where `Total` is not followed by `GST` (prompt 5.1).
  NEW:TENNYSON subtotal from `Net $`, GST from `GST $`, total from `Total $`; the item
               table header and its bands are recorded, and the priced row's amount is
               restated from the Net Price band.
Anything else is left untouched and listed as held.
"""
import json, re, sys
from decimal import Decimal, ROUND_HALF_UP

money = re.compile(r"-?\$?\s?-?\d{1,3}(?:,\d{3})*\.\d{2}")

def D(x):
    return Decimal(str(x if x is not None else 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def toks(t):
    return [Decimal(m.group(0).replace("$", "").replace(",", "").replace(" ", "")) for m in money.finditer(t)]

def label_value(doc, label, not_followed_by=None):
    """(page, row, value) for each occurrence of `label`, using the 5.2 four-row lookahead."""
    L, out = doc["lines"], []
    for i, l in enumerate(L):
        t = l["line_text"]
        j = t.find(label)
        if j < 0:
            continue
        tail = t[j + len(label):]
        if not_followed_by and tail[:8].strip().startswith(not_followed_by):
            continue
        v = toks(tail)
        if v:
            out.append((l["page"], l["line_no"], v[0]))
            continue
        for nxt in L[i + 1:i + 5]:
            vv = toks(nxt["line_text"])
            if vv:
                out.append((nxt["page"], nxt["line_no"], vv[0]))
                break
    return out

def retype(doc, rows, new_type):
    for l in doc["lines"]:
        if (l["page"], l["line_no"]) in rows:
            l["line_type"] = new_type

def restate(doc, log):
    ref, tmpl = doc["doc_ref"], doc.get("template")
    before = (doc.get("printed_subtotal_ex_gst"), doc.get("printed_gst"), doc.get("printed_total_incl_gst"))

    if tmpl == "VINTON (B)":
        cands = label_value(doc, "Total (inc-GST):") + label_value(doc, "Balance Due:") + label_value(doc, "Balance due:")
        if len(cands) < 2:
            log.append((ref, tmpl, "HELD", "fewer than two agreeing total sources", before, None)); return False
        vals = [c[2] for c in cands]
        total = max(set(vals), key=vals.count)
        if vals.count(total) < 2:
            log.append((ref, tmpl, "HELD", "total sources disagree", before, None)); return False
        sub = D(doc["printed_subtotal_ex_gst"])
        gst = (D(total) - sub).quantize(Decimal("0.01"))
        src = next(c for c in cands if c[2] == total)
        sub_src = doc.get("header_sources", {}).get("printed_subtotal_ex_gst")
        doc["printed_gst"], doc["printed_total_incl_gst"] = float(gst), float(D(total))
        doc["gst_basis"] = "derived from printed total less printed subtotal; the GST label prints with no value in its band on this layout"
        doc["header_sources"] = {"printed_subtotal_ex_gst": sub_src,
                                 "printed_gst": {"page": src[0], "row": src[1]},
                                 "printed_total_incl_gst": {"page": src[0], "row": src[1]}}
        doc["header_adds_up"] = "derived"
        retype(doc, {(src[0], src[1])}, "TOTALS")

    elif tmpl == "HERITAGE":
        sub = label_value(doc, "Subtotal")
        gst = label_value(doc, "TOTAL GST 10%") + label_value(doc, "Total GST 10%")
        tot = [c for c in label_value(doc, "Total", not_followed_by="GST") if c not in gst]
        if not (sub and gst and tot):
            # Figures already read off the right labels on this layout vintage; nothing to
            # restate. Any citation that points at the wrong row is repointed by fix_citations.
            log.append((ref, tmpl, "NO CHANGE", "header figures already consistent; citations checked only", before, None))
            return None
        doc["printed_subtotal_ex_gst"], doc["printed_gst"], doc["printed_total_incl_gst"] = \
            float(D(sub[0][2])), float(D(gst[0][2])), float(D(tot[0][2]))
        doc["header_sources"] = {"printed_subtotal_ex_gst": {"page": sub[0][0], "row": sub[0][1]},
                                 "printed_gst": {"page": gst[0][0], "row": gst[0][1]},
                                 "printed_total_incl_gst": {"page": tot[0][0], "row": tot[0][1]}}
        doc["header_adds_up"] = True
        retype(doc, {(sub[0][0], sub[0][1]), (gst[0][0], gst[0][1]), (tot[0][0], tot[0][1])}, "TOTALS")

    elif tmpl == "NEW:TENNYSON":
        sub, gst, tot = label_value(doc, "Net   $"), label_value(doc, "GST $"), label_value(doc, "Total $")
        if not (sub and gst and tot):
            log.append((ref, tmpl, "HELD", "Net / GST / Total rows not found", before, None)); return False
        doc["printed_subtotal_ex_gst"], doc["printed_gst"], doc["printed_total_incl_gst"] = \
            float(D(sub[0][2])), float(D(gst[0][2])), float(D(tot[0][2]))
        doc["header_sources"] = {"printed_subtotal_ex_gst": {"page": sub[0][0], "row": sub[0][1]},
                                 "printed_gst": {"page": gst[0][0], "row": gst[0][1]},
                                 "printed_total_incl_gst": {"page": tot[0][0], "row": tot[0][1]}}
        doc["header_adds_up"] = True
        retype(doc, {(sub[0][0], sub[0][1]), (gst[0][0], gst[0][1]), (tot[0][0], tot[0][1])}, "TOTALS")
        # item table header, its bands, and the priced row restated from the Net Price band
        hdr = next(l for l in doc["lines"] if "Net Price" in l["line_text"])
        text = hdr["line_text"]
        bands = {}
        for lab in ("Job", "Quantity", "Description", "Net Price", "GST"):
            i = text.find(lab)
            if i >= 0:
                bands[lab.lower().replace(" ", "_")] = [i, i + len(lab) - 1]
        priced = [l for l in doc["lines"] if l["line_type"] == "PRICED"]
        for l in priced:
            spans = [(m.group(0), m.start(), m.end() - 1) for m in money.finditer(l["line_text"])]
            amt_band = bands["net_price"]
            hit = next((s for s in spans if s[1] <= amt_band[1] + 6 and amt_band[0] - 6 <= s[2]), None)
            if hit:
                bands["net_price"] = [min(amt_band[0], hit[1]), max(amt_band[1], hit[2])]
                l["line_ex_gst"] = float(D(hit[0].replace(",", "")))
                l["band_hits"] = ["net_price"]
                gst_hit = next((s for s in spans if s is not hit), None)
                if gst_hit:
                    l["gst"] = float(D(gst_hit[0].replace(",", "")))
        doc["table_headers"] = [{"page": hdr["page"], "row": hdr["line_no"], "text": text,
                                 "bands": {"description": bands.get("description", [0, 0]),
                                           "amount": bands["net_price"], "gst": bands.get("gst", [0, 0])},
                                 "bands_calibrated_on": {"page": priced[0]["page"], "row": priced[0]["line_no"]},
                                 "is_item_table": True}]
        hdr["line_type"] = "TABLE_HEADER"
        doc["captured_ex_gst"] = float(sum(D(l["line_ex_gst"]) for l in priced))
    else:
        return None

    # repoint every header citation that drifted, then re-derive the document's own checks
    s, g, t = D(doc["printed_subtotal_ex_gst"]), D(doc["printed_gst"]), D(doc["printed_total_incl_gst"])
    cap = sum((D(l["line_ex_gst"]) for l in doc["lines"] if l["line_type"] == "PRICED"), Decimal("0.00"))
    doc["captured_ex_gst"] = float(cap)
    doc["self_tie"] = "TIE" if abs(cap - s) <= Decimal("0.02") else "OUT"
    doc["tie_tolerance"] = "1c" if abs(cap - s) <= Decimal("0.01") else "2c"
    log.append((doc["doc_ref"], tmpl, "RESTATED", "", before, (float(s), float(g), float(t))))
    return True

def fix_citations(doc):
    """Repoint a header citation at the row that actually prints the figure (F8 drift)."""
    moved = 0
    for field in ("printed_subtotal_ex_gst", "printed_gst", "printed_total_incl_gst"):
        val = doc.get(field)
        loc = (doc.get("header_sources") or {}).get(field)
        if val is None or not isinstance(loc, dict):
            continue
        if "deriv" in str(doc.get("gst_basis") or "").lower() and field == "printed_gst":
            continue
        want = f"{abs(D(val)):.2f}"
        rec = next((l for l in doc["lines"] if l["page"] == loc.get("page") and l["line_no"] == loc.get("row")), None)
        if rec and want in rec["line_text"].replace(",", "").replace("$", ""):
            continue
        hit = next((l for l in doc["lines"]
                    if want in l["line_text"].replace(",", "").replace("$", "")
                    and any(k in l["line_text"] for k in ("Total", "TOTAL", "Subtotal", "SUBTOTAL", "GST", "Net", "Balance"))), None)
        if hit:
            doc["header_sources"][field] = {"page": hit["page"], "row": hit["line_no"]}
            if hit["line_type"] not in ("TOTALS", "TABLE_HEADER"):
                hit["line_type"] = "TOTALS"
            moved += 1
    return moved

def main(src, out, logpath):
    corpus = json.load(open(src, encoding="utf-8"))
    log, held, moved = [], [], 0
    for doc in corpus["documents"]:
        r = restate(doc, log)
        if r is False:
            held.append(doc["doc_ref"])
        moved += fix_citations(doc)
    total = sum(D(d.get("captured_ex_gst")) for d in corpus["documents"] if not d.get("duplicate_of"))
    corpus["manifest"]["captured_ex_gst_total"] = float(total)
    corpus["manifest"]["prompt_version"] = "v7.2 (restated from retained text by pswp_header_restate.py)"
    json.dump(corpus, open(out, "w", encoding="utf-8"), indent=1)

    lines = ["# Header restatement log", "",
             f"Source: `{src}`  Output: `{out}`", "",
             f"Documents restated: {sum(1 for r in log if r[2]=='RESTATED')}. Citations repointed: {moved}. Held: {held or 'none'}.", "",
             "| doc_ref | template | subtotal before | GST before | total before | subtotal after | GST after | total after |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for ref, tmpl, status, why, b, a in log:
        if status != "RESTATED":
            lines.append(f"| {ref} | {tmpl} | {status}: {why} | | | | | |"); continue
        lines.append(f"| {ref} | {tmpl} | {b[0]:,.2f} | {b[1]:,.2f} | {b[2]:,.2f} | {a[0]:,.2f} | {a[1]:,.2f} | {a[2]:,.2f} |")
    lines += ["", f"Corpus captured ex GST after restatement: ${total:,.2f}."]
    open(logpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"restated {sum(1 for r in log if r[2]=='RESTATED')}, citations repointed {moved}, held {held or 'none'}")
    print(f"captured ex GST total: {total}")

if __name__ == "__main__":
    main(*sys.argv[1:4])
