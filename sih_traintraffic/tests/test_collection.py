from railradar.collection import (
    CollectionConfig,
    SlidingWindowRateLimiter,
    plan_collection,
)


def test_planner_maximizes_live_observations_without_exceeding_budget():
    config = CollectionConfig(duration_seconds=20 * 60, quota_total=1000)

    plan = plan_collection(config, available_trains=359)

    assert plan.train_count == 10
    assert plan.polling_interval_seconds == 60
    assert plan.expected_live_requests == 200
    assert plan.expected_total_requests <= plan.safe_budget


def test_planner_reduces_to_a_safe_configuration_for_a_small_budget():
    config = CollectionConfig(
        duration_seconds=60,
        quota_total=20,
        safety_fraction=0.85,
        candidate_train_counts=(5, 6, 7, 8, 9, 10),
    )

    plan = plan_collection(config, available_trains=10)

    assert plan.expected_total_requests <= plan.safe_budget
    assert plan.train_count < 10


def test_rate_limiter_spaces_requests_and_never_has_more_than_ten_in_window():
    current = [0.0]
    sleeps = []

    def clock():
        return current[0]

    def sleeper(seconds):
        sleeps.append(seconds)
        current[0] += seconds

    limiter = SlidingWindowRateLimiter(
        max_requests=10,
        window_seconds=60,
        minimum_spacing_seconds=6.1,
        sleeper=sleeper,
        clock=clock,
    )
    request_times = []
    for _ in range(20):
        limiter.wait_for_slot()
        request_times.append(current[0])

    assert all(b - a >= 6.1 - 1e-9 for a, b in zip(request_times, request_times[1:]))
    assert len(sleeps) == 19
