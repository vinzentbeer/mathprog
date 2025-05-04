# benchmarking.py

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

# Debug util accessibility .......
try:
    from util import read_instance
except ImportError:
    print("Error: Could not import 'read_instance' from 'util'. "
          "Make sure util.py is in the same directory or your PYTHONPATH.")
    sys.exit(1)

# --- Configuration ---
DATA_DIR_DEFAULT = "./mathprog-programming/data"
OUTPUT_CSV_DEFAULT = "benchmark_results.csv"
# List of formulation identifiers expected by kmst.py
#FORMULATIONS = ["seq", "scf", "mcf", "cec", "dcc"]
FORMULATIONS = ["seq", "scf"]# lets just use a subset for now
#benchmark params
THREADS = 1
TIMELIMIT = 3600 # seconds (1 hour)
MEMORYLIMIT = 8  # GB
# Temporary file for passing results from subprocess
TEMP_RESULT_FILENAME = "_temp_bench_result.json"

def calculate_k_values(num_nodes):
    """Calculates the required k values based on the number of nodes (|V|)."""
    if num_nodes <= 0:
        # Handle cases like empty graph if necessary, though unlikely for these instances
        return set()
    # k = floor(|V|/2)
    k1 = math.floor(num_nodes / 2)
    # k = ceil(2*|V|/3)
    k2 = math.ceil(2 * num_nodes / 3)
    # Ensure k is within the valid range {0, ..., |V|} and store unique values
    k_values = {max(0, min(num_nodes, k)) for k in [k1, k2]}
    # k=0 is trivial (empty tree, cost 0), often excluded unless specifically needed.
    # Let's keep it for now as it's technically in the range.
    return k_values

def run_single_experiment(instance_path, k_value, formulation, temp_result_path):
    """
    Runs kmst.py for a single configuration using subprocess and captures results.

    Args:
        instance_path (Path): Path to the instance .dat file.
        k_value (int): The value of k for the k-MST problem.
        formulation (str): The formulation type ('seq', 'scf', etc.).
        temp_result_path (Path): Path to use for the temporary results JSON file.

    Returns:
        dict: A dictionary containing the results from kmst.py, or None if the run failed.
    """
    # Construct the command to execute kmst.py
    command = [
        sys.executable,        # Use the same python interpreter running this script
        "./src/kmst/kmst.py",             # The script to run
        "--instance", str(instance_path),
        "--k", str(k_value),
        "--formulation", formulation,
        "--threads", str(THREADS),
        "--timelimit", str(TIMELIMIT),
        "--memorylimit", str(MEMORYLIMIT),
        "--results-file", str(temp_result_path)
        # We don't need --solution-file for benchmarking runs
    ]

    print(f"  Executing: {' '.join(command)}")
    start_time = time.time()
    run_successful = False
    run_data = None

    try:
        # Execute the command, capture output, don't raise exception on failure
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        end_time = time.time()
        print(f"  Run finished in {end_time - start_time:.2f}s. Exit code: {result.returncode}")

        # Check if the subprocess indicated success (exit code 0)
        if result.returncode == 0:
            # Check if the temporary result file was created by kmst.py
            if temp_result_path.exists():
                try:
                    with open(temp_result_path, 'r', encoding='utf-8') as f:
                        run_data = json.load(f)
                    # **IMPORTANT**: Assumes kmst.py adds 'n_lazy_constraints'
                    # Provide a default if it's missing (e.g., for non-CEC/DCC)
                    run_data.setdefault('n_lazy_constraints', 0)
                    run_successful = True
                except json.JSONDecodeError:
                    print(f"  ERROR: Failed to decode JSON from temp file: {temp_result_path}")
                except Exception as e:
                    print(f"  ERROR: Failed to read temp file {temp_result_path}: {e}")
            else:
                print(f"  ERROR: Subprocess exited successfully, but temp result file "
                      f"'{temp_result_path}' was not found.")
                print("----- STDOUT -----")
                print(result.stdout)
                print("----- STDERR -----")
                print(result.stderr)
                print("------------------")
        else:
            # Subprocess failed, print details for debugging
            print(f"  ERROR: kmst.py failed for {instance_path.name} k={k_value} form={formulation}")
            print("----- STDOUT -----")
            print(result.stdout)
            print("----- STDERR -----")
            print(result.stderr)
            print("------------------")

    except Exception as e:
        # Catch errors during subprocess execution itself
        print(f"  ERROR: Exception during subprocess execution: {e}")
    finally:
        # --- Cleanup ---
        # Ensure the temporary file is deleted, regardless of success/failure
        if temp_result_path.exists():
            try:
                temp_result_path.unlink()
            except OSError as e:
                # Log warning if deletion fails, but continue
                print(f"  Warning: Could not delete temp file {temp_result_path}: {e}")

    return run_data # Returns the dictionary on success, None on failure

