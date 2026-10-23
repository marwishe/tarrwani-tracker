"""Core focus-timer engine.

Drives the focus/break cycle for a single project, runs configured
bash/shell scripts on triggers, and supports AFK auto-pause.

This object is UI-agnostic: it only emits Qt signals describing the current
state. The UI (e.g. ActiveTimerCard) subscribes to these signals and renders
them however it likes.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QObject, QTimer, Signal

from core.afk_detector import AFKMonitor
from core.script_runner import run_script

# How many seconds of inactivity before the timer is considered "AFK".
AFK_THRESHOLD_SEC = 60


class TimerEngine(QObject):
    """Manages the focus/break/cycle state machine for one running project."""

    # Emitted once per second (and on every state change) with a full
    # snapshot — see `state()` for the shape of the dict.
    sig_tick = Signal(dict)

    # Emitted when the phase changes ("focus" <-> "break").
    sig_phase_changed = Signal(str)

    # Emitted once the whole timer (all cycles) has completed normally.
    sig_finished = Signal()

    # Emitted whenever the AFK-pause state toggles.
    sig_afk_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._afk = AFKMonitor()

        self._project: dict | None = None
        self._reset_state()

    # ── State reset ──────────────────────────────────────────
    def _reset_state(self) -> None:
        self._project = None
        self._phase = "focus"          # "focus" | "break"
        self._cycle = 1
        self._total_cycles = 1
        self._total_breaks = 0
        self._breaks_done = 0
        self._phase_total = 0
        self._phase_remaining = 0
        self._is_paused = False        # manual pause
        self._is_afk_paused = False    # automatic AFK pause
        self._running = False

    # ── Public properties ───────────────────────────────────
    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_afk_paused(self) -> bool:
        return self._is_afk_paused

    @property
    def project(self) -> dict | None:
        return self._project

    # ── Control ──────────────────────────────────────────────
    def start(self, project: dict) -> None:
        """Start (or restart) the timer for the given project dict."""
        self._reset_state()
        self._project = project

        self._total_cycles = max(1, int(project.get("cycles", 1)))
        self._total_breaks = max(0, self._total_cycles - 1)
        self._cycle = 1
        self._breaks_done = 0

        self._phase = "focus"
        self._phase_total = max(1, int(project.get("focus_min", 25))) * 60
        self._phase_remaining = self._phase_total

        self._running = True

        if project.get("afk_tracking", False):
            self._afk.start()
        else:
            self._afk.stop()

        self._timer.start()
        self._emit_tick()

    def stop(self) -> None:
        """Stop the timer immediately (manual cancel)."""
        self._timer.stop()
        self._afk.stop()
        was_running = self._running
        self._reset_state()
        if was_running:
            self._emit_tick()

    def toggle_pause(self) -> None:
        """Toggle manual pause/resume."""
        if not self._running:
            return
        self._is_paused = not self._is_paused
        self._emit_tick()

    # ── Tick handling ────────────────────────────────────────
    def _on_tick(self) -> None:
        if not self._running:
            return

        # AFK check (only if enabled for this project)
        if self._project and self._project.get("afk_tracking", False):
            idle = self._afk.idle_seconds()
            afk_now = idle >= AFK_THRESHOLD_SEC
            if afk_now != self._is_afk_paused:
                self._is_afk_paused = afk_now
                self.sig_afk_changed.emit(afk_now)

        if self._is_paused or self._is_afk_paused:
            # Still emit a tick so the UI can show the "paused" badge,
            # but don't consume any time.
            self._emit_tick()
            return

        self._phase_remaining -= 1
        if self._phase_remaining <= 0:
            self._advance_phase()
            return

        self._emit_tick()

    def _advance_phase(self) -> None:
        assert self._project is not None

        if self._phase == "focus":
            self._run_scripts("on_focus_end")

            if self._cycle >= self._total_cycles:
                # All cycles done -> finish.
                self._run_scripts("on_timer_complete")
                self._timer.stop()
                self._afk.stop()
                self._running = False
                self.sig_finished.emit()
                self._emit_tick()
                return

            # Move to the break of this cycle.
            self._phase = "break"
            self._phase_total = max(1, int(self._project.get("break_min", 5))) * 60
            self._phase_remaining = self._phase_total
            self.sig_phase_changed.emit("break")

        else:  # phase == "break"
            self._run_scripts("on_break_end")
            self._breaks_done += 1
            self._cycle += 1

            self._phase = "focus"
            self._phase_total = max(1, int(self._project.get("focus_min", 25))) * 60
            self._phase_remaining = self._phase_total
            self.sig_phase_changed.emit("focus")

        self._emit_tick()

    # ── Scripts ──────────────────────────────────────────────
    def _run_scripts(self, trigger: str) -> None:
        if not self._project:
            return

        raw = self._project.get("scripts", {})
        if isinstance(raw, list):
            parts = [s["command"] for s in raw if s.get("trigger") == trigger and s.get("command", "").strip()]
            code = "\n".join(parts).strip()
        elif isinstance(raw, dict):
            code = (raw.get(trigger) or "").strip()
        else:
            code = ""
        if not code:
            return

        env = os.environ.copy()
        env["PROJECT_NAME"] = str(self._project.get("name", ""))
        env["CYCLE"] = str(self._cycle)
        env["ELAPSED_MIN"] = str(self._phase_total // 60)

        try:
            run_script(code, env)   # shell на Windows, bash на Linux/macOS
        except Exception as exc:  # pragma: no cover - best effort
            print(f"[TimerEngine] script '{trigger}' failed: {exc}")

    # ── Snapshot ─────────────────────────────────────────────
    def _emit_tick(self) -> None:
        self.sig_tick.emit(self.state())

    def state(self) -> dict:
        """Full state snapshot consumed by the UI."""
        return {
            "running":         self._running,
            "project":         self._project,
            "phase":           self._phase,             # "focus" | "break"
            "cycle":           self._cycle,
            "total_cycles":    self._total_cycles,
            "breaks_done":     self._breaks_done,
            "total_breaks":    self._total_breaks,
            "phase_total":     self._phase_total,
            "phase_remaining": max(self._phase_remaining, 0),
            "is_paused":       self._is_paused,
            "is_afk_paused":   self._is_afk_paused,
        }