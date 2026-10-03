"""Safe access to the workforce definitions, and round-trippable serialisation.

The registry is the only supported way to ask "does this department exist" and
"what may this worker do". Lookups return `None` rather than raising for an
unknown id, because an unknown id is an ordinary outcome (a stale job, a typo in
a handoff) and an exception invites callers to catch-and-ignore, which is how a
missing identity becomes a silent bypass.

`from_dict` validates on the way in. State that round-trips through JSON is
attacker-adjacent input the moment it is stored anywhere durable, and a
workforce record that loads with an inflated authority ceiling is worse than one
that refuses to load.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from connector.schema import Risk
from .departments import DEPARTMENTS
from .schema import Authority, Role, Worker, authority_rank
from .workers import default_workers


class WorkforceRegistry:
    """An immutable view over departments and workers."""

    def __init__(
        self,
        departments: Iterable[Any] | None = None,
        workers: Iterable[Worker] | None = None,
    ) -> None:
        deps = tuple(DEPARTMENTS if departments is None else departments)
        wrks = tuple(default_workers() if workers is None else workers)

        self._departments = {d.department_id: d for d in deps}
        if len(self._departments) != len(deps):
            raise ValueError("duplicate department_id in registry")

        self._workers = {w.worker_id: w for w in wrks}
        if len(self._workers) != len(wrks):
            raise ValueError("duplicate worker_id in registry")

        # A worker in an unknown department would be unreachable by department
        # routing and therefore invisible to the checks that scope work.
        for w in self._workers.values():
            if w.department_id not in self._departments:
                raise ValueError(
                    f"{w.worker_id} belongs to unknown department {w.department_id!r}"
                )

        # A worker may never hold more authority than its head. This was checked
        # only in `workers.default_workers()`, which validates the *built-in*
        # roster -- so the rule held for the roster that ships and was silently
        # skipped for every roster that arrives any other way, including through
        # `from_dict`/`from_json`. This module's own docstring claimed the
        # opposite ("a workforce record that loads with an inflated authority
        # ceiling is worse than one that refuses to load"), and it was not true:
        # a serialised roster with one worker raised to A4 loaded without
        # complaint. The check belongs here, where every path passes through.
        for w in self._workers.values():
            head = self._departments[w.department_id]
            if authority_rank(w.authority) > authority_rank(head.authority):
                raise ValueError(
                    f"{w.worker_id} holds {w.authority.value} but its head "
                    f"{head.department_id} holds only {head.authority.value}"
                )

    # ------------------------------------------------------------ departments

    def department(self, department_id: str) -> Any | None:
        return self._departments.get(department_id)

    def departments(self) -> tuple[Any, ...]:
        return tuple(self._departments.values())

    def department_ids(self) -> tuple[str, ...]:
        return tuple(self._departments)

    # ---------------------------------------------------------------- workers

    def worker(self, worker_id: str) -> Worker | None:
        return self._workers.get(worker_id)

    def workers(self) -> tuple[Worker, ...]:
        return tuple(self._workers.values())

    def workers_in(self, department_id: str) -> tuple[Worker, ...]:
        return tuple(w for w in self._workers.values() if w.department_id == department_id)

    def verifiers(self) -> tuple[Worker, ...]:
        """Workers whose role is verification.

        Used by `verification.py` to find someone *other than* the producer. An
        empty result means independent verification is impossible, which is a
        condition callers must handle rather than treat as "no verifier needed".
        """
        return tuple(w for w in self._workers.values() if w.role is Role.VERIFIER)

    # ----------------------------------------------------------- serialisation

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "departments": [d.to_dict() for d in self._departments.values()],
            "workers": [w.to_dict() for w in self._workers.values()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkforceRegistry":
        """Rebuild from serialised state, validating every field on the way in."""
        if not isinstance(data, dict):
            raise ValueError("workforce state must be an object")
        version = data.get("version")
        if version != 1:
            raise ValueError(f"unsupported workforce state version: {version!r}")

        from .schema import Capability  # local: only needed on the load path

        departments = []
        for raw in data.get("departments") or []:
            caps = tuple(
                Capability(
                    name=c["name"],
                    required_authority=Authority(c["required_authority"]),
                    description=c.get("description", ""),
                )
                for c in raw.get("capabilities") or []
            )
            departments.append(
                type(DEPARTMENTS[0])(
                    department_id=raw["department_id"],
                    name=raw["name"],
                    title=raw["title"],
                    mission=raw["mission"],
                    authority=Authority(raw["authority"]),
                    risk_ceiling=Risk(raw["risk_ceiling"]),
                    spend_ceiling_usd=float(raw.get("spend_ceiling_usd", 0.0)),
                    capabilities=caps,
                    permitted_tools=frozenset(raw.get("permitted_tools") or []),
                    permitted_providers=frozenset(raw.get("permitted_providers") or []),
                    escalation_rules=tuple(raw.get("escalation_rules") or []),
                    status=raw.get("status", "ACTIVE"),
                )
            )

        workers = []
        for raw in data.get("workers") or []:
            workers.append(
                Worker(
                    worker_id=raw["worker_id"],
                    name=raw["name"],
                    department_id=raw["department_id"],
                    role=Role(raw["role"]),
                    mission=raw["mission"],
                    capabilities=tuple(raw.get("capabilities") or []),
                    authority=Authority(raw["authority"]),
                    risk_ceiling=Risk(raw["risk_ceiling"]),
                    spend_ceiling_usd=float(raw.get("spend_ceiling_usd", 0.0)),
                    permitted_tools=frozenset(raw.get("permitted_tools") or []),
                    permitted_providers=frozenset(raw.get("permitted_providers") or []),
                    manager_id=raw.get("manager_id"),
                    memory_scope=tuple(raw.get("memory_scope") or ("worker",)),
                    status=raw.get("status", "IDLE"),
                )
            )
        return cls(departments=departments, workers=workers)

    @classmethod
    def from_json(cls, text: str) -> "WorkforceRegistry":
        return cls.from_dict(json.loads(text))

    # ----------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        """A compact summary. Counts only -- no inference about what they mean."""
        return {
            "departments": len(self._departments),
            "workers": len(self._workers),
            "verifiers": len(self.verifiers()),
            "departments_without_workers": sorted(
                d for d in self._departments
                if not self.workers_in(d)
            ),
            "max_authority": max(
                (d.authority.value for d in self._departments.values()), default=None
            ),
            "non_zero_spend_ceilings": sorted(
                d.department_id for d in self._departments.values()
                if d.spend_ceiling_usd > 0
            ),
        }


def load() -> WorkforceRegistry:
    """The default registry, built from the shipped definitions."""
    return WorkforceRegistry()
