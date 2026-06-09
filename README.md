# EEG_from_scratch

This is an open-source project for capturing 1 EEG channel, primarly intented for eyes closed/opened detection using cheap components.
It uses an ESP32 interfaced with an ADS1292R module through SPI for the acquisition, but the UI can also be used to simulate signals and replay EEG recordings.
The ADS1292R component is designed mostly for acquiring eletrocardiogram signals (ECG), which is why only one channel for EEG is reliably adapted, even though the ADS1292 chip supports two channels (CH1N, CH1P, CH2N, CH2P)

This prototype was tested using:

- O1 as signal electrode
- Right Earlobe as reference
- Left mastoid as bias/ground

## Safety Disclaimer

This project is intended for educational and research purposes only.
The system is NOT medically certified and must never be used for medical diagnosis or clinical applications.
The electrodes are connected to battery-powered low-voltage electronics only. Avoid using the system while charging laptops or devices connected to mains power unless proper electrical isolation is implemented.
