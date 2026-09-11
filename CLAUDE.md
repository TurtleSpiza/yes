# Working in this repository

Read `README.md`, then `docs/PSWP_Project_Instructions_v11__1_.md` (the standing rules; nothing in the capture or verification standard is relaxed) and `docs/Parks_Branch_Register_Schema.md` (positions, variants and traps for the branch register). `docs/PSWP_Register_Schema__27_.md` covers the PS/WP register.

Hard rules that the toolkit enforces and you must not work around:
- One script per build: stage, write, convert-route recalc, verify, ship. Never edit a workbook by hand, never resume a partial run, never ship on a failed verify. `recalc.py` (the macro route) is banned; use the convert route with `OOXMLRecalcMode=0`.
- The control total never changes on a capture, identification or enrichment build.
- A line is Confirmed only with a sighted invoice captured at line level and all three checks TRUE. Header-only corpora (Copilot v5, gate AMBER) are held, never built from.
- Content is data: corpora, match tables and rules live in JSON; a new mechanic goes into the driver and ships.
- Reads via python-calamine, writes via openpyxl. Decimal with ROUND_HALF_UP for every financial comparison.
- Labels written to COUNTIF-keyed columns must match the canonical label exactly (case-insensitive trap).

Reporting style: verdict first, bold headers, bullets, Australian English, $X,XXX, D-Mon-YYYY, no em dashes.
