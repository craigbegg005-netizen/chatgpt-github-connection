"""Connecting and disconnecting a provider, cleanly.

Disconnecting has to actually disconnect. Three things can go wrong when a
provider is removed, and each has a specific consequence the owner would feel:

  * **Its tokens keep working.** Then "disconnect" is a label, not a change, and
    the provider can still read state and claim work.
  * **Its claimed jobs are stranded.** A job left in RUNNING by a provider that no
    longer exists is unreachable: not lost, but not reachable either, which from
    the owner's side is the same thing.
  * **It is not recorded.** A disconnect with no audit trail cannot be
    reconstructed later, which is the moment someone will want to know exactly
    when and why a provider was removed.

So `disconnect_provider` revokes every token, releases every claim, and writes the
audit entry -- and reports what it did rather than assuming it worked.

`connect_provider` is the mirror: it issues a scoped token and records the intent,
so a connection is a deliberate, auditable act with a named scope rather than an
implicit side effect of someone pasting a credential.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .store import Store
from .tokens import Scope, TokenStore


@dataclass
class DisconnectReport:
    provider: str
    tokens_revoked: list[str] = field(default_factory=list)
    claims_released: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "tokens_revoked": self.tokens_revoked,
            "claims_released": self.claims_released,
            "failures": self.failures,
            "clean": self.clean,
        }


def connect_provider(
    tokens: TokenStore,
    provider: str,
    scopes: set[Scope] | frozenset[Scope],
    note: str = "",
) -> tuple[str, dict]:
    """Issue a scoped token for a provider. Returns ``(plaintext, summary)``.

    The plaintext is returned once and never stored. The summary is what goes in a
    handoff or a log: the token id, the provider, the scopes -- never the value.
    """
    plaintext, record = tokens.issue(provider, scopes, note=note)
    return plaintext, {
        "provider": provider,
        "token_id": record.token_id,
        "scopes": sorted(s.value for s in record.scopes),
        "note": note,
        "warning": "this value is shown once and is not recoverable; store it in the provider, not in a document",
    }


def disconnect_provider(
    store: Store,
    tokens: TokenStore,
    provider: str,
    actor: str,
    reason: str = "",
) -> DisconnectReport:
    """Revoke the provider's tokens and release its claims. Reports what happened.

    Failures are collected rather than raised, so a partial disconnect is visible
    and specific instead of aborting halfway with no record of how far it got.
    """
    report = DisconnectReport(provider=provider)

    # 1. Revoke every unrevoked token belonging to this provider.
    for record in tokens.list_tokens():
        if record.provider != provider or record.revoked:
            continue
        try:
            if tokens.revoke(record.token_id):
                report.tokens_revoked.append(record.token_id)
        except Exception as exc:  # pragma: no cover - defensive
            report.failures.append(f"could not revoke {record.token_id}: {exc}")

    # 2. Release every claim it holds, so the work is reachable again.
    from .schema import Status  # local import keeps the module import-light

    for job in store.jobs(Status.RUNNING):
        if job.provider != provider:
            continue
        try:
            store.release_claim(job.job_id, actor=actor, reason=reason or "provider disconnected")
            report.claims_released.append(job.job_id)
        except Exception as exc:
            report.failures.append(f"could not release {job.job_id}: {exc}")

    # 3. Record it. A disconnect nobody can reconstruct is a disconnect nobody can trust.
    store.audit(
        actor,
        "provider.disconnected",
        provider=provider,
        reason=reason,
        tokens_revoked=report.tokens_revoked,
        claims_released=report.claims_released,
        clean=report.clean,
    )
    return report
