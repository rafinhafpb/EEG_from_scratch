import numpy as np
import pandas as pd
import threading
import time
from buffer.data_buffer import DataBuffer
import mne
from scipy.signal import resample_poly
from math import gcd
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
        self.time_start = 0
        self.elapsed_time = 0.0  # accumulate elapsed time across start/stop

        self.data = None
        self.labels = None
        self.fs = None

        self._load_file()

        # If no override: use original fs
        if self.target_fs is None:
            self.target_fs = self.fs

        # Minimum frequency to apply notch filter at 60 Hz
        if self.fs < 120:
            self.target_fs = 120

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
        values = df.values

        timestamps = values[:, 0]
        signals = values[:, 1:-1]
        labels = values[:, -1]

        self.data = signals.T.astype(np.float32)
        self.labels = labels

        # Estimate fs from total samples / total duration
        total_samples = len(timestamps)
        total_duration = timestamps[-1] - timestamps[0]

        if total_duration <= 0:
            raise ValueError("Timestamps are not monotonically increasing or file is too short.")

        original_fs = round(total_samples / total_duration)
        self.fs = original_fs

        print(f"[SignalLoader] CSV loaded | fs ≈ {original_fs} Hz")

        # Remove the DC component
        self.data = self.data - np.mean(self.data, axis=1, keepdims=True)

    def _load_edf(self):
        self.raw = mne.io.read_raw_edf(self.filepath, preload=True)

        self.fs = int(self.raw.info['sfreq'])
        self.data = self.raw.get_data().astype(np.float32)
        self.labels = None

        print(f"[SignalLoader] EDF loaded | fs = {self.fs} Hz")

    def resample_if_needed(self):
        if self.fs == self.target_fs:
            return

        print(f"[SignalLoader] Resampling {self.fs} to {self.target_fs} Hz")

        up = self.target_fs
        down = self.fs
        divisor = gcd(up, down)
        up //= divisor
        down //= divisor

        # resample_poly operates per channel (1D), so we loop
        resampled = np.stack([
            resample_poly(ch, up, down) for ch in self.data
        ], axis=0).astype(np.float32)

        # Resample labels
        if self.labels is not None:
            n_new = resampled.shape[1]
            n_old = self.data.shape[1]
            new_indices = np.round(np.linspace(0, n_old - 1, n_new)).astype(int)
            self.labels = np.array(self.labels)[new_indices]

        self.data = resampled
        self.fs = self.target_fs
        print(f"[SignalLoader] Resampling complete: {self.data.shape[1]} samples")

    def start(self):
        # start/resume: set new time origin but keep elapsed_time so timestamps continue
        self.time_start = time.time()
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join()

        # accumulate elapsed time so next start resumes timestamps
        if self.time_start:
            self.elapsed_time += time.time() - self.time_start
            self.time_start = 0

    def _run(self):
        n_samples = self.data.shape[1]
        dt = 1.0 / self.target_fs

        while self.running:
            sample = self.data[:, self.idx]
            now = time.time()
            # total elapsed time since first start across start/stop cycles
            timestamp = self.elapsed_time + (now - self.time_start)

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
        return self.labels[min(max(self.idx - 1, 0), len(self.labels)-1)]