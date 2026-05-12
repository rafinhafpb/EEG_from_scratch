from utl.data import AcquisitionParameters
import serial
from typing import List, Tuple
import numpy as np
import time
import threading
from utl.data import sps_to_ADC_value, gain_to_ADC_value
from buffer.data_buffer import DataBuffer

# Commands as byte lists
SDATAC = [0x11]
RDATAC = [0x10]
START = [0x08]
STOP = [0x0A]
RESET = [0x06]

# 9 bytes per frame: 3 status + 3 ch1 + 3 ch2
FRAME_SIZE = 9

class AcquisitionConfigurator:
    def __init__(self, port: str, baudrate: int):
        """Initialize serial connection to ESP32"""

        self.serial = serial.Serial(
            port = port,
            baudrate = baudrate,
            timeout = 1
        )
        time.sleep(1)   # Wait for ESP32 to reset

        self.sample_rate = None
        self.gain = None
        self.test_signal = None
        self.lead_off_enabled = None

        self.buffer = None
        self.n_channels = None
        self.running = False
        self.thread = None
        self._serial_lock = threading.Lock()

    def set_parameters(self, acquisition_parameters: AcquisitionParameters) -> None:
        self.sample_rate = acquisition_parameters.sample_rate
        self.gain = acquisition_parameters.gain
        self.test_signal = acquisition_parameters.test_signal
        self.lead_off_enabled = acquisition_parameters.lead_off_detect

    def set_buffer(self, buffer: DataBuffer) -> None:
        self.buffer = buffer
        self.n_channels = buffer.n_channels

    def disconnect_serial(self):
        self.serial.close()

    def measure_impedance(self) -> Tuple[float, float]:
        """
        Runs an impedance check on both electrodes and returns impedance estimates in ohms for each (z_ch1, z_ch2)
        """
        self._send_command(SDATAC)
        time.sleep(0.05)

        # CONFIG2: internal ref on (bit5), lead-off comparators on (bit6)
        self._send_command(self._write_to_register(0x02, 0xE0))

        # LOFF: AC lead-off (FLEAD_OFF=1 → bit0=1), 6nA current, default threshold
        # bit4 must be 1, bits[3:2]=00 → 6nA, bit0=1 → AC at fDR/4
        self._send_command(self._write_to_register(0x03, 0x11))

        # LOFF_SENS: enable all channels, both polarities
        self._send_command(self._write_to_register(0x07, 0x0F))

        # CH1SET and CH2SET: normal electrode input (MUX=0000), gain=1
        # Gain must be 1 to avoid saturating the PGA during impedance measurement
        self._send_command(self._write_to_register(0x04, 0x00))
        self._send_command(self._write_to_register(0x05, 0x00))

        # Set sample rate to 500 SPS → AC excitation at 125 Hz
        self._send_command(self._write_to_register(0x01, 0x02))

        # Collect data
        self._send_command(START)
        self._send_command(RDATAC)
        time.sleep(0.01)
        self.serial.reset_input_buffer()

        # Collect ~1 second of samples (500 frames at 500 SPS)
        n_samples = 500
        ch1_samples = []
        ch2_samples = []

        for _ in range(n_samples):
            raw = self.serial.read(FRAME_SIZE)
            if len(raw) < FRAME_SIZE:
                continue

            ch1 = int.from_bytes(raw[3:6], 'big', signed=True)
            ch2 = int.from_bytes(raw[6:9], 'big', signed=True)
            ch1_samples.append(ch1)
            ch2_samples.append(ch2)

        self._send_command(STOP)
        self._send_command(SDATAC)
        time.sleep(0.05)

        # 6nA = 6e-9 A (the ILEAD_OFF=00 setting)
        I_excitation = 6e-9

        z_ch1 = self.estimate_impedance(ch1_samples, I_excitation)
        z_ch2 = self.estimate_impedance(ch2_samples, I_excitation)

        return z_ch1, z_ch2

    def init_ads1292r(self):
        """Set ADC parameters and start """
        assert self.buffer is not None, "Buffer must be set before initializing ADS1292R"
        assert (self.sample_rate is not None
            and self.gain is not None
            and self.test_signal is not None
            and self.lead_off_enabled is not None
        ), "ADS1292R Parameters must be set before initializing"

        self._send_command(SDATAC)      # Stop continuous read so we can write registers
        time.sleep(0.05)                # Give ESP32 time to forward and ADS to process

        self._send_command(RESET)
        time.sleep(0.01)

        self._set_sample_rate(self.sample_rate)
        self._set_gain(self.gain)
        self._set_test_signal(self.test_signal)
        self._set_lead_off(self.lead_off_enabled)

        # Enable RLD: PDB_RLD=1, sense from CH2P and CH2N
        self._send_command(self._write_to_register(0x06, 0x2C))

        # Also need to tell RESP2 to use internal RLDREF (mid-supply)
        # bit1 = RLDREF_INT = 1, bit0 must be 1
        self._send_command(self._write_to_register(0x0A, 0x03))

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

                samples = [ch2_uv][:self.n_channels]
                self.buffer.add_sample(samples, timestamp)

            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self.running = False
                break
            except Exception as e:
                print(f"Unexpected error in acquisition thread: {e}")

    def _send_command(self, data: List[int]):
        """Send a list of bytes to the ESP32"""
        with self._serial_lock:
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
        # add test_signal enabled
        base |= (0x03 if self.test_signal else 0x00)
        self._send_command(self._write_to_register(0x02, base))

        if enabled:
            loff_val = 0x10 | (0x08 if current_ua else 0x00)
            self._send_command(self._write_to_register(0x03, loff_val))
            self._send_command(self._write_to_register(0x07, 0x0F))
        else:
            self._send_command(self._write_to_register(0x03, 0x10))  # Default LOFF value
            self._send_command(self._write_to_register(0x07, 0x00))  # Disable all sensing

    @staticmethod
    def estimate_impedance(samples: List, excitation_current_a: float) -> float:
        """
        Estimates impedance from raw ADC samples (ohm).
        Uses peak-to-peak amplitude of the AC component.
        """
        arr = np.array(samples, dtype=float)

        # Convert raw codes to volts
        # LSB = VREF / (2^23 - 1) / gain;  gain=1, VREF=2.42V
        vref = 2.42
        gain = 1
        lsb_volts = vref / ((2**23 - 1) * gain)
        arr_volts = arr * lsb_volts

        # Remove DC offset
        arr_volts -= np.mean(arr_volts)

        # Peak-to-peak voltage of the AC excitation tone
        v_pp = np.max(arr_volts) - np.min(arr_volts)

        # Peak amplitude (sinusoid: Vpeak = Vpp / 2)
        v_peak = v_pp / 2.0

        # Convert peak current to RMS for impedance calc
        # 6nA is the peak current; Z = V_peak / I_peak
        z_ohms = v_peak / excitation_current_a
        return z_ohms
    
    def activate_buzzer(self, value: bool):
        self._send_command([0xF0, 0x01 if value else 0x00])     # 0xF0 is outside ads's opcode commands