// ============= START COMMAND SENT TO START STREAMING FOR 30 SECONDS ===============
// ESP32 ECG Streaming Firmware
// Waits for "START" command from Python script, then streams data at 250Hz
// Notes:
// THIS FIRMWARE READS FROM GPIO 34 ON THE MCU TO COLLECT ANALOG SIGNAL FROM AD8232
// LO+ AND LO- ON AD8232 ARE CONNECTED TO GPIO 13 AND 14 ON MCU (logic not included for checking these readings for now)
// SAMPLING RATE IS 250HZ (change as desired)
// COLLECTING DATA FOR 30 SECONDS (change as desired)
// --- PIN DEFINITIONS ---
const int ECG_OUT_PIN = 34;    // AD8232 OUTPUT (Analog Read)
const int LO_PLUS_PIN = 13;    // AD8232 LO+ (Digital Input)
const int LO_MINUS_PIN = 14;   // AD8232 LO- (Digital Input)
const int LED_PIN = 2;         // Built-in LED for status

// --- SAMPLING CONFIGURATION ---
const int FS = 250;                              // Sampling frequency (Hz)
const int RECORDING_TIME_S = 30;                 // Total recording duration
const int TOTAL_SAMPLES = FS * RECORDING_TIME_S; // 7500 samples
const unsigned long SAMPLE_INTERVAL_US = 4000;   // 4000 microseconds = 250Hz

// --- STATE VARIABLES ---
bool is_recording = false;
unsigned long sample_count = 0;
unsigned long last_sample_time = 0;

void setup() {
  // Initialize serial at high speed
  Serial.begin(115200);
  
  // Set ADC resolution
  analogReadResolution(12);
  
  // Configure pins
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Wait a moment for serial to stabilize
  delay(1000);
  
  Serial.println("=== ESP32 ECG STREAMER READY ===");
  Serial.println("Send 'START' command to begin data collection");
  Serial.println("================================");
}

void loop() {
  // Check for START command from Python
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "START" && !is_recording) {
      // Start recording
      Serial.println("--- STARTING RECORDING ---");
      is_recording = true;
      sample_count = 0;
      last_sample_time = micros();
      digitalWrite(LED_PIN, HIGH);  // LED on during recording
    }
  }
  
  // Stream data if recording
  if (is_recording) {
    // Check if it's time for the next sample (every 4ms)
    if (micros() - last_sample_time >= SAMPLE_INTERVAL_US) {
      
      // Read ADC value
      int ecg_value = analogRead(ECG_OUT_PIN);
      
      // Send to serial (host device will receive this)
      Serial.println(ecg_value);
      
      // Update counters
      sample_count++;
      last_sample_time += SAMPLE_INTERVAL_US;
      
      // Check sample count
      if (sample_count >= TOTAL_SAMPLES) {
        Serial.println("--- RECORDING COMPLETE ---");
        is_recording = false;
        digitalWrite(LED_PIN, LOW);  // LED off
        sample_count = 0;
      }
    }
  }
}