#!/usr/bin/env bash
# lo_recalc.sh - the convert-route recalc, standalone.
#
# The ONLY sanctioned recalc route (rule 18). recalc.py, the macro route, is banned: it
# hangs in the container. The isolated profile must carry OOXMLRecalcMode=0, or LibreOffice
# loads the cached values and the converted file ships with every formula stale, which is
# indistinguishable from a real pass unless a control is expected to change.
#
#   ./lo_recalc.sh input.xlsx outdir
set -euo pipefail
SRC="$1"; OUT="${2:-$(dirname "$SRC")/recalc}"
PROFILE="$(mktemp -d /tmp/lo_profile.XXXXXX)"
mkdir -p "$PROFILE/user" "$OUT"
cat > "$PROFILE/user/registrymodifications.xcu" <<'XCU'
<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
XCU
grep -q "OOXMLRecalcMode" "$PROFILE/user/registrymodifications.xcu" || { echo "profile assertion failed"; exit 1; }
echo "recalc: converting $(basename "$SRC")"
time soffice -env:UserInstallation="file://$PROFILE" --headless --norestore \
     --convert-to xlsx --outdir "$OUT" "$SRC"
rm -rf "$PROFILE"
echo "recalc: wrote $OUT/$(basename "$SRC")"
