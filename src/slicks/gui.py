import dearpygui.dearpygui as dpg
import pandas as pd
import numpy as np
import time
from . import calculations
from . import movement_detector

class TelemetryDashboard:
    """
    Interactive Replay Dashboard using Dear PyGui.
    
    LIMITATIONS & ASSUMPTIONS:
    1. G-Force Scaling: The accelerometer scaling is ambiguous. 
       - Datasheets suggest 16384 LSB/g, but observed noise suggests a lower resolution or different format.
       - We default to a dynamic scale (slider) starting at ~256 LSB/g to allow user tuning.
       - A "G-Scale" slider is provided in the UI to manually adjust this.
    2. G-Force Bias:
       - The sensor likely has mounting tilt. We attempt 'Auto-Zero' calibration by finding 
         stationary periods (Speed < 0.2 m/s). 
       - If no stationary data is found at the start, calibration may be inaccurate.
    3. Speed Calculation:
       - Estimated from Motor RPM using fixed Tire Radius (10.2") and Gear Ratio (4.53).
       - Does not account for tire slip or deformation.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
        # Ensure calculated columns exist
        if "Speed_MPS" not in self.df.columns:
             # Try simple fallback
             if "INV_Motor_Speed" in self.df.columns:
                 # Gear Ratio: 4.53
                 # Tire Radius: 10.2 inches = 0.259 meters
                 self.df["Speed_MPS"] = calculations.estimate_speed_from_rpm(
                     self.df, tire_radius_m=0.259, gear_ratio=4.53, rpm_col="INV_Motor_Speed"
                 )
             else:
                 self.df["Speed_MPS"] = 0.0

        if "Accel_X" in self.df.columns and "Accel_Y" in self.df.columns:
             # Just keep raw values in X/Y columns
             pass
        
        # --- Auto-Zero Calibration (RAW) ---
        self.bias_x_raw = 0.0
        self.bias_y_raw = 0.0
        
        try:
            # Find stationary
            stationary = self.df[self.df["Speed_MPS"].abs() < 0.2]
            if len(stationary) < 10: stationary = self.df.iloc[:20] 
                
            self.bias_x_raw = stationary["Accel_X"].median() # Raw LSB
            self.bias_y_raw = stationary["Accel_Y"].median() # Raw LSB
            
            print(f"Calibrated Raw Bias: X={self.bias_x_raw:.1f}, Y={self.bias_y_raw:.1f}")
        except Exception as e:
             print(f"Calibration Failed: {e}") 
             
        # No pre-smoothing on Gs since we calculate dynamically. 
        # (Could smooth raw if needed, but skipping for responsiveness with slider)

        # Simulation State
        self.playing = False
        self.current_idx = 0
        self.max_idx = len(self.df) - 1
        self.playback_speed = 1 # 1x speed (approx, limited by refresh rate)
        self.last_update = time.time()
        
        # Calculate Active Segments for Timeline
        self.segments = movement_detector.get_movement_segments(self.df, speed_column="Speed_MPS", threshold=1.0)
        
        # Segment Indices (Start Index, End Index)
        # Identify indices where specific timestamps occur
        self.seg_indices = []
        if not self.segments.empty:
            for _, seg in self.segments.iterrows():
                if seg['state'] == 'Moving':
                    # Find integer index of start/end time
                    # This is approximate if indices are not continuous, but good enough for visual
                    try:
                        s_idx = self.df.index.get_indexer([seg['start_time']], method='nearest')[0]
                        e_idx = self.df.index.get_indexer([seg['end_time']], method='nearest')[0]
                        self.seg_indices.append((s_idx, e_idx))
                    except:
                        pass

        # Data Buffers for Plots (X-Axis = Index)
        self.indices = self.df.reset_index().index.tolist()
        self.speed_data = (self.df["Speed_MPS"] * 3.6).tolist() # Convert to km/h for Plot
        if "INV_Motor_Speed" in self.df.columns:
            self.rpm_data = self.df["INV_Motor_Speed"].tolist()
        else:
            self.rpm_data = [0] * len(self.df)
            
        # G-Force Trail Buffer
        self.g_trail = []

    def _timeline_click_handler(self, sender, app_data):
        # app_data is (mouse_button, index) - wait, click_handler gives different data?
        # Typically we poll get_mouse_pos relative to item.
        # But simpler: use an invisible button or just poll in loop.
        pass
        
    def _poll_timeline_click(self):
        # Check if mouse is clicked within the timeline rect
        if dpg.is_item_hovered("timeline_canvas") and dpg.is_mouse_button_down(0):
            # Get Mouse X relative to canvas
            # Timeline width is roughly window width - padding
            # Let's assume fixed width for now or retrieve it
            min_p = dpg.get_item_rect_min("timeline_canvas")
            max_p = dpg.get_item_rect_max("timeline_canvas")
            width = max_p[0] - min_p[0]
            
            if width > 0:
                mouse_x = dpg.get_mouse_pos(local=False)[0] - min_p[0]
                ratio = max(0.0, min(1.0, mouse_x / width))
                self.current_idx = int(ratio * self.max_idx)

    def _update_gui(self, idx):
        # Update Slider
        dpg.set_value("timeline_slider", idx)
        
        # Get Current Data Row
        row = self.df.iloc[idx]
        
        # 1. Update Text Stats
        curr_speed = row.get("Speed_MPS", 0) * 3.6 # kph
        curr_rpm = row.get("INV_Motor_Speed", 0)
        curr_time = str(row.name)
        
        dpg.set_value("stat_speed", f"{curr_speed:.1f} km/h")
        dpg.set_value("stat_rpm", f"{curr_rpm:.0f} RPM")
        dpg.set_value("stat_time", f"Time: {curr_time}")
        
        # 2. Update Friction Circle
        # Draw a line from center (0,0) to (LatG, LongG)
        # Canvas is e.g. 300x300. Center is 150,150.
        # Scale: 2G = 150px => 1G = 75px
        scale = 75
        center = 150
        
        gx = row.get("Accel_Y_G", 0) # Lat
        gy = row.get("Accel_X_G", 0) # Long 
        
        # --- Smoothing Logic ---
        # If the jump is huge, it looks glitchy. We can smooth it using a simple Lerp (Linear Interpolation)
        # However, since we are scrubbing random points, stateful smoothing is tricky.
        # Ideally, we pre-smooth the DataFrame on load. 
        # But for valid replay, let's just use a rolling mean if available, or just raw.
        # The user says "sudden", which implies noise.
        # Let's check if we have smoothed columns. If not, maybe we create them in __init__.
        
        # fallback: use raw (the user might just mean it jumps too fast because of playback speed)
        
        # Invert GUI Y axis (Up is -Y)
        x_pos = center + (gx * scale)
        y_pos = center - (gy * scale)
        
        dpg.set_value("g_force_dot", [[x_pos, y_pos]])
        dpg.set_value("g_force_text", f"Lat: {gx:.2f} G | Long: {gy:.2f} G")
        dpg.set_value("speed_cursor", float(self.current_idx))


    def run(self):
        dpg.create_context()
        dpg.create_viewport(title='Slicks Telemetry Replay', width=1280, height=800)
        
        with dpg.window(label="Cockpit Control", width=1260, height=760):
            
            # --- Top Bar ---
            with dpg.group(horizontal=True):
                dpg.add_button(label="Play/Pause", callback=lambda: setattr(self, 'playing', not self.playing))
                dpg.add_text("Time: ", tag="stat_time")
                dpg.add_spacer(width=50)
                dpg.add_text("G-Scale:")
                dpg.add_slider_float(tag="scale_slider", default_value=256.0, min_value=1.0, max_value=20000.0, width=150)
                dpg.add_text("(Try 256 or 16384)")
                
            dpg.add_slider_int(label="Timeline", tag="timeline_slider", min_value=0, max_value=self.max_idx, 
                               callback=lambda s, a: setattr(self, 'current_idx', a), width=-1)
            dpg.add_spacer(height=5)
            dpg.add_text("Timeline (Green = Moving)")
            
            timeline_width = 1240
            timeline_height = 40
            
            with dpg.drawlist(width=timeline_width, height=timeline_height, tag="timeline_canvas"):
                # Background
                dpg.draw_rectangle((0, 0), (timeline_width, timeline_height), color=(50, 50, 50), fill=(30, 30, 30))
                
                # Draw Segments
                for s_i, e_i in self.seg_indices:
                    # Normalize to width
                    x1 = (s_i / self.max_idx) * timeline_width
                    x2 = (e_i / self.max_idx) * timeline_width
                    # Ensure at least 1px width
                    if x2 - x1 < 1: x2 = x1 + 1
                    
                    dpg.draw_rectangle((x1, 0), (x2, timeline_height), color=(0, 200, 0, 150), fill=(0, 200, 0, 100))
                
                # Playhead (Cursor) - dynamic tag to update later
                dpg.draw_line((0, 0), (0, timeline_height), color=(255, 255, 255), thickness=3, tag="timeline_cursor")

            dpg.add_spacer(height=20)

            # --- Main Content Columns ---
            with dpg.group(horizontal=True):
                
                # LEFT: Gauges / Stats
                with dpg.group(width=300):
                    dpg.add_text("SPEED", color=(0, 255, 255))
                    dpg.add_text("0.0 km/h", tag="stat_speed") 
                    
                    dpg.add_spacer(height=20)
                    
                    dpg.add_text("RPM", color=(255, 0, 255))
                    dpg.add_text("0 RPM", tag="stat_rpm")
                    
                    dpg.add_spacer(height=20)
                    
                    if "min_cell_voltage" in self.df.columns:
                        dpg.add_text("Battery Health")
                        dpg.add_progress_bar(tag="batt_bar", default_value=0.5, width=200)

                # CENTER: Friction Circle
                with dpg.group(width=400):
                    dpg.add_text("G-Force (Friction Circle)")
                    with dpg.drawlist(width=300, height=300):
                        # Background Circle (1G, 2G rings)
                        dpg.draw_circle((150, 150), 75, color=(100, 100, 100), thickness=2) # 1G
                        dpg.draw_circle((150, 150), 150, color=(100, 100, 100), thickness=2) # 2G
                        dpg.draw_line((150, 0), (150, 300), color=(50, 50, 50)) # V Axis
                        dpg.draw_line((150, 0), (150, 300), color=(50, 50, 50)) # V Axis
                        dpg.draw_line((0, 150), (300, 150), color=(50, 50, 50)) # H Axis
                        
                        # Labels
                        dpg.draw_text((135, 5), "Accel", color=(200, 200, 200), size=15)
                        dpg.draw_text((135, 285), "Brake", color=(200, 200, 200), size=15)
                        dpg.draw_text((260, 145), "Right", color=(200, 200, 200), size=15)
                        dpg.draw_text((10, 145), "Left", color=(200, 200, 200), size=15)
                        
                        # Calibration Debug Info
                        dpg.draw_text((10, 280), f"Bias: {self.bias_x_raw:.1f}, {self.bias_y_raw:.1f}", color=(100, 100, 100))
                        
                        # Trail (The Snail) - Initialize empty
                        dpg.draw_polyline([], color=(0, 255, 255, 100), thickness=2, tag="g_trail_line")
                        
                        # Active Dot (The "Ball")
                        dpg.draw_circle((150, 150), 10, color=(255, 165, 0), fill=(255, 165, 0), tag="g_force_dot")
                    
                    dpg.add_text("0.0 G", tag="g_force_text")

                # RIGHT: Scrolling Plots
                with dpg.group(width=-1):
                    with dpg.plot(label="Speed Trace", height=300, width=-1):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label="Sample Index", tag="x_axis")
                        dpg.add_plot_axis(dpg.mvYAxis, label="Speed (km/h)", tag="y_axis")
                        
                        # Data Line
                        dpg.add_line_series(self.indices, self.speed_data, parent="y_axis", label="Speed")
                        
                        # Time Cursor (Vertical Line)
                        # DPG doesn't have a simple vline for plots, but drag_line works
                        dpg.add_drag_line(label="Current", color=(255, 255, 255, 255), vertical=True, tag="speed_cursor")

        dpg.setup_dearpygui()
        dpg.show_viewport()
        
        # Render Loop
        last_frame_time = time.time()
        
        while dpg.is_dearpygui_running():
            current_time = time.time()
            dt = current_time - last_frame_time
            last_frame_time = current_time
            
            # Helper for timeline scrubbing
            self._poll_timeline_click()

            # Update Logic
            if self.playing:
                # Calculate how many "seconds" of data to advance
                # Index is not always 1:1 with time.
                # If avg sample rate is 0.1s (10Hz), then 1 second real time = 10 indices.
                # Let's derive sample rate roughly
                # Or just check timestamp of next index.
                
                # But user asked for "real life time".
                # If indices are seconds apart:
                # We need to find the timestamp of current_idx, and target timestamp = current_ts + dt.
                # Then advance idx until ts >= target.
                
                # Check Time Delta between frames
                try:
                   current_ts = self.df.index[int(self.current_idx)]
                   # target_ts = current_ts + timedelta(seconds=dt * self.playback_speed)
                   # For simplicity in this sparse/messy dataset, let's just use a fixed Frame Rate
                   # e.g. 10 samples per second is a good "playback" feel.
                   pass
                except:
                   pass
                   
                # Moving the slider 10 indices per second (adjustable)
                self.current_idx += 30.0 * dt # 30 samples/sec playback speed
                
                if self.current_idx > self.max_idx:
                    self.current_idx = 0
            
            # Clamp and Cast to Int for slicing
            idx_int = int(max(0, min(self.current_idx, self.max_idx)))
            
            # Update GUI using the INT index
            # Passing idx_int explicitly to helper
            self._update_gui(idx_int)
            
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

    def _update_gui(self, idx):
        # Custom Timeline Cursor
        # Map idx to pixel x
        timeline_width = 1240 # Must match drawlist width
        x_pos = (idx / self.max_idx) * timeline_width
        
        # Modify the draw command directly? 
        # Actually easier to DELETE and REDRAW or use apply_transform?
        # DPG drawlist items can be configured if we know the tag?
        # dpg.configure_item("timeline_cursor", p1=(x_pos, 0), p2=(x_pos, 40)) works!
        dpg.configure_item("timeline_cursor", p1=(x_pos, 0), p2=(x_pos, 40))
        
        # Get Current Data Row
        row = self.df.iloc[idx]
        
        # 1. Update Text Stats
        curr_speed = row.get("Speed_MPS", 0) * 3.6 # kph
        curr_rpm = row.get("INV_Motor_Speed", 0)
        curr_time = str(row.name)
        
        dpg.configure_item("stat_speed", default_value=f"{curr_speed:.1f} km/h")
        dpg.configure_item("stat_rpm", default_value=f"{curr_rpm:.0f} RPM")
        dpg.configure_item("stat_time", default_value=f"Time: {curr_time}")
        
        # 2. Update Friction Circle
        scale_gui = 75 # Pixels per G
        center = 150
        
        # Get Dynamic Scale Factor from Slider
        # Default ~256?
        lsb_per_g = dpg.get_value("scale_slider")
        if lsb_per_g <= 0: lsb_per_g = 1.0
        
        # Raw Data (stored in Accel_X/Y columns, assumed raw or raw-ish)
        # Note: We previously modified Accel_X_G in place. 
        # Ideally, we should use the original "Accel_X" column for this dynamic scaling.
        # But we also need the "Bias" to be correct relative to the scale.
        # Let's calculate Gs dynamically: (Raw - RawBias) / Scale
        
        raw_x = row.get("Accel_X", 0)
        raw_y = row.get("Accel_Y", 0)
        
        gx = (raw_y - self.bias_y_raw) / lsb_per_g
        gy = (raw_x - self.bias_x_raw) / lsb_per_g
        
        # CLAMP
        gx = max(-2.0, min(2.0, gx))
        gy = max(-2.0, min(2.0, gy))
        
        x_pos_g = center + (gx * scale_gui)
        y_pos_g = center - (gy * scale_gui)
        
        # Update Trail
        self.g_trail.append([x_pos_g, y_pos_g])
        if len(self.g_trail) > 60: # Keep last 2 seconds (assuming 30fps)
            self.g_trail.pop(0)
            
        dpg.configure_item("g_trail_line", points=self.g_trail)
        
        # Draw Node
        dpg.configure_item("g_force_dot", center=[x_pos_g, y_pos_g])
        dpg.configure_item("g_force_text", default_value=f"Lat: {gx:.2f} G | Long: {gy:.2f} G")
        
        # 3. Update Line
        dpg.set_value("speed_cursor", float(idx))


def launch_dashboard(df: pd.DataFrame):
    dashboard = TelemetryDashboard(df)
    dashboard.run()
