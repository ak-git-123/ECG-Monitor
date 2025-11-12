import wfdb
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
import os
'''
This test file was developed to create and test the algorithm logic for detecting R-peak instances in heart rate data.
The following is the logic for the calculations made to do the same.:

For the first 2 seconds (calibration period), collect data and calculate threshold for R-peak (static threshold for now) - 90th percentile of data
after threshold has been calculated, do the following calculations on the next part of data. 
    Note: this will be performed on a full set of collected data in 8-bit resolution (digital), real-time analysis will be performed in main src code later

1 - Calculate difference between n and n+4 values (16ms apart) - (n4 - n0, n5-n1, etc.) - this can be configured later as well
2 - Square the difference (array)
3 - Take average of last X samples of squared differences array ("integrated", calculate rolling average)
4 - Compare each averaged value to threshold to find start and end of peak
5 - Once start and end of peak have been found, find local maximum of data within that span - this is R-Peak
6 - Store time index and value of R-peak, and calculate BPM from delta time between R-peaks (can be done between consecutive R-peaks or by calculating number of peaks in X seconds)

When testing, the following parameters were made configurable: calibration time, slope spacing, moving average window, total ECG data seconds, ECG data source.
Results of detected BPMs (calculated from algorithm) vs actual BPMs (pulled from ECG dataset annotations) were printed to the screen for comparison.
R-peaks (detected vs. annotated) were also graphed for visual inspection.


'''
class R_peak_detector:
    def __init__(self, fs = 250, sec_of_calibration = 2, slope_spacing = 4, mov_ave_window=15, sec_ecg = 20, file_name = 'ECG_Data_P0000/p00000_s00'):
        self.fs = fs
        self.sec_of_calibration = sec_of_calibration
        self.sec_ecg = sec_ecg
        self.file_name = file_name
        self.slope_spacing = slope_spacing
        self.mov_ave_window = mov_ave_window
        
        self.warmup_samples = self.fs * self.sec_of_calibration #500
        self.refractory_samples = int(0.2 * self.fs) #200ms of refractory time, during which no new peak should occur

        
        self.sample_count = 0
        self.raw_buffer = [0] * (self.slope_spacing + 5)
        self.squared_buffer = [0] * mov_ave_window
        self.integrated_warmup = [0] * self.warmup_samples
        self.warmup_complete = False
        self.threshold = 0.0

        self.samples_since_last_peak = self.refractory_samples + 1
        self.in_peak = False
        self.peak_start = 0
        self.peak_max_value = 0  
        self.peak_max_index = 0
        self.detected_peaks = []

    def check_for_peak(self, integrated, threshold):
        
        self.samples_since_last_peak += 1

        if not self.in_peak:
            # Looking for a peak
            if integrated > threshold and self.samples_since_last_peak > self.refractory_samples:
                self.in_peak = True
                self.peak_start = self.sample_count
                self.peak_max_index = self.sample_count
                self.peak_max_value = integrated
        else:
            if integrated > self.peak_max_value:
                self.peak_max_value = integrated
                self.peak_max_index = self.sample_count  # Update to current position
            # Currently in a peak, wait for it to drop back below threshold
            if integrated < threshold:
                search_start = max(0, self.peak_start)
                search_end = self.sample_count
                
                raw_max_value = -1
                raw_max_index = self.peak_max_index
                
                for check_index in range(search_start, search_end):
                    buffer_pos = check_index % len(self.raw_buffer)
                    if self.raw_buffer[buffer_pos] > raw_max_value:
                        raw_max_value = self.raw_buffer[buffer_pos]
                        raw_max_index = check_index
            
                # Peak ended, find the maximum in the peak region
                self.detected_peaks.append(raw_max_index)
                self.samples_since_last_peak = 0
                self.in_peak = False
                # print(f"Peak at sample {self.peak_max_index}, integrated value: {self.peak_max_value:.2f}")

    def process_sample(self, current_sample):
    #global sample_count, raw_buffer, squared_buffer, warmup_complete, threshold, integrated_warmup
        len_buff = len(self.raw_buffer)
        self.raw_buffer[self.sample_count % len_buff] = current_sample
        integrated_full_temp = []
        if self.sample_count >= self.slope_spacing:
            old_sample = self.raw_buffer[(self.sample_count - self.slope_spacing) % len_buff]
            diff = current_sample - old_sample
            squared = diff * diff

            #Store squared value in circular buffer
            self.squared_buffer[self.sample_count % self.mov_ave_window] = squared
            
            if self.sample_count >= (self.slope_spacing + self.mov_ave_window - 1): #sample_count being at least 19 means that squared_buffer is 15 in length
                # Sum last 15 squared values
                total = sum(self.squared_buffer)
                integrated = total / self.mov_ave_window
                integrated_full_temp.append(integrated)

                if not self.warmup_complete:
                    # WARMUP: Store for threshold calculation
                    
                    min_samples = self.slope_spacing + self.mov_ave_window - 1
                    warmup_index = self.sample_count - min_samples
                    #print(integrated_warmup)
                    if warmup_index < self.warmup_samples:
                        self.integrated_warmup[self.sample_count - min_samples] = integrated
                    
                    if self.sample_count == 519:  # 500 integrated values collected

                        self.threshold = np.percentile(self.integrated_warmup, 90)
                        self.integrated_warmup = None  # Free up memory 
                        self.warmup_complete = True
                        print(f"Warmup complete! Threshold set to: {self.threshold:.2f}")
                else:
                    # POST-WARMUP: Use for peak detection (don't store)
                    self.check_for_peak(integrated, self.threshold)

        self.sample_count += 1



