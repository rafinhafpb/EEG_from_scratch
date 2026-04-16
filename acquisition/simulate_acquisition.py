import numpy as np
import time
from threading import Thread

# To run this module, use the command to execute it from the project root:
#    python -m acquisition.simulate_acquisition
from buffer.data_buffer import DataBuffer


class SignalGenerator:
    def __init__(self, buffer: DataBuffer, fs=250):
        self.buffer = buffer
        self.fs = fs
        self.dt = 1.0 / fs
        self.running = False

        self.t = 0.0
        self.n_channels = buffer.n_channels

        # Per-channel parameters randomized
        self.amplitudes = np.random.uniform(0.5, 1.5, self.n_channels)
        self.phases = np.random.uniform(0, 2*np.pi, self.n_channels)

    def generate_sample(self):
        """Generate one multi-channel sample"""
        samples = []

        for i in range(self.n_channels):
            # Alpha wave 10 Hz
            alpha = self.amplitudes[i] * np.sin(2 * np.pi * 10 * self.t + self.phases[i])

            # Noise
            noise = np.random.normal(0, 0.5)

            # 50 Hz interference
            interference = 0.2 * np.sin(2 * np.pi * 50 * self.t)

            value = alpha + noise + interference
            samples.append(value)

        return samples

    def run(self):
        self.running = True
        next_time = time.time()

        while self.running:
            sample = self.generate_sample()

            self.buffer.add_sample(sample, self.t)
            self.t += self.dt

            next_time += self.dt
            sleep_time = next_time - time.time()

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
        time_window_s=5,
        sampling_rate_Hz=100
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