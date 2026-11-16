# BSI Codex engineering kickoff — five lanes (2026-10-17)

This is an engineering handoff, NOT evidence that Codex Cloud is running or that anything
has deployed. Public repo: no credentials, customer data, backup files or private Drive links.
Zero spend; use isolated branches, tests, review and owner approval for production/high risk.

1. **P0 Render preservation (#3)**: database export before 2026-10-27. Reuse existing
   `oddfellow/db_preserve.sh`; verify real PostgreSQL 18 custom dump, SQL.gz, file integrity,
   isolated restore and private off-Render copy. Configuration ZIP != DB backup. Live access
   required, do not expose a download endpoint or alter allowlists without approval.
2. **Oddfellow/Letta (#5)**: preserve canonical `letta/combined-single-service-v0.20.4`.
   Review existing draft PR #1 before touching handoff paths. Test idempotence, approvals,
   durable state and capability routing. No fabricated direct connections.
3. **Command Center (#4)**: build on `oddfellow/command_center.py`; fail-closed auth,
   audit, pause, idempotency and persistence. No unreviewed multi-isolate deployment.
4. **App Factory (#2)**: source and test *existing* prototypes first. Confirm actual
   source/URLs; test mobile, accessibility, privacy, startup and responsiveness.
5. **Fourthwall (#6)**: first delivered code = `commerce/tools/pricing_audit.py` +
   regression tests; offline estimate only. Historical costs require live confirmation.
   Collect current products/prices before proposing user-facing changes. Preserve separate
   Norse and Celtic collections. No launch or licensing outreach.

Treat every branch head, test count and deployment claim as a dated observation.
Never replace newer canonical work, merge automatically, or claim unattended execution.
