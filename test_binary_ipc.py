import os
import re
import struct
import unittest

from order_protocol import ORDER_FORMAT, ORDER_SIZE


class TestBinaryIPC(unittest.TestCase):

    def test_order_protocol_uses_expected_binary_format(self):
        self.assertEqual(ORDER_FORMAT, "<QqI")
        self.assertEqual(ORDER_SIZE, 20)
        self.assertEqual(struct.calcsize(ORDER_FORMAT), ORDER_SIZE)

    def test_ipc_files_do_not_use_pickle_or_json_serialization(self):
        project_folder = os.path.dirname(os.path.abspath(__file__))

        ipc_files = [
            "order_protocol.py",
            "shared_memory.py",
            "ring_buffer.py",
            "ipc_audit.py"
        ]

        forbidden_pattern = re.compile(
            r"\b(import\s+(pickle|json)|"
            r"from\s+(pickle|json)\s+import|"
            r"(pickle|json)\.(dump|dumps|load|loads))\b"
        )

        for filename in ipc_files:
            file_path = os.path.join(project_folder, filename)

            with open(file_path, "r") as file:
                source_code = file.read()

            self.assertIsNone(
                forbidden_pattern.search(source_code),
                "{} contains Pickle or JSON serialization".format(filename)
            )


if __name__ == "__main__":
    unittest.main()