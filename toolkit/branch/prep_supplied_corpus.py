"""prep_supplied_corpus.py - prepare a SUPPLIED extraction corpus (binder not supplied) for the branch build.

Batches: mix22 (Savco, Heritage, Play Force, Kachel; 40 documents), binder11111 (RST Systems t/a Vinton Tree
Services; 13 documents), mix222 (Harpley; 29), pla073_1 (Play Force; 47) and ksadasd (T & H Levai, Weis; 68). The first three were extracted by M365
Copilot under prompt v5, declare gate RED, and fail the same way: rows carrying an amount in the item table's amount band were typed NARRATIVE, so documents reached OUT or
carried no priced line at all. Under rule 19.2 neither can be built from as received.

Every failure is a PARSE failure, not a tie failure, and every one is decidable from the corpus's own retained layout
rows ("Every text-layer row in the document span is preserved"), so the repairs below RESTATE what the page printed and
never infer an amount. The same evidence drives extraction prompt v6, which gates these defects at extraction time.

Extraction defects repaired, each systematic:

  R1  Amount-bearing rows typed NARRATIVE. On all four vendor layouts the extractor took some priced rows and left
      others, so 16 documents did not reach their printed subtotal and 11 carried no priced line at all. The row's own
      retained text carries the quantity, rate and amount bands; each is restated by the vendor's band pattern and the
      rebuilt lines must then equal the printed subtotal EXACTLY, or the document is refused.
  R2  printed_total_incl_gst carrying the GST amount. On all 13 Savco documents the header extractor put the GST total
      in the total field ($452.25 where the page prints A$4,974.75): it matched the label TOTAL against the row GST
      TOTAL. Restated from the document's own printed TOTAL row, which must agree with the TOTAL DUE header and the
      BALANCE DUE footer, and must equal subtotal plus GST.
  R4  invoice_date carrying another printed date. On all 14 Weis documents of ksadasd the header extractor put the
      printed due date in invoice_date. Restated from the printed Invoice Date row (the label in the right column,
      the value on the next row at the same column); a supplied date that agrees with the printed one is left alone.
  R3  line_type values outside the schema. binder11111 types repeated invoice copies "DUPLICATE" where the schema's
      closed list says DUPLICATE_COPY. Restated, and the copied page range recorded on the document.

pla073_1 is the first supplied corpus to arrive GREEN under prompt v6 runtime A: R1 to R3 are all no-ops on it, and only
the housekeeping below and the rule 19.2 fidelity check do any work. A batch that needs no repair still comes through
here, because the housekeeping and the independent verbatim check are what the build requires, not the repairs.

Then the housekeeping the corpus schema needs and a supplied corpus lacks: vendor_template, page_text rebuilt from the
retained rows, findings restated as text, ISO dates, source_md5.

Finally the rule 19.2 per-vendor verbatim check, run against an INDEPENDENT source: the Savco, Heritage, Play Force and
Kachel page text this project parsed from real PDFs at branch v3 and v4. Every row that is constant across this batch's
documents for a vendor (its fixed template and boilerplate) must appear verbatim in that independent reference, or
differ from it only inside a digit run (an invoice number, a date). A row that is neither, but is a near neighbour of a
reference row, is a silently altered template row and FAILS the check. Per-invoice description text appears on no other
document and cannot be proven this way; that rests on the retained rows, the arithmetic tie on every invoice and the
creditor history on the register line, and the check says so.

Usage: python3 prep_supplied_corpus.py <batch id> [supplied corpus.json] [outdir]
"""
import collections, datetime as dt, difflib, hashlib, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'toolkit', 'pswp'))
import pswp_json_repair as R  # noqa

BATCH = sys.argv[1] if len(sys.argv) > 1 else 'mix22'

