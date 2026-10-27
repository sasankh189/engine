
import argparse
import sys

from ring_buffer import RingBuffer


def produce_orders(path, count, start_id=1001):
    if count <= 0:
        raise ValueError("Count must be greater than zero.")

    if start_id < 0:
        raise ValueError("Start ID cannot be negative.")

    written = 0

    with RingBuffer(path) as buffer:
        for i in range(count):
            order_id = start_id + i
            price = 12500 + (i * 10)
            quantity = (i % 10) + 1

            try:
                sequence = buffer.write_order(
                    order_id,
                    price,
                    quantity
                )
            except BufferError:
                print(
                    "Buffer is full. Stopping producer.",
                    file=sys.stderr
                )
                break

            print(
                "Wrote order:",
                (order_id, price, quantity),
                "| Sequence:",
                sequence
            )

            written += 1

        print("Orders written:", written)
        print("Final header:", buffer.get_header())

    return written


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch shared-memory order producer"
    )

    parser.add_argument(
        "--path",
        required=True,
        help="Path to the existing shared-memory file"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of orders to produce"
    )

    parser.add_argument(
        "--start-id",
        type=int,
        default=1001,
        help="ID of the first order"
    )

    args = parser.parse_args()

    try:
        produce_orders(
            args.path,
            args.count,
            args.start_id
        )
    except (ValueError, TypeError, OSError) as error:
        print("Producer error:", error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
