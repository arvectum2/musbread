#!/usr/bin/env python3
"""QA the complete LOCAL content-to-static-release handoff.

Source MUST be a disposable build of *actual approved CMS export*. This is
deliberately NOT a live transport to a museum server. The second immutable
release differs only by a local staging artifact; it proves version/rollback
mechanics, not that a second CMS editorial decision took place.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import release_site as rel
from verify_static_transfer import make_manifest, verify_manifest
from publication_sla import measure, maximum_hourly_lag, write_private_result


def verify_local_publication_cycle(
    static_output: Path, snapshot: Path, manifest: Path, destination: Path,
    qa_clock_started_at: str | None = None,
) -> dict[str, str]:
    """Fail closed on missing artifacts, corruption or wrong pointer.

    Never mutate the caller's static output or CMS snapshot.
    """
    if destination.exists():
        raise ValueError("Publication QA release directory must be new and disposable")
    if not static_output.is_dir() or not snapshot.is_file() or not manifest.is_file():
        raise ValueError("All inputs must be verified isolated CMS/Next artifacts")

    source_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    expected = raw["files"]["published.json"]
    if expected["sha256"] != source_hash or expected["bytes"] != snapshot.stat().st_size:
        raise ValueError("Source snapshot checksum does not match CMS export manifest")

    # Two physically separate directories stand in for the two isolated
    # machines. Keep the expected checksums out of the transported directory.
    received = destination.parent / (destination.name + "-receiver-staging")
    trusted = destination.parent / (destination.name + "-trusted-inventory.json")
    if received.exists() or trusted.exists():
        raise ValueError("Isolated transfer staging must not preexist")
    make_manifest(static_output, trusted)
    shutil.copytree(static_output, received, symlinks=True)
    sender_inventory = verify_manifest(received, trusted)
    if not sender_inventory["files"].get("snapshot-manifest.json"):
        raise ValueError("CMS checksum manifest missing from transferred output")

    # Detect an attacker changing a static file AFTER the build but BEFORE
    # the atomic public switch. No new release may become active.
    incoming_index = received / "index.html"
    original_index = incoming_index.read_bytes()
    try:
        incoming_index.write_bytes(original_index + b"\n<!-- INJECTED DURING TRANSFER -->\n")
        try:
            verify_manifest(received, trusted)
        except ValueError as e:
            if "checksum mismatch" not in str(e):
                raise
        else:
            raise ValueError("Tampered transfer was accepted")
    finally:
        incoming_index.write_bytes(original_index)
    verify_manifest(received, trusted)
    first = rel.prepare(received, snapshot, manifest, destination)
    state = rel.history(destination)
    if (state["current"] != first or state["verified_release_count"] != 1
            or rel.validate_release((destination / "current").resolve()) != first):
        raise ValueError("Failed initial SHA256-verified release")
    # Synthetic QA clock: do not confuse with the museum's editorial approval.
    # Verify the exact HTML over a real loopback HTTP connection.
    if qa_clock_started_at is not None:
        class LocalStaticHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(destination / "current"), **kwargs)

            def log_message(self, *_args):
                pass

        html = destination / "current/news/qa-browser-news/index.html"
        if not html.is_file():
            raise ValueError("Expected CMS-created news absent from release")
        expected_hash = hashlib.sha256(html.read_bytes()).hexdigest()
        server = ThreadingHTTPServer(("127.0.0.1", 0), LocalStaticHandler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            result = measure(
                approval_id="QA-MOONSHINE-PUBLICATION",
                approved_at=qa_clock_started_at,
                page_url=f"http://127.0.0.1:{server.server_address[1]}/news/qa-browser-news/",
                expected_html_sha256=expected_hash,
            )
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
        if result["status"] != "verified_within_60m":
            raise ValueError("Local HTTP visibility failed: " + result["status"])
        write_private_result(destination.parent / "qa-http-sla-evidence.json", result)
        if maximum_hourly_lag(
            remaining_build_transfer_seconds=result["seconds_since_approval"]
        )["within_60m_guarantee_possible"]:
            raise ValueError("Hourly polling cannot guarantee SLA with positive downstream work")
        print("TZ110_LOCAL_HTTP_SLA_PASS " + json.dumps({
            "status": result["status"],
            "seconds_since_qa_clock": result["seconds_since_approval"],
            "hourly_guarantee": False,
        }, sort_keys=True), flush=True)
    private = destination / "private-snapshots" / (source_hash + ".json")
    if (not private.is_file() or private.read_bytes() != snapshot.read_bytes()
            or private.stat().st_mode & 0o777 != 0o600):
        raise ValueError("Missing private content archive")

    # Idempotence across repeated hourly runs (no new release, no duplicate).
    if rel.prepare(received, snapshot, manifest, destination) != first:
        raise ValueError("Unchanged hourly export unexpectedly created a new release")
    if rel.history(destination)["verified_release_count"] != 1:
        raise ValueError("Idempotent export duplicated release history")

    # Simulate a changed, already-built static artifact using a separate copy.
    # Never edit the source build or invent a second CMS publication.
    second_output = destination.parent / (destination.name + "-updated-artifact")
    if second_output.exists():
        raise ValueError("Updated QA artifact directory must be absent")
    try:
        shutil.copytree(received, second_output, symlinks=True)
        initial = (static_output / "index.html").read_bytes()
        (second_output / "index.html").write_bytes(initial + b"\n<!-- isolated QA release delta -->\n")
        second = rel.prepare(second_output, snapshot, manifest, destination)
        state = rel.history(destination)
        if (first == second or state["current"] != second
                or state["previous"] != first or state["verified_release_count"] != 2):
            raise ValueError("Immutable version history did not record both releases")
        if (destination / "current/index.html").read_bytes() == initial:
            raise ValueError("Updated static artifact not activated")
        if rel.validate_release((destination / "current").resolve()) != second:
            raise ValueError("New release failed independent checksum validation")

        # An invalid export must NEVER replace the verified public pointer.
        # The caller's original CMS snapshot is NEVER modified, not even briefly.
        corrupted_snapshot = destination.parent / (destination.name + "-invalid.json")
        if corrupted_snapshot.exists():
            raise ValueError("Isolated corrupted snapshot must not preexist")
        try:
            corrupted_snapshot.write_bytes(snapshot.read_bytes() + b"corrupted")
            try:
                rel.prepare(second_output, corrupted_snapshot, manifest, destination)
            except ValueError as e:
                if "SHA256" not in str(e):
                    raise
            else:
                raise ValueError("Tampered CMS snapshot accepted by local publisher")
        finally:
            corrupted_snapshot.unlink(missing_ok=True)
        if rel.history(destination)["current"] != second:
            raise ValueError("Publisher switched pointer after failed checksum validation")

        rolled = rel.rollback(destination)
        if (rolled != first or rel.validate_release((destination / "current").resolve()) != first
                or (destination / "current/index.html").read_bytes() != initial):
            raise ValueError("Atomic rollback failed to restore original public HTML")
        record = rel.history(destination)
        assert record["current"] == first and record["previous"] == second
        if rel.prepare(received, snapshot, manifest, destination) != first:
            raise ValueError("Re-deploy after rollback is not deterministic")
        result = {"initial": first, "updated": second, "rolled_back": rolled,
                  "snapshot_sha256": source_hash,
                  "transferred_file_count": str(len(sender_inventory["files"]))}
        print("TZ104_107_ISOLATED_PUBLISH_PASS " + json.dumps(result, sort_keys=True), flush=True)
        return result
    finally:
        shutil.rmtree(second_output, ignore_errors=True)
