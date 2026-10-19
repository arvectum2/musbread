import AppKit
import ApplicationServices
import Foundation
func get(_ e:AXUIElement,_ key:String)->AnyObject? {
 var value:CFTypeRef?
 return AXUIElementCopyAttributeValue(e,key as CFString,&value) == .success ? value : nil
}
func str(_ e:AXUIElement,_ key:String)->String {(get(e,key) as? String) ?? ""}
func chars(_ s:String,_ n:Int=360)->String {String(s.prefix(n))}
guard let safari=NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.Safari").first else {print("ERROR_NO_SAFARI");exit(2)}
let app=AXUIElementCreateApplication(safari.processIdentifier)
guard let wins=get(app,kAXWindowsAttribute as String) as? [AXUIElement],!wins.isEmpty else {print("ERROR_NO_WINDOWS");exit(3)}
let title=str(wins[0],kAXTitleAttribute as String)
if title.isEmpty {print("ERROR_MISSING_TITLE");exit(4)}
var items:[[String:String]]=[]
var visited=0
var todo:[(AXUIElement,Int)]=[(wins[0],0)]
let watched:Set<String>=["AXLink","AXImage","AXTextField","AXTextArea","AXButton","AXHeading","AXCheckBox","AXPopUpButton","AXComboBox","AXRadioButton","AXSearchField","AXStaticText","AXDateField","AXDateTimeField","AXDatePicker","AXTimeField","AXIncrementor","AXGroup"]
while !todo.isEmpty && visited<3500 {
 let (node,depth)=todo.removeFirst()
 visited+=1
 let role=str(node,kAXRoleAttribute as String)
 if watched.contains(role) {
  let name=str(node,kAXTitleAttribute as String)
  let value=str(node,kAXValueAttribute as String)
  let desc=str(node,kAXDescriptionAttribute as String)
  let help=str(node,kAXHelpAttribute as String)
  var fields=["role":role,"name":chars(name),"value":chars(value),"description":chars(desc),"help":chars(help)]
  if role=="AXHeading" {fields["level"]=str(node,"AXHeadingLevel")}
  if role=="AXLink" {
   fields["url"]=chars(str(node,kAXURLAttribute as String))
  }
  if name != "" || value != "" || desc != "" || role != "AXStaticText" {items.append(fields)}
 }
 if depth<19, let children=get(node,kAXChildrenAttribute as String) as? [AXUIElement] {
  for c in children.prefix(155){todo.append((c,depth+1))}
 }
}
let data:[String:Any]=["windowTitle":title,"visited":visited,"items":items,"roles":Dictionary(grouping:items,by:{$0["role"] ?? ""}).mapValues{$0.count}]
let bytes=try JSONSerialization.data(withJSONObject:data,options:[.prettyPrinted,.sortedKeys])
print(String(data:bytes,encoding:.utf8) ?? "{}")
