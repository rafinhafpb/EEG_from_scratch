import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
import numpy as np

plot_colors = [
    "#FF0000",
    "#FF5E00",
    "#FFE600",
    "#00E732",
    "#00D8E4",
    "#4433FF",
    "#8900EB",
    "#FF0080"
]

class SignalPlotter(QWidget):
    def __init__(self, n_channels: int):
        super().__init__()
        self.n_channels = n_channels
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Main graphics layout
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)
        self.setLayout(layout)

        self.plots = []
        self.curves = []

        for i in range(self.n_channels):
            # Create a new PlotItem (row)
            plot = self.graphics_layout.addPlot(row=i, col=0)
            plot.setLabel('left', f'Ch {i+1}')
            if i == self.n_channels - 1:
                plot.setLabel('bottom', 'Time (s)')

            # Link X axis (shared time axis)
            if i > 0:
                plot.setXLink(self.plots[0])

            # Create curve
            pen = pg.mkPen(color=plot_colors[i % len(plot_colors)], width=1)
            curve = plot.plot(pen=pen)

            self.plots.append(plot)
            self.curves.append(curve)

    def update_plot(self, timestamps: np.ndarray, data: np.ndarray):
        """
        timestamps: shape (n_samples,)
        data: shape (n_channels, n_samples)
        """
        if data.shape[0] != self.n_channels:
            raise ValueError(f"Expected {self.n_channels} channels, got {data.shape[0]}")

        for i in range(self.n_channels):
            self.curves[i].setData(timestamps, data[i])

    def clear_plot(self):
        for plot in self.plots:
            plot.clear()