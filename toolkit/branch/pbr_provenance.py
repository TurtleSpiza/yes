"""pbr_provenance.py - the green block must come from the document it cites.

THE HOLE THIS CLOSES. The chain proves two things about a sighted invoice and neither of them is what the green
block mostly holds. `pswp_json_repair` proves the ARITHMETIC: captured lines equal the printed subtotal to the cent,
the header block adds up, the residue test is empty. `pswp_shingle_check` proves the WORDING of the priced rows:
every five-word shingle of a PRICED description appears in that document's own retained page text. Neither looks at
the printed header fields, and those are most of the green block: the vendor address, the phone block, the purchase
order, the contract, the bill-to, the requesting officer, the CR/WO number, the site, the work description and the
printed PK. Nothing compared them to the document.

The cost of that was nine versions of a wrong answer. `header_fields` read Levai by fixed string, so every Levai
invoice from branch v2 to v10 carried "Spring Mountain Reserve (Ref: 35715) - Bush Track Repair & Drainage Works"
as its site and work description, whatever the invoice actually said. Five captures shipped wrong. Every gate
returned GREEN the whole time, because the money was right to the cent and the priced-line shingles matched.

THE CHECK. Every printed field written to the green block must be traceable to the retained page text of the
document it cites. Tracing runs as a LADDER and the rung a field passes on is recorded, because the rungs are not
equally strong and pretending they are would hide the weak ones:

    verbatim      the whole value appears in the page text, whitespace normalised
    component     every part does, splitting on the separators the driver composes with ( | and ; and , )
    label         every part does once a fragment is split from its own label, which is the two-column case: an
                  invoice printing "Bill To:" and "Ship To:" beside each other prints neither label next to its
                  own value, so "Ship To: Logan City Council" is a correct reading that appears nowhere as text
    gloss         every part does once a trailing parenthetical is stripped, which is the project's own comment
                  on what it read ("Sara Pryor (customer contact)") and not a claim about the page
    tokens        every distinctive word of the value appears somewhere on the page, which is the reassembled
                  case: a value the driver rebuilt from rows that the page prints in separate columns
    declared      the value is one of the declared evidence states listed in DECLARED, which say in terms that
                  the page prints no single value ("Multiple parks, one printed per line")
    placeholder   "(not printed)", "(blank as printed)", "undefined (as printed)"

A field that reaches no rung is either invented or carried from another document, and the build stops rather than
shipping it. The counts per rung are reported on every build, so a drift from verbatim towards tokens is visible.

WHAT IS DELIBERATELY NOT CHECKED, and why. Dates (cols 94, 95) are reformatted to the register's own D-Mon-YYYY on
the way in, so a substring test would fail on every document; they are already tied to the corpus, which is gated
against the page. The money columns (113 to 115) are the printed subtotal, GST and total, which rule 16(b) already
reconciles to the captured lines to the cent, and the three live rule 17 checks re-prove on the register itself.
The structural columns (the evidence id, the line count, the boilerplate keys, the page span, the source stamp and
the anomalies note) are this project's own text about the document, not the document's text, and saying they do not
appear on the invoice is the point of them.

This is a completeness check on provenance, not on meaning. It proves a field came from the document. It cannot
prove the field is the RIGHT part of the document, so a reader that picks the wrong line still passes if that line
is really there. That limit is stated rather than papered over: what it removes is the whole class of failure where
a value is a constant, a leftover, or a value belonging to another invoice.
"""
import collections, re

