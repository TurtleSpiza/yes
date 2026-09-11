#!/usr/bin/env python3
"""
pswp_dup_screen.py - the rule 12 duplicate-screening gate, standalone.

Rebuilt 9-Sep-2026. `pswp_build_batch.py` runs this screen inside its gates; this is the
same screen on demand, so a binder can be triaged BEFORE anyone spends a session parsing it.

RULE 12 IS A GATE, NOT A COURTESY. md5 every upload against Data_Acquisition before any
parse, and screen every corpus id against Evidence_Invoices column A before the match table
is trusted. A re-sighting is NOT re-captured: it is audited against the existing capture and
recorded, which is what happened to 33 of the 34 invoices in Binder1 at v33 and 13 of the 14
in Tully at v120.

TWO TRAPS THIS SCREEN EXISTS FOR

1. The leading-zero false match. Harpley prints eight-digit ids and Q Power prints five, so
   a bare `endswith` makes Q Power `14725` look like an already-captured Harpley
   `00014725`. Five such hits were cleared at v119 by screening on the VENDOR as well as the
   digits. A screen that reports them as re-sightings loses five real captures.

2. The same-name-different-entity case. A series can be multi-vendor, and same-name vendors
   can be different entities across financial years, so the ABN decides (rule 8). Where a
   candidate matches an existing EvID but the ABNs differ, this reports a COLLISION rather
   than either a duplicate or a new capture, and a collision is a decision for the session,
   not for a script.

VERDICTS
    NEW            no existing capture: parse and build it
    RE_SIGHTING    already on Evidence_Invoices: audit against the existing capture, do not
                   re-capture, and record the audit
    FALSE_MATCH    digits collide but the vendor does not: this is a new capture
    COLLISION      the id matches but the ABN differs: a session decision
    FILE_SEEN      the md5 of this upload is already in Data_Acquisition

Usage
    python pswp_dup_screen.py register.xlsx --corpus corpus.json --files Batch112.pdf
    python pswp_dup_screen.py register.xlsx --refs 7470,7475 --vendor "Kachel Cleaning"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

from pswp_build_lib import clean, md5_file, read_sheets

DIGITS = re.compile(r"\d+")


def digits_of(ref: str) -> str:
    d = "".join(DIGITS.findall(str(ref)))
    return d.lstrip("0") or d


def vendor_key(name: str) -> str:
    """A loose vendor key: the first significant word, lowercased.

    'Harpley Services Pty Ltd' and 'Harpley Services' are the same vendor for screening;
    'Q Power (Qld) Pty Ltd' is not, which is the whole point.
    """
    words = [w for w in re.split(r"[^A-Za-z0-9]+", str(name or "")) if w]
    skip = {"the", "trustee", "for"}
    for w in words:
        if w.lower() not in skip:
            return w.lower()
    return ""


def screen(workbook: str, candidates: list[dict], files: list[str] | None = None) -> dict:
    sheets = read_sheets(workbook, ["Evidence_Invoices", "Data_Acquisition"])
    ei = sheets["Evidence_Invoices"]
    existing = []
    for r in ei[4:]:
        inv = clean(r[0])
        if inv:
            existing.append({"evid": inv, "vendor": clean(r[1]), "abn": clean(r[2]),
                             "ex_gst": clean(r[9]), "incl": clean(r[11])})
    by_digits: dict[str, list[dict]] = {}
    for e in existing:
        by_digits.setdefault(digits_of(e["evid"]), []).append(e)

    da_text = "\n".join(clean(c) for row in sheets["Data_Acquisition"] for c in (row or []))
    file_results = []
    for f in files or []:
        if not os.path.exists(f):
            file_results.append({"file": f, "verdict": "NOT_FOUND"})
            continue
        h = md5_file(f)
        file_results.append({"file": os.path.basename(f), "md5": h,
                             "verdict": "FILE_SEEN" if h in da_text else "NEW"})

    results = []
    for c in candidates:
        ref, vendor, abn = str(c["ref"]), c.get("vendor", ""), clean(c.get("abn"))
        hits = by_digits.get(digits_of(ref), [])
        exact = [h for h in hits if h["evid"] == ref or h["evid"].endswith(ref)]
        if not hits:
            results.append({"ref": ref, "vendor": vendor, "verdict": "NEW"})
            continue
        same_vendor = [h for h in hits if vendor_key(h["vendor"]) == vendor_key(vendor)]
        if not same_vendor:
            results.append({"ref": ref, "vendor": vendor, "verdict": "FALSE_MATCH",
                            "note": "digits collide with %s (%s); different vendor, so this is a new capture"
                                    % (hits[0]["evid"], hits[0]["vendor"]),
                            "collides_with": [h["evid"] for h in hits][:4]})
            continue
        differing = [h for h in same_vendor if abn and h["abn"] and
                     re.sub(r"\D", "", h["abn"]) != re.sub(r"\D", "", abn)]
        if differing:
            results.append({"ref": ref, "vendor": vendor, "verdict": "COLLISION",
                            "note": "same id and vendor name but a different printed ABN; rule 8 says the ABN decides",
                            "existing": differing[0]})
            continue
        results.append({"ref": ref, "vendor": vendor, "verdict": "RE_SIGHTING",
                        "existing": same_vendor[0],
                        "note": "already captured; audit against the existing capture to the cent and record it, do not re-capture"})

    counts: dict[str, int] = {}
    for r in results + file_results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return {"workbook": workbook, "files": file_results, "candidates": results,
            "counts": counts,
            "VERDICT": "CLEAR" if not counts.get("COLLISION") and not counts.get("FILE_SEEN") else "REVIEW"}


def from_corpus(path: str) -> list[dict]:
    corpus = json.load(open(path, encoding="utf-8"))
    return [{"ref": d.get("doc_ref"), "vendor": d.get("supplier"), "abn": d.get("supplier_abn")}
            for d in corpus.get("documents", [])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rule 12 duplicate screening.")
    ap.add_argument("workbook")
    ap.add_argument("--corpus")
    ap.add_argument("--refs", help="comma-separated ids, used with --vendor")
    ap.add_argument("--vendor", default="")
    ap.add_argument("--files", nargs="*", help="uploads to md5 against Data_Acquisition")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    cands = from_corpus(a.corpus) if a.corpus else \
        [{"ref": r.strip(), "vendor": a.vendor} for r in (a.refs or "").split(",") if r.strip()]
    res = screen(a.workbook, cands, a.files)
    print("screen: " + ", ".join("%s %d" % kv for kv in sorted(res["counts"].items())) + " -> " + res["VERDICT"])
    for r in res["candidates"]:
        if r["verdict"] != "NEW":
            print("  %-12s %-16s %s" % (r["verdict"], r["ref"], r.get("note", "")))
    for f in res["files"]:
        if f["verdict"] != "NEW":
            print("  %-12s %s" % (f["verdict"], f["file"]))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    return 0 if res["VERDICT"] == "CLEAR" else 1


if __name__ == "__main__":
    sys.exit(main())
