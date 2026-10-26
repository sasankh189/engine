import os
import tempfile
import unittest

from shared_memory import SharedMemoryRegion, HEADER_SIZE
from ring_buffer import RingBuffer
from order_protocol import ORDER_SIZE, unpack_order


class TestRingBuffer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name, "test_shared.bin"
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
            self.buffer.slot_offset(0), HEADER_SIZE
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

    def test_write_one_order(self):
        sequence = self.buffer.write_order(1001, 12550, 10)
        self.assertEqual(sequence, 0)

        header = self.buffer.get_header()
        self.assertEqual(header["write_seq"], 1)
        self.assertEqual(header["read_seq"], 0)

    def test_written_order_is_stored_correctly(self):
        self.buffer.write_order(1001, 12550, 10)
        offset = self.buffer.slot_offset(0)
        raw = self.buffer.region.memory_map[
            offset:offset + ORDER_SIZE
        ]
        self.assertEqual(
            unpack_order(raw), (1001, 12550, 10)
        )

    def test_multiple_orders_advance_sequence(self):
        self.buffer.write_order(1001, 12550, 10)
        self.buffer.write_order(1002, 13000, 5)
        self.buffer.write_order(1003, 12800, 7)
        self.assertEqual(
            self.buffer.get_header()["write_seq"], 3
        )

    def test_full_buffer_rejects_fifth_order(self):
        for order_id in range(4):
            self.buffer.write_order(order_id + 1, 10000, 1)

        with self.assertRaises(BufferError):
            self.buffer.write_order(5, 10000, 1)

    def test_full_buffer_does_not_overwrite_first_order(self):
        self.buffer.write_order(1001, 12550, 10)

        for order_id in range(3):
            self.buffer.write_order(order_id + 1002, 13000, 1)

        with self.assertRaises(BufferError):
            self.buffer.write_order(2000, 15000, 2)

        offset = self.buffer.slot_offset(0)
        raw = self.buffer.region.memory_map[
            offset:offset + ORDER_SIZE
        ]
        self.assertEqual(
            unpack_order(raw), (1001, 12550, 10)
        )

    def test_invalid_order_is_not_written(self):
        with self.assertRaises(TypeError):
            self.buffer.write_order(1001, 12.5, 10)

        self.assertEqual(
            self.buffer.get_header()["write_seq"], 0
        )


if __name__ == "__main__":
    unittest.main()
