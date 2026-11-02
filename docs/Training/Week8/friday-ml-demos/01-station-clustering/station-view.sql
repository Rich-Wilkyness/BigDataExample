-- Flatten the stored station-information feed to one latest metadata row per ID.
-- This is a VIEW over existing bronze data, not a new ingestion job or table copy.
-- -> keeps a JSON value; ->> extracts text; casts turn numeric text into SQL types.
CREATE OR REPLACE VIEW citibike_stations AS
-- PostgreSQL DISTINCT ON keeps the first row for each station ID according to
-- ORDER BY below. Ties at the same ingested_at have no extra tie-breaker here.
SELECT DISTINCT ON (station->>'station_id')
    station->>'station_id' AS station_id,
    station->>'name' AS station_name,
    (station->>'lat')::DOUBLE PRECISION AS latitude,
    (station->>'lon')::DOUBLE PRECISION AS longitude,
    (station->>'capacity')::INTEGER AS capacity,
    station->>'station_type' AS station_type,
    station->>'region_id' AS region_id
FROM citibike_bronze b
-- Each bronze payload contains an array. LATERAL expands that row's stations
-- into individual SQL rows, retaining access to its bronze ingestion timestamp.
CROSS JOIN LATERAL jsonb_array_elements(
    b.payload::jsonb->'data'->'stations'
) AS station
WHERE b.feed_type = 'station_information'
-- The ID groups candidates; descending ingestion time puts the latest first.
ORDER BY station->>'station_id', b.ingested_at DESC;
