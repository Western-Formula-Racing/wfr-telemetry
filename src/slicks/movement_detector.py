import pandas as pd

def detect_movement_ratio(df: pd.DataFrame, speed_column: str = "INV_Motor_Speed", threshold: float = 100.0) -> dict:
    """
    Analyzes the DataFrame to determine the portion of data where the car is actively moving.
    
    Args:
        df: Pandas DataFrame containing telemetry data.
        speed_column: Name of the column representing speed (e.g., motor speed).
        threshold: The value above which the car is considered to be moving.
        
    Returns:
        A dictionary containing:
        - total_rows: Total number of rows in the input.
        - moving_rows: Number of rows where the car is moving.
        - idle_rows: Number of rows where the car is idle/stationary.
        - movement_ratio: The fraction of data where the car is moving (0.0 to 1.0).
    """
    if speed_column not in df.columns:
        return {
            "error": f"Column '{speed_column}' not found in DataFrame."
        }
    
    total_rows = len(df)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "moving_rows": 0,
            "idle_rows": 0,
            "movement_ratio": 0.0
        }

    moving_mask = df[speed_column] > threshold
    moving_rows = moving_mask.sum()
    idle_rows = total_rows - moving_rows
    movement_ratio = moving_rows / total_rows
    
    return {
        "total_rows": total_rows,
        "moving_rows": moving_rows,
        "idle_rows": idle_rows,
        "movement_ratio": movement_ratio
    }

def filter_data_in_movement(df: pd.DataFrame, speed_column: str = "INV_Motor_Speed", threshold: float = 100.0) -> pd.DataFrame:
    """
    Filters the DataFrame to keep only rows where the car is moving.
    """
    if speed_column not in df.columns:
        print(f"Warning: '{speed_column}' not found. Returning original DataFrame.")
        return df
        
    stats = detect_movement_ratio(df, speed_column, threshold)
    print(f"Movement Detection: {stats['moving_rows']}/{stats['total_rows']} rows ({stats['movement_ratio']:.2%}) classified as active movement.")
    
    return df[df[speed_column] > threshold].copy()

def get_movement_segments(df: pd.DataFrame, speed_column: str = "INV_Motor_Speed", threshold: float = 100.0, max_gap_seconds: float = 60.0) -> pd.DataFrame:
    """
    Identifies contiguous segments of movement or idle status, 
    splitting if there are large time gaps.
    """
    if speed_column not in df.columns:
        return pd.DataFrame()
        
    data = df.sort_index() if isinstance(df.index, pd.DatetimeIndex) else df.sort_values('time')
    
    # 1. Identify state changes
    is_moving = data[speed_column] > threshold
    state_change = is_moving != is_moving.shift()
    
    # 2. Identify time gaps
    if isinstance(data.index, pd.DatetimeIndex):
        time_diffs = data.index.to_series().diff().dt.total_seconds()
    else:
        time_diffs = pd.to_datetime(data['time']).diff().dt.total_seconds()
        
    gap_detected = time_diffs > max_gap_seconds
    
    # A new segment starts if the state changed OR a large gap occurred
    segment_boundary = state_change | gap_detected
    block_ids = segment_boundary.cumsum()
    
    segments = []
    use_index = isinstance(data.index, pd.DatetimeIndex)

    grouped = data.groupby(block_ids)
    
    for _, group in grouped:
        is_moving_block = (group[speed_column] > threshold).any()
        state = "Moving" if is_moving_block else "Idle"
        
        start_t = group.index[0] if use_index else group['time'].iloc[0]
        end_t = group.index[-1] if use_index else group['time'].iloc[-1]
            
        duration = end_t - start_t
        
        segments.append({
            "start_time": start_t,
            "end_time": end_t,
            "duration": duration,
            "duration_sec": duration.total_seconds() if hasattr(duration, 'total_seconds') else 0,
            "state": state,
            "mean_speed": group[speed_column].mean(),
            "rows": len(group)
        })
        
    return pd.DataFrame(segments)

if __name__ == "__main__":
    import sys
    from datetime import timedelta
    
    file_path = "telemetry_season.csv"
    min_segment_dur = 60.0 # 1 minute threshold
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
    try:
        print(f"Loading {file_path}...")
        df = pd.read_csv(file_path)
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time', drop=False)
            
        print("\nAnalyzing Movement Segments (1-min gap & duration threshold)...")
        # Split segments if gap > 60s
        segments_df = get_movement_segments(df, max_gap_seconds=60.0)
        
        if not segments_df.empty:
            # Filter: We only care about segments that last at least 1 minute
            significant_segments = segments_df[segments_df['duration_sec'] >= min_segment_dur].copy()
            
            print(f"\nFound {len(segments_df)} raw segments.")
            print(f"Filtered to {len(significant_segments)} segments longer than {min_segment_dur}s.")
            
            print("-" * 110)
            print(f"{ 'Start Time':<25} | { 'End Time':<25} | { 'Duration':<15} | { 'State':<10} | {'Avg Speed'}")
            print("-" * 110)
            
            for _, row in significant_segments.iterrows():
                s_str = str(row['start_time'])
                e_str = str(row['end_time'])
                dur_str = str(row['duration'])
                state = row['state']
                spd = f"{row['mean_speed']:.1f}"
                print(f"{s_str:<25} | {e_str:<25} | {dur_str:<15} | {state:<10} | {spd}")

            # Save report
            significant_segments.to_csv("movement_segments_report.csv", index=False)
            
            total_moving_time = significant_segments[significant_segments['state'] == 'Moving']['duration'].sum()
            print(f"\nTotal Valid Movement Time: {total_moving_time}")
            
    except FileNotFoundError:
        print(f"File {file_path} not found. Usage: python -m slicks.movement_detector <csv_file>")
    except Exception as e:
        print(f"Error: {e}")
