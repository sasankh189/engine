
import os
import tempfile
import unittest

from shared_memory import SharedMemoryRegion, HEADER_SIZE
from ring_buffer import RingBuffer
from order_protocol import ORDER_SIZE, unpack_order


class TestRingBuffer(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for each test.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "test_shared.bin"
        )

        # Create a ring buffer with four slots.
        with SharedMemoryRegion.create(self.path, capacity=4):
            pass

        self.buffer = RingBuffer(self.path)

    def tearDown(self):
        # Close shared memory and remove temporary files.
        self.buffer.close()
        self.temp_dir.cleanup()

    # ---------------- DAY 4: RING BUFFER STRUCTURE ----------------

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

    # ---------------- DAY 5: PRODUCER WRITE ----------------

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
            unpack_order(raw),
            (1001, 12550, 10)
        )

    def test_multiple_orders_advance_sequence(self):
        self.buffer.write_order(1001, 12550, 10)
        self.buffer.write_order(1002, 13000, 5)
        self.buffer.write_order(1003, 12800, 7)

        self.assertEqual(
            self.buffer.get_header()["write_seq"],
            3
        )

    def test_full_buffer_rejects_fifth_order(self):
        for order_id in range(4):
            self.buffer.write_order(order_id + 1, 10000, 1)

        with self.assertRaises(BufferError):
            self.buffer.write_order(5, 10000, 1)

    def test_full_buffer_does_not_overwrite_first_order(self):
        self.buffer.write_order(1001, 12550, 10)

        for order_id in range(3):
            self.buffer.write_order(
                order_id + 1002, 13000, 1
            )

        with self.assertRaises(BufferError):
            self.buffer.write_order(2000, 15000, 2)

        offset = self.buffer.slot_offset(0)
        raw = self.buffer.region.memory_map[
            offset:offset + ORDER_SIZE
        ]

        self.assertEqual(
            unpack_order(raw),
            (1001, 12550, 10)
        )

    def test_invalid_order_is_not_written(self):
        with self.assertRaises(TypeError):
            self.buffer.write_order(1001, 12.5, 10)

        self.assertEqual(
            self.buffer.get_header()["write_seq"],
            0
        )

    # ---------------- DAY 6: CONSUMER READ ----------------

    def test_read_one_order(self):
        self.buffer.write_order(1001, 12550, 10)

        order = self.buffer.read_order()

        self.assertEqual(order, (1001, 12550, 10))
        self.assertEqual(
            self.buffer.get_header()["read_seq"],
            1
        )

    def test_empty_buffer_rejects_read(self):
        with self.assertRaises(BufferError):
            self.buffer.read_order()

        header = self.buffer.get_header()
        self.assertEqual(header["read_seq"], 0)
        self.assertEqual(header["write_seq"], 0)

    def test_reads_orders_in_fifo_order(self):
        orders = [
            (1001, 12550, 10),
            (1002, 13000, 5),
            (1003, 12800, 7),
        ]

        for order in orders:
            self.buffer.write_order(*order)

        received = [
            self.buffer.read_order(),
            self.buffer.read_order(),
            self.buffer.read_order(),
        ]

        self.assertEqual(received, orders)

    def test_read_frees_slot_for_new_order(self):
        for order_id in range(4):
            self.buffer.write_order(order_id + 1, 10000, 1)

        first = self.buffer.read_order()
        self.assertEqual(first, (1, 10000, 1))

        self.buffer.write_order(5, 11000, 2)

        header = self.buffer.get_header()
        self.assertEqual(header["write_seq"], 5)
        self.assertEqual(header["read_seq"], 1)

    def test_read_and_write_after_wraparound(self):
        original_orders = [
            (1001, 12500, 1),
            (1002, 12600, 2),
            (1003, 12700, 3),
            (1004, 12800, 4),
        ]

        for order in original_orders:
            self.buffer.write_order(*order)

        self.assertEqual(
            self.buffer.read_order(),
            original_orders[0]
        )
        self.assertEqual(
            self.buffer.read_order(),
            original_orders[1]
        )

        new_orders = [
            (1005, 12900, 5),
            (1006, 13000, 6),
        ]

        for order in new_orders:
            self.buffer.write_order(*order)

        received = [
            self.buffer.read_order(),
            self.buffer.read_order(),
            self.buffer.read_order(),
            self.buffer.read_order(),
        ]

        self.assertEqual(
            received,
            original_orders[2:] + new_orders
        )

    def test_buffer_is_empty_after_all_orders_are_read(self):
        self.buffer.write_order(1001, 12550, 10)
        self.buffer.read_order()

        header = self.buffer.get_header()

        self.assertEqual(
            header["read_seq"],
            header["write_seq"]
        )

        with self.assertRaises(BufferError):
            self.buffer.read_order()


if __name__ == "__main__":
    unittest.main()

