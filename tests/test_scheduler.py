import pytest

from src.models.schemas import MeetingParticipant, MeetingScheduleRequest
from src.quantum.scheduler import optimize_schedule


@pytest.mark.asyncio
async def test_basic_scheduling():
    request = MeetingScheduleRequest(
        participants=[
            MeetingParticipant(
                name="Alice",
                available_slots=["Mon 9:00-11:00", "Tue 14:00-16:00"],
            ),
            MeetingParticipant(
                name="Bob",
                available_slots=["Mon 10:00-12:00", "Tue 14:00-15:00"],
            ),
        ],
    )
    result = await optimize_schedule(request)

    assert len(result.scheduled_slots) >= 1
    assert result.satisfaction_score >= 0
    assert result.qubit_count >= 0


@pytest.mark.asyncio
async def test_scheduling_with_preferences():
    request = MeetingScheduleRequest(
        participants=[
            MeetingParticipant(
                name="Alice",
                available_slots=["Mon 9:00-12:00", "Wed 9:00-12:00"],
                preferences=["Wed 9:00-12:00"],
                priority=2.0,
            ),
            MeetingParticipant(
                name="Bob",
                available_slots=["Mon 9:00-12:00", "Wed 10:00-12:00"],
            ),
        ],
    )
    result = await optimize_schedule(request)

    assert result.satisfaction_score > 0
    assert len(result.attendance) >= 1


@pytest.mark.asyncio
async def test_multiple_meetings():
    request = MeetingScheduleRequest(
        participants=[
            MeetingParticipant(
                name="Alice",
                available_slots=["Mon 9:00-12:00", "Tue 9:00-12:00", "Wed 9:00-12:00"],
            ),
            MeetingParticipant(
                name="Bob",
                available_slots=["Mon 10:00-12:00", "Tue 10:00-12:00", "Wed 10:00-12:00"],
            ),
        ],
        num_meetings=2,
    )
    result = await optimize_schedule(request)

    assert len(result.scheduled_slots) == 2
