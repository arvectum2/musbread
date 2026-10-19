#!/usr/bin/env python3
"""Real macOS Firefox browser Page Zoom via GUI Cmd+= / Cmd+0, NOT CSS simulation.

Safety: only a disposable geckodriver profile and 127.0.0.1 static server,
restore the original foreground app, never change Firefox's real user profile.
"""
from __future__ import annotations
import json, os, subprocess, time, urllib.error, urllib.request
from contextlib import suppress
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DRIVER_PORT=19593
STATIC_PORT=19594
STATIC="http://127.0.0.1:"+str(STATIC_PORT)
BROWSER="/Volumes/ArvectumSSD/arvectum/.tooling/browser-apps/Firefox.app/Contents/MacOS/firefox"
ROUTES=("/", "/news/", "/guide/museum/", "/search/",
        "/guide/exhibitions-virtual/", "/guide/accessible-museum/")
PHYSICAL_WIDTHS=(1280,1024,768)
LEVELS=((100,0),(120,2),(150,2),(170,1),(200,1))

def osa(script, timeout=6):
    p=subprocess.run(["/usr/bin/osascript","-e",script],text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("System Events: "+p.stderr[:250])
    return p.stdout.strip()
def front():
    return osa('tell application "System Events" to get name of every process whose frontmost is true')
def command(key, count=1):
    inner="repeat "+str(count)+" times\nkeystroke "+json.dumps(key)+" using command down\nend repeat"
    osa('tell application "System Events"\n'+inner+'\nend tell')
def wd(method,path,payload=None):
    url="http://127.0.0.1:"+str(DRIVER_PORT)+path
    request=urllib.request.Request(url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type":"application/json"},method=method)
    with urllib.request.urlopen(request,timeout=18) as resp:
        result=json.load(resp)["value"]
        if isinstance(result,dict) and "error" in result:
            raise RuntimeError(result)
        return result
def verify_real_native_zoom(sample: dict, route: str, percent: int) -> tuple[bool,bool]:
    """Return (actual browser zoom verified, horizontal overflow).

    CSS style.zoom does NOT satisfy the browser Zoom requirement.
    """
    expected=percent/100
    correct=(sample["url"]==route and sample["h1"]
             and abs(sample["ratio"]-expected)<.055
             and sample["scriptZoom"]=="")
    overflow=sample["scrollWidth"]>sample["cssWidth"]+1
    return correct,overflow

def verify_local_export():
    for name in ("index.html","news/index.html","guide/museum/index.html","search/index.html"):
        if not (ROOT/"apps/web/out"/name).is_file():
            raise FileNotFoundError(name)

def run():
    verify_local_export()
    initial=front()
    # Avoid focus changes when another user is active in a third-party app.
    if initial not in ("Finder","Safari"):
        raise RuntimeError("Foreground is "+initial+"; GUI QA deferred to avoid interrupting user")
    if not Path(BROWSER).is_file():
        raise FileNotFoundError(BROWSER)
    rlog=ROOT/".local_archive/tz238-native-firefox-driver.log"
    web=subprocess.Popen(["python3","-m","http.server",str(STATIC_PORT),"--bind","127.0.0.1",
                         "--directory",str(ROOT/"apps/web/out")],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    gecko=subprocess.Popen(["geckodriver","--host","127.0.0.1","--port",str(DRIVER_PORT),"--log","error"],
                           stdout=rlog.open("w"),stderr=subprocess.STDOUT)
    sid=None
    rows=[]
    errors=[]
    version=None
    try:
        for _ in range(35):
            try:
                wd("GET","/status")
                break
            except (OSError,urllib.error.URLError):
                time.sleep(.12)
        caps={"capabilities":{"alwaysMatch":{"browserName":"firefox",
              "moz:firefoxOptions":{"binary":BROWSER,"args":["--no-remote"]}}}}
        resp=wd("POST","/session",caps)
        sid=resp["sessionId"]
        version=resp["capabilities"]["browserVersion"]
        path="/session/"+sid
        js={"script":'''return {url:location.pathname,h1:!!document.querySelector("h1"),
                    cssWidth:document.documentElement.clientWidth,
                    scrollWidth:document.documentElement.scrollWidth,
                    ratio:devicePixelRatio,scriptZoom:document.body.style.zoom,
                    windowWidth:outerWidth};''',"args":[]}
        for width in PHYSICAL_WIDTHS:
            wd("POST",path+"/window/rect",{"width":width,"height":900})
            for route in ROUTES:
                wd("POST",path+"/url",{"url":STATIC+route})
                if front().lower()!="firefox":
                    raise RuntimeError("Firefox lost foreground; stopping system keystrokes")
                command("0")
                time.sleep(.25)
                for zoom, _ in LEVELS:
                    target=zoom/100
                    measurement=None
                    # Native Cmd+= is asynchronously handled by Firefox UI.
                    # Observe ACTUAL devicePixelRatio after each single
                    # keystroke, never assume the event already took effect.
                    for attempt in range(12):
                        measurement=wd("POST",path+"/execute/sync",js)
                        actual=measurement["ratio"]
                        if abs(actual-target)<.055:
                            break
                        if actual<target-.055:
                            command("=")
                        else:
                            command("-")
                        time.sleep(.35)
                    actual=measurement["ratio"]
                    correct,overflow=verify_real_native_zoom(measurement,route,zoom)
                    row={"route":route,"physical_width":width,"browser_zoom_pct":zoom,
                         **measurement,"real_native_zoom_verified":correct,"overflow":overflow}
                    rows.append(row)
                    if not correct or overflow:
                        errors.append(row)
                command("0")
                time.sleep(.3)
                print("FIREFOX_NATIVE_ZOOM",width,route,"5 levels",
                      "OK" if not any(x["route"]==route and x["physical_width"]==width for x in errors) else "FAIL",
                      flush=True)
    finally:
        if sid:
            with suppress(Exception):wd("DELETE","/session/"+sid)
        gecko.terminate();web.terminate()
        with suppress(Exception):gecko.wait(timeout=3)
        with suppress(Exception):web.wait(timeout=3)
        if initial in ("Finder","Safari") and front()!=initial:
            osa('tell application "'+initial+'" to activate')
        after=front()
        report={"kind":"native-macOS-firefox-GUI-CmdPlus-zoom-not-CSS",
                "browser_version":version,"initial_foreground":initial,"restored_foreground":after,
                "expected_cases":len(PHYSICAL_WIDTHS)*len(ROUTES)*len(LEVELS),
                "checked":len(rows),"failures":len(errors),
                "zoom_levels":[x for x,_ in LEVELS],"physical_widths":PHYSICAL_WIDTHS,
                "results":rows,"failure_samples":errors[:12],
                "museum_production_changed":False}
        dest=ROOT/".local_archive/tz238-native-firefox-zoom-20261019.json"
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print("FIREFOX_NATIVE_ZOOM_RESULT",
              json.dumps({k:v for k,v in report.items() if k!="results"},ensure_ascii=False))
    if errors or len(rows)!=len(PHYSICAL_WIDTHS)*len(ROUTES)*len(LEVELS):
        raise SystemExit("Native Firefox Zoom failed measured criteria")

if __name__=="__main__":
    run()
