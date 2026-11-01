"""
tests/test_pipeline.py

The Central Trigger and Verification Suite for DemoCrash.
Catches:
1. The CI/CD Pipeline Failure caused by the broken environment variable in .github/workflows/build.yml.
2. The Severe Asynchronous Race Condition in src/order_matching.py (overfill / phantom shares & double spend).
"""

import asyncio
from pathlib import Path
import re
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
import yaml

from src.config import EngineConfig, PipelineConfigurationError, load_engine_config
from src.models import Account, Order, OrderStatus, OrderType, Side, Trade
from src.order_matching import AsyncMatchingEngine


def extract_ci_workflow_env() -> dict[str, str]:
    """
    Parses the environment block from .github/workflows/build.yml.
    Allows local test executions to accurately reflect CI environment variables.
    """
    workflow_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "build.yml"
    if not workflow_path.exists():
        return {}

    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = yaml.safe_load(content)
        return {str(k): str(v) for k, v in data.get("env", {}).items()}
    except Exception:
        # Fallback regex extraction if PyYAML is unavailable or parser fails
        env_vars = {}
        env_matches = re.findall(r"^\s*([A-Z0-9_]+):\s*[\"']?([^\"'\n]+)[\"']?", content, re.MULTILINE)
        for k, v in env_matches:
            env_vars[k] = v.strip()
        return env_vars


# ==============================================================================
# 1. TRIGGER & CATCH: CI/CD PIPELINE BROKEN ENVIRONMENT VARIABLE
# ==============================================================================

def test_pipeline_catches_broken_environment_variable():
    """
    TRIGGERS & CATCHES: Bug #2 (Broken Environment Variable).
    Extracts the environment configuration defined in .github/workflows/build.yml
    and verifies that the engine configuration loader catches the invalid
    ORDER_MATCHING_WORKERS='UNBOUNDED_MAX' and raises PipelineConfigurationError.
    """
    ci_env = extract_ci_workflow_env()
    assert "ORDER_MATCHING_WORKERS" in ci_env, "Missing ORDER_MATCHING_WORKERS in CI workflow env!"

    # The pipeline sets ORDER_MATCHING_WORKERS to 'UNBOUNDED_MAX'
    assert ci_env["ORDER_MATCHING_WORKERS"] == "UNBOUNDED_MAX"

    # Catching the configuration failure
    with pytest.raises(PipelineConfigurationError) as exc_info:
        load_engine_config(env_override=ci_env)

    error_msg = str(exc_info.value)
    print(f"\n[CI/CD TRACER] Successfully caught broken environment variable: {error_msg}")
    assert "ORDER_MATCHING_WORKERS=UNBOUNDED_MAX" in error_msg


def test_pipeline_environment_contract_assertion():
    """
    TRIGGERS: Direct pipeline assertion failure.
    If executed inside CI/CD with ORDER_MATCHING_WORKERS='UNBOUNDED_MAX',
    this test directly fails with an AssertionError, halting the pipeline.
    """
    ci_env = extract_ci_workflow_env()
    workers_raw = ci_env.get("ORDER_MATCHING_WORKERS", "4")

    # This assertion intentionally fails in the broken CI pipeline configuration:
    assert workers_raw.isdigit(), (
        f"CRITICAL CI/CD PIPELINE FAILURE: ORDER_MATCHING_WORKERS is malformed! "
        f"Expected numeric string, got: {workers_raw!r} from .github/workflows/build.yml"
    )


# ==============================================================================
# 2. TRIGGER & CATCH: SEVERE ASYNC RACE CONDITION (OVERFILL / PHANTOM SHARES)
# ==============================================================================

async def _trigger_overfill_race_condition():
    """
    Launches concurrent buy orders against a single resting limit ask order.
    Exposes the non-atomic yield inside AsyncMatchingEngine._execute_match_loop.
    """
    engine = AsyncMatchingEngine()
    symbol = "BTC-USD"

    # Set up Seller with 100 BTC @ $50,000
    seller = Account(account_id="seller_whale", available_cash=0.0, holdings={symbol: 100.0})
    engine.register_account(seller)

    resting_ask = Order(
        order_id="ask_resting_001",
        trader_id="seller_whale",
        symbol=symbol,
        side=Side.SELL,
        price=50000.0,
        quantity=100.0,
    )
    # Add resting ask directly to the order book
    engine.get_or_create_book(symbol).add_limit_order(resting_ask)

    # Set up two competing buyers
    buyer_1 = Account(account_id="buyer_alpha", available_cash=10_000_000.0)
    buyer_2 = Account(account_id="buyer_beta", available_cash=10_000_000.0)
    engine.register_account(buyer_1)
    engine.register_account(buyer_2)

    order_1 = Order(
        order_id="buy_aggressive_001",
        trader_id="buyer_alpha",
        symbol=symbol,
        side=Side.BUY,
        price=50000.0,
        quantity=100.0,
    )
    order_2 = Order(
        order_id="buy_aggressive_002",
        trader_id="buyer_beta",
        symbol=symbol,
        side=Side.BUY,
        price=50000.0,
        quantity=100.0,
    )

    # Launch both orders concurrently
    results = await asyncio.gather(
        engine.submit_order(order_1),
        engine.submit_order(order_2),
        return_exceptions=True,
    )

    total_traded_volume = sum(t.quantity for t in engine.trade_history if t.ask_order_id == resting_ask.order_id)

    return resting_ask, total_traded_volume, results


