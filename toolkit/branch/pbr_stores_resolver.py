"""pbr_stores_resolver.py - resolve an LCC Stores line to the goods it bought (rule 18, content as data).

Every LCC Stores line on the register is an internal inventory issue and its narration reads

    Despatch Stock Requisition '100231'-ALLSTORE/CHAMBERS/206999/BF42/VEST SAFET-STKISS

so the product number prints in full and the description is cut to ten characters. Three sources can name the
product, and they are not equal:

  0  stores_confirmed_products.json, names confirmed by the register owner                    AUTHORITATIVE
  1  the TechOne My Requisition Lines export, which prints the requisition's own full description  best machine
  2  the Marsden Stores inventory (lcc-coding-review bundle), which adds the category               second
  3  the Marsden Stores catalogue PDF, captured by pbr_stores_catalogue.py                          last

Scored against the v24 register, on the register's own truncated narration as the test:

    source                         agree   disagree   absent
    requisition export               163         41        3
    stores inventory                 117         44       46
    catalogue PDF capture            101         60       46

The export wins ON COVERAGE, because it is the record of the issue itself rather than a catalogue of what
Stores sells: it names the 44 clothing and PPE products the 2026 catalogue does not list at all, which is most
of what Parks draws.

It does NOT win on the contested cases, and that is worth stating because it contradicts the coverage ranking.
Of the seven products the register owner confirmed on 18-Sep-2026, all of them cases where the sources
disagreed, the export was exactly right on NONE and the inventory on two. On 196303 the export names a hard hat
browguard with an earmuff attachment and the goods are a face shield with a clear visor, a different piece of
PPE on the same account. The seven were chosen because they disagreed, so this is not a fair sample of the
export as a whole, but it is enough to say the export is the best machine source and not an authority. Where a
name matters, confirm it and record it in stores_confirmed_products.json.

Usage: python3 pbr_stores_resolver.py build <My_Requisition_Lines.xlsx> [out.json]
       python3 pbr_stores_resolver.py verify <out.json> <register.xlsx>
"""
import datetime as dt, hashlib, json, os, re, sys

from python_calamine import CalamineWorkbook

STK = re.compile(r"ALLSTORE/([^/]+)/(\d{6})/([^/]*)/([^-]*)-STKISS")


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def norm(t):
    return ' '.join(str(t or '').split())


def build(src):
    rows = CalamineWorkbook.from_path(src).get_sheet_by_name('Sheet1').to_python(skip_empty_area=False)
    ix = {norm(c): i for i, c in enumerate(rows[3])}
    P, D, U = ix['MYRLCatalogueProductNumber'], ix['MYRLDescription'], ix['MYRLTransactionUnitName']
    S, L = ix['MYRLSupplierName'], ix['ILLocationName']
    prod, lines = {}, 0
    for r in rows[5:]:
        code = norm(r[P]).split('.')[0]
        if not code or code == 'None':
            continue
        lines += 1
        desc = norm(r[D])
        cur = prod.get(code)
        # the longest description printed for a code is the least abbreviated one the export holds
        if cur is None or len(desc) > len(cur['description']):
            prod[code] = dict(code=code, description=desc, unit=norm(r[U]),
                              supplier=norm(r[S]), location=norm(r[L]))
        prod[code]['issues'] = (cur or {}).get('issues', 0) + 1
    return dict(manifest=dict(source=os.path.basename(src), md5=md5(src), tool='pbr_stores_resolver.py',
                              built_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                              requisition_lines=lines, products=len(prod)),
                products=prod)


def verify(data_path, reg_path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pbr_stores_catalogue import agrees
    prod = json.load(open(data_path))['products']
    rows = CalamineWorkbook.from_path(reg_path).get_sheet_by_name('Register').to_python(skip_empty_area=False)
    ok, dis, absent = 0, [], []
    for r in rows[4:]:
        if 'Stores' not in norm(r[11]):
            continue
        m = STK.search(norm(r[21]))
        if not m:
            continue
        code, trunc = m.group(2), norm(m.group(4))
        if code not in prod:
            absent.append((code, trunc))
        elif agrees(trunc, prod[code]['description']):
            ok += 1
        else:
            dis.append((code, trunc, prod[code]['description']))
    print(f'Stores lines carrying a product number: {ok + len(dis) + len(absent)}')
    print(f'  resolved and the narration agrees: {ok}')
    print(f'  resolved and the narration disagrees: {len(dis)}')
    print(f'  not in the export: {len(absent)}')
    for c, t, d in dis:
        print(f'    DISAGREE {c}  register {t!r}  export {d!r}')
    for c, t in absent:
        print(f'    ABSENT   {c}  register {t!r}')
    return len(absent)


def main():
    if sys.argv[1] == 'verify':
        sys.exit(1 if verify(sys.argv[2], sys.argv[3]) else 0)
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'reference', 'stores_requisition_products.json')
    data = build(sys.argv[2])
    json.dump(data, open(out, 'w'), indent=1)
    m = data['manifest']
    print(f"{m['requisition_lines']:,} requisition lines -> {m['products']:,} distinct products, written to {out}")


if __name__ == '__main__':
    main()
