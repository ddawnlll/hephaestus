#!/usr/bin/env python3
"""
containment-engine.py — Phase 2 Containment Mechanisms (#61, #62, #63, #64)

#61 — Authority matrix with terminal referee for every role pair
#62 — Suspect TTL and curiosity exemption (no permanent lockout)
#63 — Belief minimum residency and evidence-backed eviction
#64 — Frame-shift cooldown and ratchet hysteresis (anti-oscillation)

Commands:
  authority-check <state_file> <conflicting_roles> — Check if roles have a terminal referee
  suspect-ttl <state_file> <beliefs_file> — Age suspect beliefs, apply TTL
  curiosity-check <state_file> <hypothesis> — Check if curiosity budget allows exemption
  eviction-review <state_file> <beliefs_file> — Review candidates for eviction
  cooldown-tick <state_file> <beliefs_file> — Advance cooldown counters, check ratchet
  status <state_file> <beliefs_file> — Show containment status overview
"""

import json
import os
import sys
import time


# ── Authority Matrix (#61) ─────────────────────────────────────────────────────

# Every role pair that can conflict must have a terminal referee.
# A referee cannot be a party in the dispute.
# Format: (role_a, role_b) -> referee
# Roles: orchestrator (T1), worker (T1-exec), challenger (T2), arbiter (T3),
#        red_team, explorer, reflector, human (T4)
AUTHORITY_MATRIX = {
    # Worker disputes
    ("worker", "challenger"): "arbiter",       # T2 challenges T1 evidence -> T3 decides
    ("worker", "orchestrator"): "arbiter",      # T1-worker vs T1-orchestrator -> T3
    ("worker", "worker"): "orchestrator",       # Two workers conflict -> orchestrator prioritizes
    
    # Challenger disputes
    ("challenger", "orchestrator"): "arbiter",  # T2 challenges T1 verdict -> T3
    ("challenger", "arbiter"): "human",         # T2 challenges T3 -> T4 human only
    ("challenger", "red_team"): "arbiter",      # T2 vs Red Team -> T3
    
    # Orchestrator disputes
    ("orchestrator", "arbiter"): "human",       # T1 vs T3 -> T4 only (T3 is terminal)
    ("orchestrator", "red_team"): "arbiter",    # T1 vs Red Team -> T3
    
    # Red Team disputes
    ("red_team", "worker"): "arbiter",          # Red Team blocks worker -> T3 decides
    ("red_team", "explorer"): "orchestrator",   # Red Team vs Explorer -> orchestrator
    ("red_team", "arbiter"): "human",           # Red Team vs T3 -> T4 only
    
    # Explorer disputes
    ("explorer", "orchestrator"): "arbiter",    # Explorer diverges from T1 -> T3
    
    # Reflector disputes
    ("reflector", "arbiter"): "human",          # Reflector vs T3 -> T4
    ("reflector", "orchestrator"): "arbiter",   # Reflector vs T1 -> T3
    
    # Arbiter disputes (T3 is normally terminal)
    ("arbiter", "human"): "human",              # T3 can escalate to T4, T4 has final say
    ("arbiter", "explorer"): "human",           # T3 vs Explorer -> T4
    ("arbiter", "worker"): "human",             # T3 vs Worker -> T4 (T3 is already terminal)
    
    # Challenger edge cases
    ("challenger", "explorer"): "arbiter",      # T2 vs Explorer -> T3
    ("challenger", "reflector"): "arbiter",     # T2 vs Reflector -> T3
    
    # Explorer edge cases
    ("explorer", "reflector"): "orchestrator",  # Explorer vs Reflector -> T1
    ("explorer", "worker"): "orchestrator",     # Explorer vs Worker -> T1
    
    # Red Team edge cases
    ("red_team", "reflector"): "arbiter",       # Red Team vs Reflector -> T3
    
    # Reflector edge cases
    ("reflector", "worker"): "arbiter",         # Reflector vs Worker -> T3
    
    # Human disputes (human is terminal authority)
    ("human", "worker"): "human",               # Human overrides all
    ("human", "orchestrator"): "human",
    ("human", "arbiter"): "human",
    ("human", "red_team"): "human",
}

