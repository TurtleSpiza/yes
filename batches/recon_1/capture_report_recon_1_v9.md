Gate: GREEN

# Reconstruction batch report: recon_1

Pulled 14-Sep-2026. 5 TechOne Document Reconstruction exports received, 0 of them duplicate copies, 5 distinct documents.
Legs 4,588, of which 422 sit on branch O110-O115 and match 422 register lines one for one.
Documents embedded verbatim 4, audited only under rule 12 1.
Every document nets to $0.00: True. Every in-scope leg sum ties its register net: True.

## Documents

| Document cross reference | Ledger | Account | Journal ref | Legs | In scope | In-scope net | Nets to zero | Ties | Capture |
|---|---|---|---|---:|---:|---:|---|---|---|
| **202609031114916000000001** | 27SLACT | 1-30592-7C111 | GJ080865 | 1,958 | 205 | $162,997.28 | Yes | TRUE | embed verbatim |
| **202607311107736000000001** | 27SLACT | 1-30592-7C111 | GJ080501 | 1,952 | 204 | $162,005.52 | Yes | TRUE | embed verbatim |
| **202607301107231000000012** | 27SLACT | 1-11651-7B113 | IJ075155 | 622 | 11 | $18,755.58 | Yes | TRUE | embed verbatim |
| **202607301107231000000002** | 27SLACT | 1-30231-7B115 | IJ075145 | 54 | 2 | $17.30 | Yes | TRUE | audit only, not re-captured (rule 12) |
| **202609111117326000000001** | 27SLACT | 1-16631-6D513 | (none in scope) | 2 | 0 | $0.00 | Yes | TRUE | embed verbatim |

## 202609031114916000000001 (GJ080865)

- **What the register could not answer:** Journal_Pull Tier A ranked document file 1260709 (GJ080865) first by value, $162,997.28 across 205 legs, and rated its pull value Low on the grounds that every leg already carries its own narration on the register, so a pull would add only the Council-side counterparty legs. What the register could not show was the other side: where the plant hire charge comes from, and whether the branch share is struck on usage or on a fixed rate.
- **What the document says:** The document is the Period 2 Plant and Fleet SLA hire allocation for the whole of Council. 1,958 legs, $1,908,235.69 on each side, netting to $0.00. The branch takes $162,997.28 across 17 cost centres on 7C111 Internal - Vehicle, each leg naming the plant unit it charges. The credit side sits on the internal plant revenue accounts 1-13001-6D312 ($1,296,010.21) and 1-13141-6D312 ($171,297.75), cleared through inter-entity accounts 1330-1-1ZZZZ and 4000-3-1ZZZZ, with the other Council ledgers 27PSLACT, 27RDCACT and 27RMACT taking their own shares on the same natural account.
- **Finding:** Read against the Period 1 document (cross reference 202607311107736000000001, GJ080501), the allocation is a fixed monthly charge per plant unit, not a usage-based recharge. Sixteen of the seventeen branch cost centres take an identical amount in both periods, to the cent, $161,013.76 in all. The seventeenth, 1-20181-7C111 Park Maintenance, moves by $991.76 and it moves only because its fleet changed: F007448 leaves ($704.32), F007447 drops from $895.60 to $223.90 on a part month, and F008907 ($1,160.10) and F008908 ($1,207.68) arrive, 68 plant units in Period 1 against 69 in Period 2. The consequence for reporting is that a 7C111 variance cannot be read as a usage signal: it moves only when a unit is added to or removed from the section's fleet.
- **Coverage:** Document file 1260709 carries one journal reference in the register, GJ080865, and this reconstruction reaches all 205 of its lines. The file is fully covered.
- **Tie GJ080865:** in-scope legs $162,997.28 against register net $162,997.28 on 205 lines, 205 matched: TRUE.
- **Counterparty legs (outside branch scope):** 1,753, totalling -$162,997.28 across 5 ledger(s): 27GLACT 7, 27PSLACT 203, 27RDCACT 49, 27RMACT 116, 27SLACT 1378.

## 202607311107736000000001 (GJ080501)

- **What the register could not answer:** Journal_Pull Tier A ranked document file 1253004 (GJ080501) second by value, $162,005.52 across 204 legs, on the same grounds as GJ080865: the counterparty legs are not on the register.
- **What the document says:** The document is the Period 1 Plant and Fleet SLA hire allocation, the Period 1 twin of GJ080865. 1,952 legs, $1,895,343.51 on each side, netting to $0.00. The branch takes $162,005.52 across the same 17 cost centres on 7C111 Internal - Vehicle. The credit side sits on the same internal plant revenue accounts, 1-13001-6D312 ($1,023,453.74) and 1-13141-6D312 ($435,771.57), with the same inter-entity clearing.
- **Coverage:** Document file 1253004 carries one journal reference in the register, GJ080501, and this reconstruction reaches all 204 of its lines. The file is fully covered.
- **Tie GJ080501:** in-scope legs $162,005.52 against register net $162,005.52 on 204 lines, 204 matched: TRUE.
- **Counterparty legs (outside branch scope):** 1,748, totalling -$162,005.52 across 5 ledger(s): 27GLACT 8, 27PSLACT 203, 27RDCACT 49, 27RMACT 118, 27SLACT 1370.

## 202607301107231000000012 (IJ075155)

