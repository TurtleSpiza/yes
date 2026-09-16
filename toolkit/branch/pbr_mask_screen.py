"""pbr_mask_screen.py - the rows a binder MASKS, and the line records that read them anyway.

WHY THIS EXISTS. A supplier can hide rows on a printed attachment by filling the cells black, leaving the text in
place underneath. The page shows one row; the text layer still carries them all. `pdftotext` has no notion of fill
colour, so an extraction runtime reads the hidden rows and cannot know it did. Every gate this project runs then
passes: the corpus is well formed, the bands are anchored, the headers add up, the line types are legal. The only
symptom is a document at OUT, and a capture that ties by some other route would show nothing at all.

That is why this screen lives HERE and not in the extraction prompt. The runtime is blind to it by construction, so
asking the extractor to self-report is asking for an assertion it cannot make. The project renders the page itself.

THE DISCRIMINATOR. A masked row is a filled rectangle: a long contiguous near-black run repeated over several
scanlines. Text never produces a long contiguous run (a glyph is a few pixels of stroke), and a table rule produces
one that is one or two scanlines tall. Requiring both the width and the height is what separates the two.

WHY IT MATTERS MORE THAN THE ARITHMETIC. On the Glascott binder the masked rows are not padding: they are the rows
OTHER invoices in the same binder bill. Invoice 012193's single masked row is the row 012194 bills on its own face.
Capturing a masked row does not merely overstate one document, it counts the same work twice across the binder.

Usage:
  python3 toolkit/branch/pbr_mask_screen.py <binder.pdf> [...]              # which pages mask rows
  python3 toolkit/branch/pbr_mask_screen.py --corpus <corpus.json> <pdf>... # which line records read them
  python3 toolkit/branch/pbr_mask_screen.py --corpus c.json --restate out.json <pdf>...
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
POLICY = os.environ.get('PBR_MASK_POLICY', os.path.join(HERE, 'pbr_mask_screen_v1.json'))
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
WS = re.compile(r'\s+')


def load_policy(path=POLICY):
    with open(path) as fh:
        return json.load(fh)


def _pgm(path):
    d = open(path, 'rb').read()
    vals, i = [], 2
    while len(vals) < 3:
        while i < len(d) and d[i:i + 1].isspace():
            i += 1
        if d[i:i + 1] == b'#':
            while d[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        j = i
        while j < len(d) and not d[j:j + 1].isspace():
            j += 1
        vals.append(int(d[i:j])); i = j
    i += 1
    w, h, _ = vals
    return w, h, d[i:i + w * h]


def filled_bands(pdf, policy=None):
    """Per page, the y-bands (as fractions of page height) covered by a filled rectangle."""
    p = policy or load_policy()
    need_frac, dark, min_h = p['min_run_fraction'], p['dark_below'], p['min_scanlines']
    out = {}
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['pdftoppm', '-r', str(p['dpi']), '-gray', pdf, os.path.join(td, 'p')],
                       check=True, capture_output=True)
        for f in sorted(glob.glob(os.path.join(td, 'p-*.pgm'))):
            page = int(re.search(r'-(\d+)\.pgm$', f).group(1))
            w, h, px = _pgm(f)
            need = int(w * need_frac)
            rows = []
            for y in range(h):
                row = px[y * w:(y + 1) * w]
                best = run = 0
                for v in row:
                    if v < dark:
                        run += 1
                        if run > best:
                            best = run
                    else:
                        run = 0
                rows.append(best >= need)
            bands, start = [], None
            for y, f_ in enumerate(rows + [False]):
                if f_ and start is None:
                    start = y
                elif not f_ and start is not None:
                    if y - start >= min_h:
                        bands.append((start / h, y / h))
                    start = None
            if bands:
                out[page] = bands
    return out


def page_cells(pdf, pages):
    """{page: [(y0frac, y1frac, xMin, text)]} from pdftotext -bbox-layout.

    Each <line> in that XML is one TABLE CELL, not one printed row, so the caller reassembles rows."""
    if not pages:
        return {}
    lo, hi = min(pages), max(pages)
    xml = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(lo), '-l', str(hi), pdf, '-'],
                         check=True, capture_output=True, text=True).stdout
    out, page, height = {}, lo - 1, None
    for m in re.finditer(r'<page width="[\d.]+" height="([\d.]+)"|<line xMin="([\d.]+)" yMin="([\d.]+)"'
                         r' xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', xml, re.S):
        if m.group(1):
            page += 1; height = float(m.group(1)); out[page] = []
            continue
        if height is None:
            continue
        words = re.findall(r'>([^<]*)</word>', m.group(5))
        txt = ' '.join(words).strip()
        if txt:
            out[page].append((float(m.group(3)) / height, float(m.group(4)) / height, float(m.group(2)), txt))
    return out


def rows_from_cells(cells):
    """Reassemble printed rows: cells sharing a vertical band, joined left to right."""
    rows = []
    for y0, y1, x, txt in sorted(cells):
        for r in rows:
            ov = min(y1, r['y1']) - max(y0, r['y0'])
            if ov > 0 and ov / min(y1 - y0, r['y1'] - r['y0']) >= 0.5:
                r['cells'].append((x, txt)); r['y0'] = min(r['y0'], y0); r['y1'] = max(r['y1'], y1)
                break
        else:
            rows.append({'y0': y0, 'y1': y1, 'cells': [(x, txt)]})
    return [(r['y0'], r['y1'], ' '.join(t for _x, t in sorted(r['cells']))) for r in rows]


def masked_text(pdf, policy=None):
    """{page: set(normalised text)} for every text line sitting inside a filled band."""
    p = policy or load_policy()
    bands = filled_bands(pdf, p)
    if not bands:
        return {}
    cells = page_cells(pdf, sorted(bands))
    out = {}
    for page, bs in bands.items():
        hit = []
        for y0, y1, txt in rows_from_cells(cells.get(page, [])):
            for b0, b1 in bs:
                ov = min(y1, b1) - max(y0, b0)
                if ov > 0 and ov / max(y1 - y0, 1e-9) >= p['overlap_fraction']:
                    hit.append(WS.sub(' ', txt).strip()); break
        if hit:
            out[page] = hit
    return out


def is_masked(line_text, masked_rows, min_len=12):
    """A line record reads a masked row when its text is that row. `pdftotext -layout` truncates the trailing
    columns of a wide table, so the test is containment in the reassembled row, not equality. min_len keeps a
    short fragment such as "AMP" from matching every row on the page."""
    t = WS.sub(' ', line_text or '').strip()
    if len(t) < min_len:
        return False
    return any(t in row for row in masked_rows)


def screen(corpus, pdf_map, policy=None):
    """Per document: which of its line records read masked rows, and what they are worth."""
    p = policy or load_policy()
    masked = {name: masked_text(path, p) for name, path in pdf_map.items()}
    findings = []
    for doc in corpus.get('documents', []):
        m = masked.get(doc.get('source_file')) or {}
        if not m:
            continue
        hits = []
        for l in doc.get('lines', []):
            if is_masked(l.get('line_text'), m.get(l.get('page')) or []):
                hits.append(l)
        if not hits:
            continue
        val = D(sum(D(l.get('line_ex_gst')) for l in hits if l.get('line_type') == 'PRICED'))
        cap, sub = D(doc.get('captured_ex_gst')), D(doc.get('printed_subtotal_ex_gst'))
        findings.append({
            'doc_ref': doc.get('doc_ref'), 'source_file': doc.get('source_file'),
            'pages': sorted({l.get('page') for l in hits}), 'masked_records': len(hits),
            'masked_priced': sum(1 for l in hits if l.get('line_type') == 'PRICED'),
            'masked_value': float(val), 'captured': float(cap), 'printed_subtotal': float(sub),
            'ties_once_dropped': cap - val == sub,
        })
    return findings


def restate(corpus, pdf_map, policy=None, log=print):
    """Drop the masked line records. A row the document does not display is not a row it prints, so it is not
    captured (rule 17). The record is retained, retyped and flagged, never deleted: nothing is lost."""
    p = policy or load_policy()
    masked = {name: masked_text(path, p) for name, path in pdf_map.items()}
    n_doc = n_row = 0
    for doc in corpus.get('documents', []):
        m = masked.get(doc.get('source_file')) or {}
        if not m:
            continue
        touched = 0
        for l in doc.get('lines', []):
            if is_masked(l.get('line_text'), m.get(l.get('page')) or []):
                l['masked_on_page'] = True
                if l.get('line_type') == 'PRICED':
                    l['line_type'] = 'NARRATIVE'
                    l['restated'] = 'M1: row is masked on the printed page; not captured'
                    touched += 1
        if touched:
            n_doc += 1; n_row += touched
            doc.setdefault('findings', []).append({
                'code': 'M1', 'detail': 'Rows masked on the printed page were read from the text layer and have '
                                        'been dropped from capture.', 'rows': touched})
            log(f'  M1 {doc.get("doc_ref")}: {touched} masked priced row(s) dropped')
    return n_doc, n_row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pdfs', nargs='+')
    ap.add_argument('--corpus', help='attribute masked rows to a corpus\'s line records')
    ap.add_argument('--restate', metavar='OUT', help='write a corpus with the masked rows dropped from capture')
    a = ap.parse_args(argv)
    p = load_policy()
    pdf_map = {os.path.basename(x).replace('_', ' '): x for x in a.pdfs}
    if not a.corpus:
        for name, path in pdf_map.items():
            b = filled_bands(path, p)
            print(f'{os.path.basename(path)}: {len(b)} page(s) mask rows')
            for page in sorted(b):
                cov = sum(e - s for s, e in b[page])
                print(f'  page {page:>3}: {len(b[page])} band(s), {cov * 100:.1f}% of page height')
        return 0
    corpus = json.load(open(a.corpus))
    names = {d.get('source_file') for d in corpus.get('documents', [])}
    pdf_map = {n: path for n in names for path in a.pdfs
               if os.path.basename(path).replace('_', ' ').endswith(n.replace('_', ' '))}
    missing = names - set(pdf_map)
    if missing:
        print(f'no binder supplied for: {sorted(missing)} (those documents are not screened)')
    for f in screen(corpus, pdf_map, p):
        print(f"  {f['doc_ref']:<10} pages {f['pages']} {f['masked_priced']:>3} masked priced row(s) "
              f"${f['masked_value']:>12,.2f}  captured ${f['captured']:>12,.2f} vs printed "
              f"${f['printed_subtotal']:>12,.2f} -> {'ties once dropped' if f['ties_once_dropped'] else 'STILL OUT'}")
    if a.restate:
        nd, nr = restate(corpus, pdf_map, p)
        json.dump(corpus, open(a.restate, 'w'))
        print(f'\nrestated {nd} document(s), {nr} masked priced row(s) dropped -> {a.restate}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
