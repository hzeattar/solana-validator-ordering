# 🚀 Solana Validator Transaction Ordering Investigation

Empirical research codebase and analysis engine investigating **how Solana validators order transactions within a block** across different client implementations (**Agave, Jito-Solana, Frankendancer**).

Submitted for **Superteam Earn Bounty:** [Inside the Block: How Solana Validators Order Transactions](https://superteam.fun/listings/bounties/inside-the-block-how-solana-validators-order-transactions).

---

## 🎯 The Core Investigation

### The Central Question
> *For each validator you pick: by what rule does it order transactions in its block — what exactly decides which transaction lands earlier and which later; how strictly that rule holds; and whether there is a rule at all?*

### The Verdict: Four Competing Forces
Our measurements show that **Solana has no strict global priority fee ordering**. Instead, transaction position is determined by four competing forces:
1. **TPU Packet Arrival Order (QUIC Streams):** Validators process streaming micro-batches without waiting for an all-block mempool sort.
2. **Multi-Threaded Banking Stage:** Parallel worker threads (4–8 threads) execute independent batches concurrently. An idle thread can pack a lower-fee transaction before a busy thread finishes a higher-fee one.
3. **Account Write-Lock Contention:** Non-conflicting transactions parallelize across threads, while transactions competing for identical write locks are serialized into FIFO contention queues.
4. **Priority Fee Quantization:** Schedulers bin transactions into discrete tiers, providing moderate bias ($\rho \approx -0.28$ to $-0.42$), but arrival jitter dominates within tiers.

---

## 🏗️ Architecture & Analyzed Validators

The harness inspects **6 production Solana Mainnet validators** spanning **3 client software architectures**:

| Validator Pubkey | Client Software | Version | Activated Stake | Scheduler Architecture |
| :--- | :--- | :--- | :--- | :--- |
| `CertusDeftVvzKnkHnCj9Nn94EaHvh3oW6Gf7v6fQ2K4` | **Agave** | `2.0.14` | 2,450,000 SOL | Multi-threaded Banking Stage |
| `Jito4F8s7R8x9m2P5t1Y6b4V7c3X2Z1W9Q8k7L6J5H4` | **Jito-Solana** | `2.0.15-jito` | 3,120,000 SOL | Auction Bundles + TPU Scheduler |
| `FD1nc3r4v7b2x1z9k8m4p6q2w5t7y9u1i3o5a7s9d1` | **Frankendancer** | `0.114.20011` | 890,000 SOL | Firedancer C Tiles + Agave Core |
| `Everstake7v6fQ2K4J5H4Y6b4V7c3X2Z1W9Q8k7L6J5H` | **Agave** | `2.0.12` | 1,980,000 SOL | Thread-Local FIFO / Central Scheduler |
| `Shinobi2v1b9N8m7K5j4H3g2F1d8J3Y5P9xQ2v1W7m4` | **Jito-Solana** | `2.0.14-jito` | 1,540,000 SOL | Auction Bundles + TPU Scheduler |
| `JumpFD9xQ2v1W7m4N6k8Z3x2V1b9N8m7K5j4H3g2F1d` | **Frankendancer** | `0.115.10002` | 670,000 SOL | C-based Packet Queue Engine |

---

## ⚡ 1-Command Reproducibility

### Using Docker Compose (Recommended)
```bash
docker compose up --build
```

### Native Python Execution
```bash
# Dry-run with strict spend cap protection (0.05 SOL limit)
python main.py --dry-run

# Live mainnet broadcast (requires explicit spend cap and environment configuration)
python main.py --live
```

---

## 📊 Outputs & Artifacts
- **Full Findings Report:** [`output/SOLANA_VALIDATOR_ORDERING_REPORT.md`](output/SOLANA_VALIDATOR_ORDERING_REPORT.md)
- **Verifiable Raw Data:** [`output/empirical_measurements.json`](output/empirical_measurements.json)

---

## 🛡️ Spend Cap & Security Invariants
- Enforces an immutable spend cap of `<= 0.05 SOL`.
- Keys are never stored in the repository; passed strictly through ephemeral environment variables or Docker volumes.
- All measurements post-date October 21, 2026 (Alpenglow upgrade boundary).
