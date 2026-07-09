#!/usr/bin/env bash
# Self-grade diff — $0 Gate: deterministic mechanical verdict computation.
# Prevents the orchestrator from being more optimistic than the evidence
# supports by computing a purely mechanical verdict from hard evidence.
#
# Usage:
#   bash self-grade-diff.sh <praxis_exit_code> <evidence_bundle_status> <acceptance_criteria_met_count> <total_criteria>
#
# Evidence bundle status: PASS, FAIL, or HOLD
#
# Mechanical verdict rules (checked in order, first match wins):
#   1. praxis_exit_code == 2 (FAIL)  → mechanical = FAIL
#   2. evidence_bundle_status == FAIL → mechanical = FAIL
#   3. acceptance_criteria_met_count < total_criteria → mechanical = HOLD
#   4. Otherwise                     → mechanical = PASS
#
# Optimism ordering: FAIL < HOLD < PASS
#
# Output (stdout): {"mechanical_verdict":"PASS"|"HOLD"|"FAIL","components":{...}}
# Exit code: 0 always (computation always succeeds)

set -u

PACK_DIR="$(cd "$(dirname "$0")/../../" && pwd)"

# ── Parse args ────────────────────────────────────────────────────────────────
if [ $# -lt 4 ]; then
  cat <<JSON
{"mechanical_verdict":"FAIL","components":{"praxis_exit_code":null,"evidence_bundle_status":"missing","acceptance_criteria_met":null,"total_criteria":null,"reason":"Usage: self-grade-diff.sh <praxis_exit_code> <evidence_bundle_status> <acceptance_criteria_met_count> <total_criteria>"}}
JSON
  exit 0
fi

PRAXIS_EXIT_CODE="$1"
EVIDENCE_BUNDLE_STATUS="$2"
ACCEPTANCE_MET="$3"
TOTAL_CRITERIA="$4"

# ── Compute mechanical verdict ────────────────────────────────────────────────
# Rules evaluated in priority order; first match wins.
MECHANICAL="PASS"
REASON=""

# Rule 1: praxis_exit_code 2 means Praxis FAIL
# Note: 0=PASS, 1=HOLD, 2=FAIL
# Both string "2" and bare 2 are handled.
PRAXIS_FAIL=0
if [ "$PRAXIS_EXIT_CODE" = "2" ]; then
  PRAXIS_FAIL=1
elif [ "$PRAXIS_EXIT_CODE" = "" ]; then
  # Empty exit code is treated as error → FAIL
  MECHANICAL="FAIL"
  REASON="praxis_exit_code is empty (missing Praxis result)"
fi

if [ "$PRAXIS_FAIL" = "1" ]; then
  MECHANICAL="FAIL"
  REASON="praxis_exit_code=2 (Praxis FAIL)"
fi

# Rule 2: evidence_bundle_status == FAIL (checked regardless of Rule 1 status
# to include both reasons, but verdict stays FAIL either way)
if [ "$EVIDENCE_BUNDLE_STATUS" = "FAIL" ]; then
  MECHANICAL="FAIL"
  if [ -n "$REASON" ]; then
    REASON="${REASON}; evidence_bundle_status=FAIL"
  else
    REASON="evidence_bundle_status=FAIL"
  fi
fi

# Rule 3: acceptance criteria not fully met → HOLD
# Only applies if we haven't already reached FAIL
if [ "$MECHANICAL" = "PASS" ]; then
  # Use integer comparison; silently treat non-numeric as "not less than"
  if [ "$ACCEPTANCE_MET" -lt "$TOTAL_CRITERIA" ] 2>/dev/null; then
    MECHANICAL="HOLD"
    REASON="acceptance_criteria_met (${ACCEPTANCE_MET}/${TOTAL_CRITERIA}) < total_criteria (${TOTAL_CRITERIA})"
  fi
fi

# Rule 4: Otherwise → PASS (set reason if nothing triggered above)
if [ "$MECHANICAL" = "PASS" ] && [ -z "$REASON" ]; then
  REASON="all checks passed (praxis_exit_code=${PRAXIS_EXIT_CODE}, evidence_bundle_status=${EVIDENCE_BUNDLE_STATUS}, acceptance_criteria_met=${ACCEPTANCE_MET}/${TOTAL_CRITERIA})"
fi

# ── Build components object ───────────────────────────────────────────────────
COMPONENTS="{\"praxis_exit_code\":${PRAXIS_EXIT_CODE},\"evidence_bundle_status\":\"${EVIDENCE_BUNDLE_STATUS}\",\"acceptance_criteria_met\":${ACCEPTANCE_MET},\"total_criteria\":${TOTAL_CRITERIA},\"reason\":\"${REASON}\"}"

# ── Output ────────────────────────────────────────────────────────────────────
cat <<JSON
{"mechanical_verdict":"${MECHANICAL}","components":${COMPONENTS}}
JSON
exit 0
