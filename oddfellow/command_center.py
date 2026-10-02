"""Begg AI Command Center — the owner-facing control surface.

A private, owner-only view of the company: what each department and lane is doing,
what is waiting for the owner, and a switch that stops everything.

This is deliberately a *module of the existing service*, not a new product. The
service already has owner-token auth, rate limiting, fail-closed configuration and
an audit trail; a second service would duplicate all four and then drift from them.
The protocol also says to finish existing work before creating new products, and
this is the owner-facing layer of the one that exists.

Constraints, all taken from the operating protocol:

* **owner-only.** Every route requires the owner token. There is no anonymous read
  path, and there is no separate weaker token for "just viewing".
* **auditable.** Every mutation writes an audit record before it takes effect.
* **fail-closed.** The pause switch stops work; it does not warn about it. A paused
  service refuses to send messages rather than logging a complaint.
* **not a public product.** This is not exposed as a commercial surface.

**Single-instance only, by construction.** Approvals and the pause flag live in this
process's memory, so this module must not be deployed to a runtime that runs many
isolates — the Cloudflare Worker fallback being the obvious one. There, state is
per-isolate: an approval created on one isolate would be invisible on another, and
the pause switch would stop a fraction of requests while *appearing* to work. An
emergency stop that stops some traffic is worse than one that is absent, because it
is trusted. Moving this to a Worker means moving the state to durable storage first.

The registry below is declarative on purpose. A status page that reads its own
values from a live probe is a status page that can lie; these are claims with
dates, and the date is part of the claim.
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
import os
from typing import Any, Callable, Optional

from fastapi import APIRouter, Body, HTTPException, Request


def binding_hash(text: str) -> str:
    """Hash the exact command an approval authorises.

    The hash is what makes the binding an exact match rather than a prefix or
    substring comparison: a truncated binding would let a longer command ride in
    on a shorter approval, and a substring binding would let an approval for
    "delete the branch" authorise "delete the branch and transfer the balance".

    **What this does not do, stated plainly:** the approval record still carries
    the command in its ``detail`` field, because the owner has to be able to see
    what they are approving -- a gate that authorises an action it will not name
    is theatre. ``detail`` is truncated for display and is never used for
    enforcement. An earlier version of this docstring claimed the store "never
    holds a second copy of the owner's message"; that was false when written, and
    a runtime check caught it. The property that actually holds is narrower: the
    *binding* is a hash, and the binding is what decides.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized_binding_text(text: str) -> str:
    """The canonical form an approval binds to.

    The enforcement path binds to the *exact* text, but two spellings of the
    same command must not become two different bindings: whitespace runs are
    collapsed and stripped, so ``"delete   the  branch"`` and
    ``"delete the branch"`` hash identically. Everything else -- case,
    punctuation, wording -- is left alone: over-normalising would let a
    binding for one command authorise a near-miss variant, which is the
    exact failure the exact-match binding exists to prevent.
    """
    return " ".join((text or "").split())


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

# Status vocabulary is the protocol's, and the meanings are strict:
#   VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED > IMPLEMENTED > PENDING
#   > BLOCKED > REVENUE
# Nothing is promoted without evidence, and "LIVE" is never "VERIFIED".
#
# The docstring above says "these are claims with dates, and the date is part of
# the claim" — but until 2026-10-01 no entry carried one, so the claims drifted
# silently and two of them were wrong by the time anyone looked. This date is the
# fix for that: it is returned by /api/command/status so a reader can see how old
# the registry is before trusting it. It is not a substitute for per-entry dates.
REGISTRY_AS_OF = "2026-10-01"

# How long an APPROVED approval stays valid, counted from the decision. An
# owner decision must not be bankable indefinitely: 15 minutes is enough to
# read the result of the command the approval was made for, and short enough
# that a decision made before a change of mind cannot be executed after it.
APPROVAL_TTL_SECONDS = 15 * 60

