# API Findings --- Elexon BMRS

## 1. Objective and scope

This phase investigated the Elexon BMRS API and extracted historical
wind generation actuals and forecasts for January 2026.

The purpose of the extraction is to establish whether the API provides
the data and publication timestamps needed for a later day-ahead
forecast evaluation.

**Scope of this phase:** API investigation, data extraction,
data-structure inspection and basic coverage validation.
Forecast-versus-actual accuracy calculations and procurement-impact
analysis are outside this phase.

## 2. API and datasets investigated

The Elexon BMRS API was accessed through the dataset stream endpoints:

-   **FUELHH** --- half-hourly generation by fuel type, used here for
    actual wind generation.
-   **WINDFOR** --- wind generation forecast records, including forecast
    publication time, delivery time and generation.

Official documentation:

-   [FUELHH stream
    endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
-   [WINDFOR stream
    endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
-   [Elexon API Swagger
    specification](https://data.elexon.co.uk/swagger/v1/swagger.json)

## 3. Data extraction

The following requests were used from the project root
(`~/Desktop/Windsight`).

### 3.1 Actual wind generation --- FUELHH

``` bash
curl -L "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-31&fuelType=WIND" \
-o backend/raw/actual_generation.json
```

Saved file:

`backend/raw/actual_generation.json`

Observed extraction results:

-   Total records: **1,488**
-   Unique `startTime` values: **1,488**
-   Settlement dates: **31 dates**, covering 1--31 January 2026
-   Expected resolution: **48 half-hourly intervals per settlement day**
-   Dataset: `FUELHH`
-   Fuel type: `WIND`

The record structure includes:

-   `dataset`
-   `publishTime`
-   `startTime`
-   `settlementDate`
-   `settlementPeriod`
-   `fuelType`
-   `generation`

Example record:

``` json
{
  "dataset": "FUELHH",
  "publishTime": "2026-02-01T00:00:00Z",
  "startTime": "2026-01-31T23:30:00Z",
  "settlementDate": "2026-01-31",
  "settlementPeriod": 48,
  "fuelType": "WIND",
  "generation": 8849
}
```

`generation` is an average power value in MW for the settlement
interval. The `startTime` identifies the delivery interval. The
`publishTime` identifies when the actual record was published; it can be
after the delivery interval, as expected for outturn data.

### 3.2 Wind forecasts --- WINDFOR

The following request retrieved forecast publications across a window
that includes the January delivery period:

``` bash
curl -fL "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=2025-12-01T00:00:00Z&publishDateTimeTo=2026-02-01T00:00:00Z" \
-o backend/raw/forecast_generation.json
```

Saved file:

`backend/raw/forecast_generation.json`

Observed extraction results:

-   Total records returned: **36,208**
-   Records with January 2026 delivery `startTime`: **18,080**
-   Unique January delivery `startTime` values: **744**
-   Delivery resolution in the retrieved data: **hourly**
-   Forecast publications per delivery hour vary; they are not a fixed
    count.

The record structure includes:

-   `dataset`
-   `publishTime`
-   `startTime`
-   `generation`

Example record:

``` json
{
  "dataset": "WINDFOR",
  "publishTime": "2026-01-31T22:30:00Z",
  "startTime": "2026-01-30T21:00:00Z",
  "generation": 17683
}
```

The API request filters on forecast publication time, not solely on
delivery time. Therefore, the returned raw file contains delivery
intervals outside January. The observed `startTime` range in the
response was:

-   Earliest: `2025-11-30T21:00:00Z`
-   Latest: `2026-02-02T21:00:00Z`

For January delivery analysis, records were identified by filtering
`startTime` to the half-open UTC range:

`2026-01-01T00:00:00Z <= startTime < 2026-02-01T00:00:00Z`

The raw extraction was retained unchanged.

## 4. Forecast publication versions

Multiple WINDFOR records can exist for the same delivery `startTime`.
These represent different forecast publications and must not be treated
as duplicate records merely because they share a delivery timestamp.

For January 2026, the version-count distribution was:

    Publications per delivery hour   Number of delivery hours
  -------------------------------- --------------------------
                                16                          2
                                24                        712
                                32                         30
                         **Total**                    **744**

This confirms that publication frequency varies by delivery interval.
The raw data retains the available publication versions.

## 5. Decision-time selection test

A working procurement decision cutoff of **12:00 noon UK local time on
the day before delivery** was used to test whether the historical
forecast available at decision time could be reconstructed.

This is an assumption for the analysis and must be confirmed with the
client. The implementation uses the `Europe/London` timezone so that
GMT/BST changes are handled correctly. Timestamps in the source data are
UTC.

For each delivery interval, the selection rule is:

1.  Convert the delivery `startTime` to `Europe/London`.
2.  Calculate 12:00 local time on the previous calendar day.
3.  Convert that cutoff to UTC.
4.  Retain records whose `publishTime` is at or before the cutoff.
5.  Select the eligible record with the latest `publishTime`.

A sample was checked for delivery at `2026-01-15T12:00:00Z`:

-   Cutoff: `2026-01-14T12:00:00Z` (GMT)
-   Selected publication: `2026-01-14T11:30:00Z`
-   Selected generation: **11,351 MW**
-   Later publications, including `2026-01-14T15:30:00Z`, were excluded
    because they occurred after the cutoff.

The selection script produced:

  Validation                            Result
  ----------------------------------- --------
  Raw forecast records                  36,208
  January delivery records              18,080
  Unique January delivery intervals        744
  Selected eligible forecasts              744
  Missing eligible forecasts                 0

The processed output was saved separately as:

`backend/processed/january_2026_processed.json`

The original raw forecast file was not modified.

## 6. API behaviour and data-quality observations

The following observations were made during the API investigation:

-   One-year requests were successfully tested during the broader API
    investigation. The maximum supported request size was not
    established.
-   No pagination parameters or `Link`/`Content-Range` pagination
    headers were observed in the tested responses. This is an
    observation from testing, not proof that pagination is never used or
    supported.
-   Three-month sliced retrieval did not produce additional unique
    records after deduplication in the tested comparison.
-   FUELHH slice-boundary overlaps were observed in the broader
    extraction tests. Exact-row deduplication was used there; records
    with different forecast publication times should not be discarded as
    duplicates.
-   The dataset schemas permit nullable fields. No null or missing
    `generation` values were observed in the one-year samples tested
    during the investigation. This should not be interpreted as a
    guarantee that future or all historical responses are complete.
-   Zero generation values were present in the broader FUELHH sample and
    are valid observations; they must not be converted into missing
    values.
-   Elexon documentation notes that FUELHH settlement-date filters
    cannot be combined with publish-date filters.

## 7. Important limitations and considerations

1.  **Cutoff confirmation:** 12:00 noon UK local time on the day before
    delivery is a working assumption, not a confirmed client
    requirement.
2.  **Dataset coverage:** this extraction covers wind only. It does not
    establish total renewable generation coverage, which may also
    require solar and other relevant datasets.
3.  **Different time resolutions:** FUELHH actuals are half-hourly while
    the retrieved WINDFOR delivery forecasts are hourly. A later
    analysis must define and validate an aggregation/alignment method
    before calculating accuracy.
4.  **Measurement comparability:** confirm that the actual and forecast
    series have compatible scope and definitions before interpreting
    forecast errors.
5.  **Forecast availability:** all 744 January hourly intervals in this
    sample had at least one forecast publication at or before the
    assumed cutoff. This result applies to this extraction and cutoff
    assumption.
6.  **No accuracy or financial conclusions yet:** this phase has not
    calculated forecast accuracy, imbalance exposure, purchasing volumes
    or cost savings.

## 8. Files produced

  ----------------------------------------------------------------------------
  File                                     Description
  ---------------------------------------- -----------------------------------
  `backend/raw/actual_generation.json`     January 2026 FUELHH actual wind
                                           generation records

  `backend/raw/forecast_generation.json`   WINDFOR forecast publication
                                           records retrieved using the
                                           publication-time window

  `backend/select_forecasts.py`            Script selecting the latest
                                           eligible forecast before the
                                           assumed procurement cutoff

  `backend/processed/january_2026_processed.json`       One selected forecast for each
                                           January delivery hour
  ----------------------------------------------------------------------------

## 9. Phase 2 conclusion

The Elexon BMRS API successfully supplied the January 2026 wind
actual-generation data and the forecast publication history required for
the next stage of analysis.

The extraction contains 1,488 half-hourly actual records and 18,080
forecast records associated with 744 unique hourly January delivery
intervals. Forecast publication counts vary by delivery interval.
Applying the working noon UK-local previous-day cutoff selected one
eligible forecast for each of the 744 delivery hours, with no missing
eligible forecasts in this sample.

**Phase 2 has therefore completed its API investigation, extraction and
initial validation objectives.** The next phase can undertake the
validated alignment of hourly forecasts and half-hourly actuals,
calculate forecast accuracy, and assess the implications for
procurement. These activities have not been performed as part of this
findings document.