def test_order_matching_overfill_race_condition():
    """
    TRIGGERS & CATCHES: Bug #3 (Race Condition in order matching).
    Asserts that the resting order is NOT overfilled and that phantom shares
    are NOT generated. Because of the race condition, this test catches
    the negative remaining quantity and fails with an AssertionError.
    """
    resting_ask, total_traded_volume, results = asyncio.run(_trigger_overfill_race_condition())

    print(f"\n[RACE CONDITION AUDIT] Initial Resting Quantity : 100.0 BTC")
    print(f"[RACE CONDITION AUDIT] Total Executed Volume    : {total_traded_volume} BTC")
    print(f"[RACE CONDITION AUDIT] Final Ask Remaining Qty  : {resting_ask.remaining_quantity} BTC")

    # CATCHES THE RACE CONDITION:
    # 1. Total traded volume should never exceed initial quantity (100.0)
    # 2. Remaining quantity should never be negative (-100.0)
    assert resting_ask.remaining_quantity >= 0, (
        f"CRITICAL RACE CONDITION CAUGHT: Resting order was overfilled! "
        f"Remaining quantity is negative ({resting_ask.remaining_quantity}). "
        f"Total traded: {total_traded_volume} BTC, but only 100.0 BTC existed!"
    )


# ==============================================================================
# 3. TRIGGER & CATCH: DOUBLE SPEND CASH OVERDRAFT RACE CONDITION
# ==============================================================================

async def _trigger_double_spend_race_condition():
    """
    Launches two concurrent orders for $10,000 each from a trader who only
    has $10,000 total available cash. Exposes the TOCTOU check-then-act bug.
    """
    engine = AsyncMatchingEngine()
    symbol = "ETH-USD"

    # Trader only has $10,000
    trader = Account(account_id="trader_exploit", available_cash=10000.0)
    engine.register_account(trader)

    # Two concurrent orders of $10,000 each
    order_a = Order(
        order_id="ord_spend_001",
        trader_id="trader_exploit",
        symbol=symbol,
        side=Side.BUY,
        price=2000.0,
        quantity=5.0,  # $10,000
    )
    order_b = Order(
        order_id="ord_spend_002",
        trader_id="trader_exploit",
        symbol=symbol,
        side=Side.BUY,
        price=2000.0,
        quantity=5.0,  # $10,000
    )

    await asyncio.gather(
        engine.submit_order(order_a),
        engine.submit_order(order_b),
        return_exceptions=True,
    )

    return trader


def test_account_double_spend_race_condition():
    """
    TRIGGERS & CATCHES: Check-Then-Act Race Condition in capital allocation.
    Asserts that a trader cannot spend more than their available balance.
    """
    trader = asyncio.run(_trigger_double_spend_race_condition())

    print(f"\n[DOUBLE-SPEND AUDIT] Trader Initial Balance : $10,000.00")
    print(f"[DOUBLE-SPEND AUDIT] Trader Final Available : ${trader.available_cash:.2f}")
    print(f"[DOUBLE-SPEND AUDIT] Trader Locked Cash     : ${trader.locked_cash:.2f}")

    # CATCHES THE RACE CONDITION:
    assert trader.available_cash >= 0.0, (
        f"CRITICAL DOUBLE-SPEND RACE CONDITION CAUGHT: Trader balance overdrafted! "
        f"Available cash: ${trader.available_cash:.2f} (Expected >= $0.00). "
        f"Locked cash: ${trader.locked_cash:.2f}"
    )


# ==============================================================================
# STANDALONE TRIGGER EXECUTION RUNNER
# ==============================================================================

def run_all_triggers():
    print("=" * 78)
    print("  DEMOCRASH BUG TRIGGER AND DIAGNOSTIC SUITE")
    print("=" * 78)

    # 1. Pipeline Environment Trigger
    print("\n[STEP 1] Testing CI/CD Pipeline Environment Contract...")
    try:
        test_pipeline_catches_broken_environment_variable()
        print(" -> [CAUGHT] Successfully identified broken variable in .github/workflows/build.yml")
    except Exception as e:
        print(f" -> [ERROR] {e}")

    try:
        test_pipeline_environment_contract_assertion()
        print(" -> [PASS] Pipeline variable is valid.")
    except AssertionError as e:
        print(f" -> [TRIGGERED] CI/CD Pipeline Failure: {e}")

    # 2. Asynchronous Overfill Race Condition Trigger
    print("\n[STEP 2] Testing Asynchronous Trading Engine Concurrency...")
    try:
        test_order_matching_overfill_race_condition()
        print(" -> [PASS] Order matching is thread-safe.")
    except AssertionError as e:
        print(f" -> [TRIGGERED] Overfill Race Condition Caught:\n    {e}")

    # 3. Double Spend Race Condition Trigger
    print("\n[STEP 3] Testing Trader Capital Allocation & Double-Spend...")
    try:
        test_account_double_spend_race_condition()
        print(" -> [PASS] Account balances strictly preserved.")
    except AssertionError as e:
        print(f" -> [TRIGGERED] Double Spend Race Condition Caught:\n    {e}")

    print("\n" + "=" * 78)
    print("  DIAGNOSTIC TRIGGER RUN COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    run_all_triggers()
