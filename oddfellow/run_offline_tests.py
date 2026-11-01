"""Run trusted repository tests without inherited credentials or Python egress.

Usage: python oddfellow/run_offline_tests.py [pytest arguments]
This is an accidental-network-call guard, not a sandbox for untrusted code.
Python children inherit the guard; non-Python programs are not intercepted.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

GUARD = '''
import ipaddress
import sys

def offline_guard(event, args):
    if event not in ("socket.connect", "socket.sendto"):
        return
    address = args[1] if event == "socket.connect" else args[-1]
    if not isinstance(address, tuple):
        return  # Unix sockets are local.
    try:
        allowed = ipaddress.ip_address(address[0]).is_loopback
    except ValueError:
        allowed = False
    if not allowed:
        raise PermissionError("Offline test guard blocked external socket")

sys.addaudithook(offline_guard)
'''

def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="oddfellow-offline-") as directory:
        guard = Path(directory)
        (guard / "sitecustomize.py").write_text(GUARD)
        env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT")
               if key in os.environ}
        env.update(PYTHONPATH=str(guard), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                   PYTHONNOUSERSITE="1")
        # Verify the hook before collecting any test, without transmitting data.
        probe = 'import socket\ntry: socket.socket().connect(("192.0.2.1", 9))\nexcept PermissionError: pass\nelse: raise SystemExit("guard not loaded")'
        subprocess.run([sys.executable, "-c", probe], env=env, check=True)
        args = sys.argv[1:] or ["oddfellow/tests", "oddfellow/connector/tests", "-q"]
        return subprocess.run([sys.executable, "-m", "pytest", *args],
                              cwd=root, env=env).returncode

if __name__ == "__main__":
    raise SystemExit(main())
