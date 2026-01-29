from .fetcher import fetch_telemetry, bulk_fetch_season, list_target_sensors, get_influx_client
from .discovery import discover_sensors
from .movement_detector import detect_movement_ratio, get_movement_segments, filter_data_in_movement
from .config import connect_influxdb3

# New analysis modules
from . import battery
from . import calculations
from . import gui
import datetime

def start_replay(start_time, end_time, filter_movement=True):
    """
    Launches the Slicks Telemetry Replay (Dashboard) for the specified time range.
    
    Args:
        start_time (datetime.datetime): Start of the range
        end_time (datetime.datetime): End of the range
        filter_movement (bool): If True, only keeps data where the car is moving.
    """
    print(f"--- Slicks: Fetching data from {start_time} to {end_time} ---")
    
    df = fetch_telemetry(start_time=start_time, end_time=end_time)
    
    if df.empty:
        print("No telemetry data found for this range.")
        return

    if filter_movement:
        print("Filtering for active movement...")
        df_filtered = filter_data_in_movement(df)
        if df_filtered.empty:
            print("No movement detected (car was stationary).")
            # Ask user if they want to see raw data? For now just return
            print("Try passing filter_movement=False to see raw stationary data.")
            return
        df = df_filtered
        print(f"Loaded {len(df)} frames of active driving data.")
    else:
        print(f"Loaded {len(df)} frames of raw data.")

    print("Launching Dashboard...")
    gui.launch_dashboard(df)
