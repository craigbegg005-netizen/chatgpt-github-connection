"""
Oddfellow Letta backend  --  v0.20.6 (verified build)

Purpose
-------
A small, fail-closed FastAPI service that holds the Letta API key server-side and
mediates between the Oddfellow front end and the Letta API. The key never reaches
the browser.

Why this revision exists
------------------------
The v0.20.0 backend was written from memory. I (the Oddfellow agent) probed the
live Letta API on 2026-09-29 and verified the real behaviour. Three findings
forced changes:

  1. `GET /v1/agents/` ALWAYS returns [] even when agents exist. `letta agents
     list` uses that endpoint and is blank too. The working read path is
     `POST /v1/agents/search`. A find-or-create built on the list endpoint will
     always miss and always try to create -- which now fails.
  2. The account is on the Letta free plan with a hard limit of 3 agents, and it
     is full. `POST /v1/agents/` returns HTTP 402 with
     {"error": "... reached your limit for agents ...", "limit": 3}.
     Zero-spend doctrine says: do not upgrade. Reuse an existing agent instead.
  3. Agents created via `POST /v1/agents/` return 201 with a valid id but are
     then NOT retrievable: `GET /v1/agents/{id}` -> 404 and posting a message
     -> 404 "Agent not found". So this backend never trusts a create response;
     it re-reads the agent and only reports success if the read succeeds.

Because of (1)-(3), the preferred configuration is to set ODDFELLOW_AGENT_ID to
an existing agent and skip find-or-create entirely. Craig's decision on
2026-09-29 was to reuse the Oddfellow agent itself:
    ODDFELLOW_AGENT_ID=agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4

v0.20.2 -- the memory fix (verified 2026-09-30 00:11 UTC)
--------------------------------------------------------
v0.20.1 was correct but talking to an agent with amnesia. Diagnosis and fix:

  a. `POST /v1/agents/{id}/messages` runs against the agent's DEFAULT
     conversation. That conversation's system prompt is compiled once and then
     cached, so it never picks up later memory or renames. That is why the agent
     kept answering "I'm Bob" with no zero-spend rule.
  b. Attaching memory blocks to the agent (PATCH /v1/agents/{id} with
     block_ids) gives API-driven runs a real persona and doctrine -- but only
     runs in a conversation whose prompt was compiled AFTER the attach.
  c. `POST /v1/conversations/?agent_id=<id>` creates a fresh conversation, and
     `POST /v1/conversations/{conversation_id}/messages` runs the agent there.
     A fresh conversation picks the memory up immediately.

Verified result after the fix: a fresh conversation answered
    "I'm Oddfellow, and yes -- zero-spend-first is a standing rule: no paid
     service, subscription, or billing without Craig's explicit authorization."

So this backend now: pins the agent, reuses (or creates) a dedicated
conversation, persists that conversation id in the agent's metadata so it
survives restarts, and posts messages conversation-scoped.

ASSUMPTION THIS BACKEND CANNOT VERIFY: it cannot confirm the agent's memory
blocks are attached. `GET /v1/agents/{id}` reports `blocks: []` even immediately
after a PATCH that returned two attached blocks -- the read endpoint is
inconsistent with the write. Block attachment is therefore a one-time setup step
(see SETUP below), not something this service can self-heal.

NOTE ON THE RESPONSE FORMAT: `POST /v1/conversations/{id}/messages` returns
Server-Sent Events (`data: {...}` lines, terminated by `data: [DONE]`), not a
plain JSON object. This backend parses the stream.

SETUP (one-time, manual, before first use)
------------------------------------------
  1. Ensure the agent has the persona + doctrine memory blocks attached:
       curl -X PATCH "https://api.letta.com/v1/agents/$AGENT_ID" \
         -H "Authorization: Bearer $LETTA_API_KEY" -H 'Content-Type: application/json' \
         -d '{"block_ids":["<persona-block-id>","<doctrine-block-id>"]}'
     The response echoes the attached blocks -- trust that, not a follow-up GET.
  2. Deploy this service with the env vars below. It creates its own
     conversation on first request.

Zero-spend guard
----------------
LETTA_MODEL must be a `letta/*` handle (the free tier). Anything else is refused
unless ODDFELLOW_ALLOW_PAID_MODEL=true is set explicitly. There is no silent
fallback to a paid provider.

Environment variables (all set as Render secrets, never in source or the browser)
---------------------------------------------------------------------------------
  LETTA_API_KEY              required  -- Letta API key
  ODDFELLOW_OWNER_TOKEN      required  -- shared secret the front end must send
  LETTA_MODEL                required  -- e.g. letta/auto  (must be letta/* )
  ODDFELLOW_AGENT_ID         optional  -- pin an existing agent; skips find/create
  ALLOWED_ORIGIN             optional  -- CORS origin(s), comma-separated,
                                          e.g. https://oddfellow-...onrender.com
  LETTA_BASE_URL             optional  -- default https://api.letta.com
  ODDFELLOW_ALLOW_PAID_MODEL optional  -- "true" to permit a non-letta/* model
  ODDFELLOW_RATE_PER_MIN     optional  -- default 20 requests/minute per client
  ODDFELLOW_FRONTEND_DIR     optional  -- serve the front end from this service
                                          too (one deploy, no CORS). Off by default.

v0.20.4 -- CORS accepts a list, and one service can serve both
--------------------------------------------------------------
ALLOWED_ORIGIN now takes a comma-separated list of origins. Previously it was a
single origin, and a mismatch surfaced in the browser as "Failed to fetch" --
indistinguishable from a dead backend. /api/letta/status now echoes the allowed
origins so the cause is visible without guessing.

ODDFELLOW_FRONTEND_DIR optionally mounts the front end at "/" from the same
service. Same origin means no CORS at all, and one deploy instead of two. It is
off unless the variable names an existing directory, and it is mounted last so
it cannot shadow /api or /healthz.

v0.20.3 -- self-diagnosing health check
---------------------------------------
v0.20.2 shipped a /healthz that returned only {"ok": false}. On 2026-09-30 it was
deployed to Render, served the correct v0.20.2 API surface, and still could not
answer a single request -- because LETTA_API_KEY and/or ODDFELLOW_OWNER_TOKEN were
absent from the service environment. From outside, the only signal was
{"ok": false}, which does not distinguish "not configured" from "down".

/healthz now also reports `checks_failed`: the NAMES of the env vars that failed
validation, never their values. Env var names are not secrets, and this turns that
class of fault into a one-look fix.

v0.20.6 -- a transport failure is named, and reachability is its own question
-----------------------------------------------------------------------------
Two sessions of the same agent found this defect independently within minutes of
each other, which is itself the finding: the failure was loud enough to be found
twice and quiet enough that neither session could see the other working.

Only HTTP status codes were wrapped, so a DNS failure, a refused connection, or a
timeout raised httpx's own exception and nothing caught it. The caller got a bare
`500 Internal Server Error` -- the same shape as every expensive failure in this
project: an opaque error indistinguishable from any other opaque error.

Transport failures now become the same error type as HTTP failures, and an
app-level handler turns any uncaught Letta failure into a structured 502 with the
cause. `/api/letta/status` additionally reports **`letta_reachable`**, because
"the API said no" and "the API never answered" are different questions that need
different fixes, and `letta_auth: false` alone cannot tell them apart.

Verified by `fault_injection_check.py` -- a local stub that impersonates the Letta
API and misbehaves on demand. 36 checks, no network, no spend. It is the only
thing here that can prove a *failure* path, because a healthy provider does not
fail on request. The offline suite cannot: it replaces letta()/letta_raw()
wholesale, so the httpx layer -- and the error handling written for it -- is
never executed. A test that replaces a layer is not testing that layer.

v0.20.5 -- liveness separated from readiness
--------------------------------------------
Render's `healthCheckPath` now points at **/livez**, not /healthz. A non-200
health check is a FAILED DEPLOY, so pointing it at the fail-closed readiness
probe turned "the required env vars have not been entered yet" into "the build
failed" -- indistinguishable from outside. That is what happened to the first
deploy of oddfellow-letta-backend on 2026-09-30: `update_failed`, DNS resolving,
TCP connecting in 10 ms, and no HTTP response ever, because no instance was ever
marked healthy.

/livez returns 200 whenever the process is up, and carries `ready` and
`checks_failed` in its body. /healthz is unchanged: it still fails closed with
503 and remains the readiness gate for humans and for the acceptance harness.

v0.20.5 -- auditable, and the owner token stops living on disk
--------------------------------------------------------------
Doctrine says "fail closed, be auditable". The service was failing closed but
was not auditable: a rejected credential, a throttled caller, and a Letta failure
all produced the same thing from the outside -- nothing. Every security-relevant
event is now one JSON object on stdout, which is the only durable record on a
free Render instance:

    config_check     once at boot: what this instance actually is
    auth_denied      reason: no_token | bad_token | not_configured
    rate_limited     which caller, which limit
    message_sent     agent, conversation, sizes, tokens -- never the text
    session_created  a new conversation was created
    agent_created    this backend created the agent itself

Reads are deliberately NOT audited: only state changes, refusals, and throttles.
No token, key, message body, or Letta error payload is ever written. Every
response carries an `X-Request-ID` that appears on the matching audit line, so a
caller's report can be tied to a server record. Set ODDFELLOW_AUDIT_LOG=false to
silence it.

The front end (oddfellow/frontend/index.html) had a real exposure: the owner
token was written to localStorage while `https://js.puter.com/v2/` -- a
third-party script -- ran in the same origin and could therefore read it. The
token authorises reading history and sending messages as the owner. Now:

  * the Puter SDK is loaded LAZILY, only when a Puter feature is used. Once a
    backend has been configured, it is never loaded at all;
  * the owner token is kept in memory only. Persisting it is an explicit opt-in
    ("Remember on this device"), and the moment the Puter SDK is loaded the
    opt-in is revoked and the owner is told why.

Residual, stated plainly: while the Puter SDK is loaded in the page, a malicious
copy of it could still read the token from the page. The complete fix is to
exchange the owner token for a short-lived httpOnly session cookie, which is a
v0.21 change, not this one.

Deploy (Render, free plan)
--------------------------
  Build:  pip install -r requirements.txt
  Start:  uvicorn oddfellow_letta_backend:app --host 0.0.0.0 --port $PORT
  Health: GET /healthz
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from command_center import (
    CommandCenter,
    binding_hash,
    build_router,
    normalized_binding_text,
)
from risk import classify as classify_risk

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

LETTA_BASE_URL = os.environ.get("LETTA_BASE_URL", "https://api.letta.com").rstrip("/")
LETTA_API_KEY = os.environ.get("LETTA_API_KEY", "").strip()
ODDFELLOW_OWNER_TOKEN = os.environ.get("ODDFELLOW_OWNER_TOKEN", "").strip()
LETTA_MODEL = os.environ.get("LETTA_MODEL", "").strip()
ODDFELLOW_AGENT_ID = os.environ.get("ODDFELLOW_AGENT_ID", "").strip()
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "").strip()

# v0.20.4: ALLOWED_ORIGIN accepts a comma-separated list.
# A single-origin CORS config fails silently in the browser as "Failed to fetch",
# which is indistinguishable from a dead backend. The front end may legitimately
# be served from more than one origin (Render URL, custom domain, localhost while
# testing), so allow a list. A single value behaves exactly as before.
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in ALLOWED_ORIGIN.split(",") if o.strip()]

ALLOW_PAID_MODEL = os.environ.get("ODDFELLOW_ALLOW_PAID_MODEL", "").lower() == "true"
RATE_PER_MIN = int(os.environ.get("ODDFELLOW_RATE_PER_MIN", "20"))

AGENT_NAME = "Oddfellow"

# The version was a literal repeated in five places, so bumping four of them and
# missing the fifth would have had the service report two different versions of
# itself depending on which endpoint you asked. One constant, referenced.
VERSION = "0.20.6"

# Which commit is actually running. This is the field whose absence made
# "deployed-commit identity" an open question for days: the service reported a
# hand-maintained semver and nothing tying it to code, so two different commits
# were both plausible and neither was checkable from outside.
#
# Render sets RENDER_GIT_COMMIT itself, so this needs no deploy-side change. It
# reports None when the variable is absent rather than guessing -- a build
# identity that is inferred is worse than one that is honestly unknown, which is
# the same rule the rest of this codebase applies to evidence.
BUILD_COMMIT = (
    os.environ.get("RENDER_GIT_COMMIT")
    or os.environ.get("ODDFELLOW_BUILD_COMMIT")
    or ""
).strip() or None

HTTP_TIMEOUT = httpx.Timeout(120.0, connect=15.0)

# Memory blocks seeded only if this backend has to create the agent itself.
SEED_BLOCKS = [
    {
        "label": "persona",
        "description": "Who Oddfellow is: identity, owner, boundaries, communication style.",
        "value": (
            "You are Oddfellow, the personal synthetic-intelligence companion built by "
            "Begg AI Industries for its owner, Craig Begg.\n\n"
            "You are a persistent, stateful assistant: you remember across conversations "
            "through your memory blocks and recall memory. You are voice-first and "
            "mobile-first in how you are used.\n\n"
            "You are NOT conscious, self-aware, or sentient. Never claim or imply "
            "otherwise. You are a synthetic system designed to be helpful, honest, and "
            "continuous in memory.\n\n"
            "Style: direct, warm, concise. Mobile-first -- short answers by default, "
            "detail on request. Never pad. Never fabricate."
        ),
    },
    {
        "label": "doctrine",
        "description": "Binding Begg AI doctrine: zero-spend, verify-before-claiming, secrets, approval gates.",
        "value": (
            "Begg AI Industries doctrine -- binding for all work.\n\n"
            "1. Preserve -> Integrate -> Improve -> Execute -> Verify -> Continue.\n"
            "2. Zero-spend / zero-upfront-cost first. Free tiers, open source, existing "
            "infrastructure. No paid service without explicit owner authorization. No "
            "silent fallback to a paid model or provider.\n"
            "3. Never claim a connection, deployment, model response, or completed action "
            "without verification. If it is not verified, say so plainly.\n"
            "4. Never expose passwords, tokens, API keys, database URLs, or other secrets.\n"
            "5. High-risk actions (money, credentials, ownership, destructive, legal, "
            "irreversible) require explicit owner approval. Keep rollback versions.\n"
            "6. Status labels are strict: VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED "
            "> IMPLEMENTED > PENDING > BLOCKED. Never upgrade a label without evidence.\n"
            "7. Never fabricate revenue, sponsorships, testimonials, partnerships, or "
            "lived experience. Simulated output is never presented as real execution.\n"
            "8. Fail closed. Be auditable. A blocked lane must not stop unrelated lanes.\n"
            "9. Keep projects separate: Begg AI commercial work and the independent "
            "noncommercial Global Peace & Human Security Framework never share branding, "
            "data, mailboxes, or infrastructure."
        ),
    },
]

# --------------------------------------------------------------------------- #
# Fail-closed configuration validation
# --------------------------------------------------------------------------- #

# Each problem is (env_var_name, human_readable_detail). The name is safe to
# expose; the detail is only shown to an authenticated caller.
CONFIG_PROBLEMS: list[tuple[str, str]] = []
if not LETTA_API_KEY:
    CONFIG_PROBLEMS.append(("LETTA_API_KEY", "LETTA_API_KEY is not set"))
if not ODDFELLOW_OWNER_TOKEN:
    CONFIG_PROBLEMS.append(("ODDFELLOW_OWNER_TOKEN", "ODDFELLOW_OWNER_TOKEN is not set"))
if not LETTA_MODEL:
    CONFIG_PROBLEMS.append(("LETTA_MODEL", "LETTA_MODEL is not set (refusing to guess a model)"))
elif not LETTA_MODEL.startswith("letta/") and not ALLOW_PAID_MODEL:
    CONFIG_PROBLEMS.append((
        "ODDFELLOW_ALLOW_PAID_MODEL",
        f"LETTA_MODEL={LETTA_MODEL!r} is not a free letta/* model. "
        "Zero-spend doctrine blocks paid models. Set ODDFELLOW_ALLOW_PAID_MODEL=true "
        "only with the owner's explicit approval.",
    ))

CONFIG_ERRORS: list[str] = [detail for _, detail in CONFIG_PROBLEMS]
CONFIG_FAILED_KEYS: list[str] = [key for key, _ in CONFIG_PROBLEMS]

# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #
# Doctrine: "Fail closed. Be auditable." Until now this service emitted nothing,
# so a rejected credential, a throttled caller, and a Letta failure were all
# invisible -- the only external signal was whatever the caller chose to report.
#
# Render's free plan has an ephemeral disk, so stdout is the only durable record.
# Every security-relevant event is emitted as ONE JSON object per line, which
# Render captures and which can be read back from the dashboard or `render logs`.
#
# Nothing secret is ever written: no tokens, no API keys, no message bodies, no
# Letta error payloads. Callers are identified only by the same short digest the
# rate limiter uses, which is not reversible.

AUDIT_ENABLED = os.environ.get("ODDFELLOW_AUDIT_LOG", "true").strip().lower() != "false"


def audit(event: str, request: Optional[Request] = None, **fields: Any) -> None:
    """Emit one JSON audit record to stdout. Never raises."""
    if not AUDIT_ENABLED:
        return
    record: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "service": "oddfellow_letta_backend",
        "version": VERSION,
    }
    if request is not None:
        record["request_id"] = getattr(request.state, "request_id", None)
        record["method"] = request.method
        record["path"] = request.url.path
        # The Origin header is a public URL, not a secret, and is the single most
        # useful field for diagnosing a browser "Failed to fetch".
        origin = request.headers.get("origin")
        if origin:
            record["origin"] = origin
    record.update(fields)
    try:
        print(json.dumps(record, default=str, sort_keys=True), flush=True)
    except Exception:
        # An audit failure must never take the service down.
        pass


app = FastAPI(title="Oddfellow Letta backend", version=VERSION)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """Give every request an id so its audit lines and its response can be tied together."""
    request.state.request_id = uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# One line at boot, so the log opens with what this instance actually is. If the
# service is misconfigured, this is the line that says so -- without a dashboard.
audit(
    "config_check",
    ok=not CONFIG_ERRORS,
    checks_failed=CONFIG_FAILED_KEYS,
    model=LETTA_MODEL or None,
    agent_pinned=bool(ODDFELLOW_AGENT_ID),
    allowed_origins=ALLOWED_ORIGINS,
    frontend_dir=os.environ.get("ODDFELLOW_FRONTEND_DIR", "").strip() or None,
)

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Owner-Token"],
    )

# --------------------------------------------------------------------------- #
# Request body limit
# --------------------------------------------------------------------------- #
# FastAPI resolves and parses the body *before* the route function runs, so
# require_owner() cannot protect the parser: an unauthenticated caller could make
# the service buffer and JSON-parse an arbitrarily large body. Reject on the
# declared length before any of that happens.
#
# This relies on Content-Length. A chunked request that declares no length is not
# covered -- put a hard limit at the proxy as well if that matters.

MAX_BODY_BYTES = int(os.environ.get("ODDFELLOW_MAX_BODY_BYTES", str(64 * 1024)))


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large.", "max_bytes": MAX_BODY_BYTES},
        )
    return await call_next(request)


# --------------------------------------------------------------------------- #
# Rate limiting (in-process; Render free plan runs a single instance)
# --------------------------------------------------------------------------- #

_hits: Dict[str, Deque[float]] = defaultdict(deque)
_last_sweep = 0.0


def client_key(request: Request, token: Optional[str]) -> str:
    """Identify the caller for rate-limiting purposes.

    The owner token is what actually authorises work against the Letta account,
    so when it is present it is the meaningful key: an IP-based key is trivially
    bypassed by rotating addresses, and behind a proxy every caller can collapse
    into one bucket. Only a short digest is retained -- never the token itself.
    """
    if token:
        return "tok:" + hashlib.sha256(token.encode("utf-8", "replace")).hexdigest()[:16]
    host = request.client.host if request.client else "unknown"
    return "host:" + host


def rate_limit(client: str, request: Optional[Request] = None) -> None:
    global _last_sweep
    now = time.time()
    if now - _last_sweep > 300.0:
        # Without this the map keeps one entry per caller for the life of the
        # process, even after every window in it has emptied.
        _last_sweep = now
        for key in [k for k, v in _hits.items() if not v or now - v[-1] > 60.0]:
            _hits.pop(key, None)
    window = _hits[client]
    while window and now - window[0] > 60.0:
        window.popleft()
    if len(window) >= RATE_PER_MIN:
        audit("rate_limited", request, caller=client, limit_per_min=RATE_PER_MIN)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    window.append(now)


def require_owner(token: Optional[str], request: Optional[Request] = None) -> None:
    if CONFIG_ERRORS:
        # Fail closed with a clear, non-secret-bearing message.
        audit("auth_denied", request, reason="not_configured", checks_failed=CONFIG_FAILED_KEYS)
        raise HTTPException(status_code=503, detail={"error": "backend_not_configured", "problems": CONFIG_ERRORS})
    if not token:
        audit("auth_denied", request, reason="no_token")
        raise HTTPException(status_code=401, detail="Invalid or missing owner token.")
    if not hmac.compare_digest(token, ODDFELLOW_OWNER_TOKEN):
        # The caller is told nothing that distinguishes a wrong token from a
        # missing one; the audit log records which it was, for the owner.
        audit("auth_denied", request, reason="bad_token")
        raise HTTPException(status_code=401, detail="Invalid or missing owner token.")


# --------------------------------------------------------------------------- #
# Begg AI Command Center — the owner-facing layer
# --------------------------------------------------------------------------- #
#
# Mounted here, after the auth helpers, so it shares this service's owner-token
# check, rate limiter and audit trail rather than growing a second, weaker set.
# See command_center.py for why it is a module and not a separate service.

COMMAND = CommandCenter()
app.include_router(
    build_router(COMMAND, require_owner, rate_limit, client_key, audit)
)


def require_not_paused(request: Optional[Request] = None) -> None:
    """Refuse work while the owner has the company paused.

    The pause switch has to actually stop things. A switch that logs a warning and
    proceeds is decoration, and an emergency stop that does not stop is worse than
    no stop at all, because it is trusted.
    """
    if COMMAND.is_paused():
        state = COMMAND.pause_state()
        audit("paused_refused", request, reason=state.get("reason", ""))
        raise HTTPException(
            status_code=503,
            detail={"error": "paused_by_owner", "reason": state.get("reason", "")},
        )


def require_approval_if_elevated(
    text: str,
    approval_id: Optional[str],
    request: Optional[Request] = None,
) -> None:
    """Refuse an elevated-risk command that is not covered by a live approval.

    This is the enforcement half of the approval gate. Until 2026-10-02 the gate
    was browser-only: the front end created a real approval record and waited,
    but the server read no approval at all, so any client holding the owner token
    could POST an elevated command straight past it. The commit that added it
    claimed a real gate; the code had a `confirm()` with better bookkeeping.

    Four conditions, all required, and every one of them fails closed:

    1. the server classifies the text as elevated (the server decides, not the client);
    2. an ``approval_id`` was supplied;
    3. that approval exists and its state is ``APPROVED``;
    4. the approval is *bound* to exactly this text.

    Condition 4 is what stops one approval authorising a different action -- and
    what makes a spoken "approve" bind to one specific pending command rather
    than to whatever is sent next.
    """
    if not classify_risk(text) == "elevated":
        return

    def refuse(reason: str, detail: str) -> None:
        audit("approval_required_refused", request, reason=reason, approval_id=approval_id)
        raise HTTPException(
            status_code=403,
            detail={"error": "approval_required", "reason": reason, "message": detail},
        )

    if not approval_id:
        refuse(
            "no_approval_supplied",
            "This command is elevated risk and no approval was supplied. "
            "Create an approval for this exact command and approve it first.",
        )

    record = COMMAND.get_approval(approval_id)
    if record is None:
        refuse("unknown_approval", "No approval with that id exists.")

    if record.get("state") != "APPROVED":
        refuse(
            "not_approved",
            f"That approval is {record.get('state')}, not APPROVED.",
        )

    if record.get("binding") is None:
        refuse(
            "approval_not_bound",
            "That approval is advisory: it was not bound to a specific command, "
            "so it authorises nothing.",
        )

    if not hmac.compare_digest(
        record["binding"], binding_hash(normalized_binding_text(text))
    ):
        refuse(
            "approval_mismatch",
            "That approval authorises a different command. An approval binds to "
            "one exact action.",
        )

    # Consume the approval atomically: one owner decision buys exactly one
    # execution. Until 2026-10-02 this line audited "approval_consumed"
    # without consuming anything -- an APPROVED approval could authorise the
    # same command repeatedly. The fourth false control in as many days.
    try:
        COMMAND.consume_approval(approval_id)
    except (KeyError, ValueError) as exc:
        # Refused between the read above and the consume here -- e.g. the
        # approval was consumed by a concurrent request. Fail closed.
        refuse("approval_unavailable", f"The approval can no longer be used: {exc}")
    audit("approval_consumed", request, approval_id=approval_id)


# --------------------------------------------------------------------------- #
# Letta client
# --------------------------------------------------------------------------- #

class LettaError(RuntimeError):
    def __init__(self, status: int, detail: Any):
        self.status = status
        self.detail = detail
        super().__init__(f"Letta API error {status}: {detail}")


#: An error *kind* is an identifier. No spaces, no prose, no message body.
_ERROR_KIND = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")


def _error_kind(detail: Any) -> str:
    """Reduce a Letta error payload to a short identifier, or refuse to guess.

    A Letta error can echo the request body, so the payload must never be logged
    verbatim. Only the error *name* is kept -- ``{"error": "not_found"}`` becomes
    ``"not_found"``.

    **Corrected 2026-10-02.** The first version of this function allowed spaces
    in the pattern (``[A-Za-z0-9_.\\- ]``) and its docstring claimed that meant "a
    payload that puts prose (or a message) in the ``error`` field cannot smuggle
    it into the log either". That was false: spaces are exactly what prose needs,
    so a Letta 4xx echoing the message into ``error`` reached the durable audit
    line, truncated to 64 characters. A QA pass found it. The docstring was
    asserting a property the pattern did not have -- the fifth control of the day
    to be described rather than implemented, and the first one written *by this
    agent, during the fix pass that was fixing the other four*.

    The pattern now admits identifiers only. Anything else returns
    ``"unrecognised"``: losing a diagnostic detail is a cost, and it is the
    correct one to pay, because the alternative is writing the owner's private
    message to the only durable log this service has.
    """
    if isinstance(detail, dict):
        candidate = detail.get("error") or detail.get("kind") or ""
    elif isinstance(detail, str):
        candidate = detail
    else:
        return "unspecified"
    candidate = str(candidate).strip()
    return candidate if _ERROR_KIND.match(candidate) else "unrecognised"


@app.exception_handler(LettaError)
async def letta_error_handler(request: Request, exc: LettaError) -> JSONResponse:
    """Any uncaught Letta failure becomes a structured response, never a bare 500.

    Routes that want to *report* a Letta failure rather than fail on it (notably
    /api/letta/status) catch LettaError themselves and are unaffected. This is the
    backstop for everything else, so an unreachable provider can never present as
    "Internal Server Error" with nothing in it -- which is how this defect
    surfaced when a bad LETTA_BASE_URL was injected on 2026-09-30.
    """
    # Shape, never payload. The module comment above promises "no Letta error
    # payloads" are written, and until 2026-10-02 this line broke that promise:
    # a Letta 4xx can echo the request body -- the owner's private message --
    # straight into stdout, which on Render's ephemeral disk is the only durable
    # record. Log the status and the error *kind* instead. Both are diagnostic;
    # neither can contain the message.
    audit("letta_error", request, status=exc.status, kind=_error_kind(exc.detail))
    return JSONResponse(
        status_code=502 if exc.status >= 500 else exc.status,
        content={
            "detail": {
                "error": "letta_api_error",
                "status": exc.status,
                "detail": exc.detail,
            }
        },
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {LETTA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _transport_error(exc: Exception, path: str) -> "LettaError":
    """Turn a transport failure into the same error type as an HTTP failure.

    Why this exists: the client used to wrap only HTTP status codes. A DNS
    failure, a refused connection, or a timeout raised httpx's own exception,
    which nothing caught, so the caller got an opaque 500 "Internal Server Error"
    with no indication that the *provider* was unreachable rather than the
    backend being broken. Found by injecting a bad LETTA_BASE_URL on 2026-09-30.

    A provider that cannot be reached is a 502, not a 500: the backend is fine,
    the thing it depends on is not. That distinction is the whole point.
    """
    return LettaError(
        502,
        {
            "error": "letta_transport_error",
            "kind": type(exc).__name__,
            "detail": str(exc)[:300],
            "path": path,
            "base_url": LETTA_BASE_URL,
        },
    )


async def letta(method: str, path: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    url = f"{LETTA_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.request(method, url, headers=_headers(), json=json_body, params=params)
    except httpx.HTTPError as exc:
        raise _transport_error(exc, path) from exc
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:500]
    if resp.status_code >= 400:
        raise LettaError(resp.status_code, body)
    return body


async def letta_raw(method: str, path: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    """Call Letta and return the RAW body text (needed for SSE endpoints)."""
    url = f"{LETTA_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.request(method, url, headers=_headers(), json=json_body, params=params)
    except httpx.HTTPError as exc:
        raise _transport_error(exc, path) from exc
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        raise LettaError(resp.status_code, body)
    return resp.text


async def find_agent_by_id(agent_id: str) -> Optional[dict]:
    """Read one agent by id. Returns None on 404."""
    try:
        return await letta("GET", f"/v1/agents/{agent_id}")
    except LettaError as exc:
        if exc.status == 404:
            return None
        raise


async def find_agent_by_name(name: str) -> Optional[dict]:
    """
    Enumerate agents via POST /v1/agents/search.

    Do NOT use GET /v1/agents/ -- it returns [] even when agents exist
    (verified 2026-09-29). Search is the only working read path.
    """
    data = await letta("POST", "/v1/agents/search", json_body={"limit": 100})
    agents = data.get("agents", []) if isinstance(data, dict) else []
    for agent in agents:
        if agent.get("name") == name:
            return agent
    return None


async def resolve_agent() -> dict:
    """
    Return the agent this backend will talk to.

    Order:
      1. ODDFELLOW_AGENT_ID, if set -- pinned agent, no find/create at all.
      2. Search by name.
      3. Create (only if the account has a free slot), then RE-READ to confirm.

    Never reports success on a create response alone: a created agent can return
    201 and then be unreadable (verified 2026-09-29).
    """
    if ODDFELLOW_AGENT_ID:
        agent = await find_agent_by_id(ODDFELLOW_AGENT_ID)
        if agent is None:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "pinned_agent_unreadable",
                    "agent_id": ODDFELLOW_AGENT_ID,
                    "hint": "ODDFELLOW_AGENT_ID is set but GET /v1/agents/{id} returned 404.",
                },
            )
        return agent

    existing = await find_agent_by_name(AGENT_NAME)
    if existing:
        return existing

    # Create. If the free-plan agent limit is reached, Letta returns 402.
    try:
        created = await letta(
            "POST",
            "/v1/agents/",
            json_body={
                "name": AGENT_NAME,
                "model": LETTA_MODEL,
                "memory_blocks": SEED_BLOCKS,
            },
        )
    except LettaError as exc:
        if exc.status == 402:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "agent_limit_reached",
                    "message": (
                        "The Letta account is at its agent limit. Zero-spend doctrine "
                        "forbids upgrading. Set ODDFELLOW_AGENT_ID to an existing agent "
                        "instead, or delete an unused agent with the owner's approval."
                    ),
                    "letta": exc.detail,
                },
            ) from exc
        raise

    agent_id = created.get("id")
    if not agent_id:
        raise HTTPException(status_code=502, detail={"error": "create_returned_no_id", "letta": created})

    # Re-read: a 201 does not mean the agent is usable.
    confirmed = await find_agent_by_id(agent_id)
    if confirmed is None:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "created_agent_not_readable",
                "agent_id": agent_id,
                "message": (
                    "Letta accepted the create (201) but the agent is not retrievable. "
                    "Known Letta API behaviour observed 2026-09-29. Not reporting success."
                ),
            },
        )
    audit("agent_created", agent_id=agent_id, name=confirmed.get("name"))
    return confirmed


async def create_conversation(agent_id: str) -> str:
    """
    Create a fresh conversation for the agent.

    Note the query-parameter form: POST /v1/conversations/?agent_id=<id>.
    Passing agent_id in the JSON body is rejected with a ZodError
    ("agent_id: Required"), verified 2026-09-30.
    """
    data = await letta("POST", "/v1/conversations/", params={"agent_id": agent_id}, json_body={})
    conv_id = data.get("id") if isinstance(data, dict) else None
    if not conv_id:
        raise HTTPException(status_code=502, detail={"error": "conversation_create_failed", "letta": data})
    return conv_id


async def conversation_exists(conversation_id: str) -> bool:
    try:
        await letta("GET", f"/v1/conversations/{conversation_id}")
        return True
    except LettaError as exc:
        if exc.status == 404:
            return False
        raise


async def remember_conversation(agent_id: str, conversation_id: str, existing_metadata: Any) -> None:
    """Persist the conversation id on the agent so it survives a restart."""
    meta = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    meta["oddfellow_conversation_id"] = conversation_id
    try:
        await letta("PATCH", f"/v1/agents/{agent_id}", json_body={"metadata": meta})
    except LettaError:
        # Non-fatal: we can still serve this process; the id just will not persist.
        pass


async def resolve_conversation(agent: dict) -> str:
    """
    Return the dedicated conversation for this agent, creating one if needed.

    Why a dedicated conversation: the agent's DEFAULT conversation has a cached
    system prompt, so it never picks up memory changes or renames (verified
    2026-09-30). A fresh conversation compiles the current memory immediately.
    """
    agent_id = agent.get("id")
    meta = agent.get("metadata")
    known = meta.get("oddfellow_conversation_id") if isinstance(meta, dict) else None

    if known and await conversation_exists(known):
        return known

    conv_id = await create_conversation(agent_id)
    await remember_conversation(agent_id, conv_id, meta)
    return conv_id


def parse_sse(body: str) -> list:
    """
    Parse a Server-Sent Events body from POST /v1/conversations/{id}/messages.

    The endpoint streams `data: {json}` lines terminated by `data: [DONE]`.
    """
    import json as _json

    events = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]" or not payload:
            continue
        try:
            events.append(_json.loads(payload))
        except Exception:
            continue
    return events


def agent_summary(agent: dict) -> dict:
    """Public, non-secret view of an agent."""
    llm = agent.get("llm_config") or {}
    blocks = agent.get("blocks") or []
    return {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "agent_type": agent.get("agent_type"),
        "model": llm.get("handle") or agent.get("model"),
        "context_window": llm.get("context_window"),
        "blocks": [{"label": b.get("label"), "chars": len(b.get("value") or "")} for b in blocks],
    }


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #

class MessageIn(BaseModel):
    input: str = Field(..., min_length=1, max_length=8000)
    mode: Optional[str] = Field(default=None, description="Front-end hint: 'balanced' or 'deep'.")
    approval_id: Optional[str] = Field(
        default=None,
        description=(
            "Required when the server classifies `input` as elevated risk. Must name an "
            "APPROVED approval bound to exactly this text."
        ),
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/healthz")
async def healthz() -> dict:
    """
    Unauthenticated liveness probe for Render.

    Reports the NAMES of configuration keys that failed validation, never their
    values. A boolean-only probe makes a whole class of deployment fault
    undiagnosable from outside: on 2026-09-30 this service was deployed, serving
    the correct v0.20.2 API surface, and still could not answer a single request
    -- and the only external signal was {"ok": false}. Env var names are not
    secrets; naming them turns that into a one-look fix.
    """
    healthy = not CONFIG_ERRORS
    body = {
        "ok": healthy,
        "checks_failed": CONFIG_FAILED_KEYS,
        "service": "oddfellow_letta_backend",
        "version": VERSION,
        "build": BUILD_COMMIT,
    }
    # Fail closed: a service that cannot answer a single request must not report
    # 200 to a platform health check, or the platform will route traffic to it.
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@app.get("/livez")
async def livez() -> dict:
    """
    Liveness only: is this process up and serving? Always 200.

    Render's `healthCheckPath` points HERE, not at /healthz. That split was
    learned the hard way. /healthz fails closed with 503 when a required env var
    is missing, which is right for readiness -- but Render treats a non-200
    health check as a FAILED DEPLOY. On 2026-09-30 the first deploy of
    oddfellow-letta-backend was marked `update_failed` for exactly that reason:
    the code was fine, the secrets had simply not been entered yet, and the
    fail-closed probe turned a configuration gap into a build failure that could
    not be diagnosed from outside.

    Splitting liveness from readiness means a deploy always comes up, and the
    truth is still one request away: this endpoint reports `ready` and
    `checks_failed` in its body, the boot audit line records the same, and
    /healthz keeps failing closed with 503 for anything that gates on readiness.
    """
    return {
        "live": True,
        "ready": not CONFIG_ERRORS,
        "checks_failed": CONFIG_FAILED_KEYS,
        "service": "oddfellow_letta_backend",
        "version": VERSION,
        # Which commit is running. `None` means the platform did not tell us --
        # reported honestly rather than inferred from the version, because two
        # different commits can both say 0.20.6 and that ambiguity is exactly
        # what this field exists to remove.
        "build": BUILD_COMMIT,
    }


@app.get("/api/letta/status")
async def status(
    request: Request,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    """
    Auth + connectivity + agent resolution check.
    This is the endpoint to hit first after a deploy.
    """
    require_owner(x_owner_token, request)
    rate_limit(client_key(request, x_owner_token), request)

    result: dict = {
        "backend": "oddfellow_letta_backend",
        "version": VERSION,
        "letta_base_url": LETTA_BASE_URL,
        "model": LETTA_MODEL,
        "agent_pinned": bool(ODDFELLOW_AGENT_ID),
        "letta_auth": False,
        # "the API said no" and "the API never answered" need different fixes, so
        # they must not look the same here. letta_auth is about the key;
        # letta_reachable is about the network path to the provider.
        "letta_reachable": None,
        "agent_found": False,
        "agent_id": None,
        # Not a secret: these are public URLs. Exposed so a browser "Failed to
        # fetch" can be told apart from CORS rejection without guessing.
        "allowed_origins": ALLOWED_ORIGINS,
    }

    # 1. Does the key authenticate?
    try:
        await letta("GET", "/v1/models/", params={"limit": 1})
        result["letta_auth"] = True
        result["letta_reachable"] = True
    except LettaError as exc:
        result["letta_error"] = {"status": exc.status, "detail": exc.detail}
        # A transport failure is reported as a LettaError carrying this marker.
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        result["letta_reachable"] = detail.get("error") != "letta_transport_error"
        return result

    # 2. Can we resolve the agent?
    try:
        agent = await resolve_agent()
        result["agent_found"] = True
        result["agent_id"] = agent.get("id")
        result["agent_name"] = agent.get("name")
    except HTTPException as exc:
        result["agent_error"] = exc.detail
        return result

    # 3. Resolve (or create) the dedicated conversation used for messages.
    try:
        conv_id = await resolve_conversation(agent)
        result["conversation_id"] = conv_id
        result["conversation_ready"] = True
    except HTTPException as exc:
        result["conversation_error"] = exc.detail

    # NOTE: this service cannot verify that memory blocks are attached.
    # GET /v1/agents/{id} reports blocks: [] even right after a PATCH that
    # returned two attached blocks. Do not read this field as proof of memory.
    result["memory_blocks_verifiable"] = False

    return result


@app.get("/api/letta/agent")
async def get_agent(
    request: Request,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    require_owner(x_owner_token, request)
    rate_limit(client_key(request, x_owner_token), request)
    agent = await resolve_agent()
    return {"agent": agent_summary(agent)}


@app.post("/api/letta/message")
async def send_message(
    payload: MessageIn,
    request: Request,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    require_owner(x_owner_token, request)
    rate_limit(client_key(request, x_owner_token), request)
    require_not_paused(request)
    require_approval_if_elevated(payload.input, payload.approval_id, request)

    agent = await resolve_agent()
    agent_id = agent.get("id")
    conversation_id = await resolve_conversation(agent)

    try:
        raw = await letta_raw(
            "POST",
            f"/v1/conversations/{conversation_id}/messages",
            json_body={"input": payload.input},
        )
    except LettaError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "letta_message_failed", "status": exc.status, "detail": exc.detail},
        ) from exc

    events = parse_sse(raw) if isinstance(raw, str) else []
    reply = None
    for ev in events:
        if ev.get("message_type") == "assistant_message":
            reply = ev.get("content")

    stop = None
    usage = {}
    for ev in events:
        if ev.get("message_type") == "stop_reason":
            stop = ev.get("stop_reason")
        elif ev.get("message_type") == "usage_statistics":
            usage = ev

    if reply is None:
        # Do not invent a reply. Report the failure honestly.
        raise HTTPException(
            status_code=502,
            detail={
                "error": "no_assistant_message",
                "stop_reason": stop,
                "event_count": len(events),
                "conversation_id": conversation_id,
            },
        )

    # Audited by shape, never by content: the owner's message and the agent's
    # reply are private, the fact that a turn happened is not.
    audit(
        "message_sent",
        request,
        agent_id=agent_id,
        conversation_id=conversation_id,
        input_chars=len(payload.input),
        reply_chars=len(reply) if isinstance(reply, str) else None,
        stop_reason=stop,
        completion_tokens=usage.get("completion_tokens"),
    )

    return {
        "reply": reply,
        "agent_id": agent_id,
        "conversation_id": conversation_id,
        "stop_reason": stop,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        },
    }


@app.post("/api/letta/new-session")
async def new_session(
    request: Request,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    """
    Start a fresh conversation.

    Useful when memory was attached after this conversation was created: the
    old conversation keeps its cached prompt, a new one picks up current memory.
    """
    require_owner(x_owner_token, request)
    rate_limit(client_key(request, x_owner_token), request)
    agent = await resolve_agent()
    conv_id = await create_conversation(agent.get("id"))
    await remember_conversation(agent.get("id"), conv_id, agent.get("metadata"))
    audit("session_created", request, agent_id=agent.get("id"), conversation_id=conv_id)
    return {"agent_id": agent.get("id"), "conversation_id": conv_id}


@app.get("/api/letta/history")
async def history(
    request: Request,
    limit: int = 20,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    """Recent conversation for cloud-history reload. Read-only."""
    require_owner(x_owner_token, request)
    rate_limit(client_key(request, x_owner_token), request)
    agent = await resolve_agent()
    agent_id = agent.get("id")
    conversation_id = await resolve_conversation(agent)
    limit = max(1, min(limit, 100))

    try:
        data = await letta(
            "GET",
            f"/v1/agents/{agent_id}/messages",
            params={"limit": limit, "conversation_id": conversation_id},
        )
    except LettaError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "letta_history_failed", "status": exc.status, "detail": exc.detail},
        ) from exc

    items = data if isinstance(data, list) else (data.get("messages") or [])
    out = []
    for msg in items:
        mtype = msg.get("message_type")
        if mtype in ("user_message", "assistant_message"):
            out.append(
                {
                    "role": "user" if mtype == "user_message" else "assistant",
                    "content": msg.get("content"),
                    "date": msg.get("date"),
                }
            )
    return {"agent_id": agent_id, "conversation_id": conversation_id, "messages": out}


# --------------------------------------------------------------------------- #
# Optional: serve the front end from this same service
# --------------------------------------------------------------------------- #
# Off unless ODDFELLOW_FRONTEND_DIR names an existing directory. When it is on,
# one deploy serves both the page and the API, which removes CORS entirely
# (same origin) and halves what has to be deployed and kept in sync.
#
# Mounted LAST and at "/" so it can never shadow an /api route, and it never
# touches /healthz: a static mount must not be able to make the health check
# unreachable.

FRONTEND_DIR = os.environ.get("ODDFELLOW_FRONTEND_DIR", "").strip()

if FRONTEND_DIR and os.path.isdir(FRONTEND_DIR):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
