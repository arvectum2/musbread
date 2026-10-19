#!/usr/bin/env python3
"""TZ-317: bounded mixed-content HTTP load against an isolated local Nginx only.

No external destinations, no anonymous public site load, no large PDF downloads.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
import json
import math
import pathlib
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

def percentile(values: list[float], rank: float) -> float:
    if not values:
        raise ValueError("Empty measurement series")
    return round(sorted(values)[max(0, math.ceil(len(values) * rank) - 1)], 2)

def check_local_url(base: str) -> str:
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or not parsed.port or parsed.netloc != "127.0.0.1:" + str(parsed.port)):
        raise ValueError("Only http://127.0.0.1:<port> is allowed; never test museum production")
    return "http://127.0.0.1:" + str(parsed.port)

def routes_from_export(root: pathlib.Path) -> list[tuple[str, bool]]:
    required = ["", "news/", "events/", "guide/museum/", "search/", "novosty/"]
    found: list[tuple[str, bool]] = []
    for name in required:
        path = root / name / "index.html"
        if not path.is_file():
            raise FileNotFoundError("Missing required release HTML " + str(path))
        found.append(("/" + name, False))
    photos = sorted((root / "sites").rglob("*.webp")) if (root / "sites").exists() else []
    if not photos:
        photos = sorted(root.rglob("*.webp"))
    docs = sorted(root.rglob("*.pdf"))
    if not photos or not docs:
        raise FileNotFoundError("Mixed load requires real museum WebP and original PDF")
    found.append(("/" + photos[0].relative_to(root).as_posix(), False))
    found.append(("/" + docs[0].relative_to(root).as_posix(), True))
    return found

class RejectRedirect(urllib.request.HTTPRedirectHandler):
    """An unexpected 301/302 is a failed sample, NEVER follow a new origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Load test does not follow redirects", headers, fp)

NO_REDIRECTS = urllib.request.build_opener(RejectRedirect)

def fetch_one(args: tuple[str, bool]) -> dict:
    url, is_doc = args
    headers = {"Accept-Encoding": "gzip", "User-Agent": "MusbreadLocalQA/1.0"}
    if is_doc:
        headers["Range"] = "bytes=0-65535"
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers=headers)
        with NO_REDIRECTS.open(req, timeout=12) as response:
            # Hard cap: never download more than 2MB, especially for PDFs.
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise ValueError("Unexpectedly large response body")
            return {"ms": round((time.perf_counter()-start)*1000, 3), "status": response.status,
                    "bytes": len(body), "encoding": response.headers.get("Content-Encoding", ""),
                    "type": response.headers.get("Content-Type", "")}
    except (OSError, ValueError, urllib.error.URLError) as err:
        return {"ms": round((time.perf_counter()-start)*1000, 3), "status": 0, "bytes": 0,
                "error": type(err).__name__}

def run_test(base: str, root: pathlib.Path, workers: int, cycles: int) -> dict:
    base = check_local_url(base)
    if not (1 <= workers <= 24 and 1 <= cycles <= 40):
        raise ValueError("Bounded concurrency: 1..24 clients and 1..40 cycles")
    routes = routes_from_export(root)
    test_cases = [(base+path, is_doc) for _ in range(cycles) for path, is_doc in routes]
    # Never follow redirects from the local server, including to an external host.
    for path, is_doc in routes:
        req = urllib.request.Request(base+path, headers={"Range": "bytes=0-1023"} if is_doc else {})
        with NO_REDIRECTS.open(req, timeout=5) as response:
            if response.status not in (200, 206):
                raise ValueError("Warm-up HTTP failure: "+str(path))
            if is_doc and response.status != 206:
                raise ValueError("Original PDF range support missing: "+str(path))
            response.read(1025 if is_doc else 2_000_000)
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(fetch_one, test_cases))
    elapsed = time.perf_counter()-start
    ok = []
    fails = []
    by_route = {}
    for (url, is_doc), result in zip(test_cases, results):
        expected = 206 if is_doc else 200
        path = urllib.parse.urlsplit(url).path
        if result["status"] != expected:
            fails.append({"route": path, **result})
        else:
            ok.append(result)
        by_route.setdefault(path, []).append(result)
    stats = {}
    for path, items in by_route.items():
        vals = [s["ms"] for s in items if s["status"] in (200, 206)]
        stats[path] = {"requests": len(items), "success": len(vals),
                       "p50_ms": percentile(vals, .5) if vals else None,
                       "p95_ms": percentile(vals, .95) if vals else None,
                       "p99_ms": percentile(vals, .99) if vals else None,
                       "bytes_received": sum(s["bytes"] for s in items)}
    return {"date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scope": "isolated local Nginx: not production load test",
            "bind_host": "127.0.0.1", "concurrent_clients": workers, "cycles": cycles,
            "requests": len(results), "success": len(ok), "errors": len(fails),
            "http_statuses": dict(Counter(str(s["status"]) for s in results)),
            "p50_ms": percentile([s["ms"] for s in ok], .50),
            "p95_ms": percentile([s["ms"] for s in ok], .95),
            "p99_ms": percentile([s["ms"] for s in ok], .99),
            "throughput_rps": round(len(results)/elapsed, 2),
            "transfer_mb": round(sum(s["bytes"] for s in ok)/1_000_000, 3),
            "tested_paths": stats, "failures": fails[:10]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--root", type=pathlib.Path, default=pathlib.Path("apps/web/out"))
    p.add_argument("--workers", type=int, default=12)
    p.add_argument("--cycles", type=int, default=25)
    p.add_argument("--output", type=pathlib.Path, default=pathlib.Path(".local_archive/tz317-nginx-mixed-load.json"))
    args = p.parse_args()
    report = run_test(args.base, args.root.resolve(strict=True), args.workers, args.cycles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("requests", "success", "errors", "http_statuses", "p95_ms", "p99_ms", "throughput_rps", "transfer_mb")}, ensure_ascii=False))
    for path, item in report["tested_paths"].items():
        print("ROUTE", path, "HTTP", item["success"], "/", item["requests"], "p95", item["p95_ms"])
    if report["errors"]:
        raise SystemExit("FAIL: unexpected HTTP error(s)")
if __name__ == "__main__":
    main()
