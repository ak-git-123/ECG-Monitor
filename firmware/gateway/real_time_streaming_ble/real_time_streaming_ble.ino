// USE THIS AS A TESTER FIRMWARE FILE TO BEGIN TESTING BLE TRANSMISSION TO HOST DEVICE (DATASET IS 
// SECONDS WORTH OF DATA)


#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <BLE2901.h>

// ========== VARIABLES FOR DATA HANDLING AND PACKETIZATION ============================================
#define HEADER_1 0xAA
#define HEADER_2 0x55
#define END_MARKER 0xFF  // placeholder to indicate packet end


// ========== HARDWARE CONFIGURATION ==========
const int ECG_OUT_PIN = 34;   // AD8232 analog output
const int LO_PLUS_PIN = 13;   // AD8232 LO+ (leads-off detection)
const int LO_MINUS_PIN = 14;  // AD8232 LO- (leads-off detection)
const int LED_PIN = 2;        // Built-in LED for status


// #define SAMPLES_PER_PACKET 10
const uint8_t PACKET_SAMPLES = 10;
uint8_t packet_id = 0;  
uint16_t packet_buffer[PACKET_SAMPLES]; // buffer for samples that are being streamed, creates allocation in RAM
uint8_t sample_index = 0;
String cmd_buffer = "";
int total_sample_count = 0;
// ====================================================================================================================================

// ====== VARIABLES FOR BLE ========================================================================================
BLEServer* pServer  = nullptr;
BLECharacteristic* pDataChar = nullptr;  // NOTIFY (both modes share this)
BLECharacteristic* pCommandChar = nullptr;  // WRITE for commands

#define ECG_SERVICE_UUID "fa75e591-ba7c-4779-938d-4c5bcc3a431f"
#define ECG_DATA_CHARACTERISTIC_UUID "3f433ab7-4887-4b25-a57a-793cd0fdb3c2" // NOTIFY
#define ECG_COMMAND_CHARACTERISTIC_UUID "221f81c7-09ed-4af7-be04-e08033dd979f" // WRITE

bool deviceConnected = false;
bool streaming = false;

// ====================================================================================================================================

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
    streaming = false;
    Serial.println("Client disconnected.");
    BLEDevice::startAdvertising();  // allow reconnection
  }
};
void startStreaming() {
    packet_id = 1;    // reset packet ID
    sample_index = 0; // reset sample buffer index
    total_sample_count = 0;
    //streaming = true;


    // DEBUG: Confirm function was called
    digitalWrite(LED_PIN, HIGH);  // Turn LED on when START received
    delay(500);
    digitalWrite(LED_PIN, LOW);
    delay(500);
    digitalWrite(LED_PIN, HIGH);  // Blink twice
    delay(500);
    digitalWrite(LED_PIN, LOW);

    // Wait for BLE connection to fully stabilize before starting stream
    Serial.println("Waiting 3 seconds for BLE stack to stabilize...");
    delay(3000);
    Serial.println("Starting data stream now!");

    streaming = true;  // Enable streaming AFTER delay
}
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

   
    if (rxValue == "START") {
      // Enable stream mode, disable simple mode
      startStreaming();
      Serial.println("STARTING STREAMING");
    }
    else if (rxValue == "STOP") {
      streaming = false;
      Serial.println("STOPPING STREAMING");
    }
    // You can add more commands here later if needed
  }
};



void sendPacket(uint16_t *data) {
  // Calculate total packet size
  // Header (2) + Packet ID (1) + Timestamp (4) + 10 samples (20) + End marker (1) = 28 bytes
  const uint8_t packet_size = 2 + 1 + 4 + (PACKET_SAMPLES * 2) + 1; //make this PACKET_SAMPLES * 2 for 12 bit !!
  uint8_t packet[packet_size];
  uint8_t index = 0;
  
  // assign header to the first two bytes
  packet[index++] = HEADER_1;
  packet[index++] = HEADER_2;

  // assign packet ID to the third byte
  packet[index++] = packet_id;
  packet_id++;  // increment after assigning
  if (packet_id == 0) packet_id = 1;  // in case of overflow wrap

  // assign timestamp to bytes 4-7 (4 bytes, little-endian)
  unsigned long timestamp = millis();
  memcpy(&packet[index], &timestamp, sizeof(timestamp));
  index += sizeof(timestamp);

  // assign each of 10 signal values (2 bytes each) to bytes 8-27
  for (uint8_t i = 0; i < PACKET_SAMPLES; i++) {
    uint16_t sample = data[i] & 0x0FFF; // bit mask so only the 12bits are stored in a sample (optional but good to have)
    memcpy(&packet[index], &sample, sizeof(uint16_t));
    index += sizeof(uint16_t);
  }

  // assign end marker to last byte, 28
  packet[index++] = END_MARKER;

  // send entire packet at once
  pDataChar->setValue(packet, sizeof(packet));
  pDataChar->notify();

  

}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  // Set ADC resolution
  analogReadResolution(12);
  
  // Configure pins
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // =========== BLE SETUP ==========================================================================================
  // initialize the server/device "ECG Monitor ESP32"
  BLEDevice::init("ECG Monitor ESP32");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ECGServerCallbacks()); 
  BLEDevice::setMTU(512);  // Request larger MTU (max 512 for ESP32)



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
  // =========================================================================================================================================================

  // DIAGNOSTIC: Print ESP32 reset reason
  esp_reset_reason_t reason = esp_reset_reason();
  Serial.print("RESET_REASON:");
  Serial.println(reason);
  
  // Print startup message with timestamp
  Serial.print("BOOT_TIME:");
  Serial.println(millis());
}

void addADCSampleToBuffer() { 

  uint16_t sample = analogRead(ECG_OUT_PIN);
  total_sample_count++;
  packet_buffer[sample_index++] = sample; 
  if (sample_index >= PACKET_SAMPLES) { 
    sendPacket(packet_buffer); 
    sample_index = 0; 
  } 
} 
  
void loop() { 
  if (deviceConnected) {
    if (streaming) { 
        // static unsigned long next_sample_time = 0;
        // static unsigned long now = micros();
        static unsigned long 
        last_sample_time = 0; 
        if (micros() - last_sample_time >= 4000) { 
        addADCSampleToBuffer(); 
        last_sample_time = micros(); 
        } 
        // if (now >= next_sample_time) {
        //   addADCSampleToBuffer();
        //   next_sample_time += 4000;  // Schedule next sample 4ms from LAST scheduled time
        // }
  } 
}
}