# method for applying bandpass filter on digital data
# low pass filter at 15Hz blocks all frequencies above 15Hz - power-line hum, muscle activity
# high pass filter at 5Hz blocks all frequencies below 5Hz - removes slow-changing components like baseline drift
def bandpass_filter(data, fs, lowcut=5, highcut=15, order=2):
    nyq = 0.5 * fs # Nyquist is always half of sampling frequency 
    low = lowcut / nyq # divide by Nyquist to get the fraction of the distribution that you want to remove
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data)


def generate_data(file_name, fs, sec_ecg, sec_of_calibration):
    record = wfdb.rdrecord(file_name, sampfrom=0, sampto=fs * sec_ecg) # hz * num of seconds = number of values to extract 
    ecg_signal = record.p_signal[:, 0]
    
    # Load annotations (beat locations)
    annotation = wfdb.rdann(file_name, 'atr', sampfrom=0, sampto=fs * sec_ecg)
    print("Unique beat types:", set(annotation.symbol))
    print("Unique rhythm annotations:", set(annotation.aux_note))
    # Get R-peak sample indices
    all_r_peaks = annotation.sample  # Array of sample indices where beats occur
    # Filter out peaks that occur during calibration period
    calibration_samples = int(sec_of_calibration * fs)  # e.g., 2 * 250 = 500
    r_peaks = all_r_peaks[all_r_peaks >= calibration_samples]  # Only peaks after calibration
    
    num_peaks = len(r_peaks)
    print(f"Number of beats in {sec_ecg} seconds: {num_peaks}")
    print(f"R-peak locations (sample indices): {r_peaks}")
    return ecg_signal, num_peaks, r_peaks

#Convert single float value to digital reading (amplify by 100x, turn to voltage, add to baseline, then convert to 8-bit)
def float_to_adc(ecg_value, gain = 100, vin = 0, vref = 3.3, baseline = 1.5, adc_max = 255):
    amplified_mV = ecg_value * gain;  #e.g. 1.0 mV -> 100 mV
    amplified_V = amplified_mV / 1000; #mV -> V
    vin = baseline + amplified_V

    vin = max(0.0, min(vref, vin))  # clamp to 0..VREF
    adc = int(round((vin / vref) * adc_max))
    return adc # 0..4095

#Convert full ECG dataset to digital data
def convert_to_digital(ecg):
    ecg_digital = []
    for i in ecg:
        ecg_digital.append(float_to_adc(i))
    return ecg_digital


  

