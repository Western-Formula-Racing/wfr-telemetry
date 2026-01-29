
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime
import sys
import os

# Ensure we can import 'slicks' from 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import slicks

class TestReplayIntegration(unittest.TestCase):
    
    @patch('slicks.fetch_telemetry')
    @patch('slicks.gui.launch_dashboard')
    def test_start_replay_success(self, mock_launch, mock_fetch):
        """
        Test that start_replay correctly fetches data and launches the dashboard
        when valid data is returned.
        """
        # 1. Setup Mock Data
        # Create a dummy DataFrame with movement
        dates = pd.date_range(start='2025-10-04 13:00', periods=10, freq='S')
        data = {
            'Speed_MPS': [0.0, 0.5, 2.0, 5.0, 5.0, 5.0, 2.0, 0.5, 0.0, 0.0],
            'Accel_X': [0] * 10,
            'Accel_Y': [0] * 10,
            'INV_Motor_Speed': [0, 100, 1000, 2000, 2000, 2000, 1000, 100, 0, 0],
            'min_cell_voltage': [3.8] * 10
        }
        df_mock = pd.DataFrame(data, index=dates)
        mock_fetch.return_value = df_mock
        
        # 2. Call Function
        start = datetime.datetime(2025, 10, 4, 13, 0)
        end = datetime.datetime(2025, 10, 4, 13, 1)
        slicks.start_replay(start, end, filter_movement=True)
        
        # 3. Assertions
        # Check if fetch called with correct args
        mock_fetch.assert_called_once_with(start_time=start, end_time=end)
        
        # Check if launch_dashboard called
        mock_launch.assert_called_once()
        
        # Verify passed DataFrame is not empty (it might be filtered, but should exist)
        args, _ = mock_launch.call_args
        self.assertFalse(args[0].empty)
        # We expect fewer than 10 rows because stationary/slow start/end might be filtered
        print(f"Test Success: Launched with {len(args[0])} rows.")

    @patch('slicks.fetch_telemetry')
    @patch('slicks.gui.launch_dashboard')
    def test_start_replay_no_data(self, mock_launch, mock_fetch):
        """
        Test that start_replay handles empty data gracefully without launching GUI.
        """
        # 1. Setup Mock Data (Empty)
        mock_fetch.return_value = pd.DataFrame()
        
        # 2. Call Function
        start = datetime.datetime(2025, 10, 4, 13, 0)
        end = datetime.datetime(2025, 10, 4, 13, 1)
        slicks.start_replay(start, end)
        
        # 3. Assertions
        mock_fetch.assert_called_once()
        mock_launch.assert_not_called()
        print("Test Success: Handled empty data gracefully.")

if __name__ == '__main__':
    unittest.main()