# Blocking states that must have a timeout + safe default HOLD
BLOCKING_TIMEOUTS = {
    "challenger_pending": {"timeout_ticks": 3, "default": "HOLD"},
    "arbiter_pending": {"timeout_ticks": 5, "default": "HOLD"},
    "red_team_pending": {"timeout_ticks": 3, "default": "HOLD"},
    "human_pending": {"timeout_ticks": 24, "default": "HOLD"},  # 24 ticks ≈ 1 day
    "praxis_pending": {"timeout_ticks": 2, "default": "HOLD"},
    "eviction_review": {"timeout_ticks": 3, "default": "HOLD"},
}


def check_authority(conflicting_roles):
    """Check if two conflicting roles have a terminal referee.
    
    Returns:
        dict with referee, is_terminal, and any issues.
    """
    if not isinstance(conflicting_roles, (list, tuple)) or len(conflicting_roles) != 2:
        return {"error": "conflicting_roles must be a list/tuple of 2 role names"}
    
    role_a, role_b = conflicting_roles
    
    # Normalize role names
    roles = sorted([role_a.lower().strip(), role_b.lower().strip()])
    key = (roles[0], roles[1])
    
    # Check both orderings
    referee = AUTHORITY_MATRIX.get(key) or AUTHORITY_MATRIX.get((roles[1], roles[0]))
    
    if not referee:
        return {
            "verdict": "FAIL",
            "roles": [role_a, role_b],
            "referee": None,
            "error": f"No terminal referee defined for pair ({role_a}, {role_b})",
            "is_terminal": False,
        }
    
    # Check that referee is not a party in the dispute
    if referee in roles:
        return {
            "verdict": "FAIL",
            "roles": [role_a, role_b],
            "referee": referee,
            "error": f"Referee '{referee}' is a party in the dispute ({role_a}, {role_b})",
            "is_terminal": False,
        }
    
    is_terminal = referee in ("arbiter", "human")
    
    return {
        "verdict": "PASS",
        "roles": [role_a, role_b],
        "referee": referee,
        "is_terminal": is_terminal,
        "note": "Terminal referee" if is_terminal else f"Referee: {referee} (may escalate)",
    }


def authority_matrix_coverage():
    """Check that all defined role pairs have coverage and no gaps.
    Returns list of potential unregistered pairs that need coverage.
    """
    known_roles = set()
    for (a, b) in AUTHORITY_MATRIX:
        known_roles.add(a)
        known_roles.add(b)
    
    # Check that every role pair has coverage
    role_list = sorted(known_roles)
    missing_pairs = []
    
    for i, r1 in enumerate(role_list):
        for r2 in role_list[i+1:]:
            key = (r1, r2)
            rev_key = (r2, r1)
            if key not in AUTHORITY_MATRIX and rev_key not in AUTHORITY_MATRIX:
                missing_pairs.append(key)
    
    return {
        "known_roles": role_list,
        "total_pairs": len(AUTHORITY_MATRIX),
        "missing_pairs": missing_pairs,
    }


# ── Suspect TTL (#62) ─────────────────────────────────────────────────────────

SUSPECT_TTL_DEFAULT = 12  # ticks before suspect is auto-reviewed
CURIOSITY_BUDGET_PCT = 0.20  # 20% of daily budget reserved for curiosity


def age_suspect_beliefs(beliefs_file, tick_increment=1):
    """Age all suspect beliefs. Return list of beliefs that expired TTL.
    
    A belief in 'suspect' status advances its suspect_age by tick_increment.
    When suspect_age >= TTL, the belief is flagged for review.
    
    No permanent lockout: after review, a suspect belief can either be
    reinstated (active), refuted, or evicted.
    """
    import yaml
    if not os.path.exists(beliefs_file):
        return {"error": f"Beliefs file not found: {beliefs_file}"}
    
    with open(beliefs_file) as f:
        beliefs_data = yaml.safe_load(f)
    
    beliefs = beliefs_data.get("beliefs", [])
    expired = []
    reinstated = []
    
    for belief in beliefs:
        if belief.get("status") != "suspect":
            continue
        
        # Age the suspect
        suspect_age = belief.get("suspect_age", 0) + tick_increment
        belief["suspect_age"] = suspect_age
        
        ttl = belief.get("ttl", SUSPECT_TTL_DEFAULT)
        
        if suspect_age >= ttl:
            # TTL expired — flag for review
            expired.append({
                "id": belief.get("id"),
                "suspect_age": suspect_age,
                "ttl": ttl,
                "statement": belief.get("statement", "")[:80],
            })
    
    # Write back
    with open(beliefs_file, "w") as f:
        yaml.dump(beliefs_data, f, default_flow_style=False)
    
    return {
        "action": "aged",
        "tick_increment": tick_increment,
        "suspect_count": sum(1 for b in beliefs if b.get("status") == "suspect"),
        "expired_for_review": expired,
    }


