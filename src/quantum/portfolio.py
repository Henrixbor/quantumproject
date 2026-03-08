"""Quantum portfolio optimization using QAOA.

Formulates the Markowitz mean-variance portfolio problem as a QUBO
and solves it using QAOA for near-optimal asset allocation.
"""

from __future__ import annotations

import numpy as np

from src.models.schemas import PortfolioRequest, PortfolioResult
from src.quantum.market_data import DEFAULT_RETURNS, DEFAULT_VOLATILITY
from src.quantum.qaoa import qaoa_optimize
from src.quantum.validation import ValidationError, validate_and_preprocess_portfolio


def _build_covariance_matrix(
    symbols: list[str], volatilities: list[float]
) -> np.ndarray:
    """Build a synthetic covariance matrix from volatilities with correlations."""
    n = len(symbols)
    # Base correlation of 0.3 for same-class assets, 0.1 cross-class
    crypto = {"BTC", "ETH", "SOL", "BNB", "ADA", "DOT", "AVAX", "MATIC", "LINK", "UNI"}
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = symbols[i], symbols[j]
            if (si in crypto and sj in crypto) or (si not in crypto and sj not in crypto):
                corr[i, j] = corr[j, i] = 0.3 + np.random.uniform(-0.1, 0.1)
            else:
                corr[i, j] = corr[j, i] = 0.1 + np.random.uniform(-0.05, 0.05)

    vols = np.array(volatilities)
    cov = np.outer(vols, vols) * corr
    return cov


def _portfolio_to_qubo(
    returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_tolerance: float,
    num_bits_per_asset: int = 3,
) -> np.ndarray:
    """Convert portfolio optimization to QUBO matrix.

    Discretizes allocation into 2^num_bits levels per asset and builds
    the QUBO cost matrix for QAOA.
    """
    n_assets = len(returns)
    n_qubits = n_assets * num_bits_per_asset
    levels = 2**num_bits_per_asset

    Q = np.zeros((n_qubits, n_qubits))

    for i in range(n_assets):
        for bi in range(num_bits_per_asset):
            qi = i * num_bits_per_asset + bi
            weight_i = (2**bi) / levels
            # Return term (maximize, so negative in QUBO)
            Q[qi, qi] -= (1.0 - risk_tolerance) * returns[i] * weight_i
            # Risk term (minimize variance)
            for j in range(n_assets):
                for bj in range(num_bits_per_asset):
                    qj = j * num_bits_per_asset + bj
                    weight_j = (2**bj) / levels
                    Q[qi, qj] += risk_tolerance * cov_matrix[i, j] * weight_i * weight_j

    # Budget constraint penalty: sum of allocations should be ~1
    penalty = 5.0
    for qi in range(n_qubits):
        Q[qi, qi] += penalty
        for qj in range(qi + 1, n_qubits):
            Q[qi, qj] += 2 * penalty / n_qubits

    return Q


async def optimize_portfolio(request: PortfolioRequest) -> PortfolioResult:
    """Optimize portfolio allocation using quantum QAOA."""
    request, validation_warnings = validate_and_preprocess_portfolio(request)

    symbols = [a.symbol.upper() for a in request.assets]
    n = len(symbols)

    # Resolve returns and volatilities
    returns = np.array([
        a.expected_return if a.expected_return is not None
        else DEFAULT_RETURNS.get(a.symbol.upper(), 0.10)
        for a in request.assets
    ])
    volatilities = np.array([
        a.volatility if a.volatility is not None
        else DEFAULT_VOLATILITY.get(a.symbol.upper(), 0.30)
        for a in request.assets
    ])

    cov_matrix = _build_covariance_matrix(symbols, volatilities.tolist())

    # Build QUBO and run QAOA — scale complexity with problem size
    # Keep total qubits <= 14 to stay under 1 second
    if n <= 4:
        bits_per_asset = 3
        num_layers = 3
    elif n <= 7:
        bits_per_asset = 2
        num_layers = 2
    else:
        bits_per_asset = 1
        num_layers = 2

    qubo = _portfolio_to_qubo(returns, cov_matrix, request.risk_tolerance, bits_per_asset)
    n_qubits = n * bits_per_asset

    bitstring, _ = qaoa_optimize(qubo, num_layers=num_layers, num_shots=512)

    # Decode bitstring to allocations
    levels = 2**bits_per_asset
    raw_alloc = []
    for i in range(n):
        val = sum(
            bitstring[i * bits_per_asset + b] * (2**b) for b in range(bits_per_asset)
        )
        raw_alloc.append(val / levels)

    # Normalize and apply constraints
    raw_alloc = np.array(raw_alloc)
    raw_alloc = np.clip(raw_alloc, request.min_allocation, request.max_allocation)
    total = raw_alloc.sum()
    if total > 0:
        allocations = raw_alloc / total
    else:
        allocations = np.ones(n) / n

    # Compute portfolio metrics
    port_return = float(allocations @ returns)
    port_vol = float(np.sqrt(allocations @ cov_matrix @ allocations))
    risk_free_rate = 0.04
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0

    return PortfolioResult(
        allocations={s: round(float(a), 4) for s, a in zip(symbols, allocations)},
        expected_return=round(port_return, 4),
        volatility=round(port_vol, 4),
        sharpe_ratio=round(sharpe, 2),
        method="QAOA (simulated)",
        qubit_count=n_qubits,
        warnings=validation_warnings,
    )
