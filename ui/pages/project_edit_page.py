"""Форма создания / редактирования проекта.

Сигналы:
  sig_save(dict) — пользователь нажал «Сохранить», в словаре данные проекта
  sig_cancel()   — «Назад» или «Отмена»
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit,
    QPlainTextEdit, QPushButton,
)

from ui import theme
from ui.icons import icon
from ui.widgets.basic import (
    Card, PillButton, IconButton, Segmented, Stepper, ToggleSwitch, Dropdown,
    make_scroll, centered, label, page_title, hint_label, card_title,
)
from ui.widgets.wheel_picker import WheelPicker
from ui.widgets.tag_input import TagInput

COLUMN_W = 560

_PRESETS = [("25 / 5", 25, 5), ("52 / 17", 52, 17), ("90 / 30", 90, 30)]

_SCRIPT_TRIGGERS = [
    ("on_focus_end", "По окончании фокуса"),
    ("on_break_end", "По окончании перерыва"),
    ("on_timer_complete", "По завершении всего таймера"),
]


def _divider() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {theme.CARD_BORDER}; border: none;")
    return line


class _ScriptEntry(QWidget):
    """Один скрипт: выбор события + текст команды."""

    def __init__(self, on_remove, trigger_key: str = "", command: str = ""):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.combo = Dropdown()
        for key, text in _SCRIPT_TRIGGERS:
            self.combo.addItem(text, key)
        idx = self.combo.findData(trigger_key)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        head.addWidget(self.combo, 1)

        rm = IconButton("trash", 40, 18, theme.TEXT_SECOND, theme.DANGER)
        rm.setToolTip("Удалить скрипт")
        rm.clicked.connect(lambda: on_remove(self))
        head.addWidget(rm)
        v.addLayout(head)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("# команды bash/shell\n# например: notify-send \"Фокус завершён\"")
        self.editor.setFixedHeight(90)
        self.editor.setPlainText(command)
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid transparent; border-radius: 12px; padding: 8px;
                font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace;
                font-size: 12px; selection-background-color: {theme.ACCENT};
            }}
            QPlainTextEdit:focus {{ border: 1px solid {theme.ACCENT}; }}
        """)
        v.addWidget(self.editor)

    def wheelEvent(self, event):
        event.ignore()


