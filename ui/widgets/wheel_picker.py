"""Колесо выбора числа (как «ч / мин / сек» на экране таймера)."""

import math

from PySide6.QtCore import (
    Qt, Signal, QRectF, QPointF, QPropertyAnimation, QEasingCurve, Property,
)
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget

from ui import theme
from ui.theme import make_font, mix


class WheelPicker(QWidget):
    """Вертикальное колесо. Крутится мышью, колесиком, стрелками; клик по соседней
    строке переходит к ней. wrap=True — значения идут по кругу (59 -> 00)."""

    value_changed = Signal(int)

    ROW_H = 40
    ROWS = 5

    def __init__(self, minimum: int, maximum: int, value: int | None = None,
                 unit: str = "", wrap: bool = False, width: int = 124, parent=None):
        super().__init__(parent)
        self._min, self._max = minimum, maximum
        self._n = maximum - minimum + 1
        self._unit = unit
        self._wrap = wrap

        start = (value if value is not None else minimum) - minimum
        self._pos = float(start)      # текущая (дробная) позиция — меняется при анимации
        self._target = int(start)     # целевая строка
        self._press_y = None
        self._press_pos = 0.0
        self._moved = False
        self._wheel_acc = 0

        self.setFixedSize(width, self.ROW_H * self.ROWS)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._anim = QPropertyAnimation(self, b"scrollPos", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── Анимируемое свойство ───────────────────────────────────
    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, value: float) -> None:
        self._pos = value
        self.update()

    scrollPos = Property(float, _get_pos, _set_pos)

    # ── Значение ───────────────────────────────────────────────
    def value(self) -> int:
        return self._min + (self._target % self._n)

    def set_value(self, value: int) -> None:
        """Установить значение без анимации и без сигнала."""
        value = max(self._min, min(self._max, int(value)))
        self._anim.stop()
        self._target = value - self._min
        self._pos = float(self._target)
        self.update()

    def _go_to(self, target: int) -> None:
        if not self._wrap:
            target = max(0, min(self._n - 1, target))
        changed = (target % self._n) != (self._target % self._n)
        self._target = target
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(float(target))
        self._anim.start()
        if changed:
            self.value_changed.emit(self.value())

    def _fmt(self, value: int) -> str:
        return f"{value:02d}"

    # ── Ввод ───────────────────────────────────────────────────
    def wheelEvent(self, event):
        self._wheel_acc += event.angleDelta().y()
        steps = int(self._wheel_acc / 120)
        if steps:
            self._wheel_acc -= steps * 120
            self._go_to(self._target - steps)   # колесо вниз -> следующее значение
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self._go_to(self._target - 1)
        elif event.key() == Qt.Key.Key_Down:
            self._go_to(self._target + 1)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._anim.stop()
            self._press_y = event.position().y()
            self._press_pos = self._pos
            self._moved = False
            self.setFocus()

    def mouseMoveEvent(self, event):
        if self._press_y is None:
            return
        dy = event.position().y() - self._press_y
        if abs(dy) > 4:
            self._moved = True
        if self._moved:
            pos = self._press_pos - dy / self.ROW_H
            if not self._wrap:
                pos = max(0.0, min(float(self._n - 1), pos))
            self._set_pos(pos)

    def mouseReleaseEvent(self, event):
        if self._press_y is None:
            return
        if self._moved:
            self._go_to(round(self._pos))
        else:
            offset = round((event.position().y() - self.height() / 2) / self.ROW_H)
            self._go_to(self._target + offset)
        self._press_y = None

    # ── Отрисовка ──────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, cy = self.width(), self.height() / 2

        # подсветка выбранной строки
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SURFACE))
        p.drawRoundedRect(QRectF(0, cy - self.ROW_H / 2 + 2, w, self.ROW_H - 4), 12, 12)

        unit_font = make_font(14)
        unit_fm = QFontMetrics(unit_font)
        unit_w = unit_fm.horizontalAdvance(self._unit) + 6 if self._unit else 0

        base = math.floor(self._pos)
        for i in range(base - 3, base + 5):
            dist = i - self._pos
            a = abs(dist)
            if a > 2.5 or (not self._wrap and not 0 <= i < self._n):
                continue

            value = self._min + (i % self._n)
            y = cy + dist * self.ROW_H

            # размер и цвет зависят от удаления от центра
            size = 34 - 8 * min(a, 1.0) - 5 * max(0.0, min(a, 2.0) - 1.0)
            if a <= 1:
                color = mix(theme.TEXT, "#8e8e93", a)
            else:
                color = mix("#8e8e93", "#3f3f43", min(a - 1, 1.0))
            weight = QFont.Weight.DemiBold if a < 0.5 else QFont.Weight.Normal

            font = make_font(int(size), weight)
            fm = QFontMetrics(font)
            text = self._fmt(value)
            shift = -unit_w / 2 * max(0.0, 1 - a)   # выбранное число сдвигаем влево под «мин»
            baseline = y + (fm.ascent() - fm.descent()) / 2

            p.setFont(font)
            p.setPen(color)
            p.drawText(QPointF(w / 2 + shift - fm.horizontalAdvance(text) / 2, baseline), text)

            if unit_w and a < 0.7:
                uc = QColor(theme.TEXT_SECOND)
                uc.setAlphaF(max(0.0, 1 - a * 1.4))
                p.setFont(unit_font)
                p.setPen(uc)
                p.drawText(QPointF(w / 2 + shift + fm.horizontalAdvance(text) / 2 + 5, baseline),
                           self._unit)
