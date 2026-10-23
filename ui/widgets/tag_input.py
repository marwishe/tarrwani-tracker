"""Ввод списка имён процессов (например chrome.exe) с подсказками."""

from PySide6.QtCore import Qt, Signal, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QCompleter,
)

from ui import theme
from ui.icons import icon
from ui.widgets.basic import IconButton, ElidedLabel, label, clear_layout
from ui.widgets.process_picker import ProcessPickerDialog, running_process_names


class TagInput(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Имя процесса — Enter, или «+» для выбора")
        self._input.setFixedHeight(42)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid transparent; border-radius: 12px;
                font-size: 14px; padding: 0 14px;
                selection-background-color: {theme.ACCENT};
            }}
            QLineEdit:focus {{ border: 1px solid {theme.ACCENT}; }}
        """)
        self._input.returnPressed.connect(self._add_current)
        row.addWidget(self._input, 1)

        add_btn = IconButton("plus", 42, 20, "#ffffff", "#ffffff", bg=theme.ACCENT,
                             hover_bg=theme.ACCENT_HOVER)
        add_btn.setToolTip("Выбрать из запущенных процессов")
        add_btn.clicked.connect(self._open_picker)
        row.addWidget(add_btn)
        root.addLayout(row)

        self._list = QVBoxLayout()
        self._list.setSpacing(6)
        root.addLayout(self._list)

        self._setup_completer()
        self._rebuild()

    def _setup_completer(self) -> None:
        completer = QCompleter(QStringListModel(running_process_names(), self), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.popup().setStyleSheet(f"""
            QAbstractItemView {{
                background: {theme.CARD}; color: {theme.TEXT};
                border: 1px solid {theme.PILL_BORDER}; border-radius: 8px;
                selection-background-color: {theme.SEGMENT_SEL}; outline: none;
            }}
        """)
        completer.activated.connect(self._on_completer)
        self._input.setCompleter(completer)

    # ── Данные ─────────────────────────────────────────────────
    def get_tracked(self) -> list[str]:
        return list(self._selected)

    def set_tracked(self, names: list[str]) -> None:
        seen, unique = set(), []
        for name in names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique.append(name)
        self._selected = unique
        self._rebuild()

    def _add(self, name: str) -> None:
        name = name.strip()
        if name and name.lower() not in {n.lower() for n in self._selected}:
            self._selected.append(name)
            self._rebuild()
            self.changed.emit()

    def _add_current(self) -> None:
        self._add(self._input.text())
        self._input.clear()

    def _open_picker(self) -> None:
        """Окно со списком запущенных процессов; введённый текст — как поиск."""
        names = ProcessPickerDialog.pick(self, self._selected, self._input.text())
        for name in names:
            self._add(name)
        if names:
            self._input.clear()

    def _on_completer(self, text: str) -> None:
        self._add(text)
        QTimer.singleShot(0, self._input.clear)

    def _remove(self, name: str) -> None:
        self._selected = [n for n in self._selected if n != name]
        self._rebuild()
        self.changed.emit()

    # ── Список ─────────────────────────────────────────────────
    def _rebuild(self) -> None:
        clear_layout(self._list)

        if not self._selected:
            self._list.addWidget(label("Пока ничего не выбрано", 13, theme.TEXT_MUTED))
            return

        for name in self._selected:
            chip = QFrame()
            chip.setStyleSheet(f"QFrame {{ background: {theme.SURFACE}; border-radius: 12px; }}")
            row = QHBoxLayout(chip)
            row.setContentsMargins(14, 4, 6, 4)
            row.addWidget(ElidedLabel(name, 14, theme.TEXT), 1)
            rm = IconButton("close", 30, 14, theme.TEXT_MUTED, theme.DANGER)
            rm.setToolTip("Убрать")
            rm.clicked.connect(lambda _=False, n=name: self._remove(n))
            row.addWidget(rm)
            self._list.addWidget(chip)
