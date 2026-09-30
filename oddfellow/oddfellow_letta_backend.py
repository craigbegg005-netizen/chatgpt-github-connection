"""
Oddfellow Letta backend  --  v0.20.3 (verified build)

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
  ALLOWED_ORIGIN             optional  -- CORS origin, e.g. https://oddfellow-...onrender.com
  LETTA_BASE_URL             optional  -- default https://api.letta.com
  ODDFELLOW_ALLOW_PAID_MODEL optional  -- "true" to permit a non-letta/* model
  ODDFELLOW_RATE_PER_MIN     optional  -- default 20 requests/minute per client

v0.20.3 -- self-diagnosing health check
--------------------------------------
v0.20.2 shipped a /healthz that returned only {"ok": false}. On 2026-09-30 it was
deployed to Render, served the correct v0.20.2 API surface, and still could not
answer a single request -- because LETTA_API_KEY and/or ODDFELLOW_OWNER_TOKEN were
absent from the service environment. From outside, the only signal was
{"ok": false}, which does not distinguish "not configured" from "down".

/healthz now also reports `checks_failed`: the NAMES of the env vars that failed
validation, never their values. Env var names are not secrets, and this turns that
class of fault into a one-look fix.

Deploy (Render, free plan)
--------------------------
  Build:  pip install -r requirements.txt
  Start:  uvicorn oddfellow_letta_backend:app --host 0.0.0.0 --port $PORT
  Health: GET /healthz
"""

from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

LETTA_BASE_URL = os.environ.get("LETTA_BASE_URL", "https://api.letta.com").rstrip("/")
LETTA_API_KEY = os.environ.get("LETTA_API_KEY", "").strip()
ODDFELLOW_OWNER_TOKEN = os.environ.get("ODDFELLOW_OWNER_TOKEN", "").strip()
LETTA_MODEL = os.environ.get("LETTA_MODEL", "").strip()
ODDFELLOW_AGENT_ID = os.environ.get("ODDFELLOW_AGENT_ID", "").strip()
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "").strip()
ALLOW_PAID_MODEL = os.environ.get("ODDFELLOW_ALLOW_PAID_MODEL", "").lower() == "true"
RATE_PER_MIN = int(os.environ.get("ODDFELLOW_RATE_PER_MIN", "20"))

AGENT_NAME = "Oddfellow"
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

app = FastAPI(title="Oddfellow Letta backend", version="0.20.3")

if ALLOWED_ORIGIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Owner-Token"],
    )

# --------------------------------------------------------------------------- #
# Rate limiting (in-process; Render free plan runs a single instance)
# --------------------------------------------------------------------------- #

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limit(client: str) -> None:
    now = time.time()
    window = _hits[client]
    while window and now - window[0] > 60.0:
        window.popleft()
    if len(window) >= RATE_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    window.append(now)


def require_owner(token: Optional[str]) -> None:
    if CONFIG_ERRORS:
        # Fail closed with a clear, non-secret-bearing message.
        raise HTTPException(status_code=503, detail={"error": "backend_not_configured", "problems": CONFIG_ERRORS})
    if not token or not hmac.compare_digest(token, ODDFELLOW_OWNER_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid or missing owner token.")


# --------------------------------------------------------------------------- #
# Letta client
# --------------------------------------------------------------------------- #

class LettaError(RuntimeError):
    def __init__(self, status: int, detail: Any):
        self.status = status
        self.detail = detail
        super().__init__(f"Letta API error {status}: {detail}")


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {LETTA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def letta(method: str, path: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    url = f"{LETTA_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(method, url, headers=_headers(), json=json_body, params=params)
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
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(method, url, headers=_headers(), json=json_body, params=params)
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
        "version": "0.20.3",
    }
    # Fail closed: a service that cannot answer a single request must not report
    # 200 to a platform health check, or the platform will route traffic to it.
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@app.get("/api/letta/status")
async def status(x_owner_token: Optional[str] = Header(default=None)) -> dict:
    """
    Auth + connectivity + agent resolution check.
    This is the endpoint to hit first after a deploy.
    """
    require_owner(x_owner_token)

    result: dict = {
        "backend": "oddfellow_letta_backend",
        "version": "0.20.3",
        "letta_base_url": LETTA_BASE_URL,
        "model": LETTA_MODEL,
        "agent_pinned": bool(ODDFELLOW_AGENT_ID),
        "letta_auth": False,
        "agent_found": False,
        "agent_id": None,
    }

    # 1. Does the key authenticate?
    try:
        await letta("GET", "/v1/models/", params={"limit": 1})
        result["letta_auth"] = True
    except LettaError as exc:
        result["letta_error"] = {"status": exc.status, "detail": exc.detail}
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
async def get_agent(x_owner_token: Optional[str] = Header(default=None)) -> dict:
    require_owner(x_owner_token)
    agent = await resolve_agent()
    return {"agent": agent_summary(agent)}


@app.post("/api/letta/message")
async def send_message(
    payload: MessageIn,
    request: Request,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    require_owner(x_owner_token)
    rate_limit(request.client.host if request.client else "unknown")

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
async def new_session(x_owner_token: Optional[str] = Header(default=None)) -> dict:
    """
    Start a fresh conversation.

    Useful when memory was attached after this conversation was created: the
    old conversation keeps its cached prompt, a new one picks up current memory.
    """
    require_owner(x_owner_token)
    agent = await resolve_agent()
    conv_id = await create_conversation(agent.get("id"))
    await remember_conversation(agent.get("id"), conv_id, agent.get("metadata"))
    return {"agent_id": agent.get("id"), "conversation_id": conv_id}


@app.get("/api/letta/history")
async def history(
    limit: int = 20,
    x_owner_token: Optional[str] = Header(default=None),
) -> dict:
    """Recent conversation for cloud-history reload. Read-only."""
    require_owner(x_owner_token)
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