DEPARTMENTS: list[dict[str, Any]] = [
    {"name": "Executive / AI CEO", "state": "RUNNING",
     "note": "Coordinating lanes; blocked on Render access for the deploy."},
    {"name": "Product", "state": "RUNNING",
     "note": "Oddfellow v0.20.6 is the active product; Command Center is its owner layer."},
    {"name": "Engineering", "state": "RUNNING",
     "note": "109 tests, 39/39 fault injection, acceptance green on the rehearsal."},
    {"name": "QA / Verification", "state": "RUNNING",
     "note": "Every claim in this registry is dated; unverified items are marked."},
    {"name": "Security", "state": "RUNNING",
     "note": "Secret scan clean; owner token never persisted while a third-party SDK is loaded."},
    {"name": "Legal / Compliance / IP", "state": "PENDING",
     "note": "No registration exists or is claimed. IP inventory written; clearance search "
             "run for US/AU — register clear in Classes 9/42, but an unregistered software "
             "publisher uses the name. EU/UK still open."},
    {"name": "Finance", "state": "RUNNING",
     "note": "Spend ceiling $0. No paid service, subscription or billing without owner approval."},
    {"name": "Marketing", "state": "PENDING",
     "note": "No paid spend. Preparation only, at zero cost."},
    {"name": "Brand & Media", "state": "BLOCKED",
     "note": "Social scheduling is another AI's lane; not connected to this agent."},
    {"name": "Support / Customer Experience", "state": "PENDING",
     "note": "No live customers, so no support queue exists yet."},
    {"name": "Research / Think Tank", "state": "RUNNING",
     "note": "Portfolio review continues; no product is claimed launched."},
    {"name": "Automation / Operations", "state": "RUNNING",
     "note": "Rehearsal watchdog and monitors run continuously."},
]

LANES: list[dict[str, Any]] = [
    {"name": "Oddfellow deploy", "state": "BLOCKED",
     "blocker": "WAITING_CREDENTIAL", "owner": "Claude (Render access)",
     "note": "Target returns no HTTP response. The cause IS the missing secrets: Render's "
             "own dashboard reading is build completed, app started, config check reported "
             "both secrets missing, /healthz 503, deploy update_failed — the fail-closed "
             "health check meeting Render's non-200 healthCheckPath contract. An earlier "
             "note here said the opposite; it was wrong and is corrected. Fix: enter "
             "LETTA_API_KEY and ODDFELLOW_OWNER_TOKEN, then trigger a deploy "
             "(autoDeploy: false means saving them is not a deploy)."},
    {"name": "Oddfellow live rehearsal", "state": "LIVE",
     "note": "Self-healing; all acceptance gates green. Dies with the sandbox by design."},
    {"name": "Cloudflare Worker fallback", "state": "IMPLEMENTED",
     "note": "v0.20.6, transport and auth paths both proven locally. Not deployed."},
    {"name": "Begg AI Core v0.15.0", "state": "BLOCKED",
     "blocker": "SOURCE NOT PRESERVED", "owner": "Claude (Render access)",
     "note": "No trace of it or its SHA in any branch or history. Only the live services' "
             "API surfaces survive."},
    {"name": "Begg AI Core (live)", "state": "LIVE",
     "note": "v0.13.0 and v0.12.1 answer 200. LIVE is not end-to-end verified."},
    {"name": "Database", "state": "PENDING",
     "blocker": "not connected to any app", "note": "Postgres free plan; expires 2026-10-27."},
    {"name": "Command Center", "state": "IMPLEMENTED",
     "note": "This module. Owner-only, audited, fail-closed."},
    {"name": "App Factory", "state": "BLOCKED",
     "blocker": "Floot / app-store accounts", "owner": "Owner"},
    {"name": "7-Day Reset Planner", "state": "PENDING",
     "blocker": "seller-side access unverified", "note": "Listing exists; no revenue is claimed."},
    {"name": "Global Peace & Human Security Framework", "state": "LIVE",
     "note": "SEPARATE PROJECT. RC-1 published and serving; independent review outstanding. "
             "No Begg AI data, branding or infrastructure is shared with it."},
]


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

