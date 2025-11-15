# Format for CSV 1 - Annotated Outputs:
# R_peak_index,Analog Value,Digital Value,Instantaneous_BPM

# Format for CSV 2 - Batch Processed Outputs:
# Detected R_peak_index,Digital Value,Instantaneous_BPM

# Format for CSV 3 - Streamed Data Outputs:
# Detected R_peak_index,Digital Value,Instantaneous_BPM

# Test 1: Visually graph the digital data (ECG_Digital Dataset.csv (first column) and heartrate_csv_new.csv (second column))
# Test 2: Graph and compare r-peak index v bpm for each of the datasets

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


# UNUSED RIGHT NOW
def compare_raw_data():
    # --- Load your two CSVs ---
    expected_digital_data_csv = (
        "ecg_outputs_rpeaks_bpm/p00000_s00_ECG Digital Dataset.csv"
    )
    streamed_digital_data_csv = "heartrate_csv_new.csv"

    df1 = pd.read_csv(expected_digital_data_csv)
    df2 = pd.read_csv(streamed_digital_data_csv)

    # --- Extract desired columns ---
    # first column of CSV1  → assume it's unnamed or known as 'Column1'
    col1 = df1.iloc[:, 0]  # first column
    col2 = df2.iloc[:, 1]  # second column

    # Ensure they're same length (30 seconds of data)
    min_len = min(len(col1), len(col2))
    col1 = col1[:min_len]
    col2 = col2[:min_len]

    # ---  Exact equality check ---
    equal_mask = col1.equals(col2)
    print("Are the columns exactly equal?", equal_mask)

    # --- 2️Element-wise comparison ---
    mismatch_indices = np.where(col1 != col2)[0]
    if len(mismatch_indices) > 0:
        print(
            f"{len(mismatch_indices)} mismatches found at indices: {mismatch_indices[:10]}"
        )
    else:
        print("✅ All values are exactly equal")

    # --- 3️⃣ Within tolerance (for floats / ADC noise) ---
    tolerance = 1e-3
    within_tolerance = np.allclose(col1, col2, atol=tolerance)
    print(f"Within ±{tolerance} tolerance?", within_tolerance)

    # --- Optional: generate x-axis if both have same length ---
    x = range(len(col1))

    # --- Plot both on same figure ---
    plt.figure(figsize=(10, 5))
    plt.plot(x, col1, label="Expected Data (Digital, calculated in SW)")
    plt.plot(x, col2, label="Streamed Data (Digital, from gateway MCU)")

    plt.title("Comparison of SW-Calculated vs Streamed Digital Data")
    plt.xlabel("Sample Index")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    print()


