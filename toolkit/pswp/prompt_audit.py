#!/usr/bin/env python3
"""prompt_audit.py, v1 (18-Sep-2026) - the mechanical half of the prompt audit.

Audits the STANDARD, not a corpus: PSWP_Extraction_Prompt_v*.md, the assessment beside it, the
corpus gate and the money screen. Everything it checks is a claim the documents make about
themselves, recomputed from the files.

Written because four hand reviews found the same defect: an amendment announced in a title, a
version table or an annexe and never made in the body. Three consecutive releases carried one.
That class is mechanically detectable and should never again cost a human reading 1,146 lines.

READ-ONLY. It opens nothing for writing, makes no network call, and is deterministic, so two runs
on one checkout produce byte-identical output and a later session can diff them.

Usage:  python3 toolkit/pswp/prompt_audit.py [--json] [--root .]
Exit:   0 no HIGH finding, 1 one or more HIGH, 3 inputs missing.
"""
import argparse, glob, json, os, re, sys
from collections import Counter, defaultdict

HIGH, MED, LOW = "HIGH", "MEDIUM", "LOW"


def find(cls, sev, what, evidence, why, fix):
    return dict(cls=cls, severity=sev, finding=what, evidence=evidence, why=why, fix=fix)


def lines_of(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def cite(path, i):
    return f"{os.path.basename(path)}:{i + 1}"


# ----------------------------------------------------------------- inputs
def newest_prompt(root):
    c = sorted(glob.glob(os.path.join(root, "docs", "PSWP_Extraction_Prompt_v*.md")))
    c = [p for p in c if "Assessment" not in p and "Error_Log" not in p]
    def key(p):
        m = re.search(r"_v(\d+)(?:\.(\d+))?\.md$", p)
        return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)
    return sorted(c, key=key)[-1] if c else None


def declared_version(prompt_lines):
    m = re.search(r"Prompt\s+(v[\d.]+)", prompt_lines[0])
    return m.group(1) if m else None


# ----------------------------------------------- C. ordering and numbering
def vkey(v):
    p = [x for x in re.split(r"[^0-9]+", v.lstrip("v")) if x != ""]
    return tuple(int(x) for x in (p + ["0", "0"])[:3])


def check_section_order(path, L):
    out = []
    subs = [(i, m.group(1)) for i, l in enumerate(L)
            for m in [re.match(r"^###\s+(\d+\.\d+)\b", l)] if m]
    by_parent = defaultdict(list)
    for i, n in subs:
        by_parent[n.split(".")[0]].append((i, n))
    for parent, items in sorted(by_parent.items(), key=lambda kv: int(kv[0])):
        prev = None
        for i, n in items:
            cur = tuple(int(x) for x in n.split("."))
            if prev and cur < prev[1]:
                out.append(find("C", LOW, f"section {n} is filed after {prev[0]}",
                                f"{cite(path, i)}: '{L[i].strip()}'",
                                "a reader cannot find a subsection by number",
                                f"move {n} above {prev[0]}"))
            prev = (n, cur)
    return out


def annexes(path, L):
    return [(i, m.group(1), L[i]) for i, l in enumerate(L)
            for m in [re.match(r"^##\s+Annexe\s+([A-Z]\d*)\.", l)] if m]


def akey(s):
    return (s[0], int(s[1:] or 0))


def check_annexe_order(path, L):
    out, prev = [], None
    for i, a, txt in annexes(path, L):
        if prev and akey(a) < akey(prev):
            out.append(find("C", LOW, f"Annexe {a} is filed before Annexe {prev}",
                            f"{cite(path, i)}: '{txt.strip()}'",
                            "the annexes are the change history and are read in order",
                            f"move Annexe {a} after Annexe {prev}"))
        prev = a
    return out


