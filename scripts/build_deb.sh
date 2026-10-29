#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
arch="$(dpkg --print-architecture)"
if [[ "$arch" != amd64 ]]; then
    echo 'This package build requires an amd64 host.' >&2
    exit 1
fi
if [[ ! -x dist/CodexPet ]]; then
    echo 'Build dist/CodexPet with PyInstaller first.' >&2
    exit 1
fi
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
chmod 755 "$stage"
install -d "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/256x256/apps" "$stage/usr/share/doc/codex-pet"
install -m 755 dist/CodexPet "$stage/usr/bin/codex-pet"
install -m 644 packaging/linux/codex-pet.desktop "$stage/usr/share/applications/"
install -m 644 LICENSE "$stage/usr/share/doc/codex-pet/copyright"
QT_QPA_PLATFORM=offscreen .venv/bin/python - "$stage/usr/share/icons/hicolor/256x256/apps/codex-pet.png" <<'PY'
import sys
from PyQt6.QtWidgets import QApplication
from scripts.make_icns import draw_icon
app = QApplication([])
if not draw_icon(256).save(sys.argv[1], "PNG"):
    raise SystemExit("Could not write application icon")
PY
chmod 644 "$stage/usr/share/icons/hicolor/256x256/apps/codex-pet.png"
size="$(du -sk "$stage/usr" | cut -f1)"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: codex-pet
Version: $version
Section: utils
Priority: optional
Architecture: $arch
Maintainer: Codex Pet contributors <noreply@github.com>
Installed-Size: $size
Depends: libc6 (>= 2.43), libstdc++6, libgl1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-util1, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shm0, libxcb-sync1, libxcb-xfixes0, libxcb-render0, libxcb-shape0, libxcb-xkb1, libxcb1, libx11-xcb1, libx11-6, libglib2.0-0, libfontconfig1, libfreetype6, libdbus-1-3
Description: Desktop Codex and DeepSeek balance monitor
 Displays Codex rate limits and DeepSeek balance in a floating desktop bar.
CONTROL
mkdir -p dist
dpkg-deb --build --root-owner-group "$stage" "dist/codex-pet_${version}_${arch}.deb"
