-- ============ Indexes (created after loading, which is faster) ============
CREATE INDEX IF NOT EXISTS idx_fact_date      ON fact_crime (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_location  ON fact_crime (location_key);
CREATE INDEX IF NOT EXISTS idx_fact_crimetype ON fact_crime (crime_type_key);
CREATE INDEX IF NOT EXISTS idx_fact_loctype   ON fact_crime (location_type_key);

CREATE INDEX IF NOT EXISTS idx_loc_area     ON dim_location (community_area);
CREATE INDEX IF NOT EXISTS idx_loc_district ON dim_location (district);
CREATE INDEX IF NOT EXISTS idx_date_year    ON dim_date (year, month);

-- ============ Materialized view: pre-aggregated counts ============
DROP MATERIALIZED VIEW IF EXISTS mv_crime_summary;

CREATE MATERIALIZED VIEW mv_crime_summary AS
SELECT
    d.year,
    d.month,
    d.season,
    l.district,
    c.primary_type,
    c.crime_group,
    c.is_violent,
    COUNT(*)                          AS crime_count,
    SUM(f.arrest::int)                AS arrest_count
FROM fact_crime f
JOIN dim_date       d ON d.date_key       = f.date_key
JOIN dim_location   l ON l.location_key   = f.location_key
JOIN dim_crime_type c ON c.crime_type_key = f.crime_type_key
GROUP BY d.year, d.month, d.season, l.district,
         c.primary_type, c.crime_group, c.is_violent;

CREATE INDEX IF NOT EXISTS idx_mv_year_month ON mv_crime_summary (year, month);
CREATE INDEX IF NOT EXISTS idx_mv_district   ON mv_crime_summary (district);
CREATE INDEX IF NOT EXISTS idx_mv_type       ON mv_crime_summary (primary_type);

-- Keep the view private: the website will go through our API, not Supabase's public API
REVOKE ALL ON mv_crime_summary FROM anon, authenticated;

ANALYZE;