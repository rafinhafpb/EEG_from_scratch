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

        # Filtered buffer: same shape as raw buffer, reuses DataBuffer logic
        self._filtered = DataBuffer(
            n_channels=buffer.n_channels,
            time_window_s=buffer.time_window_s,
            sampling_rate_Hz=buffer.fs
        )

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
        n = self.buffer.n_channels
        self._notch50_state = [None] * n
        self._notch60_state = [None] * n
        self._bpf_state = [None] * n

    def _catch_up(self):
        """
        Pull any samples from the raw buffer that haven't been filtered
        yet and write them into the filtered buffer.
        Since both buffers are the same size, we compare their write_idx
        and size values directly to find the gap. We snapshot the raw
        buffer's internal state under its lock, then release immediately
        so we don't hold it during the (potentially slow) filter math.
        """
        with self.buffer.lock:
            raw_write_idx = self.buffer.write_idx
            raw_size = self.buffer.size
            raw_data = self.buffer.data.copy()
            raw_ts = self.buffer.timestamps.copy()

        if raw_size == 0:
            return

        flt_write_idx = self._filtered.write_idx
        flt_size = self._filtered.size
        max_samples = self.buffer.max_samples

        # How many samples in the raw buffer are newer than what we've filtered?
        if flt_size == 0:
            # Filtered buffer is empty: process everything currently in raw
            n_new = raw_size
        elif raw_write_idx > flt_write_idx:
            n_new = raw_write_idx - flt_write_idx
        elif raw_write_idx < flt_write_idx:
            # Raw buffer wrapped past the filtered write pointer
            n_new = (max_samples - flt_write_idx) + raw_write_idx
        else:
            # Pointers are equal: either nothing is new, or exactly one
            # full cycle of new data arrived
            n_new = raw_size - flt_size

        if n_new <= 0:
            return

        # Extract the n_new samples chronologically from the raw snapshot.
        # They are the ones immediately before raw_write_idx in the ring.
        start = (raw_write_idx - n_new) % max_samples

        if start + n_new <= max_samples:
            new_samples = raw_data[:, start:start + n_new]
            new_ts = raw_ts[start:start + n_new]
        else:
            cut = max_samples - start
            new_samples = np.concatenate([raw_data[:, start:], raw_data[:, :n_new - cut]], axis=1)
            new_ts = np.concatenate([raw_ts[start:], raw_ts[:n_new - cut]])

        filtered = self._apply_filters(new_samples)

        # Write new_samples into the filtered DataBuffer
        self._filtered.add_chunk(filtered, new_ts)

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
        Advance filtering to match the current raw buffer, then return
        the most recent time_window_s of filtered data.
        """
        self._catch_up()
        return self._filtered.get_window_time(self.time_window_s)

    def reprocess_all(self):
        """
        Throw away the filtered buffer contents and re-filter everything
        currently in the raw buffer from scratch. Called whenever a filter
        setting changes so the filtered buffer stays consistent.
        """
        self._filtered = DataBuffer(
            n_channels=self.buffer.n_channels,
            time_window_s=self.buffer.time_window_s,
            sampling_rate_Hz=self.buffer.fs
        )
        self._reset_filter_states()
        self._catch_up()

    def set_bpf_frequency(self, frequencies: Tuple[float, float]):
        self.bpf_b, self.bpf_a = signal.butter(4, frequencies, btype='bandpass', fs=self.fs)
        self._bpf_zi_base = signal.lfilter_zi(self.bpf_b, self.bpf_a)
        self.reprocess_all()

    def set_time_window(self, value: int):
        self.time_window_s = value

    def enable_50_Hz_notch(self, enabled: bool):
        self.use_notch_50 = enabled
        self.reprocess_all()

    def enable_60_Hz_notch(self, enabled: bool):
        self.use_notch_60 = enabled
        self.reprocess_all()

    def enable_bpf(self, enabled: bool):
        self.use_bpf = enabled
        self.reprocess_all()