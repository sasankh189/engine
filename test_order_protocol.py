
import unittest

from order_protocol import (
    ORDER_SIZE,
    pack_order,
    unpack_order,
)


class TestOrderProtocol(unittest.TestCase):

    def test_order_round_trip(self):
        order = (1001, 12550, 10)
        packed = pack_order(*order)

        self.assertEqual(len(packed), 20)
        self.assertEqual(unpack_order(packed), order)

    def test_negative_price(self):
        order = (1002, -500, 5)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_zero_values(self):
        order = (0, 0, 0)
        self.assertEqual(unpack_order(pack_order(*order)), order)

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            pack_order(1001, 12550, -1)

    def test_wrong_data_size(self):
        with self.assertRaises(ValueError):
            unpack_order(b"abc")

    def test_wrong_data_type(self):
        with self.assertRaises(TypeError):
            unpack_order("not bytes")

    def test_format_size(self):
        self.assertEqual(ORDER_SIZE, 20)


if __name__ == "__main__":
    unittest.main()
