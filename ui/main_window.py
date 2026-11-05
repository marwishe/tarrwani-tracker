"""Главное окно: безрамочное, со страницами и плавающей нижней навигацией."""

from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QIcon
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStackedWidget

from ui import theme
from ui.widgets.nav_bar import NavBar
from ui.widgets.title_bar import TitleBar
from ui.widgets.sidegrip import SideGrip
from ui.pages.focus_page import FocusPage
from ui.pages.stats_page import StatsPage
from ui.pages.marathon_page import MarathonPage

try:
    from config import APP_NAME, ICON_PATH
except Exception:   # интерфейс должен запускаться и без config
    APP_NAME, ICON_PATH = "Tarrwani Tracker", None

WINDOW_RADIUS = 12
GRIP = 6   # толщина полос изменения размера


class MainWindow(QWidget):
    sig_window_minimized = Signal(bool)

    def __init__(self):
        super().__init__()
        theme.apply_app_style(QApplication.instance())

        self.setWindowTitle(APP_NAME)
        if ICON_PATH is not None and ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(560, 520)
        self.resize(960, 680)

        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # страницы (порядок совпадает с кнопками навигации)
        self.focus_page = FocusPage()
        self.stats_page = StatsPage()
        self.marathon_page = MarathonPage()
        self.stats_page.set_projects(self.focus_page.projects)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.focus_page)
        self.pages.addWidget(self.stats_page)
        self.pages.addWidget(self.marathon_page)
        root.addWidget(self.pages)

        # плавающие элементы поверх страниц
        self.title_bar = TitleBar(self)
        self.nav = NavBar([
            ("home", "Фокус"),
            ("chart", "Статистика"),
            ("stopwatch", "Марафон"),
        ], self)
        self.nav.changed.connect(self._on_view_changed)

        self._grips = []
        for edges, cursor in [
            (Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.CursorShape.SizeFDiagCursor),
            (Qt.Edge.TopEdge | Qt.Edge.RightEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.BottomEdge | Qt.Edge.LeftEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.BottomEdge | Qt.Edge.RightEdge, Qt.CursorShape.SizeFDiagCursor),
        ]:
            self._grips.append(SideGrip(self, edges, cursor))

        self.title_bar.raise_()
        self.nav.raise_()
        for grip in self._grips:
            grip.raise_()

        self.sig_window_minimized.connect(self.focus_page._on_window_minimized)
        self.sig_window_minimized.connect(self.marathon_page._on_window_minimized)

    # ── Навигация ──────────────────────────────────────────────
    def _on_view_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 1:
            self.focus_page.reload_sessions()
            self.stats_page.set_projects(self.focus_page.projects)

    # ── Окно ───────────────────────────────────────────────────
    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _is_free_form(self) -> bool:
        return not (self.isMaximized() or self.isFullScreen())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        self.title_bar.setGeometry(0, 0, w, self.title_bar.height())
        self.nav.move((w - self.nav.width()) // 2, h - self.nav.height() - 22)

        g = GRIP
        areas = [
            (g, 0, w - 2 * g, g), (g, h - g, w - 2 * g, g),
            (0, g, g, h - 2 * g), (w - g, g, g, h - 2 * g),
            (0, 0, g, g), (w - g, 0, g, g), (0, h - g, g, g), (w - g, h - g, g, g),
        ]
        for grip, rect in zip(self._grips, areas):
            grip.setGeometry(*rect)
            grip.setVisible(self._is_free_form())

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            self.sig_window_minimized.emit(bool(self.windowState() & Qt.WindowState.WindowMinimized))
            self.title_bar.set_maximized(self.isMaximized())
            for grip in self._grips:
                grip.setVisible(self._is_free_form())
            self.update()
        super().changeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = WINDOW_RADIUS if self._is_free_form() else 0
        p.setPen(QPen(QColor("#252528"), 1))
        p.setBrush(QColor(theme.BG))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), radius, radius)
