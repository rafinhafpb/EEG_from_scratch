import os
from PySide6.QtWidgets import QMainWindow, QApplication, QToolBar, QMessageBox
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QAction, QIcon

from buffer.data_buffer import DataBuffer
from GUI.signal_visualization import SignalPlotter
from GUI.dock_widget import DockWidget
from GUI.processing_controls import ProcessingControls
from GUI.fft_plotter_widget import FFTWidget
from GUI.band_power_widget import BandPowerWidget
from GUI.band_detector_widget import BandDetectorWidget
from GUI.load_file_dialog import LoadFileDialog
from GUI.create_simulation_dialog import SimulationDialog
from GUI.config_acquisition_dialog import ConfigAcquisitionDialog
from utl.data import AcquisitionParameters
from acquisition.load_recording import EEGRecordingLoader
from acquisition.simulate_acquisition import SignalGenerator
from signal_processing.signal_processor import SignalProcessor

# To run this module, use the command to execute it from the project root:
#    python -m GUI.main_window

class MainWindow(QMainWindow):
    acquisition_started = Signal()
    acquisition_stopped = Signal()

    def __init__(self):
        super().__init__()

        self.buffer = None
        self.processor = None
        self.acquisition_source = None
        self.has_labels = False

        self.setWindowTitle("EEG Application")
        self.setDockNestingEnabled(True)
        self.setMinimumSize(QSize(800, 500))

        self.load_file_dialog = LoadFileDialog()
        self.simulation_dialog = SimulationDialog()
        self.acquisition_dialog = ConfigAcquisitionDialog()

        self.load_file_dialog.file_selected.connect(self._load_file)
        self.simulation_dialog.parameters_selected.connect(self._create_simulation)
        self.acquisition_dialog.parameters_selected.connect(self._set_acquisition_parameters)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._create_toolbar_button(
            icon_path=os.path.join(base_dir, "icons/open.png"),
            callback=self._open_load_file_dialog,
            tooltip="Open EEG Recording"
        )
        self._create_toolbar_button(
            icon_path=os.path.join(base_dir, "icons/graph.png"),
            callback=self._open_create_simulation_dialog,
            tooltip="Simulate Acquisition"
        )
        self._create_toolbar_button(
            icon_path=os.path.join(base_dir, "icons/signal.png"),
            callback=self._open_acquisition_config_dialog,
            tooltip="Configure Live Acquisition"
        )
        self.start_acq_buttom = self._create_toolbar_button(
            icon_path=os.path.join(base_dir, "icons/play.png"),
            callback=self._start_acquisition,
            tooltip="Start"
        )
        self.stop_acq_buttom = self._create_toolbar_button(
            icon_path=os.path.join(base_dir, "icons/stop.png"),
            callback=self._stop_acquisition,
            tooltip="Stop"
        )

        self.start_acq_buttom.setEnabled(False)
        self.stop_acq_buttom.setEnabled(False)

        # Timer for real-time updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_signal_plots)
        self.timer.setInterval(100)  # 10 FPS

    def _initialize_pipeline(self, buffer: DataBuffer):
        self.buffer = buffer
        self.processor = SignalProcessor(self.buffer)

        # Recreate all widgets that depend on buffer
        self._setup_visualization_widgets()

        self.start_acq_buttom.setEnabled(True)

    def _setup_visualization_widgets(self):
        n_channels = self.buffer.n_channels

        # Processing controls widget
        processing_control = ProcessingControls(self.processor)
        pc_dock = DockWidget("Signal Processing Control", processing_control)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, pc_dock)

        # Raw Signal Plotter
        self.signal_plotter = SignalPlotter(n_channels)
        raw_plot_dock = DockWidget("Raw Signal", self.signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, raw_plot_dock)

        # Processed Signal Plotter
        self.processed_plotter = SignalPlotter(n_channels)
        processed_plot_dock = DockWidget("Processed Signal", self.processed_plotter)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, processed_plot_dock)

        # FFT Widget
        self.fft_widget = FFTWidget(n_channels, fs=self.buffer.fs)
        fft_dock = DockWidget("FFT Processed Signal", self.fft_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, fft_dock)

        # Band Power Widget
        self.band_power_widget = BandPowerWidget(n_channels)
        band_power_dock = DockWidget("Band Power", self.band_power_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, band_power_dock)

        # Band Detector Widget
        self.band_detector = BandDetectorWidget(n_channels, self.band_power_widget.band_names, self.has_labels)
        band_detector_dock = DockWidget("Band Detector", self.band_detector)
        band_detector_dock.setMaximumHeight(150)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, band_detector_dock)

        # Organize into correct areas
        self.splitDockWidget(raw_plot_dock, band_detector_dock, Qt.Orientation.Horizontal)
        self.splitDockWidget(band_detector_dock, band_power_dock, Qt.Orientation.Horizontal)
        self.splitDockWidget(band_detector_dock, fft_dock, Qt.Orientation.Vertical)
        self.tabifyDockWidget(raw_plot_dock, processed_plot_dock)

        raw_plot_dock.raise_()

    def _create_toolbar_button(self, icon_path: str, callback, tooltip: str = None) -> QAction:
        action = QAction(QIcon(icon_path), "", self)
        action.triggered.connect(callback)
        if tooltip is not None:
            action.setToolTip(tooltip)

        self.toolbar.addAction(action)
        return action

    def _create_simulation(self, n_channels: int, time_window: int, fs: int):
        try:
            buffer = DataBuffer(
                n_channels=n_channels,
                time_window_s=time_window,
                sampling_rate_Hz=fs
            )
            self.acquisition_source = SignalGenerator(buffer, fs=fs)
            self._initialize_pipeline(buffer)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_file(self, filepath: str, fs_override: int, channels: list):
        try:
            loader = EEGRecordingLoader(
                filepath = filepath,
                target_fs = fs_override if fs_override > 0 else None
            )

            loader.select_channels(channels)
            data = loader.data
            fs = loader.target_fs

            buffer = DataBuffer(
                n_channels = data.shape[0],
                time_window_s = 10,
                sampling_rate_Hz = fs
            )

            loader.set_buffer(buffer)

            self.acquisition_source = loader
            self.has_labels = True
            self._initialize_pipeline(buffer)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _set_acquisition_parameters(self, acq_parameters: AcquisitionParameters):
        try:
            buffer = DataBuffer(
                n_channels = 1,
                time_window_s = 10,
                sampling_rate_Hz = acq_parameters.sample_rate
            )

            self.acquisition_dialog.configurator.set_buffer(buffer)
            self.acquisition_dialog.configurator.set_parameters(acq_parameters)
            self.acquisition_dialog.configurator.init_ads1292r()

            self.acquisition_source = self.acquisition_dialog.configurator
            self.has_labels = False
            self._initialize_pipeline(buffer)

            self.band_detector.trigger_signal.connect(self.acquisition_dialog.configurator.activate_buzzer)

        except AssertionError as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_load_file_dialog(self):
        self.load_file_dialog.exec()

    def _open_create_simulation_dialog(self):
        self.simulation_dialog.exec()

    def _open_acquisition_config_dialog(self):
        self.acquisition_dialog.exec()

    def _start_acquisition(self):
        if self.acquisition_source is None:
            return

        self.acquisition_source.start()
        self.timer.start()

        self.start_acq_buttom.setEnabled(False)
        self.stop_acq_buttom.setEnabled(True)

    def _stop_acquisition(self):
        if self.acquisition_source:
            self.acquisition_source.stop()

        self.timer.stop()

        self.start_acq_buttom.setEnabled(True)
        self.stop_acq_buttom.setEnabled(False)

    def update_signal_plots(self):
        raw_data, timestamps = self.buffer.get_data()
        if len(timestamps) == 0:
            return

        proc_data, ts = self.processor.get_processed_window()
        freqs, spectra = self.fft_widget.compute_fft(proc_data)
        self.fft_widget.update_plot(freqs, spectra)

        self.signal_plotter.update_plot(timestamps, raw_data)
        self.processed_plotter.update_plot(ts, proc_data)
        self.band_power_widget.update_plot(freqs, spectra)
        self.band_detector.detect(self.band_power_widget.get_band_powers())
        if self.has_labels:
            label = "Eyes closed" if self.acquisition_source.get_current_label() == 0 else "Eyes opened"
            self.band_detector.set_label(label)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())