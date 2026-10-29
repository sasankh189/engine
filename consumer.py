
import argparse

from ring_buffer import RingBuffer


def consume_orders(path, count=3):
    orders_read = 0

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
        type=int,
        default=3,
        help="Maximum number of orders to read"
    )

    args = parser.parse_args()

    if args.count < 0:
        parser.error("--count must be zero or greater")

    consume_orders(args.path, args.count)


if __name__ == "__main__":
    main()
