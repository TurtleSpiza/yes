"""pbr_stores_catalogue.py - capture the Marsden Stores inventory catalogue to JSON (rule 18, content as data).

Why this exists. Every LCC Stores line on the register is an internal inventory issue and its narration reads

    Despatch Stock Requisition '100231'-ALLSTORE/CHAMBERS/206999/BF42/VEST SAFET-STKISS

so the product number is printed in full and the description is truncated to ten characters. The stage already
types these lines Tier 1 Confirmed on the system record, but what was actually bought is not readable from the
register: "VEST SAFET" does not say which vest, and "TICK TOX F" does not say it is a first aid item. The
catalogue carries the full description, the issue unit and the category, keyed on that same product number, so
it turns a truncated narration into named goods without inferring anything.

The catalogue is an untagged Microsoft Print To PDF, so there is no structure tree to walk and pdftotext -layout
interleaves its multi-column product cards. Capture is therefore driven off PyMuPDF text blocks and their
coordinates, and the catalogue prints products in three shapes, all of which are read here:

  A  a card, one block or several in a column:      Prod No: 208508 / Description: CR2032 / Unit: EACH
  B  a size-variant table under one header:         Prod No: Description:
                                                    206988 RAINCOAT SMALL
                                                    206989 RAINCOAT MEDIUM
  C  an inline variant run beside a shared block:   Description: HAT STRAW Unit: EACH
                                                    196284 HAT SMALL 196285 HAT MEDIUM 196286 HAT LARGE
  D  a footwear size grid under a model name:       OLIVER WHEAT ZIP 55-332Z
                                                    UNIT: PAIR Size Range: 5-14 Half Sizes: ...
                                                    Prod Code UK Size *207667 5 / 206887 7 / 207332 8.5

Reading shape A alone captures 454 of the 747 products and loses almost all of the clothing and PPE, which is
most of what Parks actually draws from Stores. In shape D the description on the row is only a UK size, so the
model name is taken from the nearest name block above the grid and an asterisk on the code is kept as
order_from_supplier, which is what the page's own legend says it means.

Categories come from the catalogue's own contents page, which is the only authoritative list of them. An in-page
heading is used where one prints, but only when it names a category the contents also names: the clothing pages
print notes in capitals ("NOTE: JACKET IMAGE IS NOT ALWAYS ACCURATE") that a shape heuristic reads as headings.

The capture is then checked against the register itself, which is the only independent evidence available: the
narration truncates the description to ten characters, so every resolved product must have those characters
appear in the captured description. The register reorders words ("VEST SAFET" against "SAFETY VEST L/XL"), so
the test is on tokens and prefixes, not on a leading substring. A product the register charges and the capture
disagrees with is reported, never silently kept: a reference table nobody checked is worth less than none.

Usage: python3 pbr_stores_catalogue.py <catalogue.pdf> [out.json]
       python3 pbr_stores_catalogue.py --verify <catalogue.json> <register.xlsx>
"""
import datetime as dt, hashlib, json, os, re, sys

import pymupdf

PN = re.compile(r'(?<![\d.])(\d{6})(?![\d])')       # every product number in this catalogue is six digits
HEADISH = re.compile(r"^[A-Z][A-Z0-9 &/',.\-()]+$")
NOISE = re.compile(r'^(page\s*\d*|prod no:?|description:?|unit:?|note:.*)$', re.I)


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def norm(t):
    return ' '.join(str(t or '').split())


def clean(t):
    """Strip the printed labels and mark the unit boundary, keeping the printed words otherwise verbatim."""
    t = norm(t)
    t = re.sub(r'^\s*(Description|Desc)\s*:\s*', '', t, flags=re.I)
    return re.sub(r'\bUNIT\s*:\s*', '|UNIT:', t, flags=re.I).strip()


def contents(doc):
    """The contents page, as (printed page, category). It sits on the second printed page, two columns of
    NAME then page number. It is the canonical category list and nothing else in the file is."""
    page = doc[1].get_text('text', sort=True)
    out = []
    for line in page.splitlines():
        m = re.match(r'^(.*?\S)\s{2,}(\d{1,2})\s*$', line)
        if not m:
            continue
        name = norm(m.group(1))
        if name.upper() == name and len(name) > 2:
            out.append((int(m.group(2)), name))
    if not out:   # the layout route reads the two columns where the block route does not
        import subprocess
        txt = subprocess.run(['pdftotext', '-layout', '-f', '2', '-l', '2', doc.name, '-'],
                             capture_output=True, text=True).stdout
        for line in txt.splitlines():
            m = re.match(r'^(.*?\S)\s{2,}(\d{1,2})\s*$', line)
            if m and norm(m.group(1)).upper() == norm(m.group(1)) and len(norm(m.group(1))) > 2:
                out.append((int(m.group(2)), norm(m.group(1))))
    assert out, 'no contents page parsed: the category list is not optional'
    return out


