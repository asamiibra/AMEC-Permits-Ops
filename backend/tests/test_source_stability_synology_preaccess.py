from __future__ import annotations

import pytest

from backend.app.storage import (
    SourceStabilityTracker,
    StabilityObservation,
    StabilityPolicy,
    StabilityState,
    classify_path_change,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def observation(size=10, modified="m1", version="v1", server_id="id1"):
    return StabilityObservation(size, modified, version, server_id)


def test_stable_observations_reach_ready_without_sleeping():
    clock = FakeClock()
    tracker = SourceStabilityTracker(StabilityPolicy(required_stable_observations=3), clock=clock)
    assert tracker.observe(observation()) == StabilityState.DETECTED
    clock.advance(1)
    assert tracker.observe(observation()) == StabilityState.WAITING_FOR_STABILITY
    clock.advance(1)
    assert tracker.observe(observation()) == StabilityState.READY_FOR_INTAKE
    assert tracker.stable_count == 3


@pytest.mark.parametrize("changed", [
    observation(size=11),
    observation(modified="m2"),
    observation(server_id="id2"),
    observation(version="v2"),
])
def test_any_source_identity_change_resets_stability(changed):
    tracker = SourceStabilityTracker(StabilityPolicy())
    tracker.observe(observation())
    assert tracker.observe(changed) == StabilityState.DETECTED
    assert tracker.stable_count == 1


def test_disappear_reappear_requires_new_stability_window():
    tracker = SourceStabilityTracker(StabilityPolicy())
    tracker.observe(observation())
    assert tracker.observe(None) == StabilityState.DETECTED
    assert tracker.observe(observation()) == StabilityState.DETECTED
    assert tracker.stable_count == 1


def test_max_wait_exhaustion_does_not_promote_old_observation():
    clock = FakeClock()
    tracker = SourceStabilityTracker(StabilityPolicy(maximum_wait_seconds=2), clock=clock)
    tracker.observe(observation())
    clock.advance(3)
    assert tracker.observe(observation()) == StabilityState.DETECTED
    assert tracker.stable_count == 1


def test_same_content_at_new_path_is_only_a_move_candidate():
    previous = observation(modified="m1", server_id="id1")
    current = observation(modified="m2", server_id="id2")
    assert classify_path_change(previous, current, content_hash_equal=True) == "MOVE_RENAME_CANDIDATE"


def test_changed_content_remains_review_required():
    assert classify_path_change(observation(), observation(modified="m2"), content_hash_equal=False) == "SOURCE_CHANGED_REVIEW_REQUIRED"


def test_stability_policy_is_not_business_identity_or_assertion_creation():
    tracker = SourceStabilityTracker(StabilityPolicy())
    tracker.observe(observation())
    tracker.observe(observation())
    assert not hasattr(tracker, "create_verified_assertion")

