"""Тонкие линейные иконки (SVG прямо в коде, внешние файлы не нужны).

Использование:
    icon("home", "#ffffff", 22)   -> QIcon
    pixmap("home", "#ffffff", 22) -> QPixmap
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Содержимое <svg> в сетке 24x24
_PATHS = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/>'
            '<path d="M5 9v10.5a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9"/>',
    "stopwatch": '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 9.5v4l2.5 2"/>'
                 '<path d="M9.5 2.5h5"/><path d="M12 2.5V6"/>',
    "chart": '<path d="M4 3.5V20h16.5"/><path d="M9 16v-4"/><path d="M13.5 16V7"/>'
             '<path d="M18 16v-6"/>',
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "close": '<path d="M6 6l12 12"/><path d="M18 6 6 18"/>',
    "minimize": '<path d="M6 12h12"/>',
    "maximize": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
    "restore": '<rect x="5.5" y="9" width="9.5" height="9.5" rx="1.5"/>'
               '<path d="M9 9V7.5A1.5 1.5 0 0 1 10.5 6H16.5A1.5 1.5 0 0 1 18 7.5V13.5'
               'A1.5 1.5 0 0 1 16.5 15H15"/>',
    "chevron-left": '<path d="M15 5l-7 7 7 7"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "pencil": '<path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7.5 18.5 3 20l1.5-4.5z"/>'
              '<path d="M14.5 5.5l3 3"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4.5h6V7"/>'
             '<path d="M6.5 7l.8 12a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7"/>'
             '<path d="M10 11v6"/><path d="M14 11v6"/>',
    "play": '<path d="M7 4.5v15l12.5-7.5z"/>',
    "pause": '<rect x="6" y="4.5" width="4" height="15" rx="1.2"/>'
             '<rect x="14" y="4.5" width="4" height="15" rx="1.2"/>',
    "reset": '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1L3.5 8.5"/><path d="M3.5 3.5v5h5"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "moon": '<path d="M20.5 13.5A8.5 8.5 0 1 1 10.5 3.5a6.8 6.8 0 0 0 10 10z"/>',
}

# Эти иконки закрашиваются целиком, а не рисуются контуром
_FILLED = {"play", "pause", "stop"}


@lru_cache(maxsize=None)
def pixmap(name: str, color: str = "#ffffff", size: int = 24, stroke: float = 1.8) -> QPixmap:
    fill = color if name in _FILLED else "none"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{fill}" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round">{_PATHS[name]}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    scale = 2   # рисуем в двойном размере, чтобы было чётко на любом экране
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm


def icon(name: str, color: str = "#ffffff", size: int = 24) -> QIcon:
    return QIcon(pixmap(name, color, size))
