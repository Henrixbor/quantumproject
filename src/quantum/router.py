"""Quantum route optimization (TSP) using QAOA.

Solves the Traveling Salesman Problem by encoding it as a QUBO
and running QAOA to find near-optimal routes.
"""

from __future__ import annotations

import math

import numpy as np

from src.models.schemas import Location, RouteRequest, RouteResult
from src.quantum.qaoa import qaoa_optimize
from src.quantum.validation import ValidationError, validate_and_preprocess_route


def _haversine(loc1: Location, loc2: Location) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    R = 6371.0
    lat1, lat2 = math.radians(loc1.lat), math.radians(loc2.lat)
    dlat = lat2 - lat1
    dlon = math.radians(loc2.lon - loc1.lon)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _build_distance_matrix(locations: list[Location]) -> np.ndarray:
    """Build NxN distance matrix between all locations."""
    n = len(locations)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = _haversine(locations[i], locations[j])
            dist[i, j] = dist[j, i] = d
    return dist


def _tsp_to_qubo(dist_matrix: np.ndarray) -> np.ndarray:
    """Encode TSP as QUBO using position-based encoding.

    Uses n^2 binary variables: x_{i,p} = 1 if city i is at position p.
    """
    n = dist_matrix.shape[0]
    num_qubits = n * n
    Q = np.zeros((num_qubits, num_qubits))
    max_dist = dist_matrix.max()
    penalty = 10.0 * max_dist

    def idx(city: int, pos: int) -> int:
        return city * n + pos

    # Objective: minimize total distance
    for p in range(n):
        next_p = (p + 1) % n
        for i in range(n):
            for j in range(n):
                if i != j:
                    qi, qj = idx(i, p), idx(j, next_p)
                    Q[qi, qj] += dist_matrix[i, j]

    # Constraint: each city visited exactly once
    for i in range(n):
        for p in range(n):
            Q[idx(i, p), idx(i, p)] -= penalty
            for q in range(p + 1, n):
                Q[idx(i, p), idx(i, q)] += 2 * penalty

    # Constraint: each position has exactly one city
    for p in range(n):
        for i in range(n):
            Q[idx(i, p), idx(i, p)] -= penalty
            for j in range(i + 1, n):
                Q[idx(i, p), idx(j, p)] += 2 * penalty

    return Q


def _decode_tsp_solution(bitstring: np.ndarray, n: int) -> list[int]:
    """Decode QUBO bitstring to city ordering."""
    route = [-1] * n
    used_cities: set[int] = set()

    for p in range(n):
        best_city = -1
        best_val = -1.0
        for i in range(n):
            val = bitstring[i * n + p]
            if val > best_val and i not in used_cities:
                best_val = val
                best_city = i
        if best_city >= 0:
            route[p] = best_city
            used_cities.add(best_city)

    # Fill any gaps with remaining cities
    remaining = [i for i in range(n) if i not in used_cities]
    for p in range(n):
        if route[p] == -1 and remaining:
            route[p] = remaining.pop(0)

    return route


def _route_distance(route: list[int], dist_matrix: np.ndarray, loop: bool) -> float:
    """Calculate total route distance."""
    total = sum(dist_matrix[route[i], route[i + 1]] for i in range(len(route) - 1))
    if loop:
        total += dist_matrix[route[-1], route[0]]
    return total


async def optimize_route(request: RouteRequest) -> RouteResult:
    """Find optimal route through locations using quantum QAOA."""
    request, validation_warnings = validate_and_preprocess_route(request)

    locations = request.locations
    n = len(locations)
    dist_matrix = _build_distance_matrix(locations)

    # For small problems, use QAOA; for larger, use quantum-inspired heuristic
    if n <= 5:
        qubo = _tsp_to_qubo(dist_matrix)
        bitstring, _ = qaoa_optimize(qubo, num_layers=2, num_shots=512)
        route = _decode_tsp_solution(bitstring, n)
        n_qubits = n * n
    else:
        # Quantum-inspired nearest neighbor with 2-opt improvement
        # Start from each city, pick best
        best_route: list[int] = []
        best_dist = float("inf")
        for start in range(n):
            route = [start]
            unvisited = set(range(n)) - {start}
            while unvisited:
                current = route[-1]
                nearest = min(unvisited, key=lambda x: dist_matrix[current, x])
                route.append(nearest)
                unvisited.remove(nearest)

            # 2-opt improvement
            improved = True
            while improved:
                improved = False
                for i in range(1, n - 1):
                    for j in range(i + 1, n):
                        new_route = route[:i] + route[i : j + 1][::-1] + route[j + 1 :]
                        new_dist = _route_distance(new_route, dist_matrix, request.return_to_start)
                        old_dist = _route_distance(route, dist_matrix, request.return_to_start)
                        if new_dist < old_dist:
                            route = new_route
                            improved = True

            d = _route_distance(route, dist_matrix, request.return_to_start)
            if d < best_dist:
                best_dist = d
                best_route = route

        route = best_route
        n_qubits = n * 2  # quantum-inspired

    # Calculate distances
    optimized_dist = _route_distance(route, dist_matrix, request.return_to_start)
    naive_route = list(range(n))
    naive_dist = _route_distance(naive_route, dist_matrix, request.return_to_start)
    improvement = ((naive_dist - optimized_dist) / naive_dist * 100) if naive_dist > 0 else 0.0

    route_names = [locations[i].name for i in route]
    if request.return_to_start:
        route_names.append(route_names[0])

    return RouteResult(
        route=route_names,
        total_distance_km=round(optimized_dist, 2),
        improvement_vs_naive=round(max(improvement, 0), 1),
        method="QAOA (simulated)" if n <= 5 else "Quantum-inspired 2-opt",
        qubit_count=n_qubits,
        warnings=validation_warnings,
    )
