
import unittest
import struct

from order_protocol import (
    ORDER_FORMAT,
    ORDER_SIZE,
    pack_order,
    unpack_order,
)


class TestOrderProtocol(unittest.TestCase):

    def test_order_round_trip(self):
        order = (1001, 12550, 10)
        packed = pack_order(*order)

        self.assertEqual(unpack_order(packed), order)

    def test_binary_size_is_20_bytes(self):
        self.assertEqual(ORDER_SIZE, 20)
        self.assertEqual(struct.calcsize(ORDER_FORMAT), 20)

    def test_zero_values(self):
        order = (0, 0, 0)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_maximum_values(self):
        order = (2**64 - 1, 2**63 - 1, 2**32 - 1)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_minimum_signed_price(self):
        order = (1, -(2**63), 1)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_negative_price(self):
        order = (1002, -500, 5)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_negative_order_id_rejected(self):
        with self.assertRaises(ValueError):
            pack_order(-1, 100, 1)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            pack_order(1, 100, -1)

    def test_order_id_overflow_rejected(self):
        with self.assertRaises(ValueError):
            pack_order(2**64, 100, 1)

    def test_price_overflow_rejected(self):
        with self.assertRaises(ValueError):
            pack_order(1, 2**63, 1)

    def test_quantity_overflow_rejected(self):
        with self.assertRaises(ValueError):
            pack_order(1, 100, 2**32)

    def test_float_price_rejected(self):
        with self.assertRaises(TypeError):
            pack_order(1, 12.50, 1)

    def test_boolean_field_rejected(self):
        with self.assertRaises(TypeError):
            pack_order(True, 100, 1)

    def test_wrong_data_size_rejected(self):
        with self.assertRaises(ValueError):
            unpack_order(b"abc")

    def test_wrong_data_type_rejected(self):
        with self.assertRaises(TypeError):
            unpack_order("not bytes")


if __name__ == "__main__":
    unittest.main()
