# Getting Started with Slicks Telemetry

Welcome to the **Slicks Telemetry** package. This guide will help you install the package and write your first script to analyze race data.

## 1. Installation

### For Users
To install the latest stable version directly from GitHub:

```bash
pip install git+https://github.com/Western-Formula-Racing/wfr-telemetry.git
```

### For Developers (Contributing)
If you want to modify the package source code:

```bash
git clone https://github.com/Western-Formula-Racing/wfr-telemetry.git
cd wfr-telemetry
pip install -e .
```

---

## 2. Quick Start

Here is the minimal code needed to connect to the database and download data for a specific sensor.

### Step 1: Import and Configure
The package connects to the InfluxDB database automatically using defaults, but you can configure it explicitly.

```python
import slicks as wfr
from datetime import datetime

# Optional: Configure manually (or use .env file / defaults)
wfr.configure(
    url="http://your-influx-server:8086",
    token="your-token-here", # Ask Data Lead for your token
    org="Docs",
    db="WFR25"
)
```

### Step 2: Define Time Range
Always use Python's `datetime` objects.

```python
start = datetime(2025, 9, 28, 12, 0, 0) # Sept 28, 2025 at 12:00 PM
end   = datetime(2025, 9, 28, 14, 0, 0) # Sept 28, 2025 at 02:00 PM
```

### Step 3: Fetch Data
You can request a single sensor or a list of sensors.

```python
# Fetch Motor Speed
df = wfr.fetch_telemetry(start, end, "INV_Motor_Speed")

if df is not None:
    print(df.head())
    print(f"Average Speed: {df['INV_Motor_Speed'].mean():.2f}")
else:
    print("No data found for this range.")
```

---

## 3. Key Concepts

### Movement Filtering (Default: On)
By default, `fetch_telemetry` filters out data when the car is stationary (idling in the pits). This ensures your averages (like average speed or temp) represent **driving conditions**.

To see raw data (including pit/idle time), pass `filter_movement=False`:

```python
df_raw = wfr.fetch_telemetry(start, end, "INV_Motor_Speed", filter_movement=False)
```

### Auto-Resampling
Data is automatically aligned to a **1-second frequency** (`1s`). This makes it easy to plot multiple sensors on the same graph without worrying about mismatched timestamps.
