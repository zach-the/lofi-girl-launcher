import Cocoa
let n = 1024
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: n, pixelsHigh: n, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let g = NSGradient(starting: NSColor(srgbRed: 1.0, green: 0.451, blue: 0.2, alpha: 1), ending: NSColor(srgbRed: 0.42, green: 0.243, blue: 0.651, alpha: 1))!
g.draw(in: NSRect(x: 0, y: 0, width: n, height: n), angle: -45)  // orange top-left -> purple bottom-right
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "AppIcon.icon/Assets/bg.png"))