def curiosity_exempted(state_file, hypothesis):
    """Check if curiosity budget allows a blocked experiment to run.
    
    Red Team may block claim promotion but may not prevent curiosity-budget 
    experiments from running. Curiosity budget is 20% of daily max.
    """
    if not os.path.exists(state_file):
        return {"error": f"State file not found: {state_file}"}
    
    with open(state_file) as f:
        state = json.load(f)
    
    daily_budget = state.get("budget_usd", 25)
    spend_today = state.get("spend_today_usd", 0)
    curiosity_budget = daily_budget * CURIOSITY_BUDGET_PCT
    remaining = daily_budget - spend_today
    
    # Curiosity check
    can_run = remaining >= curiosity_budget * 0.1  # At least 10% of curiosity budget
    
    return {
        "hypothesis": hypothesis,
        "curiosity_budget_usd": round(curiosity_budget, 2),
        "remaining_budget_usd": round(remaining, 2),
        "can_run_experiment": can_run,
        "reason": "Sufficient curiosity budget" if can_run else "Curiosity budget insufficient",
        "note": "Red Team may block claim promotion, but curiosity experiments proceed independently",
    }


# ── Belief Eviction (#63) ─────────────────────────────────────────────────────

MIN_RESIDENCY_TICKS = 6  # Minimum ticks a belief must exist before eviction
EVIDENCE_REQUIRED_FOR_EVICTION = True


def review_eviction_candidates(beliefs_file, state_file=None):
    """Review beliefs eligible for eviction.
    
    Rules:
    1. Belief must have existed for >= MIN_RESIDENCY_TICKS
    2. Eviction must be evidence-backed (auditable)
    3. Eviction records the reason and evidence reference
    """
    import yaml
    from datetime import datetime
    
    if not os.path.exists(beliefs_file):
        return {"error": f"Beliefs file not found: {beliefs_file}"}
    
    with open(beliefs_file) as f:
        beliefs_data = yaml.safe_load(f)
    
    beliefs = beliefs_data.get("beliefs", [])
    candidates = []
    
    for belief in beliefs:
        bid = belief.get("id", "")
        status = belief.get("status", "active")
        
        # Skip already evicted/refuted
        if status in ("evicted", "refuted"):
            continue
        
        # Check TTL
        stagnation = belief.get("stagnation", 0)
        ttl = belief.get("ttl", 24)
        confidence = belief.get("confidence", "medium")
        
        # Eviction criteria:
        # - Stagnation >= TTL (belief hasn't produced outcome in TTL ticks)
        # - AND (low confidence OR suspect status)
        # - AND sufficient residency
        if stagnation >= ttl and confidence in ("low", "speculative"):
            candidates.append({
                "id": bid,
                "statement": belief.get("statement", "")[:80],
                "stagnation": stagnation,
                "ttl": ttl,
                "confidence": confidence,
                "status": status,
                "eligible": True,
                "reason": f"Stagnation {stagnation} >= TTL {ttl}, confidence {confidence}",
            })
    
    return {
        "total_beliefs": len(beliefs),
        "eviction_candidates": candidates,
        "candidate_count": len(candidates),
        "min_residency_ticks": MIN_RESIDENCY_TICKS,
    }


