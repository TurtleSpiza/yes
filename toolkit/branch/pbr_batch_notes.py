"""pbr_batch_notes.py - author notes_<batch>_v6.json from a gated corpus and the shipped register (rule 18).

One entry per matched invoice. Every phrase is the printed one, read by pbr_capture.header_fields, the same reader
that fills the register's green block, so the note and the block cannot disagree about what the document says. The
only judgement formed here is the verdict where the printed PK differs from, or is absent against, the PK charged.

Usage: python3 pbr_batch_notes.py <batch id> [register.xlsx]
"""
import json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import pbr_capture  # noqa: E402

BATCH = sys.argv[1]
NP = pbr_capture.NP
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
money = lambda x: f'${D(x):,.2f}'
norm = lambda s: ' '.join(str(s or '').split())


def items_of(doc):
    out = []
    for l in doc['lines']:
        if l.get('line_type') != 'PRICED':
            continue
        desc = norm(re.sub(r'\s{2,}[\d,]+(?:\.\d+)?\s{2,}\$?[\d,]+\.\d{2}\s{2,}(?:GST|FRE|\d{1,2}%)?\s*\$?-?[\d,]+\.\d{2}\s*$',
                           '', l.get('line_text') or ''))
        desc = norm(re.sub(r'\s*\$?-?[\d,]+\.\d{2}\s*$', '', desc)) or '(description as printed)'
        out.append(f'{desc} = {money(l.get("line_ex_gst"))}')
    return out


def main():
    bdir = os.path.join(ROOT, 'batches', BATCH)
    corpus = json.load(open(os.path.join(bdir, f'corpus_{BATCH}_v6.json')))
    match = json.load(open(os.path.join(bdir, f'match_{BATCH}_v6.json')))
    docs = {d['invoice_no']: d for d in corpus['documents']}
    out = {'_readme': [
        f'Authored content for Batch {BATCH} (rule 18: content as data, never ad-hoc writes). One entry per matched invoice.',
        'Each coding_note restates what the invoice face prints for that document, read by the same reader that fills the',
        'register green block (pbr_capture.header_fields), and states whether the printed PK equals the PK charged.',
        'No amount is inferred: every figure is the printed one and the corpus gates GREEN with every document at TIE.']}
    for e in match:
        d = docs[e['invoice']]
        hf = pbr_capture.header_fields(d)
        charged = e['register_lines'][0]['pk']
        pk = d['pk_refs'][0] if d['pk_refs'] else None
        bits = []
        for label, key in (('site', 'site'), ('work', 'work'), ('contract', 'contract'), ('order', 'po'),
                           ('requesting officer', 'officer')):
            v = hf.get(key)
            if v and v not in (NP, ''):
                bits.append(f'{label} {norm(v)}')
        sub, gst, tot = D(d['printed_subtotal_ex_gst']), D(d['printed_gst']), D(d['printed_total_incl_gst'])
        basis = ' (the printed line amounts are GST inclusive on this template)' if d.get('line_amount_basis') == 'incl_gst' else ''
        note = (f'{d["supplier"].split(" (")[0]}: ' + '; '.join(bits) + '. '
                f'Lines as printed: {"; ".join(items_of(d))}{basis}. '
                f'Printed subtotal {money(sub)} ex GST, GST {money(gst)}, total {money(tot)}. ')
        ent = {'coding_verdict': 'Correct'}
        if pk is None:
            note += (f'No PK is printed on the invoice face; the charge sits on {charged}, which comes from the '
                     f'TechOne order, not from the document.')
            ent['follow_up'] = (f'Ask {d["supplier"].split(" (")[0].title()} to print the PK on the face: this invoice '
                                f'states no PK, so the face cannot corroborate the PK charged ({charged}).')
        elif pk == charged:
            note += f'Printed {pk} matches the PK charged ({charged}).'
        else:
            note += f'Printed {pk} differs from the PK charged ({charged}). PK Charged stays the ledger Work Order (rule 1).'
            ent['coding_verdict'] = 'Review'
            ent['follow_up'] = (f'Confirm the WO Task with Park Services: the face prints {pk} for this site and TechOne '
                                f'charged {charged}; recode if {charged} is not the intended WO Task. No effect on the total.')
        ent['coding_note'] = norm(note)
        out[e['invoice']] = ent
    json.dump(out, open(os.path.join(bdir, f'notes_{BATCH}_v6.json'), 'w'), indent=1, ensure_ascii=False)
    v = sum(1 for k, x in out.items() if k != '_readme' and x['coding_verdict'] == 'Review')
    f = sum(1 for k, x in out.items() if k != '_readme' and x.get('follow_up'))
    print(f'{BATCH}: {len(out) - 1} entries, {v} Review, {f} with a follow-up')


if __name__ == '__main__':
    main()
