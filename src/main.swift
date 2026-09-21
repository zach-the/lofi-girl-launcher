import Cocoa
import WebKit

let videoID = "FZHOHI-L8A"  // Lofi Girl live

let js = """
(function(){
  window.lofiHD=__HD__;
  var st=document.createElement('style');
  st.textContent='html,body{background:#000!important;overflow:hidden!important}body>*:not(#lofi-ov){visibility:hidden!important}'+
   '#lofi-ov{position:fixed;inset:0;background:#000;z-index:2147483647}'+
   '#lofi-ov video{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;object-fit:cover!important;transform:none!important;left:0!important;top:0!important}';
  document.documentElement.appendChild(st);
  var ov=document.createElement('div'); ov.id='lofi-ov'; document.documentElement.appendChild(ov);
  setInterval(function(){
    var v=document.querySelector('video'); if(!v) return;
    if(v.parentNode!==ov){ var wasPlaying=!v.paused; ov.appendChild(v); if(wasPlaying||!window.__started){window.__started=true;v.play().catch(function(){});} }
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
  window.lofiToggle=function(){var v=document.querySelector('video'); if(!v)return false; if(v.paused){v.play();}else{v.pause();} return !v.paused;};
})();
"""

final class DragBar: NSView {
    override var mouseDownCanMoveWindow: Bool { true }
    override func mouseDown(with event: NSEvent) { window?.performDrag(with: event) }
}

final class DragOverlay: NSView {
    override var mouseDownCanMoveWindow: Bool { false }
    override func mouseDown(with e: NSEvent) {
        guard let w = window else { return }
        let p = convert(e.locationInWindow, from: nil), m: CGFloat = 16
        let l = p.x < m, r = p.x > bounds.width - m, b = p.y < m, t = p.y > bounds.height - m
        if !(l || r || b || t) { w.performDrag(with: e); return }
        let sf = w.frame, start = NSEvent.mouseLocation
        while let ev = w.nextEvent(matching: [.leftMouseDragged, .leftMouseUp]), ev.type != .leftMouseUp {
            let cur = NSEvent.mouseLocation, dx = cur.x - start.x, dy = cur.y - start.y
            var nw = sf.width
            if r { nw += dx } else if l { nw -= dx } else { nw += (t ? dy : -dy) * 16 / 9 }
            nw = max(w.minSize.width, nw)
            let nh = nw * 9 / 16
            var f = NSRect(x: sf.minX, y: sf.maxY - nh, width: nw, height: nh)
            if l { f.origin.x = sf.maxX - nw }
            if t && !b && !l && !r { f.origin.y = sf.minY }
            w.setFrame(f, display: true)
        }
    }
}

final class Win: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
}

final class Root: NSView {
    let web: WKWebView
    let bar = DragBar()
    let overlay = DragOverlay()
    let playBtn = NSButton()
    let closeBtn = NSButton()
    let qualityBtn = NSButton()
    var playing = true
    var hd = UserDefaults.standard.object(forKey: "hd") as? Bool ?? true

    init(web: WKWebView) {
        self.web = web
        super.init(frame: .zero)
        web.autoresizingMask = [.width, .height]
        addSubview(web)
        wantsLayer = true
        layer?.cornerRadius = 14
        layer?.cornerCurve = .continuous
        layer?.masksToBounds = true
        overlay.autoresizingMask = [.width, .height]
        addSubview(overlay)
        bar.wantsLayer = true
        bar.layer?.backgroundColor = NSColor.black.withAlphaComponent(0.55).cgColor
        bar.autoresizingMask = [.width, .minYMargin]
        addSubview(bar)
        for (b, sym, sel) in [(closeBtn, "xmark", #selector(quit)), (playBtn, "pause.fill", #selector(toggle))] {
            b.image = NSImage(systemSymbolName: sym, accessibilityDescription: nil)
            b.isBordered = false; b.contentTintColor = .white
            b.target = self; b.action = sel
            bar.addSubview(b)
        }
        qualityBtn.isBordered = false
        qualityBtn.font = .systemFont(ofSize: 11, weight: .semibold)
        qualityBtn.contentTintColor = .white
        qualityBtn.target = self; qualityBtn.action = #selector(toggleQuality)
        updateQualityTitle()
        bar.addSubview(qualityBtn)
        bar.alphaValue = 0
        addTrackingArea(NSTrackingArea(rect: .zero, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect], owner: self))
    }
    required init?(coder: NSCoder) { fatalError() }

    override func layout() {
        super.layout()
        web.frame = bounds
        overlay.frame = bounds
        bar.frame = NSRect(x: 0, y: bounds.height - 28, width: bounds.width, height: 28)
        closeBtn.frame = NSRect(x: 6, y: 4, width: 20, height: 20)
        playBtn.frame = NSRect(x: 32, y: 4, width: 20, height: 20)
        qualityBtn.frame = NSRect(x: 58, y: 4, width: 52, height: 20)
    }
    override func mouseEntered(with e: NSEvent) { NSAnimationContext.runAnimationGroup { $0.duration = 0.15; bar.animator().alphaValue = 1 } }
    override func mouseExited(with e: NSEvent) { NSAnimationContext.runAnimationGroup { $0.duration = 0.3; bar.animator().alphaValue = 0 } }
    func updateQualityTitle() { qualityBtn.title = hd ? "1080p" : "Auto" }
    @objc func toggleQuality() {
        hd.toggle()
        UserDefaults.standard.set(hd, forKey: "hd")
        web.evaluateJavaScript("window.lofiSetHD(\(hd))")
        updateQualityTitle()
    }
    @objc func quit() { NSApp.terminate(nil) }
    @objc func toggle() {
        playing.toggle()
        web.evaluateJavaScript("window.lofiToggle()")
        playBtn.image = NSImage(systemSymbolName: playing ? "pause.fill" : "play.fill", accessibilityDescription: nil)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var win: Win!
    func applicationDidFinishLaunching(_ n: Notification) {
        let cfg = WKWebViewConfiguration()
        cfg.mediaTypesRequiringUserActionForPlayback = []
        let web = WKWebView(frame: .zero, configuration: cfg)
        web.customUserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        web.setValue(false, forKey: "drawsBackground")
        cfg.userContentController.addUserScript(WKUserScript(source: js.replacingOccurrences(of: "__HD__", with: (UserDefaults.standard.object(forKey: "hd") as? Bool ?? true) ? "true" : "false"), injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        web.load(URLRequest(url: URL(string: "https://www.youtube.com/watch?v=rFZHOHl-L8A")!))

        win = Win(contentRect: NSRect(x: 0, y: 0, width: 480, height: 270),
                  styleMask: [.borderless, .resizable], backing: .buffered, defer: false)
        win.contentView = Root(web: web)
        win.contentAspectRatio = NSSize(width: 16, height: 9)
        win.minSize = NSSize(width: 240, height: 135)
        win.hasShadow = true
        win.collectionBehavior = [.fullScreenAuxiliary]
        win.isOpaque = false
        win.backgroundColor = .clear
        win.center()
        win.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ a: NSApplication) -> Bool { true }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let d = AppDelegate()
app.delegate = d
app.run()
