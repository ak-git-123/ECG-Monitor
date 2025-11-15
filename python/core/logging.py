# classes included: CSV_Logger
# pulled from Desktop/Heart Rate Project/heartrate_project_v10.py
# note: used for logging raw data CSV and BPM, R-peak CSV

import queue
import csv
import threading
import json
import time
import datetime


class CSVLogger:
    def __init__(self, file_name, stop_flag, write_interval=1.0):
        self.file_name = file_name
        self.csv_queue = queue.Queue()
        self.stop_flag = stop_flag
        self.samples_written = 0
        self._thread = None
        self.write_interval = write_interval
        self.start_time = None
        self.stop_time = None
        self.metadata_file = "run_metadata.json"
        self.header = None

    def create_CSV(self, header=None):
        # self.start_time = datetime.datetime.now().isoformat()
        self.header = header
        with open(self.file_name, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.header)

        self._thread = threading.Thread(target=self.write_batch_to_csv, daemon=False)
        self._thread.start()

    def log(self, *args):
        """Add a sample to the queue (thread-safe)"""
        self.csv_queue.put(list(args))

    def write_batch_to_csv(self):
        batch = []
        while not self.stop_flag.is_set():
            time.sleep(self.write_interval)  # Wait 1 second between writes

            while not self.csv_queue.empty():
                try:
                    entry = self.csv_queue.get(block=False)
                    batch.append(entry)
                except queue.Empty:
                    break
            if len(batch) > 0:
                with open(self.file_name, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(batch)  # Write all rows at once

                self.samples_written += len(batch)
                print(
                    f"📝 Wrote {len(batch)} samples to CSV (total: {self.samples_written})"
                )
                batch.clear()

        print("Streaming stopped, writing remaining data...")
        final_batch = []
        while not self.csv_queue.empty():
            try:
                item = self.csv_queue.get(block=False)
                final_batch.append(item)
            except queue.Empty:
                break

        if len(final_batch) > 0:
            with open(self.file_name, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(final_batch)
            self.samples_written += len(final_batch)
            print(f"📝 Final write: {len(final_batch)} samples")

        self.stop_time = datetime.datetime.now().isoformat()
        print(f"✅ CSV writer finished. Total samples written: {self.samples_written}")
        self.save_metadata()

    def save_metadata(self):
        """Write metadata about run timing and totals to JSON"""
        metadata = {
            "csv_file": self.file_name,
            "start_time": self.start_time,
            "stop_time": self.stop_time,
            "samples_written": self.samples_written,
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)
        print(f"📄 Saved metadata to {self.metadata_file}")
