# 
import serial
import time
from src.heartrate_generator import create_dataset
import matplotlib.pyplot as plt
import numpy as np
import json
ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
time.sleep(2)  # Wait for connection to stabilize

with open("heartrate_config.json") as f:
    config = json.load(f)

bpm = config["bpm"]
fs = config["sampling_hz"]
num_beats = config["num_beats"]
heartbeat_type = config["heartbeat_type"]
durations_json = config["durations"]

# GENERATE DATASET
ecg_digital = create_dataset(durations_json, bpm, fs, num_beats)

# Send a command to start streaming
ser.write(b'START\n')
digital_firmware_values = []
# Read and print 40 packets
for _ in range(42):
    line = ser.readline().decode().strip()
    if line:
        print("Received:", line)
        if line.startswith("Packet"):
            parts = line.split()
            parts = parts[2:]
            #print(parts)
            digital_firmware_values.extend([int(float(x)) for x in parts])
            #print(voltage_values)
        
digital_firmware_values = [int(x) for x in digital_firmware_values]
print(digital_firmware_values)
print(ecg_digital == digital_firmware_values)
# Stop streaming
ser.write(b'STOP\n')

ser.close()

tolerance = 0.06 # is this too high? change later if needed !!
digital_firmware_values = np.array(digital_firmware_values)
digital_ecg_expected = np.array(ecg_digital)



plt.plot(digital_ecg_expected, label="Python ECG")
plt.plot(digital_firmware_values, label="Arduino ECG")
plt.legend()
plt.show()

diff = np.abs(digital_firmware_values - digital_ecg_expected)
print(diff)
all_within_tolerance = np.all(diff < tolerance)
print(all_within_tolerance)