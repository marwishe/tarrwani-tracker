"""Крупные тонкие цифры времени (как часы на главном экране).

Каждая цифра рисуется в ячейке одинаковой ширины, поэтому текст не «дрожит»
при смене секунд.
"""

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget, QSizePolicy

from ui import theme
from ui.theme import make_font


class BigTime(QWidget):
    def __init__(self, text="00:00:00", pixel_size=96, color=theme.TEXT,
                 weight=QFont.Weight.Light, parent=None):
        super().__init__(parent)
        self._text = text
        self._px = pixel_size
        self._color = QColor(color)
        self._weight = weight
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(pixel_size * 1.2))

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.updateGeometry()
            self.update()

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def _cell_widths(self, px: int) -> list[float]:
        fm = QFontMetrics(make_font(px, self._weight))
        digit = fm.horizontalAdvance("0")
        return [digit if ch.isdigit() else fm.horizontalAdvance(ch) for ch in self._text]

    def sizeHint(self) -> QSize:
        return QSize(int(sum(self._cell_widths(self._px))) + 8, self.height())

    def minimumSizeHint(self) -> QSize:
        return QSize(80, self.height())

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        total = sum(self._cell_widths(self._px))
        px = self._px
        if total > self.width() - 8:                 # узкое окно — уменьшаем шрифт
            px = max(12, int(self._px * (self.width() - 8) / total))

        widths = self._cell_widths(px)
        p.setFont(make_font(px, self._weight))
        p.setPen(self._color)

        x = (self.width() - sum(widths)) / 2
        for ch, cw in zip(self._text, widths):
            p.drawText(QRectF(x, 0, cw, self.height()), Qt.AlignmentFlag.AlignCenter, ch)
            x += cw
