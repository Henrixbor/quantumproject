"""Quantum meeting scheduler using QAOA.

Models meeting scheduling as a constraint satisfaction / optimization
problem and solves via QAOA for maximum participant satisfaction.
"""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

from src.models.schemas import MeetingScheduleRequest, MeetingScheduleResult
from src.quantum.qaoa import qaoa_optimize

# Map day names to indices
DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _parse_slot(slot: str) -> tuple[int, int, int]:
    """Parse a slot string like 'Mon 9:00-11:00' into (day, start_hour, end_hour)."""
    match = re.match(r"(\w+)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", slot.strip())
    if not match:
        return (0, 9, 10)  # fallback
    day_str = match.group(1).lower()[:3]
    day = DAY_MAP.get(day_str, 0)
    start = int(match.group(2))
    end = int(match.group(4))
    return (day, start, end)


def _slot_to_key(day: int, hour: int) -> str:
    """Convert day/hour to readable slot key."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return f"{days[day]} {hour:02d}:00-{hour + 1:02d}:00"


async def optimize_schedule(request: MeetingScheduleRequest) -> MeetingScheduleResult:
    """Find optimal meeting schedule using quantum optimization."""
    participants = request.participants
    duration_hours = max(1, request.duration_minutes // 60)
    num_meetings = request.num_meetings

    # Collect all unique hourly slots
    all_slots: list[tuple[int, int]] = []  # (day, hour)
    slot_set: set[tuple[int, int]] = set()

    participant_available: dict[int, set[int]] = defaultdict(set)  # participant_idx -> slot_indices
    participant_preferred: dict[int, set[int]] = defaultdict(set)

    for p_idx, p in enumerate(participants):
        for slot_str in p.available_slots:
            day, start, end = _parse_slot(slot_str)
            for hour in range(start, end):
                key = (day, hour)
                if key not in slot_set:
                    slot_set.add(key)
                    all_slots.append(key)
                slot_idx = all_slots.index(key) if key in all_slots else len(all_slots) - 1
                participant_available[p_idx].add(slot_idx)

        for slot_str in p.preferences:
            day, start, end = _parse_slot(slot_str)
            for hour in range(start, end):
                key = (day, hour)
                if key in slot_set:
                    slot_idx = all_slots.index(key)
                    participant_preferred[p_idx].add(slot_idx)

    n_slots = len(all_slots)
    n_participants = len(participants)

    if n_slots == 0:
        return MeetingScheduleResult(
            scheduled_slots=["No valid slots found"],
            attendance={},
            satisfaction_score=0.0,
            method="QAOA (simulated)",
            qubit_count=0,
        )

    # Build QUBO: binary variable per slot (1 = selected for meeting)
    n_qubits = min(n_slots, 20)  # cap for performance
    Q = np.zeros((n_qubits, n_qubits))

    for s in range(n_qubits):
        # Reward: how many weighted participants can attend
        attendance_score = 0.0
        preference_bonus = 0.0
        for p_idx in range(n_participants):
            weight = participants[p_idx].priority
            if s in participant_available[p_idx]:
                attendance_score += weight
            if s in participant_preferred[p_idx]:
                preference_bonus += weight * 0.5

        # Negative = minimize in QUBO = maximize attendance
        Q[s, s] -= attendance_score + preference_bonus

    # Penalty: select exactly num_meetings slots
    penalty = 10.0
    for s in range(n_qubits):
        Q[s, s] += penalty * (1 - 2 * num_meetings / n_qubits)
        for t in range(s + 1, n_qubits):
            Q[s, t] += 2 * penalty / n_qubits

    # Run QAOA
    bitstring, _ = qaoa_optimize(Q, num_layers=2, num_shots=512)

    # Select top slots by bitstring value
    slot_scores = list(enumerate(bitstring[:n_qubits]))
    slot_scores.sort(key=lambda x: x[1], reverse=True)
    selected_slots = [idx for idx, _ in slot_scores[:num_meetings]]

    # Build results
    scheduled = []
    attendance: dict[str, list[str]] = {}

    total_satisfaction = 0.0
    max_possible = 0.0

    for slot_idx in selected_slots:
        if slot_idx < len(all_slots):
            day, hour = all_slots[slot_idx]
            slot_name = _slot_to_key(day, hour)
            scheduled.append(slot_name)

            attendees = []
            for p_idx, p in enumerate(participants):
                max_possible += p.priority
                if slot_idx in participant_available[p_idx]:
                    attendees.append(p.name)
                    total_satisfaction += p.priority
                    if slot_idx in participant_preferred[p_idx]:
                        total_satisfaction += p.priority * 0.2  # preference bonus

            attendance[slot_name] = attendees

    satisfaction = total_satisfaction / max_possible if max_possible > 0 else 0.0

    return MeetingScheduleResult(
        scheduled_slots=scheduled,
        attendance=attendance,
        satisfaction_score=round(min(satisfaction, 1.0), 2),
        method="QAOA (simulated)",
        qubit_count=n_qubits,
    )
