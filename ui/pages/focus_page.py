"""Главная страница: часы, дата и список проектов (периодов фокусировки)."""

import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

from ui import theme
from core.timer_engine import TimerEngine
from core.process_tracker import ProcessTracker
from core.notifier import Notifier
from ui.widgets.basic import (
    PillButton, make_scroll, centered, label, clear_layout,
)
from ui.widgets.big_time import BigTime
from ui.widgets.dialogs import ConfirmDialog
from ui.widgets.project_card import ProjectCard
from ui.widgets.active_timer_card import ActiveTimerCard
from ui.pages.project_edit_page import ProjectEditPage

_WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря"]

COLUMN_W = 600


def ru_date(now: datetime) -> str:
    return f"{_WEEKDAYS[now.weekday()]}, {now.day} {_MONTHS[now.month - 1]} {now.year}"


class FocusPage(QWidget):
    """Главная страница с двумя экранами: список проектов и форма проекта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[dict] = []
        self._cards: list[ProjectCard] = []
        self._edit_index: int | None = None     # None — создаём новый проект
        self._running_index: int | None = None  # проект, у которого идёт таймер

        self._engine = TimerEngine(self)
        self._engine.sig_tick.connect(self._on_engine_tick)
        self._engine.sig_finished.connect(self._on_engine_finished)
        self._engine.sig_phase_changed.connect(self._on_phase_changed)
        self._notifier = Notifier(self)

        self._proc_tracker: ProcessTracker | None = None
        self._session_accumulator: dict[str, int] = {}
        self._session_elapsed = 0

        self._setup_ui()

        # часы наверху страницы
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(500)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

    @property
    def projects(self) -> list[dict]:
        return self._projects

    # ── Построение интерфейса ──────────────────────────────────
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._edit_view = ProjectEditPage()
        self._edit_view.sig_save.connect(self._on_project_saved)
        self._edit_view.sig_cancel.connect(self._show_list)

        self._stack.addWidget(self._build_list_view())
        self._stack.addWidget(self._edit_view)

    def _build_list_view(self) -> QWidget:
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(24, 56, 24, theme.NAV_SPACE)
        v.setSpacing(0)

        # часы, дата и кнопка
        self._clock = BigTime("00:00:00", 64)
        v.addWidget(self._clock)
        self._date = label("", 17, theme.TEXT_SECOND, 700, Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._date)
        v.addSpacing(22)

        new_btn = PillButton("Новый проект", "secondary", height=46)
        new_btn.clicked.connect(self._open_create)
        v.addWidget(new_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addSpacing(30)

        # карточка запущенного таймера
        self._active_card = ActiveTimerCard()
        self._active_card.sig_toggle_pause.connect(self._engine.toggle_pause)
        self._active_card.sig_stop.connect(self._on_stop_active)
        self._active_wrap = centered(self._active_card, COLUMN_W)
        self._active_wrap.setVisible(False)
        v.addWidget(self._active_wrap)
        v.addSpacing(14)

        # подсказка, пока проектов нет
        self._empty = label(
            "Здесь появятся ваши проекты — их можно будет запускать в одно нажатие.",
            14, theme.TEXT_HINT, 400, Qt.AlignmentFlag.AlignCenter, wrap=True,
        )
        v.addWidget(self._empty)

        # список проектов
        self._cards_box = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_box)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        v.addWidget(centered(self._cards_box, COLUMN_W))
        v.addStretch()

        return make_scroll(content)

    def _update_clock(self) -> None:
        now = datetime.now()
        self._clock.set_text(now.strftime("%H:%M:%S"))
        self._date.setText(ru_date(now))

    # ── Список карточек ────────────────────────────────────────
    def _rebuild_cards(self) -> None:
        clear_layout(self._cards_layout)
        self._cards = []
        self._empty.setVisible(not self._projects)

        for i, project in enumerate(self._projects):
            card = ProjectCard(project, i)
            card.sig_edit.connect(self._open_edit)
            card.sig_delete.connect(self._confirm_delete)
            card.sig_start.connect(self._on_start)
            card.set_locked(self._engine.is_running and i != self._running_index)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

    # ── Навигация ──────────────────────────────────────────────
    def _show_list(self) -> None:
        self._stack.setCurrentIndex(0)

    def _open_create(self) -> None:
        self._edit_index = None
        self._edit_view.load_project(None)
        self._stack.setCurrentIndex(1)

    def _open_edit(self, index: int) -> None:
        self._edit_index = index
        self._edit_view.load_project(self._projects[index])
        self._stack.setCurrentIndex(1)

    # ── Создание / удаление проектов ───────────────────────────
    def _on_project_saved(self, project: dict) -> None:
        if self._edit_index is None:
            self._projects.append(project)
        else:
            self._projects[self._edit_index] = project
        self._rebuild_cards()
        self._show_list()

    def _confirm_delete(self, index: int) -> None:
        name = self._projects[index].get("name", "проект")
        if self._running_index == index:
            ConfirmDialog.info(self, "Нельзя удалить",
                               f"Таймер проекта «{name}» сейчас запущен. Сначала остановите его.")
            return
        if not ConfirmDialog.ask(self, "Удалить проект",
                                 f"Удалить «{name}»? Это действие нельзя отменить.",
                                 ok_text="Удалить", danger=True):
            return
        self._projects.pop(index)
        if self._running_index is not None and self._running_index > index:
            self._running_index -= 1
        self._rebuild_cards()

    # ── Работа с таймером ──────────────────────────────────────
    def _on_start(self, index: int) -> None:
        if self._engine.is_running:
            return
        self._running_index = index
        project = self._projects[index]

        cycles = max(1, int(project.get("cycles", 1)))
        focus_secs = max(1, int(project.get("focus_min", 25))) * 60
        self._active_card.update_state({
            "running": True, "project": project, "phase": "focus",
            "cycle": 1, "total_cycles": cycles,
            "breaks_done": 0, "total_breaks": cycles - 1,
            "phase_total": focus_secs, "phase_remaining": focus_secs,
            "is_paused": False, "is_afk_paused": False,
        })
        self._active_wrap.setVisible(True)
        self._session_elapsed = 0

        self._set_cards_locked(index)
        self._engine.start(project)
        self._start_process_tracking(project)

    def _start_process_tracking(self, project: dict) -> None:
        tracked = project.get("tracked_processes", [])
        if not tracked:
            return
        self._proc_tracker = ProcessTracker(tracked, self)
        self._proc_tracker.sig_tick.connect(self._on_proc_tracker_tick)
        self._proc_tracker.start()

    def _on_proc_tracker_tick(self, log: dict) -> None:
        merged = dict(self._session_accumulator)
        for name, secs in log.items():
            merged[name] = merged.get(name, 0) + secs
        self._active_card.update_process_log(merged)

    def _stop_process_tracking(self, save_to_project: bool = True) -> dict:
        if self._proc_tracker is not None:
            partial = self._proc_tracker.stop()
            self._proc_tracker.deleteLater()
            self._proc_tracker = None
            for name, secs in partial.items():
                self._session_accumulator[name] = self._session_accumulator.get(name, 0) + secs
        log = dict(self._session_accumulator)

        if save_to_project and self._running_index is not None:
            project = self._projects[self._running_index]
            planned = int(project.get("focus_min", 25)) * 60 * int(project.get("cycles", 1))
            project.setdefault("sessions", []).append({
                "process_log": log,
                "timestamp": time.time(),
                "project_name": project.get("name", ""),
                "planned_secs": planned,
                "actual_secs": self._session_elapsed,
            })
        self._session_accumulator.clear()
        self._session_elapsed = 0
        return log

    def _on_stop_active(self) -> None:
        self._engine.stop()
        self._stop_process_tracking()
        self._active_wrap.setVisible(False)
        self._running_index = None
        self._set_cards_locked(None)

    def _on_engine_tick(self, state: dict) -> None:
        if not state.get("running", False):
            return
        paused = state.get("is_paused", False) or state.get("is_afk_paused", False)
        if state.get("phase") == "focus" and not paused:
            self._session_elapsed += 1
        self._active_card.update_state(state)
        if self._proc_tracker:
            if paused:
                self._proc_tracker.pause()
            else:
                self._proc_tracker.resume()

    def _on_phase_changed(self, phase: str) -> None:
        """Фокус закончился (phase == "break") или закончился перерыв (phase == "focus")."""
        project = self._engine.project or {}
        if not project.get("notifications", True):
            return
        state = self._engine.state()
        name = project.get("name", "проект")
        cycle_info = f"Цикл {state['cycle']} из {state['total_cycles']}."

        if phase == "break":
            self._notifier.notify(
                "Фокус завершён",
                f"«{name}»: пора отдохнуть — перерыв {project.get('break_min', 5)} мин. {cycle_info}",
            )
        else:
            self._notifier.notify(
                "Перерыв окончен",
                f"«{name}»: пора за работу — фокус {project.get('focus_min', 25)} мин. {cycle_info}",
            )

    def _on_engine_finished(self) -> None:
        project = self._projects[self._running_index] if self._running_index is not None else {}
        name = project.get("name", "проект")
        if project.get("notifications", True):
            self._notifier.notify("Таймер завершён", f"«{name}»: все циклы завершены!")

        self._stop_process_tracking()
        self._active_wrap.setVisible(False)
        self._running_index = None
        self._set_cards_locked(None)

        ConfirmDialog.info(self, "Таймер завершён", f"«{name}» — все циклы завершены!")

    def _set_cards_locked(self, running_index: int | None) -> None:
        """Заблокировать кнопки запуска у всех карточек, кроме запущенной."""
        for i, card in enumerate(self._cards):
            card.set_locked(running_index is not None and i != running_index)

    # ── Сворачивание окна ──────────────────────────────────────
    def _on_window_minimized(self, minimized: bool) -> None:
        if not self._engine.is_running:
            return
        if minimized:
            self._stop_process_tracking(save_to_project=False)
            self._active_wrap.setVisible(False)
        elif self._running_index is not None:
            self._start_process_tracking(self._projects[self._running_index])
            self._active_wrap.setVisible(True)
