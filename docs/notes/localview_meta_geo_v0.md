# LocalView metadata geo note (v0)

Inspected `data/raw/localview/meta_localview.parquet` on 2026-09-16 PT. The parquet has 301,659 rows and 16 columns. Geo-relevant fields are:

- `st_fips` (string, non-null): the LocalView location identifier; observed 5-digit and 7-digit values, plus some multi-value/compound strings.
- `place_names` (string, non-null): Census-style place labels, including city/town/village/borough labels and county labels.
- `multiple_cities` (int64, values 0/1): indicator for records covering multiple cities.
- `predicted_st_fips` (string, non-null but often empty; also includes `UNKNOWN`): alternate/best-guess location identifier for multi-city records.

Other fields are video/meeting metadata (`id`, `title`, `description`, dates, channel and engagement fields, duration, and `government_type`). There is no dedicated `county_fips` or `county` column.

## County-FIPS finding and crosswalk proposal

County FIPS is present *implicitly* in `st_fips` for county-labeled records, rather than as a separate field: for example, `place_names = El Paso County` occurs with `st_fips = 48141`, a 5-digit state+county FIPS. City/place records commonly have 7-digit state+place FIPS (for example `1703012` with `Aurora city`). Therefore, do not treat every `st_fips` value as a place code or assume that a 5-digit value in `predicted_st_fips` is a city code; validate against official Census geography and the label.

For a derived crosswalk, first validate 5-digit county-labeled identifiers against the official county FIPS table. For 7-digit place identifiers, join state+place FIPS to an official Census place-to-county relationship (Gazetteer/TIGER-derived), retaining one-to-many relationships for places spanning counties. Use `place_names`, `multiple_cities`, and non-empty `predicted_st_fips` to flag ambiguous records for review; preserve the source identifiers and record the crosswalk source/version and confidence. Do not manufacture empirical event rows: the crosswalk should only add geography mappings to existing LocalView metadata.
