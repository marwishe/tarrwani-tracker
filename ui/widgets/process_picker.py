"""Окно выбора из запущенных процессов (открывается по кнопке «+»)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QListWidget, QApplication,
)

from ui import theme
from ui.widgets.basic import PillButton, label, hint_label
from ui.widgets.dialogs import CardDialog


def running_process_names() -> list[str]:
    try:
        from core.process_tracker import ProcessTracker
        return ProcessTracker.get_unique_process_names()
    except Exception:
        return []


class ProcessPickerDialog(CardDialog):
    """Список запущенных процессов с поиском. Можно выбрать несколько."""

    def __init__(self, parent, exclude: list[str], initial_search: str = ""):
        super().__init__(parent, width=460, margins=(24, 22, 24, 22))
        body = self.card.body
        body.setSpacing(12)
        body.addWidget(label("Запущенные процессы", 20, theme.TEXT, 700))
        body.addWidget(hint_label("Выберите приложения, активность в которых нужно "
                                  "учитывать. Можно отметить несколько."))

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по имени")
        self._search.setFixedHeight(42)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid transparent; border-radius: 12px;
                font-size: 14px; padding: 0 14px;
                selection-background-color: {theme.ACCENT};
            }}
            QLineEdit:focus {{ border: 1px solid {theme.ACCENT}; }}
        """)
        self._search.textChanged.connect(self._apply_filter)
        self._search.returnPressed.connect(self.accept)
        body.addWidget(self._search)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._list.setFixedHeight(280)
        self._list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._list.setStyleSheet(theme.SCROLL_QSS + f"""
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{
                color: {theme.TEXT}; padding: 0 12px; height: 38px;
                border-radius: 10px; margin: 1px 0;
            }}
            QListWidget::item:hover {{ background: {theme.SURFACE_HOVER}; }}
            QListWidget::item:selected {{ background: {theme.SEGMENT_SEL}; color: #ffffff; }}
        """)
        self._list.itemSelectionChanged.connect(self._update_button)
        body.addWidget(self._list)

        self._empty = hint_label("")
        body.addWidget(self._empty)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        cancel = PillButton("Отмена", "secondary", height=42)
        cancel.clicked.connect(self.reject)
        self._ok = PillButton("Добавить", "primary", height=42)
        self._ok.setDefault(True)
        self._ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self._ok)
        body.addLayout(buttons)

        self._load(exclude)
        self._search.setText(initial_search)
        self._apply_filter()
        self._search.setFocus()

    def _load(self, exclude: list[str]) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            skip = {n.lower() for n in exclude}
            self._list.addItems([n for n in running_process_names() if n.lower() not in skip])
        finally:
            QApplication.restoreOverrideCursor()

    def _apply_filter(self) -> None:
        text = self._search.text().strip().lower()
        visible = 0
        for i in range(self._list.count()):
            item = self._list.item(i)
            hidden = text not in item.text().lower()
            item.setHidden(hidden)
            visible += 0 if hidden else 1

        if self._list.count() == 0:
            self._empty.setText("Не удалось получить список процессов. "
                                "Введите имя вручную и нажмите «Добавить».")
        elif visible == 0:
            self._empty.setText("Совпадений нет. Кнопка «Добавить» добавит введённое имя.")
        else:
            self._empty.setText("")
        self._empty.setVisible(bool(self._empty.text()))
        self._update_button()

    def _update_button(self) -> None:
        n = len(self._list.selectedItems())
        self._ok.setText(f"Добавить ({n})" if n else "Добавить")

    def result_names(self) -> list[str]:
        """Выбранные имена; если ничего не выбрано — введённый в поиск текст."""
        names = [item.text() for item in self._list.selectedItems()]
        if not names and self._search.text().strip():
            names = [self._search.text().strip()]
        return names

    @staticmethod
    def pick(parent, exclude: list[str], initial_search: str = "") -> list[str]:
        dlg = ProcessPickerDialog(parent, exclude, initial_search)
        dlg.center_on(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.result_names()
        return []
