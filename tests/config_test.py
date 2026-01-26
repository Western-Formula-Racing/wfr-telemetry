import unittest
import sys
import os

# Ensure src is in path so we can import wfr_telemetry
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import slicks
from slicks import config

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        # Save original values
        self.orig_url = config.INFLUX_URL
        self.orig_token = config.INFLUX_TOKEN
        self.orig_org = config.INFLUX_ORG
        self.orig_db = config.INFLUX_DB

    def tearDown(self):
        # Restore original values
        slicks.configure(
            url=self.orig_url,
            token=self.orig_token,
            org=self.orig_org,
            db=self.orig_db
        )

    def test_configure_updates_globals(self):
        new_url = "http://test-url:8086"
        new_token = "test-token"
        new_org = "TestOrg"
        new_db = "TestDB"

        slicks.configure(
            url=new_url,
            token=new_token,
            org=new_org,
            db=new_db
        )

        self.assertEqual(config.INFLUX_URL, new_url)
        self.assertEqual(config.INFLUX_TOKEN, new_token)
        self.assertEqual(config.INFLUX_ORG, new_org)
        self.assertEqual(config.INFLUX_DB, new_db)

    def test_partial_update(self):
        new_db = "PartialDB"
        slicks.configure(db=new_db)

        self.assertEqual(config.INFLUX_DB, new_db)
        # Others should remain unchanged
        self.assertEqual(config.INFLUX_URL, self.orig_url)

if __name__ == '__main__':
    unittest.main()
