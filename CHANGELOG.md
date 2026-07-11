# Changelog

All notable changes to this project are documented here.

## [0.5.0-kaizen] — 2026-07-11

The **Kaizen Engine** — turning the loop into a self-improving system by adding a third
face (Reflector), a belief workspace (Global Workspace analog), containment for new
deadlock modes, four idea channels that supply diversity at volume, and crash-safe runtime
infrastructure. All 21 v0.5 issues (#52–#72) closed via PR [#73](https://github.com/ddawnlll/hephaestus/pull/73).
191 tests pass. Praxis evidence bundle recorded at `.praxis/runs/v05-full-evidence.jsonl`.

### Phase 0 — debt cleared (#52, #53, #54, #55)
- **T2 Challenger / T3 Arbiter personas** — `templates/SOUL.challenger.md` (read-only, blind,
  decorrelated model, one rebuttal round) and `templates/SOUL.arbiter.md` (raw-evidence-only,
  binding merge/reject, falsifiability discipline). Bootstrap wiring in `bootstrap.sh` and
  `bootstrap.ts`. Hard rule: only `__HERMES_*__` template variables.
- **Self-grade diff gate** — `templates/scripts/self-grade-diff.py` (was orphan
  `test_self_grade_diff.py`). Deterministic verdict comparison: orchestrator verdict cannot be
  more optimistic than mechanical evidence verdict. Wired into tick pipeline.
- **Pre-registration lock** — `templates/scripts/prereg-lock.py`. Locks metric, threshold,
  direction, and `relies_on` at dispatch time with SHA-256 tamper detection. Blocks p-hacking.
- **Repo hygiene** — `schema/tests_tmp/` removed; duplicate tests promoted to `schema/tests/`
  with passing implementations; `.gitignore` tripwires added for `C:Users*` and `C:/` to
  prevent Windows path artifacts.

### Phase 1 — Belief workspace + Reflector (#56, #57, #58, #59, #60)
- **`schema/beliefs.schema.json`** — narrow, capacity-limited workspace (GWT core). Hard cap
  12 active beliefs, mandatory `kill_criterion` (falsifiability contract), `blamed_by` blame
  tracking, `historical_beliefs[]` for evicted/refuted entries. Reflector is the single writer.
- **`relies_on` field on hypotheses** — the load-bearing change. When a hypothesis FAILs,
  blame propagates upward to every belief it relied on. Three failures on B-X → B-X becomes
  a *suspect*. Schema-breaking: `relies_on` is required (may be empty `[]`); migration in
  `migrate-ledger.sh`.
- **`templates/beliefs.yaml`** and **`templates/hypothesis.yaml`** — template files matching
  the new schemas.
- **Reflector agent** — `templates/SOUL.reflector.md` and `templates/scripts/reflector-dispatch.sh`.
  Three questions per run: shared-assumption extraction, relaxation probe, perspective tour.
  Decorrelated model family from orchestrator. Runs offline (idle / plateau), like human
  sleep consolidation. May mark at most ONE belief `suspect` per run. Writes only
  `beliefs.yaml` and `narrative.md` — never code, never hypotheses.
- **`narrative.md`** — one-page project story, rewritten (not appended) by Reflector each
  run. Hard cap ~500 words. Orchestrator reads it every tick as context.
- **Stagnation / momentum signals** — `state.json` extended with `stagnation` (info-gain
  per tick) and `momentum` (merge streak). Deterministic computation.
- **Suspect-belief rule** — hard rule in `SOUL.orchestrator.md` and `prompts/tick.md`:
  while a `suspect` belief exists, no new hypotheses inside that frame — either test the
  belief or file an objection to T3.

### Phase 2 — Containment (#61, #62, #63, #64)
- **Authority matrix** — `templates/scripts/containment-engine.py` with 28 role-pair entries.
  Every blocking state has a terminal referee (plus timeout + safe-default HOLD). No referee
  sits in a pair it is party to. Reflector↔Red Team disputes → T3 Arbiter.
- **Suspect TTL** — `suspect` expires after N ticks (default 5). Reflector must re-justify
  with new evidence. No permanent frame lockout.
- **Curiosity exemption** — belief-test hypotheses run from the protected curiosity budget.
  Red Team blocks MERGE of result, never the RUN of the experiment. Gates constrain
  *claims*, never *curiosity*.
- **Belief min-residency** — belief cannot be evicted for M ticks after entry (default 3)
  unless its own `kill_criterion` evidence arrived. Eviction audit log at
  `$LEDGER/beliefs-evictions.jsonl`.
- **Frame-shift cooldown + ratchet hysteresis** — after a suspect-driven frame shift, no
  new suspect marking for K ticks (default 8). Ratchet: max one notch change per R-window;
  direction reversal requires a full window of evidence.

### Phase 3 — Idea channels (#65, #66, #67, #68)
- **Analogy channel** — `templates/scripts/analogy-channel.py`. `~/.hermes/lessons.jsonl`
  cross-project corpus with dual writing (concrete + denominalized abstract). Casting
  sessions force-fit top-5 abstract lessons from other projects; survivors become hypotheses
  tagged `provenance: analogy`.
- **Random-leap channel** — `templates/scripts/dream-channel.py`. Bisociation replay (sample
  ledger pairs at MID embedding distance), dream mode (seeded entropy, generation/filtering
  separated by sleep cycle), external entropy (one random arXiv/HN item per day).
- **Affect channel** — `templates/scripts/calibration-channel.py`. Brier score tracking;
  confidently-wrong is costly; agreement is NOT rewarded. Mood as parameter modulation
  (never decision gating); boredom → hypothesis family rotation (interleaving).
- **Context channel** — `templates/scripts/whisper-channel.py`. `whispers/` inbox
  (unstructured human impressions, 30s, weakest evidence), morning briefing, regime detector.
  Security: every external stream must earn workspace entry through capacity + competition;
  no external writes to `beliefs.yaml` directly.
- All channels are **independently feature-flagged, default disabled, separate daily
  budgets, candidate-only output**. Disabled = zero spend, zero artifacts.

### Phase 4 — Provenance + measurement (#69)
- **`schema/provenance.schema.json`** — every hypothesis + merge carries a `provenance`
  tag (`elimination | analogy | replay | whisper | external | relaxation`). Schema-breaking:
  a merge without `provenance` fails validation.
- **Per-channel hit-rate reports** — reports aggregate per-channel idea → dispatched →
  merged rates, plus USD spent. A small aggregator script for the rolling table.
- **Coordinator** — rides the phase-1 schema bump; must exist from day one of channel
  operation so rates are measured from birth.

### Phase 5 — Runtime reliability (#70, #71, #72)
- **Feature flags** — `templates/scripts/feature-flags.py`. Gradual rollout with safe
  defaults (shadow mode). Disabled flag = zero execution, zero spend, zero output. Active
  mode blocked until `readiness-check.py` passes (real subprocess calls; no fake pass).
- **Tick transaction journal** — `templates/scripts/tick-journal.py`. Durable transaction
  journal with atomic write-and-rename, phase tracking, operation-key idempotency,
  stale-lock recovery, integrity checking. Proves idempotent across worker dispatch, blame
  propagation, merges, lessons, provenance, spend accounting, channel output, and
  reflector consolidation.
- **Centralized channel budget** — `templates/scripts/channel-budget.py`. Atomic daily
  idempotent accounting with file locking, stable operation keys (no UUID), UTC reset.
  Feature flag + daily budget enforcement in one place.
- **Deterministic dispatchers** — `templates/scripts/tick-runtime.py` and
  `templates/scripts/channel-dispatch.py`. Tick runtime wraps journal phase transitions
  with `init` as mandatory pre-tick hook. Channel dispatch is fail-closed at every step.
- **CI workflow** — `.github/workflows/v05-ci.yml` with 10 steps: real bootstrap
  dry-runs, budget/journal/interlock tests, full test matrix on every PR.
- **Canary suite** — `schema/tests/test_canary_suite.py`. 11 end-to-end scenarios covering
  belief capacity 12/13, TTL expiry, direct blame, authority coverage failure, ratchet
  restart, prompt-injection isolation, disabled-channel zero side effects, deadlock
  recovery, eviction, reflector shadow isolation, duplicate-tick idempotency, and crash
  recovery. 19 assertions, all pass.

### Bootstrap integration
- `bootstrap.sh` — DF_REFLECTOR_* defaults, adapter extraction, template vars, reflector
  profile install, v0.5 script copy, extra ledger dirs (beliefs, provenance, reflector,
  whispers, analogies, dreams), registry update.
- `bootstrap.ts` — `AdapterConfig.reflector_model/chain`, decorrelation check against
  orchestrator, profile install, v0.5 script copy, registry update.
- `adapters/v7-alphaforge/project.yaml` — reflector model/chain added (deepseek != claude
  orchestrator, satisfies decorrelation invariant).
- `templates/prompts/tick.md` — Phase 4 channel dispatch + reflector dispatch added.
  Every channel gated by `channel-budget.py can-run`. Channel output is explicitly
  candidate-only, never bypasses hypothesis validation.

### Invariants (enforced by tests)
- 191 tests pass across `schema/tests/` (41 correction + 19 canary + 131 legacy).
- A merge without `provenance` fails schema validation.
- `bootstrap.sh` bash syntax verified (`bash -n` clean).
- Disabled channel = `0` USD spend, `0` artifacts, `0` proposals.
- Reflector writes only `beliefs.yaml` and `narrative.md` — never code, never hypotheses.
- Authority matrix covers all role pairs; new profiles fail bootstrap without a matrix entry.
- Provider-chain decorrelation: orchestrator ≠ worker ≠ challenger ≠ arbiter ≠ reflector
  (different model families; bootstrap `validateChainDecorrelation()` fail-closed).

### Added (files)
- `schema/beliefs.schema.json`, `schema/hypothesis.schema.json`, `schema/provenance.schema.json`
- `templates/SOUL.{challenger,arbiter,reflector}.md`
- `templates/beliefs.yaml`, `templates/hypothesis.yaml`, `templates/narrative.md`
- `templates/config.{challenger,arbiter,reflector}.yaml`
- `templates/scripts/containment-engine.py`, `blame-propagation.py`, `feature-flags.py`
- `templates/scripts/{analogy,dream,whisper,calibration}-channel.py`
- `templates/scripts/{channel,reflector}-dispatch.{sh,py}`
- `templates/scripts/{channel-budget,prereg-lock,self-grade-diff,provenance-track}.py`
- `templates/scripts/{readiness-check,tick-journal,tick-runtime}.py`
- `schema/tests/test_phase{1,2,3}_*.py`, `test_correction_pass.py`, `test_canary_suite.py`, `test_ci_integration.py`
- `.praxis/v05-planspec.yaml`, `.praxis/runs/v05-{,full-}evidence.jsonl`
- `.github/workflows/v05-ci.yml`
- `reports/v05_kaizen_engine_completion.accp.yaml`, `reports/generate-accp-report.py`
- `.praxis/generate-v05-accp.py`

### Changed
- `package.json` — version bumped `0.4.0-planning` → `0.5.0-kaizen`.
- `schema/state.schema.json` — v2: beliefs summary, features, channel budgets, calibration,
  run/phase for crash recovery.
- `templates/state.json` — v2 with safe defaults; matches new schema.
- `templates/prompts/tick.md` — Phase 4 channel dispatch + reflector dispatch sections.
- `templates/scripts/tick-gate.sh` — calls `tick-runtime.py init` as mandatory pre-tick hook.
- `bootstrap.sh` — reflector profile + v0.5 script copy + extra ledger dirs.
- `bootstrap.ts` — `AdapterConfig.reflector_model/chain` + decorrelation check.
- `adapters/v7-alphaforge/project.yaml` — `reflector_model`/`reflector_chain` fields.
- `README.md` — v0.4 design section replaced with v0.5 shipped section; repo layout updated.

### Migration
- `migrate-ledger.sh` converts v1 hypothesis files (empty `relies_on`) into v0.5 schema.
- `relies_on` is required (may be empty `[]`) on all new hypotheses from this release.

## [0.4.0-planning] — 2026-07-08

Rebrand + design phase for the adversarial council architecture. **No new runtime behavior
ships in this release** — this is documentation, naming, and repo scaffolding. The actual
implementation is tracked in [milestone v0.4](https://github.com/ddawnlll/hephaestus/milestone/5)
(issues #21–#32) and has not landed yet.

### Changed
- Repository renamed `hermes-pack` → `hephaestus`. Local install directory convention changed
  from `~/.hermes-pack` to `~/.hephaestus`; env var `HERMES_PACK_DIR` → `HEPHAESTUS_DIR`.
- `package.json` name `hermes-orchestrator-pack` → `hephaestus`, version bumped to
  `0.4.0-planning`.
- GitHub repo description, topics, and motto ("Explore freely. Prove ruthlessly.") updated.
- `schema/*.schema.json` `$id` URLs updated to the new repo path.
- README rewritten: new name/motto, and a new "v0.4 — Adversarial Council (Hephaestus)" section
  describing the Janus design (Explorer + Red Team), the three \$0 deterministic gates, and the
  escalation/AFK policy — explicitly marked as design/roadmap, not implemented.

### Added
- `templates/SOUL.redteam.md` — Red Team persona (strategy-layer adversary, falsifiability
  contract, scar-tissue memory). Not yet wired into bootstrap.
- New GitHub milestone "v0.4 — Adversarial Council (Hephaestus)" and 12 tracking issues
  (#21–#32) covering: orchestrator/merge conflict-of-interest separation, provider-chain
  decorrelation, scar-tissue memory in the Hindsight bridge, Red Team + Explorer wiring,
  adaptive ratchet, pre-registration lock gate, self-grade diff gate, ROI/exploitation-throttle
  gate, curiosity budget, and escalation/AFK policy.
- New labels: `adversarial-council`, `escalation`.

### Not changed (intentionally)
- `.praxis/**` (plans, locks, runs, repairs) and `reports/**` — historical audit trail,
  left untouched. Rewriting evidence history would violate Praxis's own no-tampering principle.
- The existing v0.2/v0.3 milestone roadmap (desktop app, Ideas Engine, events ticker, etc.) —
  unrelated to this rebrand, not touched.

## [1.0.0] — prior to this changelog

Initial `hermes-pack` releases: Praxis Truth Kernel integration, versioned schema contract
(state/control/goal/ideas/events), LiteLLM provider fallback router, v1→v2 ledger migration.
Not tracked in detail retroactively.
