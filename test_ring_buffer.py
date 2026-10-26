
import os
import tempfile
import unittest

from shared_memory import SharedMemoryRegion
from ring_buffer import RingBuffer
from order_protocol import ORDER_SIZE
from shared_memory import HEADER_SIZE


class TestRingBuffer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "test_shared.bin"
        )

        with SharedMemoryRegion.create(self.path, capacity=4):
            pass

        self.buffer = RingBuffer(self.path)

    def tearDown(self):
        self.buffer.close()
        self.temp_dir.cleanup()

    def test_initial_header(self):
        header = self.buffer.get_header()

        self.assertEqual(header["capacity"], 4)
        self.assertEqual(header["read_seq"], 0)
        self.assertEqual(header["write_seq"], 0)

    def test_first_slot_offset(self):
        self.assertEqual(
            self.buffer.slot_offset(0),
            HEADER_SIZE
        )

    def test_second_slot_offset(self):
        self.assertEqual(
            self.buffer.slot_offset(1),
            HEADER_SIZE + ORDER_SIZE
        )

    def test_last_slot_offset(self):
        self.assertEqual(
            self.buffer.slot_offset(3),
            HEADER_SIZE + 3 * ORDER_SIZE
        )

    def test_wraps_to_first_slot(self):
        self.assertEqual(
            self.buffer.slot_offset(4),
            self.buffer.slot_offset(0)
        )

    def test_wraps_after_multiple_cycles(self):
        self.assertEqual(
            self.buffer.slot_offset(9),
            self.buffer.slot_offset(1)
        )

    def test_negative_sequence(self):
        with self.assertRaises(ValueError):
            self.buffer.slot_offset(-1)

    def test_non_integer_sequence(self):
        with self.assertRaises(TypeError):
            self.buffer.slot_offset(1.5)


if __name__ == "__main__":
    unittest.main()
