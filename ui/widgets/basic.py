"""Базовые виджеты, из которых собран весь интерфейс."""

from PySide6.QtCore import (
    Qt, Signal, QSize, QRectF, QPropertyAnimation, QEasingCurve, Property,
)
from PySide6.QtGui import QPainter, QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QScrollArea, QAbstractButton, QComboBox, QSizePolicy,
)

from ui import theme
from ui.theme import make_font
from ui.icons import icon, pixmap


# ── Вспомогательные функции ────────────────────────────────────

def clear_layout(layout) -> None:
    """Удалить из layout все виджеты (и вложенные layout'ы)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def make_scroll(content: QWidget) -> QScrollArea:
    """Прокручиваемая область без рамки и с тонким скроллбаром."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(theme.SCROLL_QSS)
    scroll.setWidget(content)
    content.setAutoFillBackground(False)   # QScrollArea по умолчанию закрашивает фон
    return scroll


def centered(widget: QWidget, max_width: int) -> QWidget:
    """Поместить виджет в центральную колонку ограниченной ширины."""
    widget.setMaximumWidth(max_width)
    wrapper = QWidget()
    row = QHBoxLayout(wrapper)
    row.setContentsMargins(0, 0, 0, 0)
    row.addStretch(1)
    row.addWidget(widget, 100)
    row.addStretch(1)
    return wrapper


def label(text: str = "", size: int = 14, color: str = theme.TEXT,
          weight: int = 400, align=None, wrap: bool = False) -> QLabel:
    """QLabel с готовым стилем."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight}; background: transparent;"
    )
    if align is not None:
        lbl.setAlignment(align)
    lbl.setWordWrap(wrap)
    return lbl


def page_title(text: str) -> QLabel:
    return label(text, 32, theme.TEXT, 700)


def card_title(text: str) -> QLabel:
    return label(text, 17, theme.TEXT, 700)


def hint_label(text: str, align=None) -> QLabel:
    return label(text, 13, theme.TEXT_HINT, 400, align, wrap=True)


class ElidedLabel(QLabel):
    """Метка, которая обрезает длинный текст многоточием."""

    def __init__(self, text="", size=14, color=theme.TEXT, weight=QFont.Weight.Normal, parent=None):
        super().__init__(text, parent)
        self._font = make_font(size, weight)
        self._color = QColor(color)
        self.setFont(self._font)
        self.setMinimumWidth(10)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def sizeHint(self):
        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance(self.text()), fm.height() + 2)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setFont(self._font)
        p.setPen(self._color)
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)


# ── Карточка ───────────────────────────────────────────────────

class Card(QFrame):
    """Скруглённая карточка. Содержимое добавляется в self.body (QVBoxLayout)."""

    def __init__(self, title: str = "", margins=(22, 20, 22, 22), border: str = theme.CARD_BORDER,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.set_border(border)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(*margins)
        self.body.setSpacing(14)
        if title:
            self.body.addWidget(card_title(title))

    def set_border(self, color: str) -> None:
        self.setStyleSheet(
            f"#Card {{ background: {theme.CARD}; border: 1px solid {color};"
            f" border-radius: {theme.CARD_RADIUS}px; }}"
        )


# ── Кнопки ─────────────────────────────────────────────────────

_PILL_KINDS = {
    # kind: (фон, фон при наведении, цвет текста, рамка)
    "primary":   (theme.ACCENT, theme.ACCENT_HOVER, "#ffffff", "none"),
    "secondary": (theme.PILL_BTN, "#363639", theme.TEXT, f"1px solid {theme.PILL_BORDER}"),
    "danger":    (theme.DANGER_SOFT, theme.DANGER, theme.DANGER, "none"),
    "ghost":     ("transparent", theme.SURFACE_HOVER, theme.TEXT_SECOND, "none"),
}


class PillButton(QPushButton):
    """Кнопка-«таблетка» (как «Старт» и «Новый таймер» в дизайне)."""

    def __init__(self, text: str, kind: str = "primary", icon_name: str = "",
                 height: int = 46, parent=None):
        super().__init__(text, parent)
        self._height = height
        self._icon_name = icon_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(height)
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        bg, hover, fg, border = _PILL_KINDS[kind]
        self._fg = fg
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {fg}; border: {border};
                border-radius: {self._height // 2}px;
                font-size: 15px; font-weight: 700; padding: 0 26px;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ background: {theme.SURFACE}; color: {theme.TEXT_DISABLED}; border: none; }}
        """)
        self._refresh_icon()

    def set_icon_name(self, name: str) -> None:
        self._icon_name = name
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        if self._icon_name:
            self.setIcon(icon(self._icon_name, self._fg, 18))
            self.setIconSize(QSize(18, 18))
        else:
            self.setIcon(QIcon())   # без иконки


class IconButton(QPushButton):
    """Круглая кнопка с иконкой."""

    def __init__(self, name: str, size: int = 38, icon_size: int = 18,
                 color: str = theme.TEXT_SECOND, hover_color: str = theme.TEXT,
                 bg: str = "transparent", hover_bg: str = theme.SURFACE_HOVER,
                 radius: int = -1, parent=None):
        super().__init__(parent)
        self._name, self._icon_size = name, icon_size
        self._color, self._hover_color = color, hover_color
        self.setFixedSize(size, size)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        r = size // 2 if radius < 0 else radius
        self.setStyleSheet(f"""
            QPushButton {{ background: {bg}; border: none; border-radius: {r}px; }}
            QPushButton:hover {{ background: {hover_bg}; }}
            QPushButton:disabled {{ background: {theme.SURFACE}; }}
        """)
        self.setIcon(icon(name, color, icon_size))

    def set_icon_name(self, name: str) -> None:
        self._name = name
        self.setIcon(icon(name, self._color, self._icon_size))

    def enterEvent(self, event):
        self.setIcon(icon(self._name, self._hover_color, self._icon_size))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(icon(self._name, self._color, self._icon_size))
        super().leaveEvent(event)


