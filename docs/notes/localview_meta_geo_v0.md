# LocalView metadata geo note (v0)

Inspected `data/raw/localview/meta_localview.parquet` on 2026-09-16 PT. It has 301,659 rows and 16 columns (35,339,621 bytes; SHA-256 `a7eccd0bdf7e62399207a0caa950a0e4ea33a5677fbcef8bb72f7008b24025f5`). Geo-relevant fields are:

- `st_fips` (`string`, non-null): the codebook's concatenated state + Census FIPS location identifier; it includes 7-digit place-like values, 5-digit county-like values, and semicolon-delimited composites.
- `place_names` (`string`, non-null): Census-style city/town/village/borough and county labels.
- `multiple_cities` (`int64`, only 0/1): whether a video covers multiple cities.
- `predicted_st_fips` (`string`, non-null but often blank; also `UNKNOWN`): an alternate/best-guess identifier for multi-city records.

There is **no dedicated `county_fips` or `county` column**. County FIPS can occur implicitly in `st_fips` for county-labeled records; e.g. the observed composite `st_fips = 41059; 4175650` pairs `Umatilla County; Umatilla city`, while `1703012` is a place-like identifier for `Aurora city`. Thus, do not treat every `st_fips` value as a county or place code based only on length.

## Proposed county crosswalk

1. Preserve the raw `st_fips`, `place_names`, `multiple_cities`, and `predicted_st_fips` values; tokenize semicolon-delimited values without collapsing multi-coverage records.
2. Validate 5-digit county identifiers against an official Census county FIPS table. For 7-digit place identifiers, join state+place FIPS to an official Census place-to-county relationship (Gazetteer/TIGER-derived), retaining one-to-many relationships for places spanning counties.
3. Use county/place labels, `multiple_cities`, and non-empty `predicted_st_fips` to flag ambiguous cases for review; record the crosswalk source/version and confidence. The crosswalk should only add geography mappings to existing LocalView metadata—do not manufacture empirical event rows.
