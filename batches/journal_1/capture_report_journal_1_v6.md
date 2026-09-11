Gate: GREEN

# Journal batch report: journal_1

Pulled 11-Sep-2026. 6 TechOne Document Line Table exports received, 2 of them duplicate copies, 4 distinct documents.
Legs 104, of which 16 sit on branch O110-O115 and match 16 register lines one for one.
Every document nets to $0.00: True. Every in-scope leg sum ties its register net: True.
Documents embedded verbatim 3, audited only under rule 12 1. Document files fully covered 3 of 4.

## Documents

| Document file | Doc | Format | Journal ref | Legs | In scope | In-scope net | Nets to zero | Ties | Capture |
|---|---|---|---|---:|---:|---:|---|---|---|
| **1246521** | 1 | GENJNL | GJ080188 | 12 | 6 | $53,093.89 | Yes | TRUE | audit only, not re-captured (rule 12) |
| **1248219** | 1 | GENJNL | GJ080309 | 7 | 3 | $51,121.41 | Yes | TRUE | embed verbatim |
| **1245194** | 1 | GENJNL | GJ080153 | 31 | 5 | -$3,289.09 | Yes | TRUE | embed verbatim |
| **1252466** | 2 | LC_INTJN | IJ075145 | 54 | 2 | $17.30 | Yes | TRUE | embed verbatim |

## 1246521 (GJ080188)

- **What the document says:** Already embedded in the PS & WP register v127 Journal_Sources (Tier D on the pull list). The re-pull is audited leg by leg: 12 legs in both copies, none only in the pull, none only in v127, identical on ledger, account, resource code, amount and all three narration lines. Not re-captured; no register line changes.
- **Note:** The v127 embed flags only the PK000435 leg as in PS/WP scope. On the branch scope all six PK legs are register lines, which is a scope difference, not a conflict. The document is the counterpart of the GJ080309 finding: it carries the plant reference (F007834, F006632, F007638, F007814, F008118, F008368) on every leg.
- **Rule 12 audit against PS & WP v127 Journal_Sources:** 12 legs in both, 0 only in the pull, 0 only in v127. identical to the PS & WP v127 embed; audited leg by leg and NOT re-captured (rule 12).
- **Counterparty legs (outside branch scope):** 6, totalling -$53,093.89.

## 1248219 (GJ080309)

- **What the register could not answer:** The set does not net to zero inside O110-O115 (+$51,121.41), so the balancing leg was outside scope and unknown (Open Item B-012).
- **What the document says:** The balancing legs are a G ledger clearing entry, 1330-1-31123 $43,784.58 narrated 'Reverse PJ009910-Reversal', and three cost centre E0035 credits: 1-E0035-73609 $6,880.00 (Digital Platforms), 1-E0035-73513 $258.06 and 1-E0035-72111 $198.77 (Credit card). None sits inside O110-O115 and none is a Plant & Fleet revenue account, so nothing in the document supports the plant hire charge that the three debits carry.
- **Finding:** The three debits reproduce to the cent three of the six plant hire legs that GJ080188 (document 1246521) posted on 01-Jul-2025 to 30-Jun-2026 and that IJ075016 (document 1247889) reversed in full: $27,374.51 (plant F007834, PK000435, Park Services), $23,717.08 (plant F006632, PK000396, Park Maintenance) and $29.82 (plant F008368, PK000068, Natural Areas). GJ080309 posts all three to PK000068. On the evidence of the original legs, $51,091.59 of the $51,121.41 sits on the wrong PK: $27,374.51 belongs to PK000435 and $23,717.08 to PK000396. The GJ080309 legs carry no plant reference in narration line 3, where every GJ080188 leg carries one. The remaining three original legs, PK000012 $1,733.20, PK000034 $227.10 and PK000083 $12.18 ($1,972.48), were reversed and never re-posted.
- **Counterparty legs (outside branch scope):** 4, totalling -$51,121.41.

## 1245194 (GJ080153)

- **What the register could not answer:** Blank narration on all five in-scope lines; Nature Detail read '(blank narration)' and one line sat at Pending evidence, Tier 3.
- **What the document says:** The document is the reversal of the June 2026 Plant & Fleet Services accrual. It debits the two PFS revenue accrual accounts, 1-13081-6D513 $21,057.77 and 1-13121-6D513 $13,656.71, both narrated 'Reversing Journal-June Accruals-for PFS Revenue', and credits the accrued plant, workshop and recharge expense back across 29 Council ledger legs on 7C111, 7C112 and 7C114. Five of those legs sit on branch O110-O115 and are the five register lines.
- **Counterparty legs (outside branch scope):** 26, totalling $3,289.09.

## 1252466 (IJ075145)

- **What the register could not answer:** Both lines carried the generic coding note 'Invoice may bundle multiple items and services; nature unproven at line level'.
- **What the document says:** Document 2 of file 1252466 is the internal rates journal for rating period 2027-1, schedule S03. It raises $34,505.71 against City Bank 1330-1-11111 and allocates it over 53 Council property legs (fire levy, internal water, sewerage, garbage and trade waste). Two legs land on Parks PK000092 at $8.65 each: the Parks share of the $17.65 fire levy on assessment 9915980, 41-43 Alvine Drive, and assessment 9916059, 38 Wyndham Circuit, the other $9.00 of each levy going to SL 1-30071-73422.
- **Coverage:** The export was taken with a Document filter, so it covers document 2 of file 1252466 only: journal reference IJ075145, 2 of the file's 2,020 register lines and 1 of its 8 references. Rule 21 keys the pull to the document FILE; the remaining references IJ075148 and IJ075149 to IJ075155 need the same export without the Document filter (Open Item B-031).
- **Counterparty legs (outside branch scope):** 52, totalling -$17.30.

## Open items raised

- **B-030 Plant hire re-post to a single PK** (Natural Areas / Park Maintenance / Park Services, 3 lines, $51,121.41): Ask Finance to confirm the PK split on GJ080309 against the plant references on GJ080188 and, if confirmed, recode $27,374.51 to PK000435 and $23,717.08 to PK000396; and to confirm why the PK000012, PK000034 and PK000083 legs totalling $1,972.48 were reversed by IJ075016 and never re-posted.
- **B-031 Journal pull taken with a Document filter** (Park Services / Water Parks, 2018 lines, $461,660.80): Re-pull the Document Line Table for document file 1252466 without the Document filter, so the export covers every document on the file (rule 21 keys the pull to the document FILE). The pull received covers document 2, journal reference IJ075145, 2 of the file's 2,020 register lines.

## Duplicate exports (rule 12)

- Document_Line_Table__20260911T142333.018.xlsx (md5 32c528512ce37e9e3b8df94cbaa02a41) is a second copy of document file 1245194 document 1, identical body rows; kept once, Document_Line_Table__20260911T142331.081.xlsx is the copy read.
- Document_Line_Table__20260911T142613.002.xlsx (md5 5463cd8114193b4a1b6ab29425746dfa) is a second copy of document file 1252466 document 2, identical body rows; kept once, Document_Line_Table__20260911T142612.943.xlsx is the copy read.
