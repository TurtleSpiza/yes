#!/bin/bash
# SessionStart hook: make the register toolchain ready before the session does any work.
#
# Idempotent and non-interactive. On a container that already has everything it costs about two
# seconds; on a cold one it installs poppler-utils, tesseract-ocr, libreoffice-calc, the Python requirements
# and the document-conversion set (OCRmyPDF and Docling), which is the slow part at roughly 6GB.
# The last step proves the chain end to end rather than assuming the installs worked.
set -euo pipefail

# Web sessions only. A local checkout keeps its own environment; run the two commands this prints
# by hand if you want the same setup there.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"
SUDO=""
[ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"

echo "[session-start] LCC Parks register toolchain"

# ---------------------------------------------------------------- system packages
# Checked by presence, so this is a no-op on a warm container. libreoffice-calc is checked through
# dpkg rather than the soffice binary, because libreoffice-core installs soffice WITHOUT Calc and
# every convert-route recalc then fails with a message that reads like a corrupt workbook.
# tesseract-ocr is required, not optional. A supplier that prints its letterhead as an IMAGE (Vinton) carries its
# entity name and ABN nowhere in the text layer, so rule 8 identity cannot be read without OCR, and a session that
# discovers this mid-build has to stop and install it.
need=()
command -v pdftotext >/dev/null 2>&1 || need+=(poppler-utils)
command -v tesseract >/dev/null 2>&1 || need+=(tesseract-ocr)
if command -v dpkg >/dev/null 2>&1; then
  dpkg -s libreoffice-calc >/dev/null 2>&1 || need+=(libreoffice-calc)
elif ! command -v soffice >/dev/null 2>&1; then
  need+=(libreoffice-calc)
fi
if [ ${#need[@]} -gt 0 ]; then
  echo "[session-start] installing system packages: ${need[*]}"
  $SUDO apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${need[@]}" \
    || { echo "[session-start] apt install failed; retrying once after a fresh index"
         $SUDO apt-get update -qq || true
         DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${need[@]}" || true; }
else
  echo "[session-start] system packages already present (poppler-utils, libreoffice-calc, tesseract-ocr)"
fi

# ---------------------------------------------------------------- python packages
# No --upgrade: the container's Debian-installed cryptography has no RECORD file, so an upgrade
# attempt fails the whole run. Pinned versions are satisfied without touching it.
echo "[session-start] installing Python requirements"
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements.txt \
  || { echo "[session-start] pip install failed; retrying once"
       python3 -m pip install --disable-pip-version-check --root-user-action=ignore -r requirements.txt \
         2>&1 | tail -3; }
# cffi must be importable as _cffi_backend before anything touches the optional set: the container's
# Debian cryptography panics the interpreter without it. Re-install explicitly if the pin did not land.
if ! python3 -c "import _cffi_backend" >/dev/null 2>&1; then
  echo "[session-start] _cffi_backend missing after requirements install; installing cffi explicitly"
  python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore cffi
fi
python3 -c "import _cffi_backend" >/dev/null 2>&1 \
  && echo "[session-start] cffi present (_cffi_backend imports)" \
  || echo "[session-start] WARNING: cffi still not importable; the env check below will fail on it"
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements-optional.txt \
  || echo "[session-start] note: optional PDF inspection packages did not install; the build chain does not need them"

# ---------------------------------------------------------------- document conversion (OCRmyPDF, Docling)
# OCRmyPDF writes a real text layer back into a scanned or image-borne PDF, so pdftotext then reads what a
# letterhead prints as an image. It is installed from PIP, not apt: the Debian package pins an old pikepdf whose
# extension fails to import on this container, and the apt binary is then unusable.
# Docling converts a PDF to structured markdown with its tables intact. It is NOT a replacement for a gate: it
# reports "orphan cell recovered by nearest-column fallback" on this project's own invoices, which is a guess, so
# whatever it produces is still evidence to be checked, never a figure to be trusted.
if ! command -v ocrmypdf >/dev/null 2>&1 || ! ocrmypdf --version >/dev/null 2>&1; then
  echo "[session-start] installing OCRmyPDF (pip; the apt build pins a broken pikepdf)"
  $SUDO apt-get remove -y -qq ocrmypdf >/dev/null 2>&1 || true
  python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore ocrmypdf \
    || echo "[session-start] WARNING: ocrmypdf did not install; an image-borne PDF cannot be given a text layer"
fi
if ! python3 -c "import docling" >/dev/null 2>&1; then
  echo "[session-start] installing Docling (large: ~6GB with torch, several minutes on a cold container)"
  # antlr4-python3-runtime 4.9.3 ships only an sdist and its setup.py dies on Debian's patched setuptools
  # (AttributeError: install_layout). A wheel built in a clean venv satisfies omegaconf's pin without that path.
  if ! python3 -c "import antlr4" >/dev/null 2>&1; then
    _a4=$(mktemp -d)
    if python3 -m pip download -q --no-deps --no-cache-dir "antlr4-python3-runtime==4.9.3" -d "$_a4" 2>/dev/null; then
      tar xzf "$_a4"/*.tar.gz -C "$_a4" 2>/dev/null
      python3 -m venv --clear "$_a4/venv" >/dev/null 2>&1 \
        && "$_a4/venv/bin/pip" install -q "setuptools<70" wheel >/dev/null 2>&1 \
        && (cd "$_a4"/antlr4-python3-runtime-4.9.3 && "$_a4/venv/bin/python" setup.py -q bdist_wheel >/dev/null 2>&1) \
        && python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore \
             "$_a4"/antlr4-python3-runtime-4.9.3/dist/*.whl >/dev/null 2>&1
    fi
    rm -rf "$_a4"
  fi
  # --ignore-installed rich: Debian's rich has no RECORD file, so pip cannot uninstall it and the run aborts.
  python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore --ignore-installed rich docling \
    || echo "[session-start] WARNING: docling did not install; the build chain does not need it"
fi
python3 -c "import docling" >/dev/null 2>&1 \
  && echo "[session-start] document conversion ready (ocrmypdf, docling)" \
  || echo "[session-start] document conversion: ocrmypdf only (docling unavailable)"

# ---------------------------------------------------------------- the six the build chain cannot run without
# calamine, openpyxl, lxml and cffi are pip; poppler and libreoffice-calc are apt. Everything else in this hook is
# a convenience that a session can work around. These six are not: without calamine nothing reads a register,
# without openpyxl nothing writes one, without lxml the v127 formula text cannot be recovered, without cffi any
# cryptography import panics the interpreter, without poppler no invoice can be read from a PDF, and without
# libreoffice-calc every recalc fails with a message that reads like a corrupt workbook.
#
# Each is proved by USE, not by presence, and a missing one is repaired here and then reported by name, because a
# session that finds out at the recalc step has already spent the build.
core_missing=()
python3 -c "import python_calamine" >/dev/null 2>&1 || core_missing+=(python-calamine)
python3 -c "import openpyxl"       >/dev/null 2>&1 || core_missing+=(openpyxl)
python3 -c "import lxml.etree"     >/dev/null 2>&1 || core_missing+=(lxml)
python3 -c "import _cffi_backend"  >/dev/null 2>&1 || core_missing+=(cffi)
if [ ${#core_missing[@]} -gt 0 ]; then
  echo "[session-start] core python missing after install: ${core_missing[*]}; repairing"
  python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore --ignore-installed "${core_missing[@]}" \
    2>&1 | tail -2 || true
fi
core_sys=()
command -v pdftotext >/dev/null 2>&1 || core_sys+=(poppler-utils)
if command -v dpkg >/dev/null 2>&1; then
  dpkg -s libreoffice-calc >/dev/null 2>&1 || core_sys+=(libreoffice-calc)
fi
if [ ${#core_sys[@]} -gt 0 ]; then
  echo "[session-start] core system packages missing after install: ${core_sys[*]}; repairing"
  $SUDO apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${core_sys[@]}" || true
fi
# Report the pinned version each of the four landed at, so a silent drift from requirements.txt is visible here
# rather than in a build that behaves differently from the one a register was verified on.
python3 - <<'PYCHK'
import importlib.metadata as md, re, sys
pins = {}
for line in open('requirements.txt'):
    m = re.match(r'^([A-Za-z0-9_.\-]+)==([^\s#]+)', line.strip())
    if m:
        pins[m.group(1)] = m.group(2)
bad = []
for name, want in pins.items():
    try:
        got = md.version(name)
    except Exception:
        bad.append(f'{name} MISSING (pinned {want})'); continue
    if got != want:
        bad.append(f'{name} {got} against pinned {want}')
print('[session-start] core python: ' + ', '.join(f'{k} {pins[k]}' for k in pins) + (' (all at pin)' if not bad else ''))
if bad:
    print('[session-start] WARNING: version drift from requirements.txt: ' + '; '.join(bad))
PYCHK

# ---------------------------------------------------------------- session environment
# Lets any session run `python3 -c "import pbr_stage"` from any directory.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PYTHONPATH=\"$ROOT/toolkit/branch:$ROOT/toolkit/pswp\${PYTHONPATH:+:\$PYTHONPATH}\""
    echo "export PBR_ROOT=\"$ROOT\""
  } >> "$CLAUDE_ENV_FILE"
fi

# ---------------------------------------------------------------- prove it
# Writes a workbook with a live formula, recalculates it through LibreOffice, reads it back with
# calamine, and round-trips a probe PDF through poppler. Non-zero here means the chain is not ready.
if python3 toolkit/branch/pbr_env_check.py --all; then
  echo "[session-start] ready. Build: python3 toolkit/branch/pbr_build.py"
else
  echo "[session-start] ####################################################################"
  echo "[session-start] TOOLCHAIN NOT READY - the checks above name the missing dependency."
  echo "[session-start] Do not run pbr_build.py until they pass; a build would fail at recalc."
  echo "[session-start] ####################################################################"
fi
