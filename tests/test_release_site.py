import hashlib
import os
import signal
import subprocess
import sys
import textwrap
import time
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("release_site", Path(__file__).resolve().parents[1] / "scripts/release_site.py")
assert spec and spec.loader
rel = module_from_spec(spec)
spec.loader.exec_module(rel)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.site, self.dest = root / "site", root / "deploy"
        self.snapshot, self.manifest = root / "content.json", root / "manifest.json"
        self.site.mkdir()
        (self.site / "index.html").write_text("version one")
        self.snapshot.write_bytes(b'{"events":[]}\n')
        self.manifest.write_text(json.dumps({"files": {"published.json": {
            "sha256": hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
            "bytes": self.snapshot.stat().st_size,
        }}}))

    def test_release_and_rollback(self):
        a = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version one")
        self.assertEqual(rel.prepare(self.site, self.snapshot, self.manifest, self.dest), a)
        (self.site / "index.html").write_text("version two")
        b = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertNotEqual(a, b)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version two")
        self.assertEqual(rel.rollback(self.dest), a)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version one")

    def test_history_reports_only_validated_local_releases_and_roles(self):
        first = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        second = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        state = rel.history(self.dest)
        self.assertEqual(state["scope"], "LOCAL_PREAWARD_NOT_MUSEUM_PRODUCTION")
        self.assertEqual(state["current"], second)
        self.assertEqual(state["previous"], first)
        self.assertEqual(state["verified_release_count"], 2)
        self.assertEqual({r["role"] for r in state["releases"]}, {"current", "previous"})
        self.assertEqual(sum(r["file_count"] for r in state["releases"]), 2)
        self.assertTrue(all(r["total_bytes"] > 0 for r in state["releases"]))
        self.assertNotIn("private-snapshots", json.dumps(state))

    def test_history_rejects_corrupt_archived_version_and_invalid_pointer(self):
        first = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version three")
        latest = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        before = (self.dest / "current").readlink()
        # Release one is archived (not current/previous) and still validated.
        (self.dest / "releases" / first / "index.html").write_text("modified")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.history(self.dest)
        self.assertEqual((self.dest / "current").readlink(), before)
        (self.dest / "releases" / first / "index.html").write_text("version one")
        self.assertEqual(rel.history(self.dest)["current"], latest)
        (self.dest / "previous").unlink()
        (self.dest / "previous").symlink_to(Path("releases") / ("f"*16))
        with self.assertRaisesRegex(ValueError, "Invalid or unverified release pointer"):
            rel.history(self.dest)

    def test_history_fails_closed_on_unexpected_symlink_in_release_inventory(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.dest / "releases" / ("e"*16)).symlink_to(self.site, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unexpected entry"):
            rel.history(self.dest)

    def test_private_archive_matches_release_and_never_enters_public_output(self):
        (self.site / "snapshot-manifest.json").write_bytes(self.manifest.read_bytes())
        version = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        archived = self.dest / "private-snapshots" / (sha + ".json")
        self.assertEqual(archived.read_bytes(), self.snapshot.read_bytes())
        self.assertEqual(archived.stat().st_mode & 0o777, 0o600)
        self.assertEqual(rel.archive_current(self.dest, self.snapshot), sha)
        self.assertFalse((self.dest / "current/private-snapshots").exists())
        self.assertNotIn("private-snapshots", rel.files_with_hashes(self.dest / "current"))
        self.assertEqual(rel.validate_release((self.dest / "current").resolve()), version)
        self.snapshot.write_text('tampered')
        with self.assertRaisesRegex(ValueError, "differs from release snapshot manifest"):
            rel.archive_current(self.dest, self.snapshot)

    def test_private_archive_cannot_be_silently_overwritten(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        private = self.dest / "private-snapshots" / (sha + ".json")
        private.write_bytes(b"MALICIOUS")
        with self.assertRaisesRegex(ValueError, "Private snapshot archive checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_existing_release_manifest_corruption_prevents_redeployment(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        active = (self.dest / "current").resolve()
        manifest = active / "release-manifest.json"
        doc = json.loads(manifest.read_text())
        doc["release"] = "evil-mismatched-id"
        manifest.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_corrupted_previous_release_cannot_be_rolled_back(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        before = (self.dest / "current").readlink()
        previous = (self.dest / "previous").resolve()
        (previous / "index.html").write_text("TAMPERED")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.rollback(self.dest)
        self.assertEqual((self.dest / "current").readlink(), before)

    def test_current_release_verification_rejects_tampering(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        active = (self.dest / "current").resolve()
        self.assertTrue(rel.validate_release(active))
        (active / "index.html").write_text("altered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.validate_release(active)

    def test_corrupt_snapshot_rejected(self):
        self.snapshot.write_text("tampered")
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_tampered_media_asset_rejected_before_release_switch(self):
        media = self.site / "media"
        media.mkdir()
        item = media / ("a" * 64 + ".webp")
        item.write_bytes(b"safe-public-webp-test")
        meta = json.loads(self.manifest.read_text())
        meta["files"]["media/" + item.name] = {
            "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
            "bytes": item.stat().st_size,
        }
        self.manifest.write_text(json.dumps(meta))
        release_id = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertEqual((self.dest / "current/media" / item.name).read_bytes(), item.read_bytes())
        self.assertTrue(release_id)
        item.write_bytes(b"altered-after-export")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_missing_media_asset_rejected(self):
        meta = json.loads(self.manifest.read_text())
        meta["files"]["media/" + "b" * 64 + ".webp"] = {"sha256": "b" * 64, "bytes": 8}
        self.manifest.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_document_export_is_verified_and_tamper_blocks_release(self):
        directory = self.site / "documents"
        directory.mkdir()
        name = hashlib.sha256(b"office-fixture").hexdigest() + ".docx"
        document = directory / name
        document.write_bytes(b"office-fixture")
        meta = json.loads(self.manifest.read_text())
        meta["files"]["documents/" + name] = {
            "sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
            "bytes": document.stat().st_size,
        }
        self.manifest.write_text(json.dumps(meta))
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        document.write_bytes(b"MODIFIED")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_unexpected_document_filename_is_rejected(self):
        meta = json.loads(self.manifest.read_text())
        meta["files"]["documents/../../bad.pdf"] = {"sha256": "b" * 64, "bytes": 10}
        self.manifest.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "Unexpected asset path"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_export_symlink_rejected(self):
        (self.site / "unsafe").symlink_to(self.snapshot)
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)


class InterruptedReleaseTests(unittest.TestCase):
    """SIGKILL affects a disposable child only, never the user's Mac mini."""

    setUp = ReleaseTests.setUp

    def _two_releases(self):
        a = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        b = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertNotEqual(a, b)
        self.assertEqual(rel.history(self.dest)["previous"], a)
        return a, b

    def _crash_after_pointer_change(self, action: str, kill_at: int):
        script = textwrap.dedent("""
            import os, signal, sys
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            import release_site as rel

            original_swap = rel._swap_link
            original_write = rel._write_transition
            def journal_then_crash(*args, **kwargs):
                original_write(*args, **kwargs)
                if int(sys.argv[3]) == 0:
                    os.kill(os.getpid(), signal.SIGKILL)
            rel._write_transition = journal_then_crash
            swaps = 0
            def kill_after_swap(pointer, target):
                global swaps
                original_swap(pointer, target)
                swaps += 1
                if swaps == int(sys.argv[3]):
                    os.kill(os.getpid(), signal.SIGKILL)
            rel._swap_link = kill_after_swap
            dest = Path(sys.argv[4])
            if sys.argv[2] == "deploy":
                rel.prepare(Path(sys.argv[5]), Path(sys.argv[6]), Path(sys.argv[7]), dest)
            else:
                rel.rollback(dest)
        """)
        child = subprocess.run(
            [sys.executable, "-c", script, str(Path(rel.__file__).parent),
             action, str(kill_at), str(self.dest),
             str(self.site), str(self.snapshot), str(self.manifest)],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr)
        self.assertTrue((self.dest / rel.TRANSITION_FILE).is_file())
        with self.assertRaisesRegex(ValueError, "Unrecovered release transition"):
            rel.history(self.dest)

    def test_sigkill_during_deploy_before_or_after_current_pointer_switch(self):
        for kill_after in (1, 2):
            with self.subTest(after_swap=kill_after):
                # Separate fixtures for each hard-crash test.
                with tempfile.TemporaryDirectory() as folder:
                    old_site, old_dest, old_snapshot, old_manifest = (
                        self.site, self.dest, self.snapshot, self.manifest)
                    try:
                        self.site, self.dest = Path(folder)/"site", Path(folder)/"dest"
                        self.snapshot, self.manifest = Path(folder)/"snapshot.json", Path(folder)/"manifest.json"
                        self.site.mkdir()
                        (self.site/"index.html").write_text("version one")
                        self.snapshot.write_bytes(b'{"events":[]}\n')
                        self.manifest.write_text(json.dumps({"files":{"published.json":{
                            "sha256":hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                            "bytes":self.snapshot.stat().st_size}}}))
                        first, second = self._two_releases()
                        (self.site/"index.html").write_text("version three")
                        self._crash_after_pointer_change("deploy", kill_after)
                        self.assertTrue(rel.recover(self.dest))
                        self.assertFalse(rel.recover(self.dest))
                        state = rel.history(self.dest)
                        self.assertEqual((state["current"], state["previous"]), (second, first))
                        self.assertEqual((self.dest/"current/index.html").read_text(), "version two")
                        third = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
                        self.assertNotIn(third, (first, second))
                        self.assertEqual(rel.history(self.dest)["current"], third)
                        self.assertEqual(rel.history(self.dest)["previous"], second)
                    finally:
                        self.site, self.dest, self.snapshot, self.manifest = (
                            old_site, old_dest, old_snapshot, old_manifest)

    def test_sigkill_during_rollback_restores_complete_prior_pointers(self):
        for kill_after in (1, 2):
            with self.subTest(after_swap=kill_after):
                with tempfile.TemporaryDirectory() as folder:
                    original = self.site, self.dest, self.snapshot, self.manifest
                    try:
                        self.site, self.dest = Path(folder)/"site", Path(folder)/"dest"
                        self.snapshot, self.manifest = Path(folder)/"snapshot.json", Path(folder)/"manifest.json"
                        self.site.mkdir()
                        (self.site/"index.html").write_text("version one")
                        self.snapshot.write_bytes(b'{"events":[]}\n')
                        self.manifest.write_text(json.dumps({"files":{"published.json":{
                            "sha256":hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                            "bytes":self.snapshot.stat().st_size}}}))
                        first, second = self._two_releases()
                        self._crash_after_pointer_change("rollback", kill_after)
                        self.assertTrue(rel.recover(self.dest))
                        state = rel.history(self.dest)
                        self.assertEqual((state["current"], state["previous"]), (second, first))
                        self.assertEqual(rel.rollback(self.dest), first)
                        self.assertEqual(rel.history(self.dest)["current"], first)
                    finally:
                        self.site, self.dest, self.snapshot, self.manifest = original

    def test_untrusted_or_corrupted_recovery_journal_refuses_pointer_mutation(self):
        first, second = self._two_releases()
        current = (self.dest/"current").readlink()
        previous = (self.dest/"previous").readlink()
        journal = self.dest/rel.TRANSITION_FILE
        for invalid in (
            b'{"action":"deploy","version":1,"before":{"current":"../../private"}}',
            b'{"action":"rollback","version":2,"before":{},"after":{}}',
            b'not-json',
        ):
            journal.write_bytes(invalid)
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                rel.recover(self.dest)
            self.assertEqual((self.dest/"current").readlink(), current)
            self.assertEqual((self.dest/"previous").readlink(), previous)
        journal.unlink()
        journal.symlink_to(self.snapshot)
        with self.assertRaisesRegex(ValueError, "symlink"):
            rel.recover(self.dest)
        self.assertEqual(rel.validate_release((self.dest/"current").resolve()), second)
        self.assertEqual(rel.validate_release((self.dest/"previous").resolve()), first)

    def test_deploy_automatically_recovers_interrupted_previous_attempt(self):
        first, second = self._two_releases()
        (self.site/"index.html").write_text("version three")
        self._crash_after_pointer_change("deploy", 1)
        third = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertEqual(rel.history(self.dest)["current"], third)
        self.assertEqual(rel.history(self.dest)["previous"], second)
        self.assertFalse((self.dest/rel.TRANSITION_FILE).exists())
        self.assertNotEqual(third, first)

    def test_sigkill_immediately_after_durable_journal_and_before_any_swap(self):
        a, b = self._two_releases()
        (self.site/"index.html").write_text("version three")
        self._crash_after_pointer_change("deploy", 0)
        self.assertEqual((self.dest/"current/index.html").read_text(), "version two")
        self.assertTrue(rel.recover(self.dest))
        self.assertEqual((rel.history(self.dest)["current"],
                          rel.history(self.dest)["previous"]), (b, a))

    def test_operator_read_and_private_archive_refuse_unrecovered_transition(self):
        self._two_releases()
        (self.site/"index.html").write_text("version three")
        self._crash_after_pointer_change("deploy", 1)
        with self.assertRaisesRegex(ValueError, "Unrecovered release transition"):
            rel.archive_current(self.dest, self.snapshot)
        action = subprocess.run(
            [sys.executable, str(Path(rel.__file__)), "verify", "--dest", str(self.dest)],
            capture_output=True, text=True, timeout=12,
        )
        self.assertNotEqual(action.returncode, 0)
        self.assertIn("Unrecovered release transition", action.stderr)
        cmd = subprocess.run(
            [sys.executable, str(Path(rel.__file__)), "recover", "--dest", str(self.dest)],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(cmd.returncode, 0, cmd.stderr)
        self.assertIn("RECOVERED interrupted transition", cmd.stdout)
        self.assertFalse((self.dest / rel.TRANSITION_FILE).exists())

    def test_sigkill_during_release_copy_recovers_abandoned_staging_without_losing_current(self):
        old = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site/"index.html").write_text("version two")
        script = textwrap.dedent("""
            import os, signal, sys
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            import release_site as rel
            saved = rel.shutil.copytree
            def copy_then_die(*args, **kwargs):
                saved(*args, **kwargs)
                os.kill(os.getpid(), signal.SIGKILL)
            rel.shutil.copytree = copy_then_die
            rel.prepare(*(Path(x) for x in sys.argv[2:]))
        """)
        child = subprocess.run(
            [sys.executable, "-c", script, str(Path(rel.__file__).parent),
             str(self.site), str(self.snapshot), str(self.manifest), str(self.dest)],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr)
        self.assertEqual((self.dest/"current/index.html").read_text(), "version one")
        orphaned = list((self.dest/"releases").glob(".release-*"))
        self.assertEqual(len(orphaned), 1, [p.name for p in orphaned])
        with self.assertRaisesRegex(ValueError, "Unexpected release ID"):
            rel.history(self.dest)
        self.assertTrue(rel.recover(self.dest))
        self.assertEqual(list((self.dest/"releases").glob(".release-*")), [])
        self.assertEqual(rel.history(self.dest)["current"], old)
        changed = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertNotEqual(changed, old)
        self.assertEqual(rel.history(self.dest)["previous"], old)

    def test_crash_before_journal_rename_discards_incomplete_private_file(self):
        original = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site/"index.html").write_text("version two")
        script = textwrap.dedent("""
            import os, signal, sys
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            import release_site as rel
            original_replace = rel.os.replace
            def die_before_journal_swap(source, destination):
                if str(destination).endswith(rel.TRANSITION_FILE):
                    os.kill(os.getpid(), signal.SIGKILL)
                return original_replace(source, destination)
            rel.os.replace = die_before_journal_swap
            rel.prepare(*(Path(x) for x in sys.argv[2:]))
        """)
        child = subprocess.run(
            [sys.executable, "-c", script, str(Path(rel.__file__).parent),
             str(self.site), str(self.snapshot), str(self.manifest), str(self.dest)],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr)
        remnants = list(self.dest.glob(".release-transition-*.tmp"))
        self.assertEqual(len(remnants), 1)
        self.assertFalse((self.dest/rel.TRANSITION_FILE).exists())
        self.assertEqual((self.dest/"current/index.html").read_text(), "version one")
        self.assertTrue(rel.recover(self.dest))
        self.assertEqual(list(self.dest.glob(".release-transition-*.tmp")), [])
        self.assertEqual(rel.history(self.dest)["current"], original)

    def test_recovery_rejects_unrelated_or_unsafe_lookalike_staging(self):
        original = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        foreign = self.dest/"releases"/".release-not-an-eight-char-name"
        foreign.mkdir()
        (foreign/"user.txt").write_text("PRESERVE")
        with self.assertRaisesRegex(ValueError, "Unrecognized interrupted"):
            rel.recover(self.dest)
        self.assertEqual((foreign/"user.txt").read_text(), "PRESERVE")
        self.assertEqual((self.dest/"current/index.html").read_text(), "version one")
        (foreign/"user.txt").unlink()
        foreign.rmdir()
        unsafe = self.dest/"releases"/(".release-"+"x"*8)
        unsafe.symlink_to(self.site, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsafe interrupted"):
            rel.recover(self.dest)
        self.assertEqual(rel.validate_release((self.dest/"current").resolve()), original)
        self.assertTrue(unsafe.is_symlink())

    def test_concurrent_process_deploys_keep_verified_pointers_and_full_history(self):
        initial = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        script = textwrap.dedent("""
            import sys
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            import release_site as rel
            rel.prepare(*(Path(x) for x in sys.argv[2:]))
        """)
        children = []
        try:
            # Hold flock in this process while BOTH other publishers start:
            # neither process may pass the release switch until the lock exits.
            with rel.release_lock(self.dest):
                for number in (2, 3):
                    folder = Path(self.dir.name) / f"candidate_{number}"
                    folder.mkdir()
                    (folder/"index.html").write_text(f"version {number}")
                    child = subprocess.Popen([
                        sys.executable, "-c", script, str(Path(rel.__file__).parent),
                        str(folder), str(self.snapshot), str(self.manifest), str(self.dest),
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    children.append(child)
                time.sleep(0.25)
                self.assertTrue(all(child.poll() is None for child in children))
                self.assertEqual((self.dest/"current/index.html").read_text(), "version one")
            for child in children:
                out, err = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, err)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.communicate()
        state = rel.history(self.dest)
        self.assertEqual(state["verified_release_count"], 3)
        self.assertNotEqual(state["current"], state["previous"])
        self.assertNotIn(initial, (state["current"], state["previous"]))
        self.assertIn((self.dest/"current/index.html").read_text(), ("version 2", "version 3"))
        self.assertIn((self.dest/"previous/index.html").read_text(), ("version 2", "version 3"))
        self.assertFalse((self.dest / rel.TRANSITION_FILE).exists())




if __name__ == "__main__":
    unittest.main()
