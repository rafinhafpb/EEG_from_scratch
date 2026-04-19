import numpy as np
import pandas as pd
import threading
import time
from buffer.data_buffer import DataBuffer
from collections import deque
import mne


class SignalLoader:
    def __init__(
        self,
        buffer: DataBuffer,
        filepath: str,
        target_fs: int,
        loop: bool = True
    ):
        self.buffer = buffer
        self.filepath = filepath
        self.target_fs = target_fs
        self.loop = loop

        self.running = False
        self.thread = None

        self.data = None  # shape: (n_channels, n_samples)
        self.labels = None

        self._load_file()
        self._resample_if_needed()

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

    def _load_edf(self):
        if mne is None:
            raise ImportError("Install mne to use EDF files")

        raw = mne.io.read_raw_edf(self.filepath, preload=True)

        self.original_fs = int(raw.info['sfreq'])
        data = raw.get_data()  # (n_channels, n_samples)

        self.data = data.astype(np.float32)
        self.labels = None

        print(f"[SignalLoader] EDF loaded | fs = {self.original_fs} Hz")

    def _resample_if_needed(self):
        if self.original_fs == self.target_fs:
            return

        print(f"[SignalLoader] Resampling {self.original_fs} → {self.target_fs} Hz")

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
            self.labels = deque(resampled_labels)

        self.data = np.array(resampled, dtype=np.float32)

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
        idx = 0
        n_samples = self.data.shape[1]

        dt = 1.0 / self.target_fs

        while self.running:
            sample = self.data[:, idx]

            timestamp = time.time()
            self.buffer.add_sample(sample.tolist(), timestamp)
            print(self.labels.popleft())

            idx += 1

            if idx >= n_samples:
                if self.loop:
                    idx = 0
                else:
                    break

            time.sleep(dt)