"""Плавающая нижняя панель навигации (иконки в «таблетке»)."""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect

from ui import theme
from ui.icons import pixmap


class NavBar(QWidget):
    changed = Signal(int)

    CELL_W, CELL_H, PAD = 58, 46, 6

    def __init__(self, items: list[tuple[str, str]], parent=None):
        """items — список (имя_иконки, подсказка)."""
        super().__init__(parent)
        self._items = items
        self._index = 0
        self._hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.PAD * 2 + self.CELL_W * len(items), self.PAD * 2 + self.CELL_H)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

    def set_index(self, index: int) -> None:
        self._index = index
        self.update()

    def _cell_rect(self, i: int) -> QRectF:
        return QRectF(self.PAD + i * self.CELL_W, self.PAD, self.CELL_W, self.CELL_H)

    def _index_at(self, x: float) -> int:
        i = int((x - self.PAD) // self.CELL_W)
        return i if 0 <= i < len(self._items) else -1

    # ── Мышь ───────────────────────────────────────────────────
    def mouseMoveEvent(self, event):
        i = self._index_at(event.position().x())
        if i != self._hover:
            self._hover = i
            self.setToolTip(self._items[i][1] if i >= 0 else "")
            self.update()

    def leaveEvent(self, event):
        self._hover = -1
        self.update()

    def mousePressEvent(self, event):
        i = self._index_at(event.position().x())
        if event.button() == Qt.MouseButton.LeftButton and i >= 0 and i != self._index:
            self._index = i
            self.update()
            self.changed.emit(i)

    # ── Отрисовка ──────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # корпус
        body = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(QColor("#343437"), 1))
        p.setBrush(QColor(theme.PILL))
        p.drawRoundedRect(body, body.height() / 2, body.height() / 2)

        for i, (name, _tip) in enumerate(self._items):
            cell = self._cell_rect(i)
            active = i == self._index

            if active or i == self._hover:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(theme.ACCENT_SOFT if active else "#303033"))
                p.drawRoundedRect(cell.adjusted(1, 0, -1, 0), cell.height() / 2, cell.height() / 2)

            pm = pixmap(name, theme.ACCENT if active else "#a1a1a6", 22)
            p.drawPixmap(int(cell.center().x() - 11), int(cell.center().y() - 11 - 2), pm)

            if active:   # точка под иконкой
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(theme.ACCENT))
                p.drawEllipse(QPointF(cell.center().x(), cell.bottom() - 7), 2.5, 2.5)
