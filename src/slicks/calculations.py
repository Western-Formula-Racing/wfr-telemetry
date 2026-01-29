import pandas as pd
import numpy as np

def calculate_g_sum(df: pd.DataFrame, x_col: str = "Accel_X", y_col: str = "Accel_Y", lsb_per_g: float = 81.92) -> pd.Series:
    """
    Calculates the combined G-force (friction circle usage).
    
    Args:
        df: DataFrame containing accelerometer data.
        x_col: Name of the longitudinal acceleration column.
        y_col: Name of the lateral acceleration column.
        lsb_per_g: Scaling factor. Default is 81.92.
                   Derivation: 8192 LSB/g (from +/-4G range) * 0.01 (DBC scaling factor) = 81.92.
                   If your data is pure LSBs without DBC scaling, use 8192.0.
        
    Returns:
        Series representing the vector sum of G-forces.
    """
    if x_col not in df.columns or y_col not in df.columns:
        print(f"Warning: {x_col} or {y_col} not found in DataFrame.")
        return pd.Series(index=df.index, dtype=float)
        
    x_g = df[x_col] / lsb_per_g
    y_g = df[y_col] / lsb_per_g
    
    # G_sum = sqrt(x^2 + y^2)
    g_sum = np.sqrt(x_g**2 + y_g**2)
    return g_sum

def estimate_speed_from_rpm(df: pd.DataFrame, tire_radius_m: float, gear_ratio: float = 1.0, rpm_col: str = "Right_RPM") -> pd.Series:
    """
    Estimates vehicle speed from RPM data.
    
    Args:
        df: DataFrame containing RPM data.
        tire_radius_m: Radius of the tire in meters.
        gear_ratio: Final Drive Ratio (Motor RPM -> Wheel RPM).
                    Use 1.0 if input is already Wheel RPM.
                    Example: 3.5 means Motor spins 3.5x faster than wheels.
        rpm_col: Column name for RPM. Looks for 'INV_Motor_Speed' if 'Right_RPM' missing.
        
    Returns:
        Series representing estimated speed in meters/second (m/s).
    """
    target_col = rpm_col
    
    # Fallback to Motor Speed if specific wheel speed not found
    if target_col not in df.columns and "INV_Motor_Speed" in df.columns:
        print(f"Note: '{rpm_col}' not found. Falling back to 'INV_Motor_Speed'.")
        target_col = "INV_Motor_Speed"
        
    if target_col not in df.columns:
        print(f"Warning: neither '{rpm_col}' nor 'INV_Motor_Speed' found in DataFrame.")
        return pd.Series(index=df.index, dtype=float)
        
    # RPM to Revs per Second
    rps = df[target_col] / 60.0
    
    # Wheel RPM = Motor RPM / Gear Ratio
    wheel_rps = rps / gear_ratio
    
    # Speed = Angular Speed * Radius
    # Angular Speed (rad/s) = rps * 2 * pi
    speed_mps = wheel_rps * (2 * np.pi * tire_radius_m)
    
    return speed_mps
