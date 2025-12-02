/*
 * ============================================================================
 * ESP32 BLE GATT SERVER - ECG RAW DATA STREAMING TEST
 * ============================================================================
 *
 * PURPOSE:
 * Test script for ESP32 that creates a BLE GATT server to stream ECG data
 * packets wirelessly. This replaces USB Serial communication with Bluetooth LE.
 *
 * SERVICE SPECIFICATION:
 * - Service Name: "ECG_Raw_Data"
 * - Service UUID: Custom (defined below)
 * - Purpose: Stream real-time ECG sensor data packets
 *
 * CHARACTERISTIC SPECIFICATION:
 * - Characteristic Name: "Data_Packet"
 * - Characteristic UUID: Custom (defined below)
 * - Properties: NOTIFY (one-way streaming from ESP32 to client)
 * - Data Format: 28 bytes (matches existing USB protocol)
 *
 * PACKET FORMAT (28 bytes total):
 * - Byte 0-1:   Header (0xAA, 0x55) - Sync pattern
 * - Byte 2:     Packet ID (0-255, wraps) - For packet loss detection
 * - Byte 3-6:   Timestamp (uint32_t, little-endian) - Milliseconds since boot
 * - Byte 7-26:  10 ADC samples (uint16_t each) - 12-bit values from AD8232
 * - Byte 27:    End marker (0xFF) - Integrity check
 *
 * ============================================================================
 * GATT SERVER INITIALIZATION STEPS
 * ============================================================================
 *
 * STEP 1: Initialize BLE Device
 * ------------------------------
 * What happens: Initialize the BLE stack and set the device name
 *
 * Function call: BLEDevice::init("device_name")
 *
 * Details:
 * - Device name will appear during BLE scanning (e.g., "ECG-Monitor-Test")
 * - This MUST be the first BLE call in your code
 * - Initializes the Bluedroid BLE stack on ESP32
 * - Once initialized, ESP32 is ready to act as BLE server/client
 *
 *
 * STEP 2: Create BLE Server
 * --------------------------
 * What happens: Create a server instance that will host your GATT services
 *
 * Function call: BLEDevice::createServer()
 *
 * Details:
 * - Returns a pointer to BLEServer object
 * - Server manages client connections and hosts services
 * - Can handle multiple client connections (though typically one at a time)
 * - Can attach callbacks for connection/disconnection events
 *
 *
 * STEP 3: Register Server Callbacks (Optional but Recommended)
 * -------------------------------------------------------------
 * What happens: Set up event handlers for when clients connect/disconnect
 *
 * Implementation:
 * - Create a class that inherits from BLEServerCallbacks
 * - Override onConnect() and onDisconnect() methods
 * - Call pServer->setCallbacks(new YourCallbackClass())
 *
 * Details:
 * - onConnect() is called when a client successfully connects
 * - onDisconnect() is called when client disconnects or connection drops
 * - Useful for: LED indicators, stopping data streaming, cleanup tasks
 * - Helps manage connection state and resource usage
 *
 *
 * STEP 4: Create GATT Service
 * ----------------------------
 * What happens: Create the "ECG_Raw_Data" service that contains characteristics
 *
 * Function call: pServer->createService(SERVICE_UUID)
 *
 * Details:
 * - Service UUID: Custom UUID string (e.g., "4fafc201-1fb5-459e-8fcc-c5c9c331914b")
 * - Service acts as a container/organizer for related characteristics
 * - Returns a pointer to BLEService object
 * - MUST be created BEFORE adding characteristics to it
 * - Service won't be visible to clients until started (Step 7)
 *
 *
 * STEP 5: Create GATT Characteristic
 * -----------------------------------
 * What happens: Create the "Data_Packet" characteristic within the service
 *
 * Function call: pService->createCharacteristic(CHARACTERISTIC_UUID, properties)
 *
 * Details:
 * - Characteristic UUID: Custom UUID (e.g., "beb5483e-36e1-4688-b7f5-ea07361b26a8")
 * - Properties: BLECharacteristic::PROPERTY_NOTIFY (for one-way streaming)
 * - This is where your 28-byte data packets will be sent
 * - Returns a pointer to BLECharacteristic object
 * - Can create multiple characteristics per service if needed
 *
 *
 * STEP 6: Add Descriptor to Characteristic (REQUIRED for NOTIFY)
 * ---------------------------------------------------------------
 * What happens: Add the Client Characteristic Configuration Descriptor (CCCD)
 *
 * Function call: pCharacteristic->addDescriptor(new BLE2902())
 *
 * Details:
 * - BLE2902 is the standard CCCD descriptor (UUID: 0x2902)
 * - REQUIRED for NOTIFY property to work properly
 * - Allows clients to enable/disable notifications
 * - Without this, notifications will not function
 * - Handles the enable/disable notification requests from client
 *
 *
 * STEP 7: Start the Service
 * --------------------------
 * What happens: Activate the service so it's available to connected clients
 *
 * Function call: pService->start()
 *
 * Details:
 * - MUST be called AFTER all characteristics are added
 * - Service is now part of the GATT table
 * - Clients can now discover and query this service after connection
 * - Cannot add more characteristics after service is started
 *
 *
 * STEP 8: Configure and Start Advertising
 * ----------------------------------------
 * What happens: Begin broadcasting BLE advertisements so clients can discover device
 *
 * Function calls:
 * - BLEDevice::getAdvertising()
 * - pAdvertising->addServiceUUID(SERVICE_UUID)
 * - pAdvertising->setScanResponse(true)
 * - BLEDevice::startAdvertising()
 *
 * Details:
 * - Advertising makes your device visible to BLE scanners
 * - addServiceUUID() includes service UUID in advertisement packet
 * - setScanResponse(true) improves discoverability on some devices
 * - After startAdvertising(), device appears in BLE scan results
 * - Device is now ready to accept connections
 *
 *
 * STEP 9: Send Notifications (In loop())
 * ---------------------------------------
 * What happens: Send data packets to connected clients during runtime
 *
 * Function calls:
 * - pCharacteristic->setValue(data, length)
 * - pCharacteristic->notify()
 *
 * Details:
 * - setValue() updates the characteristic value (your 28-byte packet)
 * - notify() sends the value to all subscribed clients
 * - Should only send when a client is connected and has enabled notifications
 * - For ECG: Send at 25 Hz rate (10 samples per packet, 250 Hz sampling)
 * - Each notification contains one complete 28-byte packet
 *
 * ============================================================================
 * REQUIRED LIBRARIES
 * ============================================================================
 *
 * #include <BLEDevice.h>   // Core BLE device functionality
 * #include <BLEServer.h>   // BLE server (GATT server) functionality
 * #include <BLEUtils.h>    // BLE utility functions
 * #include <BLE2902.h>     // BLE descriptor for NOTIFY/INDICATE
 *
 * These libraries are included with the ESP32 Arduino core.
 * No additional library installation needed.
 *
 * ============================================================================
 * TESTING INSTRUCTIONS
 * ============================================================================
 *
 * 1. Upload this sketch to ESP32
 *
 * 2. Open Serial Monitor (115200 baud) to see debug output
 *
 * 3. Use one of these methods to test:
 *
 *    Option A: nRF Connect Mobile App (Recommended for initial testing)
 *    - Install "nRF Connect" app on iOS/Android
 *    - Open app and scan for devices
 *    - Look for "ECG-Monitor-Test" (or your chosen device name)
 *    - Tap to connect
 *    - Explore services and characteristics
 *    - Enable notifications on Data_Packet characteristic
 *    - Observe incoming data packets (28 bytes each)
 *
 *    Option B: Python BLE Scanner (Step B of this project)
 *    - Run the companion Python script on macOS
 *    - Script will scan, connect, and receive data
 *    - Data will be parsed and displayed
 *
 * 4. Expected behavior:
 *    - ESP32 Serial Monitor shows "BLE device ready and advertising"
 *    - Device appears in BLE scan results
 *    - Connection is successful
 *    - Service UUID is visible
 *    - Data_Packet characteristic shows NOTIFY property
 *    - When notifications enabled, data packets stream at 25 Hz
 *
 * 5. Troubleshooting:
 *    - If device not found: Check ESP32 is powered and sketch uploaded
 *    - If can't connect: Restart ESP32 and try again
 *    - If no notifications: Ensure BLE2902 descriptor was added
 *    - If data looks wrong: Verify packet format matches 28-byte structure
 *
 * ============================================================================
 */


