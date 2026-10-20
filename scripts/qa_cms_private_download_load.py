#!/usr/bin/env python3
"""Bounded, isolated parallel Laravel feature-request load: actual private PDF route.

Each worker boots real Laravel + an in-memory SQLite database, logs in as a
synthetic MoonShine admin, and executes the actual route over the Laravel test
kernel. No network destinations, real files, persistent admin sessions, or
shared production database. This is a PHP-worker memory/capacity test, NOT
an HTTP network / production service throughput benchmark.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import secrets
import statistics
import threading
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CMS = ROOT / "apps" / "cms"
ARCHIVE = ROOT / ".local_archive"
SIZES_MIB = (1, 8, 14)
PARALLEL_WORKERS = (1, 2, 4)
MEMORY_LIMIT = "128M"


def run_worker(size_mib: int) -> dict:
    assert size_mib in SIZES_MIB
    filename = "cms-load-" + secrets.token_hex(12) + ".json"
    observation = ARCHIVE / filename
    env = os.environ.copy()
    env["MUSBREAD_LOAD_DOC_MIB"] = str(size_mib)
    env["MUSBREAD_LOAD_OBSERVATION_PATH"] = str(observation)
    started = time.perf_counter()
    try:
        child = subprocess.run([
            "php", "-d", f"memory_limit={MEMORY_LIMIT}", "artisan", "test",
            "--no-ansi", "--compact", "--filter=MuseumDocumentLoadTest",
        ], cwd=CMS, env=env, capture_output=True, text=True, timeout=55)
        elapsed = (time.perf_counter() - started) * 1000
        if child.returncode != 0 or not observation.is_file():
            raise RuntimeError(
                "Isolated synthetic load worker failure "
                + str(child.returncode) + ": " + (child.stdout + child.stderr)[-900:]
            )
        report = json.loads(observation.read_text(encoding="utf-8"))
        assert report["document_mib"] == size_mib
        assert report["sha256_verified"] is True
        assert report["real_private_route"] is True
        assert report["memory_limit"] == MEMORY_LIMIT
        assert report["status"] == 200
        assert report["peak_php_mib"] < 128
        return {**report, "whole_worker_ms": round(elapsed, 2)}
    finally:
        observation.unlink(missing_ok=True)


def mixed_download_and_queue() -> dict:
    """Compete four synthetic readers and a real background-job feature test.

    The processes run concurrently on the same host. Their SQLite :memory:
    databases are independent, so this is NOT a shared-DB race test.
    """
    barrier = threading.Barrier(5, timeout=12)

    def download() -> dict:
        barrier.wait()
        return run_worker(14)

    def publish() -> dict:
        barrier.wait()
        t0 = time.perf_counter()
        job = subprocess.run([
            "php", "-d", f"memory_limit={MEMORY_LIMIT}", "artisan", "test",
            "--no-ansi", "--compact",
            "--filter=test_job_exports_and_verifies_an_integrity_manifest",
        ], cwd=CMS, capture_output=True, text=True, timeout=45,
           env=os.environ.copy())
        if job.returncode != 0 or "1 passed" not in job.stdout:
            raise RuntimeError("Real Laravel publication worker failed during mixed load: "
                               + (job.stdout + job.stderr)[-800:])
        return {"publication_completed": True,
                "queue_wall_ms": round((time.perf_counter()-t0)*1000, 2)}

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        readers = [pool.submit(download) for _ in range(4)]
        queue = pool.submit(publish)
        results = [x.result() for x in readers]
        publish_result = queue.result()
    assert all(x["status"] == 200 and x["sha256_verified"] for x in results)
    return {
        "parallel_pdf_clients": 4,
        "each_document_mib": 14,
        "actual_php_publication_job_in_parallel": True,
        "independent_sqlite_in_memory_databases": True,
        "all_private_sha256_valid": True,
        "worker_memory_peak_mib": max(x["peak_php_mib"] for x in results),
        "wall_ms": round((time.perf_counter()-start)*1000, 2),
        **publish_result,
    }


def benchmark() -> dict:
    ARCHIVE.mkdir(mode=0o700, exist_ok=True)
    records = []
    for size in SIZES_MIB:
        for parallel in PARALLEL_WORKERS:
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
                futures = [pool.submit(run_worker, size) for _ in range(parallel)]
                collected = [f.result() for f in futures]
            elapsed = (time.perf_counter() - start) * 1000
            records.append({
                "document_mib": size,
                "concurrent_php_workers": parallel,
                "completed": len(collected),
                "errors": 0,
                "batch_wall_ms": round(elapsed, 2),
                "route_latency_ms_max": max(x["elapsed_ms"] for x in collected),
                "route_latency_ms_avg": round(statistics.mean(x["elapsed_ms"] for x in collected), 2),
                "php_peak_mib_max": max(x["peak_php_mib"] for x in collected),
                "sum_of_php_peaks_mib": round(sum(x["peak_php_mib"] for x in collected), 2),
                "worker_95th_percentile_ms": round(sorted(x["whole_worker_ms"] for x in collected)[
                    max(0, (len(collected)*95+99)//100 - 1)], 2),
            })
            print(
                "CMS_LOAD", "MiB", size, "workers", parallel,
                "ok", len(collected), "wall_ms", round(elapsed, 1),
                "peak_worker_mib", records[-1]["php_peak_mib_max"],
                flush=True,
            )
    mixed = mixed_download_and_queue()
    print("CMS_MIXED_QUEUE_PASS", json.dumps(mixed, sort_keys=True), flush=True)
    summary = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "synthetic PHPUnit PHP worker concurrency (NOT HTTP network load)",
        "host": "Mac mini / ArvectumSSD",
        "production_requests": 0,
        "production_db_access": False,
        "max_parallel_php_workers": 4,
        "php_process_limit_mib": 128,
        "test_document_sizes_mib": list(SIZES_MIB),
        "individual_requests": sum(x["completed"] for x in records),
        "all_passed": all(x["errors"] == 0 for x in records),
        "profiles": records,
        "maximum_observed_php_peak_mib": max(x["php_peak_mib_max"] for x in records),
        "mixed_private_download_and_publication": mixed,
    }
    return summary


def main() -> None:
    report = benchmark()
    dest = ARCHIVE / "cms-private-download-load-20261020.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CMS_LOAD_PASS", json.dumps({
        "requests": report["individual_requests"],
        "maximum_observed_php_peak_mib": report["maximum_observed_php_peak_mib"],
        "profiles": len(report["profiles"]),
    }), flush=True)


if __name__ == "__main__":
    main()
