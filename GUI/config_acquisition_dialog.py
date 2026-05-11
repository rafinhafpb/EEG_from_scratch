from PySide6.QtWidgets import QLabel, QPushButton, QDialog, QGridLayout, QVBoxLayout, QPlainTextEdit, QGroupBox, QComboBox, QMessageBox, QDialogButtonBox, QCheckBox, QApplication, QFrame
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon
from acquisition.config_acquisition import AcquisitionConfigurator
from utl.data import SAMPLE_RATE_OPTIONS, BAUDRATE_VALUES, GAIN_VALUES, AcquisitionParameters
import serial.tools.list_ports
import os

# To run this module, use the command to execute it from the project root:
#    python -m GUI.config_acquisition_dialog


class ConfigAcquisitionDialog(QDialog):
    parameters_selected = Signal(object)    # AcquisitionParameters

    def __init__(self):
        super().__init__()
        self.configurator: AcquisitionConfigurator = None

        self.setMinimumSize(QSize(300, 200))
        self.setWindowTitle("Acquisition Parameters")

        layout = QVBoxLayout()

        # ----- ESP32 Configuration -----
        groupbox_esp_config = QGroupBox("ESP32 Connection")

        container = QGridLayout()
        label_port = QLabel("Port: ")
        self.pt_port = QPlainTextEdit()
        self.pt_port.setEnabled(False)
        self.pt_port.setMaximumSize(QSize(150, 30))
        self.find_esp32_port()

        self.btn_detect_port = QPushButton()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.btn_detect_port.setIcon(QIcon(os.path.join(base_dir, "icons/reset.png")))
        self.btn_detect_port.setMaximumSize(QSize(25, 25))
        self.btn_detect_port.clicked.connect(self.find_esp32_port)

        label_baudrate = QLabel("Baudrate: ")

        self.combobox_baudrate = QComboBox()
        self.combobox_baudrate.addItems(str(b) for b in BAUDRATE_VALUES)
        self.combobox_baudrate.setCurrentIndex(0)     # Default = 115200

        btn_connect = QPushButton("Connect")
        btn_connect.clicked.connect(self.connect_to_esp32)

        self.label_connected = QLabel("No ESP connected")
        self.label_connected.setStyleSheet("color: red;")

        container.addWidget(label_port, 0, 0, 1, 1)
        container.addWidget(self.pt_port, 0, 1, 1, 1)
        container.addWidget(self.btn_detect_port, 0, 2, 1, 1)

        container.addWidget(label_baudrate, 1, 0, 1, 1)
        container.addWidget(self.combobox_baudrate, 1, 1, 1, 2)
        container.addWidget(btn_connect, 2, 0, 1, 3)
        container.addWidget(self.label_connected, 3, 0, 1, 3)
        groupbox_esp_config.setLayout(container)

        # ----- ADS1292R Configuration -----
        self.groupbox_adc_config = QGroupBox("ADC Configuration")
        self.groupbox_adc_config.setEnabled(False)

        container2 = QGridLayout()

        btn_test_impedance = QPushButton("Test Electrode Impedance")
        btn_test_impedance.clicked.connect(self._measure_impedance)

        self.label_ch1_impedance = QLabel("Ch1 not tested")
        self.label_ch2_impedance = QLabel("Ch2 not tested")
        
        self.label_ch1_impedance.setStyleSheet("color: #aa0000;")
        self.label_ch2_impedance.setStyleSheet("color: #aa0000;")

        horizontal_line = QFrame()
        horizontal_line.setFrameShape(QFrame.HLine)
        horizontal_line.setFrameShadow(QFrame.Sunken)

        label_sampling_rate = QLabel("Sample Rate: ")
        self.combobox_sampling_rate = QComboBox()
        self.combobox_sampling_rate.addItems([f"{fs} Hz" for fs in SAMPLE_RATE_OPTIONS])
        self.combobox_sampling_rate.setCurrentIndex(1)    # Default = 250 Hz

        label_gain = QLabel("Gain: ")
        self.combobox_gain = QComboBox()
        self.combobox_gain.addItems(str(g) for g in GAIN_VALUES)
        self.combobox_gain.setCurrentIndex(4)    # Default = 6

        self.cb_test_signal = QCheckBox("Test Signal")
        self.cb_lead_off_detect = QCheckBox("Lead-Off Detect")

        container2.addWidget(btn_test_impedance, 0, 0, 1, 2)
        container2.addWidget(self.label_ch1_impedance, 1, 0, 1, 1)
        container2.addWidget(self.label_ch2_impedance, 1, 1, 1, 1)
        container2.addWidget(horizontal_line, 2, 0, 1, 2)

        container2.addWidget(label_sampling_rate, 3, 0, 1, 1)
        container2.addWidget(self.combobox_sampling_rate, 3, 1, 1, 1)
        container2.addWidget(label_gain, 4, 0, 1, 1)
        container2.addWidget(self.combobox_gain, 4, 1, 1, 1)
        container2.addWidget(self.cb_test_signal, 5, 0, 1, 1)
        container2.addWidget(self.cb_lead_off_detect, 5, 1, 1, 1)

        self.groupbox_adc_config.setLayout(container2)

        # Add OK/Cancel buttons using QDialogButtonBox
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                          QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self._confirm)
        self.buttonBox.rejected.connect(self._cancel)
        
        layout.addWidget(groupbox_esp_config)
        layout.addWidget(self.groupbox_adc_config)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def find_esp32_port(self) -> None:
        """
        Auto-detects COM ports and add ESP32 port name in plaintext if found ("No ESP32 Found" otherwise).
        """
        port_name = ""

        # List all available serial ports
        ports = list(serial.tools.list_ports.comports())
        
        for port in ports:
            description = port.description.upper()
            # Check if "ESP32", "CP210x", "CH340", or similar is in the description
            if "ESP32" in description or "CP210X" in description or "CH340" in description:
                port_name = port.device

        if port_name == "":
            port_name = "No ESP32 Found"
        
        self.pt_port.setPlainText(port_name)

    def connect_to_esp32(self) -> None:
        try:
            self.configurator = AcquisitionConfigurator(
                self.pt_port.toPlainText(),
                BAUDRATE_VALUES[self.combobox_baudrate.currentIndex()]
            )

            self.groupbox_adc_config.setEnabled(True)
            self.label_connected.setText("ESP connected")
            self.label_connected.setStyleSheet("color: green;")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _measure_impedance(self):
        z_ch1, z_ch2 = self.configurator.measure_impedance()

        z1_k = z_ch1 / 1000
        z2_k = z_ch2 / 1000

        self.label_ch1_impedance.setText(f"Ch1: {z1_k:.1f} kΩ")
        self.label_ch2_impedance.setText(f"Ch2: {z2_k:.1f} kΩ")

        def impedance_color(z_k: float) -> str:
            if z_k <= 10:
                return "#00aa00"
            if z_k >= 15:
                return "#aa0000"
            if z_k <= 12.5:
                fraction = (z_k - 10) / 2.5
                r = int(255 * fraction)
                g = 170
            else:
                fraction = (z_k - 12.5) / 2.5
                r = 255
                g = int(170 * (1 - fraction))
            return f"rgb({r},{g},0)"

        self.label_ch1_impedance.setStyleSheet(f"color: {impedance_color(z1_k)}")
        self.label_ch2_impedance.setStyleSheet(f"color: {impedance_color(z2_k)}")

    def _confirm(self):
        if self.pt_port.toPlainText() == "":
            QMessageBox.critical(self, "Error", "ESP32 not connected (Port not found)")
            return
        
        acq_parameters = AcquisitionParameters(
            sample_rate = SAMPLE_RATE_OPTIONS[self.combobox_sampling_rate.currentIndex()],
            gain = GAIN_VALUES[self.combobox_gain.currentIndex()],
            test_signal = self.cb_test_signal.isChecked(),
            lead_off_detect = self.cb_lead_off_detect.isChecked()
        )

        self.parameters_selected.emit(acq_parameters)
        self.accept()

    def _cancel(self):
        if self.configurator:
            self.configurator.disconnect_serial()
            self.configurator = None

            self.groupbox_adc_config.setEnabled(False)
            self.label_connected.setText("No ESP connected")
            self.label_connected.setStyleSheet("color: red;")

        self.reject()


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    dialog = ConfigAcquisitionDialog()
    dialog.parameters_selected.connect(lambda *args: print(args))
    dialog.show()
    sys.exit(app.exec())


