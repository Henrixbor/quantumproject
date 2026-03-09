"""Quantum portfolio optimization using QAOA.

Formulates the Markowitz mean-variance portfolio problem as a QUBO
and solves it using QAOA for near-optimal asset allocation.

Performance-optimized: eliminated redundant array copies, vectorized
QUBO construction, and reduced unnecessary allocations.
"""

from __future__ import annotations

import numpy as np

from src.models.schemas import PortfolioRequest, PortfolioResult
from src.quantum.market_data import DEFAULT_RETURNS, DEFAULT_VOLATILITY
from src.quantum.qaoa import qaoa_optimize
from src.quantum.validation import ValidationError, validate_and_preprocess_portfolio


def _build_covariance_matrix(
    symbols: list[str], volatilities: np.ndarray
) -> np.ndarray:
    """Build a synthetic covariance matrix from volatilities with correlations.

    Accepts volatilities as ndarray directly to avoid list conversion overhead.
    Uses vectorized correlation matrix construction.
    """
    n = len(symbols)
    crypto = {"BTC", "ETH", "SOL", "BNB", "ADA", "DOT", "AVAX", "MATIC", "LINK", "UNI"}

    # Vectorize correlation assignment: build boolean masks
    is_crypto = np.array([s in crypto for s in symbols])
    # same_class[i,j] = True if both crypto or both non-crypto
    same_class = np.equal.outer(is_crypto, is_crypto)

    # Seed from sorted symbols for deterministic results with same inputs
    seed = hash(tuple(sorted(symbols))) & 0xFFFFFFFF
    rng = np.random.default_rng(seed)
    corr = np.eye(n)
    # Generate random perturbations for upper triangle only
    upper_mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    n_upper = upper_mask.sum()

    base_vals = np.where(
        same_class[upper_mask],
        0.3 + rng.uniform(-0.1, 0.1, size=n_upper),
        0.1 + rng.uniform(-0.05, 0.05, size=n_upper),
    )
    corr[upper_mask] = base_vals
    corr = corr + corr.T - np.eye(n)

    # cov = diag(vol) @ corr @ diag(vol) = outer(vol, vol) * corr
    cov = np.outer(volatilities, volatilities) * corr
    return cov


def _portfolio_to_qubo(
    returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_tolerance: float,
    num_bits_per_asset: int = 3,
) -> np.ndarray:
    """Convert portfolio optimization to QUBO matrix.

    Vectorized construction using numpy broadcasting instead of
    nested Python loops.
    """
    n_assets = len(returns)
    n_qubits = n_assets * num_bits_per_asset
    levels = 2**num_bits_per_asset

    Q = np.zeros((n_qubits, n_qubits))

    # Pre-compute weight vector for all qubit positions
    bit_indices = np.arange(num_bits_per_asset)
    weights_per_bit = (2.0**bit_indices) / levels  # shape (num_bits_per_asset,)

    # Build qubit-to-asset mapping and weights
    qubit_asset = np.repeat(np.arange(n_assets), num_bits_per_asset)
    qubit_weight = np.tile(weights_per_bit, n_assets)

    # Return term on diagonal: Q[qi, qi] -= (1 - risk_tolerance) * returns[asset_i] * weight_i
    return_coeff = (1.0 - risk_tolerance)
    for qi in range(n_qubits):
        Q[qi, qi] -= return_coeff * returns[qubit_asset[qi]] * qubit_weight[qi]

    # Risk term: Q[qi, qj] += risk_tolerance * cov[asset_i, asset_j] * weight_i * weight_j
    # Vectorized using outer products
    weight_outer = np.outer(qubit_weight, qubit_weight)
    cov_mapped = cov_matrix[np.ix_(qubit_asset, qubit_asset)]
    Q += risk_tolerance * cov_mapped * weight_outer

    # Budget constraint penalty
    penalty = 5.0
    diag_idx = np.arange(n_qubits)
    Q[diag_idx, diag_idx] += penalty
    # Upper triangle off-diagonal penalty
    upper = np.triu(np.ones((n_qubits, n_qubits), dtype=bool), k=1)
    Q[upper] += 2 * penalty / n_qubits

    return Q


async def optimize_portfolio(request: PortfolioRequest) -> PortfolioResult:
    """Optimize portfolio allocation using quantum QAOA."""
    request, validation_warnings = validate_and_preprocess_portfolio(request)

    symbols = [a.symbol.upper() for a in request.assets]
    n = len(symbols)

    # Resolve returns and volatilities -- single array construction, no copies
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

    # Pass ndarray directly -- no .tolist() conversion
    cov_matrix = _build_covariance_matrix(symbols, volatilities)

    # Scale complexity with problem size
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

    # Decode bitstring to allocations -- vectorized
    levels = 2**bits_per_asset
    bit_weights = 2.0 ** np.arange(bits_per_asset)
    raw_alloc = np.array([
        bitstring[i * bits_per_asset:(i + 1) * bits_per_asset] @ bit_weights
        for i in range(n)
    ]) / levels

    # Normalize and apply constraints -- in-place clip to avoid copy
    np.clip(raw_alloc, request.min_allocation, request.max_allocation, out=raw_alloc)
    total = raw_alloc.sum()
    if total > 0:
        allocations = raw_alloc / total
    else:
        allocations = np.full(n, 1.0 / n)

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
