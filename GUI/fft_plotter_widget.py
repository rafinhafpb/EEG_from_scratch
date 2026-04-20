from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QLabel, QSlider, QFrame
from PySide6.QtCore import Qt
from GUI.signal_visualization import SignalPlotter
from signal_processing.fft_calculation import FFTCalculator
from typing import Tuple
import numpy as np

class FFTWidget(QWidget):
    def __init__(self, n_channels: int, fs: int):
        super().__init__()
        self.fft_calculator = FFTCalculator(fs=fs)
        self.log_scale = False
        self.max_freq = 100

        layout = QGridLayout()

        self.label_max_freq = QLabel("Max Freq: ")
        self.label_freq_value = QLabel("")

        self.slider_max_freq = QSlider(Qt.Orientation.Horizontal)
        self.slider_max_freq.setRange(1, 100)
        self.slider_max_freq.valueChanged.connect(self._update_max_freq_label)
        self.slider_max_freq.sliderReleased.connect(self._update_max_freq)
        self.slider_max_freq.setValue(100)

        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.VLine)
        vertical_line.setFrameShadow(QFrame.Sunken)

        self.cb_log_scale = QCheckBox("Log Scale")
        self.cb_log_scale.toggled.connect(self._set_log_scale)

        self.signal_plotter = SignalPlotter(n_channels=n_channels, x_label="Frequencies (Hz)")

        layout.addWidget(self.label_max_freq, 0, 0, 1, 1)
        layout.addWidget(self.slider_max_freq, 0, 1, 1, 1)
        layout.addWidget(self.label_freq_value, 0, 2, 1, 1)
        layout.addWidget(vertical_line, 0, 3, 1, 1)
        layout.addWidget(self.cb_log_scale, 0, 4, 1, 1)

        layout.addWidget(self.signal_plotter, 1, 0, 1, 5)

        self.setLayout(layout)

    def compute_fft(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        freqs, spectra = self.fft_calculator.compute(signal)
        return freqs, spectra

    def update_plot(self, freqs: np.ndarray, spectra: np.ndarray) -> None:
        # Apply max freq
        mask = freqs <= self.max_freq
        freqs = freqs[mask]
        spectra = spectra[:, mask]

        # Apply log scale
        if self.log_scale:
            spectra = 20 * np.log10(spectra + 1e-6)

        self.signal_plotter.update_plot(freqs, spectra)

    def _set_log_scale(self, value: bool):
        self.log_scale = value

    def _update_max_freq_label(self, value: int):
        self.label_freq_value.setText(str(value) + " Hz")

    def _update_max_freq(self):
        self.max_freq = self.slider_max_freq.value()
