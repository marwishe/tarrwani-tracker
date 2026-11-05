"""Локальное хранилище: проекты и сессии на диске.

    ~/.tarrwani/
        settings.json                      настройки темы (уже было)
        projects.json                      проекты (без сессий)
        sessions/                          по одному файлу на каждую сессию
            2026-10-09_09-56-12_ab12cd34.json

Каждая сессия — отдельный файл с уникальным именем, поэтому папку `sessions`
безопасно синхронизировать (Dropbox, Syncthing, OneDrive…): файлы с разных
устройств не перезаписывают друг друга.

Хранить данные в другом месте (например, в папке синхронизации) можно через
переменную окружения TARRWANI_DATA_DIR (её можно прописать в .env).

Все функции безопасны: при ошибке диска они печатают сообщение и не роняют
приложение.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


# ── Пути ───────────────────────────────────────────────────────

def data_dir() -> Path:
    custom = os.environ.get("TARRWANI_DATA_DIR")
    return Path(custom).expanduser() if custom else Path.home() / ".tarrwani"


def sessions_dir() -> Path:
    return data_dir() / "sessions"


def projects_file() -> Path:
    return data_dir() / "projects.json"


# ── Вспомогательное ────────────────────────────────────────────

def _write_json(path: Path, data) -> None:
    """Запись через временный файл, чтобы при сбое не получить обрезанный JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _new_id() -> str:
    return uuid.uuid4().hex


# ── Проекты ────────────────────────────────────────────────────

def load_projects() -> list[dict]:
    """Прочитать проекты с диска и подцепить к ним сессии."""
    path = projects_file()
    projects: list[dict] = []

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            projects = [p for p in data.get("projects", []) if isinstance(p, dict)]
        except Exception as exc:
            # не затираем повреждённый файл: сохраняем копию и начинаем с чистого листа
            backup = path.with_name(path.name + ".bak")
            try:
                os.replace(path, backup)
            except OSError:
                pass
            print(f"[storage] projects.json повреждён ({exc}); копия: {backup}")
            projects = []

    for project in projects:
        project.setdefault("id", _new_id())
    attach_sessions(projects)
    return projects


def save_projects(projects: list[dict]) -> bool:
    """Сохранить проекты (сессии в этот файл не попадают — они лежат отдельно)."""
    try:
        payload = []
        for project in projects:
            project.setdefault("id", _new_id())
            payload.append({k: v for k, v in project.items() if k != "sessions"})
        _write_json(projects_file(), {"version": 1, "projects": payload})
        return True
    except Exception as exc:
        print(f"[storage] не удалось сохранить проекты: {exc}")
        return False


# ── Сессии ─────────────────────────────────────────────────────

def _session_files() -> list[Path]:
    folder = sessions_dir()
    return sorted(folder.glob("*.json")) if folder.exists() else []


def load_sessions() -> list[dict]:
    """Все сессии из папки sessions (битые файлы пропускаются)."""
    sessions = []
    for path in _session_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "timestamp" in data:
                sessions.append(data)
        except Exception as exc:
            print(f"[storage] пропущен файл {path.name}: {exc}")
    sessions.sort(key=lambda s: s.get("timestamp", 0))
    return sessions


def attach_sessions(projects: list[dict]) -> None:
    """Заново заполнить project["sessions"] данными с диска.

    Сессия привязывается к проекту по id, а если id не совпал (например, проекты
    на другом устройстве создавались отдельно) — по названию.
    """
    by_id = {p["id"]: p for p in projects if p.get("id")}
    by_name: dict[str, dict] = {}
    for p in projects:
        by_name.setdefault(p.get("name", ""), p)
        p["sessions"] = []

    for session in load_sessions():
        target = by_id.get(session.get("project_id")) or by_name.get(session.get("project_name", ""))
        if target is not None:
            session["project_name"] = target.get("name", session.get("project_name", ""))  # актуальное имя
            target["sessions"].append(session)


def save_session(project: dict, session: dict) -> bool:
    """Записать одну сессию отдельным файлом."""
    try:
        session.setdefault("id", _new_id())
        session["project_id"] = project.get("id", "")
        stamp = datetime.fromtimestamp(session.get("timestamp", 0)).strftime("%Y-%m-%d_%H-%M-%S")
        path = sessions_dir() / f"{stamp}_{session['id'][:8]}.json"
        _write_json(path, session)
        return True
    except Exception as exc:
        print(f"[storage] не удалось сохранить сессию: {exc}")
        return False


def delete_project_sessions(project: dict) -> None:
    """Удалить файлы сессий, привязанных к проекту (при удалении проекта).

    Перед вызовом полезно сделать attach_sessions(), чтобы учесть сессии,
    пришедшие через синхронизацию.
    """
    ids = {s.get("id") for s in project.get("sessions", []) if s.get("id")}
    if not ids:
        return
    for path in _session_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue   # чужой или битый файл — не трогаем
        if data.get("id") in ids:
            try:
                path.unlink()
            except OSError as exc:
                print(f"[storage] не удалось удалить {path.name}: {exc}")
