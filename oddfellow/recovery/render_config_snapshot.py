#!/usr/bin/env python3
"""Create and verify offline, non-secret snapshots of two reviewed Oddfellow services.

No Render/GitHub API calls, credentials, scheduled jobs, database reads or deployments.
Untrusted Render metadata is projected through a fail-closed allowlist. Private
fields are neither emitted nor included in error messages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

REPO = "https://github.com/craigbegg005-netizen/chatgpt-github-connection"
SCOPE = "BSI_ODDFELLOW_PRIMARY_ONLY"
SCHEMA_VERSION = 1
# These commands were reviewed against read-only Render metadata on 2026-10-21.
# Any change requires explicit review, not permissive token/string scrubbing.
ALLOWED = {
    "oddfellow-letta-backend-v0206": {
        "type": "web_service",
        "branch": "letta/combined-single-service-v0.20.4",
        "runtime": "python",
        "build_command": "pip install -r oddfellow/requirements.txt",
        "start_command": "cd oddfellow && uvicorn oddfellow_letta_backend:app --host 0.0.0.0 --port $PORT",
        "url": "https://oddfellow-letta-backend-v0206.onrender.com",
    },
    "oddfellow-letta-ui-v020-pwa": {
        "type": "static_site",
        "branch": "letta/frontend-letta-backend",
        "build_command": "rm -rf public && mkdir -p public && cp frontend/index.html frontend/manifest.json frontend/sw.js public/ && cp -R frontend/icons public/icons",
        "publish_path": "public",
        "url": "https://oddfellow-letta-ui-v020-pwa.onrender.com",
    },
}
# Covers the known Render service read shape; environment values are *accepted*
# as input solely so they can be discarded, never copied to output.
SERVICE_KEYS = frozenset({
    "autoDeploy", "autoDeployTrigger", "branch", "createdAt", "dashboardUrl", "id",
    "name", "notifyOnFail", "ownerId", "repo", "rootDir", "serviceDetails",
    "slug", "suspended", "suspenders", "type", "updatedAt", "envVars",
})
DETAIL_KEYS = frozenset({
    "buildPlan", "cache", "env", "envSpecificDetails", "healthCheckPath",
    "ipAllowList", "maintenanceMode", "numInstances", "openPorts", "plan",
    "previews", "pullRequestPreviewsEnabled", "region", "renderSubdomainPolicy",
    "runtime", "sshAddress", "url", "publishPath", "buildCommand", "envVars",
})
ENV_DETAIL_KEYS = frozenset({"buildCommand", "startCommand", "envVars"})
UTC_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class Rejected(ValueError):
    """Safe exception with fixed messages; no untrusted values included."""


def _object(value: Any) -> dict:
    if type(value) is not dict:
        raise Rejected("metadata must be a JSON object")
    return value


def _only_keys(value: dict, allowed: frozenset[str]) -> None:
    if set(value) - allowed:
        raise Rejected("unexpected metadata fields; manual review required")


def _matches(actual: Any, expected: Any) -> None:
    if type(actual) is not type(expected) or actual != expected:
        raise Rejected("configuration differs from the reviewed baseline")


def _nonempty_utc_stamp(s: str) -> str:
    import datetime
    if not isinstance(s, str) or not UTC_STAMP.fullmatch(s):
        raise Rejected("capture time must be RFC3339 UTC seconds")
    try:
        datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise Rejected("invalid capture time") from None
    return s


def normalize(raw: Any, captured_at: str) -> dict:
    """Project native Render service metadata into a deliberately narrow safe form.

    Other services—including public-service projects—are not permitted. This is
    NOT a general-purpose backup exporter, and it never reproduces env values.
    """
    captured_at = _nonempty_utc_stamp(captured_at)
    if type(raw) is dict:
        _only_keys(raw, frozenset({"services"}))
        raw = raw["services"]
    if not isinstance(raw, list) or not raw or len(raw) > len(ALLOWED):
        raise Rejected("expected one or two scoped Render services")
    output = []
    seen = set()
    for item in raw:
        service = _object(item)
        _only_keys(service, SERVICE_KEYS)
        name = service.get("name")
        if not isinstance(name, str) or name not in ALLOWED or name in seen:
            raise Rejected("unknown or duplicate service; manual review required")
        seen.add(name)
        allowed = ALLOWED[name]
        _matches(service.get("type"), allowed["type"])
        _matches(service.get("repo"), REPO)
        _matches(service.get("branch"), allowed["branch"])
        _matches(service.get("rootDir"), "")
        _matches(service.get("autoDeploy"), "no")
        if "autoDeployTrigger" in service:
            _matches(service["autoDeployTrigger"], "off")
        details = _object(service.get("serviceDetails"))
        _only_keys(details, DETAIL_KEYS)
        _matches(details.get("url"), allowed["url"])
        if "runtime" in allowed:
            _matches(details.get("env"), allowed["runtime"])
            if "runtime" in details:
                _matches(details["runtime"], allowed["runtime"])
            commands = _object(details.get("envSpecificDetails"))
            _only_keys(commands, ENV_DETAIL_KEYS)
            _matches(commands.get("buildCommand"), allowed["build_command"])
            _matches(commands.get("startCommand"), allowed["start_command"])
        else:
            _matches(details.get("buildCommand"), allowed["build_command"])
            _matches(details.get("publishPath"), allowed["publish_path"])
            if "envSpecificDetails" in details:
                raise Rejected("unexpected static-site command fields")
        # No dictionary merge. Only explicitly reviewed literal fields survive.
        safe = {
            "name": name,
            "type": allowed["type"],
            "repository": REPO,
            "branch": allowed["branch"],
            "root_directory": "",
            "auto_deploy": "off",
            "build_command": allowed["build_command"],
            "url": allowed["url"],
        }
        for key in ("runtime", "start_command", "publish_path"):
            if key in allowed:
                safe[key] = allowed[key]
        output.append(safe)
    output.sort(key=lambda item: item["name"])
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "captured_at_utc": captured_at,
        "source": "render_service_metadata_read_only",
        "not_a_data_backup": True,
        "services": output,
    }


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       separators=(",", ": ")) + "\n").encode("utf-8")


def package(raw: Any, captured_at: str, snapshot_file: str) -> tuple[bytes, bytes]:
    safe = normalize(raw, captured_at)
    data = canonical_bytes(safe)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "captured_at_utc": safe["captured_at_utc"],
        "snapshot_file": snapshot_file,
        "sha256": hashlib.sha256(data).hexdigest(),
        "service_count": len(safe["services"]),
        "purpose": "nonsecret_configuration_only",
        "not_a_data_backup": True,
    }
    return data, canonical_bytes(manifest)


def verify(snapshot_data: bytes, manifest_data: bytes, snapshot_file: str) -> bool:
    try:
        obj = _object(json.loads(snapshot_data))
        m = _object(json.loads(manifest_data))
        _only_keys(obj, frozenset({
            "schema_version", "scope", "captured_at_utc", "source",
            "not_a_data_backup", "services",
        }))
        _only_keys(m, frozenset({
            "schema_version", "scope", "captured_at_utc", "snapshot_file",
            "sha256", "service_count", "purpose", "not_a_data_backup",
        }))
        if canonical_bytes(obj) != snapshot_data:
            raise Rejected("noncanonical snapshot encoding")
        if canonical_bytes(m) != manifest_data:
            raise Rejected("noncanonical manifest encoding")
        for key, expected in {
            "schema_version": SCHEMA_VERSION, "scope": SCOPE,
            "snapshot_file": snapshot_file, "purpose": "nonsecret_configuration_only",
            "not_a_data_backup": True,
        }.items():
            _matches(m.get(key), expected)
        _matches(obj.get("schema_version"), SCHEMA_VERSION)
        _matches(obj.get("scope"), SCOPE)
        _matches(obj.get("not_a_data_backup"), True)
        _matches(obj.get("source"), "render_service_metadata_read_only")
        _matches(m.get("captured_at_utc"), obj.get("captured_at_utc"))
        _nonempty_utc_stamp(obj.get("captured_at_utc"))
        _matches(m.get("service_count"), len(obj.get("services", [])))
        _matches(m.get("sha256"), hashlib.sha256(snapshot_data).hexdigest())
        # Independently compare to the same safe-literal shape, not the manifest alone.
        safe_services = obj.get("services")
        if not isinstance(safe_services, list) or not safe_services:
            raise Rejected("missing normalized services")
        for service in safe_services:
            name = _object(service).get("name")
            if name not in ALLOWED:
                raise Rejected("unexpected service")
            expected = ALLOWED[name]
            known = {
                "name": name, "type": expected["type"], "repository": REPO,
                "branch": expected["branch"], "root_directory": "",
                "auto_deploy": "off", "build_command": expected["build_command"],
                "url": expected["url"],
            }
            for key in ("runtime", "start_command", "publish_path"):
                if key in expected:
                    known[key] = expected[key]
            if service != known:
                raise Rejected("snapshot service does not match reviewed policy")
        if len({s["name"] for s in safe_services}) != len(safe_services):
            raise Rejected("duplicate snapshot services")
        if safe_services != sorted(safe_services, key=lambda x: x["name"]):
            raise Rejected("noncanonical service ordering")
    except (ValueError, TypeError, KeyError, AttributeError):
        return False
    return True


def _write_new(path: Path, data: bytes) -> None:
    """Refuse to overwrite files and create mode-600 data using atomic rename."""
    if path.exists() or path.is_symlink():
        raise Rejected("output already exists; no overwrite permitted")
    if not path.parent.is_dir():
        raise Rejected("output directory does not exist")
    fd, tmp = tempfile.mkstemp(prefix=".snapshot-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        # link() is an atomic no-clobber creation; os.replace() could overwrite
        # a competing writer after the existence check.
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise Rejected("output path changed during write") from None
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Offline non-secret Oddfellow Render config snapshot")
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="normalize reviewed native metadata; no network")
    create.add_argument("--input", type=Path, required=True, help="local service JSON; never commit raw input")
    create.add_argument("--snapshot", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--captured-at", required=True, help="UTC e.g. 2026-10-21T16:00:00Z")
    chk = sub.add_parser("verify", help="offline checksum and safety-policy verification")
    chk.add_argument("--snapshot", type=Path, required=True)
    chk.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.snapshot == args.manifest:
            raise Rejected("snapshot and manifest must be different files")
        if args.command == "create":
            # Sensitive raw metadata remains local. Never output or log source values.
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            payload, manifest = package(raw, args.captured_at, args.snapshot.name)
            if not verify(payload, manifest, args.snapshot.name):
                raise Rejected("generated package failed independent verification")
            _write_new(args.snapshot, payload)
            try:
                _write_new(args.manifest, manifest)
            except Exception:
                args.snapshot.unlink(missing_ok=True)
                raise
            print("PASS: sanitized configuration and checksum manifest created (not a data backup)")
        else:
            if not verify(args.snapshot.read_bytes(), args.manifest.read_bytes(), args.snapshot.name):
                raise Rejected("verification failed")
            print("PASS: snapshot matches the manifest and reviewed non-secret service policy")
        return 0
    except (Rejected, ValueError, OSError, TypeError):
        # Never relay the exception text: it could carry untrusted sensitive data.
        print("FAIL: rejected or unverifiable configuration; inspect locally", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
