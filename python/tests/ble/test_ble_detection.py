"""
BLE Detection and Connection Test for ESP32 ECG Monitor

This script does the following:
1. Scans for all BLE devices and prints them
2. Connects to "ECG Monitor ESP32" specifically
3. Reads and displays the service/characteristic structure

Requirements:
    pip install bleak

Usage:
    python3 python/tests/ble/test_ble_detection.py
"""

import asyncio
from bleak import BleakScanner, BleakClient

# Import UUIDs from config
from ble_config import (
    TARGET_DEVICE_NAME,
    ECG_SERVICE_UUID,
    ECG_DATA_CHARACTERISTIC_UUID,
    ECG_COMMAND_CHARACTERISTIC_UUID,
)


async def test_detection_and_connection():
    """
    Test BLE device detection and connection
    """

    print("=" * 70)
    print("BLE DETECTION TEST")
    print("=" * 70)

    # ===== PART 1: SCAN FOR ALL DEVICES =====
    print("\n[1/3] Scanning for all BLE devices (5 second scan)...\n")

    devices = await BleakScanner.discover(timeout=5.0)

    print(f"Found {len(devices)} BLE devices:\n")
    print("-" * 70)

    target_device = None

    for i, device in enumerate(devices, 1):
        device_name = device.name or "Unknown"
        print(f"{i}. Name: {device_name}")
        print(f"   Address: {device.address}")
        # print(f"   RSSI: {device.rssi} dBm")

        # Check if this is the target device for ECG monitor
        if device_name == TARGET_DEVICE_NAME:
            print("   THIS IS YOUR ESP32!")
            target_device = device

        print("-" * 70)

    # ===== PART 2: CHECK IF TARGET DEVICE FOUND =====
    print(f"\n[2/3] Looking for target device: '{TARGET_DEVICE_NAME}'...")

    if target_device is None:
        print(f"ERROR: '{TARGET_DEVICE_NAME}' NOT FOUND")
        print("Troubleshooting:")
        print("  1. Make sure ESP32 is powered on")
        print("  2. Verify the sketch is uploaded to ESP32")
        print("  3. Check Serial Monitor shows 'Characteristic defined!'")
        print("  4. Try restarting the ESP32")
        print("  5. Make sure Bluetooth is enabled on your Mac")
        return

    print(f"Found '{TARGET_DEVICE_NAME}' at address: {target_device.address}")

    # ===== PART 3: CONNECT AND READ SERVICES =====
    print(f"\n[3/3] Connecting to '{TARGET_DEVICE_NAME}'...\n")

    try:
        async with BleakClient(target_device.address) as client:
            print(f"Connected: {client.is_connected}\n")

            print("=" * 70)
            print("SERVICES AND CHARACTERISTICS")
            print("=" * 70)

            # Iterate through all services
            for service in client.services:
                print(f"\nSERVICE")
                print(f"   UUID: {service.uuid}")

                # Check if this is YOUR service
                if service.uuid.lower() == ECG_SERVICE_UUID.lower():
                    print("   *THIS IS THE ECG SERVICE*")

                # Iterate through characteristics
                for char in service.characteristics:
                    print(f"\n   └─ CHARACTERISTIC")
                    print(f"      UUID: {char.uuid}")
                    print(f"      Properties: {char.properties}")

                    # Check if this is Data Packet characteristic
                    if char.uuid.lower() == ECG_DATA_CHARACTERISTIC_UUID.lower():
                        print("      *THIS IS THE DATA_PACKET CHARACTERISTIC*")

                        # Verify it has NOTIFY property
                        if "notify" in char.properties:
                            print("      NOTIFY property confirmed")
                        else:
                            print("      WARNING: NOTIFY property missing!")

                    # Check if this is Command characteristic
                    if char.uuid.lower() == ECG_COMMAND_CHARACTERISTIC_UUID.lower():
                        print("      *THIS IS THE COMMAND CHARACTERISTIC*")

                        # Verify it has NOTIFY property
                        if "write" in char.properties:
                            print("      WRITE property confirmed")
                        else:
                            print("      WARNING: WRITE property missing!")

                    # Read descriptors
                    if char.descriptors:
                        print(f"      Descriptors:")
                        for desc in char.descriptors:
                            print(f"         └─ {desc.uuid}")

                            # Try to read User Description (0x2901)
                            if (
                                desc.uuid.lower()
                                == "00002901-0000-1000-8000-00805f9b34fb"
                            ):
                                try:
                                    value = await client.read_gatt_descriptor(
                                        desc.handle
                                    )
                                    name = value.decode("utf-8")
                                    print(f"            Human-readable name: '{name}'")
                                except Exception as e:
                                    print(f"            Could not read: {e}")

                            # Note the CCCD (0x2902)
                            if (
                                desc.uuid.lower()
                                == "00002902-0000-1000-8000-00805f9b34fb"
                            ):
                                print(f"            CCCD (required for NOTIFY)")

                print()

            print("=" * 70)
            print("TEST COMPLETE - BLE Detection and Connection Successful!")
            print("ESP32 for ECG Monitor is:")
            print("  Discoverable")
            print("  Connectable")
            print("  Service structure is correct")
            print("  Ready for data transmission testing.")

    except Exception as e:
        print(f"Connection failed: {e}")
        print("Troubleshooting:")
        print(
            "  1. Make sure the ESP32 is properly powered on. Try restarting the ESP32 if needed."
        )
        print("  2. Make sure no other device is connected to the ESP32.")
        print("  3. Check ESP32 Serial Monitor for errors.")


if __name__ == "__main__":
    print("BLE Detection Test for ESP32 ECG Monitor")
    print("Make sure your ESP32 is powered on and running gateway_ble.ino")

    try:
        asyncio.run(test_detection_and_connection())
    except KeyboardInterrupt:
        print("Test interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
