# Hold record: Credit_Card_-_Daniel_Harman.pdf

**Status: HELD. Cannot be captured, and not for want of effort.** This document cannot support a rule 17
green block, and no amount of re-extraction will change that. It is logged here so the decision is on the
record rather than repeated.

## 1.0 What it is

Two pages, image only. `pdffonts` reports no fonts and `pdftotext` returns nothing for either page, so
there is no text layer at all.

- **Page 1** is a handwritten **"Credit Card Cover Slip (submit with receipt in CIA)"**. Read at 200 dpi
  it returns "Banish Harman", "unrkenfe Qveorslord", "Ceag Loan" and similar. That is OCR failing on
  handwriting, not a capture.
- **Page 2** is a **payment confirmation screenshot**, not a tax invoice: OIR Workplace Health and Safety
  Queensland, Licencing and Registrations, Biller Code 1604628 (LARI HRW), Invoice No HRW359466, card
  number masked to 555005...099, **AUD 113.41** paid 13/07/2026 01:40 PM.

## 2.0 Why it cannot be captured

1. **It is not a tax invoice.** No supplier ABN is printed, there is no GST breakdown and there are no
   priced line records. The seven mandatory elements are not present, so there is nothing for the green
   block to carry and nothing for the provenance gate to trace a printed field back to.
2. **Handwriting defeats the OCR consensus rule.** `ocr_image_letterhead.py` accepts a value only where a
   300 dpi and a 400 dpi read agree character for character. That rule earns its place on printed
   letterheads. On handwriting the two reads will disagree, and a value this project cannot read twice
   the same way is one it does not know.
3. **It is a card transaction, not an AP-ledger supplier document.** Only AP and CT lines can be closed by
   sighting a supplier document; a corporate card payment reaches the ledger by another route entirely.

## 3.0 What it is good for, and the one thing to check

The page 2 screenshot is adequate **supporting evidence for a card acquittal**, which is what the cover
slip is for. It is not evidence of what the register calls Confirmed.

- **Open question, not resolved here: GST.** A Workplace Health and Safety Queensland licence or
  registration fee is an Australian government charge and is very likely GST-free under Division 81 of
  the GST Act. The screenshot shows a single figure of $113.41 with no tax line. If $113.41 has been
  coded as GST-bearing anywhere, the input tax credit claimed against it would be wrong. That is a coding
  question for the transaction in TechOne, not a capture question, and it needs the ledger line rather
  than this PDF.