#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <BLE2901.h>

// =========================================
// Protocol constants
// =========================================
#define HEADER_1 0xAA
#define HEADER_2 0x55
#define END_MARKER 0xFF
#define PACKET_SAMPLES 10


BLEServer* pServer  = nullptr;
BLECharacteristic* pDataChar = nullptr;  // NOTIFY (both modes share this)
BLECharacteristic* pCommandChar = nullptr;  // WRITE for commands


// See the following for generating UUIDs:
// https://www.uuidgenerator.net/

#define ECG_SERVICE_UUID "fa75e591-ba7c-4779-938d-4c5bcc3a431f"
#define ECG_DATA_CHARACTERISTIC_UUID "3f433ab7-4887-4b25-a57a-793cd0fdb3c2" // NOTIFY
#define ECG_COMMAND_CHARACTERISTIC_UUID "221f81c7-09ed-4af7-be04-e08033dd979f" // WRITE


bool deviceConnected = false;

// Mode flags
bool simple_mode = false;
bool stream_mode = false;

// SIMPLE mode state
unsigned long last_simple_time = 0;
uint32_t simple_counter = 1;

// STREAM mode state
unsigned long last_stream_time = 0;
uint8_t packet_id = 1;
uint32_t stream_sample_counter = 1;  // global running sample index

