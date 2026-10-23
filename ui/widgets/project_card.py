"""Строка проекта в списке на главной странице."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel

from ui import theme
from ui.widgets.basic import IconButton, ElidedLabel, label


def plural_cycles(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "цикл"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "цикла"
    return "циклов"


def count_scripts(project: dict) -> int:
    scripts = project.get("scripts", {})
    if isinstance(scripts, list):
        return sum(1 for s in scripts if s.get("command", "").strip())
    return sum(1 for v in scripts.values() if v.strip())


def chip(text: str, color: str = theme.ACCENT) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; background: {theme.ACCENT_SOFT if color == theme.ACCENT else theme.SURFACE};"
        " border-radius: 9px; font-size: 12px; font-weight: 600; padding: 2px 9px;"
    )
    return lbl


class ProjectCard(QFrame):
    sig_edit = Signal(int)
    sig_delete = Signal(int)
    sig_start = Signal(int)

    def __init__(self, project: dict, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        self.setObjectName("ProjectCard")
        self.setStyleSheet(f"""
            #ProjectCard {{ background: {theme.CARD}; border: 1px solid {theme.CARD_BORDER};
                           border-radius: 20px; }}
            #ProjectCard:hover {{ border: 1px solid {theme.PILL_BORDER}; }}
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(22, 14, 14, 14)
        row.setSpacing(6)

        # слева — название и параметры
        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(ElidedLabel(project.get("name", "Без названия"), 17, theme.TEXT,
                                   QFont.Weight.Bold))

        cycles = int(project.get("cycles", 1))
        meta = (f"Фокус {project.get('focus_min', 25)} мин  ·  "
                f"перерыв {project.get('break_min', 5)} мин  ·  {cycles} {plural_cycles(cycles)}")
        info.addWidget(label(meta, 13, theme.TEXT_SECOND))

        chips = QHBoxLayout()
        chips.setSpacing(6)
        if project.get("afk_tracking"):
            chips.addWidget(chip("AFK"))
        scripts = count_scripts(project)
        if scripts:
            chips.addWidget(chip(f"скриптов: {scripts}", theme.TEXT_SECOND))
        if chips.count():
            chips.addStretch()
            info.addLayout(chips)
        row.addLayout(info, 1)

        # справа — кнопки
        edit = IconButton("pencil", 38, 18)
        edit.setToolTip("Изменить")
        edit.clicked.connect(lambda: self.sig_edit.emit(self._index))
        delete = IconButton("trash", 38, 18, theme.TEXT_SECOND, theme.DANGER)
        delete.setToolTip("Удалить")
        delete.clicked.connect(lambda: self.sig_delete.emit(self._index))
        row.addWidget(edit)
        row.addWidget(delete)

        self._start = IconButton("play", 46, 18, "#ffffff", "#ffffff",
                                 bg=theme.ACCENT, hover_bg=theme.ACCENT_HOVER)
        self._start.setToolTip("Запустить")
        self._start.clicked.connect(lambda: self.sig_start.emit(self._index))
        row.addSpacing(4)
        row.addWidget(self._start)

    def set_locked(self, locked: bool) -> None:
        """Пока идёт другой таймер, запуск недоступен."""
        self._start.setDisabled(locked)
        self._start.setToolTip("Уже идёт другой таймер" if locked else "Запустить")
        self._start.setCursor(Qt.CursorShape.ForbiddenCursor if locked
                              else Qt.CursorShape.PointingHandCursor)
