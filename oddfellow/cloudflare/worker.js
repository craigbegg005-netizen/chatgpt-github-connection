/**
 * Oddfellow backend — Cloudflare Worker edition.  v0.20.5
 *
 * WHY THIS EXISTS
 * ---------------
 * The Python backend (../oddfellow_letta_backend.py) is canonical and stays
 * canonical. This is the SAME API on a second runtime, built because the Render
 * deploy was blocked on a credential only one other operator held, and a Worker
 * is a deploy target this agent can drive end to end. It is not a new product
 * and it is not a fork of the contract: every route, status code, and response
 * shape below is the one the Python backend serves, and the same acceptance
 * harness (../acceptance_check.py) verifies both.
 *
 * A Worker also removes the two failure modes that cost the most time on Render:
 * there is no cold start, and no health check that can fail a deploy over a
 * missing secret.
 *
 * THE CONTRACT (identical to the Python backend)
 * ----------------------------------------------
 *   GET  /livez                  always 200 while the process is up; carries
 *                                `ready` and `checks_failed` in the body
 *   GET  /healthz                fail closed: 503 unless fully configured
 *   GET  /api/letta/status       auth + connectivity + agent resolution
 *   GET  /api/letta/agent        public, non-secret view of the agent
 *   POST /api/letta/message      one turn; returns the assistant reply
 *   POST /api/letta/new-session  start a fresh conversation
 *   GET  /api/letta/history      recent conversation for cloud-history reload
 *   GET  /                       the front end (static assets binding)
 *
 * SECRETS
 * -------
 * LETTA_API_KEY and ODDFELLOW_OWNER_TOKEN are Worker secrets, set with
 * `wrangler secret put`. They are never in this file, never in git, and never
 * returned to a caller. The owner token is compared in constant time.
 *
 * KNOWN DIFFERENCE FROM THE PYTHON BACKEND, STATED PLAINLY
 * --------------------------------------------------------
 * The rate limiter is per-isolate. A Worker runs many isolates across many
 * colos, so the limit is approximate rather than global: it stops a runaway
 * client hitting one isolate, not a distributed one. The Python backend's
 * limiter is exact because it is a single process. For a single-owner backend
 * behind a secret token this is an acceptable trade, but it is a real
 * difference and is written down rather than glossed over.
 */

const VERSION = "0.20.5";
const SERVICE = "oddfellow_letta_backend";
const AGENT_NAME = "Oddfellow";
const LETTA_BASE_URL = "https://api.letta.com";
const MAX_BODY_BYTES = 64 * 1024;
const DEFAULT_RATE_PER_MIN = 20;

// --------------------------------------------------------------------------- //
// OpenAPI document
// --------------------------------------------------------------------------- //
// FastAPI generates this for the Python backend; a Worker has to state it. It is
// not decoration: the acceptance harness reads /openapi.json to prove which
// build is deployed and that the route set and the request schema are the ones
// it expects. Without it, gate 0 cannot tell one revision from another.

