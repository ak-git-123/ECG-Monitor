"""
BLE STREAM Mode Test for ESP32 ECG Monitor

This script tests STREAM mode:
1. Establishes connection with ESP32
2. Sends START_STREAM command
3. Receives binary packets over BLE
4. Uses PacketParser to parse packets into:
   - packet_id
   - timestamp
   - 10 samples
5. Sends STOP_STREAM command
6. Reports packet count

Requirements:
    pip install bleak

Usage:
    python3 python/tests/ble/test_ble_streaming.py

Notes about this test script:
* This script is meant to stream data from the ESP32 to the host device for 10 seconds. It is primarily
meant to test integrity of data transmission at the specified streaming rate and with the specified packet format. *

Sample values for data packets are 12-bit, so values range from 0-4095. This file runs a 10-second test,
so streamed sample values range from 0-2500. If the code is run for more than ~16.4 sec (which would stream 4095 samples),
the numbers will wrap around back to 0 (and continue to do so every ~16.4 sec). The code does not account for this wrap-around,
and the validation tests for packet IDs (duplicates, missing) will fail at longer run times. This logic will be updated
during further testing to account for longer streaming times.
"""

import asyncio
import struct
from bleak import BleakScanner, BleakClient

# Import UUIDs from config
from ble_config import (
    TARGET_DEVICE_NAME,
    ECG_SERVICE_UUID,
    ECG_DATA_CHARACTERISTIC_UUID,
    ECG_COMMAND_CHARACTERISTIC_UUID,
)

# Test configuration
PACKET_SIZE = 28
TEST_DURATION_SEC = 10  # How long to collect packets
EXPECTED_PACKET_INTERVAL_MS = 40  # ESP32 sends packet every 40ms
EXPECTED_PACKET_COUNT = (
    TEST_DURATION_SEC * 1000 // EXPECTED_PACKET_INTERVAL_MS
)  # ~250 packets


class Packet:
    """Represents a single parsed packet with its attributes."""

    def __init__(self, packet_id, timestamp, samples, sample_times):
        self.packet_id = packet_id
        self.timestamp = timestamp
        self.samples = samples
        self.sample_times = sample_times

    def __repr__(self):
        return f"Packet(ID={self.packet_id}, timestamp={self.timestamp}, samples={len(self.samples)})"


