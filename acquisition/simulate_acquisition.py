import numpy as np
import time
from threading import Thread
import sys
from pathlib import Path
# Add parent directory to path to find buffer module
sys.path.insert(0, str(Path(__file__).parent.parent))
from buffer.data_buffer import DataBuffer

class SignalGenerator:
    def __init__(self, buffer: DataBuffer, fs: int = 250):
        self.buffer = buffer
        self.fs = fs
        self.dt = 1.0 / fs
        self.running = False

        self.t = 0.0

    def generate_sample(self):
        """Generate one sample for all channels"""

        # Alpha wave (10 Hz)
        alpha = np.sin(2 * np.pi * 10 * self.t)

        # Noise
        noise = np.random.normal(0, 0.5)

        # 50 Hz interference
        interference = 0.3 * np.sin(2 * np.pi * 50 * self.t)

        # Channel examples
        ch1 = alpha + noise + interference
        ch2 = 0.5 * alpha + np.random.normal(0, 0.5)

        return [ch1, ch2]

    def run(self):
        self.running = True
        while self.running:
            start_time = time.time()

            sample = self.generate_sample()
            timestamp = self.t

            self.buffer.add_sample(sample, timestamp)
            self.t += self.dt

            # maintain sampling rate
            elapsed = time.time() - start_time
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self):
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()


if __name__ == "__main__":
    buffer = DataBuffer(
        n_channels=2,
        max_samples=1000,
        sampling_rate=100
    )

    generator = SignalGenerator(buffer, fs=100)
    generator.start()

    try:
        while True:
            time.sleep(1)
            data, ts = buffer.get_data()

            print(f"Buffer size: {len(buffer)}")
            print(f"Last sample CH1: {data[0][-1]:.3f}")

    except KeyboardInterrupt:
        generator.stop()
        print("Simulation stopped.")