#!/usr/bin/env python3
"""pswp_mark_archival.py, v1 (18-Sep-2026)

Set `manifest.archival: true` on every retained snapshot, per prompt v7.7 rule 11.12.

A batch that has been restated keeps two or more corpora: the snapshot of what was received,
and the live corpus the build reads. The snapshot exists so a restatement can be read against
what it restated, and rule 12 forbids re-capturing an audited document, so the snapshot is
never edited and never built from. Every remedy in the standard is therefore unavailable to
it by design, including section 12's stem tie-break: applying one would falsify the record.

Until this flag existed the snapshots were gated as though live, and the RED count reported
five defects that were not outstanding work. The gate now prints `[ARCHIVAL]` beside the
verdict and keeps the verdict, because the verdict is a true statement about what arrived.

A corpus is a snapshot only when BOTH hold:
  - its filename ends `_as_received`, `_as_supplied` or `_v5`; AND
  - a live sibling corpus exists in the same batch directory.
The second condition matters. A lone corpus is the live one whatever it is called, and
`mixed_1_v5` would be marked archival on its name alone while `corpus_mixed_1_v6.json` is
what the build reads. Marking a lone corpus archival would quietly take a real batch out of
every count.

Usage:  python3 pswp_mark_archival.py [--apply] [--root batches]
Default is a DRY RUN that prints what it would set and changes nothing.
"""
import json, os, re, sys

SNAPSHOT = re.compile(r'_(as_received|as_supplied|v5)\.json$')


def plan(root="batches"):
    out = []
    for d in sorted(os.listdir(root)):
        bd = os.path.join(root, d)
        if not os.path.isdir(bd):
            continue
        corpora = sorted(f for f in os.listdir(bd)
                         if f.startswith("corpus_") and f.endswith(".json"))
        snaps = [f for f in corpora if SNAPSHOT.search(f)]
        live = [f for f in corpora if not SNAPSHOT.search(f)]
        if not live:
            for f in snaps:
                out.append((os.path.join(bd, f), "SKIP", "no live sibling: this is the batch"))
            continue
        for f in snaps:
            p = os.path.join(bd, f)
            man = json.load(open(p)).get("manifest", {})
            state = "ALREADY" if man.get("archival") else "SET"
            out.append((p, state, "live sibling(s): " + ", ".join(live)))
    return out


def main(argv):
    root = "batches"
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    apply_it = "--apply" in argv
    rows = plan(root)
    changed = 0
    for p, state, why in rows:
        print(f"  {state:<8} {os.path.basename(p):<58} {why}")
        if state == "SET" and apply_it:
            # Insert the key TEXTUALLY, matching the file's own indentation. A snapshot is the
            # record of what arrived, so it gets a one-line diff and not a reserialisation: a
            # json.load/json.dump round trip rewrote all 11 of these at a different indent and
            # produced a 1.3 million line diff over an audit trail, which is the opposite of
            # what the flag is for.
            src = open(p).read()
            m = re.search(r'\n(\s*)"batch_id"\s*:', src)
            if not m:
                print(f"  SKIP     {os.path.basename(p):<58} no batch_id line to anchor on")
                continue
            ind = m.group(1)
            src = src[:m.start()] + f'\n{ind}"archival": true,' + src[m.start():]
            json.loads(src)                    # the edit must leave valid JSON, or nothing is written
            open(p, "w").write(src)
            changed += 1
    n = sum(1 for _, s, _ in rows if s == "SET")
    print(f"  {n} snapshot(s) to mark, {changed} written"
          f"{'' if apply_it else '  (dry run: pass --apply to write)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
