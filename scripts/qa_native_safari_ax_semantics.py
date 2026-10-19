#!/usr/bin/env python3
"""Real macOS AX roles/names of Safari museum pages without VoiceOver audio.

Safety: localhost static site, disposable Safari window, user preexisting
Safari windows preserved, must remain mute and VoiceOver OFF throughout.
"""
from __future__ import annotations
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PORT=19622
PAGES={
 "home":("/",("AXHeading","AXLink")),
 "search":("/search/",("AXHeading","AXComboBox")),
 "feedback":("/forms/feedback/",("AXHeading","AXTextField")),
 "excursion":("/forms/excursion/",("AXHeading","AXTextField")),
 "photos":("/guide/exhibitions-virtual/",("AXHeading","AXImage","AXLink")),
 "poster":("/news/museum-news-2025-12-30-grafik-raboty-muzeya/",("AXHeading","AXImage","AXLink")),
}
def osa(script:str)->str:
 p=subprocess.run(["/usr/bin/osascript","-e",script],capture_output=True,text=True,timeout=8)
 if p.returncode:raise RuntimeError(p.stderr[:240])
 return p.stdout.strip()
def key(value:str, command:bool=False):
 osa('tell application "System Events" to keystroke '+json.dumps(value)+(' using command down' if command else ''))
def window_count()->int:
 return int(osa('tell application "System Events" to tell process "Safari" to get count of windows'))
def front()->str:
 return osa('tell application "System Events" to get name of every process whose frontmost is true')
def volume()->str:
 return osa("get volume settings")
def guarded():
 if "output volume:0" not in volume() or "output muted:true" not in volume():
  raise RuntimeError("MUTE NOT ACTIVE, REFUSING VO-RELATED ACCESSIBILITY QA")
 if subprocess.run(["pgrep","-x","VoiceOver"],capture_output=True).returncode==0:
  raise RuntimeError("VoiceOver started unexpectedly; do not interfere")
def ax():
 p=subprocess.run([str(ROOT/".local_archive/qa_native_safari_ax_semantics")],
       capture_output=True,text=True,timeout=16)
 if p.returncode:raise RuntimeError("AX "+p.stderr[:220])
 return json.loads(p.stdout)
def classify(page, data):
 items=data["items"]
 roles=Counter(it["role"] for it in items)
 texts=lambda roles:set(" ".join(str(it.get(k,"")) for k in ("name","value","description","help"))
   for it in items if it["role"] in roles)
 tag=page
 info={"roles":dict(roles),"window":data["windowTitle"],"visited":data["visited"],"checks":{}}
 info["checks"]["headings"]=roles["AXHeading"]>0
 info["checks"]["window_museum"]=("Музей" in data["windowTitle"])
 if tag=="search":
  alltext=" ".join(texts(["AXComboBox","AXTextField","AXSearchField"]))
  info["checks"]["search_field_label"]="Поиск по сайту" in alltext
 if tag in ("feedback","excursion"):
  alltext=" ".join(texts(["AXTextField","AXTextArea","AXComboBox"]))
  info["checks"]["name_labeled"]="Ваше имя" in alltext
  info["checks"]["form_fields_detected"]=roles["AXTextField"]+roles["AXTextArea"]>0
  info["checks"]["submit_labeled"]="Сформировать письмо" in " ".join(texts(["AXButton"]))
  if tag=="feedback":
   info["checks"]["message_labeled"]="Ваш вопрос" in alltext
  else:
   info["checks"]["visitor_count_labeled"]="Количество посетителей" in alltext
   info["checks"]["extra_info_labeled"]="Дополнительная информация" in alltext
   info["checks"]["visible_date_label"]=any(
       "Предпочтительная дата экскурсии" in (it.get("value","") or it.get("name",""))
       for it in items if it["role"]=="AXStaticText")
   info["checks"]["native_date_spinner_fields"]=set(["day","month","year"]).issubset(
       {it.get("name","") for it in items if it["role"]=="AXIncrementor"})
 if tag=="photos":
  alltext=" ".join(texts(["AXLink"]))
  info["checks"]["ceramic_attribution_link"]="Товарищество производства фарфоровых" in alltext
  info["checks"]["photo_alt_exposed"]="супница" in alltext.lower()
 if tag=="poster":
  alltext=" ".join(texts(["AXLink"]))
  info["checks"]["archive_warning"]="Архивное объявление" in alltext
  info["checks"]["dated_announcement"]="1, 2 января" in alltext
 info["pass"]=all(info["checks"].values())
 return info

def run():
 guarded()
 if front()!="Safari":raise RuntimeError("Safari not already foreground")
 before=window_count()
 server=subprocess.Popen(["python3","-m","http.server",str(PORT),"--bind","127.0.0.1",
           "--directory",str(ROOT/"apps/web/out")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 created=False
 samples={}
 try:
  key("n",True)
  time.sleep(.3)
  if window_count()!=before+1:raise RuntimeError("New disposable Safari window not established")
  created=True
  for name,(route,_) in PAGES.items():
   guarded()
   if front()!="Safari":raise RuntimeError("Focus no longer Safari")
   key("l",True)
   key(f"http://127.0.0.1:{PORT}{route}")
   osa('tell application "System Events" to key code 36')
   time.sleep(.60)
   data=ax()
   current=classify(name,data)
   samples[name]={"route":route,"summary":current,"raw":data}
   print("SAFARI_AX_SEMANTICS",name,
       "PASS" if current["pass"] else "PARTIAL",
       json.dumps(current,ensure_ascii=False)[:950],flush=True)
 finally:
  if created:
   key("w",True);time.sleep(.3)
  restore_count=window_count()
  server.terminate()
  try:server.wait(timeout=2)
  except subprocess.TimeoutExpired:server.kill()
  guarded()
  summary={
   "kind":"real-Safari-macOS-AX-semantics-not-VoiceOver-utterances",
   "samples":samples,
   "expected":len(PAGES),
   "pagesMeasured":len(samples),
   "fullyPassed":sum(s["summary"]["pass"] for s in samples.values()),
   "windowsBefore":before,"windowsAfter":restore_count,
   "voiceoverRemainedOff":True,"volumeAfter":volume(),
   "publicMuseumChanged":False,
  }
  (ROOT/".local_archive/tz207-safari-real-accessibility-semantics-20261020.json").write_text(
     json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
  print("SAFARI_AX_SEMANTICS_RESULT",json.dumps({k:v for k,v in summary.items() if k!="samples"},ensure_ascii=False),flush=True)
 if restore_count!=before:raise RuntimeError("Safari windows not restored")
 if len(samples)!=len(PAGES):raise RuntimeError("Not all pages tested")
if __name__=="__main__":run()
