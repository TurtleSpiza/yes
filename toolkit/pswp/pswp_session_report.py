#!/usr/bin/env python3
"""
pswp_session_report.py - the end-of-session report, assembled from the artefacts.

Rebuilt 9-Sep-2026. Section 6.8 says a session ends with the workbook, the changed knowledge
files, the brief, the corpus, match and summary JSONs, and ONE report. Section 6.10 sets its
shape: verdict first, bold headers, bullets, Australian English, $X,XXX, D-Mon-YYYY, no
em-dashes.

This assembles that report from what the session actually produced rather than from what
anyone remembers it produced. Every figure in the output is read out of an artefact: the
repair report, the brief, the match table, the verify result, the bounds result, the build
log. Nothing is retyped, so nothing drifts between the workbook and the report.

It writes the report and stops. It does not decide what the findings mean, because that is
the session's judgement and not a script's: findings come from the brief and the corpus,
where the session put them.

Usage
    python pswp_session_report.py --brief brief.json --verify verify.json \\
        --bounds bounds.json --build-log build.txt --out report.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal

from pswp_build_lib import D, fmt, money

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def au_date(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return "%d-%s-%d" % (dt.day, MONTHS[dt.month - 1], dt.year)


def load(path: str | None):
    if not path or not os.path.exists(path):
        return None
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf-8"))
    return open(path, encoding="utf-8").read()


def build_report(brief: dict | None, corpora: list[dict], match: dict | None,
                 verify: dict | None, bounds: dict | None, build_log: str | None,
                 selftest: str | None) -> str:
    lines: list[str] = []

    shipped = None
    if build_log:
        m = re.search(r"shipped: file ([^,]+), (.*)", build_log)
        if m:
            shipped = m.group(0)

    verdict_bits = []
    if verify:
        verdict_bits.append("verify %s on %d limbs" % (verify["VERDICT"], len(verify.get("ok", []))))
    if bounds:
        verdict_bits.append("bounds audit %s on %s ranges" % (bounds["VERDICT"], "{:,}".format(bounds["stats"]["tested"])))
    docs = sum(len(c.get("documents", [])) for c in corpora)
    value = money(sum(D(d.get("printed_subtotal_ex_gst") or 0) for c in corpora for d in c.get("documents", [])))

    lines.append("**Verdict: %s captured, %s ex GST%s.**"
                 % ("%d documents" % docs, fmt(value),
                    (", " + ", ".join(verdict_bits)) if verdict_bits else ""))
    lines.append("")

    if brief:
        lines.append("**Build**")
        lines.append("")
        lines.append("- **Version:** %s to %s, built %s." % (brief.get("version_from"), brief.get("version_to"), au_date()))
        lines.append("- **Batches:** %s." % brief.get("batch_label", brief.get("batch_id")))
        if shipped:
            lines.append("- **Chain:** %s" % shipped)
        lines.append("")

    lines.append("**Capture**")
    lines.append("")
    for c in corpora:
        m = c.get("manifest", {})
        lines.append("- **%s:** %d documents, %d at TIE, %d at OUT, %d line records, %s captured ex GST. Gate %s."
                     % (m.get("batch_id"), m.get("documents_found", 0), m.get("documents_tie", 0),
                        m.get("documents_out", 0), m.get("lines_captured", 0),
                        fmt(m.get("captured_ex_gst_total")), m.get("gate")))
        for entry in m.get("repair_log", []) or []:
            lines.append("  - **Repaired:** %d repair(s) applied by %s before any build."
                         % (len(entry.get("repairs", [])), entry.get("tool")))
    lines.append("")

    if match:
        total = sum(len(v) for v in match.get("batches", {}).values())
        unique = sum(1 for v in match.get("batches", {}).values() for r in v if r.get("target_count") == 1)
        lines.append("**Register match**")
        lines.append("")
        lines.append("- %d of %d documents resolve to exactly one AP row at the printed subtotal." % (unique, total))
        lines.append("")

    findings = []
    for c in corpora:
        for f in c.get("manifest", {}).get("batch_findings", []) or []:
            findings.append((f.get("code"), "batch", f.get("detail")))
        for d in c.get("documents", []):
            for f in d.get("findings", []) or []:
                findings.append((f.get("code"), d.get("doc_ref"), f.get("detail")))
    if findings:
        lines.append("**Findings**")
        lines.append("")
        seen = set()
        n = 0
        for code, where, detail in findings:
            key = (code, detail)
            if key in seen:
                continue
            seen.add(key)
            n += 1
            lines.append("%d. **%s, %s:** %s" % (n, code, where, detail))
        lines.append("")

    if brief and brief.get("open_items"):
        lines.append("**Open items raised**")
        lines.append("")
        for it in brief["open_items"]:
            lines.append("- **%s, %s:** %s" % (it.get("series"), fmt(it.get("amount")), it.get("action")))
        lines.append("")

    if verify:
        lines.append("**Controls**")
        lines.append("")
        for line in verify.get("ok", []):
            lines.append("- %s" % line)
        for line in verify.get("fails", []):
            lines.append("- **FAIL:** %s" % line)
        lines.append("")

    if bounds:
        st = bounds["stats"]
        lines.append("**Bounds audit**")
        lines.append("")
        lines.append("- %s ranges tested: %s exact, %s with headroom, %s short, %s spanning. Verdict %s."
                     % ("{:,}".format(st["tested"]), "{:,}".format(st.get("EXACT", 0)),
                        st.get("HEADROOM", 0), st.get("SHORT", 0), st.get("SPANNING", 0), bounds["VERDICT"]))
        lines.append("")

    if selftest:
        passed = selftest.count("PASS ")
        failed = selftest.count("FAIL ")
        lines.append("**Toolkit selftest**")
        lines.append("")
        lines.append("- %d tests passed, %d failed." % (passed, failed))
        lines.append("")

    lines.append("**Next**")
    lines.append("")
    lines.append("- Review the Nature Categories and Details in the brief before the candidate ships as a handover version.")
    lines.append("- Number the open items above against the live Open_Items tail.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assemble the end-of-session report from the artefacts.")
    ap.add_argument("--brief")
    ap.add_argument("--corpus", nargs="*", default=[])
    ap.add_argument("--match")
    ap.add_argument("--verify")
    ap.add_argument("--bounds")
    ap.add_argument("--build-log")
    ap.add_argument("--selftest")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    brief = load(a.brief)
    corpora = [json.load(open(p, encoding="utf-8")) for p in a.corpus]
    if not corpora and brief:
        for p in brief.get("corpora", []):
            fp = p if os.path.isabs(p) else os.path.join(os.path.dirname(os.path.abspath(a.brief)), p)
            if os.path.exists(fp):
                corpora.append(json.load(open(fp, encoding="utf-8")))

    text = build_report(brief, corpora, load(a.match), load(a.verify), load(a.bounds),
                        load(a.build_log), load(a.selftest))
    open(a.out, "w", encoding="utf-8").write(text)
    print("report written: %s (%d lines)" % (a.out, text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
