#!/usr/bin/env bash
# Build, sign and notarise the Mac app. Produces desktop/src-tauri/target/release/bundle/{macos,dmg}/.
#
# Unsigned (opens with right-click → Open on other Macs):
#   scripts/release-mac.sh
#
# Signed + notarised (needs an Apple Developer account, £79/yr):
#   export APPLE_SIGNING_IDENTITY="Developer ID Application: Craig Parker (TEAMID)"
#   export APPLE_ID="you@example.com" APPLE_PASSWORD="app-specific-password" APPLE_TEAM_ID="TEAMID"
#   scripts/release-mac.sh
# Tauri picks those variables up itself (https://v2.tauri.app/distribute/sign/macos/).
set -euo pipefail
cd "$(dirname "$0")/../desktop"
export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$PATH"

[ -d node_modules ] || npm install --no-audit --no-fund
[ -f src-tauri/icons/icon.icns ] || npm run icons

if [ -z "${APPLE_SIGNING_IDENTITY:-}" ]; then
  echo "APPLE_SIGNING_IDENTITY not set: building unsigned (Gatekeeper will warn on other Macs)."
fi
npm run build -- --bundles app,dmg

echo
echo "Built:"
ls -1 src-tauri/target/release/bundle/macos/*.app src-tauri/target/release/bundle/dmg/*.dmg
