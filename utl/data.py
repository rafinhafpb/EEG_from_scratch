from dataclasses import dataclass


@dataclass
class AcquisitionParameters:
    port: str
    baudrate: int
    sample_rate: int
    gain: int
    test_signal: bool
    lead_off_detect: bool


BAUDRATE_VALUES = [
    115200,
    230400,
    250000,
    500000
]

GAIN_VALUES = [1, 2, 3, 4, 6, 8, 12]

SAMPLE_RATE_OPTIONS = [
    125,
    250,
    500,
    1000,
    2000
]

# address 0x01
sps_to_ADC_value = {
    125: 0x00,
    250: 0x01,
    500: 0x02,
    1000: 0x03,
    2000: 0x04
}

# address 0x04 and 0x05
gain_to_ADC_value = {
    1: 0x01,
    2: 0x02,
    3: 0x03,
    4: 0x04,
    6: 0x00,
    8: 0x05,
    12: 0x06
}