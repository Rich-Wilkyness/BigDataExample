"""Check initial observations, revisions, retries, and metadata preservation."""

from datetime import datetime, timezone

from monthly_merge import merge_records


def verify_merge_contract():
    earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = datetime(2026, 2, 1, tzinfo=timezone.utc)

    fields = ["total_nonfarm_jobs", "jobs_status"]
    context = {
        "fact_table": "test_fact",
        "refresh_run_id": "test-refresh-001",
    }

    original = [{
        "id": "example",
        "total_nonfarm_jobs": 10,
        "jobs_status": "available",
        "first_loaded_at": earlier,
        "last_changed_at": earlier,
        "revision_count": 0,
    }]
    candidate = [{
        "id": "example",
        "total_nonfarm_jobs": 11,
        "jobs_status": "available",
    }]

    def merge(current, incoming, when=later):
        return merge_records(
            current, incoming, ["id"], fields,
            "test_source", when, **context,
        )

    # A real revision preserves first-load time and records the difference.
    updated, events, stats = merge(original, candidate)
    assert stats["revised"] == 1
    assert updated[0]["first_loaded_at"] == earlier
    assert updated[0]["last_changed_at"] == later
    assert updated[0]["revision_count"] == 1
    assert events[0]["event_type"] == "revision"
    assert events[0]["value_difference"] == 1

    # Retrying from the same original input produces the same event identity.
    _, retried_events, _ = merge(original, candidate, earlier)
    assert retried_events[0]["event_id"] == events[0]["event_id"]

    # Reprocessing already accepted values creates no additional event.
    repeated, events, stats = merge(updated, candidate)
    assert repeated == updated
    assert events == []
    assert stats["unchanged"] == 1

    # A brand-new measurement is an observation, not a revision.
    inserted, events, stats = merge([], candidate)
    assert stats["inserted"] == 1
    assert inserted[0]["revision_count"] == 0
    assert events[0]["event_type"] == "initial_observation"

    # A measurement arriving on an existing pending row is also initial.
    pending = [{
        **original[0],
        "total_nonfarm_jobs": None,
        "jobs_status": "not_yet_published",
    }]
    arrived, events, stats = merge(pending, candidate)
    assert arrived[0]["first_loaded_at"] == earlier
    assert arrived[0]["last_changed_at"] == later
    assert arrived[0]["revision_count"] == 0
    assert events[0]["event_type"] == "initial_observation"

    # A status-only change is tracked separately.
    status_update = [{
        **candidate[0],
        "jobs_status": "review_required",
    }]
    status_result, events, stats = merge(updated, status_update)
    assert events[0]["event_type"] == "status_change"
    assert status_result[0]["revision_count"] == 1

    # An unexplained loss of an accepted measurement must fail.
    withdrawn = [{
        **candidate[0],
        "total_nonfarm_jobs": None,
        "jobs_status": "source_missing",
    }]
    try:
        merge(updated, withdrawn)
    except ValueError:
        pass
    else:
        raise AssertionError("Valid-to-NULL change was accepted")


if __name__ == "__main__":
    verify_merge_contract()
    print("All monthly merge contract checks passed.")