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


# This project retains a line break inside a captured cell as " | " (pbr_build.py Method notes,
# Parks_Branch_Register_Schema.md: "Details (newlines as \" | \")"). The page prints a newline
# there, so a shingle straddling the join would never be found on the page and the check would
# read FAIL on a faithful capture. The marker is therefore treated as the line break it stands
# for, on BOTH sides of the comparison, which leaves the words and their order still to prove.
PIPE_BREAK = re.compile(r"\s+\|\s+")


def norm(text: str) -> str:
    """Whitespace only, plus the retained line-break marker. Case, punctuation and the
    supplier's typos are part of the record and are never touched."""
    return WS.sub(" ", PIPE_BREAK.sub(" ", str(text or ""))).strip()


def shingles(text: str, n: int = SHINGLE) -> list[str]:
    words = norm(text).split(" ")
    if len(words) <= n:
        return [" ".join(words)] if words and words != [""] else []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def page_text(doc: dict, pages: dict | None) -> tuple[str, str]:
    """The retained page text for one document, and WHERE it came from.

    The source is returned because it decides whether the check means anything. A separately
    retained pages file, or the document's own `page_text`, is an independent record of what
    the page printed. The corpus's own `line_text` is NOT: it is the captured text itself, so
    testing a captured description against it asks whether the text equals itself. That reads
    PASS on every corpus ever produced, including one whose every description is invented,
    which is the one failure mode this check exists to catch. The caller must refuse it.
    """
    if pages:
        a, b = doc.get("page_range", [0, 0])
        sf = doc.get("source_file")
        joined = []
        for p in range(a, b + 1):
            # NEW 18-Sep-2026. A multi-source corpus numbers each binder from 1 independently,
            # so a pages file keyed on the bare page number COLLIDES: page 5 of one binder and
            # page 5 of another are the same key. Found on
            # playforce_vinton_glascott_20260916, where five Play Force documents at binder
            # pages 1 to 16 were tested against the Glascott binder's pages 1 to 16 and the
            # check reported five FAILs that were artefacts of the key. A false FAIL is the
            # better half of that defect: two binders sharing boilerplate would have produced
            # a false PASS, which is the failure mode this check exists to catch.
            #
            # A qualified key "<source_file>|<page>" is read first and is what a multi-source
            # corpus must use. The bare key stays for the single-source case, which is every
            # other corpus here, and check_corpus refuses a bare-keyed file on a multi-source
            # corpus rather than letting it collide quietly.
            v = None
            if sf:
                v = pages.get(f"{sf}|{p}") or pages.get(f"{sf}|{p:d}")
            if v is None:
                v = pages.get(str(p)) or pages.get(p)
            if v:
                joined.append(v if isinstance(v, str) else "\n".join(v))
        if joined:
            return norm("\n".join(joined)), "pages_file"
    own = doc.get("page_text")
    if own:
        # retained page text is a {page: text} map on every corpus this project holds, but a
        # string or a list of pages is accepted too; a dict must be joined on its VALUES.
        if isinstance(own, dict):
            joined = "\n".join(str(v) for _k, v in sorted(own.items(), key=lambda kv: str(kv[0])))
        elif isinstance(own, (list, tuple)):
            joined = "\n".join(str(v) for v in own)
        else:
            joined = str(own)
        if joined.strip():
            return norm(joined), "page_text"
    return norm(" ".join(l.get("line_text") or "" for l in doc.get("lines", []))), "line_text"


def assert_pages_keying(corpus: dict, pages: dict | None) -> None:
    """Refuse a bare-keyed pages file on a multi-source corpus.

    Silently colliding is worse than refusing: the caller gets a verdict that looks like a
    result. If a corpus names more than one source file, every page key must be qualified
    "<source_file>|<page>", except where the pages supplied cover only ONE of those files and
    are keyed in that file's own numbering, which cannot collide with pages that were not
    supplied.
    """
    if not pages:
        return
    srcs = {d.get("source_file") for d in corpus.get("documents", []) if d.get("source_file")}
    if len(srcs) < 2:
        return
    qualified = {k for k in pages if isinstance(k, str) and "|" in k}
    if qualified and len(qualified) == len(pages):
        return
    bare = {str(k) for k in pages if not (isinstance(k, str) and "|" in k)}
    reachable = {}
    for d in corpus.get("documents", []):
        a, b = d.get("page_range", [0, 0])
        for p in range(a, b + 1):
            reachable.setdefault(str(p), set()).add(d.get("source_file"))
    clashing = sorted(k for k in bare if len(reachable.get(k, ())) > 1)
    if clashing:
        raise SystemExit(
            f"pages file is keyed on bare page numbers, but this corpus has {len(srcs)} source "
            f"files and {len(clashing)} of those keys are reachable from more than one of them "
            f"(first: {clashing[:5]}). Key every page \"<source_file>|<page>\" or supply one "
            f"binder at a time. Colliding keys test a document against another binder's page.")