// =========================================
// BLE Server callbacks (connect/disconnect)
// =========================================
class ECGServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("Client connected.");
  }

  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    simple_mode = false;
    stream_mode = false;
    Serial.println("Client disconnected.");
    BLEDevice::startAdvertising();  // allow reconnection
  }
};

// =========================================
// Command characteristic callbacks
// Commands: START_SIMPLE, STOP_SIMPLE, START_STREAM, STOP_STREAM
// =========================================
class CommandCallbacks : public BLECharacteristicCallbacks {
// onWrite, onNotify, onRead, onStatus

  void onWrite(BLECharacteristic* pCharacteristic) override {
    String rxValue = pCommandChar->getValue(); //get value that has been transmitted to ESP32 (Characteristic 2)
    if (rxValue.length() == 0) return;

    Serial.print("Command received over BLE: ");
    Serial.println(rxValue);

    if (rxValue == "START_SIMPLE") {
      // Enable simple mode, disable stream mode
      simple_mode = true;
      stream_mode = false;
      simple_counter = 1;
      last_simple_time = millis();
      Serial.println("Mode: SIMPLE ON, STREAM OFF");
    }
    else if (rxValue == "STOP_SIMPLE") {
      simple_mode = false;
      Serial.println("Mode: SIMPLE OFF");
    }
    else if (rxValue == "START_STREAM") {
      // Enable stream mode, disable simple mode
      stream_mode = true;
      simple_mode = false;
      packet_id = 1;
      stream_sample_counter = 1;
      last_stream_time = millis();
      Serial.println("Mode: STREAM ON, SIMPLE OFF");
    }
    else if (rxValue == "STOP_STREAM") {
      stream_mode = false;
      Serial.println("Mode: STREAM OFF");
    }
    // You can add more commands here later if needed
  }
};

// TESTER FUNCTIONS:

// =========================================
// Build binary 28-byte packet for STREAM mode
// Header(2) + ID(1) + timestamp(4) + 10 samples(20) + end(1) = 28
// =========================================
void buildBinaryPacket(uint8_t* packet_buf, size_t buf_size) {
  if (buf_size < 28) return;

  uint8_t index = 0;

  // Header
  packet_buf[index++] = HEADER_1;
  packet_buf[index++] = HEADER_2;

  // Packet ID
  packet_buf[index++] = packet_id;
  packet_id++;
  if (packet_id == 0) packet_id = 1;  // avoid 0 if you want

  // Timestamp (ms since boot, little-endian)
  uint32_t timestamp = millis();
  memcpy(&packet_buf[index], &timestamp, sizeof(timestamp));
  index += sizeof(timestamp);  // +4

  // 10 samples (2 bytes each) - here: consecutive integers
  for (uint8_t i = 0; i < PACKET_SAMPLES; i++) {
    uint16_t sample = (uint16_t)(stream_sample_counter++ & 0x0FFF);  // keep 12-bit-style if desired
    memcpy(&packet_buf[index], &sample, sizeof(uint16_t));
    index += sizeof(uint16_t);  // +2 each
  }

  // End marker
  packet_buf[index++] = END_MARKER;
}

