"""Offline tests. No secrets, network, Render endpoints, or database calls."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "render_config_snapshot.py"
spec = importlib.util.spec_from_file_location("render_config_snapshot", MODULE_PATH)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
STAMP = "2026-10-21T16:00:00Z"
FAKE_SECRET = "SECRET_PASSWORD_DO_NOT_OUTPUT_309483"


def raw_sample():
    return [
        {
            "name": "oddfellow-letta-backend-v0206",
            "type": "web_service", "repo": r.REPO,
            "branch": r.ALLOWED["oddfellow-letta-backend-v0206"]["branch"],
            "rootDir": "", "autoDeploy": "no", "autoDeployTrigger": "off",
            "envVars": [{"key": "LETTA_API_KEY", "value": FAKE_SECRET}],
            "serviceDetails": {
                "env": "python", "url": r.ALLOWED["oddfellow-letta-backend-v0206"]["url"],
                "envSpecificDetails": {
                    "buildCommand": r.ALLOWED["oddfellow-letta-backend-v0206"]["build_command"],
                    "startCommand": r.ALLOWED["oddfellow-letta-backend-v0206"]["start_command"],
                    "envVars": [{"key": "TOKEN", "value": FAKE_SECRET}],
                },
            },
        },
        {
            "name": "oddfellow-letta-ui-v020-pwa",
            "type": "static_site", "repo": r.REPO,
            "branch": r.ALLOWED["oddfellow-letta-ui-v020-pwa"]["branch"],
            "rootDir": "", "autoDeploy": "no", "autoDeployTrigger": "off",
            "serviceDetails": {
                "url": r.ALLOWED["oddfellow-letta-ui-v020-pwa"]["url"],
                "buildCommand": r.ALLOWED["oddfellow-letta-ui-v020-pwa"]["build_command"],
                "publishPath": "public", "envVars": {"SECRET": FAKE_SECRET},
            },
        },
    ]


class SnapshotTests(unittest.TestCase):
    def test_creates_verified_sanitized_snapshot(self):
        s, m = r.package(raw_sample(), STAMP, "safe.json")
        self.assertTrue(r.verify(s, m, "safe.json"))
        self.assertNotIn(FAKE_SECRET, s.decode())
        self.assertNotIn("LETTA_API_KEY", s.decode())
        self.assertNotIn("envVars", s.decode())
        self.assertNotIn(FAKE_SECRET, m.decode())
        self.assertEqual(len(json.loads(s)["services"]), 2)

    def test_deterministic_repeat(self):
        self.assertEqual(r.package(raw_sample(), STAMP, "x.json"),
                         r.package(raw_sample(), STAMP, "x.json"))
        backward = raw_sample()[::-1]
        self.assertEqual(r.package(backward, STAMP, "x.json"),
                         r.package(raw_sample(), STAMP, "x.json"))

    def test_rejects_unknown_service(self):
        sample = raw_sample()
        sample[0]["name"] = "global-peace-human-security-full-rc1"
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_unknown_top_level_field(self):
        sample = raw_sample()
        sample[0]["credentialDump"] = FAKE_SECRET
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_unknown_nested_field(self):
        sample = raw_sample()
        sample[1]["serviceDetails"]["sourceCode"] = FAKE_SECRET
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_source_payload_in_build_command(self):
        sample = raw_sample()
        sample[0]["serviceDetails"]["envSpecificDetails"]["buildCommand"] += " && echo " + FAKE_SECRET
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_changed_branch_or_deploy_mode(self):
        sample = raw_sample()
        sample[1]["branch"] = "main"
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)
        sample = raw_sample()
        sample[0]["autoDeploy"] = "yes"
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_duplicate_or_empty(self):
        with self.assertRaises(r.Rejected):
            r.normalize([], STAMP)
        sample = raw_sample()
        sample[1] = copy.deepcopy(sample[0])
        with self.assertRaises(r.Rejected):
            r.normalize(sample, STAMP)

    def test_rejects_invalid_time(self):
        for stamp in ("2026-10-21", "2026-02-30T16:00:00Z", "2026-10-21T16:00:00+00:00"):
            with self.subTest(stamp=stamp):
                with self.assertRaises(r.Rejected):
                    r.normalize(raw_sample(), stamp)

    def test_detects_tampering_and_truncation(self):
        s, m = r.package(raw_sample(), STAMP, "safe.json")
        self.assertFalse(r.verify(s[:-1], m, "safe.json"))
        self.assertFalse(r.verify(s.replace(b'"off"', b'"yes"'), m, "safe.json"))
        self.assertFalse(r.verify(s, m[:-1], "safe.json"))
        self.assertFalse(r.verify(s, m, "other.json"))

    def test_rejects_new_fields_even_with_recomputed_hash(self):
        import hashlib
        s, m = r.package(raw_sample(), STAMP, "safe.json")
        altered = json.loads(s)
        altered["envVars"] = {"TOKEN": FAKE_SECRET}
        s2 = r.canonical_bytes(altered)
        m2 = json.loads(m)
        m2["sha256"] = hashlib.sha256(s2).hexdigest()
        self.assertFalse(r.verify(s2, r.canonical_bytes(m2), "safe.json"))

    def test_rejects_recomputed_digest_with_unsafe_configuration(self):
        import hashlib
        s, m = r.package(raw_sample(), STAMP, "safe.json")
        altered = json.loads(s)
        altered["services"][0]["build_command"] = "echo " + FAKE_SECRET
        s2 = r.canonical_bytes(altered)
        m2 = json.loads(m)
        m2["sha256"] = hashlib.sha256(s2).hexdigest()
        self.assertFalse(r.verify(s2, r.canonical_bytes(m2), "safe.json"))

    def test_cli_dry_run_create_verify_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            path = d / "raw.json"
            path.write_text(json.dumps({"services": raw_sample()}), encoding="utf-8")
            args = [sys.executable, str(MODULE_PATH), "create", "--input", str(path),
                    "--snapshot", str(d / "safe.json"), "--manifest", str(d / "manifest.json"),
                    "--captured-at", STAMP]
            created = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(subprocess.run([sys.executable, str(MODULE_PATH), "verify",
                "--snapshot", str(d / "safe.json"), "--manifest", str(d / "manifest.json")],
                capture_output=True).returncode, 0)
            repeat = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 1)
            self.assertNotIn(FAKE_SECRET, created.stdout + created.stderr + repeat.stdout + repeat.stderr)

    def test_cli_rejects_truncated_input_without_leaking(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            (d / "raw.json").write_text('{"services":[{"key":"' + FAKE_SECRET)
            cmd = [sys.executable, str(MODULE_PATH), "create", "--input", str(d / "raw.json"),
                   "--snapshot", str(d / "safe.json"), "--manifest", str(d / "manifest.json"),
                   "--captured-at", STAMP]
            x = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(x.returncode, 1)
            self.assertNotIn(FAKE_SECRET, x.stdout + x.stderr)
            self.assertFalse((d / "safe.json").exists())


if __name__ == "__main__":
    unittest.main()
