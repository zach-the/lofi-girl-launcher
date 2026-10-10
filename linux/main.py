#!/usr/bin/env python3
"""LofiGirl: minimal Lofi Girl YouTube player, frameless picture-in-picture window.

Linux port of the macOS app (../src/main.swift). Same idea: a borderless
WebKit view playing the Lofi Girl live stream, with hover controls and no
YouTube UI. See ../README.md for the full story and ./README.md for the
Linux-specific notes (deps, window-manager float rules, limitations).
"""
import json
import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2  # noqa: E402

VIDEO_URL = "https://www.youtube.com/watch?v=rFZHOHl-L8A"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
EDGE = 24  # px, resize hit area from any edge/corner
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lofigirl.png")
CONFIG_PATH = os.path.join(
    GLib.get_user_config_dir(), "lofigirl", "state.json"
)

JS = r"""
(function(){
  window.lofiHD=__HD__;
  var st=document.createElement('style');
  st.textContent='html,body{background:#000!important;overflow:hidden!important}body>*:not(#lofi-ov){visibility:hidden!important}'+
   '#lofi-ov{position:fixed;inset:0;background:#000;z-index:2147483647}'+
   '#lofi-ov video{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;object-fit:cover!important;transform:none!important;left:0!important;top:0!important}';
  document.documentElement.appendChild(st);
  var ov=document.createElement('div'); ov.id='lofi-ov'; document.documentElement.appendChild(ov);
  // window.lofiShouldPlay is sticky user intent, not a mirror of reality: it only ever
  // changes from an explicit user action (lofiToggle, lofiGoLive), never from what the
  // video happens to be doing. It survives a page reload via localStorage (kept for
  // this origin across sleep/wake and app relaunches), and it is enforced on every
  // tick, indefinitely -- not just right after load. A one-shot correction is not
  // enough: YouTube's own player script can (re)start the stream on its own well after
  // load (e.g. after a quality change we trigger), and a fixed settling window can
  // lose that race. Enforcing forever, driven only by explicit intent, is immune to it.
  window.lofiShouldPlay = localStorage.getItem('lofiShouldPlay') !== '0';
  function setIntent(play){
    window.lofiShouldPlay = play;
    localStorage.setItem('lofiShouldPlay', play ? '1' : '0');
  }
  // Hardware/keyboard media keys route through the page's Media Session API, not
  // through our own button, so a media-key pause would otherwise look identical to
  // YouTube's own unprompted autoplay (the thing the enforcement loop above is meant
  // to override) and get immediately fought and undone. Own these handlers so a media
  // key updates intent the same way tapping our button does. YouTube can reassert its
  // own handlers later (e.g. around an ad or a quality change), so reclaim ours on
  // every tick rather than once.
  function installMediaKeyHandlers(){
    if(!navigator.mediaSession) return;
    navigator.mediaSession.setActionHandler('play', function(){ var v=document.querySelector('video'); if(v) v.play().catch(function(){}); setIntent(true); });
    navigator.mediaSession.setActionHandler('pause', function(){ var v=document.querySelector('video'); if(v) v.pause(); setIntent(false); });
  }
  setInterval(function(){
    var v=document.querySelector('video'); if(!v) return;
    if(v.parentNode!==ov){ ov.appendChild(v); }
    installMediaKeyHandlers();
    if(window.lofiShouldPlay && v.paused){ v.play().catch(function(){}); }
    else if(!window.lofiShouldPlay && !v.paused){ v.pause(); }
  },300);
  setInterval(function(){
    var p=document.getElementById('movie_player');
    if(p&&window.lofiHD&&p.setPlaybackQualityRange&&p.getPlaybackQuality&&p.getPlaybackQuality()!=='hd1080'){
      try{p.setPlaybackQualityRange('hd1080','hd1080');p.setPlaybackQuality('hd1080');}catch(e){}
    }
  },2000);
  var adMuted=false;
  setInterval(function(){
    var p=document.getElementById('movie_player'), v=document.querySelector('video'); if(!p||!v) return;
    var ad=p.classList.contains('ad-showing');
    if(ad){
      adMuted=true; v.muted=true;
      var b=document.querySelector('.ytp-skip-ad-button,.ytp-ad-skip-button,.ytp-ad-skip-button-modern,.ytp-ad-skip-button-container button'); if(b) b.click();
      if(isFinite(v.duration)&&v.duration>0) v.currentTime=v.duration;
    } else if(adMuted){ adMuted=false; v.muted=false; }
  },250);
  window.lofiSetHD=function(on){
    window.lofiHD=on;
    var p=document.getElementById('movie_player'); if(!p||!p.setPlaybackQualityRange) return;
    try{ if(on){p.setPlaybackQualityRange('hd1080','hd1080');p.setPlaybackQuality('hd1080');} else {p.setPlaybackQualityRange('auto','auto');} }catch(e){}
  };
  window.lofiToggle=function(){
    var v=document.querySelector('video'); if(!v)return false;
    if(v.paused){v.play();}else{v.pause();}
    setIntent(!v.paused);
    return !v.paused;
  };
  window.lofiIsPlaying=function(){var v=document.querySelector('video'); return v?!v.paused:null;};
  window.lofiGoLive=function(){
    var v=document.querySelector('video'); if(!v) return;
    var badge=document.querySelector('.ytp-live-badge');
    if(badge){ badge.click(); }
    else if(isFinite(v.duration)&&v.duration>0){ v.currentTime=v.duration; }
    v.play().catch(function(){});
    setIntent(true);
  };
  window.lofiNudge=function(){var v=document.querySelector('video'); if(v) v.play().catch(function(){});};
})();
"""