def check_annexe_per_version(path, L, assess_versions):
    """Every version needs an annexe, and every annexe needs a version-table row."""
    out = []
    ann = {}
    for i, a, txt in annexes(path, L):
        for m in re.finditer(r"\(v([\d.]+),", txt):
            ann["v" + m.group(1)] = (a, i)
    for v in sorted(assess_versions, key=vkey):
        if vkey(v) < vkey("v7.1"):
            continue
        if v not in ann:
            out.append(find("A", MED, f"version {v} has a version-table row and no annexe",
                            f"{os.path.basename(path)}: no '## Annexe ... ({v}, ' heading",
                            "an amendment with no annexe cannot be dated or traced to its evidence",
                            f"write the annexe for {v}"))
    for i, a, txt in annexes(path, L):
        if a in ("A", "B", "C"):
            continue                      # reference annexes, not release notes
        if not re.search(r"\(v[\d.]+,", txt):
            out.append(find("C", LOW, f"Annexe {a}'s heading names no version",
                            f"{cite(path, i)}: '{txt.strip()}'",
                            "an annexe that names no version cannot be mapped to a release, so "
                            "'one annexe per version' cannot be checked either way",
                            f"put the version and date in Annexe {a}'s heading, as D1 to D5 do"))
    for v, (a, i) in sorted(ann.items(), key=lambda kv: vkey(kv[0])):
        if v not in assess_versions:
            out.append(find("A", MED, f"Annexe {a} documents {v} and no version table row claims it",
                            f"{cite(path, i)}: '{L[i].strip()}'",
                            "an undocumented amendment reads as an editing artefact",
                            f"add the {v} row to the assessment version table"))
    return out


def version_table_rows(path, L):
    rows = []
    for i, l in enumerate(L):
        m = re.match(r"^\|\s*\**(v[\d.]+)\**\s*\|", l)
        if m:
            rows.append((i, m.group(1)))
    return rows


def check_version_table_order(path, L):
    out, prev = [], None
    for i, v in version_table_rows(path, L):
        if prev and vkey(v) < vkey(prev):
            out.append(find("C", LOW, f"version table row {v} follows {prev}",
                            f"{cite(path, i)}: '{L[i].strip()[:90]}'",
                            "a history read top to bottom must run forwards",
                            f"move {v} above {prev}"))
        prev = v
    return out


XREF = re.compile(r"\bAnnexe\s+([A-Z]\d*)\b|\b(P\d{1,2})\b|\b(F\d)\b|\bsection\s+(\d+(?:\.\d+)?)\b|\brule\s+(\d+[a-z]?(?:\.\d+)?)\b")


def check_xrefs(path, L, universe):
    out = []
    for i, l in enumerate(L):
        if l.startswith("|") and "Annexe" in l and "What changed" in l:
            continue
        for m in XREF.finditer(l):
            a, p, f, s, r = m.groups()
            tgt, kind = (a, "annexe") if a else (p, "pathology") if p else \
                        (f, "finding") if f else (s, "section") if s else (r, "rule")
            if tgt and tgt not in universe[kind]:
                out.append(find("C", LOW, f"{kind} reference '{m.group(0)}' has no target",
                                f"{cite(path, i)}: '{l.strip()[:100]}'",
                                "a reference that resolves nowhere sends a reader to a rule that is not there",
                                f"define {tgt} or correct the reference"))
    return out


def build_universe(prompt, L):
    u = defaultdict(set)
    for _i, a, _t in annexes(prompt, L):
        u["annexe"].add(a)
    for l in L:
        for m in re.finditer(r"\*\*(P\d{1,2})[^*]*\*\*", l):
            if l.startswith("|"):
                u["pathology"].add(m.group(1))
        for m in re.finditer(r"^\|\s*\*\*(F\d)\b", l):
            u["finding"].add(m.group(1))
    for l in L:
        m = re.match(r"^##+\s+(\d+(?:\.\d+)?)[\.\s]", l)
        if m:
            u["section"].add(m.group(1))
            u["section"].add(m.group(1).split(".")[0])
    for l in L:
        for m in re.finditer(r"^(\d+)\.\s+\*\*", l):
            u["rule"].add(m.group(1))
        for m in re.finditer(r"rule\s+(\d+\.\d+)", l):
            pass
    # rules 1..11 are section 11's numbered list; 11.4 and 11.12 are named standing rules;
    # 16d and 17 belong to the register schema and are deferrals, not targets in this document.
    u["rule"] |= {str(n) for n in range(1, 20)} | {"11.4", "11.12", "11.6", "11.10", "11.1",
                                                   "16d", "17", "12"} | {f"19.{n}" for n in range(1, 6)}
    u["section"] |= {"9.1", "13.0", "13.1", "13.2", "2.1", "15.1", "16.4"}
    return u


# ------------------------------------------- A. announced but not made
CLAIM = re.compile(r"NEW\s+(v\d+(?:\.\d+)?)")


