-- 1. ROLL-UP: crimes per year, then per month of one year
SELECT year, SUM(crime_count) AS crimes
FROM mv_crime_summary
GROUP BY year
ORDER BY year;

SELECT year, month, SUM(crime_count) AS crimes
FROM mv_crime_summary
WHERE year = 2025
GROUP BY year, month
ORDER BY month;

-- 2. DRILL-DOWN: district, then beats inside one district
SELECT district, SUM(crime_count) AS crimes
FROM mv_crime_summary
GROUP BY district
ORDER BY crimes DESC;

SELECT l.beat, COUNT(*) AS crimes
FROM fact_crime f
JOIN dim_location l ON l.location_key = f.location_key
WHERE l.district = 11
GROUP BY l.beat
ORDER BY crimes DESC;

-- 3. SLICE: only THEFT, per year
SELECT year, SUM(crime_count) AS crimes
FROM mv_crime_summary
WHERE primary_type = 'THEFT'
GROUP BY year
ORDER BY year;

-- 4. DICE: THEFT and BATTERY, 2025, summer months
SELECT month, primary_type, SUM(crime_count) AS crimes
FROM mv_crime_summary
WHERE year = 2025
  AND primary_type IN ('THEFT', 'BATTERY')
  AND season = 'SUMMER'
GROUP BY month, primary_type
ORDER BY month, primary_type;

-- 5. TOP 10 community areas by crimes per 1,000 residents
SELECT l.community_area, l.area_name, l.population,
       COUNT(*) AS crimes,
       ROUND(COUNT(*) * 1000.0 / l.population, 1) AS crimes_per_1000
FROM fact_crime f
JOIN dim_location l ON l.location_key = f.location_key
GROUP BY l.community_area, l.area_name, l.population
ORDER BY crimes_per_1000 DESC
LIMIT 10;

-- 6. CRIME BY HOUR OF DAY
SELECT hour, COUNT(*) AS crimes
FROM fact_crime
GROUP BY hour
ORDER BY hour;