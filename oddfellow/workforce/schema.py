"""Core vocabulary for the Begg Synthetic Intelligence System.

This module defines what a synthetic department, worker and authority level *are*.
It deliberately reuses `Risk` and `Status` from `connector.schema` rather than
inventing a second vocabulary for the same concepts -- two risk scales in one
system is how "high" comes to mean different things in different places, and the
approval gate is exactly where that would matter.

Terminology is engineering terminology. A "department head" here is a durable
identity plus a set of permissions, not a person, and nothing in this system is
conscious or sentient. That is not a disclaimer bolted on at the end: the whole
design depends on it, because a system that claimed judgement would be trusted
where it should be checked.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable

from connector.schema import Risk


class Authority(str, Enum):
    """What a synthetic identity is permitted to *do*, ordered weakest first.

    The levels exist so that "may this act?" is a lookup rather than a judgement
    call made fresh each time. A system that decides per-task whether an action
    is acceptable will eventually decide yes for the wrong reason.
    """

    A0_OBSERVE = "A0"      # read-only
    A1_DRAFT = "A1"        # may produce proposals, drafts, code, research
    A2_INTERNAL = "A2"     # approved zero-cost reversible *internal* changes
    A3_EXTERNAL = "A3"     # specifically allowed external reversible actions
    A4_CONSEQUENTIAL = "A4"  # requires owner authorization


#: Ordered weakest-to-strongest, for comparisons. An explicit list rather than
#: relying on enum declaration order, so reordering the enum cannot silently
#: change what is permitted.
_AUTHORITY_ORDER = (
    Authority.A0_OBSERVE,
    Authority.A1_DRAFT,
    Authority.A2_INTERNAL,
    Authority.A3_EXTERNAL,
    Authority.A4_CONSEQUENTIAL,
)

#: Authority levels that may never be exercised without a live owner approval,
#: regardless of who holds them. This is the organisational mirror of
#: `connector.schema.APPROVAL_REQUIRED`: that gates a *job*, this gates an
#: *identity*, and both have to hold.
OWNER_APPROVAL_REQUIRED = frozenset({Authority.A4_CONSEQUENTIAL})


def authority_rank(level: Authority) -> int:
    return _AUTHORITY_ORDER.index(level)


def allows(held: Authority, required: Authority) -> bool:
    """True when `held` is at least `required`."""
    return authority_rank(held) >= authority_rank(required)


class Role(str, Enum):
    """Coarse worker roles. Deliberately few -- a role taxonomy that grows with
    every task stops being a taxonomy and becomes a list of task names."""

    HEAD = "head"
    MANAGER = "manager"
    WORKER = "worker"
    VERIFIER = "verifier"


_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")


def valid_id(value: str) -> bool:
    """IDs are lowercase, stable, and safe to use as keys and in URLs."""
    return isinstance(value, str) and bool(_ID_RE.match(value))


@dataclass(frozen=True)
class Capability:
    """A named thing an identity can do, paired with the authority it needs.

    Capability and authority are separate on purpose. "Can write code" is a
    capability; "may commit to the canonical branch" is an authority. Collapsing
    them is how a research worker ends up able to deploy.
    """

    name: str
    required_authority: Authority
    description: str = ""

    def __post_init__(self) -> None:
        if not valid_id(self.name):
            raise ValueError(f"invalid capability name: {self.name!r}")


@dataclass
class DepartmentHead:
    """A durable organisational identity for one department.

    Note what is *absent*: a model, a provider, an endpoint. An identity that is
    synonymous with one model cannot survive a provider change, and provider
    routing is a stated requirement of this system.
    """

    department_id: str
    name: str
    title: str
    mission: str
    authority: Authority = Authority.A1_DRAFT
    risk_ceiling: Risk = Risk.MEDIUM
    spend_ceiling_usd: float = 0.0
    capabilities: tuple[Capability, ...] = ()
    permitted_tools: frozenset[str] = field(default_factory=frozenset)
    permitted_providers: frozenset[str] = field(default_factory=frozenset)
    escalation_rules: tuple[str, ...] = ()
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        if not valid_id(self.department_id):
            raise ValueError(f"invalid department_id: {self.department_id!r}")
        if self.spend_ceiling_usd < 0:
            raise ValueError("spend ceiling cannot be negative")
        if self.spend_ceiling_usd > 0 and not allows(
            self.authority, Authority.A4_CONSEQUENTIAL
        ):
            # A non-zero spend ceiling without the authority to spend is a
            # contradiction. Refused at construction rather than discovered at
            # the moment money is about to move.
            raise ValueError(
                f"{self.department_id}: spend ceiling {self.spend_ceiling_usd} "
                "requires A4 authority"
            )

    @property
    def capability_names(self) -> frozenset[str]:
        return frozenset(c.name for c in self.capabilities)

    def can(self, capability: str) -> bool:
        return capability in self.capability_names

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["authority"] = self.authority.value
        d["risk_ceiling"] = self.risk_ceiling.value
        d["capabilities"] = [asdict(c) | {"required_authority": c.required_authority.value}
                             for c in self.capabilities]
        d["permitted_tools"] = sorted(self.permitted_tools)
        d["permitted_providers"] = sorted(self.permitted_providers)
        d["escalation_rules"] = list(self.escalation_rules)
        return d


@dataclass
class Worker:
    """A synthetic worker identity. Persistent in state, not in compute.

    The distinction matters for cost: a worker keeps its identity and history
    while no model process is running for it. Spawning a process per identity
    would make the roster expensive, and an expensive roster is a roster nobody
    dares use.
    """

    worker_id: str
    name: str
    department_id: str
    role: Role
    mission: str
    capabilities: tuple[str, ...] = ()
    authority: Authority = Authority.A1_DRAFT
    risk_ceiling: Risk = Risk.LOW
    spend_ceiling_usd: float = 0.0
    permitted_tools: frozenset[str] = field(default_factory=frozenset)
    permitted_providers: frozenset[str] = field(default_factory=frozenset)
    manager_id: str | None = None
    memory_scope: tuple[str, ...] = ("worker",)
    status: str = "IDLE"

    def __post_init__(self) -> None:
        if not valid_id(self.worker_id):
            raise ValueError(f"invalid worker_id: {self.worker_id!r}")
        if self.spend_ceiling_usd < 0:
            raise ValueError("spend ceiling cannot be negative")
        if self.spend_ceiling_usd > 0 and not allows(
            self.authority, Authority.A4_CONSEQUENTIAL
        ):
            raise ValueError(
                f"{self.worker_id}: spend ceiling {self.spend_ceiling_usd} "
                "requires A4 authority"
            )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        d["authority"] = self.authority.value
        d["risk_ceiling"] = self.risk_ceiling.value
        d["capabilities"] = sorted(self.capabilities)
        d["permitted_tools"] = sorted(self.permitted_tools)
        d["permitted_providers"] = sorted(self.permitted_providers)
        d["memory_scope"] = list(self.memory_scope)
        return d


def risk_at_most(actual: Risk, ceiling: Risk) -> bool:
    """True when `actual` is within `ceiling`.

    Uses an explicit order rather than the enum's declaration order, and treats
    an unknown value as *above* any ceiling: an unrecognised risk level must fail
    closed, not fall through as harmless.
    """
    order = (Risk.LOW, Risk.MEDIUM, Risk.HIGH, Risk.CRITICAL)
    try:
        return order.index(actual) <= order.index(ceiling)
    except ValueError:
        return False


def dedupe(items: Iterable[str]) -> tuple[str, ...]:
    """Stable, order-preserving dedupe -- used for capability lists."""
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)
