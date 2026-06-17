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
        Pull unfiltered samples from the raw buffer and process them.
        Uses a single consistent snapshot of the raw buffer taken under
        its lock, then computes new samples by comparing the last filtered
        timestamp against the raw buffer's chronological sequence.
        """
        with self.buffer.lock:
            raw_write_idx = self.buffer.write_idx
            raw_size      = self.buffer.size
            raw_data      = self.buffer.data.copy()
            raw_ts        = self.buffer.timestamps.copy()

        if raw_size == 0:
            return

        # Reconstruct the raw buffer in chronological order
        if raw_size < self.buffer.max_samples:
            ordered_idx = np.arange(raw_size)
        else:
            ordered_idx = np.concatenate([
                np.arange(raw_write_idx, self.buffer.max_samples),
                np.arange(0, raw_write_idx)
            ])

        ordered_ts   = raw_ts[ordered_idx]
        ordered_data = raw_data[:, ordered_idx]

        # Find how many of these samples are newer than the last one we filtered
        if self._filtered.size == 0:
            # Nothing filtered yet — process everything
            new_data = ordered_data
            new_ts   = ordered_ts
        else:
            # Get the timestamp of the last sample we already filtered
            last_filtered_ts = self._get_last_filtered_ts()

            # Find all raw samples strictly newer than that
            mask = ordered_ts > last_filtered_ts
            if not np.any(mask):
                return

            new_data = ordered_data[:, mask]
            new_ts   = ordered_ts[mask]

        if new_data.shape[1] == 0:
            return

        filtered = self._apply_filters(new_data)
        self._filtered.add_chunk(filtered, new_ts)


    def _get_last_filtered_ts(self) -> float:
        """Return the timestamp of the most recently written filtered sample."""
        last_idx = (self._filtered.write_idx - 1) % self._filtered.max_samples
        return self._filtered.timestamps[last_idx]

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