

import argparse
import sys

from ring_buffer import RingBuffer


def consume_orders(path, count=3):
    if count < 0:
        raise ValueError("Count cannot be negative.")

    orders_read = 0

    if count == 0:
        print("Orders read: 0")
        return 0

    with RingBuffer(path) as ring:
        while orders_read < count:
            try:
                order = ring.read_order()

            except BufferError:
                print("Ring buffer is empty.")
                break

            order_id, price, quantity = order

            print(
                "Order ID: {}, Price: {}, Quantity: {}".format(
                    order_id, price, quantity
                )
            )

            orders_read += 1

    print("Orders read: {}".format(orders_read))

    return orders_read

def non_negative_int(value):
    number = int(value)

    if number < 0:
        raise argparse.ArgumentTypeError(
            "--count must be zero or greater"
        )

    return number


def main():
    parser = argparse.ArgumentParser(
        description="Read orders from the ChronosMatch ring buffer"
    )

    parser.add_argument(
        "--path",
        required=True,
        help="Path to the shared-memory file"
    )

    parser.add_argument(
        "--count",
        type=non_negative_int,
        default=3,
        help="Maximum number of orders to read"
    )

    args = parser.parse_args()

    try:
        consume_orders(args.path, args.count)

    except (OSError, ValueError) as error:
        print("Consumer error: {}".format(error))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