SIZE_ROW = re.compile(r'(\*?)(\d{6})\s+(\d{1,2}(?:\.5)?)(?!\d)')


def footwear(blocks, names):
    """Shape D. Returns {prod_no: (description, unit, from_supplier)} for a size-grid page.

    The model name does not sit on the same side of the page as its grid (page 62 prints one model top left
    with its grid on the right, the next model on the right with its grid on the left), so the grid rows are
    clustered by their vertical run and each cluster takes the name block nearest the top of that run."""
    models = []
    for b in blocks:
        t = norm(b[4])
        if NOISE.match(t) or t.upper() in names or SIZE_ROW.search(t):
            continue
        if re.match(r'^(UNIT|Prod Code|Size Range|\*)', t, re.I):
            continue
        if t.upper() == t and len(t) > 6 and re.search(r'[A-Z]{3}', t):
            models.append((b[1], t))   # may embed a style code; only a size row disqualifies a block
    models.sort()
    units = sorted((b[1], norm(b[4])) for b in blocks if re.match(r'^UNIT\s*:', norm(b[4]), re.I))
    rows = []
    for b in blocks:
        for star, pn, size in SIZE_ROW.findall(b[4]):
            rows.append((b[1], star, pn, size))
    out = {}
    for y, star, pn, size in rows:
        # The name block prints level with, or just above, the first row of its grid, and the next model's name
        # block marks where that grid ends. Taking the nearest name at or above each row needs no clustering and
        # gets the two-grids-per-page pages right, where a gap rule merged them and named both from the last model.
        above = [m for m in models if m[0] <= y + 12]
        name = above[-1][1] if above else (models[0][1] if models else '')
        ua = [u for u in units if u[0] <= y + 12]
        unit = ''
        if ua:
            mu = re.match(r'^UNIT\s*:\s*(\w+)', ua[-1][1], re.I)
            unit = mu.group(1).upper() if mu else ''
        out[pn] = (f'{name} SIZE {size}'.strip(), unit, bool(star))
    return out


def capture(path):
    doc = pymupdf.open(path)
    toc = contents(doc)
    names = {c.upper() for _, c in toc}
    by_page = sorted(toc)
    rows, carried = [], None
    for pno in range(2, doc.page_count):
        blocks = [b for b in doc[pno].get_text('blocks') if b[6] == 0 and b[4].strip()]
        heads = sorted((b[1], norm(b[4])) for b in blocks
                       if HEADISH.match(norm(b[4])) and not NOISE.match(norm(b[4]))
                       and not PN.search(b[4]) and norm(b[4]).upper() in names)
        shared = [(b[0], b[1], clean(b[4])) for b in blocks
                  if re.search(r'description\s*:', b[4], re.I) and not PN.search(b[4])]
        printed = pno            # the footer on PDF page n+1 prints Page n, so printed == pno
        is_grid = any(re.match(r'^Prod Code', norm(b[4]), re.I) for b in blocks)
        shoes = footwear(blocks, names) if is_grid else {}
        model_names = {norm(b[4]) for b in blocks} if is_grid else set()
        model_names = {t for t in model_names if t.upper() == t and len(t) > 6 and not SIZE_ROW.search(t)}
        for pn_, (desc_, unit_, sup_) in shoes.items():
            cat_ = heads[-1][1] if heads else carried
            if cat_ is None:
                for pg, name in by_page:
                    if pg <= printed:
                        cat_ = name
            rows.append(dict(prod_no=pn_, description=desc_, unit=unit_, category=cat_, page=printed,
                             order_from_supplier=sup_))
        for b in blocks:
            x0, y0, txt = b[0], b[1], b[4]
            if norm(txt) in model_names:
                continue      # a footwear model name, not a product: its six digits are the style code
            hits = list(PN.finditer(txt))
            for i, m in enumerate(hits):
                tail = txt[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(txt)]
                t, unit = clean(tail), ''
                if '|UNIT:' in t:
                    t, unit = t.split('|UNIT:', 1)
                    unit = norm(unit)
                t = norm(t.replace('Prod No', '').replace(':', ' '))
                base = ''
                if len(hits) > 1 or len(t.split()) <= 2:
                    near = [s for s in shared if abs(s[0] - x0) < 200 and abs(s[1] - y0) < 60]
                    if near:
                        nb = min(near, key=lambda s: abs(s[1] - y0))[2]
                        if '|UNIT:' in nb:
                            nb, u2 = nb.split('|UNIT:', 1)
                            unit = unit or norm(u2)
                        base = norm(nb)
                desc = (base + ' ' + t).strip() if base and not t.upper().startswith(base.upper()[:6]) else (t or base)
                cat = None
                for hy, h in heads:
                    if hy <= y0:
                        cat = h
                if cat:
                    carried = cat
                else:                     # no heading prints above this row: carry, else fall back to contents
                    cat = carried
                    if cat is None:
                        for pg, name in by_page:
                            if pg <= printed:
                                cat = name
                if m.group(1) in shoes:
                    continue      # the grid already named it, and the row carries only a size
                rows.append(dict(prod_no=m.group(1), description=desc.strip(' -:'), unit=unit,
                                 category=cat, page=printed, order_from_supplier=False))
    best = {}
    for r in rows:
        k = r['prod_no']
        if k not in best or len(r['description']) > len(best[k]['description']):
            best[k] = r
    products = sorted(best.values(), key=lambda r: r['prod_no'])
    return dict(manifest=dict(source=os.path.basename(path), md5=md5(path), pages=doc.page_count,
                              tool='pbr_stores_catalogue.py',
                              captured_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                              categories=[c for _, c in toc], products=len(products),
                              products_without_description=sum(1 for p in products if not p['description']),
                              products_without_unit=sum(1 for p in products if not p['unit'])),
                products=products)


