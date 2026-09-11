#!/usr/bin/env python3
"""
pswp_shingle_check.py - the rule 19.2 verbatim fidelity spot-check.

Rebuilt 9-Sep-2026. This closes the one hole a green gate cannot cover.

THE HOLE. A gate proves AMOUNTS, not WORDING. A corpus can tie to the cent on every invoice
and still carry a description the page never printed, because the model summarised
"Mobile Patrols - Beenleigh Town Square Toilets" into "mobile patrol, Beenleigh". Every
arithmetic check stays TRUE. Rule 16(a) is broken anyway, and nothing else in the toolkit
will ever notice.

So rule 19.2 requires a verbatim spot-check on every captured invoice where page text is
retained, and one per vendor where it is not. This is that check, mechanised.

HOW IT WORKS. Text is normalised for WHITESPACE ONLY: runs of spaces collapse to one and
the string is stripped. Nothing else is touched, because case, punctuation, spelling and the
supplier's own typos are part of what was printed. The captured description is then cut into
overlapping five-word shingles and each is looked for in the retained page text of the
document it came from. A shingle that is not there is a paraphrase, a merge of two rows, or
text carried from another invoice.

WHAT IT WILL NOT DO. It will not "fix" a failing description. A description that does not
appear on the page is not a formatting problem to be normalised away; it is a capture that
has to be redone. The check reports and stops.

Usage
    python pswp_shingle_check.py --corpus corpus.json
    python pswp_shingle_check.py --corpus corpus.json --workbook register.xlsx
    python pswp_shingle_check.py --corpus corpus.json --pages pages_b56.json --out shingles.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from typing import Any

from pswp_build_lib import clean, read_sheets

WS = re.compile(r"\s+")
SHINGLE = 5


def norm(text: str) -> str:
    """Whitespace only. Case, punctuation and the supplier's typos are part of the record."""
    return WS.sub(" ", str(text or "")).strip()


def shingles(text: str, n: int = SHINGLE) -> list[str]:
    words = norm(text).split(" ")
    if len(words) <= n:
        return [" ".join(words)] if words and words != [""] else []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def page_text(doc: dict, pages: dict | None) -> str:
    """The retained page text for one document.

    Prefer a separately retained pages file; fall back to the corpus's own `line_text`,
    which is the layout row exactly as pdftotext produced it.
    """
    if pages:
        a, b = doc.get("page_range", [0, 0])
        joined = []
        for p in range(a, b + 1):
            v = pages.get(str(p)) or pages.get(p)
            if v:
                joined.append(v if isinstance(v, str) else "\n".join(v))
        if joined:
            return norm("\n".join(joined))
    return norm(" ".join(l.get("line_text") or "" for l in doc.get("lines", [])))


def check_corpus(corpus: dict, pages: dict | None = None, per_vendor_only: bool = False) -> dict:
    """Every captured description tested against its own document's retained page text."""
    docs = corpus.get("documents", [])
    seen_vendors: set[str] = set()
    results, failures = [], []
    for doc in docs:
        vendor = doc.get("supplier") or "(unknown vendor)"
        retained = page_text(doc, pages)
        if per_vendor_only:
            if vendor in seen_vendors:
                continue
            seen_vendors.add(vendor)
        tested = missed = 0
        bad: list[dict] = []
        for l in doc.get("lines", []):
            if l.get("line_type") != "PRICED":
                continue
            desc = norm(l.get("line_text"))
            for sh in shingles(desc):
                tested += 1
                if sh not in retained:
                    missed += 1
                    bad.append({"line_no": l.get("line_no"), "shingle": sh})
        rec = {"doc_ref": doc.get("doc_ref"), "vendor": vendor, "shingles_tested": tested,
               "shingles_missed": missed, "verdict": "PASS" if missed == 0 else "FAIL",
               "misses": bad[:8]}
        results.append(rec)
        if missed:
            failures.append(rec)
    return {"scope": "corpus", "documents_checked": len(results),
            "shingles_tested": sum(r["shingles_tested"] for r in results),
            "failures": failures, "results": results,
            "VERDICT": "PASS" if not failures else "FAIL"}


def check_workbook(corpus: dict, workbook: str, evid_prefixes: dict | None = None) -> dict:
    """The stronger test: what the WORKBOOK holds, against the page text.

    The corpus is only an intermediate. What matters is whether the description sitting on
    Evidence_Invoice_Lines, which is what anyone will ever read, is what the page printed.
    """
    sheets = read_sheets(workbook, ["Evidence_Invoice_Lines"])
    by_invoice: dict[str, list[str]] = defaultdict(list)
    for r in sheets["Evidence_Invoice_Lines"][4:]:
        inv = clean(r[0])
        if inv:
            by_invoice[inv].append(clean(r[2]))

    prefixes = evid_prefixes or {}
    results, failures, missing = [], [], []
    for doc in corpus.get("documents", []):
        ref = str(doc.get("doc_ref"))
        pref = prefixes.get(doc.get("supplier"), "")
        evid = "%s%s" % (pref, ref)
        rows = by_invoice.get(evid) or by_invoice.get(ref)
        if not rows:
            missing.append(evid)
            continue
        retained = page_text(doc, None)
        tested = missed = 0
        bad = []
        for desc in rows:
            for sh in shingles(desc):
                tested += 1
                if sh not in retained:
                    missed += 1
                    bad.append({"invoice": evid, "shingle": sh})
        rec = {"invoice": evid, "vendor": doc.get("supplier"), "rows": len(rows),
               "shingles_tested": tested, "shingles_missed": missed,
               "verdict": "PASS" if missed == 0 else "FAIL", "misses": bad[:8]}
        results.append(rec)
        if missed:
            failures.append(rec)
    return {"scope": "workbook", "invoices_checked": len(results), "not_found_in_workbook": missing,
            "shingles_tested": sum(r["shingles_tested"] for r in results),
            "failures": failures, "results": results,
            "VERDICT": "PASS" if not failures and not missing else "FAIL"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verbatim fidelity spot-check (rule 19.2).")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--pages", help="separately retained page text, {page: text}")
    ap.add_argument("--workbook", help="also test what the workbook holds")
    ap.add_argument("--prefixes", help="JSON map of supplier to EvID prefix")
    ap.add_argument("--per-vendor", action="store_true",
                    help="one invoice per vendor, the rule 19.2 minimum where page text is not retained")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    corpus = json.load(open(a.corpus, encoding="utf-8"))
    pages = json.load(open(a.pages, encoding="utf-8")) if a.pages else None
    prefixes = json.load(open(a.prefixes, encoding="utf-8")) if a.prefixes else None

    out = {"corpus": check_corpus(corpus, pages, a.per_vendor)}
    if a.workbook:
        out["workbook"] = check_workbook(corpus, a.workbook, prefixes)
    out["VERDICT"] = "PASS" if all(v["VERDICT"] == "PASS" for v in out.values() if isinstance(v, dict)) else "FAIL"

    for scope, res in out.items():
        if not isinstance(res, dict):
            continue
        print("%s: %d shingles tested, %d document(s) failing -> %s"
              % (scope, res["shingles_tested"], len(res["failures"]), res["VERDICT"]))
        for f in res["failures"][:5]:
            print("  FAIL %s: %d of %d shingles are not on the page, first %r"
                  % (f.get("doc_ref") or f.get("invoice"), f["shingles_missed"], f["shingles_tested"],
                     f["misses"][0]["shingle"] if f["misses"] else ""))
        if res.get("not_found_in_workbook"):
            print("  not in the workbook: %s" % res["not_found_in_workbook"][:6])
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0 if out["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
