from PySide6.QtWidgets import QDockWidget, QWidget, QSizePolicy
from PySide6.QtCore import Qt

class DockWidget(QDockWidget):
    def __init__(
            self,
            title: str,
            widget: QWidget,
            features: QDockWidget.DockWidgetFeature = None,
            allowed_areas: Qt.DockWidgetArea = Qt.DockWidgetArea.AllDockWidgetAreas,
            size_policy = (QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ):
        super().__init__()
        self.setWindowTitle(title)
        self.setWidget(widget)
        
        if features != None:
            self.setFeatures(features)

        self.setAllowedAreas(allowed_areas)
        self.setSizePolicy(size_policy[0], size_policy[1])