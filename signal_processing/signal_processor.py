import numpy as np
from scipy import signal
from buffer.data_buffer import DataBuffer
from typing import Tuple

class SignalProcessor:
    def __init__(self, buffer: DataBuffer):
        self.buffer = buffer
        self.fs = buffer.fs

        # Processing flags (controlled by GUI)
        self.use_notch_50 = False
        self.use_notch_60 = False
        self.use_bpf = False

        # Precompute filters
        self._init_filters()

    def _init_filters(self):
        # Notch filters
        self.notch50_b, self.notch50_a = signal.iirnotch(50, Q=30, fs=self.fs)
        self.notch60_b, self.notch60_a = signal.iirnotch(60, Q=30, fs=self.fs)

        # Band-pass filter (0.5-40 Hz by default)
        self.bpf_b, self.bpf_a = signal.butter(4, [0.5, 40], btype='bandpass', fs=self.fs)

        # Initialize states
        self._reset_filter_states()

    def _reset_filter_states(self):
        n = self.buffer.n_channels

        zi_50 = signal.lfilter_zi(self.notch50_b, self.notch50_a)
        zi_60 = signal.lfilter_zi(self.notch60_b, self.notch60_a)
        zi_bpf = signal.lfilter_zi(self.bpf_b, self.bpf_a)

        self.notch50_state = [zi_50.copy() for _ in range(n)]
        self.notch60_state = [zi_60.copy() for _ in range(n)]
        self.bpf_state = [zi_bpf.copy() for _ in range(n)]

    def process(self, data: np.ndarray = None) -> np.ndarray:
        """data: (n_channels, n_samples)"""
        if data is None:
            processed = self.buffer.get_data()[0].copy()
        else:
            processed = data.copy()

        for i in range(processed.shape[0]):
            x = processed[i]

            # notch 50
            if self.use_notch_50:
                x, self.notch50_state[i] = signal.lfilter(
                    self.notch50_b,
                    self.notch50_a,
                    x,
                    zi=self.notch50_state[i]
                )

            # notch 60
            if self.use_notch_60:
                x, self.notch60_state[i] = signal.lfilter(
                    self.notch60_b,
                    self.notch60_a,
                    x,
                    zi=self.notch60_state[i]
                )

            # band-pass
            if self.use_bpf:
                x, self.bpf_state[i] = signal.lfilter(
                    self.bpf_b,
                    self.bpf_a,
                    x,
                    zi=self.bpf_state[i]
                )

            processed[i] = x

        return processed

    def set_bpf_frequency(self, frequencies: Tuple[float, float]):
        self.bpf_b, self.bpf_a = signal.butter(4, frequencies, btype='bandpass', fs=self.fs)
        self._reset_filter_states()

    def enable_50_Hz_notch(self, enabled: bool):
        self.use_notch_50 = enabled

    def enable_60_Hz_notch(self, enabled: bool):
        self.use_notch_60 = enabled

    def enable_bpf(self, enabled: bool):
        self.use_bpf = enabled
        self._reset_filter_states()

    def get_processed_window(self, time_s: int = 2.0):
        data, ts = self.buffer.get_window_time(time_s)

        if data.shape[1] < 10:
            return data, ts  # not enough samples yet

        processed = self.process(data)
        return processed, ts