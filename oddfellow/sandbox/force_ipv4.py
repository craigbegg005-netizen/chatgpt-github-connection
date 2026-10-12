"""Remove AF_INET6 from name resolution in this sandbox.

Why this exists
---------------
This sandbox has no IPv6 connectivity (`ip -6 addr` shows zero addresses), but
`trycloudflare.com` publishes an AAAA record first and the default resolver
ordering (RFC 3484) prefers IPv6. Tools therefore attempt the IPv6 address, fail
with `Errno 97 Address family not supported by protocol`, and -- for Python's
`urllib` -- do *not* fall back to the A record.

Ordering the resolver in `/etc/gai.conf` is not enough. It orders, it does not
*prevent*: the IPv6 attempt is still made and can still raise. The tell that
ordering alone is insufficient is that the failing gate *moves* -- one run fails
the token check, the next fails `/livez`, both with the same transport error. A
failure that relocates rather than disappears is probabilistic, and a
probabilistic fix is not a fix.

The deterministic fix is to never make the attempt, by removing AF_INET6 from
`getaddrinfo` entirely.

This file is the single source of truth. `sandbox_ipv4_fix.sh` copies it into
whatever site-packages the running interpreter and the rehearsal venv use. It is
not duplicated by hand into those directories, because two copies of a rule
drift -- that is the mechanism of divergence, not a coincidence (see the ninth
false control in lessons-archive-2.md).

Loading
-------
A venv `sitecustomize.py` is *shadowed* by the system one
(`/usr/lib/python3.11/sitecustomize.py`, Ubuntu's apport hook), so it never
loads. A `.pth` file in site-packages is processed regardless, which is why the
companion `zz_force_ipv4.pth` contains `import force_ipv4`.

This module is sandbox infrastructure, not product code. It is not imported by
the Oddfellow backend and does not change its behaviour beyond resolution.
"""

import socket

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Resolve, then keep only AF_INET results.

    Deliberately does NOT fall back to the IPv6 list when no A record is
    present. The first version of this fix did (`return v4 or res`), which
    silently reintroduced the very attempt the patch exists to prevent and
    swapped a clear error for an opaque one. If there is no IPv4 answer, raise
    `gaierror` -- the caller (the acceptance harness, or `rehearsal.sh`) already
    polls for the propagation window, so failing fast here is correct.
    """
    results = _original_getaddrinfo(host, port, socket.AF_UNSPEC, type, proto, flags)
    v4 = [r for r in results if r[0] == socket.AF_INET]
    if v4:
        return v4
    raise socket.gaierror(
        socket.EAI_NONAME,
        "no IPv4 address for %r (force_ipv4: AF_INET6 removed)" % (host,),
    )


socket.getaddrinfo = _ipv4_only_getaddrinfo
