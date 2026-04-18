import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from GUI.signal_visualization import plot_colors


class BandPowerWidget(QWidget):
    def __init__(self, n_channels: int):
        super().__init__()

        self.n_channels = n_channels

        # EEG bands
        self.bands = {
            "Delta": (0.5, 4),
            "Theta": (4, 8),
            "Alpha": (8, 12),
            "Beta": (12, 30),
            "Gamma": (30, 45),
        }

        self.band_names = list(self.bands.keys())
        self.n_bands = len(self.bands)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("EEG Band Power")
        self.plot_widget.setLabel('left', 'Normalized Power')
        self.plot_widget.setLabel('bottom', 'Bands')

        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # BarGraphItem for each channel
        self.bar_items = []

        for ch in range(self.n_channels):
            bar_width = 0.7 / self.n_channels
            offset = (ch - (self.n_channels - 1) / 2) * bar_width

            bg = pg.BarGraphItem(
                x = np.arange(self.n_bands) + offset,
                height = np.zeros(self.n_bands),
                width = bar_width,
                pen = pg.mkPen(color=plot_colors[ch % len(plot_colors)]),
                brush = pg.mkBrush(color=plot_colors[ch % len(plot_colors)])
            )
            self.plot_widget.addItem(bg)
            self.bar_items.append(bg)

        # Set x-axis labels
        ticks = [(i, name) for i, name in enumerate(self.band_names)]
        self.plot_widget.getAxis('bottom').setTicks([ticks])

    def update_plot(self, freqs: np.ndarray, spectra: np.ndarray):
        """
        `freqs`: fft frequencies\n
        `spectra`: fft spectrum, size (n_channels, n_freqs)
        """
        power = spectra ** 2
        band_powers = []

        for band_name, (f_low, f_high) in self.bands.items():
            mask = (freqs >= f_low) & (freqs <= f_high)

            # Mean power per channel in band
            band_power = np.mean(power[:, mask], axis=1)
            band_powers.append(band_power)

        band_powers = np.array(band_powers)

        # Normalize per channel
        total_power = np.sum(band_powers, axis=0, keepdims=True)
        normalized = band_powers / (total_power + 1e-8)

        # Update bars
        for ch in range(self.n_channels):
            heights = normalized[:, ch]
            offset = (ch - (self.n_channels - 1) / 2) * (0.7 / self.n_channels)

            self.bar_items[ch].setOpts(
                height = heights,
                x = np.arange(self.n_bands) + offset
            )