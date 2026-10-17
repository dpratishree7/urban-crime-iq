-- Star schema: 4 dimensions + 1 fact table
DROP TABLE IF EXISTS fact_crime, dim_date, dim_location, dim_crime_type, dim_location_type CASCADE;

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,          -- 20260910 style
    full_date     DATE NOT NULL,
    year          SMALLINT NOT NULL,
    month         SMALLINT NOT NULL,
    day           SMALLINT NOT NULL,
    day_of_week   SMALLINT NOT NULL,            -- 0 = Monday
    season        VARCHAR(6) NOT NULL,
    is_weekend    BOOLEAN NOT NULL,
    is_holiday    BOOLEAN NOT NULL,
    is_new_year   BOOLEAN NOT NULL
);

CREATE TABLE dim_location (
    location_key      SERIAL PRIMARY KEY,
    beat              VARCHAR(4) NOT NULL,
    district          SMALLINT NOT NULL,
    ward              SMALLINT,
    community_area    SMALLINT NOT NULL,
    area_name         VARCHAR(60) NOT NULL,
    population        INTEGER,
    poverty_rate      REAL,
    unemployment      REAL,
    per_capita_income INTEGER,
    hardship_index    REAL,
    pct_crowded       REAL,
    pct_no_diploma    REAL,
    pct_dependent     REAL
);

CREATE TABLE dim_crime_type (
    crime_type_key  SERIAL PRIMARY KEY,
    iucr            VARCHAR(4) NOT NULL,
    primary_type    VARCHAR(40) NOT NULL,
    description     VARCHAR(80),
    fbi_code        VARCHAR(4),
    crime_group     VARCHAR(30) NOT NULL,
    is_violent      BOOLEAN NOT NULL
);

CREATE TABLE dim_location_type (
    location_type_key     SERIAL PRIMARY KEY,
    location_description  VARCHAR(80) NOT NULL,
    location_group        VARCHAR(15) NOT NULL
);

CREATE TABLE fact_crime (
    crime_id          INTEGER PRIMARY KEY,
    date_key          INTEGER  NOT NULL REFERENCES dim_date(date_key),
    location_key      INTEGER  NOT NULL REFERENCES dim_location(location_key),
    crime_type_key    INTEGER  NOT NULL REFERENCES dim_crime_type(crime_type_key),
    location_type_key INTEGER  NOT NULL REFERENCES dim_location_type(location_type_key),
    hour              SMALLINT NOT NULL,
    arrest            BOOLEAN  NOT NULL,
    domestic          BOOLEAN  NOT NULL,
    latitude          REAL,
    longitude         REAL,
    temperature       REAL,
    rainfall          REAL
);

-- Block public API access (our FastAPI connects directly, so it is not affected)
ALTER TABLE dim_date          ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_location      ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_crime_type    ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_location_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_crime        ENABLE ROW LEVEL SECURITY;