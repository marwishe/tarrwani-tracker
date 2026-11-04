"""Статистика по сессиям: сводка, график по дням, проекты, приложения и история."""

import time
from collections import defaultdict
from datetime import datetime

from PySide6.QtCore import Qt, QRectF, QUrl
from PySide6.QtGui import QPainter, QColor, QPen, QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy

from ui import theme
from core import storage
from ui.theme import make_font
from ui.widgets.basic import (
    Card, Segmented, PillButton, make_scroll, centered, label, page_title, clear_layout,
)

COLUMN_W = 760
HISTORY_COMPACT = 5     # сколько сессий видно в свёрнутом списке
HISTORY_MAX = 200       # предел для развёрнутого списка

_PERIOD_LABELS = ["День", "Неделя", "Месяц", "Всё время"]
_DAY = 86400
_PERIOD_SECS = [_DAY, 7 * _DAY, 30 * _DAY, None]


def fmt_duration(secs: int) -> str:
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    if s or not parts:
        parts.append(f"{s}с")
    return " ".join(parts)


def fmt_ts(ts: float) -> str:
    dt, now = datetime.fromtimestamp(ts), datetime.now()
    if dt.date() == now.date():
        return "Сегодня " + dt.strftime("%H:%M")
    if (now.date() - dt.date()).days == 1:
        return "Вчера " + dt.strftime("%H:%M")
    return dt.strftime("%d.%m.%Y %H:%M")


def sessions_in_period(projects: list[dict], period_idx: int) -> list[dict]:
    now, limit = time.time(), _PERIOD_SECS[period_idx]
    result = []
    for project in projects:
        for s in project.get("sessions", []):
            if limit is None or now - s.get("timestamp", 0) <= limit:
                result.append(s)
    return result


def session_secs(s: dict) -> int:
    return s.get("actual_secs") or s.get("planned_secs", 0)


# ── Свои виджеты ───────────────────────────────────────────────

