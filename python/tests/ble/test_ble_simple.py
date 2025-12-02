"""
BLE SIMPLE Mode Test for ESP32 ECG Monitor

This script tests SIMPLE mode:
1. Establishes connection with ESP32
2. Sends START_SIMPLE command
3. Prints received text messages to terminal
4. Waits to receive ~15 packets over 30 seconds (1 message every 2 seconds)
5. Sends STOP_SIMPLE command
6. Reports packet count and inspects contents

Requirements:
    pip install bleak

Usage:
    python3 python/tests/ble/test_ble_simple.py
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

# Test configuration
TEST_DURATION_SEC = 30  # How long to collect messages
EXPECTED_MESSAGE_INTERVAL = 2  # ESP32 sends message every 2 seconds
EXPECTED_MESSAGE_COUNT = TEST_DURATION_SEC // EXPECTED_MESSAGE_INTERVAL  # ~15 messages


async def find_and_connect(skip_scan=False, device_address=None):
    """
    Find and connect to ESP32.

    Args:
        skip_scan: If True and device_address provided, skip scanning
        device_address: MAC address of ESP32 (optional, for faster connection)

    Returns:
        BleakClient: Connected client, or None if failed
    """
    if skip_scan and device_address:
        print(f"Connecting directly to {device_address}...")
        try:
            client = BleakClient(device_address)
            await client.connect()
            if client.is_connected:
                print(f"Connected to {device_address}")
                return client
        except Exception as e:
            print(f"Direct connection failed: {e}")
            print("Falling back to scan...")

    # Scan for device
    print(f"Scanning for '{TARGET_DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(TARGET_DEVICE_NAME, timeout=5.0)

    if device is None:
        print(f"ERROR: '{TARGET_DEVICE_NAME}' NOT FOUND")
        print("Troubleshooting:")
        print("  1. Make sure ESP32 is powered on")
        print("  2. Verify gateway_ble.ino is uploaded")
        print("  3. Check Serial Monitor shows 'BLE advertising started'")
        print("  4. Try restarting the ESP32")
        return None

    print(f"Found '{TARGET_DEVICE_NAME}' at {device.address}")

    # Connect
    client = BleakClient(device.address)
    await client.connect()

    if client.is_connected:
        print(f"Connected successfully")
        return client
    else:
        print(f"Connection failed")
        return None


async def test_simple_mode(skip_scan=False, device_address=None):
    """
    Test SIMPLE mode: Text messages every 2 seconds

    Args:
        skip_scan: Skip scanning if device_address is known
        device_address: MAC address for direct connection
    """

    print("=" * 70)
    print("SIMPLE MODE TEST")
    print("=" * 70)
    print(f"Test Configuration:")
    print(f"  Duration: {TEST_DURATION_SEC} seconds")
    print(
        f"  Expected messages: ~{EXPECTED_MESSAGE_COUNT} (1 every {EXPECTED_MESSAGE_INTERVAL}s)"
    )

    # Storage for received messages
    received_messages = []
    message_count = 0

    # Notification handler - called when ESP32 sends data
    def notification_handler(sender, data):
        """Called when BLE notification received from ESP32"""
        nonlocal message_count

        try:
            # Decode text message
            message = data.decode("utf-8").strip()
            message_count += 1

            # Print to terminal
            print(f"[{message_count:3d}] Update: {message}")

            # Store for later inspection
            received_messages.append(message)

        except Exception as e:
            print(f"Error decoding message: {e}")
            print(f"   Raw data: {data.hex()}")

    # Step 1: Connect to ESP32
    print("[1/5] Connecting to ESP32...")
    client = await find_and_connect(skip_scan=skip_scan, device_address=device_address)

    if client is None:
        return

    try:
        # Step 2: Subscribe to notifications
        print(f"\n[2/5] Subscribing to notifications on Data characteristic...")
        await client.start_notify(
            ECG_DATA_CHARACTERISTIC_UUID, notification_handler
        )  # start_notify(char_uuid, callback) is from Bleak API
        print("Subscribed to notifications")

        # Step 3: Send START_SIMPLE command
        print(f"\n[3/5] Sending START_SIMPLE command...")
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"START_SIMPLE")
        print("START_SIMPLE command sent")

        # Step 4: Collect messages for specified duration
        print(f"\n[4/5] Collecting messages for {TEST_DURATION_SEC} seconds...")
        print("-" * 70)

        await asyncio.sleep(TEST_DURATION_SEC)

        print("-" * 70)

        # Step 5: Send STOP_SIMPLE command
        print(f"\n[5/5] Sending STOP_SIMPLE command...")
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"STOP_SIMPLE")
        print("STOP_SIMPLE command sent")

        # Unsubscribe from notifications
        await client.stop_notify(ECG_DATA_CHARACTERISTIC_UUID)

        # Display summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total messages received: {message_count}")
        print(f"Expected messages: ~{EXPECTED_MESSAGE_COUNT}")

        if message_count >= EXPECTED_MESSAGE_COUNT - 2:  # Allow 2 message tolerance
            print("Message count is within expected range")
        else:
            print(f"ERROR: Received fewer messages than expected")

        # Inspect message contents
        print(f"\nMessage Contents Inspection:")
        print("-" * 70)

        if len(received_messages) > 0:
            print(f"First message: '{received_messages[0]}'")
            if len(received_messages) > 1:
                print(f"Second message: '{received_messages[1]}'")
            if len(received_messages) > 2:
                print(f"Third message: '{received_messages[2]}'")
            print(f"...")
            if len(received_messages) > 3:
                print(f"Last message: '{received_messages[-1]}'")

            # Verify message format (should be "Message N: Received")
            print(f"Message Format Validation:")
            format_errors = 0
            for i, msg in enumerate(received_messages, 1):
                expected_format = f"Message {i}: Received"
                if msg != expected_format:
                    print(f"    Message {i} format mismatch:")
                    print(f"     Expected: '{expected_format}'")
                    print(f"     Got:      '{msg}'")
                    format_errors += 1

            if format_errors == 0:
                print("All messages match expected format")
            else:
                print(f"ERROR: {format_errors} message(s) had format issues")
        else:
            print("ERROR: No messages received.")

        print("=" * 70)
        print("SIMPLE MODE TEST COMPLETE")

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Disconnect
        if client.is_connected:
            await client.disconnect()
            print("Disconnected from ESP32")


if __name__ == "__main__":
    print("BLE SIMPLE Mode Test for ESP32 ECG Monitor")
    print("Make sure your ESP32 is powered on and running gateway_ble.ino\n")

    try:
        # Run the test
        # To use direct connection (faster), provide device_address:
        # asyncio.run(test_simple_mode(skip_scan=True, device_address="XX:XX:XX:XX:XX:XX"))

        asyncio.run(test_simple_mode())

    except KeyboardInterrupt:
        print("Test interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
