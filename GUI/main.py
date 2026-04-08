from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QApplication
from PySide6.QtCore import Qt
from signal_visualization import SignalPlotter
from dock_widget import DockWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEG Application")
        self.setMinimumWidth(400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Test EEG Analysis")
        layout.addWidget(label)
        
        # Buttons
        btn_start = QPushButton("Start Recording")
        btn_stop = QPushButton("Stop Recording")
        btn_analyze = QPushButton("Analyze Data")

        # btn_start.clicked.connect()
        
        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)
        layout.addWidget(btn_analyze)
        
        central_widget.setLayout(layout)

        signal_plotter = SignalPlotter()

        # signal_plotter.plot_signal()

        dock_widget = DockWidget("Signal Plotter", signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_widget)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()