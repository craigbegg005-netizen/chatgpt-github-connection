# Oddfellow cognition package

The package contains two separate capabilities:

- `profile.py` measures evidence-backed computational behavior. It is an
  instrument, not a reasoning system or a claim about consciousness.
- `memory.py` stores local episodic records in SQLite and retrieves them by
  exact token overlap. It is a primitive for continuity, not semantic search,
  learned memory, or a connection to Letta.

## Local episodic memory

```python
from oddfellow.cognition import MemoryStore

with MemoryStore("/path/in-a-private-directory/episodes.sqlite3") as memory:
    saved = memory.remember(
        namespace="agent:odd", content="The offline suite passed 789 tests.",
        source_ref="test-run:2026-11-03", confidence="tested",
        tags=("verification", "offline"),
    )
    results = memory.search(namespace="agent:odd", query="offline suite")
```

Use a file path for persistence; `:memory:` exists only for tests. Records keep
their source reference, caller-supplied confidence label, creation time, tags,
and SHA-256 of the content. Search returns an `UNTRUSTED_CONTEXT` label and an
overlap fraction. Neither metadata nor ranking proves that a statement is true.
Callers must keep namespaces separated and authorize access before using the
store; a namespace is not authentication. `forget` removes one record by both
namespace and ID and asks SQLite to overwrite deleted cell content. It is not a
forensic erasure guarantee; filesystem snapshots and external backups are outside
this primitive. POSIX database files are set to owner read/write only.

The store is not wired into the Letta backend, connector queue, CommandCenter,
or any running service. No prior conversation is imported. A production
integration needs a separately reviewed identity boundary, retention policy,
backup plan, and user-visible memory controls.

## Local verification — 2026-11-03

- `python oddfellow/run_offline_tests.py oddfellow/tests/test_cognition_memory_store.py -q`:
  11 passed.
- `python oddfellow/run_offline_tests.py -q`: 790 passed, 1 skipped, 1 existing
  Starlette/httpx deprecation warning; 791 tests collected.
- A disposable SQLite microbenchmark wrote 1,000 small records in 0.0885 s
  (11,304.8 records/s) and searched 100 queries at 2.4989 ms median / 3.0165 ms
  p95. Python 3.12.14, local temp filesystem, one transaction per record. This
  is a storage-path timing check, not a memory-quality or model-capability result.