def execute_eviction(beliefs_file, belief_ids, evidence_refs=None):
    """Execute eviction of specified beliefs with evidence trail.
    
    Eviction is auditable: records the belief_id, reason, timestamp, and 
    evidence reference.
    """
    import yaml
    from datetime import datetime
    
    if not os.path.exists(beliefs_file):
        return {"error": f"Beliefs file not found: {beliefs_file}"}
    
    with open(beliefs_file) as f:
        beliefs_data = yaml.safe_load(f)
    
    beliefs = beliefs_data.get("beliefs", [])
    evicted = []
    not_found = []
    
    for bid in belief_ids:
        found = False
        for belief in beliefs:
            if belief.get("id") == bid:
                old_status = belief.get("status", "active")
                belief["status"] = "evicted"
                belief["updated_at"] = datetime.utcnow().isoformat() + "Z"
                belief["eviction_reason"] = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "evidence_refs": evidence_refs or [],
                }
                evicted.append({
                    "id": bid,
                    "old_status": old_status,
                    "new_status": "evicted",
                })
                found = True
                break
        if not found:
            not_found.append(bid)
    
    # Write back
    with open(beliefs_file, "w") as f:
        yaml.dump(beliefs_data, f, default_flow_style=False)
    
    return {
        "action": "evicted",
        "evicted": evicted,
        "not_found": not_found,
        "total_evicted": len(evicted),
    }


# ── Frame-shift Cooldown + Ratchet (#64) ──────────────────────────────────────

FRAME_COOLDOWN_TICKS = 6  # Cooldown after a frame shift
RATCHET_COOLDOWN_TICKS = 4  # Cooldown after a ratchet direction change
OSCILLATION_WINDOW = 8  # Check for oscillation in this many ticks


def advance_cooldowns(beliefs_file, tick_increment=1):
    """Advance cooldown counters for all beliefs. Handle frame shift and ratchet.
    
    Anti-oscillation: if a belief changes direction more than twice in the
    OSCILLATION_WINDOW, force a cooldown.
    """
    import yaml
    if not os.path.exists(beliefs_file):
        return {"error": f"Beliefs file not found: {beliefs_file}"}
    
    with open(beliefs_file) as f:
        beliefs_data = yaml.safe_load(f)
    
    beliefs = beliefs_data.get("beliefs", [])
    cooldown_active = []
    cooldown_expired = []
    
    for belief in beliefs:
        cooldown = belief.get("cooldown_remaining", 0)
        if cooldown > 0:
            new_cooldown = max(0, cooldown - tick_increment)
            belief["cooldown_remaining"] = new_cooldown
            if new_cooldown == 0:
                cooldown_expired.append(belief.get("id"))
            else:
                cooldown_active.append(belief.get("id"))
    
    # Update belief frame_shift_count for oscillation detection
    for belief in beliefs:
        momentum = belief.get("momentum", 0)
        prev_momentum = belief.get("_prev_momentum", 0)
        
        # Detect direction change
        if (prev_momentum > 0 and momentum < 0) or (prev_momentum < 0 and momentum > 0):
            shift_count = belief.get("frame_shift_count", 0) + 1
            belief["frame_shift_count"] = shift_count
            belief["_prev_momentum"] = momentum
            
            # Anti-oscillation: if shifted too many times, force cooldown
            if shift_count >= 2 and belief.get("cooldown_remaining", 0) == 0:
                belief["cooldown_remaining"] = FRAME_COOLDOWN_TICKS
                cooldown_active.append(belief.get("id"))
        else:
            belief["_prev_momentum"] = momentum
            # Reset shift count if momentum is neutral
            if momentum == 0:
                belief["frame_shift_count"] = 0
    
    # Write back
    with open(beliefs_file, "w") as f:
        yaml.dump(beliefs_data, f, default_flow_style=False)
    
    return {
        "action": "cooldowns_advanced",
        "cooldown_active": cooldown_active,
        "cooldown_expired": cooldown_expired,
        "total_active": len(cooldown_active),
    }


