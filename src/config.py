"""
src/config.py

Production configuration loader for the High-Frequency Trading (HFT)
Order Matching Engine.
"""

import os
from dataclasses import dataclass
from typing import Optional


class PipelineConfigurationError(ValueError):
    """Raised when CI/CD or runtime environment variables violate schema constraints."""
    pass


@dataclass(frozen=True)
class EngineConfig:
    environment: str
    workers: int
    batch_timeout_ms: int
    symbol_allowlist: list[str]
    preallocate_l3_cache: bool


def load_engine_config(env_override: Optional[dict[str, str]] = None) -> EngineConfig:
    """
    Loads and validates engine configuration from environment variables.
    
    Raises:
        PipelineConfigurationError: If any required environment variable is malformed.
    """
    source = os.environ if env_override is None else env_override

    env_name = source.get("ENVIRONMENT", "development")

    # Validate ORDER_MATCHING_WORKERS (expected integer between 1 and 64)
    raw_workers = source.get("ORDER_MATCHING_WORKERS", "4")
    try:
        workers = int(raw_workers)
        if workers < 1 or workers > 64:
            raise ValueError(f"Worker count must be between 1 and 64, got {workers}")
    except (ValueError, TypeError) as e:
        raise PipelineConfigurationError(
            f"CI/CD Pipeline Environment Error: Invalid 'ORDER_MATCHING_WORKERS={raw_workers}'. "
            f"Expected positive integer [1-64]. Details: {e}"
        ) from e

    # Validate MATCHING_BATCH_TIMEOUT_MS (expected positive integer ms)
    raw_timeout = source.get("MATCHING_BATCH_TIMEOUT_MS", "50")
    try:
        timeout_ms = int(raw_timeout)
        if timeout_ms <= 0:
            raise ValueError(f"Timeout must be strictly positive (> 0 ms), got {timeout_ms}")
    except (ValueError, TypeError) as e:
        raise PipelineConfigurationError(
            f"CI/CD Pipeline Environment Error: Invalid 'MATCHING_BATCH_TIMEOUT_MS={raw_timeout}'. "
            f"Expected positive integer milliseconds. Details: {e}"
        ) from e

    raw_symbols = source.get("TRADING_SYMBOL_ALLOWLIST", "BTC-USD,ETH-USD")
    symbols = [s.strip() for s in raw_symbols.split(",") if s.strip()]

    preallocate = source.get("HFT_BUILD_OPTIMIZATION", "0") in ("1", "true", "TRUE")

    return EngineConfig(
        environment=env_name,
        workers=workers,
        batch_timeout_ms=timeout_ms,
        symbol_allowlist=symbols,
        preallocate_l3_cache=preallocate,
    )

