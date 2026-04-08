import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

class SignalPlotter(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Amplitude')
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.plot_widget.setTitle('Signal Visualization')
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
    
    def plot_signal(self, x_data, y_data, pen='b', name='Signal'):
        """Plot signal data on the widget."""
        self.plot_widget.plot(x_data, y_data, pen=pen, name=name)
    
    def clear_plot(self):
        """Clear all data from the plot."""
        self.plot_widget.clear()