import os
from PySide6.QtWidgets import QMainWindow, QApplication, QToolBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from signal_visualization import SignalPlotter
from dock_widget import DockWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEG Application")
        self.setMinimumWidth(400)

        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        
        # Add toolbar buttons with icon
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._create_toolbar_button(os.path.join(base_dir, "icons/play.png"), self._start_acquisition)
        self._create_toolbar_button(os.path.join(base_dir, "icons/stop.png"), self._stop_acquisition)

        signal_plotter = SignalPlotter()
        # signal_plotter.plot_signal()

        dock_widget = DockWidget("Signal Plotter", signal_plotter)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_widget)

    def _create_toolbar_button(self, icon_path: str, callback) -> None:
        """Create a toolbar button with icon and callback."""
        action = QAction(QIcon(icon_path), "", self)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)

    def _start_acquisition(self) -> None:
        print("Acq started")

    def _stop_acquisition(self) -> None:
        print("Acq stopped")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()