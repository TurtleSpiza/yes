# Working in this repository

The toolchain is provisioned before the session starts by `.claude/hooks/session-start.sh` (python-calamine, openpyxl, lxml, poppler-utils, libreoffice-calc; pins in `requirements.txt`). If anything in the chain misbehaves, run `python3 toolkit/branch/pbr_env_check.py --all` first: it proves the recalc and PDF legs on throwaway files and names the missing package. A recalc that reports "source file could not be loaded" is a missing `libreoffice-calc`, not a corrupt workbook.

Read `README.md`, then `docs/PSWP_Project_Instructions_v11__1_.md` (the standing rules; nothing in the capture or verification standard is relaxed) and `docs/Parks_Branch_Register_Schema.md` (positions, variants and traps for the branch register). `docs/PSWP_Register_Schema__27_.md` covers the PS/WP register. Invoice extraction runs on `docs/PSWP_Extraction_Prompt_v6.md`; v5 is retained only because two held batches were extracted under it.

Hard rules that the toolkit enforces and you must not work around:
- One script per build: stage, write, convert-route recalc, verify, ship. Never edit a workbook by hand, never resume a partial run, never ship on a failed verify. `recalc.py` (the macro route) is banned; use the convert route with `OOXMLRecalcMode=0`.
- The control total never changes on a capture, identification or enrichment build.
- A line is Confirmed only with a sighted invoice captured at line level and all three checks TRUE. Header-only corpora (Copilot v5, gate AMBER) are held, never built from.
- Content is data: corpora, match tables and rules live in JSON; a new mechanic goes into the driver and ships.
- One register per family in `registers/`: the newest shipped version, plus any older version that is still a build input (pinned in `toolkit/branch/pbr_retention_v1.json`, or named literally by a toolkit script). A register is an output, and xlsx is a zip git cannot delta-compress, so every version committed costs its full size in the clone forever. The ship leg runs `pbr_retention.py` after a clean verify; `python3 toolkit/branch/pbr_retention.py` dry-runs it. Never commit a superseded register back in.
- Reads via python-calamine, writes via openpyxl. Decimal with ROUND_HALF_UP for every financial comparison.
- Labels written to COUNTIF-keyed columns must match the canonical label exactly (case-insensitive trap).
- A corpus that fails any of its own gates is logged, held and never part-built from. A misclassified row can be restated from the retained text; a page with no line record (P3) cannot, and needs the binder back.

Before shipping a change to the toolkit, run the two gates: `python3 -m compileall -q toolkit` and `python3 toolkit/branch/pbr_env_check.py --all`. The end-to-end test is a real build to a scratch directory, which leaves the repository untouched: `PBR_OUTDIR=/tmp/testout python3 toolkit/branch/pbr_build.py`.

Reporting style: verdict first, bold headers, bullets, Australian English, $X,XXX, D-Mon-YYYY, no em dashes.
