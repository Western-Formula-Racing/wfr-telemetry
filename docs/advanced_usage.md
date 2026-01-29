# Advanced Usage & Workflows

## 1. Dynamic Sensor Discovery
Not sure what sensors are available for a specific test day? Don't guess. Use the discovery tool.

```python
from slicks import discover_sensors
from datetime import datetime

start = datetime(2025, 9, 28)
end = datetime(2025, 9, 30)

# This physically queries the DB to find what tags exist
available_sensors = discover_sensors(start, end)

print(f"Found {len(available_sensors)} sensors:")
for sensor in available_sensors:
    print(f" - {sensor}")
```

## 2. Managing Environments
You often need to switch between `Development`, `Testing`, and `Production` databases, or switch to a local replay server.

### Option A: Environment Variables (Best for CI/CD)
Set these in your shell or `.env` file before running python:
```bash
export INFLUX_URL="http://production-server:8086"
export INFLUX_DB="Season2026_Final"
```

### Option B: Runtime Configuration (Best for Scripts/Notebooks)
```python
import slicks

slicks.connect_influxdb3(
    url="http://192.168.1.50:9000",
    db="DynoTest_Day1"
)
```

## 3. Bulk Export for CSV Analysis
If you need to hand off data to the aerodynamics team who uses Excel/MATLAB, use the bulk fetcher. It handles day-by-day chunking to avoid crashing the computer.

```python
from slicks import bulk_fetch_season

# Exports entire date range to a single CSV
bulk_fetch_season(start, end, output_file="full_weekend_data.csv")
```

## 4. Customizing Movement Detection
If you are analyzing **Charging** or **Static Testing**, the default movement filter will hide your data. Disable it:

```python
# Fetch Battery Current even when car is stopped
df = slicks.fetch_telemetry(
    start, end, 
    signals="PackCurrent", 
    filter_movement=False
)
```
