"""Верхняя прозрачная полоса: перетаскивание окна и кнопки свернуть/развернуть/закрыть."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from ui import theme
from ui.icons import icon


class _CaptionButton(QPushButton):
    def __init__(self, name: str, hover_bg: str, parent=None):
        super().__init__(parent)
        self._name = name
        self.setFixedSize(46, 30)
        self.setIconSize(QSize(14, 14))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._hover_icon = "#ffffff"
        self.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )
        self.set_icon_name(name)

    def set_icon_name(self, name: str) -> None:
        self._name = name
        self.setIcon(icon(name, "#d0d0d4", 14))

    def enterEvent(self, event):
        self.setIcon(icon(self._name, "#ffffff", 14))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(icon(self._name, "#d0d0d4", 14))
        super().leaveEvent(event)


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.setFixedHeight(theme.TITLEBAR_H)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 8, 0)
        row.setSpacing(2)
        row.addStretch()

        self.btn_min = _CaptionButton("minimize", "#2c2c2e")
        self.btn_max = _CaptionButton("maximize", "#2c2c2e")
        self.btn_close = _CaptionButton("close", "#e5453a")
        for btn in (self.btn_min, self.btn_max, self.btn_close):
            row.addWidget(btn)

        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(window.toggle_maximize)
        self.btn_close.clicked.connect(window.close)

    def set_maximized(self, maximized: bool) -> None:
        self.btn_max.set_icon_name("restore" if maximized else "maximize")

    # ── Перетаскивание окна за пустую область ──────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        handle = self.window().windowHandle()
        if handle is not None and handle.startSystemMove():
            event.accept()
            return
        self._drag = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag"):
            self.window().move(event.globalPosition().toPoint() - self._drag)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_maximize()
