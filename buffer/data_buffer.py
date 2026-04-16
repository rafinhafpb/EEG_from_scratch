import numpy as np
from typing import Tuple, List
from threading import Lock

class DataBuffer:
    def __init__(self, n_channels: int, time_window_s: int, sampling_rate_Hz: int):
        self.n_channels = n_channels
        self.max_samples = time_window_s * sampling_rate_Hz
        self.fs = sampling_rate_Hz

        # Shape: (n_channels, max_samples)
        self.data = np.zeros((n_channels, self.max_samples), dtype=np.float32)
        self.timestamps = np.zeros(self.max_samples, dtype=np.float64)

        self.write_idx = 0
        self.size = 0

        self.lock = Lock()

    def add_sample(self, samples: List[float], timestamp: float) -> None:
        if len(samples) != self.n_channels:
            raise ValueError(f"Expected {self.n_channels} channels, got {len(samples)}")

        with self.lock:
            self.data[:, self.write_idx] = samples
            self.timestamps[self.write_idx] = timestamp

            self.write_idx = (self.write_idx + 1) % self.max_samples
            self.size = min(self.size + 1, self.max_samples)

    def _get_ordered_indices(self) -> np.ndarray:
        """Return indices in chronological order"""
        if self.size < self.max_samples:
            return np.arange(self.size)
        else:
            return np.concatenate((
                np.arange(self.write_idx, self.max_samples),
                np.arange(0, self.write_idx)
            ))

    def get_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns full buffer in chronological order"""
        with self.lock:
            idx = self._get_ordered_indices()
            return self.data[:, idx].copy(), self.timestamps[idx].copy()

    def get_window_samples(self, n_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """Returns last n_samples"""
        n_samples = min(n_samples, self.size)

        with self.lock:
            idx = self._get_ordered_indices()
            idx = idx[-n_samples:]
            return self.data[:, idx].copy(), self.timestamps[idx].copy()

    def get_window_time(self, time_s: float) -> Tuple[np.ndarray, np.ndarray]:
        """Returns last samples from given time"""
        n_samples = int(time_s * self.fs)
        return self.get_window_samples(n_samples)

    def is_full(self) -> bool:
        return self.size == self.max_samples

    def __len__(self):
        return self.size