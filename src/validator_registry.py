"""
Validator Registry - Discovers and Categorizes Mainnet Validators by Client Version
"""
import urllib.request
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ValidatorRegistry")

class ValidatorRegistry:
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
            headers={"Content-Type": "application/json", "User-Agent": "SolanaValidatorAnalyzer/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(f"RPC Error {data['error']}")
            return data.get("result")

    def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        return self._rpc_call("getClusterNodes")

    def get_vote_accounts(self) -> Dict[str, Any]:
        return self._rpc_call("getVoteAccounts")

    def discover_target_validators(self, min_versions: int = 3) -> List[Dict[str, Any]]:
        """
        Discovers active validators across distinct client versions:
        e.g., Agave (v2.0.x), Jito-Solana (v2.0.x-jito), Firedancer/Frankendancer (v0.1.x)
        """
        nodes = self.get_cluster_nodes()
        votes = self.get_vote_accounts()
        
        node_map = {n.get("pubkey"): n for n in nodes if n.get("pubkey")}
        
        current_validators = votes.get("current", [])
        
        version_buckets: Dict[str, List[Dict[str, Any]]] = {}
        
        for val in current_validators:
            node_pubkey = val.get("nodePubkey")
            node_info = node_map.get(node_pubkey, {})
            version = node_info.get("version", "unknown")
            activated_stake = val.get("activatedStake", 0)
            
            # Categorize client type
            client_type = "Agave"
            if "jito" in version.lower() or "jito" in node_info.get("tpu", ""):
                client_type = "Jito-Solana"
            elif "fd" in version.lower() or "firedancer" in version.lower() or version.startswith("0.1"):
                client_type = "Frankendancer"
            elif version.startswith("2.") or version.startswith("1.18"):
                client_type = f"Agave-{version[:4]}"
            else:
                client_type = f"Other-{version}"
                
            entry = {
                "votePubkey": val.get("votePubkey"),
                "nodePubkey": node_pubkey,
                "version": version,
                "clientType": client_type,
                "activatedStakeSol": activated_stake / 1e9,
                "tpu": node_info.get("tpu"),
                "rpc": node_info.get("rpc")
            }
            
            version_buckets.setdefault(client_type, []).append(entry)
            
        # Select representative top validators from each version bucket
        selected = []
        for client_type, vals in sorted(version_buckets.items()):
            vals.sort(key=lambda x: x["activatedStakeSol"], reverse=True)
            if vals:
                selected.append(vals[0]) # top stake in this bucket
                if len(vals) > 1 and len(selected) < 6:
                    selected.append(vals[1])
                    
        return selected[:6]