def main():
    """Parses arguments, runs benchmarks, and writes results to CSV."""
    parser = argparse.ArgumentParser(description="Run k-MST benchmarks using kmst.py")
    parser.add_argument("--data-dir", type=str, default=DATA_DIR_DEFAULT,
                        help=f"Directory containing instance .dat files (default: {DATA_DIR_DEFAULT})")
    parser.add_argument("--output-csv", type=str, default=OUTPUT_CSV_DEFAULT,
                        help=f"Path to write the consolidated results CSV file (default: {OUTPUT_CSV_DEFAULT})")
    # Allow specifying specific formulations to run, defaults to all
    parser.add_argument("--formulations", nargs='+', default=FORMULATIONS, choices=FORMULATIONS,
                        help="List of formulations to test (default: all)")
    args = parser.parse_args()

    data_path = Path(args.data_dir)
    output_csv_path = Path(args.output_csv)
    # Use a temporary file in the current directory for simplicity
    temp_result_path = Path(TEMP_RESULT_FILENAME).resolve()
    formulations_to_run = args.formulations

    # --- Input Validation ---
    if not data_path.is_dir():
        print(f"Error: Data directory not found: {data_path}")
        sys.exit(1)

    # Find instance files (.dat)
    instance_files = sorted(list(data_path.glob("*.dat")))
    if not instance_files:
        print(f"Error: No .dat instance files found in {data_path}")
        sys.exit(1)

    print(f"Found {len(instance_files)} instances in {data_path}.")
    print(f"Testing formulations: {', '.join(formulations_to_run)}")
    print(f"Results will be saved to: {output_csv_path}")
    print(f"Using parameters: Threads={THREADS}, Timelimit={TIMELIMIT}s, MemoryLimit={MEMORYLIMIT}GB")

    all_results = [] # List to store results dictionaries from successful runs

    # --- Main Benchmarking Loop ---
    for instance_path in instance_files:
        instance_name = instance_path.stem # e.g., "g01"
        print(f"\nProcessing instance: {instance_path.name}")
        try:
            # Read graph to determine |V| for calculating k
            graph = read_instance(str(instance_path))
            num_nodes = graph.number_of_nodes()
            k_values_for_instance = calculate_k_values(num_nodes)

            if not k_values_for_instance:
                 print(f"  Skipping instance {instance_name} (could not determine valid k values, |V|={num_nodes}).")
                 continue

            print(f"  |V| = {num_nodes}, testing k values: {sorted(list(k_values_for_instance))}")

            # Loop through calculated k values
            for k in sorted(list(k_values_for_instance)):
                print(f" Testing k = {k}")
                # Loop through specified formulations
                for formulation in formulations_to_run:
                    print(f"  Testing formulation = {formulation}")

                    # Run the single experiment via subprocess
                    result_data = run_single_experiment(instance_path, k, formulation, temp_result_path)

                    # If the run was successful and returned data, store it
                    if result_data:
                        # Ensure the instance name in results is just the stem
                        result_data['instance'] = instance_name
                        all_results.append(result_data)
                    else:
                        # Log skipped run if run_single_experiment returned None
                        print(f"  Skipping results storage for failed run: {instance_name} k={k} form={formulation}")

        except FileNotFoundError:
             print(f"  ERROR: Instance file not found during read: {instance_path}. Skipping.")
        except Exception as e:
            # Catch other errors during instance processing (e.g., reading graph)
            print(f"  ERROR: Failed to process instance {instance_path.name}: {e}")
            # Decide whether to continue with the next instance or stop
            continue

    # --- Write Consolidated Results to CSV ---
    if not all_results:
        print("\nNo successful results were collected. CSV file will not be created.")
        return

    print(f"\nWriting {len(all_results)} results to {output_csv_path}...")

    
    headers = [
        "instance",             # Instance name stem (e.g., g01)
        "k",                    # Value of k used
        "formulation",          # Formulation identifier (seq, scf, etc.)
        "status",               # Gurobi status code (e.g., 2=Optimal, 9=TimeLimit)
        "objective_value",      # Best objective value found
        "best_bound",           # Best objective bound (for MIPs)
        "gap",                  # MIPGap reported by Gurobi
        "runtime",              # Runtime reported by Gurobi
        "n_nodes",              # Branch-and-bound nodes explored
        "n_lazy_constraints"    # Number of added constraints (for CEC/DCC, we should count this in kmst.py)
        # Add any other desired fields from results if needed
    ]

    try:
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Use DictWriter for easy mapping from results dictionary to CSV columns
            # extrasaction='ignore' prevents errors if the JSON has extra unexpected fields
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
            writer.writeheader() # Write the header row
            writer.writerows(all_results) # Write all collected results
        print("Benchmarking complete. Results saved.")
    except IOError as e:
        print(f"Error: Could not write results to CSV file {output_csv_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CSV writing: {e}")


if __name__ == "__main__":
    main()