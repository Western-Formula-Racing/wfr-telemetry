# Telemetry Dashboard

Slicks provides a Dear PyGui-based interactive dashboard for replaying race telemetry.

![Dashboard Preview](assets/dashboard_preview.png)

## Launching the Dashboard

You can launch the dashboard using the simple Python API:

```python
import slicks
from datetime import datetime

# 1. Define your time range (e.g. one specific run)
start = datetime(2025, 10, 4, 13, 0)
end = datetime(2025, 10, 4, 14, 0)

# 2. Launch Replay
slicks.start_replay(start, end)
```

## Features

- **Timeline**: Dark gray bar indicates the full time range. Green blocks indicate **Active Movement**. Click anywhere to scrub.
- **Friction Circle**: Visualizes Lateral vs. Longitudinal G-forces.
    - **Snail Trail (Cyan)**: Shows the path of the G-force dot over the last few seconds (cornering shape).
    - **Dot (Orange)**: Current G-force state.
- **Speed Trace**: Shows Speed (km/h) over time.

## Configuration & Physics

### Speed Calculation
Speed is estimated from Motor RPM because GPS speed is often laggy or unavailable indoors.

- **Gear Ratio**: `4.53` (Motor RPM to Wheel RPM)
- **Tire Radius**: `0.259` meters (10.2 inches)

### G-Force Calibration
The accelerometer is often mounted with a slight tilt, causing "Gravity bleeds" (e.g., constant 0.1G active).

- **Auto-Zero**: The dashboard automatically detects when the car is **Stationary** (Speed < 0.2 m/s) and calculates a bias offset.
- **Scaling**: Due to ambiguity in the sensor datasheet vs. observed noise, the dashboard includes a **G-Scale Slider** at the top.
    - **Default**: `256.0` LSB/G.
    - **Tuning**: Adjust this slider until your peak cornering forces look realistic (~1.0G - 1.5G).

## Troubleshooting

### "The dot is always on the right"
This indicates a Lateral Bias (Sensor tilt) that wasn't calibrated out.
- Ensure your dataset includes at least a few seconds of **Stationary** data at the start.
- Check the **Bias** value printed on the Friction Circle. If it is `0.0, 0.0`, calibration failed to find a stopped moment.

### "Replay is too fast/slow"
The replay attempts to match real-time, but sparse data (gaps in telemetry) can cause jumps.
- Use the **Timeline** to scrub to interesting sections.
