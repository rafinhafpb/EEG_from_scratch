from PySide6.QtWidgets import QDockWidget, QWidget
from PySide6.QtCore import Qt

class DockWidget(QDockWidget):
    def __init__(
            self,
            title: str,
            widget: QWidget,
            features: QDockWidget.DockWidgetFeature = None,
            allowed_areas: Qt.DockWidgetArea = Qt.DockWidgetArea.AllDockWidgetAreas,
        ):
        super().__init__()
        self.setWindowTitle(title)
        self.setWidget(widget)
        
        if features != None:
            self.setFeatures(features)

        self.setAllowedAreas(allowed_areas)