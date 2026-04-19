from buffer.data_buffer import DataBuffer
from GUI.main_window import MainWindow
from acquisition.simulate_acquisition import SignalGenerator
from acquisition.load_acquisition import SignalLoader
from PySide6.QtWidgets import QApplication
import numpy as np
import sys

LOAD = True

SAMPLE_RATE = 250
TIME_WINDOW = 10
N_CHANNELS = 2

def main():
    # Create buffer
    buffer = DataBuffer(
        n_channels=N_CHANNELS,
        time_window_s=TIME_WINDOW,
        sampling_rate_Hz=SAMPLE_RATE
    )

    if LOAD:
        loader = SignalLoader(buffer, filepath="acquisition/recordings/S1.csv", target_fs=160)
        loader.data = loader.data = (loader.data - np.mean(loader.data, axis=1, keepdims=True)) / 1000
    else:
        generator = SignalGenerator(buffer, fs=SAMPLE_RATE)

    # Start GUI
    app = QApplication(sys.argv)
    window = MainWindow(buffer)

    if LOAD:
        window.start_acquisition.connect(loader.start)
    else:
        window.start_acquisition.connect(generator.start)

    window.show()

    app.exec()
    if LOAD:
        loader.stop()
    else:
        generator.stop()


if __name__ == "__main__":
    main()