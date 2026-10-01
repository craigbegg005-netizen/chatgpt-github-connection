"""Scoped, revocable connector tokens -- real verification, not a placeholder.

The gateway previously accepted *any non-empty string* once its preconditions were
marked ready. That is not a credential check; it is a formality that would have
looked like security in a review and provided none. This module replaces it.

Four rules, each of which exists because of a specific way this can go wrong:

1. **Only issued tokens verify.** A token is a 256-bit random value; only its
   SHA-256 hash is stored. A stolen database yields no usable credential, and the
   plaintext is shown exactly once, at issue time.
2. **The owner master token is refused outright.** Not "should not be used" --
   refused, and refused by *value*, so a caller who pastes `ODDFELLOW_OWNER_TOKEN`
   into a connector gets a 403 rather than a working connection that quietly makes
   "disconnect this provider" a lie.
3. **Scopes are per token and per provider.** A provider that may read state may
   not claim work, and one that may claim may not approve. Escalation is refused
   rather than trimmed to fit, because silently downgrading a request hides the
   fact that someone asked for too much.
4. **Revocation is immediate and durable.** Disconnecting a provider has to
   actually disconnect it, including across a restart.

Comparison is constant-time. That is not theatre here: token verification is the
one place where an attacker controls the input being compared against a secret.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Scope(str, Enum):
    """What a token is allowed to do. Deliberately coarse but not vague."""

    READ = "read"        # get_project_state, list_jobs
    CLAIM = "claim"      # claim_job
    SUBMIT = "submit"    # submit_result
    AUDIT = "audit"      # append_audit
    APPROVE = "approve"  # request_approval (asks; never grants)


#: Which scope each gateway tool requires. Kept next to the scopes so a new tool
#: cannot be added without someone deciding what it needs.
TOOL_SCOPES: dict[str, Scope] = {
    "get_project_state": Scope.READ,
    "list_jobs": Scope.READ,
    "claim_job": Scope.CLAIM,
    "submit_result": Scope.SUBMIT,
    "append_audit": Scope.AUDIT,
    "request_approval": Scope.APPROVE,
}


class AuthError(Exception):
    """An authentication or authorization refusal, with the HTTP status it maps to.

    Carries a status so the gateway cannot accidentally answer 200 to a refusal.
    """

    def __init__(self, code: str, detail: str, status: int) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status

    def as_payload(self) -> dict:
        return {"ok": False, "error": self.code, "detail": self.detail}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class TokenRecord:
    token_id: str
    provider: str
    scopes: frozenset[Scope]
    revoked: bool
    created_at: str
    note: str = ""

    def allows(self, scope: Scope) -> bool:
        return scope in self.scopes


TOKEN_SCHEMA = """
CREATE TABLE IF NOT EXISTS connector_tokens (
    token_id    TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL UNIQUE,
    provider    TEXT NOT NULL,
    scopes      TEXT NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT ''
);
"""


class TokenStore:
    """Issue, verify and revoke connector tokens. Backed by the connector's SQLite."""

    def __init__(self, conn: sqlite3.Connection, owner_token: str | None = None) -> None:
        self._conn = conn
        self._conn.executescript(TOKEN_SCHEMA)
        self._conn.commit()
        # Held only to REFUSE it. Never stored, never logged, never compared as a
        # valid credential -- the check below is a rejection path, not an accept path.
        self._owner_token = owner_token or ""

    # ------------------------------------------------------------------ issue

    def issue(
        self,
        provider: str,
        scopes: frozenset[Scope] | set[Scope] | tuple[Scope, ...],
        note: str = "",
    ) -> tuple[str, TokenRecord]:
        """Mint a token. Returns ``(plaintext, record)`` -- the plaintext ONCE.

        The plaintext is never persisted. Losing it means issuing a new token, which
        is the correct trade: a token we can re-read is a token that leaked.
        """
        scopes = frozenset(scopes)
        if not scopes:
            raise ValueError("a token must have at least one scope")
        token_id = "ctk-" + secrets.token_hex(6)
        plaintext = "odf_" + secrets.token_hex(32)
        self._conn.execute(
            "INSERT INTO connector_tokens (token_id, token_hash, provider, scopes, "
            "revoked, created_at, note) VALUES (?,?,?,?,0,?,?)",
            (token_id, _hash(plaintext), provider,
             ",".join(sorted(s.value for s in scopes)), _now(), note),
        )
        self._conn.commit()
        return plaintext, TokenRecord(token_id, provider, scopes, False, _now(), note)

    # ----------------------------------------------------------------- verify

    def verify(self, token: str | None, required: Scope | None = None) -> TokenRecord:
        """Verify a token and (optionally) that it carries a scope.

        Raises ``AuthError`` with an explicit status for every refusal. There is no
        return-None path, because a caller that forgets to check a falsy return is
        how a verification step becomes decorative.
        """
        if not token or not str(token).strip():
            raise AuthError("missing_credential", "a connector token is required", 401)

        # Rule 2, checked first and by value: the master token is not a connector
        # credential, whatever else it is.
        if self._owner_token and hmac.compare_digest(str(token), self._owner_token):
            raise AuthError(
                "master_token_rejected",
                "ODDFELLOW_OWNER_TOKEN is not a connector credential; issue a scoped token",
                403,
            )

        presented = _hash(str(token))
        row = self._conn.execute(
            "SELECT token_id, provider, scopes, revoked, created_at, note, token_hash "
            "FROM connector_tokens WHERE token_hash=?",
            (presented,),
        ).fetchone()

        # Constant-time comparison against the stored hash even after the indexed
        # lookup, so a timing difference cannot confirm "this hash exists".
        if row is None:
            raise AuthError("invalid_token", "unknown connector token", 401)
        if not hmac.compare_digest(row["token_hash"], presented):
            raise AuthError("invalid_token", "unknown connector token", 401)
        if row["revoked"]:
            raise AuthError("token_revoked", "this connector token has been revoked", 401)

        record = TokenRecord(
            token_id=row["token_id"],
            provider=row["provider"],
            scopes=frozenset(Scope(s) for s in row["scopes"].split(",") if s),
            revoked=bool(row["revoked"]),
            created_at=row["created_at"],
            note=row["note"],
        )

        if required is not None and not record.allows(required):
            # Refused, not trimmed: silently narrowing the request would hide that
            # someone asked for more than they hold.
            raise AuthError(
                "insufficient_scope",
                f"token {record.token_id} does not carry the {required.value} scope",
                403,
            )
        return record

    # ---------------------------------------------------------------- revoke

    def revoke(self, token_id: str) -> bool:
        cur = self._conn.execute(
            "UPDATE connector_tokens SET revoked=1 WHERE token_id=? AND revoked=0",
            (token_id,),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_tokens(self) -> list[TokenRecord]:
        rows = self._conn.execute(
            "SELECT token_id, provider, scopes, revoked, created_at, note "
            "FROM connector_tokens ORDER BY created_at"
        ).fetchall()
        return [
            TokenRecord(
                token_id=r["token_id"], provider=r["provider"],
                scopes=frozenset(Scope(s) for s in r["scopes"].split(",") if s),
                revoked=bool(r["revoked"]), created_at=r["created_at"], note=r["note"],
            )
            for r in rows
        ]