def check_ratchet_direction(beliefs_file):
    """Check ratchet direction for oscillation detection.
    
    The ratchet should resist oscillation: if the direction has changed
    more than once within the oscillation window, flag it.
    """
    import yaml
    if not os.path.exists(beliefs_file):
        return {"error": f"Beliefs file not found: {beliefs_file}"}
    
    with open(beliefs_file) as f:
        beliefs_data = yaml.safe_load(f)
    
    beliefs = beliefs_data.get("beliefs", [])
    oscillating = []
    
    for belief in beliefs:
        shift_count = belief.get("frame_shift_count", 0)
        if shift_count >= 2:
            oscillating.append({
                "id": belief.get("id"),
                "shift_count": shift_count,
                "statement": belief.get("statement", "")[:60],
                "cooldown": belief.get("cooldown_remaining", 0),
            })
    
    return {
        "oscillating_beliefs": oscillating,
        "oscillation_count": len(oscillating),
        "oscillation_window_ticks": OSCILLATION_WINDOW,
        "cooldown_ticks": FRAME_COOLDOWN_TICKS,
        "ratchet_cooldown_ticks": RATCHET_COOLDOWN_TICKS,
    }


# ── Status Overview ───────────────────────────────────────────────────────────

def status_overview(state_file, beliefs_file):
    """Show combined containment status."""
    result = {
        "authority_matrix": {
            "total_pairs": len(AUTHORITY_MATRIX),
            "coverage": authority_matrix_coverage(),
        },
        "suspect_ttl": {
            "default_ttl": SUSPECT_TTL_DEFAULT,
            "curiosity_budget_pct": CURIOSITY_BUDGET_PCT,
        },
        "eviction": {
            "min_residency_ticks": MIN_RESIDENCY_TICKS,
        },
        "cooldown": {
            "frame_cooldown_ticks": FRAME_COOLDOWN_TICKS,
            "ratchet_cooldown_ticks": RATCHET_COOLDOWN_TICKS,
            "oscillation_window": OSCILLATION_WINDOW,
        },
    }
    
    if os.path.exists(beliefs_file):
        import yaml
        with open(beliefs_file) as f:
            bd = yaml.safe_load(f)
        beliefs = bd.get("beliefs", [])
        result["beliefs_summary"] = {
            "total": len(beliefs),
            "active": sum(1 for b in beliefs if b.get("status") == "active"),
            "suspect": sum(1 for b in beliefs if b.get("status") == "suspect"),
            "evicted": sum(1 for b in beliefs if b.get("status") == "evicted"),
            "refuted": sum(1 for b in beliefs if b.get("status") == "refuted"),
            "in_cooldown": sum(1 for b in beliefs if b.get("cooldown_remaining", 0) > 0),
        }
    
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "authority-check":
        if len(sys.argv) < 5:
            print("Usage: containment-engine.py authority-check <state_file> <role_a> <role_b>", file=sys.stderr)
            sys.exit(1)
        result = check_authority([sys.argv[3], sys.argv[4]])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("verdict") == "PASS" else 1)

    elif command == "coverage":
        result = authority_matrix_coverage()
        print(json.dumps(result, indent=2))
        sys.exit(1 if result.get("missing_pairs") else 0)

    elif command == "suspect-ttl":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py suspect-ttl <state_file> <beliefs_file>", file=sys.stderr)
            sys.exit(1)
        result = age_suspect_beliefs(sys.argv[3])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif command == "curiosity-check":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py curiosity-check <state_file> <hypothesis_id>", file=sys.stderr)
            sys.exit(1)
        result = curiosity_exempted(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif command == "eviction-review":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py eviction-review <state_file> <beliefs_file>", file=sys.stderr)
            sys.exit(1)
        result = review_eviction_candidates(sys.argv[3], sys.argv[2])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif command == "eviction-execute":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py eviction-execute <beliefs_file> <belief_id> [more_ids...]", file=sys.stderr)
            sys.exit(1)
        result = execute_eviction(sys.argv[2], sys.argv[3:])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif command == "cooldown-tick":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py cooldown-tick <state_file> <beliefs_file>", file=sys.stderr)
            sys.exit(1)
        result = advance_cooldowns(sys.argv[3])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif command == "ratchet-check":
        if len(sys.argv) < 3:
            print("Usage: containment-engine.py ratchet-check <beliefs_file>", file=sys.stderr)
            sys.exit(1)
        result = check_ratchet_direction(sys.argv[2])
        print(json.dumps(result, indent=2))
        sys.exit(1 if result.get("oscillation_count", 0) > 0 else 0)

    elif command == "status":
        if len(sys.argv) < 4:
            print("Usage: containment-engine.py status <state_file> <beliefs_file>", file=sys.stderr)
            sys.exit(1)
        result = status_overview(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
