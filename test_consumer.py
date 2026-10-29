
import os
import subprocess
import sys
import tempfile
import unittest

from shared_memory import SharedMemoryRegion
from ring_buffer import RingBuffer


class TestConsumer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "consumer_shared.bin"
        )

        self.region = SharedMemoryRegion.create(
            self.path,
            capacity=10
        )

    def tearDown(self):
        self.region.close()
        self.temp_dir.cleanup()

    def test_consumer_reads_orders(self):
        expected_orders = [
            (1001, 12500, 1),
            (1002, 12510, 2),
            (1003, 12520, 3)
        ]

        with RingBuffer(self.path) as ring:
            for order in expected_orders:
                ring.write_order(*order)

        result = subprocess.run(
            [
                sys.executable,
                "consumer.py",
                "--path",
                self.path,
                "--count",
                "3"
            ],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Order ID: 1001", result.stdout)
        self.assertIn("Order ID: 1002", result.stdout)
        self.assertIn("Order ID: 1003", result.stdout)
        self.assertIn("Orders read: 3", result.stdout)

    def test_consumer_stops_when_empty(self):
        result = subprocess.run(
            [
                sys.executable,
                "consumer.py",
                "--path",
                self.path,
                "--count",
                "3"
            ],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ring buffer is empty.", result.stdout)
        self.assertIn("Orders read: 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
