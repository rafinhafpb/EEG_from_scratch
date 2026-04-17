from signal_processing.signal_processor import SignalProcessor
from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QLabel
from superqt import QRangeSlider
from PySide6.QtCore import Qt, QSize


class ProcessingControls(QWidget):
    def __init__(self, processor: SignalProcessor):
        super().__init__()
        self.processor = processor

        layout = QGridLayout()

        self.cb_50 = QCheckBox("Notch 50 Hz")
        self.cb_50.setMinimumSize(QSize(100, 25))
        self.cb_60 = QCheckBox("Notch 60 Hz")
        self.cb_60.setMinimumSize(QSize(100, 25))
        self.cb_bpf = QCheckBox("Band-pass Filter")
        self.cb_bpf.setMinimumSize(QSize(105, 25))

        self.cb_50.toggled.connect(self.processor.enable_50_Hz_notch)
        self.cb_60.toggled.connect(self.processor.enable_60_Hz_notch)
        self.cb_bpf.toggled.connect(self.processor.enable_bpf)

        self.label_bpf1 = QLabel("0.5 Hz")
        self.label_bpf1.setMinimumSize(QSize(45, 25))
        self.label_bpf2 = QLabel("40 Hz")
        self.label_bpf2.setMinimumSize(QSize(45, 25))

        self.min_gap = 24
        self.slider_bpf = QRangeSlider(Qt.Orientation.Horizontal)
        self.slider_bpf.setMinimumSize(QSize(100, 10))
        self.slider_bpf.setRange(0, 199)    # Values actually vary between 0.5-100
        self.slider_bpf.sliderMoved.connect(self._enforce_min_gap)
        self.slider_bpf.valueChanged.connect(self._update_labels)
        self.slider_bpf.sliderReleased.connect(self._bpf_slider_value_changed)
        self.slider_bpf.setValue((0, 79))   # Default 0.5-40 Hz
        self.slider_bpf.setEnabled(False)
        self.cb_bpf.toggled.connect(self.slider_bpf.setEnabled)

        # First row: 50 and 60 notch checkboxes
        layout.addWidget(self.cb_50, 0, 0, 1, 2)
        layout.addWidget(self.cb_60, 0, 2, 1, 2)

        # Second row: bpf checkbox, label min_value, slider, label max_value
        layout.addWidget(self.cb_bpf, 1, 0, 1, 1)
        layout.addWidget(self.label_bpf1, 1, 1, 1, 1)
        layout.addWidget(self.slider_bpf, 1, 2, 1, 1)
        layout.addWidget(self.label_bpf2, 1, 3, 1, 1)

        self.setLayout(layout)

    def _enforce_min_gap(self, value):
        low, high = value

        if high - low < self.min_gap:
            curr_low, _ = self.slider_bpf.value()

            if low > curr_low:  # inferior handle moved last
                self.slider_bpf.setValue((high - self.min_gap, high))
            else:               # superior handle moved last
                self.slider_bpf.setValue((low, low + self.min_gap))

    def _update_labels(self, value):
        low, high = value
        low = 0.5 + low / 2.0
        high = 0.5 + high / 2.0
        self.label_bpf1.setText(f"{str(low)} Hz")
        self.label_bpf2.setText(f"{str(high)} Hz")

    def _bpf_slider_value_changed(self):
        low, high = self.slider_bpf.value()
        low = 0.5 + low / 2.0
        high = 0.5 + high / 2.0
        self.processor.set_bpf_frequency((low, high))
