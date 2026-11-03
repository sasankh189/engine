
import argparse
import multiprocessing
import os
import tempfile
import time
import queue
import uuid

from shared_memory import SharedMemoryRegion, DEFAULT_CAPACITY
from ring_buffer import RingBuffer
from order_generator import generate_orders


BATCH_SIZE = 1024
RETRY_DELAY = 0.001
PROCESS_TIMEOUT = 600


def producer_worker(
    path, count, start_id,
    producer_done, consumer_done, stop_event,
    results, batch_size
):
    written = 0

    try:
        with RingBuffer(path) as ring:
            orders = []

            for order in generate_orders(count, start_id):

                if stop_event.is_set():
                    raise RuntimeError("Audit stopped.")

                if consumer_done.is_set():
                    raise RuntimeError("Consumer stopped before producer finished.")

                orders.append(order)

                if len(orders) >= batch_size:

                    while True:
                        if stop_event.is_set():
                            raise RuntimeError("Audit stopped.")

                        if consumer_done.is_set():
                            raise RuntimeError(
                                "Consumer stopped while producer was writing."
                            )

                        try:
                            ring.write_orders(orders)
                            written += len(orders)
                            orders = []
                            break

                        except BufferError:
                            time.sleep(RETRY_DELAY)

            if orders:
                while True:
                    if stop_event.is_set():
                        raise RuntimeError("Audit stopped.")

                    if consumer_done.is_set():
                        raise RuntimeError(
                            "Consumer stopped before final batch."
                        )

                    try:
                        ring.write_orders(orders)
                        written += len(orders)
                        break

                    except BufferError:
                        time.sleep(RETRY_DELAY)

        results.put(("producer", written, None))

    except Exception as error:
        results.put(("producer", written, str(error)))

    finally:
        producer_done.set()


def consumer_worker(
    path, count, start_id,
    producer_done, consumer_done, stop_event,
    results, batch_size
):
    orders_read = 0
    mismatches = 0

    expected_orders = generate_orders(count, start_id)

    try:
        with RingBuffer(path) as ring:

            while orders_read < count:

                if stop_event.is_set():
                    raise RuntimeError("Audit stopped.")

                orders = ring.read_orders(batch_size)

                if not orders:

                    if producer_done.is_set():
                        break

                    time.sleep(RETRY_DELAY)
                    continue

                for actual_order in orders:

                    try:
                        expected_order = next(expected_orders)

                    except StopIteration:
                        mismatches += 1
                        orders_read += 1
                        continue

                    if actual_order != expected_order:
                        mismatches += 1

                    orders_read += 1

        results.put(("consumer", orders_read, mismatches))

    except Exception as error:
        results.put(("consumer", orders_read, str(error)))

    finally:
        consumer_done.set()


def run_audit(count, start_id=1001, capacity=DEFAULT_CAPACITY):

    if count < 0:
        raise ValueError("Count cannot be negative.")

    if start_id < 0:
        raise ValueError("Start ID cannot be negative.")

    if capacity <= 0:
        raise ValueError("Capacity must be positive.")

    max_uint64 = 18446744073709551615

    if count > 0 and start_id + count - 1 > max_uint64:
        raise ValueError("Order IDs exceed uint64 range.")

    batch_size = min(BATCH_SIZE, capacity)

    path = os.path.join(
        tempfile.gettempdir(),
        "chronosmatch_day12_{}_{}.bin".format(
            os.getpid(),
            uuid.uuid4().hex
        )
    )

    producer_done = multiprocessing.Event()
    consumer_done = multiprocessing.Event()
    stop_event = multiprocessing.Event()

    results = multiprocessing.Queue()

    producer = None
    consumer = None

    try:
        with SharedMemoryRegion.create(path, capacity=capacity):
            pass

        # Create the lock file before starting either process.
        with open(path + ".lock", "wb") as lock_file:
            lock_file.write(b"\0")

        consumer = multiprocessing.Process(
            target=consumer_worker,
            args=(
                path, count, start_id,
                producer_done, consumer_done, stop_event,
                results, batch_size
            )
        )

        producer = multiprocessing.Process(
            target=producer_worker,
            args=(
                path, count, start_id,
                producer_done, consumer_done, stop_event,
                results, batch_size
            )
        )

        start_time = time.perf_counter()

        consumer.start()
        producer.start()

        producer.join(PROCESS_TIMEOUT)

        if producer.is_alive():
            stop_event.set()
            producer_done.set()
            consumer_done.set()

            producer.terminate()
            producer.join()

            if consumer.is_alive():
                consumer.terminate()
                consumer.join()

            raise RuntimeError("Producer process timed out.")

        if producer.exitcode != 0:
            stop_event.set()
            producer_done.set()

            consumer.join(10)

            if consumer.is_alive():
                consumer.terminate()
                consumer.join()

            raise RuntimeError(
                "Producer exited with code {}".format(producer.exitcode)
            )

        consumer.join(PROCESS_TIMEOUT)

        if consumer.is_alive():
            stop_event.set()
            consumer_done.set()

            consumer.terminate()
            consumer.join()

            raise RuntimeError("Consumer process timed out.")

        elapsed = time.perf_counter() - start_time

        if consumer.exitcode != 0:
            raise RuntimeError(
                "Consumer exited with code {}".format(consumer.exitcode)
            )

        reports = {}

        for unused in range(2):
            try:
                name, total, detail = results.get(timeout=10)

            except queue.Empty:
                raise RuntimeError("Missing process report.")

            reports[name] = (total, detail)

        written, producer_error = reports["producer"]
        read, mismatches = reports["consumer"]

        if producer_error:
            raise RuntimeError("Producer error: " + producer_error)

        if isinstance(mismatches, str):
            raise RuntimeError("Consumer error: " + mismatches)

        throughput = read / elapsed if elapsed > 0 else 0

        success = (
            written == count
            and read == count
            and mismatches == 0
        )

        print("\n===== CHRONOSMATCH DAY 12 IPC AUDIT =====")
        print("Orders requested: {}".format(count))
        print("Orders written: {}".format(written))
        print("Orders read: {}".format(read))
        print("Data mismatches: {}".format(mismatches))
        print("Elapsed time: {:.6f} seconds".format(elapsed))
        print("Throughput: {:.2f} orders/second".format(throughput))
        print("Batch size: {}".format(batch_size))
        print("Buffer capacity: {}".format(capacity))
        print("Audit result: {}".format(
            "PASSED" if success else "FAILED"
        ))

        return success

    finally:
        stop_event.set()

        for process in (producer, consumer):
            if process is not None and process.is_alive():
                process.terminate()
                process.join()

        results.close()
        results.join_thread()

        for temporary_path in (path, path + ".lock"):
            if os.path.exists(temporary_path):
                try:
                    os.remove(temporary_path)
                except PermissionError:
                    print(
                        "Warning: Could not remove {}".format(
                            temporary_path
                        )
                    )


def main():

    parser = argparse.ArgumentParser(
        description="ChronosMatch Day 12 IPC Audit"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1000000
    )

    parser.add_argument(
        "--start-id",
        type=int,
        default=1001
    )

    parser.add_argument(
        "--capacity",
        type=int,
        default=DEFAULT_CAPACITY
    )

    args = parser.parse_args()

    try:
        success = run_audit(
            args.count,
            args.start_id,
            args.capacity
        )

        return 0 if success else 1

    except Exception as error:
        print("IPC audit error: {}".format(error))
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
