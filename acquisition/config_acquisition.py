from utl.data import AcquisitionParameters
import serial
from typing import List
import time
import threading
from utl.data import sps_to_ADC_value, gain_to_ADC_value
from buffer.data_buffer import DataBuffer

# Commands as byte lists
SDATAC  = [0x11]
RDATAC  = [0x10]
START   = [0x08]
STOP    = [0x0A]

# 9 bytes per frame: 3 status + 3 ch1 + 3 ch2
FRAME_SIZE = 9

class AcquisitionConfigurator:
    def __init__(self, acquisition_parameters: AcquisitionParameters, buffer: DataBuffer):
        """Initialize serial connection to ESP32"""

        self.serial = serial.Serial(
            port = acquisition_parameters.port,
            baudrate = acquisition_parameters.baudrate,
            timeout = 1
        )
        time.sleep(1)   # Wait for ESP32 to reset

        self.sample_rate = acquisition_parameters.sample_rate
        self.gain = acquisition_parameters.gain
        self.test_signal = acquisition_parameters.test_signal
        self.lead_off_enabled = acquisition_parameters.lead_off_detect

        self.buffer = buffer
        self.n_channels = buffer.n_channels
        self.running = False
        self.thread = None


    def init_ads1292r(self):
        """Set ADC parameters and start """
        self._send_command(SDATAC)      # Stop continuous read so we can write registers
        time.sleep(0.05)                # Give ESP32 time to forward and ADS to process

        self._set_sample_rate(self.sample_rate)
        self._set_gain(self.gain)
        self._set_test_signal(self.test_signal)
        # self._set_lead_off(self.lead_off_enabled)

    def start(self):
        self.serial.reset_input_buffer()    # Flush any stale bytes
        
        self._send_command(RDATAC)     # Set continuous read
        time.sleep(0.01)
        self._send_command(START)
        time.sleep(0.01)

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

        self._send_command(STOP)
        self._send_command(SDATAC)
        time.sleep(0.01)

    def _run(self):
        while self.running:
            try:
                # Block until we have a full frame
                raw = self.serial.read(FRAME_SIZE)

                if len(raw) < FRAME_SIZE:
                    # Timeout with no data — just loop
                    continue

                # --- Parse status bytes (first 3) ---
                # Format: 1100 + LOFF_STAT[4:0] + GPIO[1:0] + 13 zeros
                # Byte 0: 0xC_ (top nibble should be 0xC)
                header = (raw[0] >> 4) & 0xF
                if header != 0xC:
                    # Frame sync lost — try to re-sync by reading byte by byte
                    self.serial.reset_input_buffer()
                    continue

                loff_stat = ((raw[0] & 0x0F) << 1) | ((raw[1] >> 7) & 0x01)
                gpio_data = (raw[1] >> 5) & 0x03

                # --- Parse channel data (signed 24-bit two's complement) ---
                ch1 = int.from_bytes(raw[3:6], byteorder='big', signed=True)
                ch2 = int.from_bytes(raw[6:9], byteorder='big', signed=True)

                # Convert to voltage (uV)
                # LSB weight = VREF / (2^23 - 1) / gain
                vref = 2.42  # volts (internal reference)
                lsb = vref / ((2**23 - 1) * self.gain) * 1e6  # in uV
                ch1_uv = ch1 * lsb
                ch2_uv = ch2 * lsb

                # Timestamp from system clock (seconds)
                timestamp = time.perf_counter()

                samples = [ch1_uv, ch2_uv][:self.n_channels]
                self.buffer.add_sample(samples, timestamp)

            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self.running = False
                break
            except Exception as e:
                print(f"Unexpected error in acquisition thread: {e}")

    def _send_command(self, data: List[int]):
        """Send a list of bytes to the ESP32"""
        self.serial.write(bytes(data))
        time.sleep(0.002)       # Small flush delay — important for multi-byte commands

    @staticmethod
    def _write_to_register(address: int, value: int):
        # WREG: 0x40|addr, num_regs-1 (0x00 = 1 reg), value
        return [0x40 | address, 0x00, value]
    
    def _set_sample_rate(self, sps: int):
        assert sps in sps_to_ADC_value, f"Invalid sample rate. Choose from {list(sps_to_ADC_value.keys())}"

        # Config1: address 0x01
        self._send_command(self._write_to_register(0x01, sps_to_ADC_value[sps]))

    def _set_gain(self, gain: int):
        assert gain in gain_to_ADC_value, f"Invalid gain. Choose from {list(gain_to_ADC_value.keys())}"

        val = gain_to_ADC_value[gain]
        # Test signal = MUX=101 = 0x05
        val |= 0x05 if self.test_signal else 0x00

        # Channel 1 Settings: address 0x04
        self._send_command(self._write_to_register(0x04, val))
        # Channel 2 Settings: address 0x05
        self._send_command(self._write_to_register(0x05, val))

    def _set_test_signal(self, enabled: bool):
        # Bit 7=1 (mandatory), bit 5=1 (internal ref)
        base = 0xA0

        # bit 6=lead-off enabled or not
        base |= 0x40 if self.lead_off_enabled else 0x00

        if enabled:
            base |= 0x03          # INT_TEST on, TEST_FREQ = 1Hz square wave

        # Config2: address 0x02
        self._send_command(self._write_to_register(0x02, base))

    def _set_lead_off(self, enabled: bool, current_ua: bool = False):
        # CONFIG2 is also written here to keep PDB_LOFF_COMP in sync
        # in case _set_test_signal wasn't called first
        base = 0xA0
        base |= (0x40 if enabled else 0x00)
        self._send_command(self._write_to_register(0x02, base))

        if enabled:
            loff_val = 0x10 | (0x08 if current_ua else 0x00)
            self._send_command(self._write_to_register(0x03, loff_val))
            self._send_command(self._write_to_register(0x07, 0x0F))
        else:
            self._send_command(self._write_to_register(0x03, 0x10))  # Default LOFF value
            self._send_command(self._write_to_register(0x07, 0x00))  # Disable all sensing