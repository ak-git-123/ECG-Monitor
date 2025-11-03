// DESCRIPTION:
// This code will generate data of a single heart beat at 75bpm, sampled at 500Hz (400 samples for a 0.8sec heartbeat). 
// It will then create packets of ten data points each and stream them to the corresponding Python file, where they will be compared with the expected data.
// Right now, the frequency and bpm values are hardcoded into the code, not set by the Python file. This can be changed later to make the code more dynamic.



#include <vector>  // include for std::vector
#include <math.h>  // for M_PI, sin
#define PACKET_SIZE 10
#define PACKETS 41
const int LED_PIN = 5;
const int frequency_hz = 500;
const int bpm = 75;
int packets = 1;
int bufferIndex = 0;
float buffer[PACKET_SIZE]; // you MUST either use #define or const in to initialize array size, int packet_size = 10 would not be allowed - 
// C++ requires these kinds of values to be known at compile time, whereas int packet_size is accessed only at runtime
// Other times to use constant values = pin assignment, protocol/hardware parameters (timing, sample rate), registers (?)
bool streaming = false;
int sampleCounter = 0;
std::vector<float> ecg_beat;
std::vector<int> ecg_beat_digital;
std::vector<float> full_heart_beat();
std::vector<int> convert_to_digital(const std::vector<float>& ecg_beat);
const float BASELINE_V = 1.5f;
const float GAIN = 100.0f;
const float VREF = 3.3f;
const int ADC_MAX = 4095; 



void setup() {
  // put your setup code here, to run once:

  Serial.begin(115200); // establishes connection between laptop and MCU, send data bytes at rate of 115200 bits/sec
  delay(1000); // let serial initialize
  pinMode(LED_PIN, OUTPUT);  // configure as output
  digitalWrite(LED_PIN, LOW);
  Serial.println("Serial test started");
  ecg_beat = full_heart_beat();
  ecg_beat_digital = convert_to_digital(ecg_beat);

}

// FUNCTIONS FOR GENERATING EACH PART OF HEARTBEAT ---------------------------------------------------------------------
std::vector<float> p_wave(int n){
  std::vector<float> wave;
  wave.reserve(n);
  for (int i = 0; i < n; i++) {
    float t = M_PI * i / (n - 1);
    wave.push_back(0.25 * sin(t));  // mV
  }
  return wave;
  }

std::vector<float> qrs_complex(int n){
  std::vector<float> wave;
  wave.reserve(n);
  int q = int(n * 0.25);
  int r = int(n * 0.5);
  int s = n - q - r;
    // Q wave: small downward deflection
  for (int i = 0; i < q; i++) {
    wave.push_back(-0.1f * (static_cast<float>(i) / q));  
  }

  // R wave: sharp upward spike
  for (int i = 0; i < r; i++) {
    wave.push_back(-0.1f + (1.1f * static_cast<float>(i) / r));  
  }

  // S wave: rapid drop back to baseline
  for (int i = 0; i < s; i++) {
    wave.push_back(1.0f - (1.0f * static_cast<float>(i) / s));  
  }

  return wave;
}
    
// T wave: long sin wave
std::vector<float> t_wave(int n){
  std::vector<float> wave;
  wave.reserve(n);
  for (int i = 0; i < n; i++) {
    float t = M_PI * i / (n - 1);
    wave.push_back(0.35 * sin(t));  // mV
  }
  return wave;
}

// Flat segments
std::vector<float> flat(int n) {
  return std::vector<float>(n, 0.0f);
}
// --------------------------------------------------------------------------------------------------------------------
// Analog to Digital Conversion of voltage

// def voltage_ADC(ecg):
//     ecg_amplified_mV = ecg * 100 #amplify mV by 100x
//     ecg_adjusted = ecg_amplified_mV/1000 + 1.5 #convert to V from mV, then add 1.5V to bring to baseline
//     return ecg_adjusted

// CREATE FULL HEART BEAT DATA --------------------------------------------------------------------------------------------------------------------
std::vector<float> full_heart_beat(){
  int total_samples = frequency_hz/bpm;
  std::vector<float> beat;
  beat.reserve(total_samples);

  int P   = int(0.08 * frequency_hz);
  int PR  = int(0.04 * frequency_hz);
  int QRS = int(0.08 * frequency_hz);
  int ST  = int(0.12 * frequency_hz);
  int T   = int(0.16 * frequency_hz);
  int TP  = int(0.32 * frequency_hz);

  std::vector<float> P_seg   = p_wave(P);
  std::vector<float> PR_seg  = flat(PR);
  std::vector<float> QRS_seg = qrs_complex(QRS);
  std::vector<float> ST_seg  = flat(ST);
  std::vector<float> T_seg   = t_wave(T);
  std::vector<float> TP_seg  = flat(TP);

  // Concatenate segments
  beat.insert(beat.end(), P_seg.begin(), P_seg.end());
  beat.insert(beat.end(), PR_seg.begin(), PR_seg.end());
  beat.insert(beat.end(), QRS_seg.begin(), QRS_seg.end());
  beat.insert(beat.end(), ST_seg.begin(), ST_seg.end());
  beat.insert(beat.end(), T_seg.begin(), T_seg.end());
  beat.insert(beat.end(), TP_seg.begin(), TP_seg.end());

  return beat;
}

float floatToADC(float ecg_mV){
  float amplified_mV = ecg_mV * GAIN;         // e.g. 1.0 mV -> 100 mV
  float amplified_V = amplified_mV / 1000.0f; // mV -> V
  float vin = BASELINE_V + amplified_V;

  if (vin < 0.0f) vin = 0.0f; 
  if (vin > VREF) vin = VREF; 
  int adc = (int) roundf((vin / VREF) * ADC_MAX); 
  return adc; // 0..4095
}



std::vector<int> convert_to_digital(const std::vector<float>& ecg_beat){
  std::vector<int> adc_values;
  adc_values.reserve(ecg_beat.size());
  for (size_t i = 0; i < ecg_beat.size(); i++){
    adc_values.push_back(floatToADC(ecg_beat[i]));
  }
  return adc_values;

}
// int total_samples

void addToPacket(float sample){
  buffer[bufferIndex] = sample;   // store in RAM buffer
  bufferIndex++;

  if (bufferIndex >= PACKET_SIZE) {
    // Buffer full → packet ready
    sendPacket();
    bufferIndex = 0; // reset for next packet
  }
}

void sendPacket(){
  //int num_of_packets = 1;
  String packetNum = String(packets);
  Serial.print("Packet " + packetNum + ": ");

  for (int i = 0; i < PACKET_SIZE; i++) {
    Serial.print(buffer[i]);
    Serial.print(" ");
  }
  Serial.println();
  //num_of_packets++;
  packets++;
}
void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available()){
    String cmd = Serial.readStringUntil('\n');  // read until newline
    cmd.trim();                                 // remove extra whitespace

    if (cmd == "START") {
      streaming = true;
      digitalWrite(LED_PIN, HIGH);
      packets = 1;
      bufferIndex = 0;
      sampleCounter = 0;

      Serial.println("Streaming started");
    } 
    else if (cmd == "STOP") {
      streaming = false;
      digitalWrite(LED_PIN, LOW);
      Serial.println("Streaming stopped");
    }

  }  

  if (streaming) {

    if (packets < PACKETS){
      int sample = ecg_beat_digital[sampleCounter];
      // Store it in a packet buffer
      addToPacket(sample);
      sampleCounter++;
      // Simple wait to slow down generation for testing
      delay(2);  // 500Hz
    }
    else {
      streaming = false;
      Serial.println("Finished printing all packets.");

    }
  }


}