class BarChart(QWidget):
    """Столбчатая диаграмма «время по дням»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, int]] = []
        self.setMinimumHeight(190)

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self._data = list(data)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(make_font(12))

        if not self._data:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных за выбранный период")
            return

        w, h = self.width(), self.height()
        left, right, top, bottom = 58, 8, 8, 26
        cw, ch = w - left - right, h - top - bottom
        if cw < 20 or ch < 20:
            return

        max_val = max(v for _, v in self._data) or 1
        n = len(self._data)

        # сетка и подписи оси Y
        for i in range(5):
            y = top + ch - ch * i / 4
            p.setPen(QPen(QColor(theme.CARD_BORDER), 1))
            p.drawLine(int(left), int(y), int(w - right), int(y))
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(QRectF(0, y - 9, left - 8, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       fmt_duration(max_val * i // 4))

        # столбцы
        slot = cw / n
        bar_w = max(6.0, min(36.0, slot * 0.6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.ACCENT))
        for i, (day, val) in enumerate(self._data):
            x = left + slot * i + (slot - bar_w) / 2
            bar_h = ch * val / max_val
            p.drawRoundedRect(QRectF(x, top + ch - bar_h, bar_w, bar_h), 5, 5)

            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(QRectF(left + slot * i, h - bottom + 4, slot, 20),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, day)
            p.setPen(Qt.PenStyle.NoPen)


class ShareBar(QWidget):
    """Тонкая полоса «доля от максимума»."""

    def __init__(self, fraction: float, parent=None):
        super().__init__(parent)
        self._fraction = max(0.0, min(1.0, fraction))
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SURFACE))
        p.drawRoundedRect(self.rect(), 3, 3)
        p.setBrush(QColor(theme.ACCENT))
        p.drawRoundedRect(QRectF(0, 0, max(6.0, self.width() * self._fraction), 6), 3, 3)


# ── Страница ───────────────────────────────────────────────────

class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[dict] = []
        self._period_idx = 3
        self._history_expanded = False
        self._sessions: list[dict] = []
        self._setup_ui()

    def set_projects(self, projects: list[dict]) -> None:
        self._projects = projects
        self._refresh()

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

        col.addWidget(page_title("Статистика"))

        self._period = Segmented(_PERIOD_LABELS, self._period_idx)
        self._period.changed.connect(self._on_period)
        col.addWidget(self._period)

        # сводка
        summary = QHBoxLayout()
        summary.setSpacing(12)
        self._summary_vals = []
        for caption in ["Всего времени", "Сессий", "Проектов"]:
            card = Card(margins=(18, 16, 18, 16))
            card.body.setSpacing(2)
            val = label("—", 28, theme.TEXT, 300, Qt.AlignmentFlag.AlignCenter)
            card.body.addWidget(val)
            card.body.addWidget(label(caption, 13, theme.TEXT_SECOND, 400, Qt.AlignmentFlag.AlignCenter))
            summary.addWidget(card, 1)
            self._summary_vals.append(val)
        col.addLayout(summary)

        # график
        chart_card = Card("Активность по дням")
        self._chart = BarChart()
        chart_card.body.addWidget(self._chart)
        col.addWidget(chart_card)

        # разделы
        projects_card = Card("Проекты")
        self._projects_box = QVBoxLayout()
        self._projects_box.setSpacing(14)
        projects_card.body.addLayout(self._projects_box)
        col.addWidget(projects_card)

        apps_card = Card("Приложения")
        self._apps_box = QVBoxLayout()
        self._apps_box.setSpacing(14)
        apps_card.body.addLayout(self._apps_box)
        col.addWidget(apps_card)

        history_card = Card("История сессий")
        self._history_box = QVBoxLayout()
        self._history_box.setSpacing(0)
        history_card.body.addLayout(self._history_box)
        col.addWidget(history_card)

        root.addWidget(make_scroll(content))
        self._refresh()

    def _on_period(self, idx: int) -> None:
        self._period_idx = idx
        self._history_expanded = False
        self._refresh()

    def _toggle_history(self) -> None:
        self._history_expanded = not self._history_expanded
        self._fill_history(self._sessions)

    # ── Данные ─────────────────────────────────────────────────
    def _refresh(self) -> None:
        sessions = sessions_in_period(self._projects, self._period_idx)

        total = 0
        by_project: dict[str, int] = defaultdict(int)
        by_app: dict[str, int] = defaultdict(int)
        by_day: dict[str, int] = defaultdict(int)

        for s in sessions:
            secs = session_secs(s)
            total += secs
            by_project[s.get("project_name", "Без проекта")] += secs
            for app, app_secs in s.get("process_log", {}).items():
                by_app[app] += app_secs
            if s.get("timestamp"):
                by_day[datetime.fromtimestamp(s["timestamp"]).strftime("%d.%m")] += secs

        self._summary_vals[0].setText(fmt_duration(total) if total else "—")
        self._summary_vals[1].setText(str(len(sessions)))
        self._summary_vals[2].setText(str(len(self._projects)))

        # дни в хронологическом порядке (по реальной дате, а не по тексту)
        day_order = {}
        for s in sessions:
            ts = s.get("timestamp")
            if ts:
                key = datetime.fromtimestamp(ts).strftime("%d.%m")
                day_order[key] = min(day_order.get(key, ts), ts)
        days = sorted(by_day.items(), key=lambda kv: day_order[kv[0]])
        self._chart.set_data(days)

        self._fill_shares(self._projects_box, by_project, "Нет данных по проектам")
        self._fill_shares(self._apps_box, by_app, "Нет данных по приложениям")
        self._fill_history(sessions)

    def _fill_shares(self, box: QVBoxLayout, data: dict, empty_text: str) -> None:
        clear_layout(box)
        if not data:
            box.addWidget(label(empty_text, 13, theme.TEXT_MUTED))
            return

        max_val = max(data.values()) or 1
        for name, val in sorted(data.items(), key=lambda kv: -kv[1]):
            item = QWidget()
            v = QVBoxLayout(item)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(6)
            row = QHBoxLayout()
            row.addWidget(label(name, 14, theme.TEXT, 600), 1)
            row.addWidget(label(fmt_duration(val), 13, theme.TEXT_SECOND, 600))
            v.addLayout(row)
            v.addWidget(ShareBar(val / max_val))
            box.addWidget(item)

    def _fill_history(self, sessions: list[dict]) -> None:
        self._sessions = sessions
        clear_layout(self._history_box)

        newest_first = sorted(sessions, key=lambda s: s.get("timestamp", 0), reverse=True)
        limit = HISTORY_MAX if self._history_expanded else HISTORY_COMPACT

        if not sessions:
            self._history_box.addWidget(label("Нет завершённых сессий", 13, theme.TEXT_MUTED))

        for s in newest_first[:limit]:
            # одна компактная строка: проект · время · длительность
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 7, 0, 7)
            h.setSpacing(12)
            h.addWidget(label(s.get("project_name", "—"), 14, theme.TEXT, 600), 1)
            h.addWidget(label(fmt_ts(s["timestamp"]) if s.get("timestamp") else "—",
                              12, theme.TEXT_MUTED))
            duration = label(fmt_duration(session_secs(s)), 14, theme.ACCENT, 700)
            duration.setMinimumWidth(64)
            duration.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(duration)

            # приложения — во всплывающей подсказке
            apps = sorted(s.get("process_log", {}).items(), key=lambda kv: -kv[1])[:5]
            if apps:
                row.setToolTip("\n".join(f"{n}: {fmt_duration(v)}" for n, v in apps))
            self._history_box.addWidget(row)

        # кнопки внизу: «показать все / свернуть» и «открыть папку с данными»
        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch()
        if len(sessions) > HISTORY_COMPACT:
            text = "Свернуть" if self._history_expanded else f"Показать все ({len(sessions)})"
            toggle = PillButton(text, "ghost",
                                "chevron-up" if self._history_expanded else "chevron-down",
                                height=40)
            toggle.clicked.connect(self._toggle_history)
            footer.addWidget(toggle)
        folder = PillButton("Папка с данными", "ghost", "folder", height=40)
        folder.setToolTip(str(storage.sessions_dir()))
        folder.clicked.connect(self._open_data_folder)
        footer.addWidget(folder)
        footer.addStretch()
        self._history_box.addSpacing(6)
        self._history_box.addLayout(footer)

    def _open_data_folder(self) -> None:
        """Открыть папку sessions в проводнике (её можно синхронизировать)."""
        folder = storage.sessions_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