class PacketParser:
    def __init__(self, packet_size):
        self.packet_size = packet_size
        self.buffer = b""
        self.HEADER_1 = 0xAA
        self.HEADER_2 = 0x55
        self.END_MARKER = 0xFF
        self.NUM_SAMPLES = 10
        self.SAMPLE_INTERVAL_MS = 4  # matches firmware assumption

    def update_buffer(self, data: bytes):
        """Append new raw bytes to internal buffer."""
        self.buffer += data

    def has_complete_packet(self) -> bool:
        """Check if buffer has at least one full packet worth of data."""
        return len(self.buffer) >= self.packet_size

    def get_packet(self):
        """Try to extract and parse one packet from buffer. Returns Packet or None."""
        # Not enough bytes yet
        if len(self.buffer) < self.packet_size:
            return None

        # Check header
        if self.buffer[0] != self.HEADER_1 or self.buffer[1] != self.HEADER_2:
            # Misaligned header; drop one byte and retry later
            self.buffer = self.buffer[1:]
            return None

        # Extract 1 packet
        packet_bytes = self.buffer[: self.packet_size]
        self.buffer = self.buffer[self.packet_size :]

        # Check end marker
        if packet_bytes[-1] != self.END_MARKER:
            # Resync by dropping until next potential header
            while len(self.buffer) >= 2 and not (
                self.buffer[0] == self.HEADER_1 and self.buffer[1] == self.HEADER_2
            ):
                self.buffer = self.buffer[1:]
            return None

        # Parse fields
        packet_id = packet_bytes[2]
        timestamp = struct.unpack("<I", packet_bytes[3:7])[0]
        samples = struct.unpack("<" + "H" * self.NUM_SAMPLES, packet_bytes[7:27])

        # Compute sample times (approximate)
        sample_times = [
            (timestamp + i * self.SAMPLE_INTERVAL_MS) / 1000.0
            for i in range(self.NUM_SAMPLES)
        ]

        return Packet(packet_id, timestamp, samples, sample_times)


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

    # Scan for device, timeout after 5 seconds
    print(f"Scanning for '{TARGET_DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(TARGET_DEVICE_NAME, timeout=5.0)

    # if device not found, return after 5 seconds
    if device is None:
        print(f"ERROR: '{TARGET_DEVICE_NAME}' not found")
        return None

    print(f"Found '{TARGET_DEVICE_NAME}' at {device.address}")

    # Connect
    client = BleakClient(device.address)
    await client.connect()

    if client.is_connected:
        print("Connected successfully")
        return client
    else:
        print("Connection failed")
        return None


async def test_stream_mode(skip_scan=False, device_address=None):
    """
    Test STREAM mode: binary packets every 40ms.

    Args:
        skip_scan: Skip scanning if device_address is known
        device_address: MAC address for direct connection
    """

    print("=" * 70)
    print("STREAM MODE TEST")
    print("=" * 70)
    print(f"\nTest Configuration:")
    print(f"  Duration: {TEST_DURATION_SEC} seconds")
    print(
        f"  Expected packets: ~{EXPECTED_PACKET_COUNT} (1 every {EXPECTED_PACKET_INTERVAL_MS}ms)"
    )
    print()

    parser = PacketParser(packet_size=PACKET_SIZE)
    received_packets = []

    # Notification handler - called when ESP32 sends data
    def notification_handler(sender, data):
        """Called when BLE notification received from ESP32."""
        # data is raw bytes from ESP32 (28-byte packet in this test)
        parser.update_buffer(data)

        # Try to pull out as many complete packets as possible
        while parser.has_complete_packet():
            pkt = parser.get_packet()
            if pkt is None:
                break
            received_packets.append(pkt)
            # Minimal debug print; you can comment this out later if desired
            print(
                f"Packet {len(received_packets)}: "
                f"ID={pkt.packet_id}, ts={pkt.timestamp}, "
                f"samples={pkt.samples[:]}"
            )

    # Step 1: Connect to ESP32
    print("[1/3] Connecting to ESP32...")
    client = await find_and_connect(skip_scan=skip_scan, device_address=device_address)

    if client is None:
        return

    try:
        # Step 2: Subscribe to notifications and start stream
        print(f"\n[2/3] Subscribing to notifications and sending START_STREAM...")
        await client.start_notify(ECG_DATA_CHARACTERISTIC_UUID, notification_handler)
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"START_STREAM")

        # Step 3: Collect packets for specified duration
        print(f"\n[3/3] Collecting packets for {TEST_DURATION_SEC} seconds...")
        print("-" * 70)

        await asyncio.sleep(TEST_DURATION_SEC)

        print("-" * 70)
        print("Stopping stream...")

        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"STOP_STREAM")
        await client.stop_notify(ECG_DATA_CHARACTERISTIC_UUID)

        # === VALIDATION ANALYSIS ===
        print("\n" + "=" * 70)
        print("VALIDATION ANALYSIS")
        print("=" * 70)

        # 1. Check packet_id sequence
        packet_ids = [p.packet_id for p in received_packets]  # all collected packet IDs
        expected_ids = list(
            range(1, len(received_packets) + 1)
        )  # number list of expected packet IDs
        missing_ids = set(expected_ids) - set(packet_ids)
        duplicate_ids = [p_id for p_id in set(packet_ids) if packet_ids.count(p_id) > 1]

        if missing_ids:
            print(f"ERROR: Missing packet IDs: {sorted(missing_ids)}")
        else:
            print("No missing packet IDs")

        if duplicate_ids:
            print(f"ERROR: Duplicate packet IDs: {duplicate_ids}")
        else:
            print("No duplicate packet IDs")

        # 2. Check sample counter sequence (should be 1,2,3...N)
        all_samples = []
        for p in received_packets:
            all_samples.extend(p.samples)

        if len(all_samples) > 1:
            sample_gaps = []
            for i in range(len(all_samples) - 1):
                expected_next = all_samples[i] + 1
                actual_next = all_samples[i + 1]
                if actual_next != expected_next:
                    sample_gaps.append((i, all_samples[i], actual_next))

            if sample_gaps:
                for gap in sample_gaps:
                    print(
                        f"ERROR: Sample counter gap detected at index {gap[0]}. Counters: {gap[1]} and {gap[2]}."
                    )

            else:
                print(f"Sample counter is consecutive (1 → {all_samples[-1]})")

        # 3. Timestamp analysis
        if len(received_packets) > 1:
            timestamp_diffs = [
                received_packets[i + 1].timestamp - received_packets[i].timestamp
                for i in range(len(received_packets) - 1)
            ]

        timestamps_in_range = True
        for i in range(len(timestamp_diffs)):

            if timestamp_diffs[i] != EXPECTED_PACKET_INTERVAL_MS:
                timestamps_in_range = False
                print(
                    f"Timestamp inconsistency found at sample {i}: calculated difference is {timestamp_diffs[i]}."
                )
        if timestamps_in_range is False:
            print("ERROR: Out-of-range time intervals detected.")
        else:
            print("Timing is within expected range")

        # 4. Data rate
        total_samples = len(all_samples)
        actual_sample_rate = total_samples / TEST_DURATION_SEC
        expected_sample_rate = (1000 / EXPECTED_PACKET_INTERVAL_MS) * 10  # 250 Hz
        print(f"\nSample rate:")
        print(f"  Expected: {expected_sample_rate:.1f} Hz")
        print(f"  Actual: {actual_sample_rate:.1f} Hz")
        print(f"  Difference: {actual_sample_rate - expected_sample_rate:.1f} Hz")

        # 5. Loss percentage
        expected_total_packets = EXPECTED_PACKET_COUNT
        received_total_packets = len(received_packets)
        loss_pct = (
            (expected_total_packets - received_total_packets) / expected_total_packets
        ) * 100
        print(f"\nPacket loss:")
        print(f"  Expected: {expected_total_packets}")
        print(f"  Received: {received_total_packets}")
        print(f"  Loss: {loss_pct:.1f}%")

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total packets parsed: {len(received_packets)}")
        print(f"Expected packets:    ~{EXPECTED_PACKET_COUNT}")

        if received_packets:
            example = received_packets[0]
            print("\nExample packet:")
            print(f"  {example}")
            print(f"  Samples: {example.samples}")

        print("=" * 70)
        print("\nSTREAM MODE TEST COMPLETE")

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Disconnect
        if client.is_connected:
            await client.disconnect()
            print("\nDisconnected from ESP32")


if __name__ == "__main__":
    print("\nBLE STREAM Mode Test for ESP32 ECG Monitor")
    print("Make sure your ESP32 is powered on and running the BLE test firmware.\n")

    try:
        asyncio.run(test_stream_mode())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