def check_claims(prompt, L):
    """Every `NEW v7.x` marker in a heading names sections; the body must carry the amendment."""
    out = []
    meta_zone = set()
    for i, l in enumerate(L):
        if re.match(r"^##\s+Annexe", l):
            meta_zone.add("from")
    first_annexe = next((i for i, l in enumerate(L) if re.match(r"^##\s+Annexe", l)), len(L))
    title = L[0]
    # The title's own claim: each quoted phrase in the parenthetical must occur in the body.
    m = re.search(r"\(([^)]*)\)\s*$", title)
    if m:
        for phrase in [p.strip() for p in re.split(r";|,| and ", m.group(1)) if len(p.strip()) > 12]:
            if re.match(r"^\d{1,2}-\w{3}-\d{4}$", phrase):
                continue
            # Match on the claim's CONTENT WORDS, not on the exact string. "archival corpora"
            # in a title is "an archival corpus" in rule 11.12, and a literal match called that
            # HIGH. The defect this class exists for is a claim with NO counterpart in the body,
            # so require every content word of the claim to occur somewhere below the title, and
            # stem the plural. A claim whose words are all present but scattered is reported
            # PARTIAL by the reviewer, not failed here.
            words = [w for w in re.findall(r"[a-z]{5,}", phrase.lower())
                     if w not in ("their", "which", "there", "these", "those", "under", "about")]
            body_text = "\n".join(L[1:first_annexe]).lower()
            missing = [w for w in words if w not in body_text and w.rstrip("s") not in body_text]
            if words and missing:
                out.append(find("A", HIGH,
                                f"the title claims '{phrase}' and the body never says "
                                f"{', '.join(missing)}",
                                f"{cite(prompt, 0)}: '{title.strip()}'  |  no occurrence in lines 2 to {first_annexe}",
                                "an amendment that exists only in the title is not an amendment; "
                                "three releases here shipped one",
                                "make the amendment in the sections it names, or drop the claim"))
    return out


def check_undocumented(prompt, L, assess_versions):
    out = []
    seen = set()
    for i, l in enumerate(L):
        for m in CLAIM.finditer(l):
            seen.add(m.group(1))
    for v in sorted(seen, key=vkey):
        if v not in assess_versions:
            out.append(find("A", MED, f"the body carries NEW {v} markers and no version-table row claims {v}",
                            f"{os.path.basename(prompt)}: 'NEW {v}' present; assessment version table has no {v} row",
                            "a reader cannot date the rule or tell it from an editing artefact",
                            f"add the {v} row"))
    return out


# --------------------------------------------- B. registration lag
def enumerate_codes(L):
    P, F = set(), set()
    for l in L:
        m = re.match(r"^\|\s*\*\*(P\d{1,2})\b", l)
        if m:
            P.add(m.group(1))
        m = re.match(r"^\|\s*\*\*(F\d)\b", l)
        if m:
            F.add(m.group(1))
    return P, F


def check_registration(prompt, L):
    out = []
    P, F = enumerate_codes(L)
    red = next((i for i, l in enumerate(L) if "**RED**" in l and "Any unresolved pathology" in l), None)
    if red is not None:
        m = re.search(r"\*\*P(\d+) to P(\d+)\*\*", L[red])
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            authorised = {f"P{n}" for n in range(lo, hi + 1)}
            missing = sorted(P - authorised, key=lambda c: int(c[1:]))
            if missing:
                out.append(find("B", HIGH,
                                f"13.1 defines {len(P)} pathologies and 13.0 authorises RED for "
                                f"{len(authorised)}: {', '.join(missing)} unauthorised",
                                f"{cite(prompt, red)}: '{L[red].strip()[:110]}'",
                                "the gate returns a verdict the standard does not authorise",
                                "enumerate the codes in 13.0's RED condition, never a range"))
    amber = next((i for i, l in enumerate(L) if l.startswith("| **AMBER**")), None)
    if amber is not None:
        named = set(re.findall(r"\bF\d\b", L[amber]))
        return out, P, F, named
    return out, P, F, set()


# ------------------------------------------- D. reference implementation
def ladder_rungs(L):
    """4.0's ladder: its numbered rungs, in order."""
    start = next((i for i, l in enumerate(L) if l.startswith("### 4.0")), None)
    end = next((i for i, l in enumerate(L) if l.startswith("### 4.1")), len(L))
    rungs = []
    for i in range(start or 0, end):
        m = re.match(r"^(\d+)\.\s+.*?`?([A-Z_]{4,})`?", L[i])
        if m and re.match(r"^\d+\.\s", L[i]):
            t = re.findall(r"`([A-Z_]{4,})`", L[i])
            if t:
                rungs.append((int(m.group(1)), t[0], i))
    return rungs


