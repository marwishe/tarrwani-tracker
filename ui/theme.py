"""Тема интерфейса: цвета, шрифты и общие стили (дизайн в стиле NovaClock).

Все цвета лежат здесь в одном месте. Хотите другой акцент — поменяйте ACCENT.
"""

from PySide6.QtGui import QColor, QFont, QPalette

# ── Цвета ──────────────────────────────────────────────────────
BG             = "#101012"   # фон окна
CARD           = "#1c1c1e"   # карточки
CARD_BORDER    = "#2c2c2e"   # тонкая рамка карточек
SURFACE        = "#232325"   # поля ввода, выбранная строка колеса
SURFACE_HOVER  = "#2c2c2e"
PILL           = "#27272a"   # нижняя панель навигации
PILL_BTN       = "#2c2c2e"   # вторичные кнопки
PILL_BORDER    = "#3a3a3c"
SEGMENT_BG     = "#2b2b2b"   # группа переключателей
SEGMENT_SEL    = "#115992"   # выбранный пункт

ACCENT         = "#0a84ff"
ACCENT_HOVER   = "#3d9bff"
ACCENT_PRESS   = "#0070e0"
ACCENT_SOFT    = "#23364b"   # мягкая подложка активной иконки

TEXT           = "#f5f5f7"
TEXT_SECOND    = "#9d9da3"
TEXT_MUTED     = "#6c6c72"
TEXT_HINT      = "#8b94a5"   # серо-голубые подсказки
TEXT_DISABLED  = "#505055"

DANGER         = "#ff453a"
DANGER_SOFT    = "#3a1f1f"
SUCCESS        = "#30d158"
WARNING        = "#ff9f0a"

# ── Размеры ────────────────────────────────────────────────────
CARD_RADIUS = 20
TITLEBAR_H  = 40
NAV_SPACE   = 120   # нижний отступ страниц, чтобы нижняя панель не закрывала контент

# ── Шрифты ─────────────────────────────────────────────────────
# Если Inter не установлен, Qt возьмёт следующий из списка.
FONT_FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI",
                 "SF Pro Text", "Helvetica Neue", "Arial"]

MONO_FAMILIES = ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "monospace"]


def make_font(pixel_size: int, weight=QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def mix(c1: str, c2: str, t: float) -> QColor:
    """Смесь двух цветов: t=0 -> c1, t=1 -> c2."""
    a, b = QColor(c1), QColor(c2)
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


# ── Общие стили ────────────────────────────────────────────────
SCROLL_QSS = f"""
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 0; }}
    QScrollBar::handle:vertical {{
        background: {PILL_BORDER}; border-radius: 3px; min-height: 28px; margin: 0 1px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #4c4c50; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""

_APP_QSS = f"""
    QToolTip {{
        background: {PILL_BTN}; color: {TEXT}; border: 1px solid {PILL_BORDER};
        border-radius: 6px; padding: 4px 8px;
    }}
"""


def apply_app_style(app) -> None:
    """Шрифт, тёмная палитра и подсказки для всего приложения."""
    app.setStyle("Fusion")   # одинаково выглядит на любой ОС
    app.setFont(make_font(14))

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    pal.setColor(QPalette.ColorRole.Button, QColor(PILL_BTN))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(PILL_BTN))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(pal)

    app.setStyleSheet(_APP_QSS)
