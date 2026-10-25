"""
Probe Sender - Controlled Transaction Emission with Strict Spend Cap & Dry-Run Enforcement
"""
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ProbeSender")

class ProbeSender:
    def __init__(self, rpc_url: str, spend_cap_sol: float = 0.05, dry_run: bool = True):
        self.rpc_url = rpc_url
        self.spend_cap_sol = spend_cap_sol
        self.dry_run = dry_run
        self.total_spent_sol = 0.0
        self.records: List[Dict[str, Any]] = []

    def can_spend(self, amount_sol: float) -> bool:
        return (self.total_spent_sol + amount_sol) <= self.spend_cap_sol

    def simulate_or_send_probes(self, target_slot: int, validator_pubkey: str, count: int = 4) -> List[Dict[str, Any]]:
        """
        Creates synthetic or simulated micro-transactions targeted at a specific validator slot window.
        Enforces dry-run safety and strict spend cap.
        """
        results = []
        fee_per_tx_sol = 0.000005 # 5,000 lamports base

        for i in range(count):
            prio_micro_lamports = (i + 1) * 1000 # increasing priority fee
            estimated_cost_sol = fee_per_tx_sol + (prio_micro_lamports * 200_000 / 1e15)

            if not self.can_spend(estimated_cost_sol):
                logger.warning(f"Spend cap reached: {self.total_spent_sol:.6f} SOL. Aborting further probes.")
                break

            record = {
                "target_slot": target_slot,
                "validator_pubkey": validator_pubkey,
                "probe_index": i,
                "priority_micro_lamports": prio_micro_lamports,
                "estimated_cost_sol": estimated_cost_sol,
                "mode": "DRY_RUN (Simulated)" if self.dry_run else "LIVE_MAINNET",
                "signature": f"sim_sig_{target_slot}_{i}_{validator_pubkey[:8]}" if self.dry_run else None,
                "status": "simulated" if self.dry_run else "pending"
            }

            if not self.dry_run:
                # In real sending mode (when authorized with PRIVATE_KEY env var)
                # would sign and send via sendTransaction RPC
                self.total_spent_sol += estimated_cost_sol
            else:
                # Dry run does not consume SOL
                pass

            results.append(record)
            self.records.append(record)

        return results
