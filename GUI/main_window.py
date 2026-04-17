import os
from PySide6.QtWidgets import QMainWindow, QApplication, QToolBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

# To run this module, use the command to execute it from the project root:
#    python -m GUI.main_window
from buffer.data_buffer import DataBuffer
from GUI.signal_visualization import SignalPlotter
from GUI.dock_widget import DockWidget
from GUI.processing_controls import ProcessingControls
from GUI.fft_plotter_widget import FFTWidget
from acquisition.simulate_acquisition import SignalGenerator
from signal_processing.signal_processor import SignalProcessor


class MainWindow(QMainWindow):
    def __init__(self, buffer: DataBuffer):
        super().__init__()

        self.buffer = buffer
        self.processor = SignalProcessor(self.buffer)
        self.setWindowTitle("EEG Application")
        self.setMinimumWidth(600)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._create_toolbar_button(os.path.join(base_dir, "icons/play.png"), self._start_acquisition)
        self._create_toolbar_button(os.path.join(base_dir, "icons/stop.png"), self._stop_acquisition)

        # Processing controls widget
        processing_control = ProcessingControls(self.processor)
        pc_dock = DockWidget("Signal Processing Control", processing_control)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, pc_dock)

        # Raw Signal Plotter
        self.signal_plotter = SignalPlotter(n_channels=self.buffer.n_channels)
        raw_plot_dock = DockWidget("Raw Signal", self.signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, raw_plot_dock)

        # Processed Signal Plotter
        self.processed_plotter = SignalPlotter(n_channels=self.buffer.n_channels)
        processed_plot = DockWidget("Processed Signal", self.processed_plotter)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, processed_plot)

        # FFT Widget
        self.fft_widget = FFTWidget(n_channels=self.buffer.n_channels, fs=self.buffer.fs)
        fft_dock = DockWidget("FFT Processed Signal", self.fft_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, fft_dock)

        # Timer for real-time updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_signal_plots)
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

    def update_signal_plots(self):
        raw_data, timestamps = self.buffer.get_data()
        proc_data, ts = self.processor.get_processed_window()
        self.fft_widget.compute_fft_and_update_plot(proc_data)

        if len(timestamps) == 0:
            return

        self.signal_plotter.update_plot(timestamps, raw_data)
        self.processed_plotter.update_plot(ts, proc_data)


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