def main(file_name, sec_ecg, slope_spacing):
    ecg_data_path = os.path.join(os.path.dirname(__file__), "..", "data", file_name)

    file_name = ecg_data_path
    fs = 250
    sec_ecg = sec_ecg
    slope_spacing = slope_spacing
    sec_of_calibration = 2
    ecg_signal, num_peaks, r_peaks = generate_data(file_name, fs, sec_ecg, sec_of_calibration) #generate analog dataset from Incentia dataset
    ecg_digital = convert_to_digital(ecg_signal) #convert dataset from analog to digital
    print("ECG Signal to paste into firmware of ESP32 #2 (DAC): ")
    print(ecg_digital)
    ecg_digital_filtered = bandpass_filter(ecg_digital, fs, lowcut=5, highcut=15, order=2) #apply bandpass filtering on dataset
    
    # plt.plot(ecg_digital, label='Digital')
    plt.plot(ecg_digital_filtered, label = 'Digital and filtered')
    plt.legend()
    plt.show()
    
    # create detector with specific testing parameters
    detector = R_peak_detector(fs=fs, sec_of_calibration=sec_of_calibration, slope_spacing = slope_spacing, mov_ave_window=15, sec_ecg=sec_ecg, file_name = file_name)
    
    # run spike detection on each sample 
    for sample in ecg_digital_filtered:
        detector.process_sample(sample)

    # compare detected peaks with actual peaks (information parsed from dataset annotations)
    np_detected_peaks = np.array(detector.detected_peaks)
    np_actual_peaks = np.array(r_peaks)
    np_actual_peaks = np_actual_peaks[0:len(np_detected_peaks)]
    
    len_detected_peaks = len(np_detected_peaks)
    pass_counter = len_detected_peaks
    for i in range(len_detected_peaks):
        if np.abs(np_detected_peaks[i] - np_actual_peaks[i]) > 5:
            pass_counter -= 1

    # calculate BPM
    bpm_values_detected = []
    bpm_values_actual = []
    actual_inst_bpms = []
    detected_inst_bpms = []
    # iterate with step of 3 peaks
    for i in range(0, len(np_detected_peaks) - 2, 3):
        start = np_detected_peaks[i]
        end = np_detected_peaks[i + 2]
        rr_interval = (end - start) / fs  # in seconds
        bpm = 60 / (rr_interval / 2)  # divide by 2 because it spans 2 beats (3 peaks)
        bpm_values_detected.append(round(float(bpm), 1))

    for i in range(0, len(np_actual_peaks) - 2, 3):
        start = np_actual_peaks[i]
        end = np_actual_peaks[i + 2]
        rr_interval = (end - start) / fs  # in seconds
        bpm = 60 / (rr_interval / 2)  # divide by 2 because it spans 2 beats (3 peaks)
        bpm_values_actual.append(round(float(bpm),1))
    
    length_peaks = len(np_actual_peaks)
    for i in range(length_peaks-1):
        d_bpm = 60/((np_detected_peaks[i+1] - np_detected_peaks[i])/fs)
        a_bpm = 60/((np_actual_peaks[i+1] - np_actual_peaks[i])/fs)
        detected_inst_bpms.append(round(float(d_bpm), 1))
        actual_inst_bpms.append(round(float(a_bpm), 1))

    print("Detected v. Actual BPM values:")
    for i in range(len(bpm_values_actual)):
        print(f"{bpm_values_detected[i]} vs. {bpm_values_actual[i]}")

    print(f"\nTotal peaks detected: {len(detector.detected_peaks)}")
   
    print(f"Actual peaks: {r_peaks}")
    
    print(f"Number of peaks that are within tolerance: {pass_counter}/{len_detected_peaks}")

    print(f"Instantaneous detected bpms: {detected_inst_bpms}")
    print(f"Instantaneous actual bpms: {actual_inst_bpms}")

    # Plotting - simple version
    plt.figure(figsize=(14, 6))
    plt.plot(ecg_digital, label='ECG Signal', color='blue')
    
    # Mark detected peaks
    print(f"Detector detected peaks: {detector.detected_peaks}")


    peak_values = [ecg_digital[i] for i in detector.detected_peaks if i < len(ecg_digital)] #-detector.slope_spacing
    plt.scatter(detector.detected_peaks, peak_values, 
                color='red', s=100, marker='o', label='Detected R-Peaks')
    plt.scatter(r_peaks, [ecg_digital[i] for i in r_peaks if i < len(ecg_digital)], 
                color='g', marker='o', s=50, label='Actual Peaks')
    
    plt.xlabel('Sample Number')
    plt.ylabel('ADC Value')
    plt.title('R-Peak Detection')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":

# GOLDEN DATA: P00000_s00