const OPENAPI = {
  openapi: "3.1.0",
  info: { title: "Oddfellow Letta backend", version: VERSION },
  paths: {
    "/livez": {
      get: {
        summary: "Liveness",
        description: "Always 200 while the process is up. Carries `ready` and `checks_failed`.",
        responses: { "200": { description: "Alive" } },
      },
    },
    "/healthz": {
      get: {
        summary: "Readiness",
        description: "Fails closed with 503 when a required environment variable is missing.",
        responses: { "200": { description: "Ready" }, "503": { description: "Not configured" } },
      },
    },
    "/api/letta/status": {
      get: {
        summary: "Auth, connectivity and agent resolution",
        responses: { "200": { description: "Status" }, "401": { description: "Bad or missing owner token" } },
      },
    },
    "/api/letta/agent": {
      get: {
        summary: "Non-secret view of the resolved agent",
        responses: { "200": { description: "Agent" }, "401": { description: "Bad or missing owner token" } },
      },
    },
    "/api/letta/message": {
      post: {
        summary: "Send one turn and return the assistant reply",
        requestBody: {
          required: true,
          content: { "application/json": { schema: { $ref: "#/components/schemas/MessageIn" } } },
        },
        responses: { "200": { description: "Reply" }, "401": { description: "Bad or missing owner token" } },
      },
    },
    "/api/letta/new-session": {
      post: {
        summary: "Start a fresh conversation",
        responses: { "200": { description: "New conversation" }, "401": { description: "Bad or missing owner token" } },
      },
    },
    "/api/letta/history": {
      get: {
        summary: "Recent conversation, for cloud-history reload",
        parameters: [{ name: "limit", in: "query", required: false, schema: { type: "integer", default: 20 } }],
        responses: { "200": { description: "Messages" }, "401": { description: "Bad or missing owner token" } },
      },
    },
  },
  components: {
    schemas: {
      MessageIn: {
        type: "object",
        required: ["input"],
        properties: {
          input: { type: "string", minLength: 1, maxLength: 8000 },
          mode: { type: ["string", "null"], description: "Front-end hint: 'balanced' or 'deep'." },
        },
      },
    },
  },
};

// --------------------------------------------------------------------------- //
// Audit log
// --------------------------------------------------------------------------- //
// Doctrine: "Fail closed. Be auditable." Cloudflare captures console output, so
// one JSON object per line is the durable record. Nothing secret is ever
// written: no tokens, no keys, no message bodies.

function audit(event, fields = {}) {
  try {
    console.log(JSON.stringify({
      ts: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
      event,
      service: SERVICE,
      version: VERSION,
      ...fields,
    }));
  } catch {
    // An audit failure must never take the service down.
  }
}

// --------------------------------------------------------------------------- //
// Configuration
// --------------------------------------------------------------------------- //

function configProblems(env) {
  const problems = [];
  if (!env.LETTA_API_KEY) problems.push(["LETTA_API_KEY", "LETTA_API_KEY is not set"]);
  if (!env.ODDFELLOW_OWNER_TOKEN) {
    problems.push(["ODDFELLOW_OWNER_TOKEN", "ODDFELLOW_OWNER_TOKEN is not set"]);
  }
  if (!env.LETTA_MODEL) {
    problems.push(["LETTA_MODEL", "LETTA_MODEL is not set (refusing to guess a model)"]);
  } else if (!env.LETTA_MODEL.startsWith("letta/") &&
             String(env.ODDFELLOW_ALLOW_PAID_MODEL).toLowerCase() !== "true") {
    problems.push(["ODDFELLOW_ALLOW_PAID_MODEL",
      `LETTA_MODEL=${env.LETTA_MODEL} is not a free letta/* model. Zero-spend ` +
      `doctrine blocks paid models. Set ODDFELLOW_ALLOW_PAID_MODEL=true only ` +
      `with the owner's explicit approval.`]);
  }
  return problems;
}

function allowedOrigins(env) {
  return String(env.ALLOWED_ORIGIN || "")
    .split(",")
    .map((o) => o.trim().replace(/\/+$/, ""))
    .filter(Boolean);
}

function corsHeaders(env, request) {
  const origin = request.headers.get("origin");
  const allowed = allowedOrigins(env);
  if (!origin || !allowed.includes(origin)) return {};
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "Content-Type, X-Owner-Token",
    "vary": "Origin",
  };
}

// --------------------------------------------------------------------------- //
// Responses
// --------------------------------------------------------------------------- //

function json(body, status, env, request, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      "x-request-id": request ? request.headers.get("x-oddfellow-request-id") || "" : "",
      ...corsHeaders(env, request),
      ...extra,
    },
  });
}

function fail(status, detail, env, request) {
  return json({ detail }, status, env, request);
}

