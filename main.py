
import argparse
import asyncio
import multiprocessing as mp
import os
import statistics
import time

from market_simulator import produce_orders
from order_protocol import BUY, SELL, unpack_order
from ring_buffer import MMapRingBuffer
from matching_engine import OrderBook, ENGINE_MODE
from trade_ledger import TradeLedger

SENTINEL = b"STOPCHRONOSMATCH".ljust(24, b"\0")

def consumer_worker(path, capacity, lock, number_of_orders, result_queue):
    buffer = MMapRingBuffer(path, capacity=capacity, lock=lock)
    book = OrderBook()
    ledger = TradeLedger()
    latencies = []
    processed = 0
    total_trades = 0
    try:
        while processed < number_of_orders:
            record = buffer.get(timeout=60)
            order = unpack_order(record)
            start_ns = time.perf_counter_ns()
            trades = book.add_order(order)
            end_ns = time.perf_counter_ns()
            latencies.append(end_ns - start_ns)
            if trades:
                ledger.save_many(trades)
                total_trades += len(trades)
            processed += 1
        result_queue.put({
            "processed": processed,
            "trades": total_trades,
            "ledger_count": ledger.count(),
            "latencies": latencies,
            "best_bid": book.best_bid(),
            "best_ask": book.best_ask(),
        })
    finally:
        ledger.close()
        buffer.close()

async def run(args):
    path = os.path.abspath("chronos_ring.bin")
    if os.path.exists(path):
        os.remove(path)

    capacity = max(4096, min(args.orders, 65536))
    lock = mp.Lock()
    result_queue = mp.Queue()
    buffer = MMapRingBuffer(path, capacity=capacity, lock=lock, create=True)
    process = mp.Process(
        target=consumer_worker,
        args=(path, capacity, lock, args.orders, result_queue),
    )
    process.start()
    producer_start = time.perf_counter()
    try:
        producer_seconds = await produce_orders(buffer, args.orders)
    finally:
        buffer.close()
    process.join(timeout=120)

    if process.is_alive():
        process.terminate()
        process.join()
        raise RuntimeError("Consumer timed out; try a smaller order count.")
    if process.exitcode != 0:
        raise RuntimeError("Consumer process failed. Check terminal output.")

    results = result_queue.get(timeout=5)
    latencies = sorted(results["latencies"])
    def percentile(values, p):
        if not values:
            return 0
        return values[min(len(values)-1, int((len(values)-1) * p))]

    elapsed = max(time.perf_counter() - producer_start, 1e-9)
    print("\n========== CHRONOSMATCH RESULTS ==========")
    print("Engine mode       :", ENGINE_MODE)
    print("Orders processed  :", results["processed"])
    print("Trades executed   :", results["trades"])
    print("Trades in SQLite  :", results["ledger_count"])
    print("Best bid          :", f"{results['best_bid']/100:.2f}" if results["best_bid"] else "—")
    print("Best ask          :", f"{results['best_ask']/100:.2f}" if results["best_ask"] else "—")
    print("Producer time     :", f"{producer_seconds:.3f} seconds")
    print("End-to-end runtime:", f"{elapsed:.3f} seconds")
    print("Observed rate     :", f"{results['processed']/elapsed:,.0f} orders/sec")
    print("Engine latency p50:", f"{percentile(latencies, .50):,} ns")
    print("Engine latency p95:", f"{percentile(latencies, .95):,} ns")
    print("Engine latency p99:", f"{percentile(latencies, .99):,} ns")
    print("==========================================")
    print("Database: chronos_trades.db")
    print("Ring file: chronos_ring.bin")

def main():
    parser = argparse.ArgumentParser(description="ChronosMatch demo")
    parser.add_argument("--orders", type=int, default=10000,
                        help="number of simulated orders (default: 10000)")
    args = parser.parse_args()
    if args.orders < 1:
        parser.error("--orders must be at least 1")
    mp.freeze_support()
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
