"""
BLE Configuration for ESP32 ECG Monitor
Shared UUIDs and constants across all test scripts and firmware

This file serves as the single source of truth for BLE configuration.
Update UUIDs here and they will propagate to all test scripts.
"""

# Device name
TARGET_DEVICE_NAME = "ECG Monitor ESP32"

# Service UUID
ECG_SERVICE_UUID = "fa75e591-ba7c-4779-938d-4c5bcc3a431f"

# Characteristic UUIDs
ECG_DATA_CHARACTERISTIC_UUID = "3f433ab7-4887-4b25-a57a-793cd0fdb3c2"  # NOTIFY
ECG_COMMAND_CHARACTERISTIC_UUID = "221f81c7-09ed-4af7-be04-e08033dd979f"  # WRITE
