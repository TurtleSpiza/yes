"""pbr_env_check.py - prove the toolchain before a build depends on it.

The build chain fails late and misleadingly when a dependency is missing. The case that cost a
session: the container carried libreoffice-core but not libreoffice-calc, so the convert-route
recalc returned "Error: source file could not be loaded", which reads like a corrupt workbook and
is nothing of the kind. This runs each leg of the chain on a throwaway file and names the fix.

Checks
  1  Python version
  2  hard imports: python_calamine, openpyxl, lxml, cffi (_cffi_backend, see requirements.txt)
  3  toolkit modules import and their rule and manifest JSON parses
  4  openpyxl write -> LibreOffice convert-route recalc -> calamine read, with a live formula
  5  poppler: pdfinfo counts the page of a probe PDF built here and pdftotext -layout reads its text
  6  optional imports: pymupdf, pdfplumber, pypdf
  7  --all also byte-compiles every toolkit module (the project's lint gate)

Exit 0 when every hard check passes; exit 1 naming what to install. Usage:
    python3 toolkit/branch/pbr_env_check.py [--all] [--quiet]
"""
import importlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
FIX_PIP = 'pip install -r requirements.txt  (optional extras: requirements-optional.txt)'
FIX_APT = 'apt-get install -y poppler-utils libreoffice-calc'
rows = []


def rec(name, ok, detail, fix='', hard=True):
    rows.append(dict(name=name, ok=bool(ok), detail=str(detail), fix=fix, hard=hard))
    return ok


def check_python():
    v = sys.version_info
    rec('python', v >= (3, 11), f'{v.major}.{v.minor}.{v.micro}', 'Python 3.11 or newer')


def check_imports():
    for mod, why in (('python_calamine', 'workbook reads'), ('openpyxl', 'workbook writes'), ('lxml', 'v127 formula recovery'),
                     ('_cffi_backend', 'cffi; without it any cryptography import panics the interpreter')):
        try:
            m = importlib.import_module(mod)
            rec(mod, True, f'{getattr(m, "__version__", "installed")} ({why})')
        except Exception as e:
            rec(mod, False, f'{type(e).__name__}: {e}', FIX_PIP)
    for mod in ('pymupdf', 'pdfplumber', 'pypdf'):
        try:
            importlib.import_module(mod); rec(mod, True, 'installed (optional)', hard=False)
        except BaseException as e:  # BaseException: a pyo3 panic from a broken cryptography is not an Exception
            rec(mod, False, f'not importable (optional, only for ad hoc PDF inspection): {type(e).__name__}', FIX_PIP, hard=False)


def check_toolkit():
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(ROOT, 'toolkit', 'pswp'))
    for mod, why in (('pswp_json_repair', 'corpus gate'), ('pswp_shingle_check', 'verbatim check'),
                     ('pbr_stage', 'stage: rules and history manifest'), ('pbr_capture', 'rule 16/17 capture'),
                     ('pbr_build', 'build chain')):
        try:
            importlib.import_module(mod); rec(mod, True, f'imports ({why})')
        except Exception as e:
            rec(mod, False, f'{type(e).__name__}: {e}', 'check the repo is intact and requirements installed')


def check_recalc():
    """openpyxl write, convert-route recalc, calamine read. The formula must come back evaluated."""
    if not shutil.which('soffice'):
        return rec('soffice', False, 'not on PATH', FIX_APT)
    try:
        from openpyxl import Workbook
        from python_calamine import CalamineWorkbook
        sys.path.insert(0, HERE)
        from pbr_build import recalc            # the build's own routine, so this tests what ships
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'envcheck.xlsx')
            wb = Workbook(); ws = wb.active; ws.title = 'S'
            ws['A1'] = 2; ws['B1'] = 3; ws['C1'] = '=A1*B1'; ws['D1'] = '=IF(C1=6,"TRUE","FALSE")'
            wb.save(src)
            out = recalc(src, os.path.join(td, 'out'))
            row = CalamineWorkbook.from_path(out).get_sheet_by_name('S').to_python(skip_empty_area=False)[0]
            ok = row[2] == 6 and row[3] == 'TRUE'
            return rec('convert-route recalc', ok, 'formula evaluated by LibreOffice and read back by calamine' if ok
                       else f'recalc returned {row!r}; formulas did not evaluate', FIX_APT)
    except Exception as e:
        msg = f'{type(e).__name__}: {str(e)[:160]}'
        hint = FIX_APT if 'could not be loaded' in str(e) or 'no file' in str(e) else 'see the traceback'
        return rec('convert-route recalc', False, msg + ('  <- libreoffice-calc is missing, not a bad workbook' if hint == FIX_APT else ''), hint)


def _probe_pdf(text):
    """A minimal one-page PDF built here, so the poppler check depends on nothing else.
    (LibreOffice cannot make one from a .txt without Writer, which this project does not need.)"""
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>']
    stream = ('BT /F1 12 Tf 72 760 Td (%s) Tj ET' % text).encode()
    objs.append(b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    out, offs = bytearray(b'%PDF-1.4\n'), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for off in offs:
        out += b'%010d 00000 n \n' % off
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
    return bytes(out)


def check_poppler():
    missing = [t for t in ('pdftotext', 'pdfinfo') if not shutil.which(t)]
    for t in missing:
        rec(t, False, 'not on PATH', FIX_APT)
    if missing:
        return
    marker = 'PBR environment check line'
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, 'probe.pdf')
        open(pdf, 'wb').write(_probe_pdf(marker))
        info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
        pages = [l for l in info.splitlines() if l.startswith('Pages:')]
        rec('pdfinfo', bool(pages), pages[0] if pages else f'no page count in output: {info[:60]!r}', FIX_APT)
        back = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
        rec('pdftotext -layout', marker in back, 'text layer read back verbatim from a probe PDF' if marker in back
            else f'probe text not recovered: {back[:60]!r}', FIX_APT)


def check_compile():
    import compileall
    ok = compileall.compile_dir(os.path.join(ROOT, 'toolkit'), quiet=2, force=True)
    rec('toolkit byte-compiles', ok, 'every module in toolkit/ parses', 'fix the syntax error printed above')


def check_provenance():
    """The green-block provenance gate must be able to fail: replay the v2-to-v10 Levai values on a real invoice."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import pbr_provenance
        ok, msg = pbr_provenance.selftest()
    except Exception as e:                                        # noqa: BLE001
        ok, msg = False, f'{type(e).__name__}: {e}'
    rec('provenance self-test', bool(ok), str(msg)[:90],
        'pbr_provenance no longer refuses a field that is absent from its own document; do not ship until it does')


def main():
    quiet = '--quiet' in sys.argv
    check_python(); check_imports(); check_toolkit(); check_recalc(); check_poppler(); check_provenance()
    if '--all' in sys.argv:
        check_compile()
    hard_bad = [r for r in rows if r['hard'] and not r['ok']]
    soft_bad = [r for r in rows if not r['hard'] and not r['ok']]
    if not quiet or hard_bad:
        width = max(len(r['name']) for r in rows)
        for r in rows:
            mark = 'ok  ' if r['ok'] else ('FAIL' if r['hard'] else 'note')
            print(f'  [{mark}] {r["name"]:<{width}}  {r["detail"]}')
    if hard_bad:
        print('\nTOOLCHAIN NOT READY. Fix:')
        for f in dict.fromkeys(r['fix'] for r in hard_bad if r['fix']):
            print(f'    {f}')
        return 1
    print(f'toolchain ready: {len(rows) - len(soft_bad)} of {len(rows)} checks pass'
          + (f', {len(soft_bad)} optional package(s) absent' if soft_bad else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
