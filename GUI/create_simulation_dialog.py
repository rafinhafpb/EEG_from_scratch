from PySide6.QtWidgets import QLabel, QDialog, QGridLayout, QSpinBox, QComboBox, QDialogButtonBox
from PySide6.QtCore import Signal
from utl.data import SAMPLE_RATE_OPTIONS


class SimulationDialog(QDialog):
    parameters_selected = Signal(int, int, int)     # n_channels, time_window, sample_rate

    def __init__(self):
        super().__init__()

        layout = QGridLayout()

        label_sampling_rate = QLabel("Sampling Rate: ")
        self.combobox_sampling_rate = QComboBox()
        self.combobox_sampling_rate.addItems([f"{fs} Hz" for fs in SAMPLE_RATE_OPTIONS])

        label_n_channels = QLabel("Number of channels: ")
        self.sb_n_channels = QSpinBox()
        self.sb_n_channels.setRange(1, 16)
        self.sb_n_channels.setValue(2)

        label_time_window = QLabel("Time window (s): ")
        self.sb_time_window = QSpinBox()
        self.sb_time_window.setRange(1, 20)
        self.sb_time_window.setValue(10)

        # Add OK/Cancel buttons using QDialogButtonBox
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                          QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self._confirm)
        self.buttonBox.rejected.connect(self.reject)

        layout.addWidget(label_sampling_rate, 0, 0, 1, 1)
        layout.addWidget(self.combobox_sampling_rate, 0, 1, 1, 1)

        layout.addWidget(label_n_channels, 1, 0, 1, 1)
        layout.addWidget(self.sb_n_channels, 1, 1, 1, 1)

        layout.addWidget(label_time_window, 2, 0, 1, 1)
        layout.addWidget(self.sb_time_window, 2, 1, 1, 1)

        layout.addWidget(self.buttonBox, 3, 0, 1, 2)

        self.setLayout(layout)

    def _confirm(self):
        self.parameters_selected.emit(
            self.sb_n_channels.value(),
            self.sb_time_window.value(),
            SAMPLE_RATE_OPTIONS[self.combobox_sampling_rate.currentIndex()]
        )
        self.accept()
