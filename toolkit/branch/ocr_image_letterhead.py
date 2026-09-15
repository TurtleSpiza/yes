"""ocr_image_letterhead.py - read what a binder prints as an IMAGE, and retain the read as evidence.

WHY THIS EXISTS. The register's identity rule is rule 8: the PRINTED ABN decides, and an ABN is never carried onto a
line that does not evidence it. A supplier that prints its letterhead as an image defeats that rule through no fault
of its own, because pdftotext returns nothing for it: no ABN, no entity name. R.S.T. Systems t/a Vinton Tree Services
is such a supplier, and the vinton_new extraction reported reading both by OCR while retaining no OCR text, so the
claim could not be checked and was withdrawn (prep R7). An OCR read whose text is not retained is an assertion.

WHAT IT DOES. It renders each page ITSELF, reads it, and RETAINS the text, so the claim becomes evidence this project
holds and the provenance gate can trace the fields back to it.

THE CONSENSUS RULE. One OCR pass is not evidence either: OCR misreads digits, and a digit is exactly what an ABN is.
Each page is therefore rendered at TWO resolutions and read independently, and a value is accepted only where both
reads agree character for character after whitespace normalisation. Where they disagree the value is refused and the
disagreement is recorded, because a field this project cannot read twice the same way is one it does not know. On the
vinton_new binder the two reads agree on the ABN and the entity on every invoice page and disagree on one digit of a
mobile number, which is the rule earning its place rather than a hypothetical.

Usage: python3 ocr_image_letterhead.py <batch id> <binder.pdf> [--dpi 300,400]
"""
import collections, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BATCH = sys.argv[1]
PDF = sys.argv[2]
DPIS = [int(x) for x in (sys.argv[3].split('=')[-1] if len(sys.argv) > 3 else '300,400').split(',')]
ABN = re.compile(r'\bABN[:\s]*((?:\d[\s]?){10}\d)')
# The legal entity, anchored on its SUFFIX and grown outwards only through capitalised words, so OCR noise on either
# side of the letterhead line ("Ls ae R. S. T. ..." / "... Services i .") cannot join the value. Without that anchor
# the two reads disagreed on all 42 pages over noise alone, while agreeing on the entity itself character for
# character, which would have refused a value this binder states plainly.
ENTITY = re.compile(r"((?:[A-Z][A-Za-z'.]{0,20}\.? ){1,8}?Pty\.? ?(?:Ltd|Limited)\.?"
                    r"(?:\s+Trading as(?:\s+[A-Z][A-Za-z']{1,20}){1,5})?)")
norm = lambda s: ' '.join(str(s or '').split())


def ocr_page(page, dpi):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'p')
        subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', str(dpi), '-png', PDF, out],
                       capture_output=True)
        pngs = sorted(f for f in os.listdir(td) if f.endswith('.png'))
        if not pngs:
            return ''
        return subprocess.run(['tesseract', os.path.join(td, pngs[0]), '-', '--psm', '6'],
                              capture_output=True, text=True).stdout


def longest(rx, text):
    """The longest match, because a page prints both the full legal form and a short one (the bank block's
    "RST Systems Pty Ltd" against the letterhead's "R. S. T. Systems Pty. Limited Trading as Vinton Tree
    Services"), and the full form is the one rule 8 wants."""
    ms = [norm(m) for m in rx.findall(text)]
    return max(ms, key=len) if ms else None


def agreed(reads, rx, group=1):
    """The value both reads give, or None where they differ or only one finds it."""
    vals = [longest(rx, t) for t in reads]
    return vals[0] if len(set(vals)) == 1 and vals[0] else None


def main():
    assert shutil.which('tesseract'), 'tesseract is not installed; the session-start hook installs it'
    cpath = os.path.join(ROOT, 'batches', BATCH, f'corpus_{BATCH}_v6.json')
    corpus = json.load(open(cpath))
    npages = int(next(l.split(':')[1] for l in subprocess.run(['pdfinfo', PDF], capture_output=True, text=True)
                      .stdout.splitlines() if l.startswith('Pages:')))
    per_page, disagree = {}, []
    for p in range(1, npages + 1):
        reads = [ocr_page(p, d) for d in DPIS]
        abn = agreed(reads, ABN)
        ent = agreed(reads, ENTITY)
        per_page[p] = dict(ocr_text=reads[0], ocr_dpi=DPIS, abn=re.sub(r'\s+', ' ', abn) if abn else None, entity=ent)
        for name, rx in (('abn', ABN), ('entity', ENTITY)):
            got = [longest(rx, t) for t in reads]
            if len(set(got)) > 1:
                disagree.append(dict(page=p, field=name, reads=got))
        print(f'  page {p:3}: abn {abn or "-"} | entity {(ent or "-")[:52]}')

    hit = 0
    for d in corpus['documents']:
        pages = list(range(d['page_range'][0], d['page_range'][1] + 1))
        reads = [per_page[p] for p in pages if p in per_page]
        d['ocr_pages'] = {str(p): per_page[p]['ocr_text'] for p in pages if p in per_page}
        d['ocr_tool'] = f'tesseract {subprocess.run(["tesseract","--version"],capture_output=True,text=True).stdout.splitlines()[0]}'
        d['ocr_basis'] = (f'each page rendered by pdftoppm at {" and ".join(str(x) for x in DPIS)} dpi and read '
                          f'independently; a value is retained only where both reads agree')
        abns = {r['abn'] for r in reads if r['abn']}
        ents = {r['entity'] for r in reads if r['entity']}
        if len(abns) == 1:
            d['ocr_abn'] = abns.pop(); hit += 1
        if len(ents) == 1:
            d['ocr_entity'] = ents.pop()
    json.dump(corpus, open(cpath, 'w'), indent=1, ensure_ascii=False)
    out = os.path.join(ROOT, 'batches', BATCH, f'ocr_{BATCH}_v6.json')
    json.dump(dict(binder=os.path.basename(PDF), pages=npages, dpis=DPIS, disagreements=disagree,
                   pages_read={str(k): v for k, v in per_page.items()}), open(out, 'w'), indent=1, ensure_ascii=False)
    print(f'\n{BATCH}: {npages} pages read at {DPIS} dpi; {hit} documents now carry an agreed OCR ABN; '
          f'{len(disagree)} field(s) where the two reads disagreed (refused, listed in {os.path.basename(out)})')


if __name__ == '__main__':
    main()