# ── Переключатель вариантов (как «Цветовая тема» в настройках) ──

class Segmented(QFrame):
    """Группа взаимоисключающих пунктов. index = -1 — ничего не выбрано."""

    changed = Signal(int)

    def __init__(self, labels: list[str], index: int = 0, parent=None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setStyleSheet(f"#Segmented {{ background: {theme.SEGMENT_BG}; border-radius: 12px; }}")
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(4)

        self._buttons: list[QPushButton] = []
        for i, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {theme.TEXT_SECOND}; border: none;
                    border-radius: 9px; font-size: 14px; font-weight: 600; padding: 0 14px;
                }}
                QPushButton:hover {{ background: #363638; color: {theme.TEXT}; }}
                QPushButton:checked {{ background: {theme.SEGMENT_SEL}; color: #ffffff; }}
            """)
            btn.clicked.connect(lambda _=False, i=i: self.set_index(i, emit=True))
            row.addWidget(btn, 1)
            self._buttons.append(btn)
        self._index = -1
        self.set_index(index)

    def index(self) -> int:
        return self._index

    def set_index(self, index: int, emit: bool = False) -> None:
        self._index = index
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        if emit:
            self.changed.emit(index)


# ── Степпер «− 96 px +» ────────────────────────────────────────

class Stepper(QWidget):
    changed = Signal(int)

    def __init__(self, value: int = 1, minimum: int = 1, maximum: int = 99,
                 suffix: str = "", parent=None):
        super().__init__(parent)
        self._min, self._max, self._suffix = minimum, maximum, suffix
        self._value = value

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self._minus = IconButton("minus", 36, 20, theme.ACCENT, theme.ACCENT_HOVER)
        self._plus = IconButton("plus", 36, 20, theme.ACCENT, theme.ACCENT_HOVER)
        for btn in (self._minus, self._plus):
            btn.setAutoRepeat(True)
            btn.setAutoRepeatDelay(400)
            btn.setAutoRepeatInterval(80)
        self._minus.clicked.connect(lambda: self.set_value(self._value - 1, emit=True))
        self._plus.clicked.connect(lambda: self.set_value(self._value + 1, emit=True))

        self._lbl = label("", 16, theme.TEXT, 600, Qt.AlignmentFlag.AlignCenter)
        self._lbl.setFixedWidth(70)

        row.addWidget(self._minus)
        row.addWidget(self._lbl)
        row.addWidget(self._plus)
        self.set_value(value)

    def value(self) -> int:
        return self._value

    def set_value(self, value: int, emit: bool = False) -> None:
        value = max(self._min, min(self._max, int(value)))
        changed = value != self._value
        self._value = value
        self._lbl.setText(f"{value}{self._suffix}")
        self._minus.setEnabled(value > self._min)
        self._plus.setEnabled(value < self._max)
        if emit and changed:
            self.changed.emit(value)


# ── Переключатель on/off ───────────────────────────────────────

class ToggleSwitch(QAbstractButton):
    _W, _H, _D, _PAD = 48, 28, 22, 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_x = float(self._PAD)

        self._anim = QPropertyAnimation(self, b"thumbX", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._on_toggled)

    def _get_thumb_x(self) -> float:
        return self._thumb_x

    def _set_thumb_x(self, x: float) -> None:
        self._thumb_x = x
        self.update()

    thumbX = Property(float, _get_thumb_x, _set_thumb_x)

    def _end_x(self, checked: bool) -> float:
        return float(self._W - self._D - self._PAD) if checked else float(self._PAD)

    def _on_toggled(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb_x)
        self._anim.setEndValue(self._end_x(checked))
        self._anim.start()

    def setChecked(self, checked: bool) -> None:
        # при программной установке — без анимации
        super().setChecked(checked)
        self._anim.stop()
        self._thumb_x = self._end_x(checked)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.ACCENT if self.isChecked() else "#3a3a3d"))
        p.drawRoundedRect(QRectF(0, 0, self._W, self._H), self._H / 2, self._H / 2)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(self._thumb_x, (self._H - self._D) / 2, self._D, self._D))

    def sizeHint(self):
        return QSize(self._W, self._H)


# ── Выпадающий список ──────────────────────────────────────────

class Dropdown(QComboBox):
    """QComboBox в стиле дизайна (со стрелкой-шевроном)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QComboBox {{
                background: {theme.BG}; color: {theme.TEXT};
                border: 1px solid {theme.PILL_BORDER}; border-radius: 10px;
                font-size: 14px; padding: 0 34px 0 14px;
            }}
            QComboBox:focus, QComboBox:on {{ border: 1px solid {theme.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{
                background: {theme.CARD}; color: {theme.TEXT};
                border: 1px solid {theme.PILL_BORDER}; border-radius: 8px;
                selection-background-color: {theme.SEGMENT_SEL}; outline: none; padding: 4px;
            }}
        """)

    def wheelEvent(self, event):
        event.ignore()   # чтобы колесо мыши прокручивало страницу, а не список

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.drawPixmap(self.width() - 28, (self.height() - 16) // 2,
                     pixmap("chevron-down", theme.TEXT_SECOND, 16))
