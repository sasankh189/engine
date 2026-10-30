
import os
import subprocess
import sys
import tempfile
import unittest

from shared_memory import SharedMemoryRegion


class TestSeparateProcessIPC(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "ipc_shared.bin"
        )

        self.region = SharedMemoryRegion.create(
            self.path,
            capacity=10
        )

    def tearDown(self):
        self.region.close()
        self.temp_dir.cleanup()

    def test_producer_to_consumer_processes(self):

        # Process 1: Run the producer.
        producer = subprocess.run(
            [
                sys.executable,
                "producer.py",
                "--path",
                self.path,
                "--count",
                "3"
            ],
            capture_output=True,
            text=True
        )

        self.assertEqual(
            producer.returncode,
            0,
            producer.stderr
        )

        self.assertIn("Orders written: 3", producer.stdout)

        # Process 2: Run the consumer.
        consumer = subprocess.run(
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

        self.assertEqual(
            consumer.returncode,
            0,
            consumer.stderr
        )

        self.assertIn("Order ID: 1001", consumer.stdout)
        self.assertIn("Order ID: 1002", consumer.stdout)
        self.assertIn("Order ID: 1003", consumer.stdout)
        self.assertIn("Orders read: 3", consumer.stdout)


if __name__ == "__main__":
    unittest.main()
