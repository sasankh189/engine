
import os
import subprocess
import sys
import tempfile
import unittest

from shared_memory import SharedMemoryRegion
from ring_buffer import RingBuffer
from order_protocol import ORDER_SIZE, unpack_order
from shared_memory import HEADER_SIZE


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCER_PATH = os.path.join(PROJECT_DIR, "producer.py")


class TestProducer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "producer_test.bin"
        )

        # Create a buffer large enough for the test orders.
        with SharedMemoryRegion.create(self.path, capacity=10):
            pass

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_producer_writes_three_orders(self):
        result = subprocess.run(
            [
                sys.executable,
                PRODUCER_PATH,
                "--path", self.path,
                "--count", "3",
                "--start-id", "1001",
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stdout + result.stderr
        )

        self.assertIn("Orders written: 3", result.stdout)

        # Verify the shared-memory header after the child process exits.
        with RingBuffer(self.path) as buffer:
            header = buffer.get_header()

            self.assertEqual(header["write_seq"], 3)
            self.assertEqual(header["read_seq"], 0)

            expected_orders = [
                (1001, 12500, 1),
                (1002, 12510, 2),
                (1003, 12520, 3),
            ]

            for sequence, expected in enumerate(expected_orders):
                offset = HEADER_SIZE + (
                    sequence % header["capacity"]
                ) * ORDER_SIZE

                raw = buffer.region.memory_map[
                    offset:offset + ORDER_SIZE
                ]

                self.assertEqual(unpack_order(raw), expected)

    def test_producer_stops_when_buffer_is_full(self):
        result = subprocess.run(
            [
                sys.executable,
                PRODUCER_PATH,
                "--path", self.path,
                "--count", "12",
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Buffer is full", result.stderr)
        self.assertIn("Orders written: 10", result.stdout)

        with RingBuffer(self.path) as buffer:
            header = buffer.get_header()
            self.assertEqual(header["write_seq"], 10)
            self.assertEqual(header["read_seq"], 0)


if __name__ == "__main__":
    unittest.main()
