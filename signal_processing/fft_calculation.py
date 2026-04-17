import numpy as np
from typing import Tuple


class FFTCalculator:
    def __init__(self, fs: int):
        self.fs = fs

    def compute(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        signal: shape (n_channels, n_samples)\n
        returns: frequencies, magnitude
        """
        n = signal.shape[1]

        # Apply window
        window = np.hanning(n)
        signal_windowed = signal * window[np.newaxis, :]

        # FFT (real-valued optimized) for each channel
        fft_vals_all_channels = np.fft.rfft(signal_windowed, axis=1)

        # Only positive frequencies
        freqs = np.fft.rfftfreq(n, 1 / self.fs)

        # Normalized magnitude
        magnitude = (2.0 / n) * np.abs(fft_vals_all_channels)

        return freqs, magnitude