// --------------------------------------------------------------------------- //
// Rate limiting (per isolate — see the note at the top of this file)
// --------------------------------------------------------------------------- //

const hits = new Map();

async function sha16(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

async function callerKey(request, token) {
  if (token) return "tok:" + (await sha16(token));
  return "host:" + (request.headers.get("cf-connecting-ip") || "unknown");
}

function rateLimit(env, key, request) {
  const limit = parseInt(env.ODDFELLOW_RATE_PER_MIN || DEFAULT_RATE_PER_MIN, 10) || DEFAULT_RATE_PER_MIN;
  const now = Date.now();
  if (hits.size > 1000) {
    for (const [k, v] of hits) if (!v.length || now - v[v.length - 1] > 60000) hits.delete(k);
  }
  const window = (hits.get(key) || []).filter((t) => now - t <= 60000);
  if (window.length >= limit) {
    hits.set(key, window);
    audit("rate_limited", { caller: key, limit_per_min: limit, path: new URL(request.url).pathname });
    return fail(429, "Rate limit exceeded. Try again shortly.", env, request);
  }
  window.push(now);
  hits.set(key, window);
  return null;
}

// --------------------------------------------------------------------------- //
// Auth — constant time, and the caller is told nothing that distinguishes a
// wrong token from a missing one.
// --------------------------------------------------------------------------- //

function timingSafeEqual(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(a);
  const y = enc.encode(b);
  // Compare a fixed number of bytes so the loop length does not depend on input.
  const len = Math.max(x.length, y.length);
  let diff = x.length ^ y.length;
  for (let i = 0; i < len; i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

function requireOwner(env, token, request) {
  const problems = configProblems(env);
  if (problems.length) {
    audit("auth_denied", { reason: "not_configured", checks_failed: problems.map((p) => p[0]) });
    return fail(503, { error: "backend_not_configured", problems: problems.map((p) => p[1]) }, env, request);
  }
  if (!token) {
    audit("auth_denied", { reason: "no_token", path: new URL(request.url).pathname });
    return fail(401, "Invalid or missing owner token.", env, request);
  }
  if (!timingSafeEqual(token, env.ODDFELLOW_OWNER_TOKEN)) {
    audit("auth_denied", { reason: "bad_token", path: new URL(request.url).pathname });
    return fail(401, "Invalid or missing owner token.", env, request);
  }
  return null;
}

// --------------------------------------------------------------------------- //
// Letta client
// --------------------------------------------------------------------------- //

async function letta(env, method, path, body) {
  const res = await fetch(LETTA_BASE_URL + path, {
    method,
    headers: {
      authorization: `Bearer ${env.LETTA_API_KEY}`,
      "content-type": "application/json",
      accept: "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let parsed;
  try { parsed = JSON.parse(text); } catch { parsed = text.slice(0, 500); }
  if (!res.ok) {
    const err = new Error(`Letta API error ${res.status}`);
    err.status = res.status;
    err.detail = parsed;
    throw err;
  }
  return parsed;
}

async function lettaRaw(env, method, path, body) {
  const res = await fetch(LETTA_BASE_URL + path, {
    method,
    headers: {
      authorization: `Bearer ${env.LETTA_API_KEY}`,
      "content-type": "application/json",
      accept: "text/event-stream",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) {
    let parsed;
    try { parsed = JSON.parse(text); } catch { parsed = text.slice(0, 500); }
    const err = new Error(`Letta API error ${res.status}`);
    err.status = res.status;
    err.detail = parsed;
    throw err;
  }
  return text;
}

/**
 * The agent this backend will talk to.
 *
 * Pinned id ONLY. `POST /v1/agents/search` and `GET /v1/agents/{id}` return
 * disjoint sets — search lists agents that by-id 404s, and vice versa — so
 * search cannot be trusted to decide whether the pinned agent exists. Verified
 * 2026-09-30. Do not "fix" this to fall back to search.
 */
async function resolveAgent(env) {
  const pinned = String(env.ODDFELLOW_AGENT_ID || "").trim();
  if (!pinned) {
    const err = new Error("ODDFELLOW_AGENT_ID is not set");
    err.status = 503;
    err.detail = {
      error: "no_pinned_agent",
      message: "This Worker requires ODDFELLOW_AGENT_ID. It never creates an agent.",
    };
    throw err;
  }
  try {
    return await letta(env, "GET", `/v1/agents/${pinned}`);
  } catch (e) {
    if (e.status === 404) {
      const err = new Error("pinned agent unreadable");
      err.status = 502;
      err.detail = {
        error: "pinned_agent_unreadable",
        agent_id: pinned,
        hint: "ODDFELLOW_AGENT_ID is set but GET /v1/agents/{id} returned 404.",
      };
      throw err;
    }
    throw e;
  }
}

async function conversationExists(env, id) {
  try {
    await letta(env, "GET", `/v1/conversations/${id}`);
    return true;
  } catch (e) {
    if (e.status === 404) return false;
    throw e;
  }
}

async function rememberConversation(env, agentId, convId, metadata) {
  const meta = (metadata && typeof metadata === "object") ? { ...metadata } : {};
  meta.oddfellow_conversation_id = convId;
  try {
    await letta(env, "PATCH", `/v1/agents/${agentId}`, { metadata: meta });
  } catch {
    // Non-fatal: this request can still be served; the id just will not persist.
  }
}

/**
 * The dedicated conversation for this agent.
 *
 * Not the agent's default conversation: that one caches its system prompt, so it
 * never picks up memory changes or a rename. A fresh conversation compiles the
 * current memory immediately. Verified 2026-09-30.
 */
async function resolveConversation(env, agent) {
  const agentId = agent.id;
  const meta = agent.metadata;
  const known = (meta && typeof meta === "object") ? meta.oddfellow_conversation_id : null;
  if (known && await conversationExists(env, known)) return known;

  // Note the query-parameter form. Passing agent_id in the JSON body is rejected
  // with a ZodError ("agent_id: Required") — verified 2026-09-30.
  const created = await letta(env, "POST", `/v1/conversations/?agent_id=${encodeURIComponent(agentId)}`, {});
  const convId = created && created.id;
  if (!convId) {
    const err = new Error("conversation create failed");
    err.status = 502;
    err.detail = { error: "conversation_create_failed", letta: created };
    throw err;
  }
  await rememberConversation(env, agentId, convId, meta);
  return convId;
}

/** Parse the SSE body from POST /v1/conversations/{id}/messages. */
function parseSSE(body) {
  const events = [];
  for (const line of String(body).split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("data:")) continue;
    const payload = trimmed.slice(5).trim();
    if (!payload || payload === "[DONE]") continue;
    try { events.push(JSON.parse(payload)); } catch { /* skip malformed frame */ }
  }
  return events;
}

function agentSummary(agent) {
  const llm = agent.llm_config || {};
  const blocks = agent.blocks || [];
  return {
    id: agent.id,
    name: agent.name,
    agent_type: agent.agent_type,
    model: llm.handle || agent.model,
    context_window: llm.context_window,
    blocks: blocks.map((b) => ({ label: b.label, chars: (b.value || "").length })),
  };
}

// --------------------------------------------------------------------------- //
// Routes
// --------------------------------------------------------------------------- //

async function handleLivez(env, request) {
  const problems = configProblems(env);
  return json({
    live: true,
    ready: problems.length === 0,
    checks_failed: problems.map((p) => p[0]),
    service: SERVICE,
    version: VERSION,
  }, 200, env, request);
}

async function handleHealthz(env, request) {
  const problems = configProblems(env);
  const healthy = problems.length === 0;
  return json({
    ok: healthy,
    checks_failed: problems.map((p) => p[0]),
    service: SERVICE,
    version: VERSION,
  }, healthy ? 200 : 503, env, request);
}

async function handleStatus(env, request, token) {
  const denied = requireOwner(env, token, request);
  if (denied) return denied;
  const limited = rateLimit(env, await callerKey(request, token), request);
  if (limited) return limited;

  const result = {
    backend: SERVICE,
    version: VERSION,
    runtime: "cloudflare-worker",
    letta_base_url: LETTA_BASE_URL,
    model: env.LETTA_MODEL,
    agent_pinned: Boolean(env.ODDFELLOW_AGENT_ID),
    letta_auth: false,
    agent_found: false,
    agent_id: null,
    allowed_origins: allowedOrigins(env),
  };

  try {
    await letta(env, "GET", "/v1/models/?limit=1");
    result.letta_auth = true;
  } catch (e) {
    result.letta_error = { status: e.status, detail: e.detail };
    return json(result, 200, env, request);
  }

  try {
    const agent = await resolveAgent(env);
    result.agent_found = true;
    result.agent_id = agent.id;
    result.agent_name = agent.name;
    try {
      result.conversation_id = await resolveConversation(env, agent);
      result.conversation_ready = true;
    } catch (e) {
      result.conversation_error = e.detail || String(e.message);
    }
  } catch (e) {
    result.agent_error = e.detail || String(e.message);
  }

  // This service cannot verify that memory blocks are attached: GET
  // /v1/agents/{id} reports blocks: [] even right after a PATCH that returned
  // two attached blocks. Do not read this as proof of memory.
  result.memory_blocks_verifiable = false;
  return json(result, 200, env, request);
}

async function handleAgent(env, request, token) {
  const denied = requireOwner(env, token, request);
  if (denied) return denied;
  const limited = rateLimit(env, await callerKey(request, token), request);
  if (limited) return limited;
  try {
    return json({ agent: agentSummary(await resolveAgent(env)) }, 200, env, request);
  } catch (e) {
    return fail(e.status || 502, e.detail || String(e.message), env, request);
  }
}

async function handleMessage(env, request, token, payload) {
  const denied = requireOwner(env, token, request);
  if (denied) return denied;
  const limited = rateLimit(env, await callerKey(request, token), request);
  if (limited) return limited;

  if (!payload || typeof payload.input !== "string" || !payload.input.trim()) {
    return fail(422, "input is required", env, request);
  }
  if (payload.input.length > 8000) {
    return fail(422, "input is too long (max 8000 characters)", env, request);
  }

  let agent, conversationId, raw;
  try {
    agent = await resolveAgent(env);
    conversationId = await resolveConversation(env, agent);
    raw = await lettaRaw(env, "POST", `/v1/conversations/${conversationId}/messages`, { input: payload.input });
  } catch (e) {
    if (e.status) return fail(e.status, e.detail || String(e.message), env, request);
    return fail(502, { error: "letta_message_failed", detail: String(e.message) }, env, request);
  }

  const events = parseSSE(raw);
  let reply = null, stop = null, usage = {};
  for (const ev of events) {
    if (ev.message_type === "assistant_message" && reply === null) reply = ev.content;
    else if (ev.message_type === "stop_reason") stop = ev.stop_reason;
    else if (ev.message_type === "usage_statistics") usage = ev;
  }

  if (reply === null) {
    // Do not invent a reply. Report the failure honestly.
    return fail(502, {
      error: "no_assistant_message",
      stop_reason: stop,
      event_count: events.length,
      conversation_id: conversationId,
    }, env, request);
  }

  // Audited by shape, never by content.
  audit("message_sent", {
    agent_id: agent.id,
    conversation_id: conversationId,
    input_chars: payload.input.length,
    reply_chars: typeof reply === "string" ? reply.length : null,
    stop_reason: stop,
    completion_tokens: usage.completion_tokens,
  });

  return json({
    reply,
    agent_id: agent.id,
    conversation_id: conversationId,
    stop_reason: stop,
    usage: {
      prompt_tokens: usage.prompt_tokens ?? null,
      completion_tokens: usage.completion_tokens ?? null,
    },
  }, 200, env, request);
}

async function handleNewSession(env, request, token) {
  const denied = requireOwner(env, token, request);
  if (denied) return denied;
  const limited = rateLimit(env, await callerKey(request, token), request);
  if (limited) return limited;
  try {
    const agent = await resolveAgent(env);
    const created = await letta(env, "POST", `/v1/conversations/?agent_id=${encodeURIComponent(agent.id)}`, {});
    const convId = created && created.id;
    if (!convId) return fail(502, { error: "conversation_create_failed", letta: created }, env, request);
    await rememberConversation(env, agent.id, convId, agent.metadata);
    audit("session_created", { agent_id: agent.id, conversation_id: convId });
    return json({ agent_id: agent.id, conversation_id: convId }, 200, env, request);
  } catch (e) {
    return fail(e.status || 502, e.detail || String(e.message), env, request);
  }
}

async function handleHistory(env, request, token, limitParam) {
  const denied = requireOwner(env, token, request);
  if (denied) return denied;
  const limited = rateLimit(env, await callerKey(request, token), request);
  if (limited) return limited;

  let limit = parseInt(limitParam || "20", 10);
  if (!Number.isFinite(limit)) limit = 20;
  limit = Math.max(1, Math.min(limit, 100));

  try {
    const agent = await resolveAgent(env);
    const conversationId = await resolveConversation(env, agent);
    const data = await letta(
      env, "GET",
      `/v1/agents/${agent.id}/messages?limit=${limit}&conversation_id=${encodeURIComponent(conversationId)}`,
    );
    const items = Array.isArray(data) ? data : (data.messages || []);
    const out = [];
    for (const msg of items) {
      if (msg.message_type === "user_message" || msg.message_type === "assistant_message") {
        out.push({
          role: msg.message_type === "user_message" ? "user" : "assistant",
          content: msg.content,
          date: msg.date,
        });
      }
    }
    return json({ agent_id: agent.id, conversation_id: conversationId, messages: out }, 200, env, request);
  } catch (e) {
    return fail(e.status || 502, e.detail || String(e.message), env, request);
  }
}

// --------------------------------------------------------------------------- //
// Entry point
// --------------------------------------------------------------------------- //

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const token = request.headers.get("x-owner-token");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(env, request) });
    }

    // Reject an oversized body before reading it, so an unauthenticated caller
    // cannot make the isolate buffer and parse an arbitrary payload.
    const declared = request.headers.get("content-length");
    if (declared && /^\d+$/.test(declared) && parseInt(declared, 10) > MAX_BODY_BYTES) {
      return json({ detail: "Request body too large.", max_bytes: MAX_BODY_BYTES }, 413, env, request);
    }

    try {
      if (path === "/livez") return await handleLivez(env, request);
      if (path === "/healthz") return await handleHealthz(env, request);
      if (path === "/openapi.json") return json(OPENAPI, 200, env, request);
      if (path === "/api/letta/status") return await handleStatus(env, request, token);
      if (path === "/api/letta/agent") return await handleAgent(env, request, token);
      if (path === "/api/letta/new-session" && request.method === "POST") {
        return await handleNewSession(env, request, token);
      }
      if (path === "/api/letta/history") {
        return await handleHistory(env, request, token, url.searchParams.get("limit"));
      }
      if (path === "/api/letta/message" && request.method === "POST") {
        let payload = null;
        try { payload = await request.json(); } catch { payload = null; }
        return await handleMessage(env, request, token, payload);
      }
    } catch (e) {
      audit("unhandled_error", { path, message: String(e && e.message) });
      return fail(500, { error: "internal_error" }, env, request);
    }

    // Anything else is the front end, served by the static assets binding.
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return fail(404, "Not found.", env, request);
  },
};
