
import argparse
import time

from order_generator import generate_orders


def benchmark_orders(count, start_id=1001):
    start_time = time.perf_counter()

    orders_generated = 0

    for order in generate_orders(count, start_id):
        orders_generated += 1

    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    if elapsed_time > 0:
        throughput = orders_generated / elapsed_time
    else:
        throughput = 0

    print("\n===== CHRONOSMATCH DAY 11 BENCHMARK =====")
    print("Orders generated: {}".format(orders_generated))
    print("Elapsed time: {:.6f} seconds".format(elapsed_time))
    print("Throughput: {:.2f} orders/second".format(throughput))

    return orders_generated, elapsed_time, throughput


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch Order Generation Benchmark"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=100000,
        help="Number of orders to generate"
    )

    parser.add_argument(
        "--start-id",
        type=int,
        default=1001,
        help="Starting order ID"
    )

    args = parser.parse_args()

    if args.count < 0:
        parser.error("--count must be zero or greater")

    benchmark_orders(args.count, args.start_id)


if __name__ == "__main__":
    main()
