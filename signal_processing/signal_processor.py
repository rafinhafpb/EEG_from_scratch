import numpy as np
from scipy import signal
from buffer.data_buffer import DataBuffer
from typing import Tuple

class SignalProcessor:
    def __init__(self, buffer: DataBuffer):
        self.buffer = buffer
        self.fs = buffer.fs
        self.time_window_s = buffer.time_window_s

        self.use_notch_50 = False
        self.use_notch_60 = False
        self.use_bpf = False

        # Internal filtered circular buffer — same shape as raw buffer
        self._max_samples = buffer.max_samples
        self._n_channels = buffer.n_channels

        self._filtered_data = np.zeros((self._n_channels, self._max_samples), dtype=np.float32)
        self._filtered_ts = np.zeros(self._max_samples, dtype=np.float64)
        self._write_idx = 0
        self._size = 0              # how many slots are valid, up to _max_samples
        self._n_filtered = 0        # monotonic count of samples filtered so far

        self._init_filters()

    def _init_filters(self):
        self.notch50_b, self.notch50_a = signal.iirnotch(50, Q=30, fs=self.fs)
        self.notch60_b, self.notch60_a = signal.iirnotch(60, Q=30, fs=self.fs)
        self.bpf_b, self.bpf_a = signal.butter(4, [0.5, 40], btype='bandpass', fs=self.fs)

        self._notch50_zi_base = signal.lfilter_zi(self.notch50_b, self.notch50_a)
        self._notch60_zi_base = signal.lfilter_zi(self.notch60_b, self.notch60_a)
        self._bpf_zi_base = signal.lfilter_zi(self.bpf_b, self.bpf_a)

        self._reset_filter_states()

    def _reset_filter_states(self):
        n = self._n_channels
        self._notch50_state = [None] * n
        self._notch60_state = [None] * n
        self._bpf_state = [None] * n

    def _catch_up(self):
        """
        Pull unfiltered samples from the raw buffer and process them.
        We track the raw buffer's write_idx and size directly to know exactly which samples are new since the last call.
        """
        with self.buffer.lock:
            raw_write_idx = self.buffer.write_idx
            raw_size = self.buffer.size
            raw_data = self.buffer.data.copy()
            raw_ts = self.buffer.timestamps.copy()

        if raw_size == 0:
            return

        # Filtered buffer is empty (fresh start or after reprocess_all): process everything the raw buffer currently holds
        if self._size == 0:
            n_new = raw_size
        # raw_write_idx > self._write_idx: n_new is the diff
        elif raw_write_idx > self._write_idx:
            n_new = raw_write_idx - self._write_idx
        # raw_write_idx < self._write_idx: raw buffer wrapped around, distance going forward around the ring
        elif raw_write_idx < self._write_idx:
            n_new = (self._max_samples - self._write_idx) + raw_write_idx
        # Indices are equal: either nothing is new or a full cycle passed.
        else:
            # Compare sizes: if raw grew by max_samples we have a full buffer of new data.
            n_new = raw_size - self._size

        if n_new <= 0:
            return

        # Extract the new samples in chronological order
        start = (raw_write_idx - n_new) % self._max_samples

        if start + n_new <= self._max_samples:
            # Contiguous slice: no wrap
            new_samples = raw_data[:, start:start + n_new]
            new_ts = raw_ts[start:start + n_new]
        else:
            # Wraps around end of array
            first_part = self._max_samples - start
            new_samples = np.concatenate([raw_data[:, start:], raw_data[:, :n_new - first_part]], axis=1)
            new_ts = np.concatenate([raw_ts[start:], raw_ts[:n_new - first_part]])

        filtered = self._apply_filters(new_samples)

        # Write into the internal circular filtered buffer
        for k in range(n_new):
            self._filtered_data[:, self._write_idx] = filtered[:, k]
            self._filtered_ts[self._write_idx]       = new_ts[k]
            self._write_idx = (self._write_idx + 1) % self._max_samples
            self._size = min(self._size + 1, self._max_samples)

    def _apply_filters(self, chunk: np.ndarray) -> np.ndarray:
        """
        Apply active filters to chunk of shape (n_channels, n_samples).
        Filter states are preserved across calls for continuity.
        """
        out = chunk.copy().astype(float)

        for i in range(out.shape[0]):
            x = out[i]

            if self.use_notch_50:
                if self._notch50_state[i] is None:
                    self._notch50_state[i] = self._notch50_zi_base.copy() * x[0]
                x, self._notch50_state[i] = signal.lfilter(
                    self.notch50_b,
                    self.notch50_a,
                    x,
                    zi=self._notch50_state[i]
                )
            else:
                self._notch50_state[i] = None

            if self.use_notch_60:
                if self._notch60_state[i] is None:
                    self._notch60_state[i] = self._notch60_zi_base.copy() * x[0]
                x, self._notch60_state[i] = signal.lfilter(
                    self.notch60_b,
                    self.notch60_a,
                    x,
                    zi=self._notch60_state[i]
                )
            else:
                self._notch60_state[i] = None

            if self.use_bpf:
                if self._bpf_state[i] is None:
                    self._bpf_state[i] = self._bpf_zi_base.copy() * x[0]
                x, self._bpf_state[i] = signal.lfilter(
                    self.bpf_b,
                    self.bpf_a,
                    x,
                    zi=self._bpf_state[i]
                )
            else:
                self._bpf_state[i] = None

            out[i] = x

        return out

    def get_processed_window(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Advance filtering to match current raw buffer, then return the
        most recent time_window_s of filtered data.
        """
        self._catch_up()

        if self._size < 10:
            return np.zeros((self._n_channels, 0)), np.array([])

        n_window = min(int(self.time_window_s * self.fs), self._size)

        # Read n_window samples backwards from the write pointer, same pattern as DataBuffer
        if self._size < self._max_samples:
            # Buffer not yet full: data lives in [0, _write_idx)
            idx = np.arange(self._write_idx - n_window, self._write_idx)
        else:
            # Buffer full: unwrap from write pointer
            idx = np.array([(self._write_idx - n_window + k) % self._max_samples for k in range(n_window)])

        return self._filtered_data[:, idx].copy(), self._filtered_ts[idx].copy()

    def reprocess_all(self):
        """
        Re-filter the entire raw buffer from scratch.
        Called when any filter parameter changes so the filtered buffer stays consistent with the new settings.
        """
        self._write_idx = 0
        self._size = 0
        self._reset_filter_states()
        self._catch_up()

    def set_bpf_frequency(self, frequencies: Tuple[float, float]):
        self.bpf_b, self.bpf_a = signal.butter(4, frequencies, btype='bandpass', fs=self.fs)
        self._bpf_zi_base = signal.lfilter_zi(self.bpf_b, self.bpf_a)
        self.reprocess_all()

    def set_time_window(self, value: int):
        self.time_window_s = value
        # No reprocessing needed — only affects how much get_processed_window returns

    def enable_50_Hz_notch(self, enabled: bool):
        self.use_notch_50 = enabled
        self.reprocess_all()

    def enable_60_Hz_notch(self, enabled: bool):
        self.use_notch_60 = enabled
        self.reprocess_all()

    def enable_bpf(self, enabled: bool):
        self.use_bpf = enabled
        self.reprocess_all()