import numpy as np
import pandas as pd
import threading
import time
from buffer.data_buffer import DataBuffer
import mne
from typing import List


class EEGRecordingLoader:
    def __init__(self, filepath: str, target_fs: int = None, loop: bool = True):
        super().__init__()

        self.buffer: DataBuffer = None
        self.filepath = filepath
        self.target_fs = target_fs
        self.loop = loop

        self.running = False
        self.thread = None
        self.idx = 0

        self.data = None
        self.labels = None
        self.original_fs = None

        self._load_file()

        # If no override → use original fs
        if self.target_fs is None:
            self.target_fs = self.original_fs

        self.resample_if_needed()

    def set_buffer(self, buffer: DataBuffer):
        self.buffer = buffer

    def select_channels(self, channel_names: List[str]):
        if not channel_names:
            return

        if self.filepath.endswith(".csv"):
            indices = [int(ch) for ch in channel_names if ch.isdigit()]
            if not indices:
                raise ValueError("CSV channels must be numeric indices")
            self.data = self.data[indices]

        elif self.filepath.endswith(".edf"):
            indices = [self.raw.ch_names.index(ch) for ch in channel_names]
            self.data = self.data[indices]

    def _load_file(self):
        if self.filepath.endswith(".csv"):
            self._load_csv()
        elif self.filepath.endswith(".edf"):
            self._load_edf()
        else:
            raise ValueError("Unsupported file format")

    def _load_csv(self):
        df = pd.read_csv(self.filepath, header=None)

        # Assume: timestamp, ch1, ch2, ..., label
        values = df.values

        timestamps = values[:, 0]
        signals = values[:, 1:-1]
        labels = values[:, -1]

        # Transpose to (n_channels, n_samples)
        self.data = signals.T.astype(np.float32)
        self.labels = labels

        # Estimate sampling rate
        dt = np.diff(timestamps)
        dt = dt[dt > 0]  # remove duplicates
        self.original_fs = int(1.0 / np.mean(dt))

        print(f"[SignalLoader] CSV loaded | fs ≈ {self.original_fs} Hz")

        # For this file specifically, to transform into mV:
        self.data = (self.data - np.mean(self.data, axis=1, keepdims=True)) / 1000

    def _load_edf(self):
        self.raw = mne.io.read_raw_edf(self.filepath, preload=True)

        self.original_fs = int(self.raw.info['sfreq'])
        self.data = self.raw.get_data().astype(np.float32)
        self.labels = None

        print(f"[SignalLoader] EDF loaded | fs = {self.original_fs} Hz")

    def resample_if_needed(self, target_fs: int = None):
        if self.original_fs == self.target_fs and target_fs is None:
            return

        if target_fs is not None:
            self.target_fs = target_fs

        print(f"[SignalLoader] Resampling {self.original_fs} to {self.target_fs} Hz")

        n_samples = self.data.shape[1]
        duration = n_samples / self.original_fs

        new_n_samples = int(duration * self.target_fs)

        new_time = np.linspace(0, duration, new_n_samples)
        old_time = np.linspace(0, duration, n_samples)

        resampled = []
        resampled_labels = []

        for ch in self.data:
            resampled.append(np.interp(new_time, old_time, ch))

        # Resample labels by nearest-neighbor interpolation
        if self.labels is not None:
            labels_array = np.array(list(self.labels))
            new_indices = np.linspace(0, n_samples - 1, new_n_samples)
            resampled_labels = labels_array[np.round(new_indices).astype(int)]
            self.labels = resampled_labels

        self.data = np.array(resampled, dtype=np.float32)
        print(f"[SignalLoader] Resampling complete")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run(self):
        n_samples = self.data.shape[1]
        dt = 1.0 / self.target_fs

        while self.running:
            sample = self.data[:, self.idx]
            timestamp = time.time()

            if self.buffer is not None:
                self.buffer.add_sample(sample.tolist(), timestamp)

            self.idx += 1
            if self.idx >= n_samples:
                if self.loop:
                    self.idx = 0
                else:
                    break

            time.sleep(dt)

    def get_current_label(self):
        return self.labels[self.idx]