// =========================================
// Build SIMPLE mode message: "Message N: Received\n"
// Returns length in bytes
// =========================================
int buildSimpleMessage(char* buf, size_t buf_size, uint32_t msg_index) {
  if (buf_size == 0) return 0;

  // Example: "Message 1: Received\n"
  // snprintf() function both a) writes to the buffer up to buffer_size - 1
  // and b) returns the number of characters that would have been written if the buffer s had been large enough, not counting the terminating null character 
  int len = snprintf(buf, buf_size, "Message %lu: Received\n", (unsigned long)msg_index);
  if (len < 0) return 0;
  if ((size_t)len >= buf_size) {
    // truncated; ensure null-termination
    buf[buf_size - 1] = '\0';
    return buf_size - 1;
  }
  return len;
}



void setup() {
    Serial.begin(115200);
    Serial.println("Starting BLE work!");

    // initialize the server/device "ECG Monitor ESP32"
    BLEDevice::init("ECG Monitor ESP32");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ECGServerCallbacks()); 


    // initialize the service of the server/device (ECG Monitor Service 1)
    BLEService *pService = pServer->createService(ECG_SERVICE_UUID);
    Serial.println("Service: ECG Monitor Service");
    Serial.print("  UUID: ");
    Serial.println(ECG_SERVICE_UUID);

   // -----------------------------------------
  // Data characteristic (NOTIFY) - shared for both modes
  // -----------------------------------------
  pDataChar = pService->createCharacteristic(
      ECG_DATA_CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_NOTIFY
  );

  BLE2901* pDataDesc = new BLE2901();
  pDataDesc->setValue("ECG Test Data");
  pDataDesc->setAccessPermissions(ESP_GATT_PERM_READ);
  pDataChar->addDescriptor(pDataDesc);

  // CCCD for NOTIFY
  pDataChar->addDescriptor(new BLE2902());

  // -----------------------------------------
  // Command characteristic (WRITE) for all commands
  // -----------------------------------------
  pCommandChar = pService->createCharacteristic(
      ECG_COMMAND_CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_WRITE
  );

  BLE2901* pCmdDesc = new BLE2901();
  pCmdDesc->setValue("Commands (START_SIMPLE, STOP_SIMPLE, START_STREAM, STOP_STREAM)");
  pCmdDesc->setAccessPermissions(ESP_GATT_PERM_READ);
  pCommandChar->addDescriptor(pCmdDesc);

  pCommandChar->setCallbacks(new CommandCallbacks());

  // Start service
  pService->start();

  // Start advertising
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(ECG_SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.println("BLE advertising started. Ready for connection.");
}




// =========================================
// Main loop
// - SIMPLE mode: send message every 2000 ms
// - STREAM mode: send binary packet every 40 ms
// =========================================
void loop() {
  if (deviceConnected) {
    unsigned long now = millis();

    // SIMPLE MODE
    if (simple_mode) {
      if (now - last_simple_time >= 2000) {  // 2 seconds
        last_simple_time = now;

        char msgBuf[64]; //allocates 64 bytes in memory 
        int len = buildSimpleMessage(msgBuf, sizeof(msgBuf), simple_counter); // pass in buffer, buffer size, and sample counter for simple mode
        // len = number of bytes consumed in msgBuf memory
        if (len > 0) {
          pDataChar->setValue((uint8_t*)msgBuf, len); //set pDataChar to contain values up to number of filled spaces in msgBuf
          pDataChar->notify(); //send data to host device 

          Serial.print("SIMPLE TX: ");
          Serial.write((uint8_t*)msgBuf, len);

          simple_counter++;
        }
      }
    }

    // STREAM MODE
    if (stream_mode) {
      if (now - last_stream_time >= 40) {  // ~25 Hz; 10 samples/packet => 250 Hz equivalent
        last_stream_time = now;

        uint8_t packet[28];
        buildBinaryPacket(packet, sizeof(packet));

        pDataChar->setValue(packet, sizeof(packet));
        pDataChar->notify();

        // Optional debug: print packet ID to Serial
        // Serial.print("STREAM TX packet ID: ");
        // Serial.println(packet[2]);
      }
    }
  }

  // Small yield; no blocking delays so BLE stack can run
  delay(1);
}