def check_corpus(corpus: dict, pages: dict | None = None, per_vendor_only: bool = False) -> dict:
    """Every captured description tested against its own document's retained page text."""
    docs = corpus.get("documents", [])
    seen_vendors: set[str] = set()
    results, failures, unverifiable = [], [], []
    for doc in docs:
        vendor = doc.get("supplier") or "(unknown vendor)"
        retained, source = page_text(doc, pages)
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
        verdict = "FAIL" if missed else ("UNVERIFIABLE" if source == "line_text" else "PASS")
        rec = {"doc_ref": doc.get("doc_ref"), "vendor": vendor, "shingles_tested": tested,
               "shingles_missed": missed, "source": source, "verdict": verdict,
               "misses": bad[:8]}
        results.append(rec)
        if missed:
            failures.append(rec)
        elif verdict == "UNVERIFIABLE":
            unverifiable.append(rec)
    return {"scope": "corpus", "documents_checked": len(results),
            "shingles_tested": sum(r["shingles_tested"] for r in results),
            "failures": failures, "unverifiable": unverifiable, "results": results,
            "VERDICT": "FAIL" if failures else ("UNVERIFIABLE" if unverifiable else "PASS")}


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
    results, failures, missing, unverifiable = [], [], [], []
    for doc in corpus.get("documents", []):
        ref = str(doc.get("doc_ref"))
        pref = prefixes.get(doc.get("supplier"), "")
        evid = "%s%s" % (pref, ref)
        rows = by_invoice.get(evid) or by_invoice.get(ref)
        if not rows:
            missing.append(evid)
            continue
        retained, source = page_text(doc, None)
        tested = missed = 0
        bad = []
        for desc in rows:
            for sh in shingles(desc):
                tested += 1
                if sh not in retained:
                    missed += 1
                    bad.append({"invoice": evid, "shingle": sh})
        verdict = "FAIL" if missed else ("UNVERIFIABLE" if source == "line_text" else "PASS")
        rec = {"invoice": evid, "vendor": doc.get("supplier"), "rows": len(rows),
               "shingles_tested": tested, "shingles_missed": missed, "source": source,
               "verdict": verdict, "misses": bad[:8]}
        results.append(rec)
        if missed:
            failures.append(rec)
        elif verdict == "UNVERIFIABLE":
            unverifiable.append(rec)
    return {"scope": "workbook", "invoices_checked": len(results), "not_found_in_workbook": missing,
            "shingles_tested": sum(r["shingles_tested"] for r in results),
            "failures": failures, "unverifiable": unverifiable, "results": results,
            "VERDICT": "FAIL" if failures or missing else ("UNVERIFIABLE" if unverifiable else "PASS")}


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

    assert_pages_keying(corpus, pages)
    out = {"corpus": check_corpus(corpus, pages, a.per_vendor)}
    if a.workbook:
        out["workbook"] = check_workbook(corpus, a.workbook, prefixes)
    vs = [v["VERDICT"] for v in out.values() if isinstance(v, dict)]
    out["VERDICT"] = "FAIL" if "FAIL" in vs else ("UNVERIFIABLE" if "UNVERIFIABLE" in vs else "PASS")

    for scope, res in out.items():
        if not isinstance(res, dict):
            continue
        print("%s: %d shingles tested, %d document(s) failing, %d unverifiable -> %s"
              % (scope, res["shingles_tested"], len(res["failures"]),
                 len(res.get("unverifiable") or []), res["VERDICT"]))
        if res.get("unverifiable"):
            print("  UNVERIFIABLE: %d document(s) retain no page text, so the only haystack is the captured"
                  % len(res["unverifiable"]))
            print("  text itself and the test cannot fail. Supply the binder's page text with --pages.")
        for f in res["failures"][:5]:
            print("  FAIL %s: %d of %d shingles are not on the page, first %r"
                  % (f.get("doc_ref") or f.get("invoice"), f["shingles_missed"], f["shingles_tested"],
                     f["misses"][0]["shingle"] if f["misses"] else ""))
        if res.get("not_found_in_workbook"):
            print("  not in the workbook: %s" % res["not_found_in_workbook"][:6])
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0 if out["VERDICT"] == "PASS" else 1  # UNVERIFIABLE is not a pass


if __name__ == "__main__":
    sys.exit(main())
