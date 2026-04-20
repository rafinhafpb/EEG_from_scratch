from PySide6.QtWidgets import QLabel, QPushButton, QFileDialog, QDialog, QGridLayout, QVBoxLayout, QPlainTextEdit, QGroupBox, QHBoxLayout, QComboBox, QDialogButtonBox
from PySide6.QtCore import Signal, QSize
from typing import List

SAMPLE_RATE_OPTIONS = [
    160,
    240,
    320,
    400
]

class LoadFileDialog(QDialog):
    file_selected = Signal(str, int, list)     # file_path, sample_rate, selected_channels

    def __init__(self):
        super().__init__()
        self.file_path = ""

        layout = QVBoxLayout()

        groupbox_file_path = QGroupBox("File")

        container = QHBoxLayout()
        label_file_path = QLabel("File path: ")
        self.plaintex_file_path = QPlainTextEdit("Choose File")
        self.plaintex_file_path.setMaximumSize(QSize(250, 26))

        self.button_file_path = QPushButton("...")
        self.button_file_path.setMaximumSize(QSize(30, 25))
        self.button_file_path.clicked.connect(self._open_file)

        container.addWidget(label_file_path)
        container.addWidget(self.plaintex_file_path)
        container.addWidget(self.button_file_path)
        groupbox_file_path.setLayout(container)

        groupbox_config = QGroupBox("Configuration")

        container2 = QGridLayout()
        label_sampling_rate = QLabel("Sampling Rate: ")
        self.combobox_sampling_rate = QComboBox()
        self.combobox_sampling_rate.addItem("Default (from file)")
        self.combobox_sampling_rate.addItems([f"{fs} Hz" for fs in SAMPLE_RATE_OPTIONS])

        label_channel_select = QLabel("Channels: ")
        self.plaintex_channel = QPlainTextEdit("Default (all channels from file)")
        self.plaintex_channel.setMaximumSize(QSize(250, 26))
        self.plaintex_channel.setToolTip("Examples:\nC3, C4, O1, O2 (if .edf file)\n1, 2, 3 (if .csv file)")

        container2.addWidget(label_sampling_rate, 0, 0, 1, 1)
        container2.addWidget(self.combobox_sampling_rate, 0, 1, 1, 1)
        container2.addWidget(label_channel_select, 1, 0, 1, 1)
        container2.addWidget(self.plaintex_channel, 1, 1, 1, 1)

        groupbox_config.setLayout(container2)

        # Add OK/Cancel buttons using QDialogButtonBox
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                          QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self._confirm)
        self.buttonBox.rejected.connect(self.reject)
        
        layout.addWidget(groupbox_file_path)
        layout.addWidget(groupbox_config)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def _confirm(self):
        self.file_selected.emit(
            self.file_path,
            self._validate_sample_rate(),
            self._validade_channel_selection()
        )
        self.accept()

    def _validate_sample_rate(self) -> int:
        index = self.combobox_sampling_rate.currentIndex()
        fs = 0
        if index > 0:
            fs = SAMPLE_RATE_OPTIONS[index - 1]

        return fs
    
    def _validade_channel_selection(self) -> List[str]:
        text = self.plaintex_channel.toPlainText().strip()

        if text.startswith("Default") or text == "":
            return []  # empty list = all channels

        return [ch.strip() for ch in text.split(',')]

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "CSV Files (*.csv);;EDF Files (*.edf);;All Files (*)"
        )
        if file_path:
            self.plaintex_file_path.setPlainText(file_path)
            self.file_path = file_path
