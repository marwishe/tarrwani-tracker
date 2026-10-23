"""Диалог подтверждения/сообщения в стиле приложения."""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect

from ui import theme
from ui.widgets.basic import Card, PillButton, label


class ConfirmDialog(QDialog):
    def __init__(self, parent, title, text, ok_text="ОК", cancel_text="Отмена", danger=False):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 24, 30, 40)   # место под тень

        card = Card(margins=(26, 24, 26, 22))
        card.setFixedWidth(380)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 180))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        card.body.addWidget(label(title, 20, theme.TEXT, 700))
        card.body.addWidget(label(text, 14, theme.TEXT_SECOND, 400, wrap=True))
        card.body.addSpacing(6)

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
        card.body.addLayout(buttons)

    def _center_on(self, parent) -> None:
        self.adjustSize()
        if parent is not None:
            center = parent.window().frameGeometry().center()
            self.move(center - QPoint(self.width() // 2, self.height() // 2))

    @staticmethod
    def ask(parent, title, text, ok_text="ОК", cancel_text="Отмена", danger=False) -> bool:
        dlg = ConfirmDialog(parent, title, text, ok_text, cancel_text, danger)
        dlg._center_on(parent)
        return dlg.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def info(parent, title, text, ok_text="Хорошо") -> None:
        dlg = ConfirmDialog(parent, title, text, ok_text, cancel_text=None)
        dlg._center_on(parent)
        dlg.exec()
