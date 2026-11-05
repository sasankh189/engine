
import argparse
import csv
import os


REQUIRED_COLUMNS = [
    "orders",
    "time",
    "throughput",
    "status"
]


def load_results(csv_path):
    results = []

    with open(csv_path, "r", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty.")

        for column in REQUIRED_COLUMNS:
            if column not in reader.fieldnames:
                raise ValueError(
                    "Missing CSV column: {}".format(column)
                )

        for row in reader:
            results.append({
                "orders": int(row["orders"]),
                "time": float(row["time"]),
                "throughput": float(row["throughput"]),
                "status": row["status"].strip().upper()
            })

    return results


def analyze_results(results):
    passed = [
        result for result in results
        if result["status"] == "PASSED"
    ]

    failed = [
        result for result in results
        if result["status"] != "PASSED"
    ]

    if not passed:
        raise ValueError("No successful benchmark results found.")

    passed.sort(key=lambda result: result["orders"])

    best = max(
        passed,
        key=lambda result: result["throughput"]
    )

    average = sum(
        result["throughput"] for result in passed
    ) / len(passed)

    first = passed[0]

    growth = (
        best["throughput"] / first["throughput"]
        if first["throughput"] > 0 else 0
    )

    return {
        "passed": passed,
        "failed": failed,
        "best": best,
        "average": average,
        "growth": growth
    }


def create_report(results):
    analysis = analyze_results(results)

    lines = []

    lines.append("CHRONOSMATCH DAY 14")
    lines.append("IPC PERFORMANCE ANALYSIS REPORT")
    lines.append("=" * 55)
    lines.append("")

    lines.append(
        "Successful benchmarks: {}".format(
            len(analysis["passed"])
        )
    )

    lines.append(
        "Failed benchmarks: {}".format(
            len(analysis["failed"])
        )
    )

    lines.append("")
    lines.append("BENCHMARK RESULTS")
    lines.append("-" * 55)

    lines.append(
        "{:<12} {:<15} {:<20} {}".format(
            "Orders",
            "Time (sec)",
            "Orders/sec",
            "Status"
        )
    )

    for result in analysis["passed"]:
        lines.append(
            "{:<12} {:<15.6f} {:<20.2f} {}".format(
                result["orders"],
                result["time"],
                result["throughput"],
                result["status"]
            )
        )

    for result in analysis["failed"]:
        lines.append(
            "{:<12} {:<15.6f} {:<20.2f} {}".format(
                result["orders"],
                result["time"],
                result["throughput"],
                result["status"]
            )
        )

    best = analysis["best"]

    lines.append("")
    lines.append("PERFORMANCE SUMMARY")
    lines.append("-" * 55)

    lines.append(
        "Highest throughput: {:.2f} orders/second".format(
            best["throughput"]
        )
    )

    lines.append(
        "Best workload: {} orders".format(best["orders"])
    )

    lines.append(
        "Average throughput: {:.2f} orders/second".format(
            analysis["average"]
        )
    )

    lines.append(
        "Throughput growth factor: {:.2f}x".format(
            analysis["growth"]
        )
    )

    lines.append("")
    lines.append("OBSERVATIONS")
    lines.append("-" * 55)

    lines.append(
        "The IPC audit measures producer-consumer communication "
        "using shared memory."
    )

    lines.append(
        "The benchmark includes process startup, synchronization, "
        "data transfer and cleanup."
    )

    lines.append(
        "Further optimization should focus on reducing "
        "synchronization and locking overhead."
    )

    lines.append("")
    lines.append("End of report.")

    return "\n".join(lines)


def generate_report(csv_path, output_path):
    results = load_results(csv_path)
    report = create_report(results)

    with open(output_path, "w") as file:
        file.write(report)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch Day 14 Performance Analysis"
    )

    parser.add_argument(
        "--input",
        default="day13_ipc_benchmark.csv"
    )

    parser.add_argument(
        "--output",
        default="day14_performance_report.txt"
    )

    args = parser.parse_args()

    project_folder = os.path.dirname(
        os.path.abspath(__file__)
    )

    csv_path = os.path.join(project_folder, args.input)
    output_path = os.path.join(project_folder, args.output)

    if not os.path.isfile(csv_path):
        print("Error: Benchmark CSV file not found.")
        return 1

    try:
        report = generate_report(csv_path, output_path)

        print(report)
        print("\nReport saved to:", output_path)

        return 0

    except (ValueError, OSError) as error:
        print("Performance analysis error:", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
