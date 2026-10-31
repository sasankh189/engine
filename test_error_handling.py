
import os
import subprocess
import sys
import tempfile
import unittest


class TestIPCErrorHandling(unittest.TestCase):

    def test_consumer_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            missing_path = os.path.join(
                folder,
                "missing_shared.bin"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "consumer.py",
                    "--path",
                    missing_path,
                    "--count",
                    "3"
                ],
                capture_output=True,
                text=True
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Consumer error:", result.stdout)

    def test_consumer_negative_count(self):
        result = subprocess.run(
            [
                sys.executable,
                "consumer.py",
                "--path",
                "unused.bin",
                "--count",
                "-1"
            ],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--count must be zero or greater",
            result.stderr
        )

    def test_producer_negative_count(self):
        result = subprocess.run(
            [
                sys.executable,
                "producer.py",
                "--path",
                "unused.bin",
                "--count",
                "-1"
            ],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--count must be zero or greater",
            result.stderr
        )


if __name__ == "__main__":
    unittest.main()
