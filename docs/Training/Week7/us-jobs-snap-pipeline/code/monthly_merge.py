"""
Apply source updates to current facts and return queryable history events.

This module has no filesystem, network, or GCP dependencies.
The caller owns window validation, input loading, and publication.

Event types:
- initial_observation: first non-NULL measurement received.
- revision: a previously observed measurement changes.
- status_change: availability or quality changes without a value change.

History is returned to the caller; it is not persisted here.
"""

import hashlib
import json


METADATA_FIELDS = {
    "first_loaded_at", "last_changed_at", "revision_count"
}

# Each measurement's corresponding availability/quality status.
MEASURE_STATUS = {
    "total_nonfarm_jobs": "jobs_status",
    "unemployment_rate_pct": "unemployment_status",
    "industry_nonfarm_jobs": "jobs_status",
    "snap_persons": "snap_persons_status",
    "snap_households": "snap_households_status",
    "snap_benefit_cost_usd": "snap_benefits_status",
}

# Additional quality information associated with a measurement.
MEASURE_QUALITY = {
    "snap_benefit_cost_usd": "benefit_review_required",
}


def index_rows(rows, keys):
    """Build an index while rejecting NULL or duplicate business keys."""
    indexed = {}

    for row in rows:
        key = tuple(row[field] for field in keys)

        if any(value is None for value in key):
            raise ValueError(f"NULL business key: {key}")
        if key in indexed:
            raise ValueError(f"Duplicate business key: {key}")

        indexed[key] = dict(row)

    return indexed


def build_event_id(refresh_run_id, fact_table, source, business_key, measure):
    """
    Give a logical change a stable identity across retries.

    Retries of the same refresh must reuse refresh_run_id.
    A single accepted source contribution per key/measure/run is expected.
    """
    identity = {
        "refresh_run_id": refresh_run_id,
        "fact_table": fact_table,
        "source": source,
        "business_key": business_key,
        "measure": measure,
    }
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def merge_records(
    current_rows,
    incoming_rows,
    keys,
    content_fields,
    source,
    detected_at,
    *,
    fact_table,
    refresh_run_id,
):
    """
    Update one source's contribution while preserving other source fields.

    revision_count counts source updates that revise existing measurements.
    Individual measure adjustment counts come from revision events.

    A valid-to-NULL change requires review rather than automatic acceptance.
    """
    if not fact_table or not refresh_run_id:
        raise ValueError("Fact table and logical refresh run ID are required")

    measures = [
        field for field in content_fields if field in MEASURE_STATUS
    ]
    if not measures:
        raise ValueError("No recognized measurement fields supplied")

    allowed_fields = set(measures)
    for measure in measures:
        allowed_fields.add(MEASURE_STATUS[measure])
        quality_field = MEASURE_QUALITY.get(measure)
        if quality_field:
            allowed_fields.add(quality_field)

    if set(content_fields) - allowed_fields:
        raise ValueError("Unrecognized content fields")

    current = index_rows(current_rows, keys)
    incoming = index_rows(incoming_rows, keys)

    events = []
    stats = {
        "inserted": 0,
        "revised": 0,
        "unchanged": 0,
        "initial_observations": 0,
        "status_changes": 0,
    }

    for key, candidate in incoming.items():
        if METADATA_FIELDS.intersection(candidate):
            raise ValueError("Incoming data must not set revision metadata")

        for field in content_fields:
            if field not in candidate:
                raise ValueError(f"Missing incoming field: {field}")

        is_insert = key not in current
        previous = current.get(key, {})

        changed = is_insert or any(
            previous.get(field) != candidate[field]
            for field in content_fields
        )

        if is_insert:
            updated = {
                **candidate,
                "first_loaded_at": detected_at,
                "last_changed_at": detected_at,
                "revision_count": 0,
            }
            stats["inserted"] += 1
        else:
            # Advance source lineage without changing content timestamps
            # when measurements and statuses are identical.
            updated = {**previous, **candidate}

        row_events = []
        business_key = dict(zip(keys, key))

        # Include only the changing source's supplied lineage columns.
        lineage_fields = [
            field for field in candidate
            if field not in keys and field not in content_fields
        ]

        for measure in measures:
            status_field = MEASURE_STATUS[measure]
            quality_field = MEASURE_QUALITY.get(measure)

            old_value = previous.get(measure)
            new_value = candidate[measure]
            old_status = previous.get(status_field)
            new_status = candidate.get(status_field)

            old_quality = (
                previous.get(quality_field) if quality_field else None
            )
            new_quality = (
                candidate.get(quality_field) if quality_field else None
            )

            if old_value is not None and new_value is None:
                raise ValueError(
                    f"{source}: valid-to-NULL change requires review: "
                    f"{key}/{measure}"
                )

            if old_value is None and new_value is not None:
                event_type = "initial_observation"
            elif old_value != new_value:
                event_type = "revision"
            elif (
                old_status != new_status
                or old_quality != new_quality
            ):
                event_type = "status_change"
            else:
                continue

            row_events.append({
                "event_id": build_event_id(
                    refresh_run_id, fact_table, source,
                    business_key, measure,
                ),
                "event_type": event_type,
                "refresh_run_id": refresh_run_id,
                "fact_table": fact_table,
                "source": source,
                "business_key": business_key,
                "date_key": candidate.get("date_key"),
                "state_key": candidate.get("state_key"),
                "industry_key": candidate.get("industry_key"),
                "measure": measure,
                "detected_at": detected_at,
                "old_value": old_value,
                "new_value": new_value,
                "value_difference": (
                    new_value - old_value
                    if old_value is not None and new_value is not None
                    else None
                ),
                "old_status": old_status,
                "new_status": new_status,
                "old_quality_flag": old_quality,
                "new_quality_flag": new_quality,
                "old_lineage": {
                    field: previous.get(field)
                    for field in lineage_fields
                },
                "new_lineage": {
                    field: candidate[field]
                    for field in lineage_fields
                },
            })

        has_revision = any(
            event["event_type"] == "revision" for event in row_events
        )

        if not is_insert:
            if changed:
                updated["last_changed_at"] = detected_at
            else:
                stats["unchanged"] += 1

            if has_revision:
                updated["revision_count"] = previous["revision_count"] + 1
                stats["revised"] += 1

        for event in row_events:
            event["fact_revision_count"] = updated["revision_count"]

            if event["event_type"] == "initial_observation":
                stats["initial_observations"] += 1
            elif event["event_type"] == "status_change":
                stats["status_changes"] += 1

        events.extend(row_events)
        current[key] = updated

    return list(current.values()), events, stats