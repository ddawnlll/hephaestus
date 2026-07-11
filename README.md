# Hephaestus

> **Explore freely. Prove ruthlessly.**

A generic, reusable bootstrap and orchestration package for [Hermes Agent](https://github.com/NousResearch/hermes-agent).
Turns any codebase into a hypothesis-driven, evidence-gated, autonomous improvement loop.
All projects share the **same Hermes instance** with unique namespacing.

> Formerly `hermes-pack`. Renamed to Hephaestus — the forge/automaton god — to give this
> orchestration+verification layer its own identity, separate from the Hermes Agent runtime
> it bootstraps. See the [v0.5 Kaizen Engine release](https://github.com/ddawnlll/hephaestus/releases/tag/v0.5.0-kaizen).

## Architecture

```
hephaestus/
  install.sh               # One-liner curl installer
  bootstrap.sh             # Bash bootstrap (zero deps) — orchestrator mode
  bootstrap.ts             # TypeScript bootstrap (Bun)
  templates/               # Generic template files (SOULs, configs, prompts, scripts)
    SOUL.{orchestrator,redteam,worker,challenger,arbiter,reflector}.md
    beliefs.yaml           # Narrow, capacity-limited belief workspace (GWT analog)
    scripts/               # Deterministic gates + channel dispatchers
      tick-gate.sh, tick-runtime.py, tick-journal.py
      containment-engine.py, blame-propagation.py, feature-flags.py
      channel-{budget,dispatch}.py, channel-{analogy,dream,whisper,calibration}.py
      reflector-dispatch.sh, prereg-lock.py, self-grade-diff.py
      readiness-check.py, provenance-track.py
    prompts/tick.md        # Orchestrator tick prompt (all phases)
  adapters/                # Project-specific adapters
    v7-alphaforge/         # V7/AlphaForge adapter (orchestrator mode) — uses Reflector
    designforge/           # DesignForge adapter (custom mode)
    money-radar/           # Money Radar stub (custom mode, coming soon)
  schema/                  # Versioned JSON Schemas (state, control, goal, ideas, events,
                           # beliefs, hypothesis, provenance)
  schema/tests/            # Deterministic test suite — 191 tests, all pass
  .praxis/                 # Praxis Truth Kernel — plan specs + evidence ledger
```

### Two setup modes

| Mode | Adapter | Creates | Use case |
|------|---------|---------|----------|
| `orchestrator` | `v7-alphaforge` | 1 orchestrator + N worker profiles, 1 cron tick, gate script, hypotheses ledger | Hypothesis-driven alpha research |
| `custom` | `designforge`, `money-radar` | Adapter-defined profiles, multiple cron jobs, kanban | Non-orchestrator pipelines |

---

## Praxis Truth Kernel Integration

Hermes Pack integrates with the **[Praxis Truth Kernel](https://github.com/ddawnlll/praxis)** (`ddawnlll/praxis`) — an independent, deterministic verification layer for agent outputs. Praxis is **not** reimplemented here; it lives in its own repo and is called as a CLI tool via `tools/praxis-bridge.sh`.

### Architecture

```
Worker produces evidence bundle
        │
        ▼
┌──────────────────────────────────┐
│  praxis verify --plan planspec   │  ◄── 6 deterministic gates
│  • SchemaGate  — evidence format │       (NO LLM involved)
│  • LockGate    — plan integrity  │
│  • EvidenceGate — claims backed? │
│  • WiringGate  — contracts kept? │
│  • ExecGate    — tests actually  │
│                  ran?            │
│  • FinalGate   — criteria met?   │
└───────┬──────────────────────────┘
        │
    PASS/HOLD/FAIL
        │
    ┌───┴───┐
  FAIL     PASS/HOLD
    │        │
    ▼        ▼
Reject   Proceed to T1/T2/T3/T4
(no LLM)  (evidence-informed LLM gates)
```

### Integration Points

| Hermes Pack | Praxis Repo | Purpose |
|-------------|-------------|---------|
| `tools/praxis/` (submodule) | `ddawnlll/praxis` | Full Truth Kernel, CLI, plugin |
| `tools/praxis-bridge.sh` | — | Thin wrapper calling `praxis verify` |
| `adapters/*/project.yaml → praxis:` block | — | Adapter-level Praxis configuration |

### Key Rules

- **Praxis before T1.** No LLM gate runs before deterministic verification.
- **No evidence = no claim.** Worker output without evidence is invalid.
- **Workers don't write memory.** Only orchestrator after Praxis PASS + gate verdict.
- **Merge policy:** PR-only, never direct.

### Flow

```
cron tick → pre_tick_gate.sh → orchestrator wakes
  → dispatch worker (context capsule)
  → worker produces evidence
  → praxis verify (6 gates, deterministic)
  → T1 Proposer → T2 Challenger → T3 Arbiter → T4 Human
  → PR / reject / memory retain
```

See [`ddawnlll/praxis`](https://github.com/ddawnlll/praxis) for full Truth Kernel documentation.

## How it works (orchestrator mode)

1. **Bootstrap** creates Hermes profiles, a project ledger, and a cron tick.
2. **Orchestrator** runs on a cron schedule, reads hypotheses, dispatches work via Kanban, judges results.
3. **Workers** execute bounded hypothesis-testing tasks on isolated branches.
4. **Evidence** must come from deterministic runner JSON — never agent prose.
5. **Tick gate** pre-flight checks before waking the LLM.

## Quick Start

### 1. Install via one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/ddawnlll/hephaestus/main/install.sh | bash
```

Or clone directly:

```bash
git clone https://github.com/ddawnlll/hephaestus.git ~/.hephaestus
```

### 2. Bootstrap a project

```bash
# Orchestrator project (AlphaForge):
bash ~/.hephaestus/bootstrap.sh /path/to/alphaforge-infa --adapter v7-alphaforge

# Custom project (DesignForge):
bash ~/.hephaestus/bootstrap.sh /path/to/designforge --adapter designforge
```

### 3. Dry-run first (no changes made)

```bash
bash ~/.hephaestus/bootstrap.sh --dry-run /path/to/repo --adapter v7-alphaforge
```

## Multi-Project Setup (Single Hermes Instance)

All projects share the **same Hermes** with unique naming. Each adapter defines its own:

| Project | Profile Names | Cron Jobs | Kanban Board |
|---------|--------------|-----------|--------------|
| **AlphaForge** | `af-orchestrator`, `af-worker-1..3` | `af-orchestrator-tick` (every 45m) | `alphaforge` |
| **DesignForge** | `designforge-designer`, `designforge-judge` | `designforge-lead-discovery` (daily 09:00) | `designforge` |
| | | `designforge-draft-create` (daily 10:00) | |
| | | `designforge-reply-monitor` (every 2h weekdays) | |

```bash
# Install ALL on one Hermes:
bash ~/.hephaestus/bootstrap.sh ~/Documents/alphaforge-infa --adapter v7-alphaforge
bash ~/.hephaestus/bootstrap.sh ~/Documents/designforge --adapter designforge
```

No naming collisions. Each project is independent.

## Adapter System

Each adapter lives in `adapters/<name>/`:

```
adapters/<name>/
  project.yaml          # Project identity, names, providers, paths
  setup.sh              # Custom setup script (for custom mode)
  AGENTS.adapter.md     # Project-specific AGENTS.md (copied to repo)
  SOUL.*.md             # Profile SOUL overrides
  prompts/              # Cron job prompts
  hypotheses.seed.yaml  # Initial hypothesis families (orchestrator mode)
```

### Creating a new adapter

**For orchestrator projects** (hypothesis-driven, with T0/T1/T2/T3 gates):

Create `adapters/<name>/project.yaml`:

```yaml
project:
  name: "MyProject"
  objective: "Improve the project in measurable ways."
  board_name: "myproject-board"
  board_desc: "MyProject orchestration"

hermes:
  setup_mode: "orchestrator"           # default, can omit
  profile_orchestrator: "myproject-orch"
  profile_worker_prefix: "myproject-worker"
  worker_count: 3
  tick_name: "myproject-tick"
  tick_schedule: "every 45m"
  delivery: "local"
  provider:
    orchestrator: "anthropic"
    orchestrator_model: "claude-opus-4"
    worker: "openrouter"
    worker_model: "deepseek/deepseek-v4-flash"

paths:
  ledger: ".orchestrator"

boundaries:
  allowed:
    - "src/"
  forbidden:
    - "vendor/"

merge_policy: "pr_only"
max_parallel_workers: 3
max_llm_spend_per_day_usd: 25
```

**For custom projects** (non-orchestrator, with own setup script):

```yaml
project:
  name: "MyCustomProject"
  board_name: "myproject-board"

hermes:
  setup_mode: "custom"
  provider:
    default: "opencode-go"
    default_model: "deepseek-v4-flash"

paths:
  ledger: ".myproject"
```

Then create `adapters/<name>/setup.sh` with the custom profile/cron/kanban logic (see `adapters/designforge/setup.sh` as reference).

## Environment Overrides

```bash
# Override provider/model at bootstrap time:
HERMES_ORCH_MODEL="claude-sonnet-4" bash bootstrap.sh /repo --adapter v7-alphaforge
```

## Controls (orchestrator mode)

| Control | File | Action |
|---------|------|--------|
| Pause | `$LEDGER/control.yaml` → `mode: paused` | Orchestrator stops, writes one-paragraph report |
| Resume | `$LEDGER/control.yaml` → `mode: running` | Next tick proceeds normally |
| Kill | `$LEDGER/control.yaml` → `mode: killed` | Blocks all tasks, stops |
| Human directive | `human_instruction: "..."` | Treated as top priority next tick |
| Emergency stop | `hermes cron pause <tick-name>` | Master off switch |

## Commands

```bash
# Dry-run (no changes, no API keys needed)
bash bootstrap.sh --dry-run /path/to/repo --adapter v7-alphaforge

# Real bootstrap
bash bootstrap.sh /path/to/repo --adapter v7-alphaforge

# One-liner install + bootstrap
curl -fsSL https://raw.githubusercontent.com/ddawnlll/hephaestus/main/install.sh | bash -s -- --adapter designforge
```

## Available Adapters

| Adapter | Setup Mode | Target Repo | Status |
|---------|-----------|-------------|--------|
| `v7-alphaforge` | orchestrator | `ddawnlll/alphaforge-infa` | Active |
| `designforge` | custom | `ddawnlll/designforge` | Active |
| `money-radar` | custom | (coming soon) | Stub |

## Versioned Schema Contract

All stateful data in Hermes Pack follows a versioned JSON Schema contract. Five schema files live in `schema/`:

| Schema | File | Purpose |
|--------|------|---------|
| State | `schema/state.schema.json` | Orchestrator state.json — tick counters, worker status, budget, gate counters |
| Control | `schema/control.schema.json` | Control plane configuration — mode, paths, budget, risk gating |
| Goal | `schema/goal.schema.json` | Eternal/metric/gate_target goal definition with success criteria |
| Ideas | `schema/ideas.schema.json` | Idea lifecycle — spark, triage, hypothesis, verdict |
| Events | `schema/events.schema.json` | Append-only event log — tick/worker/gate/budget events |

### Schema Version Bump Procedure

When making backward-incompatible changes to any schema:

1. **Increment `schema_version`** in the affected schema file(s) — e.g., `1 → 2`.
2. **Create a migration script** `migrate-ledger-<from>to<to>.sh` or update `migrate-ledger.sh` with a version router.
3. **Update templates** — `templates/state.json`, `templates/control.yaml`, `goal.yaml`, `ideas/*.yaml`, `events.jsonl` to match the new schema.
4. **Update `tick-gate.sh`** if the validation logic needs updating for the new fields.
5. **Update the tick prompt** at `templates/prompts/tick.md` if schema changes affect orchestrator behavior.
6. **Run the test suite:** `python schema/tests/test_schema_validation.py`.
7. **Document the change** in the schema file's `description` field and in commit message.

> Backward-compatible additions (new optional fields, wider enums) do not require a schema bump or migration — but do update templates and tests.

### Validation Gate

The pre-tick gate (`templates/scripts/tick-gate.sh`) validates `state.json` against `state.schema.json` before waking the orchestrator. If validation fails, the gate emits `{"wakeAgent": false}` with an error context, preventing the LLM from reading or writing garbage state.

### Migration

Use `migrate-ledger.sh` to convert v1 ledger state (from the Lightning.ai era) to the v2 unified format:

```bash
bash migrate-ledger.sh .alphaforge/orchestrator/state.json --backup
```

## Provider Fallback Router (LiteLLM Proxy)

Hermes Pack includes a **LiteLLM proxy configuration** that provides the "never-dies" guarantee for all profiles.

### Architecture

```
Orchestrator → proxy → [claude-opus → deepseek-v3 → local-qwen]   ← never dies
Worker       → proxy → [deepseek-flash → openrouter-free → local-llama]
Challenger   → proxy → [mid → cheap → local]                       ← different model from orchestrator
Arbiter      → proxy → [premium → mid → local]                     ← different model from challenger
```

Every profile chain ends with a **local model** (Ollama/LM Studio). If all cloud providers are down, the system continues running locally.

### Configuration

Provider chains are defined in the adapter's `project.yaml`:

```yaml
hermes:
  provider:
    orchestrator_chain:
      - "claude-sonnet-4-20250514"
      - "deepseek/deepseek-chat"
      - "ollama/llama3"            # local fallback — never dies
    worker_chain:
      - "deepseek/deepseek-chat"
      - "ollama/llama3"
    challenger_chain:
      - "deepseek/deepseek-chat"
      - "ollama/llama3"
    arbiter_chain:
      - "claude-sonnet-4-20250514"
      - "deepseek/deepseek-chat"
      - "ollama/llama3"
```

### Bootstrap

During bootstrap, the LiteLLM config is generated at `~/.hermes/scripts/litellm-config.yaml`. Start the proxy:

```bash
litellm --config ~/.hermes/scripts/litellm-config.yaml
```

Then configure Hermes profiles to point to `http://localhost:4000` (the default LiteLLM proxy endpoint).

### Key Properties

- **No fork required.** LiteLLM is a standalone proxy; Hermes sees a single OpenAI-compatible endpoint.
- **Per-profile chains.** Orchestrator, worker, challenger, and arbiter each have their own fallback chain.
- **Challenger/arbiter diversity.** Different models are guaranteed for challenger (read-only, blind evaluation) and arbiter (binding decision).
- **Sequential fallback.** On primary provider failure, the chain drops to the next model automatically.
- **Local last resort.** Every chain ends with a local Ollama/LM Studio model.

## v0.5 — Kaizen Engine (Hephaestus)

> **Status: shipped in v0.5.0-kaizen** (PR [#73](https://github.com/ddawnlll/hephaestus/pull/73)).
> All issues #52–#72 closed. 191 tests pass. Praxis evidence bundle recorded at
> `.praxis/runs/v05-full-evidence.jsonl`. See [release notes](https://github.com/ddawnlll/hephaestus/releases/tag/v0.5.0-kaizen).

The **Kaizen Engine** turns the loop into a self-improving system by adding a third face
(Reflector), a belief workspace (Global Workspace analog), containment for new deadlock
modes, and four idea channels that supply diversity at volume. The org chart, end to end:

```
                        ┌───────────────────────────┐
                        │   HUMAN  (T4)             │  ← only disputes +
                        │   final arbiter / veto    │    Red-Team blocking escalation
                        └─────────────┬─────────────┘
                                      │ (disputes only)
        control.yaml ┌────────────────┴────────────────┐ goal.yaml
        (mode/priority)│                                 │(target + ratchet)
                       ▼                                 ▲
   ╔═══════════╗   ┌───────────────────────────────┐    │
   ║ EXPLORER  ║──►│                               │    │
   ║ divergence║   │        ORCHESTRATOR           │    │
   ║           ║   │     (commander / hub)         │    │
   ║ "what if? "║   │  dispatch • propose          │    │
   ║ no veto   ║   │  no merge (→ T3)              │    │
   ╚═════▲═════╝   └───┬───────────────────────▲───┘    │
         │             │ dispatch               │ verdict│
   channels:            ▼                        │        │
   ┌──────────┐   ┌─────────┐  evidence   ┌─────┴──────┐ │
   │ ANALOGY  │   │ WORKERS │────────────►│  PRAXIS    │ │
   │ DREAM    │   │ (N)     │  bundle     │ 6 gates    │ │
   │ WHISPER  │   │ execute │             │ determ.    │ │
   │ CALIBR.  │   └─────────┘             │ FAIL=hard  │ │
   └────┬─────┘                           └─────┬──────┘ │
        │ candidates only                PASS │        │
        │ (never bypass hypothesis)            ▼        │
        │                              ┌──────────────┐   │
        │                              │ T1→T2→T3     │   │  per-evidence
        │                              │ LLM gates    │   │  judgment
        │                              └──────┬───────┘   │
        │                              tier verdict │     │
        │                                     ▼           │
        │ objections.jsonl    ╔══════════════════╗       │
        └──────────────────────║   RED TEAM       ║───────┘ ratchet.json
           "don't re-propose   ║   convergence    ║  (raises the bar)
            this dead hyp."    ║ strategy-adversary║
                              ║ VETO + ratchet   ║
                              ║ no merge          ║
                              ╚════════╤═════════╝
                                       │
                            BLOCK ◄────┼────► CONCEDE
                               │              │
                     escalate to T3     Orchestrator MERGEs
                       Arbiter      → writes to Hindsight memory

   ┌──────────────────────────────────────────────────────────────┐
   │              BELIEF WORKSPACE (beliefs.yaml)                 │
   │   HARD CAP 12 active beliefs. Every entry has a              │
   │   kill_criterion (falsifiability contract). Single-writer:   │
   │   Reflector only. Capacity competition for entry.            │
   └──────────────────────────────────────────────────────────────┘
                                ▲
                                │ consolidation runs (idle / plateau)
                                │
                         ┌──────┴──────┐
                         │  REFLECTOR  │  explain/ · consolidate
                         │  (decorrel.)│  • shared-assumption extraction
                         │  writes:    │  • relaxation probe
                         │   beliefs,  │  • perspective tour
                         │   narrative │  may mark ≤ 1 belief suspect/run
                         └─────────────┘
```

### What ships in v0.5

**Phase 0 — debt cleared** (issues #52–#55):
- `SOUL.challenger.md` (T2, read-only, blind, decorrelated model) and `SOUL.arbiter.md`
  (T3, raw-evidence-only, binding merge/reject) — personas + bootstrap wiring.
- `self-grade-diff.py` and `prereg-lock.py` — the two orphan gates implemented; tests moved
  out of `tests_tmp/` into `schema/tests/`. `.gitignore` tripwires added for `C:Users*` and
  `C:/` Windows path artifacts.

**Phase 1 — Belief workspace + Reflector** (#56–#60):
- `schema/beliefs.schema.json` — capacity cap 12, mandatory `kill_criterion` (falsifiability
  contract), `blamed_by` blame tracking, `historical_beliefs[]` for evicted/refuted entries.
- `relies_on` field on hypotheses — when a hypothesis FAILs, blame propagates upward to every
  belief it relied on. Three failures on B-X → B-X becomes a *suspect* — this is the mechanism
  that produces "grow the dataset" without ever enumerating axes in config.
- `narrative.md` — one-page project story, rewritten (not appended) by Reflector each run.
- `SOUL.reflector.md` + `reflector-dispatch.sh` — shared-assumption extraction, relaxation
  probe, perspective tour. **Decorrelated model family** from orchestrator (else self-grading
  theater). Runs offline (idle / plateau), never writes code.
- Stagnation/momentum signals in `state.json`; SOUL hard rule: while a `suspect` belief
  exists, no new hypotheses inside that frame — either test the belief or file to T3.

**Phase 2 — Containment** (#61–#64):
- `authority-matrix.yaml` — terminal referee for every role pair (no referee sits in a pair
  it is party to; every blocking state has a timeout + safe-default HOLD).
- `suspect TTL` — `suspect` expires after N ticks (default 5); Reflector must re-justify.
- `curiosity exemption` — belief-test hypotheses run from the protected curiosity budget;
  Red Team blocks MERGE of result, never the RUN of the experiment.
- `belief min-residency` (M ticks, default 3) + evidence-backed eviction audit log.
- `frame-shift cooldown` (K ticks, default 8) + ratchet hysteresis (max one notch per
  R-window; direction reversal requires a window of evidence, not a single reading).

**Phase 3 — Idea channels** (#65–#68):
- **Analogy** — `~/.hermes/lessons.jsonl` cross-project corpus with dual writing (concrete
  + denominalized abstract). Casting sessions force-fit top-5 abstract lessons from OTHER
  projects; survivors become hypotheses tagged `provenance: analogy`.
- **Random-leap** — bisociation replay (sample ledger pairs at MID embedding distance),
  dream mode (seeded entropy, generation/filtering separated by sleep cycle), and one
  random arXiv/HN item per day for external entropy.
- **Affect** — calibration (Brier scores; confidently-wrong is costly, agreement is NOT
  rewarded), mood as parameter modulation (never decision gating), boredom → family
  rotation (interleaving).
- **Context** — `whispers/` inbox (unstructured human impressions, 30s, weakest evidence),
  morning briefing, regime detector. Security: every external stream must earn workspace
  entry through capacity + competition; no external writes to `beliefs.yaml` directly.
- All channels are **independently feature-flagged, default disabled, separate daily
  budgets, candidate-only output**. Disabled = zero spend, zero artifacts.

**Phase 4 — Provenance + measurement** (#69): every hypothesis + merge carries a
`provenance` tag (`elimination | analogy | replay | whisper | external | relaxation`).
Reports aggregate per-channel hit rates. A merge without provenance fails schema validation.

**Phase 5 — Runtime reliability** (#70, #71, #72):
- `feature-flags.py` — gradual rollout with safe defaults (shadow mode, zero execution
  for disabled flags). Active mode blocked until `readiness-check.py` passes.
- `tick-journal.py` — durable transaction journal with atomic write-and-rename, phase
  tracking, operation-key idempotency, stale-lock recovery, integrity checking. Proves
  idempotent across worker dispatch, blame propagation, merges, lessons, provenance,
  spend accounting, channel output, and reflector consolidation.
- `channel-budget.py` — atomic daily idempotent accounting with file locking, stable
  operation keys (no UUID), and UTC reset.
- **Canary suite** — 11 end-to-end scenarios covering belief capacity 12/13, TTL expiry,
  direct blame, authority coverage failure, ratchet restart, prompt-injection isolation,
  disabled-channel zero side effects, deadlock recovery, eviction, reflector shadow
  isolation, duplicate-tick idempotency, and crash recovery.
- `tick-runtime.py` deterministic wrapper with journal phase transitions; `tick-gate.sh`
  calls `tick-runtime.py init` as mandatory pre-tick hook.
- `.github/workflows/v05-ci.yml` — full test matrix, real bootstrap dry-runs, budget,
  journal, and interlock tests on every PR.

### Invariants (enforced by tests)

- 191 tests pass across `schema/tests/` (41 correction + 19 canary + 131 legacy).
- A merge without `provenance` fails schema validation.
- `bootstrap.sh` bash syntax verified (`bash -n` clean).
- Disabled channel = `0` USD spend, `0` artifacts, `0` proposals.
- Reflector writes only `beliefs.yaml` and `narrative.md` — never code, never hypotheses.
- Authority matrix covers all role pairs; new profiles fail bootstrap without a matrix entry.

### Migration from v0.4

`migrate-ledger.sh` converts v1 hypothesis files (empty `relies_on`) into v0.5 schema.
The `relies_on` field is required on all new hypotheses from this release forward.

## Known limitations

- Reflector active mode requires readiness check + containment verified; default is
  shadow mode (writes `reflector_proposals.yaml`, never touches `beliefs.yaml`).
- Channel dispatch is wired in the tick prompt; deterministic channel-dispatch scripting
  (pre-commit hooks, cron-side enforcement) is a hardening opportunity.
- `bootstrap.sh` registry update uses a Python heredoc — bash `bash -n` passes, but
  prefer `bootstrap.ts` (Bun) for new adapter work.
