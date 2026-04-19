from PySide6.QtWidgets import QWidget, QComboBox, QGridLayout, QLabel, QSlider, QProgressBar
from typing import List
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap
import numpy as np
import os

# Base directory for accessing icons
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BandDetectorWidget(QWidget):
    """
    A widget for detecting if an EEG frequency band exceeds a threshold for a certain channel (or the average)
    when provided the DPS.\n
    Emits `trigger_signal` when the trigger state changes based on selected band power exceeding the threshold.
    """
    trigger_signal = Signal(bool)

    def __init__(self, n_channels: int, bands: List[str]):
        super().__init__()
        # Initialize selection indices and threshold
        self.selected_band_idx = 0
        self.selected_channel_idx = -1
        self.threshold = 1.0
        self.trigger = False

        layout = QGridLayout()

        # Labels for UI elements
        label_band_select = QLabel("Band: ")
        label_band_select.setMinimumSize(QSize(20, 15))
        label_channel_select = QLabel("Channel: ")
        label_channel_select.setMinimumSize(QSize(20, 15))
        label_threshold = QLabel("Threshold: ")
        label_threshold.setMinimumSize(QSize(20, 15))
        self.label_threshold_value = QLabel("")
        self.label_threshold_value.setMinimumSize(QSize(30, 15))

        # Trigger indicator label with icons
        self.label_trigger = QLabel(self)
        self.label_trigger.setFixedSize(QSize(30, 30))

        pixmap = QPixmap(os.path.join(BASE_DIR, "icons/green.png"))
        self.trigger_true_img = pixmap.scaled(self.label_trigger.width(), self.label_trigger.height(), Qt.AspectRatioMode.KeepAspectRatio)
        pixmap2 = QPixmap(os.path.join(BASE_DIR, "icons/red.png"))
        self.trigger_false_img = pixmap2.scaled(self.label_trigger.width(), self.label_trigger.height(), Qt.AspectRatioMode.KeepAspectRatio)

        self.label_trigger.setPixmap(self.trigger_false_img)

        # Progress bar for power visualization
        self.power_bar = QProgressBar()
        self.power_bar.setRange(0, 100)
        self.power_bar.setTextVisible(False)
        self.power_bar.setMaximumHeight(6)

        # Combo box for band selection
        self.list_bands = QComboBox()
        self.list_bands.addItems(bands)
        self.list_bands.currentIndexChanged.connect(self._update_band_idx)
        self.list_bands.setMinimumSize(QSize(100, 20))

        # Combo box for channel selection, including "All (Average)"
        self.list_channels = QComboBox()
        for i in range(n_channels + 1):
            if i == n_channels:
                self.list_channels.addItem("All (Average)")
            else:
                self.list_channels.addItem(f"Channel {i+1}")

        self.list_channels.currentIndexChanged.connect(self._update_channel_idx)
        self.list_channels.setMinimumSize(QSize(100, 20))

        # Slider for threshold adjustment
        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(1, 100)
        self.slider_threshold.setMinimumSize(QSize(25, 20))
        self.slider_threshold.valueChanged.connect(self._update_threshold)
        self.slider_threshold.setValue(100)
        # Set slider bar transparent
        self.slider_threshold.setStyleSheet("""
            QSlider::groove:horizontal {
                background: transparent;
                height: 8px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #aaa;
                width: 10px;
                margin: -5px 0;
                border-radius: 6px;
            }
        """)

        # Layout arrangement
        layout.addWidget(label_band_select, 0, 0, 1, 1)
        layout.addWidget(self.list_bands, 0, 1, 1, 3)

        layout.addWidget(label_channel_select, 1, 0, 1, 1)
        layout.addWidget(self.list_channels, 1, 1, 1, 3)

        layout.addWidget(label_threshold, 2, 0, 1, 1)
        layout.addWidget(self.power_bar, 2, 1, 1, 1)
        layout.addWidget(self.slider_threshold, 2, 1, 1, 1)
        layout.addWidget(self.label_threshold_value, 2, 2, 1, 1)
        layout.addWidget(self.label_trigger, 2, 3, 1, 1)

        self.setLayout(layout)

    def _update_threshold(self, value: int):
        self.threshold = value / 100
        self.label_threshold_value.setText(str(value / 100))

    def _update_band_idx(self, idx: int):
        self.selected_band_idx = idx

    def _update_channel_idx(self, idx: int):
        self.selected_channel_idx = idx

    def detect(self, band_power: np.ndarray):
        """
        Detect if the power in the selected band and channel exceeds the threshold.
        Updates the progress bar and trigger state.
        
        `band_power`: size (n_bands, n_channels)
        """
        if band_power.shape[0] != self.list_bands.count():
            raise ValueError(f"Band dimension mismatch. Expected {self.list_bands.count()}, got {band_power.shape[0]}")
        
        if band_power.shape[1] != self.list_channels.count() - 1:
            raise ValueError(f"Channel dimension mismatch. Expected {self.list_channels.count() - 1}, got {band_power.shape[1]}")
        
        # Calculate power: average if "All" selected, else specific channel
        if self.selected_channel_idx == self.list_channels.count() - 1:
            power = np.mean(band_power[self.selected_band_idx, :])
        else:
            power = band_power[self.selected_band_idx, self.selected_channel_idx]

        self.power_bar.setValue(int(power * 100))

        # Check if trigger state changed
        cur_trigger = power > self.threshold
        if cur_trigger != self.trigger:
            self.trigger = cur_trigger
            self.trigger_changed()

    def trigger_changed(self):
        """Update the trigger indicator icon and emit the signal."""
        if self.trigger:
            self.label_trigger.setPixmap(self.trigger_true_img)
        else:
            self.label_trigger.setPixmap(self.trigger_false_img)
        
        self.trigger_signal.emit(self.trigger)