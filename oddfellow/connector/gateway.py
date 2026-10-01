"""MCP gateway scaffold -- defined, and deliberately NOT serving.

This module exists so that the tool surface is settled and reviewable *before*
anything is exposed to a network. It answers the connector's remote-MCP rung, and
it refuses to answer anything else until the preconditions in ``PRECONDITIONS``
are met.

Why it is off by default, stated plainly: an MCP endpoint is an authenticated
door into the owner's canonical project state. Turning it on before the auth model
is verified would make the connector itself the weakest link in a system whose
entire purpose is protecting that state. So the scaffold refuses, and names what
is missing, rather than shipping enabled-and-unverified.

Two rules are encoded here rather than left to a caller's discipline:

  * **The owner master token is never an accepted connector credential.** A
    connector token is separate, scoped, revocable, and safe to hand to a provider
    that the owner may later disconnect. Reusing the master token would make
    "disconnect this provider" a lie.
  * **Read-only by default.** Every write-class tool requires an approval gate and
    is refused when one is not configured. A provider that can write without a gate
    can rewrite the shared state that every other AI trusts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .store import Store
from .tokens import TOOL_SCOPES, AuthError, TokenStore


@dataclass
class ToolSpec:
    """A tool exposed over MCP.

    ``mutates`` drives the default-deny behaviour: a mutating tool is refused
    unless the deployment has an approval gate wired up.
    """

    name: str
    description: str
    mutates: bool
    schema: dict
    handler: Callable[..., Any] | None = None


def build_tool_surface() -> list[ToolSpec]:
    """The minimum tool set, per the connective contract.

    Deliberately small. Every additional tool is another way into the state, and
    the point of the connector is a narrow, auditable waist rather than a wide one.
    """
    return [
        ToolSpec(
            "get_project_state",
            "Read canonical project state (optionally a single key).",
            mutates=False,
            schema={
                "type": "object",
                "properties": {"project": {"type": "string"}, "key": {"type": "string"}},
                "required": ["project"],
            },
        ),
        ToolSpec(
            "list_jobs",
            "List jobs, optionally filtered by status.",
            mutates=False,
            schema={
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        ),
        ToolSpec(
            "claim_job",
            "Claim a READY job for this provider. Records the attempt.",
            mutates=True,
            schema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        ),
        ToolSpec(
            "submit_result",
            "Submit a result for a claimed job. Idempotent on content hash.",
            mutates=True,
            schema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}, "result": {}},
                "required": ["job_id", "result"],
            },
        ),
        ToolSpec(
            "append_audit",
            "Append an audit event. Never records payloads or results.",
            mutates=True,
            schema={
                "type": "object",
                "properties": {"event": {"type": "string"}, "job_id": {"type": "string"}},
                "required": ["event"],
            },
        ),
        ToolSpec(
            "request_approval",
            "Ask the owner to approve a gated action. Does not itself approve.",
            mutates=True,
            schema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["job_id", "reason"],
            },
        ),
    ]


#: What must be true before the gateway is allowed to serve. Each entry is a fact
#: to establish, not a task to tick -- the gateway reads this list at runtime and
#: refuses while any entry is unmet.
PRECONDITIONS = (
    "at least one scoped connector token has been issued",
    "token verification is implemented and rejects anything else",
    "host and origin allow-listing is configured",
    "an approval gate is wired for every mutating tool",
    "audit logging is confirmed to strip payloads and results",
)


@dataclass
class Gateway:
    """Refuses to serve unless explicitly enabled *and* fully preconditioned.

    Credential validation is **real**: every call must present a token issued by the
    TokenStore, carrying the scope the tool requires. An earlier version accepted any
    non-empty string once the preconditions were marked ready, which is a formality
    that reads as security in a review and provides none.
    """

    store: Store
    tokens: TokenStore | None = None
    enabled: bool = False
    host_origin_allowlisted: bool = False
    #: Exact hostnames permitted to reach this gateway. Empty means serving is
    #: refused outright rather than permitted-by-default -- an allow-list that
    #: starts empty and permissive is not an allow-list.
    allowed_hosts: tuple[str, ...] = ()
    approval_gate_configured: bool = False
    tools: list[ToolSpec] = field(default_factory=build_tool_surface)

    def unmet_preconditions(self) -> list[str]:
        unmet: list[str] = []
        if not self.enabled:
            unmet.append("gateway is not enabled (set enabled=True deliberately, not by default)")
        if self.tokens is None or not self.tokens.list_tokens():
            unmet.append(PRECONDITIONS[0])
        if not self.host_origin_allowlisted or not self.allowed_hosts:
            unmet.append(PRECONDITIONS[2])
        if not self.approval_gate_configured:
            unmet.append(PRECONDITIONS[3])
        return unmet

    def host_allowed(self, host: str | None) -> bool:
        """Exact-match host check. No wildcards, no suffix matching.

        Suffix matching is how `evil-example.com` passes a naive check for
        `example.com`. The list is short and explicit on purpose.
        """
        if not host:
            return False
        return host.strip().lower() in {h.strip().lower() for h in self.allowed_hosts}

    def may_serve(self) -> bool:
        return not self.unmet_preconditions()

    def refusal(self) -> dict:
        """The payload returned while unready. Names what is missing; claims nothing."""
        return {
            "serving": False,
            "reason": "MCP gateway is not serving",
            "unmet_preconditions": self.unmet_preconditions(),
            "note": (
                "Remote MCP exposure stays disabled until authentication, "
                "authorization and host/origin protections are verified. This is "
                "deliberate, not an oversight."
            ),
        }

    def call(
        self,
        tool_name: str,
        credential: str | None = None,
        host: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Refuse, or dispatch. There is no permissive default.

        Order matters: serving state, then the tool's existence, then the
        host, then the credential, then the scope. A refusal always carries a
        status so a caller cannot mistake it for success.
        """
        if not self.may_serve():
            return self.refusal()
        spec = next((t for t in self.tools if t.name == tool_name), None)
        if spec is None:
            return {"ok": False, "error": "unknown_tool", "detail": f"unknown tool: {tool_name}", "status": 404}
        if not self.host_allowed(host):
            return {
                "ok": False,
                "error": "host_not_allowed",
                "detail": f"host {host!r} is not on the allow-list",
                "status": 403,
            }
        try:
            assert self.tokens is not None  # guaranteed by may_serve()
            self.tokens.verify(credential, TOOL_SCOPES.get(tool_name))
        except AuthError as exc:
            return {**exc.as_payload(), "status": exc.status}
        if spec.mutates and not self.approval_gate_configured:
            return {
                "ok": False,
                "error": "approval_gate_required",
                "detail": f"{tool_name} requires an approval gate",
                "status": 403,
            }
        if spec.handler is None:
            return {
                "ok": False,
                "error": "not_implemented",
                "detail": f"{tool_name} has no handler wired",
                "status": 501,
            }
        return {"ok": True, "result": spec.handler(**kwargs)}
