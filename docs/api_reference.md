# API Reference

This document details the functions available in the `slicks` package.

## Core Functions

### `slicks.connect_influxdb3`

Updates the global InfluxDB connection settings dynamically.

```python
slicks.connect_influxdb3(url=None, token=None, org=None, db=None)
```
- **url** *(str)*: The InfluxDB host URL (e.g., `"http://localhost:8086"`).
- **token** *(str)*: Authentication token.
- **org** *(str)*: Organization name (default: `"Docs"`).
- **db** *(str)*: Database/Bucket name (default: `"WFR25"`).

---

### `slicks.fetch_telemetry`

The primary function to retrieve data. It handles querying, pivoting, resampling, and movement filtering.

```python
slicks.fetch_telemetry(start_time, end_time, signals=None, client=None, filter_movement=True)
```

- **start_time** *(datetime)*: Start of the query range.
- **end_time** *(datetime)*: End of the query range.
- **signals** *(str or list[str])*: A single sensor name or a list of sensor names to fetch. Defaults to standard configuration if None.
- **client** *(InfluxDBClient3, optional)*: An existing client instance (advanced use).
- **filter_movement** *(bool)*: If `True` (default), strips out rows where the car is stationary. If `False`, returns all raw data.

**Returns:** `pandas.DataFrame` indexed by time, with 1-second resolution. Returns `None` if no data is found.

---

### `slicks.discover_sensors`

Scans the database to find which sensors actually recorded data during a time period.

```python
slicks.discover_sensors(start_time, end_time, chunk_size_days=1)
```

- **start_time** *(datetime)*: Start of scan.
- **end_time** *(datetime)*: End of scan.
- **chunk_size_days** *(int)*: How many days to query at once (prevents timeouts).

**Returns:** `list[str]` of unique sensor names sorted alphabetically.

---

## Analysis Tools

### `slicks.get_movement_segments`

Identifies distinct "laps" or driving sessions by detecting gaps in movement.

```python
slicks.get_movement_segments(df, speed_column="INV_Motor_Speed", threshold=100.0, max_gap_seconds=60.0)
```

- **df** *(pd.DataFrame)*: DataFrame containing at least a speed column.
- **max_gap_seconds** *(float)*: Time in seconds to wait before declaring a new "segment" (default: 60s).

**Returns:** `pandas.DataFrame` with columns `start_time`, `end_time`, `duration`, `state` ("Moving"/"Idle"), and `mean_speed`.

### `slicks.detect_movement_ratio`

Calculates the percentage of time the car was active.

```python
slicks.detect_movement_ratio(df, speed_column="INV_Motor_Speed")
```

**Returns:** `dict` containing `total_rows`, `moving_rows`, `idle_rows`, and `movement_ratio` (0.0 - 1.0).
