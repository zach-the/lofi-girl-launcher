#!/bin/bash
# Install LofiGirl for the current user: copies the app into
# ~/.local/share/lofigirl, drops a launcher script on PATH, and registers
# a desktop entry + icon so it shows up in an app launcher.
set -euo pipefail
cd "$(dirname "$0")"

APP_DIR="$HOME/.local/share/lofigirl"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
DESKTOP_DIR="$HOME/.local/share/applications"

mkdir -p "$APP_DIR" "$BIN_DIR" "$ICON_DIR" "$DESKTOP_DIR"
cp main.py "$APP_DIR/main.py"
cp lofigirl.png "$APP_DIR/lofigirl.png"
cp lofigirl.png "$ICON_DIR/lofigirl.png"
cat > "$BIN_DIR/lofigirl" <<EOF
#!/bin/bash
exec python3 "$APP_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/lofigirl"

# Use an absolute Exec= path: app-launcher "run" dialogs (wofi/rofi run mode,
# etc.) and even some drun-style launchers spawn commands via the systemd
# user session's PATH, which commonly does not include ~/.local/bin even
# when an interactive shell's PATH does (that's usually added by
# .bashrc/.profile, which graphical launchers don't source).
sed "s|^Exec=.*|Exec=$BIN_DIR/lofigirl|" lofigirl.desktop > "$DESKTOP_DIR/lofigirl.desktop"

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

mkdir -p "$HOME/.config/environment.d"
ENV_DROPIN="$HOME/.config/environment.d/60-local-bin.conf"
if [ ! -f "$ENV_DROPIN" ] || ! grep -q '.local/bin' "$ENV_DROPIN" 2>/dev/null; then
    echo 'PATH=${PATH}:'"$BIN_DIR" >> "$ENV_DROPIN"
    echo "Added $BIN_DIR to your systemd user session PATH ($ENV_DROPIN)."
    echo "Log out and back in (or reboot) for that to take effect for app launchers."
fi

echo "Installed. Run: lofigirl (works right away from a terminal)"
echo "It should also now appear in your application launcher as LofiGirl."
