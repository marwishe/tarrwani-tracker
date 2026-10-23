"""Диалоги в стиле приложения: базовая карточка и подтверждение/сообщение."""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect

from ui import theme
from ui.widgets.basic import Card, PillButton, label


class CardDialog(QDialog):
    """Безрамочный диалог-карточка с тенью. Содержимое добавляется в self.card.body."""

    def __init__(self, parent, width: int = 380, margins=(26, 24, 26, 22)):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 24, 30, 40)   # место под тень

        self.card = Card(margins=margins)
        self.card.setFixedWidth(width)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

    def center_on(self, parent) -> None:
        self.adjustSize()
        if parent is not None:
            center = parent.window().frameGeometry().center()
            self.move(center - QPoint(self.width() // 2, self.height() // 2))


class ConfirmDialog(CardDialog):
    def __init__(self, parent, title, text, ok_text="ОК", cancel_text="Отмена", danger=False):
        super().__init__(parent)
        body = self.card.body
        body.addWidget(label(title, 20, theme.TEXT, 700))
        body.addWidget(label(text, 14, theme.TEXT_SECOND, 400, wrap=True))
        body.addSpacing(6)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        if cancel_text:
            cancel = PillButton(cancel_text, "secondary", height=42)
            cancel.clicked.connect(self.reject)
            buttons.addWidget(cancel)
        ok = PillButton(ok_text, "danger" if danger else "primary", height=42)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        body.addLayout(buttons)

    @staticmethod
    def ask(parent, title, text, ok_text="ОК", cancel_text="Отмена", danger=False) -> bool:
        dlg = ConfirmDialog(parent, title, text, ok_text, cancel_text, danger)
        dlg.center_on(parent)
        return dlg.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def info(parent, title, text, ok_text="Хорошо") -> None:
        dlg = ConfirmDialog(parent, title, text, ok_text, cancel_text=None)
        dlg.center_on(parent)
        dlg.exec()
