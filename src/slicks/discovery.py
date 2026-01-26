from datetime import timedelta
from . import config
from .fetcher import get_influx_client

def discover_sensors(start_time, end_time, chunk_size_days=1, client=None):
    """
    Scans the database for ALL unique sensor names within the time range.
    Uses recursive splitting to handle server resource limits.
    """
    if client is None:
        client = get_influx_client()

    unique_sensors = set()
    
    def _scan_recursive(start, end, depth=0):
        # Stop recursion if interval is too small (< 10 seconds) or depth too high
        if (end - start).total_seconds() < 10 or depth > 5:
            # print(f"  Skipping small/deep chunk: {start} to {end}")
            return

        query = f"""
        SELECT DISTINCT "signalName"
        FROM "iox"."{config.INFLUX_DB}"
        WHERE time >= '{start.isoformat()}Z'
        AND time < '{end.isoformat()}Z'
        """
        
        try:
            # print(f"Scanning {start} -> {end} (Depth {depth})...")
            table = client.query(query=query, mode="all")
            df = table.to_pandas()
            
            if not df.empty and "signalName" in df.columns:
                batch_sensors = set(df["signalName"].unique())
                unique_sensors.update(batch_sensors)
                
        except Exception as e:
            # print(f"  Chunk failed ({e}). Splitting...")
            mid_point = start + (end - start) / 2
            _scan_recursive(start, mid_point, depth + 1)
            _scan_recursive(mid_point, end, depth + 1)

    print(f"Discovering sensors from {start_time} to {end_time}...")
    current = start_time
    while current < end_time:
        next_step = min(current + timedelta(days=chunk_size_days), end_time)
        if next_step <= current: break
        
        # Start recursion for this chunk
        _scan_recursive(current, next_step)
        current = next_step

    sorted_sensors = sorted(list(unique_sensors))
    print(f"Discovery Complete. Found {len(sorted_sensors)} unique sensors.")
    return sorted_sensors