# Patient 00000 - segment 0 (16ms interval for slope spacing)
    # main('ECG_Data_P0000/p00000_s00', 10, 4) #12/12 passed
    #Detected bpms: [88.5, 91.5, 91.7, 92.0]
    #Actual bpm: [88.5, 91.2, 92.6, 91.7]
    # main('ECG_Data_P0000/p00000_s00', 20, 4) #25/28 passed 
    #Detected bpms: [88.5, 91.5, 91.7, 92.0, 92.9, 92.9, 92.0, 91.5, 91.7]
    #Actual bpm: [88.5, 91.2, 92.6, 91.7, 92.9, 91.7, 91.7, 92.9, 91.2]
    main('ECG_Data_P0000/p00000_s00', 30, 4) #25/28 passed 

    # main('ECG_Data_P0000/p00000_s00', 60, 4) #76/91 passed
    #Detected bpms: [88.5, 91.5, 91.7, 92.0, 92.9, 92.9, 92.0, 91.5, 91.7, 91.5, 90.1, 91.5, 91.5, 92.0, 88.5, 88.8, 89.8, 89.6, 90.4, 91.2, 95.2, 92.3, 91.2, 92.9, 96.2, 99.7, 102.4, 104.2, 109.5, 109.5]
    #Actual bpm: [88.5, 91.2, 92.6, 91.7, 92.9, 91.7, 91.7, 92.9, 91.2, 91.5, 90.9, 91.5, 91.7, 92.0, 88.2, 88.5, 91.2, 89.3, 89.0, 91.2, 92.6, 92.3, 91.2, 91.7, 94.0, 100.7, 102.0, 104.5, 107.9, 110.7
    
# Patient 00001 - segment 5 (16ms interval for slope spacing)
    # main('ECG_Data_P0001/p00001_s05', 10, 4) #5/12 passed
    # #Detected bpms: [73.7, 73.2, 73.3]
    # #Actual bpm: [73.9, 74.1, 73.5]
    # main('ECG_Data_P0001/p00001_s05', 20, 4) #5/26 passed
    # #Detected bpms: [73.7, 73.2, 73.3, 75.4, 77.9, 76.7, 76.3]
    # #Actual bpm: [73.9, 74.1, 73.5, 76.1, 76.5, 76.7, 76.1]
    # main('ECG_Data_P0001/p00001_s05', 60, 4) #didn't work
    # #Detected bpms: [73.7, 73.2, 73.3, 75.4, 77.9, 76.7, 76.3, 76.3, 75.2, 75.6, 75.9, 75.2, 75.4, 75.0, 74.6, 74.3, 74.1, 75.8, 75.4, 76.5, 77.3, 76.3, 75.2, 72.8]
    # #Actual bpm: [73.9, 74.1, 73.5, 76.1, 76.5, 76.7, 76.1, 76.1, 75.9, 76.3, 76.3, 75.2, 74.6, 74.4, 74.4, 74.1, 74.1, 74.1, 74.8, 75.9, 77.1, 75.9, 74.4, 73.7]


# OTHER TESTED CONDITIONS
# # Patient 00000 - segment 0 (8ms interval for slope spacing)
#     main('ECG_Data_P0000/p00000_s00', 10, 2) #8/12 passed
#     main('ECG_Data_P0000/p00000_s00', 20, 2) #14/28 passed 
#     main('ECG_Data_P0000/p00000_s00', 60, 2) #39/91 passed

# Patient 00000 - segment 0 (12ms interval for slope spacing)
    # main('ECG_Data_P0000/p00000_s00', 10, 3) #11/12 passed
    # main('ECG_Data_P0000/p00000_s00', 20, 3) #25/28 passed 
    # main('ECG_Data_P0000/p00000_s00', 60, 3) #77/91 passed
    
# Patient 00000 - segment 0 (24ms interval for slope spacing)   
    # main('ECG_Data_P0000/p00000_s00', 10, 6) #11/12 passed
    # main('ECG_Data_P0000/p00000_s00', 20, 6) # 23/28 passed
    # main('ECG_Data_P0000/p00000_s00', 60, 6) #68/91 passed

# Patient 00000 - segment 0 (40ms interval for slope spacing)
    # main('ECG_Data_P0000/p00000_s00', 10, 10) #12/12 passed
    # main('ECG_Data_P0000/p00000_s00', 20, 10) #27/28 passed 
    # main('ECG_Data_P0000/p00000_s00', 60, 10) #81/91 passed


# Patient P00005 - segment 0 (16ms interval for slope spacing)
    # main('ECG_Data_P0005/p00005_s00', 10, 4) 
    # main('ECG_Data_P0005/p00005_s00', 20, 4)  
    # main('ECG_Data_P0005/p00005_s00', 60, 4)


# # BAD FILE -- Patient 00001 - segment 0 (40ms interval for slope spacing)
#     main('ECG_Data_P0001/p00001_s00', 10, 4) 
#     main('ECG_Data_P0000/p00001_s00', 20, 4) 
#     main('ECG_Data_P0000/p00001_s00', 60, 4) 

   