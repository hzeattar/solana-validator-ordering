"""
Solana Validator Ordering Analyzer - Configuration & Spend Cap Protection
"""
import os
from dataclasses import dataclass

@dataclass
class Config:
    rpc_url: str = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    backup_rpc_url: str = os.getenv("SOLANA_BACKUP_RPC_URL", "https://solana-mainnet.g.alchemy.com/v2/demo")
    spend_cap_sol: float = float(os.getenv("SPEND_CAP_SOL", "0.05"))
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
    data_dir: str = os.getenv("DATA_DIR", "./data")
    output_dir: str = os.getenv("OUTPUT_DIR", "./output")
    target_validators_count: int = 6
    min_client_versions: int = 3
    
config = Config()