- **What the register could not answer:** The open item "Journal pull taken with a Document filter" records that the Document Line Table pulled for document file 1252466 was taken with a Document filter, so it covered document 2 (IJ075145) and 2 of the file's 2,020 register lines, leaving the other seven journal references on the file unevidenced.
- **What the document says:** The document is the Council rates, utilities and fire levy charge for rating period 2027-1, segment S13. 622 legs, $720,178.85 on each side, netting to $0.00, credited in one line to 1330-1-11111 City Bank ($719,550.65) and charged across the internal utility accounts. The branch takes $18,755.58 on cost centre 20361 (Park Services), split across six natural accounts: 7B113 Internal - Water $9,404.03, 7B112 Internal - Water $5,861.16, 7B115 Internal - Garbage $2,013.75, 7B114 Internal - Sewerage $1,043.10, 7B121 $350.89 and 73422 Fire Levy $82.65. Every one of the 11 register lines on IJ075155 is matched leg for leg and the sum ties the register net exactly.
- **Coverage:** This reconstruction reaches IJ075155 only. With IJ075145 already embedded from the v6 Document Line Table pull, 2 of the 8 journal references the register carries on document file 1252466 are now evidenced. IJ075148, IJ075149, IJ075151, IJ075152, IJ075153 and IJ075154 remain, 2,007 register lines and $442,905.22, so the open item "Journal pull taken with a Document filter" is advanced and not closed.
- **Tie IJ075155:** in-scope legs $18,755.58 against register net $18,755.58 on 11 lines, 11 matched: TRUE.
- **Counterparty legs (outside branch scope):** 611, totalling -$18,755.58 across 2 ledger(s): 27GLACT 1, 27SLACT 610.

## 202607301107231000000002 (IJ075145)

- **What the register could not answer:** Whether a Document Reconstruction and a Document Line Table taken over the same journal agree, and whether the internal ledger account a reconstruction carries can be relied on to reach a register line.
- **What the document says:** The document is the rating period 2027-1 segment S03 charge, 54 legs, $34,505.71 each side, netting to $0.00, and the branch takes $17.30 on 73422 Fire Levy. It is the same document already embedded on Journal_Sources from the v6 Document Line Table pull of document file 1252466 document 2, so it is audited and not re-captured under rule 12.
- **Finding:** The audit proves the two export types are reconciled projections of one document: 54 legs in both, identical multiset of leg amounts, and the same two in-scope legs of $8.65 each. It also confirms the account crosswalk this batch relies on, because the Document Line Table prints those two legs on PK000092 / 73422 and the reconstruction prints them on 1-20361-73422. That is the evidence that a reconstruction leg can be mapped to a register line through the register's own Src Account column without inventing a crosswalk.
- **Coverage:** Reaches IJ075145 only, the same single reference the v6 pull reached. Document file 1252466 remains partly covered; see the open item "Journal pull taken with a Document filter" and the coverage note on cross reference 202607301107231000000012.
- **Rule 12 audit against the embedded Document Line Table:** 54 legs against 54 held, amounts identical True. same document as the Document Line Table already embedded on Journal_Sources (document file 1252466, LC_INTJN); audited and NOT re-captured (rule 12).
- **Tie IJ075145:** in-scope legs $17.30 against register net $17.30 on 2 lines, 2 matched: TRUE.
- **Counterparty legs (outside branch scope):** 52, totalling -$17.30 across 4 ledger(s): 27GLACT 1, 27RDCACT 2, 27RMACT 13, 27SLACT 36.

## 202609111117326000000001 (no in-scope reference)

- **What the register could not answer:** Journal_Pull Tier B lists document file 1256470 (IJ075271, 96 register lines, $9,365.00 on 7B214 Internal - Maintenance) as a document to sight rather than pull, so the register showed the branch side of the charge and nothing of where it went on the Council side.
- **What the document says:** The document is the counterparty transfer for IJ075271 and names it in its own narration, 'Transfer between Natural Account IJ075271'. It carries two legs and nothing else: a $9,365.00 debit to 1-16631-6D513 Internal Income and a $9,365.00 credit to 1-16631-6D421 Internal - Sales, netting to $0.00. The amount is the exact net of the 96 register lines on IJ075271.
- **Note:** Neither leg sits inside branch O110-O115, so this document evidences no register line of its own and adds none. It is retained because it is the only evidence held of the Council side of a Tier B document, and because it proves the $9,365.00 the branch was charged was recognised as internal income on a single cost centre rather than spread.
- **Counterparty legs (outside branch scope):** 2, totalling $0.00 across 1 ledger(s): 27SLACT 2.

## Open items raised

- **Plant hire SLA is a fixed monthly charge, not a usage recharge** (Branch-wide (17 cost centres on 7C111), 409 lines, $325,002.80): Record on the plant and fleet lines, and in any forecast built on 7C111, that the internal plant hire allocation is struck as a fixed monthly amount per plant unit and not on usage. Across Period 1 (GJ080501) and Period 2 (GJ080865) sixteen of the seventeen branch cost centres take an identical charge to the cent, $161,013.76 in all; only 1-20181-7C111 Park Maintenance moves, by $991.76, and only because two plant units left the section and two arrived. Confirm with Plant and Fleet that the SLA rate per unit is fixed for the year, and if it is, phase 7C111 on fleet composition rather than on season.
- **Document file 1252466 still only partly evidenced** (Park Services and branch-wide, 2007 lines, $442,905.22): Pull the remaining six journal references on document file 1252466: IJ075148 (2 lines, $33.15), IJ075149 (1,810 lines, $353,091.92), IJ075151 (33 lines, $6,384.51), IJ075152 (157 lines, $82,839.22), IJ075153 (4 lines, $491.42) and IJ075154 (1 line, $65.00). A Document Reconstruction keyed to each reference's own cross reference is the route that worked here; a Document Line Table taken with a Document filter is what left the file partly covered in the first place. This advances the open item "Journal pull taken with a Document filter" and does not close it.