# Columns the driver fills with text the document printed. Numbers beside each are the register column.
FIELDS = {
    89: 'Ev Vendor (printed)', 90: 'Ev ABN (printed)', 92: 'Ev Vendor address (printed)',
    93: 'Ev Vendor phone (printed)', 96: 'Ev Purchase Order (printed)', 97: 'Ev Contract # (printed)',
    98: 'Ev Bill To (printed)', 100: 'Ev Requesting Officer (printed)', 101: 'Ev Request Date (printed)',
    102: 'Ev Request Via (printed)', 103: 'Ev CR/WO # (printed)', 104: 'Ev PK # (as printed)',
    106: 'Ev Site Details (printed)', 107: 'Ev Site Contact (printed)', 108: 'Ev Work Description (printed)',
    109: 'Ev Technician (printed)', 111: 'Ev Line items (printed, verbatim)', 116: 'Ev Payments Made (printed)',
    117: 'Ev Balance Due (printed)',
}
# Compared on alphanumerics alone: the register carries the grouped form and the page may print either
# (Savco prints 78161366749 where the register carries 78 161 366 749).
LOOSE = {90, 104}
PLACEHOLDERS = {'(not printed)', '(blank as printed)', 'undefined (as printed)', '(none printed)'}
PLACEHOLDERS = {p.lower() for p in PLACEHOLDERS} | PLACEHOLDERS
# The separators the driver composes with. A composed value passes when every component of it does.
SPLITS = (' | ', '; ', ', ')
MIN_LEN = 4        # a fragment shorter than this is not probative on its own
WS = re.compile(r'\s+')
ITEM_NO = re.compile(r'(?:^|\s)\d{1,3}\.\s')
TRIM = re.compile(r'^[\s,;|]+|[\s,;|.]+$')


def norm(s):
    return WS.sub(' ', str(s or '')).strip()


def loose(s):
    return re.sub(r'[^0-9a-z]', '', str(s or '').lower())


ALLSEP = re.compile(r' \| |; |, ')
# Splitting a fragment from its own label. See the "label" rung above.
LABELSEP = re.compile(r' \| |; |, |(?<=[A-Za-z]): ')
GLOSS = re.compile(r'\s*\([^()]*\)\s*$')
# Values that state an evidence position rather than quote the page. Each says in terms that no single value is
# printed, so there is nothing to trace. The list is deliberately short and explicit: anything added here stops
# being checked, so it is the one place this module can be weakened by accident.
DECLARED = (
    'multiple parks,', 'multiple sites', 'multiple water play sites', 'consolidated invoice,',
    'no park named on the printed line', 'multiple parks and roads',
)
STOP = {'the', 'and', 'for', 'with', 'per', 'from', 'this', 'that', 'each', 'all', 'one', 'not', 'printed'}
WORD = re.compile(r"[A-Za-z][A-Za-z'&/-]{3,}|\d[\d,.]{2,}")


def _components(value):
    """The value, then its parts under each separator in turn, widest first so a whole match wins."""
    yield 'verbatim', [value]
    parted = False
    for sep in SPLITS:
        if sep in value:
            parted = True
            yield 'component', [TRIM.sub('', p) for p in value.split(sep)]
    if ITEM_NO.search(value):
        parted = True
        yield 'component', [TRIM.sub('', p) for p in ITEM_NO.split(value)]
        yield 'component', [TRIM.sub('', q) for p in ITEM_NO.split(value) for q in ALLSEP.split(p)]
    if ALLSEP.search(value):
        yield 'component', [TRIM.sub('', p) for p in ALLSEP.split(value)]
    if LABELSEP.search(value):
        yield 'label', [TRIM.sub('', p) for p in LABELSEP.split(value)]
    if GLOSS.search(value):
        stripped = GLOSS.sub('', value)
        yield 'gloss', [stripped]
        yield 'gloss', [TRIM.sub('', p) for p in LABELSEP.split(stripped)]
    if parted or ' ' in value:
        yield 'tokens', [w for w in WORD.findall(value) if w.lower() not in STOP]


def _found(part, hay, hay_loose, col):
    part = TRIM.sub('', part)
    if len(part) < MIN_LEN:
        return True                       # too short to be evidence either way
    if part.lower().strip('()') in {p_.strip('()') for p_ in PLACEHOLDERS}:
        return True                       # a declared blank inside a composed value declares an absence
    if col in LOOSE:
        return loose(part) in hay_loose
    return part in hay or loose(part) in hay_loose


