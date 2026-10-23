"""Запуск пользовательских скриптов с учётом операционной системы.

  Windows        -> «shell» (командная строка cmd)
  Linux / macOS  -> «bash»

Интерфейс берёт отсюда название категории и подсказки, а TimerEngine — запуск.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"


def shell_name() -> str:
    """Название скриптов для интерфейса: «shell» на Windows, «bash» на Linux/macOS."""
    return "shell" if IS_WINDOWS else "bash"


def env_var(name: str) -> str:
    """Как обратиться к переменной окружения в скрипте этой ОС."""
    return f"%{name}%" if IS_WINDOWS else f"${name}"


def placeholder() -> str:
    """Подсказка для пустого поля скрипта."""
    if IS_WINDOWS:
        return ("REM команды shell (cmd)\n"
                "REM например: echo %PROJECT_NAME% >> %TEMP%\\focus.log")
    return ("# команды bash\n"
            "# например: echo \"$PROJECT_NAME\" >> /tmp/focus.log")


def run_script(code: str, env: dict) -> subprocess.Popen:
    """Запустить скрипт в фоне, не дожидаясь завершения."""
    common = dict(env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if IS_WINDOWS:
        # shell=True -> cmd.exe; CREATE_NO_WINDOW — чтобы не мигало чёрное окно
        return subprocess.Popen(code, shell=True,
                                creationflags=subprocess.CREATE_NO_WINDOW, **common)

    bash = shutil.which("bash")
    if bash:
        return subprocess.Popen([bash, "-c", code], **common)
    return subprocess.Popen(code, shell=True, **common)   # запасной вариант: /bin/sh
