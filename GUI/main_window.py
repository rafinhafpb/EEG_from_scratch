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
from GUI.band_power_widget import BandPowerWidget
from GUI.band_detector_widget import BandDetectorWidget
from acquisition.simulate_acquisition import SignalGenerator
from signal_processing.signal_processor import SignalProcessor


class MainWindow(QMainWindow):
    def __init__(self, buffer: DataBuffer):
        super().__init__()

        self.buffer = buffer
        self.processor = SignalProcessor(self.buffer)
        self.setWindowTitle("EEG Application")
        self.setDockNestingEnabled(True)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._create_toolbar_button(os.path.join(base_dir, "icons/play.png"), self._start_acquisition)
        self._create_toolbar_button(os.path.join(base_dir, "icons/stop.png"), self._stop_acquisition)

        # Processing controls widget
        processing_control = ProcessingControls(self.processor)
        pc_dock = DockWidget("Signal Processing Control", processing_control)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, pc_dock)

        # Raw Signal Plotter
        self.signal_plotter = SignalPlotter(n_channels=self.buffer.n_channels)
        raw_plot_dock = DockWidget("Raw Signal", self.signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, raw_plot_dock)

        # Processed Signal Plotter
        self.processed_plotter = SignalPlotter(n_channels=self.buffer.n_channels)
        processed_plot_dock = DockWidget("Processed Signal", self.processed_plotter)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, processed_plot_dock)

        # FFT Widget
        self.fft_widget = FFTWidget(n_channels=self.buffer.n_channels, fs=self.buffer.fs)
        fft_dock = DockWidget("FFT Processed Signal", self.fft_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, fft_dock)

        # Band Power Widget
        self.band_power_widget = BandPowerWidget(self.buffer.n_channels)
        band_power_dock = DockWidget("Band Power", self.band_power_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, band_power_dock)

        # Band Detector Widget
        self.band_detector = BandDetectorWidget(self.buffer.n_channels, self.band_power_widget.band_names)
        band_detector_dock = DockWidget("Band Detector", self.band_detector)
        band_detector_dock.setMaximumHeight(150)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, band_detector_dock)

        # Organize into correct areas
        self.splitDockWidget(raw_plot_dock, band_detector_dock, Qt.Orientation.Horizontal)
        self.splitDockWidget(band_detector_dock, band_power_dock, Qt.Orientation.Horizontal)
        self.splitDockWidget(band_detector_dock, fft_dock, Qt.Orientation.Vertical)
        self.tabifyDockWidget(raw_plot_dock, processed_plot_dock)

        raw_plot_dock.raise_()

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
        if len(timestamps) == 0:
            return

        proc_data, ts = self.processor.get_processed_window()
        freqs, spectra = self.fft_widget.compute_fft_and_update_plot(proc_data)

        self.signal_plotter.update_plot(timestamps, raw_data)
        self.processed_plotter.update_plot(ts, proc_data)
        self.band_power_widget.update_plot(freqs, spectra)
        self.band_detector.detect(self.band_power_widget.get_band_powers())


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