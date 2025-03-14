#!/usr/bin/env python

"""
Script to run performance tests for station monitoring and generate a report.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))


def run_command(command, cwd=None, env=None):
    """Run a command and return the output."""
    print(f"Running command: {command}")

    # Use current environment if none provided
    if env is None:
        env = os.environ.copy()

    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, env=env)
    print(f"Exit code: {result.returncode}")

    return result


def parse_test_output(output):
    """Parse the test output to extract performance metrics."""
    lines = output.split("\n")
    results = {}

    # Extract station monitoring performance results
    station_monitoring_section = False
    current_station_count = None

    # Extract concurrent processing performance results
    concurrent_processing_section = False
    current_concurrency_level = None

    # Extract system resource usage results
    resource_usage_section = False
    current_resource_count = None

    for line in lines:
        if "Station Monitoring Performance Results:" in line:
            station_monitoring_section = True
            concurrent_processing_section = False
            resource_usage_section = False
            results["station_monitoring"] = {}
            continue

        if "Concurrent Station Processing Performance Results:" in line:
            station_monitoring_section = False
            concurrent_processing_section = True
            resource_usage_section = False
            results["concurrent_processing"] = {}
            continue

        if "System Resource Usage During Monitoring:" in line:
            station_monitoring_section = False
            concurrent_processing_section = False
            resource_usage_section = True
            results["resource_usage"] = {}
            continue

        if station_monitoring_section:
            if line.startswith("Stations: "):
                current_station_count = int(line.split("Stations: ")[1])
                results["station_monitoring"][current_station_count] = {}
            elif line.startswith("Processing Time: ") and current_station_count is not None:
                processing_time = float(line.split("Processing Time: ")[1].split(" seconds")[0])
                results["station_monitoring"][current_station_count][
                    "processing_time"
                ] = processing_time
            elif line.startswith("Stations Per Second: ") and current_station_count is not None:
                stations_per_second = float(line.split("Stations Per Second: ")[1])
                results["station_monitoring"][current_station_count][
                    "stations_per_second"
                ] = stations_per_second
            elif line.startswith("Average Processing Time: "):
                avg_processing_time = float(
                    line.split("Average Processing Time: ")[1].split(" seconds")[0]
                )
                results["avg_processing_time"] = avg_processing_time
            elif line.startswith("Average Stations Per Second: "):
                avg_stations_per_second = float(line.split("Average Stations Per Second: ")[1])
                results["avg_stations_per_second"] = avg_stations_per_second
            elif line.startswith("Estimated Optimal Number of Stations for 60-second processing: "):
                estimated_optimal_stations = int(
                    line.split("Estimated Optimal Number of Stations for 60-second processing: ")[1]
                )
                results["estimated_optimal_stations"] = estimated_optimal_stations

        if concurrent_processing_section:
            if line.startswith("Concurrency Level: "):
                current_concurrency_level = int(line.split("Concurrency Level: ")[1])
                results["concurrent_processing"][current_concurrency_level] = {}
            elif line.startswith("Processing Time: ") and current_concurrency_level is not None:
                processing_time = float(line.split("Processing Time: ")[1].split(" seconds")[0])
                results["concurrent_processing"][current_concurrency_level][
                    "processing_time"
                ] = processing_time
            elif line.startswith("Stations Per Second: ") and current_concurrency_level is not None:
                stations_per_second = float(line.split("Stations Per Second: ")[1])
                results["concurrent_processing"][current_concurrency_level][
                    "stations_per_second"
                ] = stations_per_second
            elif line.startswith("Optimal Concurrency Level: "):
                optimal_concurrency = int(line.split("Optimal Concurrency Level: ")[1])
                results["optimal_concurrency"] = optimal_concurrency

        if resource_usage_section:
            if line.startswith("Stations: "):
                current_resource_count = int(line.split("Stations: ")[1])
                results["resource_usage"][current_resource_count] = {}
            elif line.startswith("CPU Usage: ") and current_resource_count is not None:
                cpu_usage = float(line.split("CPU Usage: ")[1].split("%")[0])
                results["resource_usage"][current_resource_count]["cpu_usage"] = cpu_usage
            elif line.startswith("Memory Usage: ") and current_resource_count is not None:
                memory_usage = float(line.split("Memory Usage: ")[1].split(" MB")[0])
                results["resource_usage"][current_resource_count]["memory_usage"] = memory_usage
            elif line.startswith(
                "Estimated Maximum Number of Stations Based on Available Resources: "
            ):
                max_stations = line.split(
                    "Estimated Maximum Number of Stations Based on Available Resources: "
                )[1]
                try:
                    max_stations = int(max_stations)
                except ValueError:
                    max_stations = "inf"
                results["max_stations"] = max_stations

    return results


def generate_plots(results, output_dir):
    """Generate plots from the performance test results."""
    os.makedirs(output_dir, exist_ok=True)

    # Plot station monitoring performance
    if "station_monitoring" in results:
        station_counts = sorted(results["station_monitoring"].keys())
        processing_times = [
            results["station_monitoring"][count]["processing_time"] for count in station_counts
        ]
        stations_per_second = [
            results["station_monitoring"][count]["stations_per_second"] for count in station_counts
        ]

        plt.figure(figsize=(10, 6))
        plt.plot(station_counts, processing_times, "o-", label="Processing Time (s)")
        plt.xlabel("Number of Stations")
        plt.ylabel("Processing Time (s)")
        plt.title("Station Monitoring Performance")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "station_monitoring_time.png"))
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(station_counts, stations_per_second, "o-", label="Stations Per Second")
        plt.xlabel("Number of Stations")
        plt.ylabel("Stations Per Second")
        plt.title("Station Monitoring Throughput")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "station_monitoring_throughput.png"))
        plt.close()

    # Plot concurrent processing performance
    if "concurrent_processing" in results:
        concurrency_levels = sorted(results["concurrent_processing"].keys())
        processing_times = [
            results["concurrent_processing"][level]["processing_time"]
            for level in concurrency_levels
        ]
        stations_per_second = [
            results["concurrent_processing"][level]["stations_per_second"]
            for level in concurrency_levels
        ]

        plt.figure(figsize=(10, 6))
        plt.plot(concurrency_levels, processing_times, "o-", label="Processing Time (s)")
        plt.xlabel("Concurrency Level")
        plt.ylabel("Processing Time (s)")
        plt.title("Concurrent Processing Performance")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "concurrent_processing_time.png"))
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(concurrency_levels, stations_per_second, "o-", label="Stations Per Second")
        plt.xlabel("Concurrency Level")
        plt.ylabel("Stations Per Second")
        plt.title("Concurrent Processing Throughput")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "concurrent_processing_throughput.png"))
        plt.close()

    # Plot system resource usage
    if "resource_usage" in results:
        station_counts = sorted(results["resource_usage"].keys())
        cpu_usage = [results["resource_usage"][count]["cpu_usage"] for count in station_counts]
        memory_usage = [
            results["resource_usage"][count]["memory_usage"] for count in station_counts
        ]

        plt.figure(figsize=(10, 6))
        plt.plot(station_counts, cpu_usage, "o-", label="CPU Usage (%)")
        plt.xlabel("Number of Stations")
        plt.ylabel("CPU Usage (%)")
        plt.title("CPU Usage During Station Monitoring")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "cpu_usage.png"))
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(station_counts, memory_usage, "o-", label="Memory Usage (MB)")
        plt.xlabel("Number of Stations")
        plt.ylabel("Memory Usage (MB)")
        plt.title("Memory Usage During Station Monitoring")
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "memory_usage.png"))
        plt.close()


def generate_report(results, output_dir):
    """Generate a report from the performance test results."""
    os.makedirs(output_dir, exist_ok=True)

    report_file = os.path.join(output_dir, "performance_report.html")

    with open(report_file, "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Station Monitoring Performance Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                h1, h2, h3 {{
                    color: #333;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .summary {{
                    background-color: #e6f7ff;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .plot {{
                    margin: 20px 0;
                    text-align: center;
                }}
                .plot img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Station Monitoring Performance Report</h1>
            <p>Generated on: {0}</p>

            <div class="summary">
                <h2>Summary</h2>
        """.format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        # Write summary
        if "avg_processing_time" in results:
            f.write(f"<p>Average Processing Time: {results['avg_processing_time']:.2f} seconds</p>")
        if "avg_stations_per_second" in results:
            f.write(f"<p>Average Stations Per Second: {results['avg_stations_per_second']:.2f}</p>")
        if "estimated_optimal_stations" in results:
            f.write(
                f"<p>Estimated Optimal Number of Stations for 60-second processing: {results['estimated_optimal_stations']}</p>"
            )
        if "optimal_concurrency" in results:
            f.write(f"<p>Optimal Concurrency Level: {results['optimal_concurrency']}</p>")
        if "max_stations" in results:
            f.write(
                f"<p>Estimated Maximum Number of Stations Based on Available Resources: {results['max_stations']}</p>"
            )

        f.write("</div>")

        # Write station monitoring performance results
        if "station_monitoring" in results:
            f.write(
                """
            <h2>Station Monitoring Performance</h2>
            <table>
                <tr>
                    <th>Number of Stations</th>
                    <th>Processing Time (s)</th>
                    <th>Stations Per Second</th>
                </tr>
            """
            )

            for count in sorted(results["station_monitoring"].keys()):
                data = results["station_monitoring"][count]
                f.write(
                    f"""
                <tr>
                    <td>{count}</td>
                    <td>{data['processing_time']:.2f}</td>
                    <td>{data['stations_per_second']:.2f}</td>
                </tr>
                """
                )

            f.write("</table>")

            f.write(
                """
            <div class="plot">
                <h3>Processing Time vs. Number of Stations</h3>
                <img src="station_monitoring_time.png" alt="Processing Time vs. Number of Stations">
            </div>

            <div class="plot">
                <h3>Throughput vs. Number of Stations</h3>
                <img src="station_monitoring_throughput.png" alt="Throughput vs. Number of Stations">
            </div>
            """
            )

        # Write concurrent processing performance results
        if "concurrent_processing" in results:
            f.write(
                """
            <h2>Concurrent Processing Performance</h2>
            <table>
                <tr>
                    <th>Concurrency Level</th>
                    <th>Processing Time (s)</th>
                    <th>Stations Per Second</th>
                </tr>
            """
            )

            for level in sorted(results["concurrent_processing"].keys()):
                data = results["concurrent_processing"][level]
                f.write(
                    f"""
                <tr>
                    <td>{level}</td>
                    <td>{data['processing_time']:.2f}</td>
                    <td>{data['stations_per_second']:.2f}</td>
                </tr>
                """
                )

            f.write("</table>")

            f.write(
                """
            <div class="plot">
                <h3>Processing Time vs. Concurrency Level</h3>
                <img src="concurrent_processing_time.png" alt="Processing Time vs. Concurrency Level">
            </div>

            <div class="plot">
                <h3>Throughput vs. Concurrency Level</h3>
                <img src="concurrent_processing_throughput.png" alt="Throughput vs. Concurrency Level">
            </div>
            """
            )

        # Write system resource usage results
        if "resource_usage" in results:
            f.write(
                """
            <h2>System Resource Usage</h2>
            <table>
                <tr>
                    <th>Number of Stations</th>
                    <th>CPU Usage (%)</th>
                    <th>Memory Usage (MB)</th>
                </tr>
            """
            )

            for count in sorted(results["resource_usage"].keys()):
                data = results["resource_usage"][count]
                f.write(
                    f"""
                <tr>
                    <td>{count}</td>
                    <td>{data['cpu_usage']:.2f}</td>
                    <td>{data['memory_usage']:.2f}</td>
                </tr>
                """
                )

            f.write("</table>")

            f.write(
                """
            <div class="plot">
                <h3>CPU Usage vs. Number of Stations</h3>
                <img src="cpu_usage.png" alt="CPU Usage vs. Number of Stations">
            </div>

            <div class="plot">
                <h3>Memory Usage vs. Number of Stations</h3>
                <img src="memory_usage.png" alt="Memory Usage vs. Number of Stations">
            </div>
            """
            )

        f.write(
            """
            <h2>Recommendations</h2>
            <p>Based on the performance test results, here are some recommendations:</p>
            <ul>
        """
        )

        if "estimated_optimal_stations" in results:
            f.write(
                f"<li>For optimal performance, monitor no more than {results['estimated_optimal_stations']} stations simultaneously.</li>"
            )
        if "optimal_concurrency" in results:
            f.write(
                f"<li>Use a concurrency level of {results['optimal_concurrency']} for best throughput.</li>"
            )
        if "max_stations" in results:
            f.write(
                f"<li>Based on system resources, the maximum number of stations that can be monitored is approximately {results['max_stations']}.</li>"
            )

        f.write(
            """
            </ul>

            <h2>Conclusion</h2>
            <p>
                The performance tests show that the system can effectively monitor multiple radio stations simultaneously.
                By following the recommendations above, you can optimize the monitoring process for your specific needs.
            </p>

        </body>
        </html>
        """
        )

    print(f"Report generated: {report_file}")
    return report_file


def main():
    """Run the performance tests and generate a report."""
    # Create output directory
    output_dir = os.path.join(
        project_root, "reports", "performance", datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    os.makedirs(output_dir, exist_ok=True)

    # Install required packages
    print("Installing required packages...")
    run_command("pip install matplotlib numpy psutil")

    # Run the performance tests
    print("Running performance tests...")
    result = run_command(
        "python -m pytest -xvs backend/tests/performance/test_station_monitoring.py::test_create_stations backend/tests/performance/test_station_monitoring.py::test_concurrent_processing_simulation backend/tests/performance/test_station_monitoring.py::test_resource_usage_simulation",
        cwd=str(project_root),
    )

    # Save the test output
    with open(os.path.join(output_dir, "test_output.txt"), "w") as f:
        f.write(result.stdout)

    # Parse the test output
    print("Parsing test output...")
    results = parse_test_output(result.stdout)

    # Save the parsed results
    with open(os.path.join(output_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Generate plots
    print("Generating plots...")
    generate_plots(results, output_dir)

    # Generate report
    print("Generating report...")
    report_file = generate_report(results, output_dir)

    print(f"Performance testing completed. Results saved to: {output_dir}")
    print(f"Report: {report_file}")


if __name__ == "__main__":
    main()