STK = re.compile(r"ALLSTORE/[^/]+/(\d{6})/([^/]*)/([^-]*)-STKISS")


def agrees(trunc, desc):
    """The narration prints the description cut to ten characters and often reordered. It agrees when every
    whole word of the truncation appears in the captured description, and the trailing cut word prefixes one."""
    tw = [w for w in re.split(r'[^A-Za-z0-9]+', trunc.upper()) if w]
    dw = [w for w in re.split(r'[^A-Za-z0-9]+', desc.upper()) if w]
    if not tw or not dw:
        return False
    for w in tw[:-1]:
        if w not in dw:
            return False
    return any(d.startswith(tw[-1]) or tw[-1].startswith(d) for d in dw)


def verify(cat_path, reg_path):
    from python_calamine import CalamineWorkbook
    cat = {p['prod_no']: p for p in json.load(open(cat_path))['products']}
    rows = CalamineWorkbook.from_path(reg_path).get_sheet_by_name('Register').to_python(skip_empty_area=False)
    seen, ok, bad, absent = 0, 0, [], {}
    for r in rows[4:]:
        if 'Stores' not in norm(r[11]):
            continue
        m = STK.search(norm(r[21]))
        if not m:
            continue
        seen += 1
        pn, trunc = m.group(1), norm(m.group(3))
        if pn not in cat:
            absent[pn] = absent.get(pn, [trunc, 0])
            absent[pn][1] += 1
        elif agrees(trunc, cat[pn]['description']):
            ok += 1
        else:
            bad.append((pn, trunc, cat[pn]['description']))
    print(f'Stores lines carrying a product number: {seen}')
    print(f'  resolved and the narration agrees: {ok}')
    print(f'  resolved and the narration DISAGREES: {len(bad)}')
    print(f'  not in the catalogue: {sum(v[1] for v in absent.values())} over {len(absent)} products')
    for pn, t, d in bad:
        print(f'    DISAGREE {pn}  register {t!r}  capture {d!r}')
    for pn, (t, n) in sorted(absent.items(), key=lambda kv: -kv[1][1]):
        print(f'    ABSENT   {pn}  register {t!r}  charged {n}x')
    return len(bad)


def main():
    if sys.argv[1] == '--verify':
        sys.exit(1 if verify(sys.argv[2], sys.argv[3]) else 0)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'pbr_stores_catalogue_v1.json')
    cap = capture(src)
    json.dump(cap, open(out, 'w'), indent=1)
    m = cap['manifest']
    print(f"captured {m['products']} products over {m['pages']} pages into {len(m['categories'])} categories; "
          f"{m['products_without_description']} without a description, {m['products_without_unit']} without a unit")


if __name__ == '__main__':
    main()
