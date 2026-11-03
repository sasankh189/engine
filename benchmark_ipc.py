
import argparse
import csv
import os
import subprocess
import sys
import time


def run_benchmark(count, audit_file):
    command = [
        sys.executable,
        audit_file,
        "--count",
        str(count)
    ]

    print("\n====================================")
    print("Running benchmark: {} orders".format(count))
    print("====================================")

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=700
        )

        elapsed = time.perf_counter() - start_time

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("Errors:")
            print(result.stderr)

        if result.returncode == 0:
            throughput = count / elapsed if elapsed > 0 else 0

            print("Benchmark status: PASSED")
            print("Total execution time: {:.6f} seconds".format(elapsed))
            print("Throughput: {:.2f} orders/second".format(throughput))

            return {
                "orders": count,
                "time": round(elapsed, 6),
                "throughput": round(throughput, 2),
                "status": "PASSED"
            }

        print("Benchmark status: FAILED")

        return {
            "orders": count,
            "time": round(elapsed, 6),
            "throughput": 0,
            "status": "FAILED"
        }

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time

        print("Benchmark timed out.")

        return {
            "orders": count,
            "time": round(elapsed, 6),
            "throughput": 0,
            "status": "TIMEOUT"
        }


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch Day 13 IPC Performance Benchmark"
    )

    parser.add_argument(
        "--counts",
        default="10000,50000,100000,250000,1000000",
        help="Comma-separated order counts"
    )

    parser.add_argument(
        "--output",
        default="day13_ipc_benchmark.csv",
        help="CSV output filename"
    )

    args = parser.parse_args()

    try:
        counts = [
            int(value.strip())
            for value in args.counts.split(",")
        ]

        if not counts or any(count <= 0 for count in counts):
            raise ValueError("All order counts must be positive.")

    except ValueError as error:
        print("Invalid order counts:", error)
        return 1

    project_folder = os.path.dirname(os.path.abspath(__file__))

    audit_file = os.path.join(
        project_folder,
        "ipc_audit.py"
    )

    output_file = os.path.join(
        project_folder,
        args.output
    )

    if not os.path.isfile(audit_file):
        print("Error: ipc_audit.py was not found.")
        return 1

    results = []

    for count in counts:
        result = run_benchmark(count, audit_file)
        results.append(result)

    with open(output_file, "w", newline="") as csv_file:
        fieldnames = [
            "orders",
            "time",
            "throughput",
            "status"
        ]

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n========== DAY 13 SUMMARY ==========")
    print("{:<12} {:<15} {:<20} {}".format(
        "Orders",
        "Time (sec)",
        "Orders/sec",
        "Status"
    ))

    for result in results:
        print("{:<12} {:<15} {:<20} {}".format(
            result["orders"],
            result["time"],
            result["throughput"],
            result["status"]
        ))

    print("\nResults saved to:", output_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
