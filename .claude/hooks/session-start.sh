#!/bin/bash
# SessionStart hook: make the register toolchain ready before the session does any work.
#
# Idempotent and non-interactive. On a container that already has everything it costs about two
# seconds; on a cold one it installs poppler-utils, libreoffice-calc and three Python packages.
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
need=()
command -v pdftotext >/dev/null 2>&1 || need+=(poppler-utils)
if command -v dpkg >/dev/null 2>&1; then
  dpkg -s libreoffice-calc >/dev/null 2>&1 || need+=(libreoffice-calc)
elif ! command -v soffice >/dev/null 2>&1; then
  need+=(libreoffice-calc)
fi
if [ ${#need[@]} -gt 0 ]; then
  echo "[session-start] installing system packages: ${need[*]}"
  $SUDO apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${need[@]}"
else
  echo "[session-start] system packages already present (poppler-utils, libreoffice-calc)"
fi

# ---------------------------------------------------------------- python packages
# No --upgrade: the container's Debian-installed cryptography has no RECORD file, so an upgrade
# attempt fails the whole run. Pinned versions are satisfied without touching it.
echo "[session-start] installing Python requirements"
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements.txt
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements-optional.txt \
  || echo "[session-start] note: optional PDF inspection packages did not install; the build chain does not need them"

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
