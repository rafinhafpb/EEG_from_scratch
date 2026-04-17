from buffer.data_buffer import DataBuffer
from GUI.main_window import MainWindow
from acquisition.simulate_acquisition import SignalGenerator
import sys
from PySide6.QtWidgets import QApplication

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

    # Start simulated signal
    generator = SignalGenerator(buffer, fs=SAMPLE_RATE)
    generator.start()

    # Start GUI
    app = QApplication(sys.argv)
    window = MainWindow(buffer)
    window.show()

    app.exec()
    generator.stop()


if __name__ == "__main__":
    main()