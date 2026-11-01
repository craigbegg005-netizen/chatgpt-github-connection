"""Recovery and failure controls for private SQLite snapshots; no network needed."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from connector import Job, Risk, Status, Store, TaskKind, new_job_id
from connector.snapshot import main, snapshot


def test_queue_progress_and_pause_survive_snapshot(tmp_path):
    source, target = tmp_path / "queue.db", tmp_path / "saved.sqlite"
    with Store(source) as store:
        payload = {"spec": "private research"}
        job, _ = store.create_job(Job(
            job_id=new_job_id(TaskKind.CODE, "resume", payload),
            kind=TaskKind.CODE, title="resume", payload=payload, risk=Risk.LOW), actor="owner")
        store.record_checkpoint(job.job_id, "analysis saved", actor="owner")
        approval = store.request_approval(job.job_id, actor="owner")
        store.set_paused(True, actor="owner", reason="preservation drill")
        before = source.read_bytes()
        report = snapshot(source, target)
        assert source.read_bytes() == before
    with Store(target) as restored:
        recovered = restored.get_job(job.job_id)
        assert recovered.checkpoints[0]["step"] == "analysis saved"
        assert recovered.status == Status.READY and not recovered.verified
        assert restored.is_paused()
        assert restored.pause_reason() == "preservation drill"
        assert restored.get_approval(approval["approval_id"])["state"] == "WAITING_AUTHORIZATION"
        assert restored.audit_trail()
    assert report["status"] == "snapshot_verified"
    assert "private research" not in json.dumps(report)


def test_wal_commits_are_included(tmp_path):
    source, target = tmp_path / "wal.db", tmp_path / "backup.sqlite"
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE evidence (value TEXT)")
        db.execute("INSERT INTO evidence VALUES ('committed WAL')")
        db.commit()
        assert Path(str(source) + "-wal").exists()
        report = snapshot(source, target)
    assert report["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    with sqlite3.connect(target) as saved:
        assert saved.execute("SELECT value FROM evidence").fetchone()[0] == "committed WAL"


def test_missing_source_is_not_created(tmp_path):
    source, target = tmp_path / "missing.db", tmp_path / "backup.sqlite"
    with pytest.raises(FileNotFoundError):
        snapshot(source, target)
    assert not source.exists() and not target.exists()


def test_existing_files_and_symlinks_are_never_replaced(tmp_path):
    source = tmp_path / "source.db"
    with Store(source):
        pass
    target = tmp_path / "existing"
    target.write_bytes(b"keep")
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "missing")
    for path in (source, target, link):
        with pytest.raises(FileExistsError):
            snapshot(source, path)
    assert target.read_bytes() == b"keep" and link.is_symlink()


def test_corrupt_source_leaves_no_output(tmp_path):
    source = tmp_path / "bad.db"
    source.write_bytes(b"not a SQLite database")
    with pytest.raises(sqlite3.DatabaseError):
        snapshot(source, tmp_path / "backup.sqlite")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.db"]


def test_publish_failure_preserves_existing_destination(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "backup.sqlite"
    with Store(source):
        pass
    real_link = os.link
    def race(src, dst):
        target.write_bytes(b"other writer")
        real_link(src, dst)
    with patch("connector.snapshot.os.link", side_effect=race):
        with pytest.raises(FileExistsError):
            snapshot(source, target)
    assert target.read_bytes() == b"other writer"
    assert not list(tmp_path.glob(".oddfellow-snapshot-*"))


def test_snapshot_is_private_under_permissive_umask(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "backup.sqlite"
    with Store(source):
        pass
    previous = os.umask(0)
    try:
        snapshot(source, target)
    finally:
        os.umask(previous)
    assert target.stat().st_mode & 0o777 == 0o600


def test_timeout_and_cli_failure_are_safe(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "backup.sqlite"
    with Store(source):
        pass
    for timeout in (0, -1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            snapshot(source, target, timeout=timeout)
    with patch("connector.snapshot.time.monotonic", side_effect=[0, 100]):
        with pytest.raises(TimeoutError):
            snapshot(source, target, timeout=1)
    assert not target.exists() and not list(tmp_path.glob(".oddfellow-snapshot-*"))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main(["--source", str(tmp_path / "private-missing"),
                     "--destination", str(target)]) == 2
    assert "private-missing" not in output.getvalue()
