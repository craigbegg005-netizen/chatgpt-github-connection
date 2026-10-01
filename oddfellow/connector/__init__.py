"""Oddfellow Universal Connector.

An optional bridge that lets authorised AI providers (OpenAI, Anthropic, Google,
xAI, Letta) collaborate through one canonical project state, without any provider
having to expose its private application memory to another.

The shape of the thing:

    Oddfellow Core
      -> canonical shared state      (store.set_state / get_state)
      -> durable idempotent queue    (store.create_job / claim / submit_result)
      -> audit log without payloads  (store.audit)
      -> approval + emergency stop   (router.route, store.set_paused)
      -> capability registry         (providers.build_registry)
      -> provider routing            (router.route, router.failover_order)
      -> universal MCP gateway       (gateway.Gateway -- scaffolded, disabled)

Two properties are load-bearing and worth stating at the top:

1. **Nothing claims to work that has not been observed.** A provider capability
   is only routable once capability detection has verified it; declared support
   is recorded separately and never routed on.
2. **The connector refuses by default.** High-risk work waits for approval, paid
   providers are ineligible under the zero-spend rule, and the MCP gateway will
   not serve until its preconditions are met.
"""

from .gateway import Gateway, ToolSpec, build_tool_surface
from .providers import (
    Capability,
    Provider,
    UNVERIFIED,
    build_registry,
    detect_http_liveness,
    unverified_providers,
)
from .router import Decision, choose_transport, explain, failover_order, route
from .schema import (
    APPROVAL_REQUIRED,
    TRANSPORT_LADDER,
    Job,
    Risk,
    Status,
    TaskKind,
    Transport,
    canonical_json,
    new_job_id,
    result_hash,
)
from .store import Store
from .store import ClaimRefused, SubmitRefused
from .tokens import TOOL_SCOPES, AuthError, Scope, TokenRecord, TokenStore

__all__ = [
    "APPROVAL_REQUIRED",
    "Capability",
    "Decision",
    "Gateway",
    "Job",
    "Provider",
    "Risk",
    "Status",
    "Store",
    "ClaimRefused",
    "SubmitRefused",
    "TOOL_SCOPES",
    "AuthError",
    "Scope",
    "TokenRecord",
    "TokenStore",
    "TRANSPORT_LADDER",
    "TaskKind",
    "ToolSpec",
    "Transport",
    "UNVERIFIED",
    "build_registry",
    "build_tool_surface",
    "canonical_json",
    "choose_transport",
    "detect_http_liveness",
    "explain",
    "failover_order",
    "new_job_id",
    "result_hash",
    "route",
    "unverified_providers",
]
