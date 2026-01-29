import pandas as pd
import re

def get_cell_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyzes all cell voltage columns (M*_Cell*_Voltage) to calculate min, max,
    average, and imbalance (delta) for each timestamp.
    
    Also identifies which specific cell is the minimum at each timestamp.
    
    Args:
        df: DataFrame containing telemetry data with cell voltage columns.
        
    Returns:
        DataFrame with columns: 
        - 'min_cell_voltage'
        - 'max_cell_voltage'
        - 'avg_cell_voltage'
        - 'pack_imbalance' (max - min)
        - 'lowest_cell_name' (name of the cell with the lowest voltage)
    """
    # 1. Identify all cell voltage columns
    # Pattern matches M1_Cell1_Voltage, M5_Cell20_Voltage, etc.
    cell_cols = [c for c in df.columns if re.match(r"M\d+_Cell\d+_Voltage", c)]
    
    if not cell_cols:
        print("Warning: No cell voltage columns found (expected format 'M*_Cell*_Voltage').")
        return pd.DataFrame(index=df.index)
        
    cell_data = df[cell_cols]
    
    # 2. Calculate statistics
    stats = pd.DataFrame(index=df.index)
    stats['min_cell_voltage'] = cell_data.min(axis=1)
    stats['max_cell_voltage'] = cell_data.max(axis=1)
    stats['avg_cell_voltage'] = cell_data.mean(axis=1)
    stats['pack_imbalance'] = stats['max_cell_voltage'] - stats['min_cell_voltage']
    
    # 3. Identify lowest cell
    # idxmin returns the column name of the minimum value
    stats['lowest_cell_name'] = cell_data.idxmin(axis=1)
    
    return stats

def identify_weak_cells(df: pd.DataFrame) -> pd.DataFrame:
    """
    Determines which cells are most frequently the lowest voltage in the pack.
    
    Args:
        df: DataFrame containing telemetry data.
        
    Returns:
        DataFrame containing identifying weak cells:
        - 'cell_name': Name of the cell
        - 'time_as_lowest_sec': Approximate seconds spent as the lowest cell
        - 'percentage': Percentage of total time spent as the lowest cell
    """
    stats = get_cell_statistics(df)
    
    if 'lowest_cell_name' not in stats.columns:
        return pd.DataFrame()
    
    # Count occurrences
    counts = stats['lowest_cell_name'].value_counts()
    
    # Convert to DataFrame
    report = counts.to_frame(name='count')
    report.index.name = 'cell_name'
    report.reset_index(inplace=True)
    
    total_samples = len(stats)
    
    # Assuming 1s resolution based on default fetcher behavior, but let's try to be robust
    # If index is datetime, we could calculate actual duration, but row count is a good proxy for sampled data
    report['percentage'] = (report['count'] / total_samples) * 100.0
    
    return report

def get_pack_health(df: pd.DataFrame) -> dict:
    """
    Returns a high-level summary of the pack's health over the provided data duration.
    
    Args:
        df: DataFrame containing telemetry data.
        
    Returns:
        Dictionary with keys:
        - 'max_imbalance': The highest recorded voltage difference.
        - 'avg_imbalance': The average voltage difference.
        - 'weakest_cell': The cell that was lowest most often.
        - 'min_pack_voltage': The lowest single cell voltage recorded.
    """
    stats = get_cell_statistics(df)
    weak_cells = identify_weak_cells(df)
    
    if stats.empty:
        return {}
        
    health = {
        'max_imbalance': stats['pack_imbalance'].max(),
        'avg_imbalance': stats['pack_imbalance'].mean(),
        'weakest_cell': weak_cells.iloc[0]['cell_name'] if not weak_cells.empty else None,
        'min_pack_voltage': stats['min_cell_voltage'].min()
    }
    
    return health
