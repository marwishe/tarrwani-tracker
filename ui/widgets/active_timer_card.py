"""Карточка запущенного таймера (показывается наверху главной страницы)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar

from ui import theme
from ui.widgets.basic import Card, PillButton, ElidedLabel, label
from ui.widgets.big_time import BigTime
from ui.widgets.project_card import chip, count_scripts


class ActiveTimerCard(Card):
    sig_toggle_pause = Signal()
    sig_stop = Signal()

    def __init__(self, parent=None):
        super().__init__(border=theme.ACCENT_SOFT, margins=(24, 20, 24, 22), parent=parent)
        self.body.setSpacing(10)

        # заголовок: название + плашка фазы
        head = QHBoxLayout()
        head.setSpacing(8)
        self._name = ElidedLabel("Проект", 18, theme.TEXT, QFont.Weight.Bold)
        head.addWidget(self._name, 1)
        self._afk_chip = chip("AFK")
        self._scripts_chip = chip("", theme.TEXT_SECOND)
        self._phase = QLabel("Фокус")
        head.addWidget(self._afk_chip)
        head.addWidget(self._scripts_chip)
        head.addWidget(self._phase)
        self.body.addLayout(head)

        # время
        self._time = BigTime("00:00", 72)
        self.body.addWidget(self._time)

        # прогресс
        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(f"""
            QProgressBar {{ background: {theme.SURFACE}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {theme.ACCENT}; border-radius: 3px; }}
        """)
        self.body.addWidget(self._progress)

        self._info = label("", 13, theme.TEXT_SECOND, 400, Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self._info)

        # кнопки
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        self._pause = PillButton("Пауза", "secondary", "pause", height=44)
        self._pause.setMinimumWidth(150)
        self._pause.clicked.connect(self.sig_toggle_pause.emit)
        stop = PillButton("Стоп", "danger", "stop", height=44)
        stop.clicked.connect(self.sig_stop.emit)
        buttons.addWidget(self._pause)
        buttons.addWidget(stop)
        buttons.addStretch()
        self.body.addSpacing(4)
        self.body.addLayout(buttons)

        # приложения, в которых вы работали
        self._apps = label("", 12, theme.TEXT_MUTED, 400, Qt.AlignmentFlag.AlignCenter, wrap=True)
        self._apps.setVisible(False)
        self.body.addWidget(self._apps)

    def _set_phase(self, text: str, color: str) -> None:
        self._phase.setText(text)
        self._phase.setStyleSheet(
            f"color: {color}; background: {theme.SURFACE}; border-radius: 10px;"
            " font-size: 12px; font-weight: 700; padding: 3px 12px;"
        )

    def update_state(self, state: dict) -> None:
        project = state.get("project") or {}
        self._name.setText(project.get("name", "Проект"))

        remaining = max(state.get("phase_remaining", 0), 0)
        mins, secs = divmod(remaining, 60)
        self._time.set_text(f"{mins:02d}:{secs:02d}")

        phase = state.get("phase", "focus")
        paused = state.get("is_paused", False)
        afk_paused = state.get("is_afk_paused", False)

        # плашка фазы и цвет цифр
        if afk_paused:
            self._set_phase("AFK-пауза", theme.WARNING)
            self._time.set_color(theme.TEXT_SECOND)
        elif paused:
            self._set_phase("Пауза", theme.TEXT_SECOND)
            self._time.set_color(theme.TEXT_SECOND)
        elif phase == "focus":
            self._set_phase("Фокус", theme.ACCENT)
            self._time.set_color(theme.TEXT)
        else:
            self._set_phase("Перерыв", theme.SUCCESS)
            self._time.set_color(theme.TEXT)

        # кнопка паузы
        if afk_paused:
            self._pause.setText("Нет активности")
            self._pause.set_icon_name("moon")
            self._pause.setEnabled(False)
        elif paused:
            self._pause.setText("Продолжить")
            self._pause.set_icon_name("play")
            self._pause.set_kind("primary")
            self._pause.setEnabled(True)
        else:
            self._pause.setText("Пауза")
            self._pause.set_icon_name("pause")
            self._pause.set_kind("secondary")
            self._pause.setEnabled(True)

        # подпись и чипы
        self._info.setText(
            f"Цикл {state.get('cycle', 1)} из {state.get('total_cycles', 1)}"
            f"  ·  перерывов {state.get('breaks_done', 0)} из {state.get('total_breaks', 0)}"
        )
        self._afk_chip.setVisible(bool(project.get("afk_tracking")))
        scripts = count_scripts(project)
        self._scripts_chip.setVisible(bool(scripts))
        self._scripts_chip.setText(f"скриптов: {scripts}")

        total = state.get("phase_total", 1) or 1
        self._progress.setValue(max(0, min(1000, int(1000 * (1 - remaining / total)))))

    def update_process_log(self, log: dict) -> None:
        if not log:
            self._apps.setVisible(False)
            return
        parts = []
        for name, secs in sorted(log.items(), key=lambda x: -x[1]):
            m, s = divmod(secs, 60)
            parts.append(f"{name} {m}м {s}с" if m else f"{name} {s}с")
        self._apps.setText("   ·   ".join(parts))
        self._apps.setVisible(True)
