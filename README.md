# DemoCrash: High-Frequency Trading (HFT) Matching Engine

A production-grade, asynchronous order matching engine repository engineered with **four interconnected, professional-grade architectural bugs** spanning containerization, CI/CD orchestration, asynchronous concurrency, and automated pipeline verification.

---

## 📁 Repository Architecture

```text
DemoCrash/
├── .github/
│   └── workflows/
│       └── build.yml               # [BUG #2] CI/CD pipeline with broken environment variable
├── infra/
│   ├── Dockerfile                  # [BUG #1] Misconfigured Docker build causing OOM crash (exit 137)
│   └── build_hooks/
│       ├── __init__.py
│       └── prewarm_cache.py        # 128 GB contiguous memory allocation hook triggering OOM
├── src/
│   ├── __init__.py                 # Core package init with sandbox runtime compatibility
│   ├── config.py                   # Strict pipeline environment variable validator
│   ├── models.py                   # Domain models (Order, Trade, Account, Side, OrderStatus)
│   └── order_matching.py           # [BUG #3] Severe TOCTOU & non-atomic yield race conditions
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py            # [BUG #4] Central trigger suite catching pipeline & race condition bugs
├── pyproject.toml                  # Build system & pytest configuration
├── requirements.txt                # System dependencies
└── README.md                       # Architectural documentation & debugging runbook
```

---

## 💥 The 4 Interconnected Bugs

```
                                      ┌────────────────────────────────────────────────┐
                                      │   .github/workflows/build.yml                  │
                                      │   [BUG #2] Broken CI Env Var:                  │
                                      │   ORDER_MATCHING_WORKERS="UNBOUNDED_MAX"       │
                                      └──────────────────────┬─────────────────────────┘
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              ▼                                                             ▼
  ┌────────────────────────────────────────────────┐           ┌────────────────────────────────────────────────┐
  │   infra/Dockerfile                             │           │   tests/test_pipeline.py                       │
  │   [BUG #1] Build-Phase OOM Crash:              │           │   [BUG #4] Trigger & Detection:                │
  │   PREALLOCATE_MARKET_DEPTH_GB=128              │           │   1. Catches Broken Pipeline Env Var           │
  │   RUN python -m infra.build_hooks.prewarm      │           │   2. Catches Engine Race Condition Overfill    │
  │   -> Process killed by Linux OOM (Exit 137)    │           │   3. Catches Balance Double-Spend Overdraft    │
  └────────────────────────────────────────────────┘           └────────────────────┬───────────────────────────┘
                                                                                    │ triggers & catches
                                                                                    ▼
                                                               ┌────────────────────────────────────────────────┐
                                                               │   src/order_matching.py                        │
                                                               │   [BUG #3] Async Race Condition:               │
                                                               │   Yields execution to event loop               │
                                                               │   (`await _async_settle_match`) before state   │
                                                               │   decrement -> Phantom shares & Double-Spend   │
                                                               └────────────────────────────────────────────────┘
```

---

### 1. `infra/Dockerfile` — Build-Phase Out-Of-Memory (OOM) Crash