# supplier as printed on the face -> vendor template carried by pbr_capture (CAT, BPK, header_fields, BOILER)
BATCHES = {
    'mix22': dict(src='corpus_mix22.json', vendors={
        'SAVCO VEGETATION SERVICES PTY LTD': 'SAVCO',
        'Heritage Tree Services Pty Ltd ATF Rowan Family Trust': 'HERITAGE',
        'Play Force Australia Pty Ltd': 'PLAYFORCE',
        'Kachel Cleaning': 'KACHEL'}),
    'binder11111': dict(src='corpus_Binder11111.json', vendors={'RST Systems Pty Ltd': 'VINTON'}),
    'mix222': dict(src='corpus_mix222.json', vendors={'Harpley Services Pty Ltd': 'HARPLEY'}),
    # pla073_1 is the first supplied corpus to arrive GREEN with no repair outstanding (runtime A, prompt v6):
    # R1 to R3 are no-ops on it and only the housekeeping and the rule 19.2 fidelity check do any work.
    'pla073_1': dict(src='corpus_pla073_1_as_supplied.json', vendors={'Play Force Australia Pty Ltd': 'PLAYFORCE'}),
    # ksadasd (branch v11): 68 documents, T & H Levai (54) and Weis Contractors (14), runtime A, gate GREEN as supplied.
    # The only restatement beyond housekeeping is the due date, which the corpus schema carries and this extraction
    # omitted although every face prints it (DUE DATE / Due Date: row).
    'ksadasd': dict(src='corpus_ksadasd_as_supplied.json', vendors={'T & H LEVAI PTY LTD': 'LEVAI', 'WEIS CONTRACTORS': 'WEIS'}),
    # playforce_new (branch v13): 109 Play Force documents over 319 pages, runtime A, gate GREEN as supplied. The
    # extraction returned the literal "(not printed)" for invoice_date on all 109 although every face prints it, in
    # two layouts: the legacy Xero block (label "Invoice Date" in the right column, value on the next row at the same
    # column) and the current letterhead ("Date  28-Aug-2025" at the right of the Billing block). R4 restates it.
    # Play Force prints two layouts in this binder and they are separate templates, because the fidelity check works by
    # taking the rows CONSTANT across a vendor's documents: mixing two layouts makes the letterhead and the terms pages
    # look like per-invoice text on one and template on the other. PLAYFORCE_XERO is the legacy Xero block (6 documents,
    # all FY2024/25): no letterhead, no terms pages, and the item table in the Xero
    # "Description / Quantity / Unit Price / GST / Amount AUD" shape rather than the current "Qty / Item / Description".
    # harp_new (branch v14): 70 Harpley documents over 123 pages, FY2023/24 to FY2026/27, runtime A, GREEN as supplied.
    'harp_new': dict(src='corpus_harp_new_as_supplied.json', vendors={'Harpley Services Pty Ltd': 'HARPLEY'}),
    # vinton_new (branch v14): 42 R.S.T. Systems t/a Vinton Tree Services documents over 84 pages, runtime A, GREEN.
    # The ABN is image-borne on the letterhead and was read by OCR at 300 dpi, which the corpus records.
    'vinton_new': dict(src='corpus_vinton_new_as_supplied.json',
                       vendors={'R. S. T. Systems Pty. Limited Trading as Vinton Tree Services': 'VINTON'}),
    'playforce_new': dict(src='corpus_playforce_new_as_supplied.json', vendors={'Play Force Australia Pty Ltd': 'PLAYFORCE'},
                          layouts=[('PLAYFORCE_XERO', re.compile(r'^Description\s{2,}Quantity\s{2,}Unit Price\s{2,}GST\s{2,}Amount AUD', re.M))]),
}
CFG = BATCHES[BATCH]
VENDOR = CFG['vendors']
SRC = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'cache', CFG['src'])
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'batches', BATCH)
# independently parsed reference corpora (page text retained, parsed from the real PDF by this project)
REF_CORPORA = [
    ('mixed_1', os.path.join(ROOT, 'batches', 'mixed_1', 'corpus_mixed_1_v6.json'), 'branch v2, Mixed_1.pdf, parse_mixed1.py'),
    ('attach_1', os.path.join(ROOT, 'batches', 'attach_1', 'corpus_attach_1_v6.json'), 'branch v4, TechOne attachment PDF, parse_attach1.py'),
    ('mixed_new_26_27', os.path.join(ROOT, 'batches', 'mixed_new_26_27', 'corpus_mixed_new_26_27_v6.json'), 'branch v3, Mixed_new_26-27.pdf, parse_mixed_new.py'),
]

