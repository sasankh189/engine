
import unittest

from order_generator import generate_orders


class TestOrderGenerator(unittest.TestCase):

    def test_generate_five_orders(self):
        orders = list(generate_orders(5))

        expected = [
            (1001, 12500, 1),
            (1002, 12510, 2),
            (1003, 12520, 3),
            (1004, 12530, 4),
            (1005, 12540, 5)
        ]

        self.assertEqual(orders, expected)

    def test_custom_start_id(self):
        orders = list(generate_orders(2, start_id=5000))

        self.assertEqual(
            orders,
            [
                (5000, 12500, 1),
                (5001, 12510, 2)
            ]
        )

    def test_zero_orders(self):
        self.assertEqual(list(generate_orders(0)), [])

    def test_negative_count(self):
        with self.assertRaises(ValueError):
            list(generate_orders(-1))

    def test_negative_start_id(self):
        with self.assertRaises(ValueError):
            list(generate_orders(5, start_id=-1))

    def test_invalid_count(self):
        with self.assertRaises(ValueError):
            list(generate_orders("100"))

    def test_generator_is_lazy(self):
        orders = generate_orders(1000000)

        self.assertEqual(
            next(orders),
            (1001, 12500, 1)
        )

    def test_order_ids_are_sequential(self):
        orders = list(generate_orders(100))

        ids = [order[0] for order in orders]

        self.assertEqual(ids, list(range(1001, 1101)))


if __name__ == "__main__":
    unittest.main()
