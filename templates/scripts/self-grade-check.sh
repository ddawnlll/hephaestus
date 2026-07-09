#!/usr/bin/env bash
# Self-grade check — $0 Gate: orchestrator optimism check.
# Verifies that orchestrator_verdict is not more optimistic than
# mechanical_verdict. Optimism ordering: FAIL < HOLD < PASS.
#
# Usage:
#   bash self-grade-check.sh <mechanical_verdict> <orchestrator_verdict>
#
# Invariant: orchestrator_verdict <= mechanical_verdict
# If orchestrator_verdict > mechanical_verdict → FAIL (block merge,
# route to Red Team or human).
#
# Output (stdout):
#   PASS: {"verdict":"PASS","orchestrator":"...","mechanical":"...","optimism_rank":{...}}
#   FAIL: {"verdict":"FAIL","orchestrator":"...","mechanical":"...","error":"..."}
# Exit code: 0=PASS, 1=FAIL

set -u

# ── Parse args ────────────────────────────────────────────────────────────────
if [ $# -lt 2 ]; then
  cat <<JSON
{"verdict":"FAIL","orchestrator":"","mechanical":"","error":"Usage: self-grade-check.sh <mechanical_verdict> <orchestrator_verdict>"}
JSON
  exit 1
fi

MECHANICAL_VERDICT="$1"
ORCHESTRATOR_VERDICT="$2"

# ── Define optimism ranks ─────────────────────────────────────────────────────
# FAIL=0, HOLD=1, PASS=2  (ascending optimism)
rank_of() {
  case "$1" in
    FAIL) echo 0 ;;
    HOLD) echo 1 ;;
    PASS) echo 2 ;;
    *) echo -1 ;;  # unknown/invalid
  esac
}

MECHANICAL_RANK=$(rank_of "$MECHANICAL_VERDICT")
ORCHESTRATOR_RANK=$(rank_of "$ORCHESTRATOR_VERDICT")

# ── Validate inputs ───────────────────────────────────────────────────────────
if [ "$MECHANICAL_RANK" -eq -1 ]; then
  echo "{\"verdict\":\"FAIL\",\"orchestrator\":\"${ORCHESTRATOR_VERDICT}\",\"mechanical\":\"${MECHANICAL_VERDICT}\",\"error\":\"Invalid mechanical_verdict '${MECHANICAL_VERDICT}'. Must be FAIL, HOLD, or PASS.\"}"
  exit 1
fi

if [ "$ORCHESTRATOR_RANK" -eq -1 ]; then
  echo "{\"verdict\":\"FAIL\",\"orchestrator\":\"${ORCHESTRATOR_VERDICT}\",\"mechanical\":\"${MECHANICAL_VERDICT}\",\"error\":\"Invalid orchestrator_verdict '${ORCHESTRATOR_VERDICT}'. Must be FAIL, HOLD, or PASS.\"}"
  exit 1
fi

# ── Check invariant ───────────────────────────────────────────────────────────
# orchestrator_verdict <= mechanical_verdict → PASS
# orchestrator_verdict > mechanical_verdict  → FAIL (orchestrator too optimistic)
if [ "$ORCHESTRATOR_RANK" -gt "$MECHANICAL_RANK" ]; then
  cat <<JSON
{"verdict":"FAIL","orchestrator":"${ORCHESTRATOR_VERDICT}","mechanical":"${MECHANICAL_VERDICT}","optimism_rank":{"orchestrator":${ORCHESTRATOR_RANK},"mechanical":${MECHANICAL_RANK}},"error":"Orchestrator verdict '${ORCHESTRATOR_VERDICT}' (rank ${ORCHESTRATOR_RANK}) is more optimistic than mechanical verdict '${MECHANICAL_VERDICT}' (rank ${MECHANICAL_RANK}). Orchestrator cannot be more optimistic than evidence."}
JSON
  exit 1
fi

# ── PASS ──────────────────────────────────────────────────────────────────────
cat <<JSON
{"verdict":"PASS","orchestrator":"${ORCHESTRATOR_VERDICT}","mechanical":"${MECHANICAL_VERDICT}","optimism_rank":{"orchestrator":${ORCHESTRATOR_RANK},"mechanical":${MECHANICAL_RANK}},"error":""}
JSON
exit 0