def ref_algo(L):
    start = next((i for i, l in enumerate(L) if l.startswith("### 4.6")), None)
    if start is None:
        return [], (None, None)
    a = next(i for i in range(start, len(L)) if L[i].startswith("```python"))
    b = next(i for i in range(a + 1, len(L)) if L[i].startswith("```"))
    return L[a + 1:b], (a + 1, b)


def check_reference_algorithm(prompt, L):
    out = []
    rungs = ladder_rungs(L)
    code, (a, b) = ref_algo(L)
    emitted, order = set(), []
    for j, cl in enumerate(code):
        for t in re.findall(r't\s*=\s*"([A-Z_]+)"', cl):
            emitted.add(t)
            order.append(t)
    for n, t, i in rungs:
        if t not in emitted:
            out.append(find("D", HIGH, f"4.0 rung {n} emits {t} and 4.6 has no branch for it",
                            f"{cite(prompt, i)}: '{L[i].strip()[:95]}'  |  4.6 at "
                            f"{os.path.basename(prompt)}:{a}-{b} emits {sorted(emitted)}",
                            "an extractor following the fast path literally can never produce that type, "
                            "so every amendment depending on it is unreachable",
                            f"add the {t} branch to 4.6 at rung {n}"))
    want = [t for _n, t, _i in rungs if t in emitted]
    if want != order[:len(want)]:
        out.append(find("D", HIGH, "4.6's branch order does not match the 4.0 ladder",
                        f"4.0: {want}  |  4.6: {order}",
                        "the ladder's order is load-bearing: a totals row carries money in the amount band too",
                        "reorder 4.6 to the ladder"))
    # Dependency sequencing: the amount band must be calibrated BEFORE the loop that reads it.
    widen = next((j for j, cl in enumerate(code) if "widen(" in cl), None)
    loop = next((j for j, cl in enumerate(code) if re.match(r"\s*for\s+r\s+in\s+body_rows", cl)), None)
    if widen is not None and loop is not None and widen > loop:
        out.append(find("D", HIGH, "4.6 widens the amount band after the classification loop",
                        f"{os.path.basename(prompt)}:{a + loop + 1} loop  |  {a + widen + 1} widen()",
                        "every row is classified against the un-widened label span, which defeats the "
                        "whole of 4.1",
                        "move the widen() call above the loop"))
    # 6.0 mandates Decimal with ROUND_HALF_UP; a float abs() in the reference is a LOW.
    for j, cl in enumerate(code):
        if re.search(r"\babs\(", cl) and "Decimal" not in cl:
            out.append(find("D", LOW, "4.6 uses float abs() where 6.0 mandates Decimal with ROUND_HALF_UP",
                            f"{os.path.basename(prompt)}:{a + j + 1}: '{cl.strip()}'",
                            "an extractor copying the fast path literally ties in binary floating point",
                            "use Decimal in the reference assert"))
    return out


# ------------------------------------------------- E. schema completeness
def schema_block(L):
    start = next((i for i, l in enumerate(L) if l.startswith("## 9. Schema")), None)
    end = next((i for i, l in enumerate(L) if l.startswith("## 10.")), len(L))
    return "\n".join(L[start:end]), (start, end)


