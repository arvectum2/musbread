import AppKit
import ApplicationServices
import Foundation

func attr(_ e: AXUIElement, _ key:String)->AnyObject? {
  var value:CFTypeRef?
  if AXUIElementCopyAttributeValue(e,key as CFString,&value) != .success {return nil}
  return value
}
func string(_ e: AXUIElement, _ key:String)->String {
  (attr(e,key) as? String) ?? ""
}
func size(_ e: AXUIElement)->CGSize {
  guard let raw=attr(e,kAXSizeAttribute as String),
        CFGetTypeID(raw)==AXValueGetTypeID() else {return .zero}
  var s=CGSize.zero
  if AXValueGetValue((raw as! AXValue),.cgSize,&s) {return s}
  return .zero
}
guard let process=NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.Safari").first else {print("ERR no safari");exit(2)}
let root=AXUIElementCreateApplication(process.processIdentifier)
guard let wins=attr(root,kAXWindowsAttribute as String) as? [AXUIElement], !wins.isEmpty else {print("ERR no windows");exit(3)}
var queue:[(AXUIElement,Int)]=[(wins[0],0)]
var webArea:AXUIElement?
var scrollArea:AXUIElement?
var headings:[String]=[]
var navLabelSize:CGFloat = 0
var skipLabelSize:CGFloat = 0
var headingSizes:[CGFloat]=[]
var horizontalScrollBars=0
var skipped=0
while !queue.isEmpty && skipped<850 {
  let (node,depth)=queue.removeFirst()
  skipped+=1
  let role=string(node,kAXRoleAttribute as String)
  if role=="AXWebArea" && webArea == nil {webArea=node}
  if role=="AXScrollArea" && scrollArea == nil {scrollArea=node}
  if role=="AXStaticText" {
    let txt=string(node,kAXValueAttribute as String)
    if txt=="Санкт-Петербургский музей Хлеба" {navLabelSize=size(node).height}
    if txt=="Перейти к содержимому" {skipLabelSize=size(node).height}
  }
  if role=="AXHeading" {
    let title=string(node,kAXTitleAttribute as String)
    let val=string(node,kAXValueAttribute as String)
    let t=title.isEmpty ? val:title
    headings.append(String(t.prefix(55)))
    headingSizes.append(size(node).height)
  }
  if role=="AXScrollBar" && size(node).width>size(node).height {horizontalScrollBars+=1}
  if depth<14, let children=attr(node,kAXChildrenAttribute as String) as? [AXUIElement] {
    for child in children.prefix(110) {queue.append((child,depth+1))}
  }
}
let title=string(wins[0],kAXTitleAttribute as String)
let ws=webArea.map(size) ?? .zero
let ss=scrollArea.map(size) ?? .zero
let hs=headingSizes.first ?? 0
print("SAFARI_AX_METRICS", "window="+title,
      "webWidth="+String(format:"%.2f",ws.width),
      "webHeight="+String(format:"%.2f",ws.height),
      "scrollWidth="+String(format:"%.2f",ss.width),
      "scrollHeight="+String(format:"%.2f",ss.height),
      "h1Height="+String(format:"%.2f",hs),
      "navLabelHeight="+String(format:"%.2f",navLabelSize),
      "skipLabelHeight="+String(format:"%.2f",skipLabelSize),
      "headings="+headings.prefix(6).joined(separator:"/"),
      "horizontalScrollbars="+String(horizontalScrollBars),
      "inspected="+String(skipped))