- **Location**: [`infra/Dockerfile`](file:///infra/Dockerfile) and [`infra/build_hooks/prewarm_cache.py`](file:///infra/build_hooks/prewarm_cache.py)
- **The Misconfiguration**:
  To achieve sub-microsecond tick execution during market open, the engine attempts to pre-allocate and page-lock a static Level-3 order book depth matrix during container image assembly.
  ```dockerfile
  ENV PREALLOCATE_MARKET_DEPTH_GB=128
  RUN python -m infra.build_hooks.prewarm_cache
  ```
- **Failure Mechanism**:
  Standard container build runners (Docker Desktop with 4-8 GB limit, GitHub Actions runners with 7 GB RAM, or Kubernetes build pods with memory cgroups) cannot satisfy an unchunked 128 GB memory request. The Linux kernel OOM Killer immediately delivers `SIGKILL 137` to the build container, or Python raises `MemoryError`, failing `docker build` during the `RUN` layer.

---

### 2. `.github/workflows/build.yml` — Broken CI/CD Pipeline Environment Variable

- **Location**: [`.github/workflows/build.yml`](file:///.github/workflows/build.yml) and [`src/config.py`](file:///src/config.py)
- **The Misconfiguration**:
  The CI workflow defines global engine settings under `env:`. A misconfiguration sets:
  ```yaml
  env:
    ORDER_MATCHING_WORKERS: "UNBOUNDED_MAX"   # Should be integer [1-64]
    MATCHING_BATCH_TIMEOUT_MS: "-100"         # Negative timeout violates schema
  ```
- **Failure Mechanism**:
  1. The pre-flight workflow step checks the format of `ORDER_MATCHING_WORKERS` and halts the workflow immediately if not numeric.
  2. [`src/config.py`](file:///src/config.py) strictly validates configuration types. When `load_engine_config()` parses `"UNBOUNDED_MAX"`, it raises `PipelineConfigurationError`, failing the test runner before execution.

---

### 3. `src/order_matching.py` — Severe Asynchronous Trading Race Conditions

- **Location**: [`src/order_matching.py`](file:///src/order_matching.py)
- **The Bug**:
  A double Time-Of-Check to Time-Of-Use (TOCTOU) vulnerability in asynchronous coroutine scheduling:
  
  #### A. Overfill & Phantom Shares (`_execute_match_loop`):
  ```python
  # Match quantity calculated based on current book state:
  match_qty = min(incoming_order.remaining_quantity, best_match.remaining_quantity)

  # NON-ATOMIC ASYNC YIELD: Control returns to event loop for WAL logging / settlement
  await self._async_settle_match(incoming_order, best_match, match_qty, match_price)

  # BUG: Concurrent orders have already read best_match with un-decremented quantity!
  incoming_order.remaining_quantity -= match_qty
  best_match.remaining_quantity -= match_qty  # Drops below zero!
  ```
  **Consequence**: If two aggressive BUY orders of 100 BTC each target a single resting ASK of 100 BTC, both coroutines see the full 100 BTC during the async yield. Both execute, generating **200 BTC of traded volume** from a seller who only owned 100 BTC. The seller's resting order remaining quantity becomes **-100 BTC**, creating 100 phantom Bitcoins out of thin air.

  #### B. Account Balance Double-Spend (`submit_order`):
  ```python
  # TIME-OF-CHECK:
  if account.available_cash < required_funds:
      raise ValueError(...)

  # ASYNC YIELD: Control returns to event loop for pre-trade risk check
  await self._async_pretrade_risk_check(order)

  # TIME-OF-USE: Cash deducted only after coroutine resumes
  account.available_cash -= required_funds
  ```
  **Consequence**: A trader with \$10,000 can submit two concurrent \$10,000 BUY orders simultaneously. Both pass the balance check before either deducts capital, resulting in a **-\$10,000 cash overdraft**.

---

### 4. `tests/test_pipeline.py` — Bug Trigger & Verification Suite

- **Location**: [`tests/test_pipeline.py`](file:///tests/test_pipeline.py)
- **Role**:
  Acts as the primary verification harness that deterministically reproduces and catches all bugs:
  1. `test_pipeline_catches_broken_environment_variable`: Extracts CI environment variables from `.github/workflows/build.yml` and catches `PipelineConfigurationError`.
  2. `test_pipeline_environment_contract_assertion`: Fails if `ORDER_MATCHING_WORKERS` is not numeric, replicating CI pipeline halts.
  3. `test_order_matching_overfill_race_condition`: Concurrently executes 2 BUY orders against 1 resting ASK, asserting `resting_ask.remaining_quantity >= 0`. Catches the overfill and phantom volume.
  4. `test_account_double_spend_race_condition`: Submits simultaneous orders exceeding total equity, asserting `trader.available_cash >= 0`. Catches the cash balance overdraft.

---

## 🚀 Execution & Reproduction Guide

### Run Diagnostics Directly (Prints Detailed Audit Report)
```bash
python tests/test_pipeline.py
```
**Sample Output:**
```text
==============================================================================
  DEMOCRASH BUG TRIGGER AND DIAGNOSTIC SUITE
==============================================================================

[STEP 1] Testing CI/CD Pipeline Environment Contract...
[CI/CD TRACER] Successfully caught broken environment variable: CI/CD Pipeline Environment Error: Invalid 'ORDER_MATCHING_WORKERS=UNBOUNDED_MAX'. Expected positive integer [1-64]. Details: invalid literal for int() with base 10: 'UNBOUNDED_MAX'
 -> [CAUGHT] Successfully identified broken variable in .github/workflows/build.yml
 -> [TRIGGERED] CI/CD Pipeline Failure: CRITICAL CI/CD PIPELINE FAILURE: ORDER_MATCHING_WORKERS is malformed! Expected numeric string, got: 'UNBOUNDED_MAX' from .github/workflows/build.yml

[STEP 2] Testing Asynchronous Trading Engine Concurrency...
[RACE CONDITION AUDIT] Initial Resting Quantity : 100.0 BTC
[RACE CONDITION AUDIT] Total Executed Volume    : 200.0 BTC
[RACE CONDITION AUDIT] Final Ask Remaining Qty  : -100.0 BTC
 -> [TRIGGERED] Overfill Race Condition Caught:
    CRITICAL RACE CONDITION CAUGHT: Resting order was overfilled! Remaining quantity is negative (-100.0). Total traded: 200.0 BTC, but only 100.0 BTC existed!

[STEP 3] Testing Trader Capital Allocation & Double-Spend...
[DOUBLE-SPEND AUDIT] Trader Initial Balance : $10,000.00
[DOUBLE-SPEND AUDIT] Trader Final Available : $-10000.00
[DOUBLE-SPEND AUDIT] Trader Locked Cash     : $20000.00
 -> [TRIGGERED] Double Spend Race Condition Caught:
    CRITICAL DOUBLE-SPEND RACE CONDITION CAUGHT: Trader balance overdrafted! Available cash: $-10000.00 (Expected >= $0.00). Locked cash: $20000.00

==============================================================================
  DIAGNOSTIC TRIGGER RUN COMPLETE
==============================================================================
```

### Run via Pytest (Fails CI Test Suite)
```bash
pytest -v tests/test_pipeline.py
```

### Reproduce Docker Build OOM Crash
```bash
docker build -t matching-engine:latest -f infra/Dockerfile .
```
*(Terminates with exit code 137 / SIGKILL)*