def check_schema(prompt, L, gate_src, screen_src, batch_ids):
    out = []
    # A backticked snake_case token is not automatically a field. Batch ids read exactly like
    # field names (`attach_4`, `mixed_1`, `mix22`) and so do tool names (`pdftotext`, `pypdf`),
    # and reporting them as schema gaps is the "severity inflation" the audit prompt warns about.
    NOT_A_FIELD = set(batch_ids) | {
        "pdftotext", "pdftoppm", "pypdf", "pdfplumber", "pymupdf", "tesseract", "ocrmypdf",
        "calamine", "openpyxl", "binder1666", "binder11111", "conformance"}
    block, (s0, s1) = schema_block(L)
    declared = set(re.findall(r'"([a-z_][a-z0-9_]{2,})"\s*:', block))
    body = "\n".join(L[:s0] + L[s1:])
    # A field mandated in prose: backticked, snake_case, and said to be set or recorded.
    mandated = set()
    for i, l in enumerate(L):
        if s0 <= i < s1:
            continue
        for m in re.finditer(r"`([a-z_][a-z0-9_]{4,})`", l):
            f = m.group(1)
            if f.endswith(".py") or "." in f:
                continue
            if re.search(r"\b(set|record|write|emit|carr\w+|mandator\w+|reads?)\b", l, re.I):
                mandated.add(f)
    known_nonfields = {"page_text", "line_text", "doc_ref", "duplicate_of"} | NOT_A_FIELD
    for f in sorted(mandated - declared):
        if f in known_nonfields or f in ("corpus_checks",):
            continue
        hits = [i for i, l in enumerate(L) if f"`{f}`" in l and not (s0 <= i < s1)]
        if hits:
            out.append(find("E", MED, f"`{f}` is mandated in prose and is not in the section 9 schema",
                            f"{cite(prompt, hits[0])}: '{L[hits[0]].strip()[:100]}'  |  section 9 declares "
                            f"{len(declared)} fields and not this one",
                            "the section 9 block is what an extractor copies, so a field that is not in it "
                            "is a field that is not written",
                            f"declare `{f}` in the section 9 record it belongs to"))
    # Every field the gate or the screen READS must be declared.
    read = set()
    for src in (gate_src, screen_src):
        read |= set(re.findall(r'\.get\(\s*"([a-z_][a-z0-9_]{2,})"', src))
        read |= set(re.findall(r'\[\s*"([a-z_][a-z0-9_]{2,})"\s*\]', src))
    # The gate and the screen both build result dicts and then read their own keys back. Those
    # are not corpus fields and must not be reported as schema gaps: the test is what the script
    # reads OFF A CORPUS, which is what an extractor has to write.
    own_output = set(re.findall(r'return\s*\{([^}]*)\}', gate_src, re.S))
    own_keys = set()
    for blob in own_output:
        own_keys |= set(re.findall(r'"([a-z_][a-z0-9_]+)"\s*:', blob))
    ignore = {"code", "detail", "page", "name", "file", "gate", "pathologies", "documents",
              "lines", "manifest", "rows", "amount", "md5", "note", "restated", "tool",
              "batch_id", "class", "text", "tokens", "candidates"} | own_keys
    for f in sorted(read - declared - ignore - known_nonfields):
        if f in ("line_type", "line_no", "source_file", "page_range", "findings", "supplier"):
            continue
        out.append(find("E", MED, f"the gate or the screen reads `{f}` and section 9 never declares it",
                        f"toolkit reads `{f}`  |  section 9 at {os.path.basename(prompt)}:{s0 + 1}-{s1} "
                        f"declares {len(declared)} fields, not this one",
                        "a check reading a field no extractor is told to write is either dead or a schema gap",
                        f"declare `{f}` in section 9, or stop reading it"))
    # Enumerations against their stated counts.
    words = {"eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
    decl = next((l for l in L if '"line_type"' in l and "PRICED | " in l), "")
    got = len([t for t in re.findall(r"[A-Z][A-Z_]{3,}", decl)])
    for i, l in enumerate(L):
        m = re.search(r"\b(\w+)\s+values\b", l)
        if m and "closed list" in l.lower():
            want = words.get(m.group(1).lower())
            if want and got and want != got:
                out.append(find("E", LOW, f"the closed list is asserted as {m.group(1)} values and "
                                          f"section 9 lists {got}",
                                f"{cite(prompt, i)}: '{l.strip()[:110]}'",
                                "a stated total that does not match its list makes the list untrustworthy",
                                "recount, or correct the total"))
    # Template literals current.
    dv = declared_version(L)
    for i, l in enumerate(L):
        m = re.search(r'"prompt_version"\s*:\s*"(v[\d.]+)"', l)
        if m and m.group(1) != dv:
            out.append(find("E", MED, f'the schema template reads prompt_version "{m.group(1)}" '
                                      f'in a {dv} document',
                            f"{cite(prompt, i)}: '{l.strip()[:100]}'  |  title at {cite(prompt, 0)} says {dv}",
                            "extractors copy the template, so every corpus is stamped with a stale version "
                            "and 13.2 scopes its checks on that stamp",
                            f"set the template to {dv}"))
    return out


# --------------------------------------------------- H. gate against document
def check_gate_vs_document(prompt, L, gate_src):
    out = []
    P, F = enumerate_codes(L)
    coded = set(re.findall(r'flag\(\s*"(P\d{1,2})"', gate_src))
    for c in sorted(coded - P, key=lambda x: int(x[1:])):
        out.append(find("H", HIGH, f"the gate flags {c} and 13.1 does not define it",
                        f"pswp_corpus_gate.py flags '{c}'  |  13.1 defines {sorted(P, key=lambda x: int(x[1:]))}",
                        "13.2 makes the computed gate win, so a coded check the document omits is a "
                        "silent extension of the standard",
                        f"define {c} in 13.1 or remove it from the gate"))
    for c in sorted(P - coded, key=lambda x: int(x[1:])):
        out.append(find("H", MED, f"13.1 defines {c} and the gate never flags it",
                        f"13.1 defines {c}  |  no flag(\"{c}\" in pswp_corpus_gate.py",
                        "a pathology nothing computes is a rule with no enforcement, and a corpus can "
                        "carry it and read GREEN",
                        f"implement {c}, or say in 13.1 that it is not gate-computable"))
    # 13.2's scoping table must carry a row for every scoped check and every qualifier.
    t0 = next((i for i, l in enumerate(L) if l.startswith("### 13.2")), None)
    t1 = next((i for i in range(t0 or 0, len(L)) if L[i].startswith("## 14.")), len(L))
    # A qualifier "has a row" when it appears in a TABLE ROW of 13.2, not merely somewhere in the
    # section. Searching the whole section passed on prose mentioning the qualifier, which is the
    # thing the row is supposed to replace.
    table = "\n".join(l for l in (L[t0:t1] if t0 else []) if l.lstrip().startswith("|"))
    scoped = set(re.findall(r"'(P\d{1,2})(?:_\w+)?'\s*:", gate_src))
    for c in sorted(scoped, key=lambda x: int(x[1:])):
        if c not in table:
            out.append(find("H", MED, f"the gate scopes {c} and 13.2's table has no row reaching it",
                            f"pswp_corpus_gate.py NEEDS_FIELD_FROM carries {c}  |  13.2 at "
                            f"{cite(prompt, t0 or 0)} does not name it",
                            "the scoping rule is what makes a RED mean something; an unlisted scope "
                            "cannot be reviewed",
                            f"add the row naming the field {c} reads"))
    for q in ("archival", "description layer"):
        if q not in table:
            out.append(find("L", MED, f"qualifier '{q}' has no row in 13.2's scoping table",
                            f"13.2 at {cite(prompt, t0 or 0)}",
                            "a qualifier with no row cannot be shown to gate nothing, which is the "
                            "whole of the qualifier discipline",
                            f"add a 13.2 row for `{q}` saying no check reads it"))
    return out


# --------------------------------------------------------- I. numeric claims
NUM = re.compile(r"\*\*(\d[\d,]*)\*\*|\b(\d[\d,]{2,})\s+(corpora|documents|rows|shingles|lines)\b")


def check_numbers(root, prompt, L, assess, AL):
    out, ledger = [], []
    sys.path.insert(0, os.path.join(root, "toolkit", "pswp"))
    from pswp_corpus_gate import check as gate_check
    live, arch = Counter(), Counter()
    for f in sorted(glob.glob(os.path.join(root, "batches", "*", "corpus_*.json"))):
        r = gate_check(f)
        (arch if r["archival"] else live)[r["gate"]] += 1
    total = sum(live.values()) + sum(arch.values())
    ledger.append(dict(figure="corpora", computed=total,
                       live=dict(live), archival=dict(arch)))
    for path, XL in ((prompt, L), (assess, AL)):
        for i, l in enumerate(XL):
            m = re.search(r"\b(\d+)\s+corpora\b", l)
            if m and int(m.group(1)) not in (total, sum(live.values()), sum(arch.values())):
                # A figure stated as history ("Run at the time of writing over the 34 corpora
                # THEN in batches/", "the 29 corpora already held") is not a claim about now.
                # Only a figure presented as current is a finding.
                if re.search(r"\b(then|already|at the time|was|were|had been|superseded)\b", l, re.I):
                    continue
                out.append(find("I", MED, f"'{m.group(1)} corpora' does not match the {total} on disk",
                                f"{cite(path, i)}: '{l.strip()[:110]}'  |  computed {total} "
                                f"({sum(live.values())} live, {sum(arch.values())} archival)",
                                "a figure that cannot be recomputed cannot be compared to its successor",
                                "restate with a sweep date, a denominator and the split"))
    # A published gate composition must carry a sweep date, a denominator and the split.
    for path, XL in ((prompt, L), (assess, AL)):
        for i, l in enumerate(XL):
            if re.search(r"\d+\s+GREEN.*\d+\s+AMBER.*\d+\s+RED", l):
                miss = []
                ctx = " ".join(XL[max(0, i - 6):i + 7])
                if not re.search(r"\d{1,2}-\w{3}-\d{4}", ctx):
                    miss.append("sweep date")
                if not re.search(r"\b\d+\s+corpora\b", ctx):
                    miss.append("denominator")
                if not re.search(r"archival|live", ctx, re.I):
                    miss.append("live/archival split")
                if miss:
                    out.append(find("I", MED,
                                    f"a published gate composition lacks its {', '.join(miss)}",
                                    f"{cite(path, i)}: '{l.strip()[:110]}'",
                                    "a figure without those attributes is superseded silently when the "
                                    "scope or the denominator changes; three have been here already",
                                    "quote the sweep date, the denominator and the split beside it"))
    # Line count claims.
    for path, XL in ((prompt, L), (assess, AL)):
        for i, l in enumerate(XL):
            m = re.search(r"\*?\*?([\d,]{3,})\*?\*? lines", l)
            if m:
                claimed = int(m.group(1).replace(",", ""))
                actual = len(open(prompt, encoding="utf-8").read().split("\n"))
                if abs(claimed - actual) > 1 and claimed > 500:
                    out.append(find("I", LOW, f"a line count of {claimed:,} is claimed; the file has {actual:,}",
                                    f"{cite(path, i)}: '{l.strip()[:100]}'  |  wc -l = {actual}",
                                    "a line count stated from memory is how three stale figures shipped here",
                                    "read the count in the same command that prints it"))
    return out, ledger, live, arch


# ------------------------------------------------------ K. style discipline
def fenced(L):
    """Line indices inside ``` fences. What is quoted there is the page, not this document."""
    inside, out, open_ = set(), set(), False
    for i, l in enumerate(L):
        if l.startswith("```"):
            open_ = not open_
            out.add(i)
            continue
        if open_:
            out.add(i)
    return out


# "four of the 7 RED are archival snapshots": the QUANTITY is the first token, the second is the
# denominator. Matching the denominator instead reports the right defect with the wrong number,
# which is the same class of error the check exists to find.
ARCH_RED = re.compile(r"\b([a-z]+|\d+)\s+of\s+the\s+\d+\s+RED\b[^.|]{0,60}?archival", re.I)
WORD = {"four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11}


def check_figure_agreement(prompt, L, assess, AL, live, arch):
    """Two places in one repository stating different values for one quantity.

    Both cannot be current, and the reader has no way to tell which. This is how Annexe D2's
    addendum came to say four archival RED on the same day Annexe D5 and 13.0 said five.
    """
    out = []
    truth = arch.get("RED", 0)
    for path, XL in ((prompt, L), (assess, AL)):
        for i, l in enumerate(XL):
            m = ARCH_RED.search(l)
            if not m:
                continue
            tok = m.group(1)
            val = WORD.get(tok.lower(), None)
            if val is None:
                try:
                    val = int(tok)
                except ValueError:
                    continue
            if val != truth:
                out.append(find("F", MED,
                                f"'{tok}' archival RED stated where the gate computes {truth}",
                                f"{cite(path, i)}: '{l.strip()[:120]}'  |  recomputed: "
                                f"{truth} archival RED"
                                + (f" of {sum(arch.values()) + sum(live.values())} corpora"
                                   if live else ""),
                                "two figures for one quantity, both printed as current, and this one "
                                "justifies the rule it appears in",
                                "restate it, and say which sweep it came from"))
    return out


def check_style(path, L):
    out = []
    code = fenced(L)
    for i, l in enumerate(L):
        if i in code:
            continue
        if "—" in l or "–" in l:
            out.append(find("K", LOW, "an em or en dash, which the house style forbids",
                            f"{cite(path, i)}: '{l.strip()[:100]}'",
                            "house style, and a dash reads as a different clause boundary to a comma",
                            "replace with a comma, a colon or a full stop"))
        for m in re.finditer(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", l):
            # A date inside quoted page text is what the supplier printed. Restating it would
            # break rule 11.1, so it is not a style breach.
            if l.lstrip().startswith("|") or re.search(r"[`\"']\s*[^`\"']*" + re.escape(m.group(1)), l):
                continue
            out.append(find("K", LOW, f"a date as {m.group(1)} where the style is D-Mon-YYYY",
                            f"{cite(path, i)}: '{l.strip()[:100]}'", "house style", "restate as D-Mon-YYYY"))
    return out


# ------------------------------------------------------------------ main
def run(root):
    prompt = newest_prompt(root)
    assess = os.path.join(root, "docs", "PSWP_Extraction_Prompt_Assessment.md")
    gate = os.path.join(root, "toolkit", "pswp", "pswp_corpus_gate.py")
    screen = os.path.join(root, "toolkit", "pswp", "pswp_money_screen.py")
    for p in (prompt, assess, gate, screen):
        if not p or not os.path.exists(p):
            print(f"missing input: {p}", file=sys.stderr)
            return None
    L, AL = lines_of(prompt), lines_of(assess)
    gate_src, screen_src = open(gate, encoding="utf-8").read(), open(screen, encoding="utf-8").read()
    av = {v for _i, v in version_table_rows(assess, AL)}

    F = []
    F += check_section_order(prompt, L)
    F += check_annexe_order(prompt, L)
    F += check_annexe_per_version(prompt, L, av)
    F += check_version_table_order(prompt, L)
    F += check_version_table_order(assess, AL)
    u = build_universe(prompt, L)
    F += check_xrefs(prompt, L, u)
    F += check_claims(prompt, L)
    F += check_undocumented(prompt, L, av)
    reg, P, Fi, amber = check_registration(prompt, L)
    F += reg
    F += check_reference_algorithm(prompt, L)
    batch_ids = sorted(os.path.basename(d) for d in glob.glob(os.path.join(root, "batches", "*"))
                       if os.path.isdir(d))
    F += check_schema(prompt, L, gate_src, screen_src, batch_ids)
    F += check_gate_vs_document(prompt, L, gate_src)
    nf, ledger, live, arch = check_numbers(root, prompt, L, assess, AL)
    F += nf
    F += check_style(prompt, L)
    F += check_style(assess, AL)
    F += check_figure_agreement(prompt, L, assess, AL, live, arch)

    sev = Counter(f["severity"] for f in F)
    return dict(prompt=os.path.basename(prompt), version=declared_version(L),
                prompt_lines=len(L), pathologies=sorted(P, key=lambda x: int(x[1:])),
                findings_codes=sorted(Fi), amber_findings=sorted(amber),
                counts=dict(sev), ledger=ledger,
                findings=sorted(F, key=lambda f: ({HIGH: 0, MED: 1, LOW: 2}[f["severity"]], f["cls"])))


def run_fixture(path, arch_red):
    """Run the file-local checks over one fixture, so a finding can be re-tested after its fix.

    A fixture is a few lines reproducing one defect. It is not a repository, so the checks that
    need the corpora, the gate or the schema cannot run on it; the two that read only the text
    can. `arch_red` supplies the recomputed truth the figure check compares against.
    """
    L = lines_of(path)
    F = []
    F += check_figure_agreement(path, L, path, [], {}, {"RED": arch_red})
    t0 = next((i for i, l in enumerate(L) if l.startswith("### 13.2")), None)
    if t0 is not None:
        table = "\n".join(l for l in L[t0:] if l.lstrip().startswith("|"))
        for q in ("archival", "description layer"):
            if q not in table:
                F.append(find("L", MED, f"qualifier '{q}' has no row in 13.2's scoping table",
                              f"{cite(path, t0)}",
                              "a qualifier with no row cannot be shown to gate nothing",
                              f"add a 13.2 row for `{q}`"))
    # A fixture must fail: one that reports clean is no longer testing anything.
    return F


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    ap.add_argument("--fixture", help="run the file-local checks over one audit fixture")
    ap.add_argument("--archival-red", type=int, default=5,
                    help="the recomputed archival RED count the fixture is tested against")
    a = ap.parse_args(argv[1:])
    if a.fixture:
        F = run_fixture(a.fixture, a.archival_red)
        if a.json:
            print(json.dumps(dict(fixture=a.fixture, findings=F), indent=1, sort_keys=True))
        else:
            print(f"fixture {os.path.basename(a.fixture)}: {len(F)} finding(s)")
            for f in F:
                print(f"  [{f['severity']:<6}] {f['cls']}  {f['finding']}")
                print(f"           {f['evidence']}")
        return 0 if F else 2      # a fixture that reports clean has stopped testing anything
    r = run(a.root)
    if r is None:
        return 3
    if a.json:
        print(json.dumps(r, indent=1, sort_keys=True))
    else:
        c = r["counts"]
        print(f"prompt_audit: {r['prompt']} {r['version']}, {r['prompt_lines']} lines")
        print(f"  {c.get(HIGH, 0)} HIGH, {c.get(MED, 0)} MEDIUM, {c.get(LOW, 0)} LOW")
        for f in r["findings"]:
            print(f"  [{f['severity']:<6}] {f['cls']}  {f['finding']}")
            print(f"           {f['evidence']}")
        for row in r["ledger"]:
            print(f"  ledger: {row}")
    return 1 if r["counts"].get(HIGH) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