CSS = b"""
window { background-color: transparent; }
.lofi-transparent { background-color: transparent; background-image: none; }
.lofi-bar {
  background-color: rgba(0, 0, 0, 0.55);
  min-height: 28px;
}
.lofi-bar button {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 2px 6px;
  color: #ffffff;
}
.lofi-bar button:hover { background: rgba(255, 255, 255, 0.15); }
.lofi-bar image { color: #ffffff; }
.lofi-bar label { color: #ffffff; font-size: 11px; font-weight: 600; }
"""


def load_state():
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return bool(data.get("playing", True)), bool(data.get("hd", True))
    except (OSError, ValueError):
        return True, True


def save_state(playing, hd):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"playing": playing, "hd": hd}, f)
    except OSError:
        pass


class MprisService:
    """Minimal MPRIS2 player so Linux hardware/media keys (routed through
    playerctl, GNOME/KDE media-key daemons, etc.) can play/pause this app
    the same way macOS media keys drive the WKWebView's Media Session."""

    INTROSPECTION = """
    <node>
      <interface name="org.mpris.MediaPlayer2">
        <method name="Raise"/>
        <method name="Quit"/>
        <property name="CanQuit" type="b" access="read"/>
        <property name="CanRaise" type="b" access="read"/>
        <property name="HasTrackList" type="b" access="read"/>
        <property name="Identity" type="s" access="read"/>
        <property name="SupportedUriSchemes" type="as" access="read"/>
        <property name="SupportedMimeTypes" type="as" access="read"/>
      </interface>
      <interface name="org.mpris.MediaPlayer2.Player">
        <method name="Play"/>
        <method name="Pause"/>
        <method name="PlayPause"/>
        <method name="Stop"/>
        <method name="Next"/>
        <method name="Previous"/>
        <property name="PlaybackStatus" type="s" access="read"/>
        <property name="CanPlay" type="b" access="read"/>
        <property name="CanPause" type="b" access="read"/>
        <property name="CanGoNext" type="b" access="read"/>
        <property name="CanGoPrevious" type="b" access="read"/>
        <property name="CanSeek" type="b" access="read"/>
        <property name="CanControl" type="b" access="read"/>
      </interface>
    </node>
    """

    def __init__(self, on_play, on_pause, on_playpause):
        self.on_play = on_play
        self.on_pause = on_pause
        self.on_playpause = on_playpause
        self.playing = True
        self._node_info = Gio.DBusNodeInfo.new_for_xml(self.INTROSPECTION)
        self._registration_ids = []
        self._bus = None
        Gio.bus_own_name(
            Gio.BusType.SESSION,
            "org.mpris.MediaPlayer2.lofigirl",
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            None,
            None,
        )

    def _on_bus_acquired(self, connection, name):
        self._bus = connection
        for iface in self._node_info.interfaces:
            reg_id = connection.register_object(
                "/org/mpris/MediaPlayer2",
                iface,
                self._handle_method_call,
                self._handle_get_property,
                None,
            )
            self._registration_ids.append(reg_id)

    def _handle_method_call(
        self, connection, sender, path, interface, method, params, invocation
    ):
        if method == "PlayPause":
            self.on_playpause()
        elif method == "Play":
            self.on_play()
        elif method == "Pause":
            self.on_pause()
        # Quit/Raise/Stop/Next/Previous: no-op, just acknowledge.
        invocation.return_value(None)

    def _handle_get_property(self, connection, sender, path, interface, name):
        if interface == "org.mpris.MediaPlayer2":
            if name == "CanQuit":
                return GLib.Variant("b", False)
            if name == "CanRaise":
                return GLib.Variant("b", False)
            if name == "HasTrackList":
                return GLib.Variant("b", False)
            if name == "Identity":
                return GLib.Variant("s", "LofiGirl")
            if name == "SupportedUriSchemes":
                return GLib.Variant("as", [])
            if name == "SupportedMimeTypes":
                return GLib.Variant("as", [])
        elif interface == "org.mpris.MediaPlayer2.Player":
            if name == "PlaybackStatus":
                return GLib.Variant("s", "Playing" if self.playing else "Paused")
            if name in ("CanPlay", "CanPause", "CanControl"):
                return GLib.Variant("b", True)
            if name in ("CanGoNext", "CanGoPrevious", "CanSeek"):
                return GLib.Variant("b", False)
        return None

    def set_playing(self, playing):
        if playing == self.playing:
            return
        self.playing = playing
        if self._bus is None:
            return
        status = "Playing" if playing else "Paused"
        self._bus.emit_signal(
            None,
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant(
                "(sa{sv}as)",
                (
                    "org.mpris.MediaPlayer2.Player",
                    {"PlaybackStatus": GLib.Variant("s", status)},
                    [],
                ),
            ),
        )


class LofiGirlWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.playing, self.hd = load_state()

        self.set_title("LofiGirl")
        self.set_decorated(False)
        self.set_resizable(True)
        self.set_default_size(480, 270)
        # Aspect ratio is enforced entirely by our own code (live during a
        # drag in _on_motion, after the fact in _on_size_allocate) rather
        # than this hint's ASPECT flag: GTK/the Wayland backend apply that
        # hint with their own rounding and timing, which fought our manual
        # corrections rather than complementing them (a forced resize could
        # come back at a completely unrelated size, e.g. 600x600 -> 1164x290
        # instead of settling on width x width*9/16).
        geometry = Gdk.Geometry()
        geometry.min_width, geometry.min_height = 240, 135
        self.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE)
        if os.path.exists(ICON_PATH):
            self.set_icon_from_file(ICON_PATH)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.webview = self._build_webview()
        self.bar, self.play_btn, self.quality_btn = self._build_bar()

        overlay = Gtk.Overlay()
        overlay.add(self.webview)

        # These need a real GdkWindow (the default for EventBox) rather than
        # a windowless widget: WebKitWebView paints through its own native
        # surface, and only a sibling with its own window is guaranteed to
        # sit above it in actual window-stacking order and receive pointer
        # events, regardless of GTK's logical widget z-order. Left fully
        # transparent via CSS so the video shows through underneath.
        drag_box = Gtk.EventBox()
        drag_box.get_style_context().add_class("lofi-transparent")
        drag_box.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        drag_box.connect("button-press-event", self._on_button_press)
        drag_box.connect("motion-notify-event", self._on_motion)
        drag_box.connect("button-release-event", self._on_button_release)
        drag_box.connect("enter-notify-event", self._on_hover_enter)
        drag_box.connect("leave-notify-event", self._on_hover_leave)
        overlay.add_overlay(drag_box)
        overlay.set_overlay_pass_through(drag_box, False)

        # Wrapping the bar in its own EventBox makes the buttons genuine
        # children of its GdkWindow, so moving the pointer onto a button
        # reports as an INFERIOR leave (filtered out below) instead of a
        # real one -- otherwise hovering a button would read as leaving the
        # bar and it would fade out from under the cursor.
        bar_box = Gtk.EventBox()
        bar_box.get_style_context().add_class("lofi-transparent")
        bar_box.add(self.bar)
        bar_box.connect("enter-notify-event", self._on_hover_enter)
        bar_box.connect("leave-notify-event", self._on_hover_leave)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.revealer.set_transition_duration(200)
        self.revealer.set_halign(Gtk.Align.FILL)
        self.revealer.set_valign(Gtk.Align.START)
        self.revealer.add(bar_box)
        overlay.add_overlay(self.revealer)

        self.add(overlay)

        self.connect("key-press-event", self._on_key_press)
        self._hide_timeout = None
        self._resizing = False
        self._resize_edges = (False, False, False, False)
        self._resize_start_pointer = (0, 0)
        self._resize_start_size = (480, 270)

        GLib.timeout_add_seconds(1, self._sync_play_state)

        self.mpris = MprisService(
            on_play=lambda: self._set_playing(True),
            on_pause=lambda: self._set_playing(False),
            on_playpause=lambda: self._set_playing(not self.playing),
        )

        self._watch_sleep_wake()

    # -- UI construction -------------------------------------------------

    def _build_webview(self):
        content_manager = WebKit2.UserContentManager()
        script_source = JS.replace("__HD__", "true" if self.hd else "false")
        content_manager.add_script(
            WebKit2.UserScript(
                script_source,
                WebKit2.UserContentInjectedFrames.TOP_FRAME,
                WebKit2.UserScriptInjectionTime.END,
                None,
                None,
            )
        )
        webview = WebKit2.WebView.new_with_user_content_manager(content_manager)
        settings = webview.get_settings()
        settings.set_user_agent(USER_AGENT)
        settings.set_media_playback_requires_user_gesture(False)
        webview.load_uri(VIDEO_URL)
        return webview

    def _build_bar(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.get_style_context().add_class("lofi-bar")
        bar.set_margin_start(4)
        bar.set_margin_top(2)
        bar.set_margin_bottom(2)

        close_btn = Gtk.Button()
        close_btn.add(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR))
        close_btn.connect("clicked", lambda _b: self.close())
        bar.pack_start(close_btn, False, False, 0)

        play_btn = Gtk.Button()
        play_btn.add(Gtk.Image.new_from_icon_name(self._play_icon_name(), Gtk.IconSize.SMALL_TOOLBAR))
        play_btn.connect("clicked", lambda _b: self._toggle())
        bar.pack_start(play_btn, False, False, 0)

        quality_btn = Gtk.Button(label=self._quality_label())
        quality_btn.connect("clicked", lambda _b: self._toggle_quality())
        bar.pack_start(quality_btn, False, False, 0)

        live_btn = Gtk.Button(label="Live")
        live_btn.connect("clicked", lambda _b: self._go_live())
        bar.pack_start(live_btn, False, False, 0)

        return bar, play_btn, quality_btn

    def _play_icon_name(self):
        return "media-playback-pause-symbolic" if self.playing else "media-playback-start-symbolic"

    def _quality_label(self):
        return "1080p" if self.hd else "Auto"

    # -- Hover reveal (with a short grace period so moving from the drag
    #    overlay onto the bar itself doesn't flicker it closed) ---------

    def _on_hover_enter(self, _widget, _event):
        if self._hide_timeout is not None:
            GLib.source_remove(self._hide_timeout)
            self._hide_timeout = None
        self.revealer.set_reveal_child(True)
        return False

    def _on_hover_leave(self, _widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        if self._hide_timeout is not None:
            GLib.source_remove(self._hide_timeout)
        self._hide_timeout = GLib.timeout_add(80, self._do_hide)
        return False

    def _do_hide(self):
        self.revealer.set_reveal_child(False)
        self._hide_timeout = None
        return False

    # -- Drag to move, drag from an edge/corner to resize ----------------
    #
    # Moving delegates to the compositor (begin_move_drag) since Wayland
    # clients can't reposition themselves directly anyway. Resizing does
    # NOT delegate to begin_resize_drag: that hands the whole gesture to
    # the compositor, which has no idea we want to stay locked to 16:9, so
    # our own correction would end up fighting its live grab and flicker
    # at whichever edge was being dragged. A client CAN resize itself
    # freely on Wayland (unlike moving), so we drive the resize ourselves
    # from raw pointer motion instead -- the same approach, and the same
    # aspect math, as the mac build's DragOverlay.

    def _on_button_press(self, widget, event):
        if event.button != 1:
            return False
        alloc = widget.get_allocation()
        left = event.x < EDGE
        right = event.x > alloc.width - EDGE
        top = event.y < EDGE
        bottom = event.y > alloc.height - EDGE
        if not (left or right or top or bottom):
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        self._resize_edges = (left, right, top, bottom)
        self._resize_start_pointer = (event.x_root, event.y_root)
        self._resize_start_size = (alloc.width, alloc.height)
        seat = widget.get_display().get_default_seat()
        seat.grab(
            widget.get_window(),
            Gdk.SeatCapabilities.POINTER,
            False,
            None,
            event,
            None,
            None,
        )
        self._resizing = True
        return True

    def _on_motion(self, _widget, event):
        if not self._resizing:
            return False
        left, right, top, bottom = self._resize_edges
        sx, sy = self._resize_start_pointer
        sw, _sh = self._resize_start_size
        dx, dy = event.x_root - sx, event.y_root - sy
        nw = sw
        if right:
            nw += dx
        elif left:
            nw -= dx
        else:
            nw += (dy if bottom else -dy) * 16 / 9
        nw = max(240, nw)
        nh = round(nw * 9 / 16)
        self.resize(round(nw), nh)
        return True

    def _on_button_release(self, widget, _event):
        if self._resizing:
            self._resizing = False
            widget.get_display().get_default_seat().ungrab()
        return False

    # -- Button actions ---------------------------------------------------
    #
    # There's no post-hoc "snap back to 16:9" correction here for resizes
    # that happen outside our own drag handlers above (e.g. Hyprland's
    # native border-drag resize, from resize_on_border). An earlier attempt
    # at that got into a feedback loop with WebKitWebView's own internal
    # layout requests and made the window drift through wildly different
    # sizes on its own. Wayland also has no protocol-level "lock aspect
    # ratio" hint a compositor would honor during its own resize grab (the
    # X11 ICCCM hint the mac build's platform provides has no equivalent
    # here), so this is accepted as a real platform limitation rather than
    # fought: the window can end up any shape when resized that way, and
    # the video crops/stretches to fill it (object-fit: cover, in JS above).

    def _run_js(self, script):
        self.webview.evaluate_javascript(script, -1, None, None, None, None, None)

    def _toggle(self):
        self._run_js("window.lofiToggle()")
        self._set_playing(not self.playing)

    def _set_playing(self, playing):
        self.playing = playing
        save_state(self.playing, self.hd)
        self.play_btn.get_child().set_from_icon_name(self._play_icon_name(), Gtk.IconSize.SMALL_TOOLBAR)
        self.mpris.set_playing(playing)
        if playing:
            self._run_js("window.lofiShouldPlay=true; localStorage.setItem('lofiShouldPlay','1'); window.lofiNudge();")
        else:
            self._run_js("window.lofiToggle && (function(){var v=document.querySelector('video'); if(v && !v.paused){window.lofiToggle();}})();")

    def _toggle_quality(self):
        self.hd = not self.hd
        save_state(self.playing, self.hd)
        self._run_js(f"window.lofiSetHD({'true' if self.hd else 'false'})")
        self.quality_btn.set_label(self._quality_label())

    def _go_live(self):
        self._run_js("window.lofiGoLive()")
        self._set_playing(True)

    def _on_key_press(self, _widget, event):
        keyval = event.keyval
        if keyval in (Gdk.KEY_AudioPlay, Gdk.KEY_AudioPause):
            self._toggle()
            return True
        if keyval == Gdk.KEY_space:
            self._toggle()
            return True
        return False

    # -- Keep the play/pause icon honest even when the video pauses
    #    itself (buffering, a dropped connection), same as the mac build.

    def _sync_play_state(self):
        def on_result(webview, task, _data):
            try:
                value = webview.evaluate_javascript_finish(task)
                is_playing = value.to_boolean()
            except GLib.Error:
                return
            if is_playing != self.playing:
                self.playing = is_playing
                save_state(self.playing, self.hd)
                self.play_btn.get_child().set_from_icon_name(
                    self._play_icon_name(), Gtk.IconSize.SMALL_TOOLBAR
                )
                self.mpris.set_playing(is_playing)

        self.webview.evaluate_javascript("window.lofiIsPlaying()", -1, None, None, None, on_result, None)
        return True

    # -- systemd-logind sleep/wake, analogous to NSWorkspace.didWakeNotification

    def _watch_sleep_wake(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        except GLib.Error:
            return
        bus.signal_subscribe(
            "org.freedesktop.login1",
            "org.freedesktop.login1.Manager",
            "PrepareForSleep",
            "/org/freedesktop/login1",
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_prepare_for_sleep,
        )

    def _on_prepare_for_sleep(self, _conn, _sender, _path, _iface, _signal, params):
        going_to_sleep = params.unpack()[0]
        if going_to_sleep:
            return
        # Waking up: only nudge playback if we were actually supposed to be
        # playing, mirroring the mac build's didWakeNotification handler.
        if self.playing:
            self._run_js("window.lofiNudge()")
        self._sync_play_state()


def main():
    GLib.set_prgname("lofigirl")
    win = LofiGirlWindow()
    win.connect("destroy", lambda _w: Gtk.main_quit())
    win.show_all()
    win.present()
    Gtk.main()


if __name__ == "__main__":
    main()