def plot_data_and_peaks(window_start=0, window_end=500):
    # === Load your datasets ===
    annotated = pd.read_csv("ecg_outputs_rpeaks_bpm/p00000_s00_annotated_outputs.csv")
    batch = pd.read_csv("ecg_outputs_rpeaks_bpm/p00000_s00_batch_processed_outputs.csv")
    streamed = pd.read_csv(
        "ecg_outputs_rpeaks_bpm/p00000_s00_streamed_data_outputs.csv"
    )

    # === Load ECG digital dataset (from annotated CSV or from your generator) ===
    streamed_digital_data_csv = (
        "ecg_outputs_rpeaks_bpm/p00000_s00_ECG Digital Dataset.csv"
    )
    ecg_digital = pd.read_csv(streamed_digital_data_csv)

    # === Create plot ===
    plt.figure(figsize=(14, 6))
    plt.plot(ecg_digital, label="ECG Digital Signal", color="blue", linewidth=1)

    # --- Plot each dataset’s detected peaks ---
    plt.scatter(
        annotated["R_peak_index"],
        annotated["Digital Value"],
        color="green",
        s=60,
        label="Annotated Peaks",
    )

    plt.scatter(
        batch["Detected R_peak_index"],
        batch["Digital Value"],
        color="red",
        s=60,
        label="Batch-Detected Peaks",
    )

    plt.scatter(
        streamed["Detected R_peak_index"],
        streamed["Digital Value"],
        color="orange",
        s=60,
        label="Streamed-Detected Peaks",
    )

    # === Styling ===
    plt.xlabel("Sample Number")
    plt.ylabel("ADC Value")
    plt.title("Comparison of R-Peak Detection (Annotated vs Batch vs Streamed)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_bpms():
    plt.figure(figsize=(12, 6))
    annotated = pd.read_csv("ecg_outputs_rpeaks_bpm/p00000_s00_annotated_outputs.csv")
    batch = pd.read_csv("ecg_outputs_rpeaks_bpm/p00000_s00_batch_processed_outputs.csv")
    streamed = pd.read_csv(
        "ecg_outputs_rpeaks_bpm/p00000_s00_streamed_data_outputs.csv"
    )
    # Plot BPMs for all three datasets
    plt.plot(
        annotated["R_peak_index"],
        annotated["Instantaneous_BPM"],
        color="green",
        marker="o",
        label="Annotated BPM",
    )

    plt.plot(
        batch["Detected R_peak_index"],
        batch["Instantaneous_BPM"],
        color="red",
        marker="x",
        label="Batch Processed BPM",
    )

    plt.plot(
        streamed["Detected R_peak_index"],
        streamed["Instantaneous_BPM"],
        color="orange",
        marker="^",
        label="Streamed BPM",
    )

    # === Styling ===
    plt.xlabel("R-Peak Index (Sample Number)")
    plt.ylabel("Instantaneous BPM")
    plt.title("Instantaneous BPM Comparison (Annotated vs Batch vs Streamed)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_all(csv_log_folder_path):
    fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=False)

    annotated_path = os.path.join(csv_log_folder_path, "annotated_outputs.csv")
    batch_path = os.path.join(csv_log_folder_path, "batch_processed_outputs.csv")
    streamed_path = os.path.join(csv_log_folder_path, "streamed_data_outputs.csv")

    annotated = pd.read_csv(annotated_path)
    batch = pd.read_csv(batch_path)
    streamed = pd.read_csv(streamed_path)

    # === Load ECG digital dataset (from annotated CSV or from your generator) ===
    digital_dataset_path = os.path.join(csv_log_folder_path, "ECG Digital Dataset.csv")

    ecg_digital = pd.read_csv(digital_dataset_path)
    # --- Top: ECG + R-peaks ---
    axs[0].plot(ecg_digital, color="blue", label="ECG Signal")
    axs[0].scatter(
        annotated["R_peak_index"],
        annotated["Digital Value"],
        color="green",
        s=50,
        label="Annotated",
    )
    axs[0].scatter(
        batch["Detected R_peak_index"],
        batch["Digital Value"],
        color="red",
        s=50,
        label="Batch",
    )
    axs[0].scatter(
        streamed["Detected R_peak_index"],
        streamed["Digital Value"],
        color="orange",
        s=50,
        label="Streamed",
    )
    axs[0].set_ylabel("ADC Value")
    axs[0].set_title("R-Peak Detection Comparison")
    axs[0].legend()
    axs[0].grid(True)

    # --- Bottom: BPM vs R-peak index ---
    axs[1].plot(
        annotated["R_peak_index"],
        annotated["Instantaneous_BPM"],
        color="green",
        marker="o",
        label="Annotated",
    )
    axs[1].plot(
        batch["Detected R_peak_index"],
        batch["Instantaneous_BPM"],
        color="red",
        marker="x",
        label="Batch",
    )
    axs[1].plot(
        streamed["Detected R_peak_index"],
        streamed["Instantaneous_BPM"],
        color="orange",
        marker="^",
        label="Streamed",
    )
    axs[1].set_xlabel("R-Peak Index (Sample Number)")
    axs[1].set_ylabel("Instantaneous BPM")
    axs[1].set_title("BPM Comparison")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    plt.show()


def main(csv_logs_folder_path):
    # plot_data_and_peaks(0, 7500)
    # plot_bpms()
    plot_all(csv_logs_folder_path)


if __name__ == "__main__":
    # main(csv_logs_folder_path=None)
    main("/Users/anuyakamath/Desktop/ecg_project/data_logs/p00000_s00")
