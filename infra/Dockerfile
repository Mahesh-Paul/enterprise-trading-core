# syntax=docker/dockerfile:1
# ==============================================================================
# DemoCrash HFT Order Matching Engine - Container Build Manifest
# ==============================================================================

FROM python:3.11-slim-bookworm AS builder

LABEL maintainer="HFT Core Engineering <core-engine@democrash.internal>"
LABEL description="Low-Latency Asynchronous Order Matching Engine"

WORKDIR /app

# Install system compilation packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    git \
    libjemalloc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree and infra hooks
COPY . .

# ==============================================================================
# BUG #1: OUT-OF-MEMORY (OOM) CRASH DURING BUILD PHASE
# ==============================================================================
# Root Cause:
# To eliminate cold-start garbage collection pauses and CPU spikes upon market
# open, the build pipeline executes an in-memory Level-3 order book cache
# initialization step.
#
# The Misconfiguration:
# 1. PREALLOCATE_MARKET_DEPTH_GB is configured to 128 (128 Gigabytes of RAM).
# 2. In typical Docker build hosts (Docker Desktop with 4GB-8GB limit, CI runners
#    with 7GB RAM, or K8s build pods with memory cgroups), the builder process
#    exhausts physical host RAM and swap within seconds.
# 3. The Linux cgroup controller / Kernel OOM Killer sends SIGKILL (exit 137),
#    or Python aborts with MemoryError, crashing the `docker build` phase.
# ==============================================================================
ENV HFT_BUILD_OPTIMIZATION=1
ENV PREALLOCATE_MARKET_DEPTH_GB=128
ENV PARALLEL_L3_WORKERS=64
ENV PYTHONUNBUFFERED=1

# Trigger the build-phase OOM crash:
RUN python -m infra.build_hooks.prewarm_cache

# ==============================================================================
# Production Runtime Stage (Never reached due to build-phase OOM crash above)
# ==============================================================================
EXPOSE 8080 9090

ENTRYPOINT ["python", "-m", "src.order_matching"]