def check_document(evid, fields, page_text, vendor=None):
    """fields: {column: value} as written to the green block.

    Returns (failures, rungs): failures is empty when every field traced, rungs counts how many reached each rung.
    """
    hay = norm(page_text)
    hay_loose = loose(page_text)
    out, rungs = [], collections.Counter()
    for col, name in FIELDS.items():
        raw = fields.get(col)
        if raw is None or isinstance(raw, (int, float)):
            continue
        value = norm(raw)
        if not value:
            continue
        if value in PLACEHOLDERS:
            rungs['placeholder'] += 1; continue
        low = value.lower()
        if any(low.startswith(d) for d in DECLARED):
            rungs['declared'] += 1; continue
        best, rung = None, None
        for name_, parts in _components(value):
            missing = [p for p in parts if not _found(p, hay, hay_loose, col)]
            if not missing:
                rungs[name_] += 1; best = []; break
            if best is None or sum(map(len, missing)) < sum(map(len, best)):
                best, rung = missing, name_
        if best:
            out.append(dict(evid=evid, col=col, field=name, vendor=vendor, value=value[:160], rung=rung,
                            missing=[m[:90] for m in best[:3]], missing_n=len(best)))
    return out, rungs


def report(failures, checked_docs, checked_fields, rungs=None):
    lines = [f'green-block provenance: {checked_docs} documents, {checked_fields} printed fields tested against '
             f'their own retained page text, {len(failures)} not traceable']
    if rungs:
        order = ('verbatim', 'component', 'label', 'gloss', 'tokens', 'declared', 'placeholder')
        lines.append('  traced at: ' + ', '.join(f'{k} {rungs[k]:,}' for k in order if rungs.get(k)))
    for f in failures[:25]:
        lines.append(f'  {f["evid"]} col {f["col"]} {f["field"]}: {f["missing_n"]} fragment(s) absent from the page '
                     f'text, first {f["missing"][0]!r} (value {f["value"]!r})')
    if len(failures) > 25:
        lines.append(f'  ... and {len(failures) - 25} more')
    return '\n'.join(lines)


def selftest():
    """Prove the check catches the failure it was built for, on a real document.

    The Levai reader carried one job on every Levai invoice from branch v2 to v10. This replays that: the wrong
    values are offered against an invoice that is about something else, and must be refused; the values the
    invoice really prints must pass. A check nobody has seen fail is not a check.
    """
    import glob, json, os
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    doc = None
    for f in sorted(glob.glob(os.path.join(root, 'batches', '*', 'corpus_*_v6.json'))):
        for d in json.load(open(f))['documents']:
            if d.get('vendor_template') == 'LEVAI' and d.get('page_text') and 'Spring Mountain' not in json.dumps(d['page_text']):
                doc = d; break
        if doc:
            break
    if doc is None:
        return None, 'no Levai document with retained page text to test against'
    page = '\n'.join(doc['page_text'][k] for k in sorted(doc['page_text'], key=int))
    wrong = {106: 'Spring Mountain Reserve (Ref: 35715)',
             108: 'Bush Track Repair & Drainage Works; Completed - 29.06.2026'}
    bad, _ = check_document(doc['invoice_no'], wrong, page, 'LEVAI')
    right = {92: '41 Industrial Ave, LOGAN VILLAGE QLD 4207, AUSTRALIA',
             93: 'Office: (07) 3803 0032; Email: admin@thlevai.com', 90: '65 100 395 480'}
    good, _ = check_document(doc['invoice_no'], right, page, 'LEVAI')
    ok = len(bad) == 2 and not good
    return ok, (f'{doc["invoice_no"]}: the v2-to-v10 Levai values are refused ({len(bad)} of 2 fields), '
                f'the values it prints are traced ({len(good)} refused of 3)')


if __name__ == '__main__':
    ok, msg = selftest()
    print(('PASS  ' if ok else 'FAIL  ') + str(msg))
    raise SystemExit(0 if ok else 1)
