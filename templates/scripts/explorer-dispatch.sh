#!/usr/bin/env bash
# Explorer Dispatch — idle-tethered divergence feeder.
# Called when the orchestrator detects an idle state (fewer open hypotheses
# than the idle_trigger_hypotheses threshold in explorer-profile.yaml).
#
# Workflow:
#   1. Check scar-tissue (objections.jsonl) for refuted hypotheses.
#   2. Down-weight any topic family that appears in a BLOCK stance objection.
#   3. Pick a source_type from the explorer profile.
#   4. Generate exploration parameters for a new hypothesis.
#
# Output (stdout): {"action":"generate","params":{...}}
# Exit code: 0 on success, 1 on error
#
# Dependencies:
#   - templates/explorer-profile.yaml  (read via grep for bash compat)
#   - <ledger>/redteam/objections.jsonl (scar-tissue memory, issue #23)

set -u

PACK_DIR="$(cd "$(dirname "$0")/../../" && pwd)"
LEDGER_DIR="__HERMES_LEDGER_DIR__"
REPO="__HERMES_REPO_DIR__"

PROFILE="$PACK_DIR/templates/explorer-profile.yaml"
SCAR_TISSUE="$REPO/$LEDGER_DIR/redteam/objections.jsonl"
STATE_FILE="$REPO/$LEDGER_DIR/state.json"

# ── Helper: parse key: value from YAML ────────────────────────────────────────
yaml_val() {
  local key="$1"
  grep -E "^${key}:" "$PROFILE" | head -1 | sed 's/^[^:]*:[[:space:]]*//' | sed 's/[[:space:]]*$//'
}

# ── Helper: count open hypotheses from state.json ──────────────────────────────
count_open_hypotheses() {
  if [ ! -f "$STATE_FILE" ]; then
    echo 0
    return
  fi
  python -c "
import json
try:
    with open('$STATE_FILE') as f:
        s = json.load(f)
    hyps = s.get('hypotheses', s.get('open_hypotheses', []))
    if isinstance(hyps, list):
        print(sum(1 for h in hyps if h.get('status','open') in ('open','in_progress')))
    elif isinstance(hyps, dict):
        print(sum(1 for h in hyps.values() if h.get('status','open') in ('open','in_progress')))
    else:
        print(0)
except Exception:
    print(0)
"
}

# ── 1) Check profile exists ────────────────────────────────────────────────────
if [ ! -f "$PROFILE" ]; then
  echo '{"action":"none","error":"explorer-profile.yaml not found at '"$PROFILE"'"}'
  exit 1
fi

# ── 2) Read profile parameters ─────────────────────────────────────────────────
DIVERGENCE_TEMP=$(yaml_val "divergence_temp")
REFUTED_PENALTY=$(yaml_val "refuted_penalty")
BUDGET_PCT=$(yaml_val "exploration_budget_pct")
IDLE_TRIGGER=$(yaml_val "idle_trigger_hypotheses")

# Defaults if parsing failed
[ -z "$DIVERGENCE_TEMP" ] && DIVERGENCE_TEMP=1.2
[ -z "$REFUTED_PENALTY" ] && REFUTED_PENALTY=0.5
[ -z "$BUDGET_PCT" ] && BUDGET_PCT=20
[ -z "$IDLE_TRIGGER" ] && IDLE_TRIGGER=3

# ── 3) Check idle state ────────────────────────────────────────────────────────
OPEN_COUNT=$(count_open_hypotheses)
if [ "$OPEN_COUNT" -ge "$IDLE_TRIGGER" ]; then
  echo "{\"action\":\"none\",\"params\":{\"reason\":\"Not idle: ${OPEN_COUNT} open hypotheses >= ${IDLE_TRIGGER} threshold\"}}"
  exit 0
fi

# ── 4) Check scar-tissue (objections.jsonl) for refuted hypothesis families ────
# Build a comma-separated list of refuted family labels to avoid.
REFUTED_FAMILIES=""
if [ -f "$SCAR_TISSUE" ]; then
  REFUTED_FAMILIES=$(python -c "
import json
refuted = []
try:
    with open('$SCAR_TISSUE') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # An objection with BLOCK stance and severity blocking|major
            # marks a refuted direction.
            stance = (obj.get('stance') or obj.get('verdict', {})).get('stance', '')
            if not stance:
                stance = obj.get('stance', '')
            sev = obj.get('severity', '')
            if stance == 'BLOCK' and sev in ('blocking', 'major'):
                # Use claim_attacked or hypothesis_id as the family label
                fam = obj.get('claim_attacked', obj.get('hypothesis_id', ''))
                if fam:
                    refuted.append(fam)
except Exception:
    pass
print(','.join(refuted))
" 2>/dev/null)
fi

# ── 5) Determine active source types (after removing refuted families) ─────────
# Read allowed source_types from profile
SOURCE_TYPES_RAW=$(yaml_val "source_types")
# Remove brackets and split
SOURCE_TYPES=$(echo "$SOURCE_TYPES_RAW" | tr -d '[]' | tr ',' ' ' | xargs)

# If scar-tissue has a refuted family that maps to a source type, zero it out.
# Build a penalty map for each source type.
ACTIVE_SOURCES=$(python -c "
import json, sys

refuted_raw = '''${REFUTED_FAMILIES}'''
refuted_set = set(f.strip().lower() for f in refuted_raw.split(',') if f.strip())

source_types = '''${SOURCE_TYPES}'''.split()
penalty_str = '''${REFUTED_PENALTY}'''
try:
    penalty = float(penalty_str)
except ValueError:
    penalty = 0.5

active = []
for st in source_types:
    st_key = st.replace('_', '').replace('-', '').lower()
    # Check if any refuted family name contains the source type key
    blocked = any(st_key in rf for rf in refuted_set)
    if blocked and penalty <= 0.5:
        continue  # skip — heavily penalized
    active.append(st)

if not active:
    # Fallback: if all sources are refuted, use the first one anyway at
    # reduced temperature (prevent complete exploration deadlock)
    active.append(source_types[0])

print(' '.join(active))
")

# ── 6) Select source type ──────────────────────────────────────────────────────
SELECTED_SOURCE=""
for st in $ACTIVE_SOURCES; do
  SELECTED_SOURCE="$st"
  break
done
[ -z "$SELECTED_SOURCE" ] && SELECTED_SOURCE="codebase_scan"

# ── 7) Generate exploration parameters ──────────────────────────────────────────
# Use python3 to compute a tick-unique seed and apply divergence temp.
EXPLORATION_PARAMS=$(python -c "
import json, time, hashlib

div_temp = float('${DIVERGENCE_TEMP}')
ref_penalty = float('${REFUTED_PENALTY}')
budget_pct = float('${BUDGET_PCT}')
open_count = int('${OPEN_COUNT}')

# Deterministic seed from the tick timestamp
seed_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
seed = int(seed_hash, 16) % (2**31)

params = {
    'divergence_temp': div_temp,
    'refuted_penalty': ref_penalty,
    'budget_pct': budget_pct,
    'open_hypotheses': open_count,
    'source_type': '${SELECTED_SOURCE}',
    'seed': seed,
    'refuted_families': '${REFUTED_FAMILIES}',
    'active_sources': '${ACTIVE_SOURCES}',
}

print(json.dumps(params))
")

# ── 8) Output JSON ──────────────────────────────────────────────────────────────
cat <<JSON
{"action":"generate","params":${EXPLORATION_PARAMS}}
JSON
exit 0