class ProjectEditPage(QWidget):
    sig_save = Signal(dict)
    sig_cancel = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: dict = {}
        self._scripts: list[_ScriptEntry] = []
        self._advanced_open = False
        self._setup_ui()

    # ── Публичный API ──────────────────────────────────────────
    def load_project(self, project: dict | None) -> None:
        """Заполнить форму данными проекта (или очистить для нового)."""
        self._project = dict(project) if project else {}
        p = self._project

        self._name_edit.setText(p.get("name", ""))
        self._focus_wheel.set_value(p.get("focus_min", 25))
        self._break_wheel.set_value(p.get("break_min", 5))
        self._cycles.set_value(p.get("cycles", 4))
        self._afk_toggle.setChecked(p.get("afk_tracking", False))
        self._tags.set_tracked(p.get("tracked_processes", []))

        for entry in list(self._scripts):
            self._remove_script(entry)
        scripts = p.get("scripts", {})
        if isinstance(scripts, dict):
            scripts = [{"trigger": k, "command": (v or "").strip()}
                       for k, v in scripts.items() if (v or "").strip()]
        for item in scripts:
            self._add_script(item.get("trigger", ""), item.get("command", ""))

        is_new = "name" not in p
        self._title.setText("Новый проект" if is_new else "Редактировать проект")
        self._save_btn.setText("Создать" if is_new else "Сохранить")

        has_advanced = bool(p.get("afk_tracking") or p.get("tracked_processes") or scripts)
        self._set_advanced_open(has_advanced)
        self._update_presets()
        self._name_card.set_border(theme.CARD_BORDER)
        self._name_edit.setFocus()

    # ── Построение интерфейса ──────────────────────────────────
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(24, 52, 24, theme.NAV_SPACE)

        column = QWidget()
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(16)
        v.addWidget(centered(column, COLUMN_W))
        v.addStretch()

        # шапка: назад + заголовок
        head = QHBoxLayout()
        head.setSpacing(6)
        back = IconButton("chevron-left", 40, 24, theme.TEXT, theme.ACCENT)
        back.setToolTip("Назад")
        back.clicked.connect(self.sig_cancel.emit)
        self._title = page_title("Новый проект")
        head.addWidget(back)
        head.addWidget(self._title)
        head.addStretch()
        col.addLayout(head)
        col.addSpacing(4)

        col.addWidget(self._build_name_card())
        col.addWidget(self._build_time_card())
        col.addWidget(self._build_cycles_card())
        col.addWidget(self._build_advanced_card())
        col.addSpacing(6)
        col.addLayout(self._build_buttons())

        outer.addWidget(make_scroll(content))
        self._set_advanced_open(False)

    def _build_name_card(self) -> Card:
        self._name_card = Card(margins=(24, 12, 24, 12))
        row = QHBoxLayout()
        row.addWidget(label("Название", 16, theme.TEXT, 600))

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Без названия")
        self._name_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._name_edit.setFixedHeight(40)
        self._name_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none; color: {theme.TEXT};
                font-size: 16px; selection-background-color: {theme.ACCENT};
            }}
        """)
        self._name_edit.returnPressed.connect(self._on_save)
        row.addWidget(self._name_edit, 1)
        self._name_card.body.addLayout(row)
        return self._name_card

    def _build_time_card(self) -> Card:
        card = Card("Время")

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(4)
        self._focus_wheel = WheelPicker(1, 480, 25, "мин", width=140)
        self._break_wheel = WheelPicker(1, 120, 5, "мин", width=140)
        for col, (text, wheel) in enumerate([("Фокус", self._focus_wheel),
                                             ("Перерыв", self._break_wheel)]):
            grid.addWidget(label(text, 13, theme.TEXT_SECOND, 600, Qt.AlignmentFlag.AlignCenter),
                           0, col)
            grid.addWidget(wheel, 1, col, Qt.AlignmentFlag.AlignHCenter)
            wheel.value_changed.connect(lambda _v: self._update_presets())
        card.body.addLayout(grid)

        self._presets = Segmented([p[0] for p in _PRESETS], index=-1)
        self._presets.changed.connect(self._apply_preset)
        card.body.addWidget(self._presets)
        return card

    def _apply_preset(self, i: int) -> None:
        _, focus, brk = _PRESETS[i]
        self._focus_wheel.set_value(focus)
        self._break_wheel.set_value(brk)
        self._update_presets()

    def _update_presets(self) -> None:
        pair = (self._focus_wheel.value(), self._break_wheel.value())
        index = -1
        for i, (_, focus, brk) in enumerate(_PRESETS):
            if pair == (focus, brk):
                index = i
        self._presets.set_index(index)

    def _build_cycles_card(self) -> Card:
        card = Card()
        row = QHBoxLayout()
        row.addWidget(label("Количество циклов", 16, theme.TEXT, 600))
        row.addStretch()
        self._cycles = Stepper(4, 1, 99)
        row.addWidget(self._cycles)
        card.body.addLayout(row)
        card.body.addWidget(hint_label(
            "Цикл — это период фокуса и перерыв. Последний цикл заканчивается без перерыва."))
        return card

    # ── Дополнительно (сворачиваемая карточка) ─────────────────
    def _build_advanced_card(self) -> Card:
        card = Card(margins=(22, 12, 22, 16))

        self._adv_header = QPushButton("  Дополнительно")
        self._adv_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._adv_header.setFixedHeight(40)
        self._adv_header.setLayoutDirection(Qt.LayoutDirection.RightToLeft)   # иконка справа
        self._adv_header.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {theme.TEXT};
                          font-size: 17px; font-weight: 700; text-align: left; }}
        """)
        self._adv_header.clicked.connect(lambda: self._set_advanced_open(not self._advanced_open))
        card.body.addWidget(self._adv_header)

        self._adv_body = QWidget()
        b = QVBoxLayout(self._adv_body)
        b.setContentsMargins(0, 6, 0, 0)
        b.setSpacing(14)

        # AFK
        row = QHBoxLayout()
        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(label("Отслеживание AFK", 15, theme.TEXT, 600))
        info.addWidget(hint_label("Ставит таймер на паузу, если вы долго ничего не делаете."))
        row.addLayout(info, 1)
        self._afk_toggle = ToggleSwitch()
        row.addWidget(self._afk_toggle)
        b.addLayout(row)
        b.addWidget(_divider())

        # процессы
        b.addWidget(label("Отслеживаемые процессы", 15, theme.TEXT, 600))
        b.addWidget(hint_label("Приложения, активность в которых запишется во время таймера."))
        self._tags = TagInput()
        b.addWidget(self._tags)
        b.addWidget(_divider())

        # скрипты
        b.addWidget(label("Скрипты bash / shell", 15, theme.TEXT, 600))
        b.addWidget(hint_label("Выполняются при выбранном событии. "
                               "Доступны переменные $PROJECT_NAME, $CYCLE, $ELAPSED_MIN."))
        self._scripts_layout = QVBoxLayout()
        self._scripts_layout.setSpacing(14)
        b.addLayout(self._scripts_layout)
        add = PillButton("Добавить скрипт", "ghost", "plus", height=40)
        add.clicked.connect(lambda: self._add_script())
        b.addWidget(add, 0, Qt.AlignmentFlag.AlignLeft)

        card.body.addWidget(self._adv_body)
        return card

    def _set_advanced_open(self, is_open: bool) -> None:
        self._advanced_open = is_open
        self._adv_body.setVisible(is_open)
        self._adv_header.setIcon(icon("chevron-up" if is_open else "chevron-down",
                                      theme.TEXT_SECOND, 20))

    def _add_script(self, trigger_key: str = "", command: str = "") -> None:
        entry = _ScriptEntry(self._remove_script, trigger_key, command)
        self._scripts_layout.addWidget(entry)
        self._scripts.append(entry)

    def _remove_script(self, entry: _ScriptEntry) -> None:
        self._scripts.remove(entry)
        self._scripts_layout.removeWidget(entry)
        entry.hide()
        entry.setParent(None)
        entry.deleteLater()

    # ── Кнопки и сохранение ────────────────────────────────────
    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()
        cancel = PillButton("Отмена", "secondary")
        cancel.clicked.connect(self.sig_cancel.emit)
        self._save_btn = PillButton("Создать", "primary")
        self._save_btn.setMinimumWidth(170)
        self._save_btn.clicked.connect(self._on_save)
        row.addWidget(cancel)
        row.addWidget(self._save_btn)
        return row

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_card.set_border(theme.DANGER)
            self._name_edit.setPlaceholderText("Введите название проекта")
            self._name_edit.setFocus()
            QTimer.singleShot(2000, self._reset_name_error)
            return

        scripts = []
        for entry in self._scripts:
            command = entry.editor.toPlainText().strip()
            if command:
                scripts.append({"trigger": entry.combo.currentData(), "command": command})

        self._project.update({
            "name": name,
            "focus_min": self._focus_wheel.value(),
            "break_min": self._break_wheel.value(),
            "cycles": self._cycles.value(),
            "afk_tracking": self._afk_toggle.isChecked(),
            "tracked_processes": self._tags.get_tracked(),
            "scripts": scripts,
        })
        self.sig_save.emit(dict(self._project))

    def _reset_name_error(self) -> None:
        self._name_card.set_border(theme.CARD_BORDER)
        self._name_edit.setPlaceholderText("Без названия")
