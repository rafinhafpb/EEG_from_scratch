import os
from PySide6.QtWidgets import QMainWindow, QApplication, QToolBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

# To run this module, use the command to execute it from the project root:
#    python -m GUI.main_window
from buffer.data_buffer import DataBuffer
from GUI.signal_visualization import SignalPlotter
from GUI.dock_widget import DockWidget
from acquisition.simulate_acquisition import SignalGenerator


class MainWindow(QMainWindow):
    def __init__(self, buffer: DataBuffer):
        super().__init__()

        self.buffer = buffer
        self.setWindowTitle("EEG Application")
        self.setMinimumWidth(600)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._create_toolbar_button(os.path.join(base_dir, "icons/play.png"), self._start_acquisition)
        self._create_toolbar_button(os.path.join(base_dir, "icons/stop.png"), self._stop_acquisition)

        # Plotter
        self.signal_plotter = SignalPlotter(n_channels=self.buffer.n_channels)
        dock_widget = DockWidget("Signal Plotter", self.signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_widget)

        # Timer for real-time updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.setInterval(100)  # 10 FPS

    def _create_toolbar_button(self, icon_path: str, callback) -> None:
        action = QAction(QIcon(icon_path), "", self)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)

    def _start_acquisition(self):
        print("Acq started")
        self.timer.start()

    def _stop_acquisition(self):
        print("Acq stopped")
        self.timer.stop()

    def update_plot(self):
        data, timestamp = self.buffer.get_data()

        if len(timestamp) == 0:
            return

        self.signal_plotter.update_plot(timestamp, data)


if __name__ == "__main__":
    fs = 250
    n_channels = 3

    # Create buffer
    buffer = DataBuffer(
        n_channels=n_channels,
        time_window_s=10,
        sampling_rate_Hz=fs
    )

    # Start simulated signal
    generator = SignalGenerator(buffer, fs=fs)
    generator.start()

    # Start GUI
    app = QApplication([])
    window = MainWindow(buffer)
    window.show()

    app.exec()
    generator.stop()