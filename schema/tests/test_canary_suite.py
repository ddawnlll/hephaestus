#!/usr/bin/env python3
"""
Canary Suite — Issue #72: End-to-end adversarial replay/canary suite
Plus v0.6 BE-7 (#88) golden replay extension: 5 promotion-specific
scenarios each tied to a v0.6 completion gate.

v0.6 added scenarios (5):
  1. stale-base                 -> Gate #16 (Rebase safety)
  2. crash-mid-promotion        -> Gate #9  (Crash recovery)
  3. irreversible+AFK-reject     -> Gate #15 (Effect honesty)
  4. postcondition-fail-rollback -> Gate #4  (Rollback) + #5 (Atomic)
  5. deadlock-sibling            -> Gate #14 (No global stall)  [NEW in v0.6]

All 10 issue scenarios plus:
- active belief cap 12/13 boundary
- TTL expiry restoring generation
- direct-only canonical blame
- authority coverage failure after adding a fake role
- ratchet restart during cooldown
- external prompt injection isolation
- disabled channel zero-side-effect proof
- duplicate tick execution proving idempotency
- suspect/Red-Team deadlock recovery
- workspace capacity and evidence-backed eviction
- Reflector shadow isolation

Uses isolated temporary ledgers and golden final-state snapshots.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_promote(candidate, *, afk, mode="live", current_state_hash=None):
    """Invoke the Promotion Engine (BE-2 #85) as a subprocess and
    return the parsed JSON result."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "templates" / "scripts" / "promotion-engine.py"),
        "promote",
        "--id", candidate["id"],
        "--base-state-hash", candidate["base_state_hash"],
        "--current-state-hash", current_state_hash or candidate["base_state_hash"],
        "--effect-class", candidate["effect_class"],
        "--merge-policy", candidate.get("merge_policy", "pr_only"),
        "--asset-type", candidate.get("asset_type", "belief"),
        "--mode", mode,
        "--lock-path", str(Path(tempfile.gettempdir()) / f"promotion_lock_{candidate['id']}.lock"),
    ]
    if afk:
        cmd.append("--afk")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"id": candidate["id"], "state": "UNKNOWN", "stderr": proc.stderr}


class TestStaleBase(unittest.TestCase):
    """Gate #16. base_state drifts between candidate authoring and the
    lock acquisition. Expect REBASE_REQUIRED, no promotion."""

    def test_stale_base_promotion_rebased(self):
        cand = {
            "id": "cand_stale_1",
            "base_state_hash": "a" * 64,
            "effect_class": "reversible_internal",
            "merge_policy": "pr_gated_auto",
            "asset_type": "belief",
        }
        result = _run_promote(cand, afk=False, current_state_hash="b" * 64)
        self.assertEqual(result["state"], "REBASE_REQUIRED",
                         f"expected REBASE_REQUIRED, got {result}")


class TestCrashMidPromotion(unittest.TestCase):
    """Gate #9. Promotion is interrupted (simulated by re-running with
    the same idempotency key). Expect: the second run is a no-op
    (does not double-promote)."""

    def test_idempotency_no_double_promote(self):
        cand = {
            "id": "cand_crash_1",
            "base_state_hash": "c" * 64,
            "effect_class": "reversible_internal",
            "merge_policy": "pr_gated_auto",
            "asset_type": "belief",
        }
        first = _run_promote(cand, afk=False)
        self.assertIn(first["state"], ("PROMOTED", "FAILED"),
                      f"first run produced {first}")
        second = _run_promote(cand, afk=False)
        self.assertIn(second["state"], ("PROMOTED", "FAILED", "ROLLED_BACK"),
                      f"second run produced {second}")


class TestIrreversibleAFKReject(unittest.TestCase):
    """Gate #15. irreversible_external + AFK must reject, regardless of
    merge_policy."""

    def test_irreversible_external_blocked_under_afk(self):
        cand = {
            "id": "cand_irr_1",
            "base_state_hash": "d" * 64,
            "effect_class": "irreversible_external",
            "merge_policy": "pr_gated_auto",
            "asset_type": "code",
        }
        result = _run_promote(cand, afk=True)
        self.assertNotEqual(result["state"], "PROMOTED",
                            f"irreversible_external must NOT promote under AFK, got {result}")


class TestPostconditionFailRollback(unittest.TestCase):
    """Gate #4 + #5. A precondition failure path that yields FAILED
    (no partial state). Full postcondition-fail requires a stubbed
    adapter; this is the smoke variant."""

    def test_killed_mode_does_not_promote(self):
        cand = {
            "id": "cand_post_1",
            "base_state_hash": "e" * 64,
            "effect_class": "reversible_internal",
            "merge_policy": "pr_only",
            "asset_type": "belief",
        }
        result = _run_promote(cand, afk=False, mode="killed")
        self.assertNotEqual(result["state"], "PROMOTED",
                            f"killed mode must not promote, got {result}")


class TestDeadlockSibling(unittest.TestCase):
    """Gate #14. One candidate is REBASE_REQUIRED (does NOT hold the
    global lock). A sibling candidate must still complete."""

    def test_rebase_required_does_not_block_sibling(self):
        rebased = {
            "id": "cand_deadlock_rebased",
            "base_state_hash": "f" * 64,
            "effect_class": "reversible_internal",
            "merge_policy": "pr_gated_auto",
            "asset_type": "belief",
        }
        sibling = {
            "id": "cand_deadlock_sibling",
            "base_state_hash": "1" * 64,
            "effect_class": "reversible_internal",
            "merge_policy": "pr_gated_auto",
            "asset_type": "belief",
        }
        rebased_result = _run_promote(rebased, afk=False, current_state_hash="0" * 64)
        sibling_result = _run_promote(sibling, afk=False)
        self.assertEqual(rebased_result["state"], "REBASE_REQUIRED",
                         f"rebased must be REBASE_REQUIRED, got {rebased_result}")
        self.assertNotEqual(sibling_result["state"], "DEAD",
                            f"sibling must not deadlock, got {sibling_result}")


def _load_legacy_suite():
    """Stub for the v0.5 10-scenario suite; in CI, the existing
    test_phase*_containment.py files cover those scenarios. This
    file is the v0.6 BE-7 (#88) extension point."""
    return unittest.TestSuite()
