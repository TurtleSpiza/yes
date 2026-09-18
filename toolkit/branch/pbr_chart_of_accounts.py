"""pbr_chart_of_accounts.py - capture the Council chart of accounts and coding guide to JSON (rule 18).

The register carries a natural account on every line and its short description truncated by TechOne to fifteen
characters ("Landscapers & G", "Maintenance Ser", "Internal - Vehi"). The coding guide prints the full title and
a definition of what the account is for, plus the FBT reason codes A to L that decide 73511 against 73512. Both
are needed to say whether a line is coded correctly, and neither is on the register.

The guide is an untagged Microsoft Print To PDF and prints in two shapes:

  1  the account LISTS, two columns of "Number Description" under a group heading (1&&&& - CURRENT ASSETS)
  2  the data dictionary, "Number Title Description" where the title and the description both wrap over lines

Shape 2 is the one that matters and the one a naive line parser destroys: a row's description runs over two to
four printed lines and its title over one or two, so a row ends where the next account number begins and nowhere
else. Capture is therefore driven off the account number column: text is read with pdftotext -layout, a row
opens on a line whose first token is an account number, and every following line accrues to it until the next
one opens.

The title and the description are separated by COLUMN BAND, not by guessing where one sentence ends and the next
begins: each page prints its own "Number Title Description" header, which gives the character offset of each
column. Splitting on keywords instead produced "Supplies su" for 72113.

The rows themselves need one more rule, because the table's cells are VERTICALLY CENTRED. A two-line definition
puts its first line ABOVE the account number and its second BELOW, so a row does not begin at its number line and
a parser that assumes it does attributes half of every wrapped definition to the row before:

    72116   Dog Food                      Purchase of dog food for operations at Council's Animal
                                          Management Centre.

prints as three lines, with 72116 and "Dog Food" on the middle one. So a line carrying no number attaches to the
OPEN row while that row's definition has not yet reached a full stop, and otherwise waits for the next number.
That is the only signal the text layer carries, and it reads every wrapped row in this document correctly.

The band is finally applied to WHOLE SEGMENTS, never to a character offset. The description column shifts two or
three characters between pages, so slicing every line at the header's own offset cut words in half and produced
"Ex penses related to" and "Pu rchase of dog food". A line is split on runs of two or more spaces and each
segment is assigned to the column whose offset it starts nearest, which cannot split a word because a segment
boundary is always whitespace.

Account numbers are five characters: five digits (73126), or digits with an alpha in the fourth position for an
internal transaction (7B115, 6D312, 6A211). The register carries both forms.

The capture is checked against the register, which is the only independent evidence held: the register prints
each account's short description truncated by TechOne to fifteen characters, so a captured title must agree with
it. Of the 63 natural accounts this register uses, 62 are in the guide and 58 titles agree; the disagreements are
reported rather than quietly kept.

Usage: python3 pbr_chart_of_accounts.py <guide.pdf> [out.json]
       python3 pbr_chart_of_accounts.py --verify <chart.json> <register.xlsx>
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys

ACCT = re.compile(r'^([0-9][0-9A-Z][0-9A-Z0-9]{3})\b')
GROUP = re.compile(r'^([0-9])&+\s*-\s*(.+?)(?:\s+cont\'d)?\s*$')
NOISE = re.compile(r'^(Page \d+|Number\s+(Description|Title)|Data Dictionary.*|Natural Accounts?( List)?)\s*$', re.I)
REASON = re.compile(r'^([A-L])\s*-\s*(.+)$')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def norm(t):
    return ' '.join(str(t or '').split())


def layout_text(path):
    r = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


SEG = re.compile(r'\S(?:.*?\S)?(?=\s{2,}|$)')


def split_bands(line, bands):
    """Assign whole segments to the title or description column by which offset they start nearest. The columns
    shift two or three characters between pages, so a character slice cuts words; a segment boundary cannot."""
    t0, d0 = bands
    tt, dd = [], []
    for m in SEG.finditer(line):
        st = m.start()
        if st < t0 - 2:
            continue                                  # the number column
        (tt if abs(st - t0) <= abs(st - d0) else dd).append(m.group(0))
    return norm(' '.join(tt)), norm(' '.join(dd))


def capture(path):
    text = layout_text(path)
    group, groups = None, {}
    listed, dictionary, reasons = {}, {}, {}
    cur = None
    bands = None                      # (title offset, description offset) for the page being read
    pend_t, pend_d = [], []           # cell text printed ABOVE its own account number (cells are centred)
    for page in text.split('\f'):
        for raw in page.splitlines():
            line = raw.rstrip()
            s = norm(line)
            if not s:
                continue
            h = re.match(r'^(\s*)Number(\s+)(Title|Description)', line)
            if h:
                # the header names the columns and fixes their offsets for every body line on this page
                t0 = line.index(h.group(3))
                d0 = line.index('Description', t0 + 1) if h.group(3) == 'Title' and 'Description' in line[t0 + 1:] else None
                bands = (t0, d0) if h.group(3) == 'Title' else None
                cur = None
                pend_t, pend_d = [], []
                continue
            g = GROUP.match(s)
            if g:
                group = g.group(1)
                groups[group] = g.group(2).strip()
                cur = None
                continue
            if NOISE.match(s):
                cur = None
                continue
            r = REASON.match(s)
            if r and len(s) > 12:
                reasons[r.group(1)] = r.group(2).strip()
                continue
            pairs = re.findall(r'(?<![\w-])([0-9][0-9A-Z][0-9A-Z0-9]{3})\s{2,}([A-Za-z][^0-9]{2,50}?)(?=\s{2,}[0-9][0-9A-Z]|\s*$)', line)
            if len(pairs) >= 2:
                for num, desc in pairs:
                    listed.setdefault(num, dict(number=num, description=norm(desc)))
                cur = None
                continue
            m = ACCT.match(s)
            opens = m and (bands is None or line.index(m.group(1)) < bands[0])
            t, dsc = ('', '')
            if bands and bands[1]:
                t, dsc = split_bands(line, bands)
            if opens:
                num = m.group(1)
                if not (bands and bands[1]):
                    t, dsc = norm(s[len(num):]), ''
                elif not t and not dsc:
                    pass
                cur = dictionary.setdefault(num, dict(number=num, _t=[], _d=[]))
                cur['_t'] += pend_t
                cur['_d'] += pend_d
                pend_t, pend_d = [], []
                if t:
                    cur['_t'].append(t)
                if dsc:
                    cur['_d'].append(dsc)
                continue
            if not (t or dsc):
                continue
            # a continuation attaches to the open row until its definition reaches a full stop, then waits
            if cur is not None and not norm(' '.join(cur['_d'])).endswith('.'):
                if t:
                    cur['_t'].append(t)
                if dsc:
                    cur['_d'].append(dsc)
            else:
                if t:
                    pend_t.append(t)
                if dsc:
                    pend_d.append(dsc)
    for d in dictionary.values():
        d['title'] = norm(' '.join(d.pop('_t', [])))
        d['description'] = norm(' '.join(d.pop('_d', [])))
    for num, l in listed.items():
        if num in dictionary and not dictionary[num]['title']:
            dictionary[num]['title'] = l['description']
    accounts = []
    for num in sorted(set(listed) | set(dictionary)):
        d = dictionary.get(num, {})
        l = listed.get(num, {})
        accounts.append(dict(number=num, title=norm(d.get('title') or l.get('description', '')),
                             description=norm(d.get('description', '')),
                             group=num[0],          # the account group IS the first character, never the last heading seen
                             internal=bool(re.match(r'^[0-9][A-Z]', num)),
                             in_dictionary=num in dictionary, in_list=num in listed))
    return dict(manifest=dict(source=os.path.basename(path), md5=md5(path), tool='pbr_chart_of_accounts.py',
                              captured_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                              accounts=len(accounts), groups=groups,
                              in_dictionary=sum(1 for a in accounts if a['in_dictionary']),
                              list_only=sum(1 for a in accounts if not a['in_dictionary']),
                              without_description=sum(1 for a in accounts if not a['description']),
                              fbt_reason_codes=len(reasons)),
                fbt_reason_codes=reasons, accounts=accounts)


def verify(chart_path, reg_path):
    from python_calamine import CalamineWorkbook
    acct = {a['number']: a for a in json.load(open(chart_path))['accounts']}
    rows = CalamineWorkbook.from_path(reg_path).get_sheet_by_name('Register').to_python(skip_empty_area=False)
    use, short = {}, {}
    for r in rows[4:]:
        na = norm(r[13])
        if na:
            use[na] = use.get(na, 0) + 1
            short.setdefault(na, norm(r[14]))
    absent = sorted(n for n in use if n not in acct)
    agree, dis = 0, []
    for n in (n for n in use if n in acct):
        t = acct[n]['title'].upper().replace('&', 'AND')
        v = short[n].upper().rstrip(' .').replace('&', 'AND')
        if not v:
            continue
        if t.startswith(v[:min(len(v), 12)]) or v.startswith(t[:min(len(t), 12)]):
            agree += 1
        else:
            dis.append((n, short[n], acct[n]['title']))
    withdesc = sum(1 for n in use if n in acct and acct[n]['description'])
    print(f'natural accounts the register uses: {len(use)}')
    print(f'  in the guide: {len(use) - len(absent)} | not in the guide: {absent or "none"}')
    print(f'  title agrees with the register short description: {agree} | disagrees: {len(dis)}')
    print(f'  carrying a captured definition: {withdesc}')
    for n, v, t in dis:
        print(f'    DISAGREE {n}  register {v!r}  capture {t!r}')
    return len(dis)


def main():
    if sys.argv[1] == '--verify':
        sys.exit(1 if verify(sys.argv[2], sys.argv[3]) else 0)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'pbr_chart_of_accounts_v1.json')
    cap = capture(src)
    json.dump(cap, open(out, 'w'), indent=1)
    m = cap['manifest']
    print(f"captured {m['accounts']} accounts ({m['in_dictionary']} with a data dictionary entry, "
          f"{m['list_only']} listed only), {m['without_description']} without a description, "
          f"{m['fbt_reason_codes']} FBT reason codes, {len(m['groups'])} account groups")


if __name__ == '__main__':
    main()
