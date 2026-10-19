#!/usr/bin/env python3
"""Real Safari Zoom + Accessibility API tree on disposable local Safari window.

No WebDriver, no CSS scaling, no Safari JavaScript. Uses Safari menu commands,
real macOS Accessibility tree, and explicitly restores original domain zoom
and the user's original Safari windows. Only 127.0.0.1 test server.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scripts/qa_native_safari_ax_metrics.swift"
BIN=ROOT/".local_archive/qa_native_safari_ax_metrics"
PORT=19601
ORIGIN=f"http://127.0.0.1:{PORT}"
ROUTES=("/", "/news/", "/guide/museum/", "/search/",
        "/guide/exhibitions-virtual/", "/guide/accessible-museum/")
WIDTHS=(1280,1024,768)
# Six real menu positions: observed 17→20→23→26→28→34 CSS-independent
# Safari AX heading-point heights, from 100% through approximately 200%.
ZOOM_STEPS=tuple(range(6))

def osa(script:str)->str:
    p=subprocess.run(["/usr/bin/osascript","-e",script],
                     text=True,capture_output=True,timeout=7)
    if p.returncode:raise RuntimeError("Safari macOS GUI operation: "+p.stderr[:200])
    return p.stdout.strip()

def key(text:str,cmd=False):
    osa('tell application "System Events" to keystroke '+
        json.dumps(text)+(' using command down' if cmd else ''))

def window_count()->int:
    return int(osa('tell application "System Events" to tell process "Safari" to get count of windows'))

def front()->str:
    return osa('tell application "System Events" to get name of every process whose frontmost is true')

def menu(item:str):
    assert item in ("Zoom In","Zoom Out")
    osa('tell application "System Events" to tell process "Safari" to click menu item '+
        json.dumps(item)+' of menu 1 of menu bar item "View" of menu bar 1')

def read_metrics()->dict:
    output=subprocess.run([str(BIN)],capture_output=True,text=True,timeout=8,check=True).stdout
    if "SAFARI_AX_METRICS" not in output:raise ValueError("No Safari Accessibility tree")
    numeric=("webWidth","webHeight","scrollWidth","scrollHeight","h1Height","navLabelHeight","skipLabelHeight",
             "horizontalScrollbars","inspected")
    result={}
    for keyname in numeric:
        found=re.search(r"\b"+keyname+r"=([0-9.]+)",output)
        if not found:raise ValueError("Missing "+keyname+": "+output)
        result[keyname]=float(found.group(1))
    result["hasHeadings"]="headings=" in output and "Музей" in output
    result["windowTitle"]=output.split("window=",1)[1].split(" webWidth=",1)[0]
    return result

def reset_site_to_baseline():
    # Historical initial real Safari heading height on the original site was
    # exactly 17 px. Zoom is per-origin and persists across temporary windows.
    for _ in range(12):
        m=read_metrics()
        if abs(m["skipLabelHeight"]-15)<1.1:return m
        menu("Zoom Out" if m["skipLabelHeight"]>15 else "Zoom In")
        time.sleep(.3)
    raise RuntimeError("Unable to restore Safari 100% baseline")

def assert_native_safari_measurement(sample:dict,width:int,step:int)->bool:
    baseline=(15,18,20,23,25,30)
    return (abs(sample["skipLabelHeight"]-baseline[step])<2.6 and
       abs(sample["scrollWidth"]-sample["webWidth"])<2 and
       abs(sample["webWidth"]-width)<4 and
       sample["horizontalScrollbars"]==0 and sample["hasHeadings"])

def run():
    if front()!="Safari":raise RuntimeError("Safari is not already foreground; avoiding user interference")
    if not (ROOT/"apps/web/out/index.html").exists():raise FileNotFoundError("Static export not found")
    subprocess.run(["swiftc",str(SOURCE),"-o",str(BIN)],timeout=35,check=True)
    initial_windows=window_count()
    server=subprocess.Popen(["python3","-m","http.server",str(PORT),"--bind","127.0.0.1",
                             "--directory",str(ROOT/"apps/web/out")],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    created=False
    recorded=[]
    errors=[]
    cleanup={"initialWindows":initial_windows,"originalFront":"Safari"}
    try:
        key("n",True)
        time.sleep(.3)
        if window_count()!=initial_windows+1:raise RuntimeError("Did not open exactly one Safari QA window")
        created=True
        for width in WIDTHS:
            osa('tell application "System Events" to tell process "Safari" to set size of window 1 to {'+
                str(width)+',900}')
            time.sleep(.22)
            for route in ROUTES:
                if front()!="Safari":raise RuntimeError("Safari no longer foreground; refusing GUI keys")
                key("l",True)
                key(ORIGIN+route)
                osa('tell application "System Events" to key code 36')
                time.sleep(.44)
                reset_site_to_baseline()
                for step in ZOOM_STEPS:
                    if step:
                        menu("Zoom In")
                        time.sleep(.35)
                    m=read_metrics()
                    ok=assert_native_safari_measurement(m,width,step)
                    row={"width":width,"route":route,"zoomMenuSteps":step,
                         "approxZoomPct":(100,118,135,153,165,200)[step],
                         "pass":ok,**m}
                    recorded.append(row)
                    if not ok:errors.append(row)
                reset_site_to_baseline()
                print("SAFARI_NATIVE_AX",width,route,
                      "PASS" if not any(x["width"]==width and x["route"]==route for x in errors)
                      else "FAIL",flush=True)
    finally:
        try:
            if created:
                try:
                    cleanup["finalSiteZoom"]=reset_site_to_baseline()
                except Exception as error:
                    cleanup["zoomRestoreError"]=str(error)
                finally:
                    key("w",True)
                    time.sleep(.28)
        finally:
            cleanup["finalWindows"]=window_count()
            cleanup["finalFront"]=front()
            server.terminate()
            try:server.wait(timeout=3)
            except subprocess.TimeoutExpired:server.kill()
            report={"kind":"real-Safari-AX-heading-size-and-native-View-menu-zoom",
                    "browserVersion":"27.0.1","count":len(recorded),
                    "expected":len(WIDTHS)*len(ROUTES)*len(ZOOM_STEPS),
                    "failures":len(errors),"windows":cleanup,
                    "measurements":recorded,"failureSamples":errors[:12],
                    "productionMuseumChanged":False}
            (ROOT/".local_archive/tz238-native-safari-ax-zoom-20261019.json").write_text(
                json.dumps(report,ensure_ascii=False,indent=2)+"\n")
            print("SAFARI_AX_ZOOM_RESULT",json.dumps({k:v for k,v in report.items()
                             if k!="measurements"},ensure_ascii=False),flush=True)
    if errors or len(recorded)!=len(WIDTHS)*len(ROUTES)*len(ZOOM_STEPS):
        raise SystemExit("Safari AX native zoom failed measured criteria")

if __name__=="__main__":
    run()
