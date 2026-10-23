"""Марафон: секундомер, который считает время работы и активность приложений."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from ui import theme
from core.marathon_engine import MarathonEngine
from core.process_tracker import ProcessTracker
from ui.widgets.basic import (
    Card, PillButton, make_scroll, centered, label, page_title, hint_label, clear_layout,
)
from ui.widgets.big_time import BigTime
from ui.widgets.tag_input import TagInput

COLUMN_W = 560


def fmt_secs(total: int) -> str:
    h, rem = divmod(int(total), 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    parts.append(f"{s}с")
    return " ".join(parts)


class MarathonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = MarathonEngine(self)
        self._engine.sig_tick.connect(self._on_tick)

        self._tracker: ProcessTracker | None = None
        self._session_accumulator: dict[str, int] = {}

        self._setup_ui()
        self._update_ui()

    # ── Построение интерфейса ──────────────────────────────────
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(24, 52, 24, theme.NAV_SPACE)

        column = QWidget()
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(16)
        v.addWidget(centered(column, COLUMN_W))
        v.addStretch()

        col.addWidget(page_title("Марафон"))
        col.addSpacing(12)

        # большое время и статус
        self._time = BigTime("00:00:00", 88)
        col.addWidget(self._time)
        self._status = label("Готов к старту", 18, theme.TEXT_SECOND, 700, Qt.AlignmentFlag.AlignCenter)
        col.addWidget(self._status)
        col.addSpacing(8)

        # кнопки
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addStretch()
        self._toggle_btn = PillButton("Старт", "primary", "play", height=50)
        self._toggle_btn.setFixedWidth(180)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._reset_btn = PillButton("Сброс", "secondary", "reset", height=50)
        self._reset_btn.setFixedWidth(150)
        self._reset_btn.clicked.connect(self._on_reset)
        buttons.addWidget(self._toggle_btn)
        buttons.addWidget(self._reset_btn)
        buttons.addStretch()
        col.addLayout(buttons)
        col.addSpacing(14)

        # процессы
        procs = Card("Отслеживаемые процессы")
        procs.body.addWidget(hint_label(
            "Введите имя приложения, например figma.exe или chrome.exe. "
            "Время засчитывается, пока его окно активно."))
        self._tags = TagInput()
        procs.body.addWidget(self._tags)
        col.addWidget(procs)

        # активность
        log_card = Card("Активность приложений")
        self._log_layout = QVBoxLayout()
        self._log_layout.setSpacing(2)
        log_card.body.addLayout(self._log_layout)
        col.addWidget(log_card)
        self._update_process_log({})

        root.addWidget(make_scroll(content))

    # ── Управление ─────────────────────────────────────────────
    def _on_toggle(self) -> None:
        if not self._engine.is_running:
            self._engine.start()
            tracked = self._tags.get_tracked()
            if tracked:
                self._session_accumulator = {n: 0 for n in tracked}
                self._tracker = ProcessTracker(tracked, self)
                self._tracker.sig_tick.connect(self._on_tracker_tick)
                self._tracker.start()
        else:
            self._engine.toggle_pause()
            if self._tracker:
                if self._engine.is_paused:
                    self._tracker.pause()
                else:
                    self._tracker.resume()
        self._update_ui()

    def _on_reset(self) -> None:
        self._engine.stop()
        if self._tracker is not None:
            self._tracker.stop()
            self._tracker.deleteLater()
            self._tracker = None
        self._session_accumulator.clear()
        self._time.set_text("00:00:00")
        self._set_status("Готов к старту", theme.TEXT_SECOND)
        self._update_process_log({})
        self._update_ui()

    # ── Обновление по тикам ────────────────────────────────────
    def _on_tick(self, state: dict) -> None:
        total = state.get("elapsed", 0)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        self._time.set_text(f"{h:02d}:{m:02d}:{s:02d}")

        if state.get("running") and not state.get("paused"):
            self._set_status("Идёт запись", theme.ACCENT)
        elif state.get("paused"):
            self._set_status("На паузе", theme.TEXT_SECOND)

    def _on_tracker_tick(self, tracker_log: dict) -> None:
        merged = dict(self._session_accumulator)
        for name, secs in tracker_log.items():
            merged[name] = merged.get(name, 0) + secs
        self._update_process_log(merged)

    def _set_status(self, text: str, color: str) -> None:
        self._status.setText(text)
        self._status.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: 700; background: transparent;"
        )

    def _update_ui(self) -> None:
        running = self._engine.is_running
        paused = self._engine.is_paused

        if not running:
            self._toggle_btn.setText("Старт")
            self._toggle_btn.set_icon_name("play")
            self._toggle_btn.set_kind("primary")
        elif paused:
            self._toggle_btn.setText("Продолжить")
            self._toggle_btn.set_icon_name("play")
            self._toggle_btn.set_kind("primary")
        else:
            self._toggle_btn.setText("Пауза")
            self._toggle_btn.set_icon_name("pause")
            self._toggle_btn.set_kind("secondary")

        self._reset_btn.setEnabled(running)
        self._tags.setEnabled(not running)

    def _on_window_minimized(self, minimized: bool) -> None:
        """При сворачивании окна ставим марафон на паузу."""
        if self._engine.is_running and minimized and not self._engine.is_paused:
            self._on_toggle()
            self._set_status("Пауза: приложение свёрнуто", theme.TEXT_SECOND)

    # ── Список активности ──────────────────────────────────────
    def _update_process_log(self, log: dict) -> None:
        clear_layout(self._log_layout)
        if not log:
            self._log_layout.addWidget(label("Пока нет данных об активности", 13, theme.TEXT_MUTED))
            return

        for name, secs in sorted(log.items(), key=lambda x: -x[1]):
            row = QHBoxLayout()
            row.setContentsMargins(0, 6, 0, 6)
            row.addWidget(label(name, 14, theme.TEXT, 600), 1)
            row.addWidget(label(fmt_secs(secs), 14, theme.ACCENT, 700))
            wrapper = QWidget()
            wrapper.setLayout(row)
            self._log_layout.addWidget(wrapper)
