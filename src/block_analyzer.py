"""
Block Analyzer - Measures Empirical Transaction Ordering Rules within Blocks
"""
import urllib.request
import json
import logging
import math
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("BlockAnalyzer")

class BlockAnalyzer:
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url

    def _rpc_call(self, method: str, params: list = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        req = urllib.request.Request(
            self.rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SolanaBlockAnalyzer/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(f"RPC Error {data['error']}")
            return data.get("result")

    def fetch_block(self, slot: int) -> Dict[str, Any]:
        """
        Fetches full block with transaction details and compute unit consumption.
        """
        params = [
            slot,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False
            }
        ]
        return self._rpc_call("getBlock", params)

    def extract_priority_fee(self, tx: Dict[str, Any]) -> int:
        """
        Extracts priority fee (micro-lamports per compute unit) from ComputeBudget instruction.
        """
        try:
            message = tx.get("transaction", {}).get("message", {})
            instructions = message.get("instructions", [])
            for ix in instructions:
                # ComputeBudgetProgram: ComputeBudget111111111111111111111111111111
                prog_id = ix.get("programId")
                data = ix.get("data", "")
                # If decoded instruction
                parsed = ix.get("parsed")
                if parsed and isinstance(parsed, dict):
                    if parsed.get("type") == "setComputeUnitPrice":
                        return int(parsed.get("info", {}).get("microLamports", 0))
        except Exception:
            pass
        return 0

    def analyze_block_ordering(self, block: Dict[str, Any], leader_pubkey: str = None) -> Dict[str, Any]:
        """
        Calculates correlation between priority fee, arrival order proxy, and block index.
        """
        transactions = block.get("transactions", [])
        total_txs = len(transactions)
        if total_txs == 0:
            return {"total_txs": 0, "status": "empty_block"}

        indexed_txs = []
        for idx, tx in enumerate(transactions):
            meta = tx.get("meta", {})
            err = meta.get("err")
            fee = meta.get("fee", 5000)
            compute_units = meta.get("computeUnitsConsumed", 0)
            priority_fee = self.extract_priority_fee(tx)
            
            # Extract account keys for lock collision tracking
            account_keys = []
            msg = tx.get("transaction", {}).get("message", {})
            if isinstance(msg.get("accountKeys"), list):
                for k in msg.get("accountKeys"):
                    if isinstance(k, str):
                        account_keys.append(k)
                    elif isinstance(k, dict):
                        account_keys.append(k.get("pubkey", ""))
                        
            indexed_txs.append({
                "block_index": idx,
                "fee": fee,
                "priority_fee": priority_fee,
                "compute_units": compute_units,
                "is_successful": err is None,
                "account_keys": account_keys[:3] # sample write locks
            })

        # Calculate Rank Correlation (Spearman's Rho between priority fee and block_index)
        # Note: If priority fee strictly determines order, higher priority fee -> lower block_index (negative correlation)
        pf_list = [x["priority_fee"] for x in indexed_txs]
        idx_list = [x["block_index"] for x in indexed_txs]
        
        spearman_rho = self._calculate_spearman(pf_list, idx_list)
        
        # Check non-zero priority fee sub-population
        prio_sub = [x for x in indexed_txs if x["priority_fee"] > 0]
        prio_rho = 0.0
        if len(prio_sub) > 5:
            prio_rho = self._calculate_spearman(
                [x["priority_fee"] for x in prio_sub],
                [x["block_index"] for x in prio_sub]
            )

        return {
            "slot": block.get("parentSlot", 0) + 1,
            "blockhash": block.get("blockhash"),
            "block_time": block.get("blockTime"),
            "total_transactions": total_txs,
            "priority_tx_count": len(prio_sub),
            "priority_ratio": len(prio_sub) / max(1, total_txs),
            "spearman_rho_all": spearman_rho,
            "spearman_rho_priority_only": prio_rho,
            "ordering_verdict": self._classify_ordering_verdict(prio_rho, len(prio_sub))
        }

    def _calculate_spearman(self, x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        # Compute ranks
        rx = self._get_ranks(x)
        ry = self._get_ranks(y)
        d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
        rho = 1.0 - (6.0 * d_sq) / (n * (n * n - 1))
        return round(rho, 4)

    def _get_ranks(self, data: List[float]) -> List[float]:
        sorted_indices = sorted(range(len(data)), key=lambda i: data[i])
        ranks = [0.0] * len(data)
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = float(rank + 1)
        return ranks

    def _classify_ordering_verdict(self, prio_rho: float, sample_size: int) -> str:
        if sample_size < 5:
            return "insufficient_priority_traffic (sparse)"
        if prio_rho < -0.4:
            return "strong_priority_fee_ordering (higher fee lands first)"
        elif -0.4 <= prio_rho <= -0.15:
            return "moderate_priority_ordering_with_tpu_arrival_jitter"
        elif -0.15 < prio_rho < 0.15:
            return "fifo_or_arrival_dominated (priority fee weakly affects slot position)"
        else:
            return "noise_or_parallel_banking_threads"
