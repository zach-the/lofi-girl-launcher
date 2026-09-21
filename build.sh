#!/bin/bash
# Build LofiGirl.app from source. Usage: ./build.sh [output-path]
set -euo pipefail
cd "$(dirname "$0")"

APP="${1:-$HOME/Applications/LofiGirl.app}"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

swiftc -O src/main.swift -o "$APP/Contents/MacOS/LofiGirl"
cp Info.plist "$APP/Contents/Info.plist"

# Use Xcode's toolchain for actool even if xcode-select points at the Command Line Tools.
if [ -z "${DEVELOPER_DIR:-}" ] && [ -d /Applications/Xcode.app ]; then
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
fi

# Icon: requires full Xcode (actool). Without it the app builds with the default icon.
if xcrun --find actool >/dev/null 2>&1; then
    tmp="$(mktemp -d)"
    xcrun actool AppIcon.icon --compile "$tmp" --platform macosx \
        --minimum-deployment-target 26.0 --app-icon AppIcon \
        --output-partial-info-plist "$tmp/partial.plist" >/dev/null
    cp "$tmp/Assets.car" "$tmp/AppIcon.icns" "$APP/Contents/Resources/"
    rm -rf "$tmp"
else
    echo "actool not found (install Xcode for the custom icon); skipping icon." >&2
fi

codesign -s - --force "$APP"
echo "Built $APP"
