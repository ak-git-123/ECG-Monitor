import struct


# classes included: Packet, Packet_Parser
# pulled from Desktop/Heart Rate Project/heartrate_project_v10.py
class Packet:
    """Represents a single parsed packet with its attributes"""

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
        self.SAMPLE_INTERVAL_MS = 4
        self.packet_count = 0

    def update_buffer(self, data):
        self.buffer += data

    def has_complete_packet(self):
        return len(self.buffer) >= self.packet_size

    def get_packet(self):
        # Not enough bytes yet
        if len(self.buffer) < self.packet_size:
            return None  # What does this do

        # Check header
        if self.buffer[0] != self.HEADER_1 or self.buffer[1] != self.HEADER_2:
            self.buffer = self.buffer[1:]  # Shift by 1 and retry
            return None

        # Extract packet
        packet = self.buffer[: self.packet_size]
        self.buffer = self.buffer[self.packet_size :]

        # Check footer
        if packet[-1] != self.END_MARKER:
            print("⚠️ End marker mismatch, resyncing...")
            # Resync: find next header
            while len(self.buffer) >= 2 and not (
                self.buffer[0] == self.HEADER_1 and self.buffer[1] == self.HEADER_2
            ):
                self.buffer = self.buffer[1:]
            return None

        # Parse all fields at once
        packet_id = packet[2]
        timestamp = struct.unpack("<I", packet[3:7])[0]
        samples = struct.unpack(
            "<" + "H" * 10, packet[7:27]
        )  # changed B (unsigned char, 1 byte) to H (unsigned short, 2 bytes) when going from 8-bit to 12-bit resolution

        # Calculate sample times
        sample_times = [(timestamp + i * 4) / 1000.0 for i in range(10)]
        sample_times = [round(t, 4) for t in sample_times]

        # Return Packet object
        return Packet(packet_id, timestamp, samples, sample_times)
