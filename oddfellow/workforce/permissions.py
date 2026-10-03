"""Whether a synthetic identity may do a thing, as a lookup rather than a judgement.

Every function here returns a `Decision` carrying the reason it refused. That is
deliberate: "denied" with no reason is indistinguishable from a bug, and an
operator who cannot tell a policy refusal from a malfunction will eventually
work around both.

Nothing in this module consults a model. Permission is data.
"""

from __future__ import annotations

from dataclasses import dataclass

from connector.schema import Risk
from .schema import (
    Authority,
    OWNER_APPROVAL_REQUIRED,
    Worker,
    allows,
    risk_at_most,
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""
    requires_owner_approval: bool = False

    def __bool__(self) -> bool:
        # Truthy only when actually allowed. `if decision:` must not read as
        # permission when the decision was a refusal carrying a reason.
        return self.allowed

    @classmethod
    def yes(cls, reason: str = "") -> "Decision":
        return cls(True, reason)

    @classmethod
    def no(cls, reason: str, *, needs_owner: bool = False) -> "Decision":
        return cls(False, reason, needs_owner)


def check_authority(actor: Worker | object, required: Authority) -> Decision:
    """Whether `actor` holds at least `required` authority.

    A4 always returns a refusal that names owner approval, even when the actor
    holds A4 -- because no synthetic identity is permitted to exercise A4
    unilaterally. Holding the level means the request is *eligible* to be
    approved, not that it is approved.
    """
    held = getattr(actor, "authority", None)
    if held is None:
        return Decision.no("actor has no declared authority")
    if required in OWNER_APPROVAL_REQUIRED:
        return Decision.no(
            f"{required.value} requires explicit owner approval", needs_owner=True
        )
    if not allows(held, required):
        return Decision.no(
            f"holds {held.value}, needs {required.value}"
        )
    return Decision.yes()


def check_risk(actor: Worker | object, risk: Risk) -> Decision:
    """Whether `risk` is within the actor's ceiling."""
    ceiling = getattr(actor, "risk_ceiling", None)
    if ceiling is None:
        return Decision.no("actor has no declared risk ceiling")
    if not risk_at_most(risk, ceiling):
        return Decision.no(f"risk {risk.value} exceeds ceiling {ceiling.value}")
    return Decision.yes()


def check_tool(actor: Worker | object, tool: str) -> Decision:
    """Whether the actor may use a named tool.

    An empty permission set means *no* tools, not all tools. The permissive
    reading is the one that turns a missing configuration into an open door.
    """
    permitted = getattr(actor, "permitted_tools", None)
    if permitted is None:
        return Decision.no("actor has no declared tool permissions")
    if tool not in permitted:
        return Decision.no(f"tool {tool!r} is not permitted for this identity")
    return Decision.yes()


def check_provider(actor: Worker | object, provider: str) -> Decision:
    permitted = getattr(actor, "permitted_providers", None)
    if permitted is None:
        return Decision.no("actor has no declared provider permissions")
    if provider not in permitted:
        return Decision.no(f"provider {provider!r} is not permitted for this identity")
    return Decision.yes()


def check_spend(actor: Worker | object, amount_usd: float) -> Decision:
    """Whether the actor may commit this amount.

    Any amount above zero requires owner approval regardless of the ceiling,
    because the standing rule is zero-spend-first and a ceiling is a limit on
    what *may be approved*, never a standing allowance to spend it.
    """
    if amount_usd < 0:
        return Decision.no("negative amount is not a spend")
    if amount_usd == 0:
        return Decision.yes("zero-cost action")
    ceiling = getattr(actor, "spend_ceiling_usd", 0.0)
    if amount_usd > ceiling:
        return Decision.no(
            f"{amount_usd:.2f} exceeds the {ceiling:.2f} ceiling", needs_owner=True
        )
    return Decision.no(
        "any non-zero spend requires explicit owner approval", needs_owner=True
    )


def check_all(
    actor: Worker | object,
    *,
    authority: Authority | None = None,
    risk: Risk | None = None,
    tool: str | None = None,
    provider: str | None = None,
    spend_usd: float = 0.0,
) -> Decision:
    """Evaluate every supplied constraint. The first refusal wins.

    Returns the *first* refusal rather than collecting all of them: a caller
    acting on "here are five reasons" tends to fix the cheapest one and retry,
    which is a loop. One clear reason is more actionable.
    """
    checks = []
    if authority is not None:
        checks.append(lambda: check_authority(actor, authority))
    if risk is not None:
        checks.append(lambda: check_risk(actor, risk))
    if tool is not None:
        checks.append(lambda: check_tool(actor, tool))
    if provider is not None:
        checks.append(lambda: check_provider(actor, provider))
    if spend_usd:
        checks.append(lambda: check_spend(actor, spend_usd))
    for check in checks:
        d = check()
        if not d.allowed:
            return d
    return Decision.yes()
