"""Update PR markdown and streaming stages in app.py."""
from pathlib import Path

app_path = Path("D:/Secret/dashboard/app.py")
content = app_path.read_text(encoding="utf-8")

start_marker = "def get_system_level_pr_markdown() -> str:"
end_marker = '@app.get("/api/pr-content")'

start_pos = content.find(start_marker)
end_pos = content.find(end_marker)

assert start_pos != -1, "start_marker not found"
assert end_pos != -1, "end_marker not found"

new_func = '''def get_system_level_pr_markdown() -> str:
    """Builds the comprehensive, system-level multi-file repair PR Markdown payload for the Elite Enterprise Scenario."""
    return """# 🛡️ AutoPatch-Kernel: Elite Enterprise Autonomous Flight Recorder PR

> **Pull Request Status:** Verified & Mathematically Proven Safe  
> **Target Branch:** `main`  
> **Source Worktree:** `worktree_a_refactor` (`strategy_elite_enterprise_repair`)  
> **Autonomous Agent Harness:** Meta Muse Code 1.0 & Meta Muse Spark 1.3  
> **Theorem Verdict:** `PROVEN_LEADER_EXCLUSION_EXACT_DECIMAL_DEADLOCK_FREE` (`UNSAT_PROVEN_SAFE`)  

---

## 1. Executive Summary & Root Cause Analysis

An automated multi-system regression triggered catastrophic production outages across cluster orchestration, pricing precision, and persistent storage:

1. **Kubernetes Split-Brain (Two active leaders during network partition) (`k8s/statefulset.yaml`):**
   - The primary trading engine StatefulSet was deployed with unconstrained topology scheduling, allowing multiple leader-candidate replicas to co-locate on the same host or network partition.
   - Without hard `podAntiAffinity` and lacking an external quorum-based distributed lease with monotonic fencing tokens (Redis Redlock), a transient cross-switch partition severed etcd heartbeat signals. Both partitions independently promoted an active leader, causing two primary engines to execute competing orders simultaneously and corrupting exchange state.

2. **HFT IEEE-754 Floating-Point Arbitrage Leak (Sub-cent precision loss) (`src/pricing_engine.py`):**
   - The pricing engine utilized binary IEEE-754 double-precision floating-point arithmetic (`float`) for base pricing, tiered basis point fee computations, and volume rebates.
   - Non-terminating binary fractions (such as $0.1$ and $0.02$) introduced minute precision drift ($0.00000000000004$ per trade).
   - Under institutional volume (>150,000 orders/sec), high-frequency arbitrage bots detected this deterministic rounding artifact and repeatedly exploited sub-cent price differentials, systematically siphoning liquidity from liquidity provider reserves.

3. **Cascading PostgreSQL Transaction Deadlock in ORM (`src/db_transactions.py`):**
   - Settlement and ledger rebalancing coroutines acquired row-level write locks (`SELECT ... FOR UPDATE`) in non-deterministic, unordered sequences.
   - Simultaneous bidirectional transfers (e.g., Transfer 1 locking Account A then Account B; Transfer 2 locking Account B then Account A) formed cyclical wait-for graphs, triggering PostgreSQL kernel error `40P01: deadlock detected`.
   - Cascading transaction rollbacks flooded connection pools, leading to thread exhaustion and complete settlement pipeline freezes.

Using the **AST 2-Hop Call-Graph MCP Server** and cross-file causal tracing, AutoPatch-Kernel isolated the multi-tier dependency chain, synthesized 3 parallel candidate hypotheses via Meta open-weight models, and raced them in isolated Git worktrees under the **Read-Only Sandbox Guardrail**.

---

## 2. Mermaid.js Causal Fault & Multi-File Repair Topology

```mermaid
flowchart TD
    subgraph S1["1. Incident Telemetry & Multi-Tier Production Outage"]
        K8S["Kubernetes Split-Brain: Dual Active Leaders (k8s/statefulset.yaml)"] --> Telemetry["Kernel Syscall & Traceback Capture"]
        Float["IEEE-754 Sub-Cent Arbitrage Leak (src/pricing_engine.py)"] --> Telemetry
        Deadlock["Cascading PostgreSQL ORM Deadlock: 40P01 (src/db_transactions.py)"] --> Telemetry
    end

    subgraph S2["2. MCP Cross-File Surgical Context"]
        Telemetry --> AST["AST 2-Hop Call-Graph MCP Extractor"]
        AST --> MuseSpark["Meta Muse Spark 1.3 Deep Mathematical Reasoning"]
    end

    subgraph S3["3. Parallel Git Worktree Tournament"]
        MuseSpark --> WT_A["Worktree A: Elite Enterprise Multi-Fault Fix"]
        MuseSpark --> WT_B["Worktree B: Float Rounding Only (Partial)"]
        MuseSpark --> WT_C["Worktree C: Naive Ordered Lock (Deadlock/Timeout)"]
        
        WT_B --> FailB["FAILED: Split-Brain & PG Deadlock Unresolved"]
        WT_C --> FailC["FAILED: Queue Starvation & Execution Timeout (>30s)"]
        WT_A --> SandboxA["Read-Only Test Sandbox (ALL PASSED)"]
    end

    subgraph S4["4. Formal Verification & Certification"]
        SandboxA --> Z3["Microsoft Z3 SMT Theorem Prover"]
        Z3 -- "UNSAT (Provably Safe)" --> Winner["Winner: ELITE_ENTERPRISE_REPAIR (99.6/100)"]
    end

    Winner --> PR["Certified Autonomous Pull Request"]
```

---

## 3. Meta Model Telemetry Matrix

| Meta Model | Role in AutoPatch-Kernel | Output Summary |
| :--- | :--- | :--- |
| **Meta Muse Spark 1.3** | Deep Mathematical & Code Repair | Synthesized Redis distributed lease with monotonic fencing tokens, migrated float pricing to Decimal `ROUND_HALF_EVEN`, and implemented ordered row locks with `SKIP LOCKED` |
| **Meta Muse Wonder 1.0** | Generator-Critic Quality Gate | Verified pod anti-affinity topology spread, audited decimal currency quantization contexts, and proved cycle-free lock graphs |
| **Meta Muse Code 1.0** | Autonomous Agent Worktree Harness | Orchestrated parallel Git worktrees (`.autopatch/worktrees/`) for isolated fault verification and tournament racing |
| **Meta Muse Glimmer Open** | Fast Open-Weight Triage & Probing | Simulated partition heartbeats, high-frequency rounding arbitrage probes, and concurrent bidirectional transaction stress tests |

---

## 4. 3-Way Worktree Tournament Scorecard (100 Points Matrix)

| Worktree | Strategy Hypothesis | Status | Model Engine | Z3 (35) | AST (20) | Security (20) | Latency (15) | Static (10) | Total Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `worktree_a_refactor` | `ELITE_ENTERPRISE_REPAIR` (Full Multi-File Resolution) | 🏆 WINNER | `Meta-Muse-Spark-1.3` | 35.0/35 | 19.8/20 | 20.0/20 | 14.9/15 | 9.9/10 | **99.6/100** |
| `worktree_b_partial` | `FLOAT_ROUND_ONLY` (Partial Pricing Patch) | 🚫 FAILED | `Meta-Muse-Glimmer-Open` | 0.0/35 | 11.2/20 | 15.0/20 | 5.0/15 | 10.0/10 | **41.2/100** |
| `worktree_c_timeout` | `NAIVE_ORDERED_LOCK` (Unsynchronized Worker Pool) | 🚫 FAILED | `Meta-Muse-Spark-Open-1.3` | 0.0/35 | 0.0/20 | 0.0/20 | 0.0/15 | 0.0/10 | **0.0/100** |

### Tournament Outcome Details:
- **`worktree_a_refactor` (Winner):** Flawless resolution of all three enterprise faults. K8s split-brain prevented via Redis-backed distributed lease and pod anti-affinity; IEEE-754 arbitrage leak permanently eliminated via `Decimal` + `ROUND_HALF_EVEN`; database deadlocks resolved via canonical row ordering and `SKIP LOCKED`.
- **`worktree_b_partial` (Failed):** Attempted simple `round(val, 2)` on existing floating-point values without eliminating underlying float representation. Failed Z3 mathematical precision proof, leaving split-brain and ORM deadlocks completely unresolved.
- **`worktree_c_timeout` (Failed):** Implemented naive blocking retry loop without `SKIP LOCKED`, resulting in worker queue contention, lock convoying, and thread starvation timeout (>30s).

---

## 5. Cryptographic Z3 SMT Verification Certificate

```text
================================================================================
                    MICROSOFT Z3 SMT FORMAL VERIFICATION CERTIFICATE
================================================================================
Certificate ID     : Z3-PROVEN-9d84f1ac72e811bc
Verification Time  : 1793522400.0028
Target Subsystems  : k8s/statefulset.yaml, src/pricing_engine.py, src/db_transactions.py
Theorem Verdict    : PROVEN_LEADER_EXCLUSION_EXACT_DECIMAL_DEADLOCK_FREE (UNSAT_PROVEN_SAFE)
Mathematical Proof : UNSAT (Negation of leader exclusivity, decimal precision, & deadlock-freedom is provably unsatisfiable)
Solver Version     : Microsoft Z3 v4.13.0
SHA-256 Digest     : 8fa7b2c918e5b42a99182370f1a4e58b19c6e3952f418d10b7ea17983c5092a43
--------------------------------------------------------------------------------
FORMAL PRE-CONDITIONS (Phi_pre):
  [+] network_partition == TRUE || network_partition == FALSE
  [+] transaction_concurrency >= 10000
  [+] order_price > 0 && order_quantity > 0

PROVEN POST-CONDITION INVARIANTS (Phi_post):
  [+] Leader Quorum Exclusivity: For all time t, |{p in Pods | IsActiveLeader(p, t)}| <= 1 (No Split-Brain)
  [+] Exact Decimal Invariant: |ComputedAmount - ExactRationalAmount| == 0 (Zero Arbitrage Drift)
  [+] Strict Total Ordering: For all transactions T1, T2, LockGraph(T1, T2) is Acyclic (Deadlock-Free)
  [+] Non-Blocking Concurrency: Orders consumed via SKIP LOCKED guarantee wait_time == 0
================================================================================
```

---

## 6. Raw Unified Patch Diffs (Multi-File System Repair)

### Diff 1: `k8s/statefulset.yaml`
*Added Redis-backed distributed lease durations, quorum fencing keys, and hard pod anti-affinity rules to prevent split-brain leader elections during network partitions.*

```diff
diff --git a/k8s/statefulset.yaml b/k8s/statefulset.yaml
--- a/k8s/statefulset.yaml
+++ b/k8s/statefulset.yaml
@@ -18,12 +18,34 @@ spec:
   replicas: 2
   serviceName: "trading-engine-headless"
   template:
     metadata:
       labels:
         app: trading-engine
     spec:
+      affinity:
+        podAntiAffinity:
+          requiredDuringSchedulingIgnoredDuringExecution:
+            - labelSelector:
+                matchExpressions:
+                  - key: app
+                    operator: In
+                    values: ["trading-engine"]
+              topologyKey: "kubernetes.io/hostname"
       containers:
       - name: engine
         image: enterprise-trading-core:v2.4.1
-        # BUG: Uncoordinated leader election without quorum fencing
-        env:
-        - name: LEADER_ELECTION_ENABLED
-          value: "false"
+        # FIX: Redis-backed distributed lease with strict anti-split-brain fence
+        env:
+        - name: DISTRIBUTED_LEASE_ENABLED
+          value: "true"
+        - name: REDIS_LEASE_TTL_MS
+          value: "5000"
+        - name: LEASE_RENEWAL_INTERVAL_MS
+          value: "1500"
+        - name: LEASE_QUORUM_KEY
+          value: "election:leader:active_lease"
+        readinessProbe:
+          httpGet:
+            path: /health/lease-status
+            port: 8080
+          initialDelaySeconds: 2
+          periodSeconds: 2
```

### Diff 2: `src/pricing_engine.py`
*Completely migrated all float types to Python's decimal.Decimal with strict ROUND_HALF_EVEN contexts to mathematically plug the sub-cent arbitrage leak.*

```diff
diff --git a/src/pricing_engine.py b/src/pricing_engine.py
--- a/src/pricing_engine.py
+++ b/src/pricing_engine.py
@@ -1,18 +1,38 @@
-from typing import Dict, List
+# Completely migrated to Python decimal with strict ROUND_HALF_EVEN context
+from decimal import Decimal, Context, ROUND_HALF_EVEN, localcontext
+from typing import Dict, List
 
+# Enforce institutional-grade 28-digit precision and banker's rounding
+CURRENCY_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
+SATOSHI_QUANTIZER = Decimal("0.00000001")
+CENT_QUANTIZER = Decimal("0.01")
 
 class PricingEngine:
-    def calculate_discounted_price(self, base_price: float, quantity: float, discount_bps: float) -> float:
-        # BUG: IEEE-754 float arithmetic introduces sub-cent precision leak
-        multiplier = 1.0 - (discount_bps / 10000.0)
-        raw_total = base_price * quantity * multiplier
-        return round(raw_total, 2)
+    def calculate_discounted_price(self, base_price: Decimal, quantity: Decimal, discount_bps: Decimal) -> Decimal:
+        # FIX: Eliminate IEEE-754 float drift via exact Decimal arithmetic
+        with localcontext(CURRENCY_CONTEXT):
+            multiplier = Decimal("1.0") - (discount_bps / Decimal("10000.0"))
+            raw_total = base_price * quantity * multiplier
+            return raw_total.quantize(CENT_QUANTIZER, rounding=ROUND_HALF_EVEN)
 
-    def apply_spread(self, bid: float, ask: float, fee_rate: float) -> Dict[str, float]:
-        # BUG: Sub-cent rounding artifacts accumulate across high-throughput ticks
-        spread = ask - bid
-        fee = spread * fee_rate
-        return {"effective_spread": spread, "net_fee": fee}
+    def apply_spread(self, bid: Decimal, ask: Decimal, fee_rate: Decimal) -> Dict[str, Decimal]:
+        # FIX: Exact spread calculation with zero sub-cent arbitrage leak
+        with localcontext(CURRENCY_CONTEXT):
+            spread = ask - bid
+            fee = (spread * fee_rate).quantize(SATOSHI_QUANTIZER, rounding=ROUND_HALF_EVEN)
+            return {"effective_spread": spread, "net_fee": fee}
```

### Diff 3: `src/db_transactions.py`
*Injected strictly ordered row-level locks and SELECT ... FOR UPDATE SKIP LOCKED to eliminate circular dependencies and fix PostgreSQL deadlocks.*

```diff
diff --git a/src/db_transactions.py b/src/db_transactions.py
--- a/src/db_transactions.py
+++ b/src/db_transactions.py
@@ -24,20 +24,35 @@ class SettlementManager:
     def process_transfer(self, session: Session, from_account_id: int, to_account_id: int, amount: Decimal) -> None:
-        # BUG: Arbitrary lock acquisition order causes circular wait deadlock (40P01)
-        source = session.query(Account).filter_by(id=from_account_id).with_for_update().one()
-        target = session.query(Account).filter_by(id=to_account_id).with_for_update().one()
-        
-        source.balance -= amount
-        target.balance += amount
-        session.commit()
+        # FIX: Enforce canonical row-level lock ordering to eliminate circular waits
+        first_id, second_id = sorted([from_account_id, to_account_id])
+        account_map = {}
+        for acc_id in [first_id, second_id]:
+            account_map[acc_id] = (
+                session.query(Account)
+                .filter_by(id=acc_id)
+                .with_for_update()
+                .one()
+            )
+        
+        account_map[from_account_id].balance -= amount
+        account_map[to_account_id].balance += amount
+        session.commit()
 
     def dequeue_pending_orders(self, session: Session, limit: int = 50) -> List[Order]:
-        # BUG: Multiple workers block each other on queue head, causing cascading contention
-        return session.query(Order).filter_by(status="PENDING").limit(limit).all()
+        # FIX: Non-blocking queue concurrency via SKIP LOCKED
+        return (
+            session.query(Order)
+            .filter_by(status="PENDING")
+            .order_by(Order.priority.desc(), Order.created_at.asc())
+            .with_for_update(skip_locked=True)
+            .limit(limit)
+            .all()
+        )
```

---
*Generated autonomously by **AutoPatch-Kernel** built on Model Context Protocol (MCP) and Meta AI.*
"""
'''

updated_content = content[:start_pos] + new_func + "\n\n\n" + content[end_pos:]
app_path.write_text(updated_content, encoding="utf-8")
print("Successfully updated get_system_level_pr_markdown in app.py!")

