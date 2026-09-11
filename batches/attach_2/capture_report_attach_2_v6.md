# Batch attach_2 capture report (raw-text route, branch v5, 11-Sep-2026)

## 1.0 Gate

**GREEN** (pswp_json_repair.repair_and_gate, zero repairs, zero pathologies). Rule 19.2 shingle check: 50 five-word shingles against the retained page text, 0 misses (`shingles_attach_2_v6.json`).

## 2.0 Source and tool

Six single-invoice TechOne attachment PDFs (EzeScan Server21 exports; the file name is the attachment id), delivered in the 11-Sep-2026 13:16 zip with four APLEDGER creditor histories. Extraction: `toolkit/branch/parse_attach2.py`, pdftotext 24.02.0 `-layout`, page text retained, four templates (BURLY, CERTIFIED, C2C_INCL, FLAVELL_ATT). The PDFs are not embedded (rule 15); md5s on Data_Acquisition.

## 3.0 Documents

| Invoice | Vendor | File | Printed ex GST | GST | Incl GST | Priced | Register line(s) | Variant |
|---|---|---|---:|---:|---:|---:|---|---|
| 2122 | Burly Holdings | C00310036.pdf | 5,790.00 | 579.00 | 6,369.00 | 1 | PK000366 | standard |
| INV-0711 | Certified Mowing Pty Ltd | C00311803.pdf | 3,419.40 | 341.94 | 3,761.34 | 1 | PK000397 | standard |
| INV-11824 | Coast2Coast Grounds and Gardens | C00313458.pdf | 4,143.74 | 414.38 | 4,558.12 | 3 | PK000427 + PK000513 | split-posting, check 3 basket |
| INV-0339 | The Trustee for Flavell-Dau Family Trust | C00313632.pdf | 4,388.00 | 438.80 | 4,826.80 | 2 | PK000022 | standard |
| INV-11833 | Coast2Coast Grounds and Gardens | C00315793.pdf | 60,798.99 | 6,079.90 | 66,878.89 | 3 | PK000427 + PK000513 | split-posting |
| INV-0722 | Certified Mowing Pty Ltd | C00316104.pdf | 49,002.91 | 4,900.29 | 53,903.20 | 2 | PK000042 + PK000397 | split-posting |

Total captured $127,543.04 ex GST; every invoice ties to its printed target to the cent. All nine register lines were Tier 3 Unidentified at v4 and are Confirmed, Tier 1 at v5 with all three checks TRUE.

## 4.0 Findings

1. **Coast2Coast fuel levy on a GST-inclusive base (INV-11824), $6.82 ex GST over-claimed.** The invoice prints its own calculation, `$4,475.56 x 0.2477 = $1108.59 x 0.0677 = $75.05`. The base $4,475.56 is the GST-inclusive figure for work of $4,068.69 ex GST. On the ex-GST base the levy is $68.23. INV-11833, the same supplier under the same contract in the same month, uses the ex-GST base correctly ($59,796.25 x 0.2477 x 0.0677 = $1,002.74). Verdict Review, Open Item B-029.
2. **C2C_INCL layout trap.** On this Coast2Coast layout the printed Unit Price and Amount AUD columns are GST inclusive and the description states the ex-GST base; the foot prints "INCLUDES GST 10%" and TOTAL AUD. Lines are captured ex GST as ROUND(printed / 1.1, 2) with the printed figure in the line note (ELEMENTAL precedent), and the printed subtotal is TOTAL AUD less printed GST. Both invoices then tie exactly to their register lines.
3. **Fuel levy legs post to Section NA.** Both C2C fuel levy lines post to PK000513 service 20821 beside the mowing line on the zone PK, the pattern resolved at v3 (Open Item B-023).
4. **Five-digit PK typo (INV-0722).** The main roads line prints "PK00042" and is charged to PK000042; normalised on join with the printed form recorded (rule 13). The invoice also prints "NOTE: this invoice includes Partial deletion MZ3-016 sqm-164, -$4.26".
5. **Burly total label trap.** The layout prints SUBTOTAL, GST, TOTAL, PAID and BALANCE DUE in one column; a `TOTAL:` pattern also matches `SUBTOTAL:`, which read the total as $5,790.00 on the first parse. The template now anchors on `(?<!SUB)TOTAL:`.
6. **Duplicate screen (rule 12).** None of the six invoice numbers exists in the branch or PS_WP v127 Evidence_Invoices; none of the file md5s had been received before.
