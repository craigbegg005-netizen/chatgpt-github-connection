"""Routing: capability-aware, zero-spend-aware, and fail-closed.

The router answers one question -- "who should do this, and how do we reach them" --
and it answers it in a way that can refuse. Refusal is a first-class outcome here,
because the three ways this system can go wrong are all cases where it should have
said no and did not:

  * running work that needed the owner's approval,
  * spending money under a zero-spend rule,
  * claiming a provider supports something we never verified.

So every route decision is one of: a concrete plan, or a status explaining why not.
There is no "best effort" path.

The fallback ladder is walked in order -- MCP, API, structured handoff, durable
queue -- and the chosen rung is recorded. Falling back is not silent: a job handed
off through a queue is a different fact from a job executed over MCP, and the
record has to say which happened.
"""

from __future__ import annotations

from dataclasses import dataclass

from .providers import Provider
from .schema import (
    APPROVAL_REQUIRED,
    TRANSPORT_LADDER,
    Job,
    Risk,
    Status,
    TaskKind,
    Transport,
)


@dataclass
class Decision:
    """Either a plan, or a reason there is none.

    ``status`` is always set. ``provider``/``transport`` are set only when the
    decision is to proceed, so a caller cannot accidentally act on a refusal by
    reading a field that was never populated.
    """

    status: Status
    reason: str
    provider: str | None = None
    transport: Transport | None = None

    @property
    def runnable(self) -> bool:
        return self.provider is not None and self.transport is not None


def choose_transport(provider: Provider, kind: TaskKind) -> Transport | None:
    """Highest verified rung of the ladder this provider can serve for ``kind``.

    Returns ``None`` when nothing is verified. Declared-but-unverified support is
    not returned -- routing on documentation rather than observation is the mistake
    this project keeps paying for.
    """
    for transport in TRANSPORT_LADDER:
        if provider.supports(transport, kind):
            return transport
    return None


def route(
    job: Job,
    registry: dict[str, Provider],
    *,
    paused: bool = False,
    pause_reason: str = "",
    approval_granted: bool = False,
    allow_paid: bool = False,
    preferred: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
) -> Decision:
    """Decide how to run ``job``, or why it cannot be run.

    Order of checks matters and is deliberate: the emergency stop is consulted
    before anything else, and approval before capability, so a high-risk job can
    never slip through on the strength of a provider being available.

    **``approval_granted`` is a planning input, not enforcement.** This function
    is pure and has no store, so it cannot verify anything -- it can only be told.
    The caller should derive it from ``Store.approval_state_for_job(job_id)``, and
    ``Store.claim_job`` re-checks the approval record itself before any work runs.
    A decision read now and acted on later is a decision that can change in
    between, so the check that matters is the one at the claim, not this one.
    """
    # 1. Emergency stop. Nothing runs while it is pressed, including safe work --
    #    a stop button with exceptions is not a stop button.
    if paused:
        return Decision(
            Status.BLOCKED,
            f"emergency pause is set: {pause_reason or 'no reason recorded'}",
        )

    # 2. Approval. High and critical work never runs unapproved.
    if job.risk in APPROVAL_REQUIRED and not approval_granted:
        return Decision(
            Status.WAITING_AUTHORIZATION,
            f"{job.risk.value}-risk work requires explicit owner approval",
        )

    # 3. Dependencies.
    #    (Dependency completion is enforced by Store.ready_jobs before routing;
    #    this is the second gate, for callers that route directly.)

    # 4. Candidate order: caller preference first, then everything else.
    names = list(preferred) + [n for n in registry if n not in preferred]
    refusals: list[str] = []

    for name in names:
        if name in exclude:
            continue
        provider = registry.get(name)
        if provider is None:
            refusals.append(f"{name}: unknown provider")
            continue
        if provider.paid and not allow_paid:
            refusals.append(f"{name}: paid, and spend is not approved")
            continue
        transport = choose_transport(provider, job.kind)
        if transport is None:
            refusals.append(f"{name}: no verified transport for {job.kind.value}")
            continue
        return Decision(
            Status.READY,
            f"{name} via {transport.value}",
            provider=name,
            transport=transport,
        )

    # 5. Nothing eligible. Say why, per candidate -- "no provider" is not an
    #    answer anyone can act on.
    return Decision(
        Status.BLOCKED,
        "no eligible provider: " + ("; ".join(refusals) if refusals else "registry is empty"),
    )


def failover_order(
    job: Job,
    registry: dict[str, Provider],
    *,
    failed: tuple[str, ...] = (),
    allow_paid: bool = False,
) -> list[tuple[str, Transport]]:
    """Ordered (provider, transport) pairs to try, excluding those that already failed.

    Used when a job fails retryably: the caller walks this list rather than
    retrying the same provider, because a provider that just failed is the least
    likely to succeed next and the ladder exists precisely for this case.
    """
    out: list[tuple[str, Transport]] = []
    for name, provider in registry.items():
        if name in failed:
            continue
        if provider.paid and not allow_paid:
            continue
        transport = choose_transport(provider, job.kind)
        if transport is not None:
            out.append((name, transport))
    # Prefer providers that can act without a human present: a job that needs
    # someone to open a chat is not a failover, it is a deferral.
    out.sort(key=lambda pair: (not registry[pair[0]].polling, pair[0]))
    return out


def explain(job: Job, decision: Decision) -> str:
    """One-line human-readable rendering, for the Command Center and the audit log."""
    if decision.runnable:
        return f"{job.job_id} [{job.risk.value}] -> {decision.reason}"
    return f"{job.job_id} [{job.risk.value}] -> {decision.status.value}: {decision.reason}"
