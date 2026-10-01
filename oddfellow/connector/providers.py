"""Provider capability registry -- declared vs verified, kept apart.

The single most important property of this module is that it will not let a
*claim* of capability pass as a *capability*. Every provider record separates:

  * what we believe the provider supports (``declared``), sourced from its docs;
  * what we have actually observed (``verified``), which only capability
    detection can set, and which carries the evidence that set it.

Routing reads ``verified``. A provider whose MCP support is only declared is not
routed over MCP, because "the docs say so" is not the same fact as "we reached
it". This is the same distinction the project keeps making elsewhere -- a search
hit is a lead, not a finding -- applied to infrastructure.

Cost is a first-class capability because of the standing zero-spend rule: a paid
provider is not merely expensive, it is *ineligible* unless the owner has
approved spend, so the router must be able to see cost without asking anyone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .schema import TaskKind, Transport


@dataclass
class Capability:
    """One (transport, task-kind) pair a provider may be able to serve."""

    transport: Transport
    kinds: frozenset[TaskKind]
    note: str = ""


@dataclass
class Provider:
    """A provider record.

    ``verified`` is the only field routing trusts. It is written by capability
    detection and by nothing else, and each entry records the evidence string that
    justified it so a later reader can re-check rather than re-trust.
    """

    name: str
    label: str
    #: Declared capabilities, from the provider's own documentation.
    declared: tuple[Capability, ...] = ()
    #: transport -> evidence string. Populated only by detect_*.
    verified: dict[Transport, str] = field(default_factory=dict)
    #: True when using this provider costs money at our volume.
    paid: bool = False
    #: Can the provider be reached without a human present? Claude cannot poll,
    #: so work handed to it waits until the owner opens a chat.
    polling: bool = False
    background_exec: bool = False
    #: How a scoped credential is obtained. NEVER the owner master token.
    auth: str = "none"
    notes: str = ""

    def supports(self, transport: Transport, kind: TaskKind) -> bool:
        """True only when *verified* -- declared support is not enough to route on."""
        if transport not in self.verified:
            return False
        return any(
            c.transport is transport and kind in c.kinds for c in self.declared
        )

    def verified_transports(self) -> tuple[Transport, ...]:
        return tuple(t for t in self.declared if t.transport in self.verified)


#: Evidence string used when nothing has been probed yet. Spelled out rather than
#: left empty so it reads as a fact about our knowledge, not as a blank field.
UNVERIFIED = "not probed in this environment"


def build_registry() -> dict[str, Provider]:
    """The initial provider set.

    Every entry starts with EMPTY ``verified``. Nothing here claims a provider
    works; that is what capability detection is for, and until it runs the router
    will refuse to use these providers rather than assume.
    """
    drafting_code_etc = frozenset(TaskKind)

    return {
        "letta": Provider(
            name="letta",
            label="Letta / Oddfellow",
            declared=(
                Capability(Transport.API, drafting_code_etc, "native"),
                Capability(Transport.MCP, drafting_code_etc, "via MCP gateway"),
            ),
            paid=False,
            polling=True,
            background_exec=True,
            auth="ODDFELLOW_OWNER_TOKEN (owner) or scoped connector token",
            notes="Oddfellow itself. The canonical state owner, not merely a worker.",
        ),
        "openai": Provider(
            name="openai",
            label="OpenAI / ChatGPT",
            declared=(
                Capability(Transport.MCP, drafting_code_etc, "remote MCP where offered"),
                Capability(Transport.API, drafting_code_etc, "official API"),
            ),
            paid=True,
            polling=False,
            background_exec=False,
            auth="scoped connector token or OAuth; API key only if spend approved",
            notes="Tier 2 (API) is disabled unless the owner approves spend.",
        ),
        "anthropic": Provider(
            name="anthropic",
            label="Anthropic / Claude",
            declared=(
                Capability(
                    Transport.MCP,
                    drafting_code_etc,
                    "remote MCP connector (Streamable HTTP)",
                ),
                Capability(Transport.API, drafting_code_etc, "official API"),
                Capability(Transport.HANDOFF, drafting_code_etc, "structured handoff"),
                Capability(Transport.QUEUE, drafting_code_etc, "durable queued handoff"),
            ),
            paid=True,
            polling=False,
            background_exec=False,
            auth="separate scoped revocable connector token -- never the owner token",
            notes=(
                "Claude cannot poll, so queued jobs sit at WAITING_DEPENDENCY until "
                "the owner opens a chat. API tier is paid and disabled by default."
            ),
        ),
        "google": Provider(
            name="google",
            label="Google / Gemini",
            declared=(
                Capability(Transport.API, drafting_code_etc, "official API"),
            ),
            paid=True,
            polling=False,
            background_exec=False,
            auth="scoped credential; API key only if spend approved",
            notes="No verified MCP path recorded.",
        ),
        "xai": Provider(
            name="xai",
            label="xAI / Grok",
            declared=(
                Capability(Transport.API, drafting_code_etc, "official API"),
            ),
            paid=True,
            polling=False,
            background_exec=False,
            auth="scoped credential; API key only if spend approved",
            notes="No verified MCP path recorded.",
        ),
    }


def detect_http_liveness(
    provider: Provider,
    transport: Transport,
    probe: Callable[[], tuple[bool, str]],
) -> None:
    """Record a verified capability from an actual probe.

    ``probe`` must return ``(ok, evidence)`` where evidence describes *what was
    observed* -- a status code, a latency, a specific error. The evidence string
    is stored verbatim and is the only justification a capability has.

    A failed probe records nothing. Silence is not evidence of absence, but it is
    also not evidence of presence, and this function refuses to guess between the
    two -- an earlier version of this project lost 20 hours to exactly that
    confusion.
    """
    ok, evidence = probe()
    if ok:
        provider.verified[transport] = evidence


def unverified_providers(registry: Iterable[Provider]) -> list[str]:
    """Providers with nothing verified at all. Surfaced, not hidden."""
    return [p.name for p in registry if not p.verified]
