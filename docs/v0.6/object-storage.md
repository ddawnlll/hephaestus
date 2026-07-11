# Object Storage Pointer Convention (DL-3)

**Issue:** #96 (Track D)
**Status:** Accepted — v0.6
**Consumed by:** BE-3 (#86) rollback snapshots, BE-6 (#84) precedent memory, DL-4 (#98) memory layers, BE-7 (#88) golden replay
**Completion gates:** indirectly contributes to #11 (shared workspace — the pointer is part of the shared state).

## 1. What this contract locks

Large evidence artifacts (test logs, checkpoints, datasets, diffs, snapshots) MUST NOT live inside Postgres rows. Instead, the artifact bytes live in object storage, and a **pointer** (this schema) lives in the DB. The pointer is small, queryable, and immutable; the bytes are large, opaque, and content-addressed.

This separation keeps Postgres row sizes bounded (so query plans stay predictable), enables horizontal scaling of storage (S3-compatible, including local MinIO), and gives a single, uniform convention for evidence across all subsystems.

## 2. Pointer fields

| Field | Type | Description |
|---|---|---|
| `artifact_uri` | `s3://...` or `file://...` | Where the bytes are. Resolved by `templates/scripts/artifact_store.py`. |
| `hash` | `sha256:<hex64>` | Content hash. Verified on read. Mismatches move the artifact to `QUARANTINED`. |
| `size` | integer (bytes) | Verified on read. |
| `mime_type` | string (IANA) | What the bytes are. Producers SHOULD set the precise type. |
| `producer` | `<role>:<id>` | Who created it. Used for audit and producer-rate-limits. |
| `evidence_status` | enum | `PENDING` (write done, not yet verified) → `VERIFIED` (hash/size match) → `QUARANTINED` (mismatch) or `REVOKED` (explicit). |
| `captured_at` | ISO-8601 | When the producer wrote the artifact. |
| `expires_at` | ISO-8601 (optional) | Garbage-collected after this time. Default: 7 days for snapshots, indefinite for precedent memory. |
| `metadata` | object (free-form) | Producer-defined. Common keys: `candidate_id`, `tick_id`, `phase`, `schema_version`. |

## 3. Storage adapter

`templates/scripts/artifact_store.py` is the single point of read/write. It dispatches on `artifact_uri` scheme:

- `s3://<bucket>/<key>` → MinIO local in dev, S3 in prod. Auth via env (`ARTIFACT_S3_ENDPOINT`, `ARTIFACT_S3_KEY`, `ARTIFACT_S3_SECRET`).
- `file://<abs_path>` → local filesystem. Used for tests and offline replay. The path MUST be inside `templates/storage/artifacts/` (the canonical local root) or an override set via `ARTIFACT_FS_ROOT`.

Both implementations:

1. On write: write bytes, compute `sha256`, record `size`, return pointer.
2. On read: open the URI, recompute `sha256`, compare to `hash`, compare `size` to the actual byte count. On mismatch, log to `tick-journal.py` and move the pointer's `evidence_status` to `QUARANTINED`. The bytes are not returned; the caller is told the artifact is unavailable.
3. On delete: idempotent; returns success whether the artifact existed or not (used by the GC job).

## 4. Lifecycle

```
PENDING → (verify on first read or by background job) → VERIFIED
                                                            │
                                                            ↓ (hash/size mismatch)
                                                       QUARANTINED
                                                            │
                                                            ↓ (explicit invalidation)
                                                        REVOKED
```

- `PENDING` is the initial state. Writers set it; the verify step (either on first read or via a background job) transitions to `VERIFIED` or `QUARANTINED`.
- `REVOKED` is set explicitly (e.g. by a rollback operation that invalidates the evidence for a failed candidate). Reads of `REVOKED` artifacts return `None` and log the access.

## 5. GC policy

| Artifact kind | Default retention | Override |
|---|---|---|
| `rollback_snapshot` | 7 days | per-candidate override (`rollback_pointer.expires_at`) |
| `precedent_memory` | indefinite | n/a |
| `canary_log` | 30 days | per-tick override |
| `test_log` | 14 days | n/a |
| `evidence_dataset` | 90 days | per-candidate override |

The GC job (`templates/scripts/artifact_store.py gc`) is run nightly by `tick-gate.sh` after the tick completes. GC is idempotent: deleting an already-deleted artifact is a no-op.

## 6. Consumed by

- **BE-3** (#86): rollback snapshots — every snapshot is an artifact (mime `application/json`, status `VERIFIED`).
- **BE-6** (#84): precedent memory — large lessons (with embedded narrative + diffs) become artifacts; small lessons stay inline.
- **BE-7** (#88): golden replay — replay reads `evidence_pointers[].key` from the executive packet and resolves them via this convention.
- **DL-4** (#98): memory layers — episodic / scar / cross-project memory may include large artifacts.
- **Containment Engine** (`templates/scripts/containment-engine.py`, 30K, merged from #61): the audit trail of any action may attach an artifact pointer (e.g. "why was this candidate killed" with a snapshot of the kill state).

## 7. Failure modes

- **S3 / filesystem unavailable**: reads return `None`; the caller decides whether to pause. For `evidence_status=VERIFIED` artifacts, the convention is "fail closed" — a missing artifact is treated as no evidence, not as a false positive.
- **Hash mismatch on read**: pointer moves to `QUARANTINED`. A `quarantined_artifact` event is appended to `tick-journal.py`. The artifact is not deleted (forensic value); it is held aside.
- **Producer impersonation**: the `producer` field is logged but not cryptographically signed in v0.6. Future work (v0.7+) may add signed producer identity.

## 8. Reference

- A-4 (#79): State-of-Record cutover — the same OR'ling logic applies to artifact ownership during the file → DB migration.
- A-3 (#78): Promotion Mechanism — `code` asset type produces a PR-attachable diff artifact.
- BE-1 (#82): candidate manifest — `rollback_pointer` is an artifact pointer.
- #61 (merged): Containment Engine — audit trail of any system action.
- `templates/scripts/tick-gate.sh` (8.5K) — runs the GC job post-tick.
