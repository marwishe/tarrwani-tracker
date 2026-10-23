"""Системные уведомления (всплывающее сообщение в углу экрана).

Не требует сторонних библиотек: использует QSystemTrayIcon, а если трея нет
(например, в некоторых оболочках Linux) — notify-send / osascript.

Использование:
    notifier = Notifier(parent)
    notifier.notify("Фокус завершён", "Пора отдохнуть")
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon


def _default_icon() -> QIcon:
    """Иконка приложения; если её нет — простой синий кружок."""
    icon = QApplication.windowIcon()
    if not icon.isNull():
        return icon
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(0, 0, 0, 0))
    p.setBrush(QColor("#0a84ff"))
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(24, 24, 16, 16)
    p.end()
    return QIcon(pm)


class Notifier(QObject):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tray: QSystemTrayIcon | None = None

        # значок в трее нужен только на время показа сообщения
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_tray)

    def notify(self, title: str, message: str, timeout_ms: int = 8000) -> bool:
        """Показать уведомление. Возвращает True, если удалось."""
        try:
            if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
                if self._tray is None:
                    self._tray = QSystemTrayIcon(_default_icon(), self)
                self._tray.show()
                self._tray.showMessage(title, message, self._tray.icon(), timeout_ms)
                self._hide_timer.start(timeout_ms + 2000)
                return True
            return self._fallback(title, message)
        except Exception as exc:  # уведомление не должно ронять таймер
            print(f"[Notifier] не удалось показать уведомление: {exc}")
            return False

    def _hide_tray(self) -> None:
        if self._tray is not None:
            self._tray.hide()

    @staticmethod
    def _fallback(title: str, message: str) -> bool:
        """Запасной вариант без трея."""
        if sys.platform.startswith("linux") and shutil.which("notify-send"):
            subprocess.Popen(["notify-send", title, message])
            return True
        if sys.platform == "darwin" and shutil.which("osascript"):
            def esc(s: str) -> str:
                return s.replace("\\", "\\\\").replace('"', '\\"')
            script = f'display notification "{esc(message)}" with title "{esc(title)}"'
            subprocess.Popen(["osascript", "-e", script])
            return True
        return False
