"""Невидимые полосы по краям окна для изменения размера."""

from PySide6.QtWidgets import QWidget


class SideGrip(QWidget):
    def __init__(self, parent, edges, cursor):
        super().__init__(parent)
        self._edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        handle = self.window().windowHandle()
        if handle is not None:
            handle.startSystemResize(self._edges)   # системное изменение размера
        event.accept()
