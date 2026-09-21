#!/bin/bash
# Build the app and package it into dist/LofiGirl.app and dist/LofiGirl.dmg.
set -euo pipefail
cd "$(dirname "$0")"

rm -rf dist && mkdir -p dist
./build.sh dist/LofiGirl.app

stage="$(mktemp -d)"
cp -R dist/LofiGirl.app "$stage/"
ln -s /Applications "$stage/Applications"
hdiutil create -volname "LofiGirl" -srcfolder "$stage" -ov -format UDZO dist/LofiGirl.dmg >/dev/null
rm -rf "$stage"
echo "Packaged dist/LofiGirl.dmg"