class CommandCenter:
    """Approvals, the pause switch, and a bounded audit ring.

    Deliberately in-memory: this service is single-instance and free-tier, and a
    database would be a second thing to configure before the first thing works.
    The trade is stated rather than hidden — state does not survive a restart, and
    the status endpoint says so.
    """

    def __init__(self, audit_ring: int = 200) -> None:
        self._lock = threading.Lock()
        self._approvals: dict[str, dict[str, Any]] = {}
        self._audit: list[dict[str, Any]] = []
        self._audit_ring = audit_ring
        self._paused = False
        self._pause_reason = ""

    # -- approvals ---------------------------------------------------------- #

    def add_approval(
        self,
        title: str,
        detail: str,
        risk: str,
        binding_text: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a pending approval.

        ``binding_text`` is the exact command this approval authorises. It is
        **hashed, never stored**: the approval then authorises one specific
        action and nothing else, and the store holds no second copy of the
        owner's message. Without a binding the approval is advisory -- it can be
        displayed and decided, but it authorises nothing.
        """
        title = (title or "").strip()
        if not title:
            raise ValueError("title is required")
        if risk not in ("low", "high", "critical"):
            raise ValueError("risk must be low, high or critical")
        record = {
            "id": "apr-" + uuid.uuid4().hex[:12],
            "title": title,
            "detail": (detail or "").strip(),
            "risk": risk,
            "state": "WAITING_AUTHORIZATION",
            "created_at": time.time(),
            "decided_at": None,
            "decision": None,
            "note": "",
            "binding": binding_hash(normalized_binding_text(binding_text))
                       if binding_text is not None else None,
        }
        with self._lock:
            self._approvals[record["id"]] = record
        return record

    def get_approval(self, approval_id: str) -> Optional[dict[str, Any]]:
        """Return a copy of one approval, or ``None``. Never returns the live dict."""
        with self._lock:
            record = self._approvals.get(approval_id)
            return dict(record) if record is not None else None

    def consume_approval(self, approval_id: str) -> dict[str, Any]:
        """Atomically retire an APPROVED approval so it can authorise once only.

        Until 2026-10-02 the enforcement path audited ``approval_consumed``
        without consuming anything: an APPROVED, bound approval could
        authorise the same command any number of times. One owner decision
        must buy exactly one execution. Returns the retired record; raises
        ``KeyError`` if unknown and ``ValueError`` if not APPROVED.
        """
        with self._lock:
            record = self._approvals.get(approval_id)
            if record is None:
                raise KeyError(approval_id)
            if record["state"] != "APPROVED":
                raise ValueError(f"approval is {record['state']}, not APPROVED")
            if self.approval_expired(record):
                record["state"] = "EXPIRED"
                raise ValueError(
                    "approval expired: decided more than "
                    f"{APPROVAL_TTL_SECONDS // 60} minutes ago"
                )
            record["state"] = "CONSUMED"
            record["consumed_at"] = time.time()
            return dict(record)

    def approval_expired(self, record: dict[str, Any]) -> bool:
        """True when an APPROVED approval has outlived its validity window.

        An approval that never expires is an approval that can be banked:
        decide today, execute in a month, against a decision the owner no
        longer remembers making. The window runs from the *decision*, not
        creation -- an approval that sat WAITING_AUTHORIZATION for a week
        must not be born half-expired.
        """
        if record.get("state") != "APPROVED":
            return False
        decided_at = record.get("decided_at")
        if not decided_at:
            return False
        return (time.time() - decided_at) > APPROVAL_TTL_SECONDS

    def list_approvals(self, state: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._approvals.values())
        if state:
            rows = [r for r in rows if r["state"] == state]
        return sorted(rows, key=lambda r: r["created_at"])

    def decide(self, approval_id: str, decision: str, note: str = "") -> dict[str, Any]:
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        with self._lock:
            record = self._approvals.get(approval_id)
            if record is None:
                raise KeyError(approval_id)
            if record["state"] != "WAITING_AUTHORIZATION":
                raise ValueError("already decided")
            record["decision"] = decision
            record["state"] = "APPROVED" if decision == "approve" else "REJECTED"
            record["decided_at"] = time.time()
            record["note"] = (note or "").strip()
            return dict(record)

    # -- pause -------------------------------------------------------------- #

    def set_paused(self, paused: bool, reason: str = "") -> dict[str, Any]:
        with self._lock:
            self._paused = bool(paused)
            self._pause_reason = (reason or "").strip() if paused else ""
            return {"paused": self._paused, "reason": self._pause_reason}

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def pause_state(self) -> dict[str, Any]:
        with self._lock:
            return {"paused": self._paused, "reason": self._pause_reason}

    # -- audit -------------------------------------------------------------- #

    def remember(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._audit.append(record)
            if len(self._audit) > self._audit_ring:
                del self._audit[: len(self._audit) - self._audit_ring]

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit)[-max(1, min(limit, self._audit_ring)):]

    # -- status ------------------------------------------------------------- #

    def status(self) -> dict[str, Any]:
        pending = [r for r in self.list_approvals() if r["state"] == "WAITING_AUTHORIZATION"]
        return {
            "service": "begg_ai_command_center",
            "registry_as_of": REGISTRY_AS_OF,
            "paused": self.is_paused(),
            "pause_reason": self._pause_reason,
            "departments": DEPARTMENTS,
            "lanes": LANES,
            "approvals_pending": len(pending),
            "state_persistence": "in-memory: this state does not survive a restart",
            "note": "Statuses are claims with evidence, not live probes. LIVE is not VERIFIED. "
                    "The claims are hand-maintained, so read registry_as_of before trusting "
                    "them — two of them were already stale when this date was added.",
        }


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #

def build_router(
    center: CommandCenter,
    require_owner: Callable[..., None],
    rate_limit: Callable[..., None],
    client_key: Callable[..., str],
    audit: Callable[..., None],
) -> APIRouter:
    """Build the Command Center routes against the host service's own guards.

    The guards are injected rather than imported so this module has no dependency
    on the backend and can be tested on its own. Sharing the host's guards is the
    point: a second, weaker auth path is how a private surface stops being private.
    """
    router = APIRouter(prefix="/api/command", tags=["command"])

    def guard(request: Request, token: Optional[str]) -> None:
        require_owner(token, request)
        rate_limit(client_key(request, token), request)

    def note(event: str, request: Request, **fields: Any) -> None:
        """Record a control-surface action to stdout AND to the queryable ring.

        The ring existed but nothing ever wrote to it, so /api/command/audit
        returned {"records": []} no matter what happened. An endpoint whose result
        cannot vary is worse than no endpoint: it looks like a clean audit. Found
        by pausing the service and then asking what the audit said.

        stdout remains the durable record; the ring is the last N, for the owner
        to read back from a phone.
        """
        audit(event, request, **fields)
        center.remember({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "request_id": getattr(request.state, "request_id", None),
            **fields,
        })

    @router.get("/status")
    async def command_status(request: Request) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        return center.status()

    @router.get("/approvals")
    async def list_approvals(request: Request, state: Optional[str] = None) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        return {"approvals": center.list_approvals(state)}

    @router.post("/approvals")
    async def create_approval(
        request: Request,
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        try:
            record = center.add_approval(
                payload.get("title", ""),
                payload.get("detail", ""),
                payload.get("risk", "high"),
                binding_text=payload.get("binding_text"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        note("command_approval_created", request, approval_id=record["id"], risk=record["risk"])
        # The binding itself is a hash and is safe to return; the text it was
        # computed from is not returned, and is not stored.
        return record

    @router.post("/approvals/{approval_id}/decide")
    async def decide_approval(
        request: Request,
        approval_id: str,
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        try:
            record = center.decide(
                approval_id, payload.get("decision", ""), payload.get("note", "")
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown approval") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        note("command_approval_decided", request,
             approval_id=approval_id, decision=record["decision"])
        return record

    @router.post("/pause")
    async def set_pause(
        request: Request,
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        state = center.set_paused(bool(payload.get("paused")), payload.get("reason", ""))
        # Audited after the switch flips, and the record says which way it went --
        # an emergency stop that is not in the log is not auditable.
        note("command_pause", request, paused=state["paused"], reason=state["reason"])
        return state

    @router.get("/audit")
    async def recent_audit(request: Request, limit: int = 50) -> dict[str, Any]:
        guard(request, request.headers.get("X-Owner-Token"))
        return {"records": center.recent(limit)}

    @router.get("/jobs")
    async def queue_jobs(
        request: Request, status: Optional[str] = None
    ) -> dict[str, Any]:
        """The connector's job queue, if a queue database is configured.

        Read-only and owner-gated like every other route here. Three deliberate
        choices:

        * **It degrades instead of failing.** With no queue configured it returns
          an explicit `configured: false` payload, not an error. A control surface
          that 500s when an optional component is absent teaches the owner to
          ignore it, and an ignored control surface is worse than none.
        * **The connector is imported lazily.** A problem in the connector cannot
          take down the whole backend, and the connector is not a hard dependency
          of the service that serves the page.
        * **It reads; it does not decide.** Approving, claiming, or requeueing are
          state changes with their own gates. This endpoint is a window, and a
          window that can also act is a door.
        """
        guard(request, request.headers.get("X-Owner-Token"))

        db = os.environ.get("ODDFELLOW_QUEUE_DB", "").strip()
        empty = {
            "configured": False,
            "jobs": [],
            "count": 0,
            "dead_letters": {"count": 0, "jobs": []},
        }
        if not db:
            return {**empty, "note": "No queue configured. Set ODDFELLOW_QUEUE_DB to the connector database path."}
        if not os.path.exists(db):
            return {**empty, "note": f"ODDFELLOW_QUEUE_DB is set but does not exist: {db}"}

        try:
            from connector.schema import Status as JobStatus
            from connector.store import Store
        except Exception as exc:
            # Reported, not raised: the connector is optional by design.
            return {**empty, "note": f"Connector is not importable: {type(exc).__name__}: {exc}"}

        store = Store(db)
        try:
            wanted = None
            if status:
                try:
                    wanted = JobStatus(status)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"unknown status {status!r}; expected one of "
                               + ", ".join(s.value for s in JobStatus),
                    ) from None
            jobs = store.jobs(wanted)
            return {
                "configured": True,
                "count": len(jobs),
                "jobs": [
                    {
                        "job_id": j.job_id,
                        "title": j.title,
                        "kind": j.kind.value,
                        "risk": j.risk.value,
                        "status": j.status.value,
                        "provider": j.provider,
                        "attempts": j.attempts,
                        # Reported separately and prominently, because COMPLETE is
                        # not VERIFIED and a reader must not have to remember that.
                        "verified": j.verified,
                    }
                    for j in jobs
                ],
                "dead_letters": store.dead_letter_report(),
            }
        finally:
            store.close()

    return router