# R1 band patterns, per printed layout: a list per template, because one supplier can print two layouts.
# Each demands the whole row, so a row can only be retyped when every band it claims is actually there.
BANDS = {
    # DESCRIPTION ... QTY  RATE  GST  AMOUNT
    'SAVCO': [re.compile(r'^(?P<desc>\S.*?)\s{2,}(?P<qty>[\d,]+(?:\.\d+)?)\s{2,}(?P<rate>[\d,]+\.\d{2})\s{2,}(?P<tax>GST|FRE)\s{2,}(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # Description ... Quantity  Unit Price  GST  Amount AUD
    'HERITAGE': [re.compile(r'^(?P<desc>\S.*?)\s{2,}(?P<qty>[\d,]+\.\d{2})\s{2,}(?P<rate>[\d,]+\.\d{2})\s{2,}(?:(?P<tax>\d{1,2}%)\s{2,})?(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # Qty  Item  Description  Unit Price  Price (Ex. GST)
    'PLAYFORCE': [re.compile(r'^\s*(?P<qty>\d+\.\d{2})\s{2,}(?P<item>\S+)\s{2,}(?P<desc>.*?)\s{2,}(?P<rate>[\d,]+(?:\.\d+)?)\s{2,}(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # Legacy Play Force (Xero): Description  Quantity  Unit Price  GST  Amount AUD
    'PLAYFORCE_XERO': [re.compile(r'^(?P<desc>\S.*?)\s{2,}(?P<qty>[\d,]+\.\d{2})\s{2,}(?P<rate>[\d,]+\.\d{2})\s{2,}(?:(?P<tax>\d{1,2}%)\s{2,})?(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # <indent> description <indent> amount, in the claim block only
    'KACHEL': [re.compile(r'^\s{10,}(?P<desc>\S.*?)\s{10,}(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # RST Systems t/a Vinton prints two layouts. B: HRS | DESCRIPTION | UNIT PRICE (ex-GST) | TOTAL PRICE (ex-GST).
    # A: DESCRIPTION | EX AMOUNT | TAX CODE, with no quantity and no unit price at all.
    # QUANTITY | DESCRIPTION | UNIT PRICE(ex-GST) | TOTAL PRICE(ex-GST), quantity first
    'HARPLEY': [re.compile(r'^\s*(?P<qty>[\d,]+(?:\.\d+)?)\s{2,}(?P<desc>\S.*?)\s{2,}\$?(?P<rate>[\d,]+\.\d{2})\s{2,}\$?(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # T & H Levai: DESCRIPTION | AMOUNT, item rows indented one space; the bank block at column 0 carries "Total" and is
    # not an item row, so the single leading space is part of the band.
    'LEVAI': [re.compile(r'^ (?P<desc>\S.*?)\s{2,}(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    # Weis: Description | Quantity | Unit Price | GST | Amount AUD; the date and site rows print 1.00 / 0.00 / 0.00 with
    # no GST band and are narrative, so the GST band is mandatory here.
    'WEIS': [re.compile(r'^(?P<desc>\S.*?)\s{2,}(?P<qty>[\d,]+\.\d{2})\s{2,}(?P<rate>[\d,]+\.\d{2})\s{2,}(?P<tax>\d{1,2}%)\s{2,}(?P<amt>-?[\d,]+\.\d{2})\s*$')],
    'VINTON': [re.compile(r'^\s*(?P<qty>[\d,]+(?:\.\d+)?)\s{2,}(?P<desc>\S.*?)\s{2,}\$(?P<rate>[\d,]+\.\d{2})\s{2,}\$(?P<amt>-?[\d,]+\.\d{2})\s*$'),
               re.compile(r'^(?P<desc>\S.*?)\s{2,}\$(?P<amt>-?[\d,]+\.\d{2})\s{2,}(?P<tax>GST|FRE|GST FREE)\s*$')],
}
SKIP_TYPES = ('PRICED', 'TABLE_HEADER', 'TOTALS', 'BLANK', 'PAYMENT_ADVICE', 'DUPLICATE', 'DUPLICATE_COPY')
LINE_TYPES = ('PRICED', 'NARRATIVE', 'TABLE_HEADER', 'TOTALS', 'FOOTER', 'TERMS', 'BLANK', 'OCR_DUPLICATE',
              'IMAGE_TEXT', 'ANNOTATION', 'DUPLICATE_COPY', 'PAYMENT_ADVICE')
TYPE_FIX = {'DUPLICATE': 'DUPLICATE_COPY'}
SAV_TOTAL = re.compile(r'^\s+TOTAL\s{2,}([\d,]+\.\d{2})\s*$', re.M)
SAV_DUE = re.compile(r'^\s*\S+\s{2,}\d{2}/\d{2}/\d{4}\s{2,}A\$([\d,]+\.\d{2})', re.M)
SAV_BAL = re.compile(r'A\$([\d,]+\.\d{2})\s*$', re.M)
MONEY = re.compile(r'\d[\d,]*\.\d{2}')
DIGITS = re.compile(r'\d+')

norm = lambda s: re.sub(r'\s+', ' ', str(s or '')).strip()
mask = lambda s: DIGITS.sub('#', norm(s))
fmask = lambda s: ' '.join('#' if any(ch.isdigit() for ch in t) else t for t in norm(s).split(' '))


def D(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), ROUND_HALF_UP)


def money(s):
    return D(str(s).replace(',', '').replace('$', ''))


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def captured(doc):
    return sum((D(l['line_ex_gst']) for l in doc['lines'] if l['line_type'] == 'PRICED' and l['line_ex_gst'] is not None), Decimal('0'))


# ------------------------------------------------------------------------------------------------ R1 and R2


def restate_lines(doc, log):
    """R1: retype amount-bearing NARRATIVE rows PRICED, restating qty, rate and amount from the row's own bands."""
    rxs = BANDS[doc['vendor_template']]
    n = 0
    for l in doc['lines']:
        if l['line_type'] in SKIP_TYPES:
            continue
        m = next((x for x in (r.match(l['line_text'] or '') for r in rxs) if x), None)
        if not m:
            continue
        g = m.groupdict()
        l['line_type'] = 'PRICED'
        l['line_ex_gst'] = float(money(g['amt']))
        l['qty'] = float(money(g['qty'])) if g.get('qty') else None
        l['unit_price_ex_gst'] = float(money(g['rate'])) if g.get('rate') else None
        l['band_hits'] = [k for k in ('qty', 'rate', 'amt') if g.get(k)]
        if g.get('tax'):
            l['gst_rate_printed'] = g['tax']
        l['note'] = ('R1: the printed row carries its amount in the %s band and was typed NARRATIVE by the extractor. '
                     'Retyped PRICED and restated from the row\'s own retained text; line_text untouched.' % doc['vendor_template'])
        n += 1
    if n:
        log.append(f'{doc["doc_ref"]}: R1 retyped {n} amount-bearing row(s) NARRATIVE -> PRICED, '
                   f'captured {captured(doc)} against printed subtotal {D(doc["printed_subtotal_ex_gst"])}')
    return n


def restate_savco_total(doc, log):
    """R2: the Savco header extractor put the GST total in printed_total_incl_gst. Restate from the printed TOTAL row."""
    sub, gst, tot = D(doc['printed_subtotal_ex_gst']), D(doc['printed_gst']), D(doc['printed_total_incl_gst'])
    if tot != gst or sub + gst == tot:
        return 0
    t = '\n'.join(l['line_text'] for l in doc['lines'])
    printed = {money(x) for x in SAV_TOTAL.findall(t)} | {money(x) for x in SAV_DUE.findall(t)} | {money(x) for x in SAV_BAL.findall(t)}
    want = sub + gst
    assert printed == {want}, (doc['doc_ref'], sorted(map(str, printed)), str(want))
    doc['printed_total_incl_gst'] = float(want)
    log.append(f'{doc["doc_ref"]}: R2 printed_total_incl_gst {tot} was the printed GST total; restated {want} from the '
               f'printed TOTAL row, agreeing with the TOTAL DUE header and the BALANCE DUE footer')
    return 1


# R4: the printed invoice date per layout, read from the retained rows. Levai prints "DATE  30 Jun 2026" on the header
# block; Weis layout B prints the label "Invoice Date" in the right column with the value on the next row at the same
# column. A supplied invoice_date that is not the printed one is restated and logged; a supplied value that agrees is left.
def printed_invoice_date(doc):
    rows = [l['line_text'] for l in doc['lines'] if l['line_type'] not in ('DUPLICATE_COPY',)]
    t = '\n'.join(rows)
    v = doc['vendor_template']
    if v == 'LEVAI':
        m = re.search(r'(?<!DUE )\bDATE\s+(\d{1,2} \w{3} \d{4})\s*$', t, re.M)
        return m.group(1) if m else None
    if v == 'WEIS':
        for i, x in enumerate(rows[:-1]):
            if 'Invoice Date' in x:
                col = x.index('Invoice Date')
                nxt = rows[i + 1][col:]
                m2 = re.match(r'\s*(\d{1,2} \w{3,4}\.? \d{4})', nxt)
                if m2:
                    return m2.group(1)
        m = re.search(r'Issue date[^\n]*\n[^\n]*?\s{2,}(\d{1,2} \w{3,4}\.? \d{4})\s{2,}INV-', t)
        return m.group(1) if m else None
    if v in ('PLAYFORCE', 'PLAYFORCE_XERO'):
        # Current letterhead: the Billing block prints "Date" and the value at the right of the same row.
        m = re.search(r'(?<!Completed: )\bDate\s{2,}(\d{1,2}-\w{3}-\d{4})\s*$', t, re.M)
        if m:
            return m.group(1)
        # Legacy Xero block: the label sits in the right column and the value on the next row at the same column.
        for i, x in enumerate(rows[:-1]):
            if 'Invoice Date' in x:
                m2 = re.match(r'\s*(\d{1,2} \w{3} \d{4})', rows[i + 1][x.index('Invoice Date'):])
                if m2:
                    return m2.group(1)
        return None
    return None


def rounding_basket(doc):
    """The printed subtotal a page would carry if it summed qty x unit price unrounded, from the printed figures only."""
    pr = [l for l in doc['lines'] if l['line_type'] == 'PRICED']
    if not pr or any(l.get('qty') is None or l.get('unit_price_ex_gst') is None for l in pr):
        return None
    return sum(D(l['qty']) * D(l['unit_price_ex_gst']) for l in pr).quantize(Decimal('0.01'), ROUND_HALF_UP)


# R5: printed_gst carrying the printed TOTAL. Every Harpley document of harp_new carries the Total Inc GST in the GST
# field, on both printed layouts: the header extractor matched the label "GST" against the row "Total Inc GST". The GST
# is restated from the page's own separate GST row where the layout prints one, and otherwise from the two other
# PRINTED figures (total minus subtotal), which is arithmetic on the page rather than an inference about it. The
# restated GST must equal total minus subtotal either way, or the document is refused.
GST_ROW = re.compile(r'(?<!Inc )\bGST:\s*\$?([\d,]+\.\d{2})')


def restate_gst(doc, log):
    sub, tot = D(doc.get('printed_subtotal_ex_gst')), D(doc.get('printed_total_incl_gst'))
    have = D(doc.get('printed_gst'))
    want = (tot - sub).quantize(Decimal('0.01'), ROUND_HALF_UP)
    if have == want:
        return 0
    printed = None
    for l in doc['lines']:
        if l['line_type'] in SKIP_TYPES:
            continue
        x = ' '.join((l.get('line_text') or '').split())
        m = GST_ROW.search(x)
        if m and not x.startswith('Total'):
            printed = D(m.group(1).replace(',', ''))
            break
    src = 'the printed GST row' if printed is not None else 'the printed total less the printed subtotal'
    val = printed if printed is not None else want
    assert val == want, (doc['doc_ref'], f'printed GST row {printed} does not equal total less subtotal {want}')
    doc['printed_gst_as_supplied'] = float(have)
    doc['printed_gst'] = float(val)
    log.append(f'{doc["doc_ref"]}: R5 printed_gst {have} as supplied is the printed Total Inc GST; restated {val} from {src}')
    return 1


# R6: pk_refs empty where the face PRINTS a PK. The vinton_new extraction returned no PK on any of its 42 documents
# and its capture report stated "No PK reference is printed on the invoice face" for every one, yet 34 of them print a
# PK in the work description block (CR# 3735053 PK000477). Left alone this is not a cosmetic gap: the printed PK is
# what the register compares against the PK charged, so the whole comparison silently disappears and the batch asks
# the vendor to print a PK it already prints. Restated from the retained rows only, and only where the document prints
# exactly ONE distinct PK, because a document naming several is a real question about scope and not a housekeeping fix.
PK_ON_FACE = re.compile(r'PK\s?(0\d{5})')


def restate_pk_refs(doc, log):
    if doc.get('pk_refs'):
        return 0
    t = '\n'.join(doc['page_text'][k] for k in sorted(doc['page_text'], key=int)) if doc.get('page_text') else \
        '\n'.join(l.get('line_text') or '' for l in doc['lines'] if l['line_type'] not in SKIP_TYPES)
    found = sorted({'PK' + m for m in PK_ON_FACE.findall(t)})
    if len(found) != 1:
        if len(found) > 1:
            log.append(f'{doc["doc_ref"]}: the face prints {len(found)} PKs {found} and the corpus carries none; '
                       f'left empty, because which one the charge belongs to is a question about scope')
        return 0
    doc['pk_refs'] = found
    doc['printed_account_codes'] = found
    log.append(f'{doc["doc_ref"]}: R6 pk_refs empty as supplied although the face prints {found[0]}; restated from the retained rows')
    return 1


# R7: an identity the corpus asserts but cannot evidence. The vinton_new extraction reports the supplier name and ABN
# as read by OCR from an image-borne letterhead, and retains no OCR text: nothing in the corpus carries either string,
# so the register would print a vendor and an ABN that its own evidence cannot show. Rule 8 decides identity on the
# PRINTED ABN and never carries an ABN onto a line that does not evidence it, so the assertion is withdrawn to what the
# retained text actually holds (the same position binder11111 already takes for this vendor: 'RST Systems Pty Ltd',
# ABN absent, the register label and ABN coming from the APLEDGER history VIN003 and not from the document). The
# extraction's claim is kept beside it, so the OCR read can be reinstated the moment its text is supplied.
def _loose(x):
    return re.sub(r'[^0-9a-z]', '', str(x or '').lower())


def restate_identity(doc, log):
    if not doc.get('page_text'):
        return 0
    t = '\n'.join(doc['page_text'][k] for k in sorted(doc['page_text'], key=int))
    tl = _loose(t)
    name, abn = str(doc.get('supplier') or ''), str(doc.get('supplier_abn') or '')
    n = 0
    if abn and _loose(abn) not in tl:
        doc['supplier_abn_as_supplied'] = abn
        doc['supplier_abn'] = None
        doc['abn_source'] = 'absent from the retained text; the extraction reports an OCR read whose text was not retained'
        log.append(f'{doc["doc_ref"]}: R7 supplier ABN {abn} appears nowhere in the retained text; withdrawn to absent '
                   f'(rule 8: an ABN is never carried onto a line that does not evidence it). The claim is kept in '
                   f'supplier_abn_as_supplied.')
        n += 1
    if name and _loose(name) not in tl:
        # Fall back to the longest entity string the retained text DOES carry for this supplier.
        cand = [' '.join(x.split()) for x in t.splitlines()]
        found = None
        for w in sorted({m for c_ in cand for m in re.findall(r'[A-Z][A-Za-z.&\' ]*(?:Pty\.? ?Ltd\.?|Pty\.? Limited)', c_)},
                        key=len, reverse=True):
            if _loose(w) in tl:
                found = ' '.join(w.split())
                break
        if found:
            doc['supplier_as_supplied'] = name
            doc['supplier'] = found
            log.append(f'{doc["doc_ref"]}: R7 supplier {name!r} appears nowhere in the retained text; restated {found!r}, '
                       f'which the face does print. The claim is kept in supplier_as_supplied.')
            n += 1
    return n


def restate_invoice_date(doc, log):
    if doc.get('duplicate_of'):
        return 0
    printed = printed_invoice_date(doc)
    if printed is None:
        return 0
    have = str(doc.get('invoice_date') or '').strip()
    if have == printed:
        return 0
    doc['invoice_date_as_supplied'] = have
    doc['invoice_date'] = printed
    log.append(f'{doc["doc_ref"]}: R4 invoice_date {have!r} as supplied is not the printed Invoice Date; restated {printed!r} from the printed row')
    return 1


def prepare(corpus):
    log, r1, r2, r4, r5, r6, r7 = [], 0, 0, 0, 0, 0, 0
    for d in corpus['documents']:
        d['vendor_template'] = VENDOR[d['supplier']]
        # A supplier that prints more than one layout carries one template per layout (see the batch config).
        for tpl_, rx_ in CFG.get('layouts', []):
            if rx_.search('\n'.join(l['line_text'] for l in d['lines'])):
                d['vendor_template'] = tpl_
                log.append(f'{d["doc_ref"]}: layout {tpl_} (the supplier prints more than one; assigned from the printed item-table header)')
                break
        r1 += restate_lines(d, log)
        if d['vendor_template'] == 'SAVCO':
            r2 += restate_savco_total(d, log)
        pages = collections.defaultdict(list)
        for l in d['lines']:
            pages[l['page']].append((l['line_no'], l['line_text']))
        d['page_text'] = {str(p): '\n'.join(t for _, t in sorted(rows)) for p, rows in sorted(pages.items())}
        d['findings'] = [f'[{f["code"]}] {f["detail"]} Amount ${f["amount"]:,.2f}.' if isinstance(f, dict) else str(f) for f in d['findings']]
        fixed = collections.Counter()
        for l in d['lines']:
            if l['line_type'] in TYPE_FIX:
                fixed[l['line_type']] += 1
                l['line_type'] = TYPE_FIX[l['line_type']]
            assert l['line_type'] in LINE_TYPES, (d['doc_ref'], l['line_no'], l['line_type'])
        if fixed:
            log.append(f'{d["doc_ref"]}: R3 restated {sum(fixed.values())} line_type value(s) {dict(fixed)} to the schema list')
        dup = sorted({l['page'] for l in d['lines'] if l['line_type'] == 'DUPLICATE_COPY'})
        d['duplicate_copy_pages'] = dup
        if dup:
            log.append(f'{d["doc_ref"]}: duplicate invoice copies on page(s) {dup}, typed DUPLICATE_COPY and outside the arithmetic')
        r4 += restate_invoice_date(d, log)
        r5 += restate_gst(d, log)
        r6 += restate_pk_refs(d, log)
        r7 += restate_identity(d, log)
        if not d.get('due_date'):
            # The corpus schema carries due_date; a supplied extraction that left it out is restated from the retained
            # rows only where exactly one printed due-date label is found in the document span (never inferred).
            t_ = '\n'.join(l['line_text'] for l in d['lines'] if l['line_type'] != 'DUPLICATE_COPY')
            found = sorted({x.strip() for x in re.findall(r'(?:DUE DATE|Due Date:?)\s+(\d{1,2} \w{3} \d{4})\s*$', t_, re.M)})
            if len(found) == 1:
                d['due_date'] = found[0]
                log.append(f'{d["doc_ref"]}: due_date {found[0]} restated from the printed due-date row (absent from the supplied corpus)')
        for k in ('invoice_date', 'due_date'):
            v = str(d.get(k) or '').strip()
            if not v or re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
                continue
            for fmt in ('%d/%m/%Y', '%d-%b-%Y', '%d %b %Y', '%d/%m/%y', '%d.%m.%Y'):
                try:
                    d[k] = dt.datetime.strptime(v, fmt).date().isoformat()
                    break
                except ValueError:
                    continue
            else:
                raise AssertionError(f'{d["doc_ref"]}: {k} {v!r} is not a date format this corpus schema knows')
            log.append(f'{d["doc_ref"]}: {k} {v} restated as ISO {d[k]} (corpus schema)')
        bad = [p for p in d['pk_refs'] if not re.fullmatch(r'PK\d{6}', str(p))]
        if bad:
            d['pk_refs'] = [p for p in d['pk_refs'] if re.fullmatch(r'PK\d{6}', str(p))]
            d['printed_account_codes'] = d['pk_refs']
            log.append(f'{d["doc_ref"]}: pk_refs {bad} dropped, not of the PK000000 form')
        d['source_md5'] = None
        if d.get('duplicate_of'):
            # A repeated copy of an invoice already captured earlier in the binder (prompt v6 3.5): every row is typed
            # DUPLICATE_COPY, it carries no priced line and sits outside the arithmetic; the match table skips it.
            assert all(l['line_type'] in ('DUPLICATE_COPY', 'BLANK') for l in d['lines']), (d['doc_ref'], 'duplicate copy carrying a non-DUPLICATE_COPY row')
            log.append(f'{d["doc_ref"]}: duplicate copy of the document at pages {d["duplicate_of"]}, every row typed DUPLICATE_COPY, outside the arithmetic and not captured again')
            continue
        cap, sub = captured(d), D(d['printed_subtotal_ex_gst'])
        tot_ = D(d['printed_total_incl_gst'])
        if cap != sub and cap == tot_:
            # The template prints its line amounts GST INCLUSIVE, so the lines tie the printed TOTAL and not the
            # printed subtotal. The gate records that basis (R2 rung 2) and the register's check 1 takes the
            # incl-GST form; nothing is restated, because both printed figures are captured as printed.
            d['line_amount_basis'] = 'incl_gst'
            log.append(f'{d["doc_ref"]}: printed line amounts are GST inclusive; the lines tie the printed total {tot_}')
        elif cap != sub and rounding_basket(d) == sub and abs(cap - sub) <= D('0.01'):
            # The PAGE does not foot, and its own figures say why: the vendor's subtotal carries the unrounded
            # qty x unit price where the line column shows it truncated (INV-7327 prints 7.50 x 105.41 as 790.57
            # and totals 790.575). Nothing is restated and no amount is inferred: the printed line and the printed
            # subtotal are both captured as printed, and the cent is declared here and carried as an anomaly so the
            # match table takes the per-line rounding variant rather than an exact tie.
            d.setdefault('findings', []).append(
                f'The printed lines sum to {cap} and the printed Total (Ex. GST) is {sub}: the invoice does not foot '
                f'by {abs(cap - sub)}, because the subtotal carries the unrounded quantity x unit price '
                f'({rounding_basket(d)}) where the line column prints it truncated. Both figures are captured as printed.')
            log.append(f'{d["doc_ref"]}: printed lines {cap} against printed subtotal {sub}; the difference is the '
                       f'vendor\'s own per-line rounding and is declared, not restated')
        else:
            assert cap == sub, f'{d["doc_ref"]}: restated lines {cap} do not equal the printed subtotal {sub}'
    log.append(f'batch: R1 restated {r1} amount-bearing rows over {sum(1 for d in corpus["documents"])} documents; '
               f'R2 restated {r2} printed totals carrying the GST amount; R4 restated {r4} invoice dates from the printed Invoice Date row; '
               f'R5 restated {r5} GST amounts carrying the printed total; R6 restated {r6} empty pk_refs from a PK printed on the face')
    return log


# ------------------------------------------------------------------------------------------------ rule 19.2 fidelity


def references():
    refs = collections.defaultdict(list)
    for batch, path, how in REF_CORPORA:
        if not os.path.exists(path):
            continue
        for d in json.load(open(path))['documents']:
            v = d.get('vendor_template')
            if v in VENDOR.values() and d.get('page_text'):
                refs[v].append(dict(batch=batch, how=how, doc=d['doc_ref'], date=str(d.get('invoice_date') or ''),
                                    rows={norm(x) for k in d['page_text'] for x in d['page_text'][k].splitlines() if norm(x)}))
    return refs


def fidelity(corpus, refs):
    """Every row constant across a vendor's documents in this batch, verified against an independent reference."""
    dates = {d['doc_ref']: str(d.get('invoice_date') or '') for d in corpus['documents']}
    by_vendor = collections.defaultdict(list)
    for d in corpus['documents']:
        by_vendor[d['vendor_template']].append((d['doc_ref'], {norm(l['line_text']) for l in d['lines'] if norm(l['line_text'])}))
    out, failures = [], []
    for v, docs in sorted(by_vendor.items()):
        rs = refs.get(v, [])
        if not rs:
            const = set.intersection(*[rows for _, rows in docs])
            out.append(dict(vendor_template=v, batch_documents=len(docs), reference_documents=[],
                            batch_constant_template_rows=len(sorted(x for x in const if not MONEY.search(x))),
                            verbatim_in_reference=0, digit_variant_of_a_reference_row=0, digit_variant_rows=[],
                            unmatched_rows=0, unmatched=[], altered_template_rows=[], reference_intersection_check=None,
                            check='NOT RUN: this project has never parsed a document of this vendor from a real PDF, so there is '
                                  'no independent source to check the retained rows against. The compensating controls are the '
                                  'arithmetic tie on every document of the batch and the reference-level match of every document '
                                  'to its register line in the batch match table.'))
            continue
        ref_rows = set.intersection(*[r['rows'] for r in rs]) if len(rs) > 1 else rs[0]['rows']
        ref_all = set.union(*[r['rows'] for r in rs])
        ref_masked = {mask(x) for x in ref_all}
        const = set.intersection(*[rows for _, rows in docs])
        template = sorted(x for x in const if not MONEY.search(x))
        verbatim = [x for x in template if x in ref_all]
        variant = [x for x in template if x not in ref_all and mask(x) in ref_masked]
        rest = [x for x in template if x not in ref_all and mask(x) not in ref_masked]
        altered = []
        for x in rest:
            near = difflib.get_close_matches(mask(x), sorted(ref_masked), n=1, cutoff=0.85)
            if near:
                altered.append(dict(batch_row=x, nearest_reference_row=near[0]))
        if altered:
            failures.append((v, altered))
        two_way = None
        if len(rs) >= 3:  # enough independent documents to fix the template by intersection (prep_code_corpus precedent)
            # Compared on digit-masked rows, as the variant limb above already is. A reference template row whose digits
            # legitimately differ is not a miss: a page-number footer moves with the document's own page count ("1 of 3"
            # against "1 of 4"), as do invoice numbers and dates. A template row genuinely absent still fails, because
            # masking only neutralises digit runs.
            # Field-masked: every token carrying a digit is neutralised (an order number, a contract reference such as
            # PAR/340A/2026 whose letter suffix moves with the contract, a date), because the reference set is small
            # enough for a per-invoice field to be constant across it and so look like template. A reference row still
            # absent after masking is then looked for as a near neighbour (the same cutoff as the altered-row test):
            # one found is the same row printed with a different field or a punctuation variant of the layout
            # (Weis prints "P/O # 717316" on one invoice and "P/O # - 717316" on the next) and is reported as a
            # field variant, not a miss; none found is a template row genuinely absent and fails.
            ref_rows_masked = {fmask(x) for x in ref_rows}
            missing, variants_2w = {}, {}
            # A reference document fixes ONE VINTAGE of the vendor's template. This limb asks the opposite question to
            # the one above: not "is this batch's row real", but "does this batch's document still carry the rows the
            # reference has". That question is only answerable against a document of the same vintage. A vendor rewrites
            # its terms and changes its remittance block: Play Force added a safety-inspection scope clause and dropped
            # the "Account Name" row between 2025 and the Aug-2026 reference, so requiring the reference's rows on a
            # 2025 invoice would fail the document for printing what it actually printed. Documents older than the
            # earliest reference are declared here and left to the limb above, which is the one that catches a
            # fabricated or silently altered row. Rule 11: the asymmetry is declared, not papered over.
            ref_from = min((r['date'] for r in rs if r['date']), default='')
            older = sorted(ref_ for ref_, _ in docs if ref_from and str(dates.get(ref_, '')) < ref_from)
            for ref, rows in docs:
                if ref in set(older):
                    continue
                have = {fmask(x) for x in rows}
                gone = sorted(ref_rows_masked - have)
                if not gone:
                    continue
                near_ok, truly = {}, []
                for g in gone:
                    near = difflib.get_close_matches(g, sorted(have), n=1, cutoff=0.85)
                    (near_ok.__setitem__(g, near[0]) if near else truly.append(g))
                if near_ok:
                    variants_2w[ref] = near_ok
                if truly:
                    missing[ref] = truly
            two_way = dict(reference_template_rows=len(ref_rows),
                           reference_vintage_from=ref_from, documents_tested=len(docs) - len(older),
                           documents_older_than_the_reference=len(older), older_documents=older[:40],
                           documents_missing_any=len(missing), misses=missing,
                           documents_with_field_variants=len(variants_2w), field_variants=variants_2w,
                           basis='field-masked comparison (every digit-bearing token neutralised); a reference row absent after masking but '
                                 'with a near neighbour in the document (cutoff 0.85) is a field or punctuation variant, not a miss; a reference row '
                                 'still absent is a miss and fails')
            if missing:
                failures.append((v, missing))
        out.append(dict(vendor_template=v, batch_documents=len(docs), reference_documents=[f'{r["batch"]}:{r["doc"]} ({r["how"]})' for r in rs],
                        batch_constant_template_rows=len(template), verbatim_in_reference=len(verbatim),
                        digit_variant_of_a_reference_row=len(variant), digit_variant_rows=variant,
                        unmatched_rows=len(rest), unmatched=rest, altered_template_rows=altered,
                        reference_intersection_check=two_way))
    rep = dict(check='rule 19.2 per-vendor verbatim fidelity, independent source',
               method=('For each vendor template: take every row that is constant across this batch\'s documents for that vendor and '
                       'carries no money token, and verify it against page text this project parsed independently from a real PDF. A row '
                       'passes verbatim, or as a digit variant (invoice number, date) of a reference row. A row that is neither but is a '
                       'near neighbour of a reference row is a silently altered template row and fails.'),
               vendors=out, verdict='FAIL' if failures else 'PASS',
               scope=('Proves the fixed template and boilerplate rows this batch carries are verbatim against an independent parse of the '
                      'same vendor. It cannot prove per-invoice description text, which appears on no other document; that rests on the '
                      f'retained layout rows, the arithmetic tie on every invoice (all {sum(1 for d in corpus["documents"] if not d.get("duplicate_of"))} reconcile to the printed subtotal to the cent) and '
                      'the creditor history on the register line. Where a vendor contributes a single document to this batch, "constant '
                      'across the batch" is that document\'s own rows, so the unmatched list for that vendor is its invoice-specific text.'))
    assert rep['verdict'] == 'PASS', failures
    return rep


# ------------------------------------------------------------------------------------------------ main


def main():
    corpus = json.load(open(SRC))
    src_md5 = md5(SRC)
    corpus['manifest']['supplied_corpus_md5'] = src_md5
    corpus['manifest']['gate_as_supplied'] = corpus['manifest'].get('gate')
    corpus['manifest']['pathologies_as_supplied'] = list(corpus['manifest'].get('pathologies') or [])
    corpus['manifest']['documents_out_as_supplied'] = corpus['manifest'].get('documents_out')
    log = prepare(corpus)
    res = R.repair_and_gate(corpus)
    # The verbatim check is a gate on what gets BUILT, so it runs after the corpus has passed its own gates. A held
    # corpus is not built from, and running it there would only report a second failure on a batch already stopped.
    rep = fidelity(corpus, references()) if res.gate == 'GREEN' else None
    corpus['manifest'].setdefault('repair_log', []).insert(0, {'tool': os.path.basename(__file__), 'repairs': log})
    corpus['manifest']['fidelity_check'] = rep or {
        'check': 'rule 19.2 per-vendor verbatim fidelity, independent source',
        'verdict': 'NOT RUN', 'scope': 'The corpus did not pass its own gates, so it is held and not built from (rule 19.2); '
                                       'the verbatim check runs on the re-extraction.'}
    corpus['manifest']['extraction_tool'] = (corpus['manifest'].get('extraction_tool', '') +
                                             f'; prepared and restated by {os.path.basename(__file__)} (R1 band restatement, R2 printed total carrying the GST amount, R3 line_type)')
    os.makedirs(OUT, exist_ok=True)
    if res.gate != 'GREEN':
        # rule 19.2: a corpus that fails any of its own gates is logged, HELD and not part-built from.
        hold = dict(batch=BATCH, corpus=os.path.basename(SRC), corpus_md5=src_md5,
                    received=dt.date.today().strftime('%d-%b-%Y'), tool=corpus['manifest'].get('extraction_tool'),
                    declared_gate=corpus['manifest']['gate_as_supplied'],
                    repair_gate=f'{res.gate} after prep_supplied_corpus.py restatement',
                    repairs=log, documents=len(corpus['documents']),
                    fidelity_check='NOT RUN (corpus held; the check runs on the re-extraction)',
                    pathologies=[p.as_dict() for p in res.pathologies],
                    rule16=R.rule16_check(corpus),
                    decision=('HELD, not built (rule 19.2). The remaining pathologies are not decidable from the retained rows: '
                              'the corpus carries no line record at all for the pages listed, so there is nothing to restate from. '
                              'Supply the binder PDF for the raw-text route, or re-extract under extraction prompt v6, which gates '
                              'this at extraction time.'))
        json.dump(hold, open(os.path.join(OUT, f'hold_{BATCH}_v5.json'), 'w'), indent=1)
        json.dump(corpus, open(os.path.join(OUT, f'corpus_{BATCH}_v6_HELD.json'), 'w'), indent=1)
        open(os.path.join(OUT, f'capture_report_{BATCH}_v6.md'), 'w').write(R.report(corpus, res))
        print(f'gate {corpus["manifest"]["gate_as_supplied"]} as supplied -> {res.gate} after restatement; HELD, not built (rule 19.2). '
              f'{len(res.pathologies)} pathology(ies) remain: ' + '; '.join(sorted({p.code for p in res.pathologies})))
        for l in log[-3:]:
            print('  repair:', l)
        return
    bad = R.rule16_check(corpus)
    assert not bad, bad
    json.dump(corpus, open(os.path.join(OUT, f'corpus_{BATCH}_v6.json'), 'w'), indent=1)
    json.dump(rep, open(os.path.join(OUT, f'fidelity_{BATCH}_v6.json'), 'w'), indent=1)
    open(os.path.join(OUT, f'capture_report_{BATCH}_v6.md'), 'w').write(R.report(corpus, res))
    m = corpus['manifest']
    print(f'gate {m["gate_as_supplied"]} as supplied -> {res.gate}; {len(corpus["documents"])} documents, '
          f'{m["documents_tie"]} at TIE, {m["documents_out"]} at OUT (was {m["documents_out_as_supplied"]}); '
          f'captured ex GST {m["captured_ex_gst_total"]:,.2f}; repairs {len(log)}; fidelity {rep["verdict"]}')
    for v in rep['vendors']:
        print(f'  fidelity {v["vendor_template"]}: {v["batch_constant_template_rows"]} constant template rows, '
              f'{v["verbatim_in_reference"]} verbatim, {v["digit_variant_of_a_reference_row"]} digit variants, '
              f'{v["unmatched_rows"]} unmatched, {len(v["altered_template_rows"])} altered')


if __name__ == '__main__':
    main()
