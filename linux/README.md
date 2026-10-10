# LofiGirl for Linux

A Linux port of the macOS app in the parent directory (`../src/main.swift`,
see `../README.md` for the full story). Same idea, rebuilt on GTK3 +
WebKit2GTK instead of AppKit + WebKit: a frameless window playing the Lofi
Girl live stream with no YouTube UI, hover controls for play/pause, quality,
Live, and close.

The injected page script (ad skipping, 1080p forcing, the Live button, and
the sticky play/pause intent that survives reloads) is copied verbatim from
the mac build — that part of the app is pure web JS and isn't
platform-specific. Only the native window shell is reimplemented.

## Requirements

- Python 3
- PyGObject, GTK3, and WebKit2GTK 4.1 (`webkit2gtk-4.1`/`webkit2gtk4.1` —
  package names vary by distro)

On Arch: `sudo pacman -S python-gobject gtk3 webkit2gtk-4.1`
On Debian/Ubuntu: `sudo apt install python3-gi gir1.2-webkit2-4.1 gir1.2-gtk-3.0`
On Fedora: `sudo dnf install python3-gobject webkit2gtk4.1 gtk3`

## Run it

```sh
cd linux
python3 main.py
```

## Install it (desktop entry + launcher on PATH)

```sh
cd linux
./install.sh
```

This copies the app to `~/.local/share/lofigirl`, adds a `lofigirl` script to
`~/.local/bin`, and registers a desktop entry + icon so it shows up in your
app launcher. Make sure `~/.local/bin` is on your `PATH`.

## Tiling window managers

This is meant to float as a small picture-in-picture window, not get tiled
into your layout. GTK asks for a floating, undecorated window, but some
tiling compositors (Hyprland, sway, i3, etc.) tile new windows by default
regardless. Add a float rule for it, e.g. for Hyprland in `hyprland.conf`:

```
windowrulev2 = float,class:^(lofigirl)$
```

For sway, in your config:

```
for_window [app_id="lofigirl"] floating enable
```

## Hardware/media keys

The app registers a minimal MPRIS2 player (`org.mpris.MediaPlayer2.lofigirl`)
so play/pause media keys work the way most Linux desktops route them — via
MPRIS, usually through a desktop media-key daemon or `playerctl`, not by
delivering the key to whichever window has focus. If your setup binds media
keys directly to a command (common on Hyprland/sway, which don't handle this
for you), bind them to `playerctl -p lofigirl play-pause` or similar. When
the app window itself has focus, pressing Play/Pause or Space also works
directly.

## Known limitations vs. the mac build

- **Rounded corners**: not drawn by the app itself. GTK3/WebKitGTK don't
  reliably clip a WebView's native rendering surface to a rounded shape
  across Wayland compositors, so this is skipped rather than half-working.
  Some compositors (Hyprland, KDE, etc.) round all window corners themselves
  regardless, which looks the same in practice.
- **Aspect-ratio lock while resizing**: only guaranteed when you drag from
  an edge/corner of the app's own window (the app computes the 16:9 size
  itself and drives the resize). If your compositor has its own native
  floating-resize mechanism — e.g. Hyprland's `resize_on_border` — that
  bypasses the app entirely and can leave the window any shape; the video
  just crops/stretches to fill it (`object-fit: cover`). There's no fix for
  that short of letterboxing the video (`object-fit: contain`) instead,
  which trades "always correct proportions" for visible black bars at
  non-16:9 sizes. Wayland has no protocol-level aspect-ratio hint a
  compositor would honor during its own resize grab (unlike X11's ICCCM
  hints), and post-hoc "snap back to 16:9 after the compositor resizes it"
  correction was tried and removed — it fed back with WebKitWebView's own
  internal layout requests and made the window drift through random sizes
  on its own, which is worse than an occasionally-wrong aspect ratio.
- **Sleep/wake nudge**: uses systemd-logind's `PrepareForSleep` signal over
  D-Bus. On a non-systemd system this silently does nothing (the enforced
  play/pause intent in the page script still protects against unwanted
  autoplay after a reload; it just won't get an extra nudge on wake).
- If the video area renders solid black with everything else working
  (page loads, controls respond), it's almost always WebKitGTK falling back
  to software video compositing in a VM or a GPU-less sandbox — check that
  VA-API/GL drivers are working, or try running with
  `WEBKIT_DISABLE_COMPOSITING_MODE=1`.

## Project layout

```
linux/main.py          Application (GTK3 + WebKit2GTK)
linux/lofigirl.png      App icon (composited from ../AppIcon.icon's layers)
linux/lofigirl.desktop  Desktop entry
linux/install.sh        Installs to ~/.local/{share,bin}
```
