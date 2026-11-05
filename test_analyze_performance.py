
import csv
import os
import tempfile
import unittest

from analyze_performance import (
    load_results,
    analyze_results,
    create_report,
    generate_report
)


class TestPerformanceAnalysis(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(
            self.temp_dir.name,
            "test_benchmark.csv"
        )

        self.results = [
            {
                "orders": 10000,
                "time": 0.35,
                "throughput": 28571.42,
                "status": "PASSED"
            },
            {
                "orders": 100000,
                "time": 0.66,
                "throughput": 151515.15,
                "status": "PASSED"
            },
            {
                "orders": 1000000,
                "time": 3.74,
                "throughput": 267379.67,
                "status": "PASSED"
            },
            {
                "orders": 250000,
                "time": 2.0,
                "throughput": 0,
                "status": "FAILED"
            }
        ]

        with open(self.csv_path, "w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "orders",
                    "time",
                    "throughput",
                    "status"
                ]
            )

            writer.writeheader()
            writer.writerows(self.results)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_results(self):
        results = load_results(self.csv_path)

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["orders"], 10000)

    def test_analyze_successful_results(self):
        results = load_results(self.csv_path)
        analysis = analyze_results(results)

        self.assertEqual(len(analysis["passed"]), 3)
        self.assertEqual(len(analysis["failed"]), 1)

    def test_find_best_throughput(self):
        analysis = analyze_results(self.results)

        self.assertEqual(
            analysis["best"]["orders"],
            1000000
        )

    def test_average_throughput(self):
        analysis = analyze_results(self.results)

        self.assertGreater(analysis["average"], 0)

    def test_report_content(self):
        report = create_report(self.results)

        self.assertIn("CHRONOSMATCH DAY 14", report)
        self.assertIn("PERFORMANCE SUMMARY", report)
        self.assertIn("1000000", report)

    def test_no_successful_results(self):
        failed_results = [
            {
                "orders": 10000,
                "time": 1.0,
                "throughput": 0,
                "status": "FAILED"
            }
        ]

        with self.assertRaises(ValueError):
            analyze_results(failed_results)

    def test_generate_report_file(self):
        output_path = os.path.join(
            self.temp_dir.name,
            "day14_report.txt"
        )

        generate_report(self.csv_path, output_path)

        self.assertTrue(os.path.isfile(output_path))


if __name__ == "__main__":
    unittest.main()
