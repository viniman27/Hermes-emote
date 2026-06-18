"""Máquina de estados temporal — decide qual frame mostrar a cada instante.

Estados: idle, think, talk, read, write, tool, failure, hi, compact.
Estados transitórios (hold_ms) voltam sozinhos para idle.
"""
from __future__ import annotations

import random
import time
from pathlib import Path

CYCLE_STATES = {"read", "write", "tool", "think", "hi", "failure", "compact", "success"}


class Animator:
    def __init__(self, assets, cfg: dict):
        self.a = assets
        self.cfg = cfg
        self.state = "idle"
        self._t0 = time.monotonic()
        self._last_tick = 0.0
        self._blink_next = self._sched_blink()
        self._cur: Path | None = None
        self._pick()

    def _frames(self, st: str):
        return self.a.frames.get(st) or self.a.frames.get("idle") or []

    def has(self, st: str) -> bool:
        return st in self.a.frames

    def set_state(self, st: str) -> None:
        if st == self.state:
            return
        # estado sem assets: ignora (mantém o atual), exceto idle que sempre existe
        if st != "idle" and not self.has(st):
            return
        self.state = st
        self._t0 = time.monotonic()
        self._last_tick = 0.0
        self._pick()

    def _sched_blink(self) -> float:
        lo = self.cfg["blink_min_ms"] / 1000.0
        hi = self.cfg["blink_max_ms"] / 1000.0
        return time.monotonic() + random.uniform(lo, hi)

    def _pick(self) -> None:
        st = self.state
        frames = self._frames(st)
        if not frames:
            self._cur = None
            return
        if st == "talk":
            self._cur = self._pick_talk(frames)
        elif st in CYCLE_STATES and len(frames) > 1:
            cyc = max(1, int(self.cfg["cycle_ms"])) / 1000.0
            idx = int((time.monotonic() - self._t0) / cyc) % len(frames)
            self._cur = frames[idx]
        else:
            self._cur = frames[0]

    def _pick_talk(self, frames):
        names = {p.name: p for p in frames}
        weights = (self.a.meta.get("talk") or {}).get("weights")
        if weights:
            items = [(names[n], float(w)) for n, w in weights.items() if n in names]
            if items:
                paths, ws = zip(*items)
                return random.choices(paths, weights=ws, k=1)[0]
        return random.choice(frames)

    def tick(self) -> Path | None:
        """Avança o tempo; devolve o frame atual (pode ter mudado)."""
        now = time.monotonic()
        st = self.state

        hold = self.cfg["hold_ms"].get(st)
        if hold and (now - self._t0) * 1000.0 >= hold:
            self.set_state("idle")
            return self._cur

        if st == "talk":
            if (now - self._last_tick) * 1000.0 >= self.cfg["talk_tick_ms"]:
                self._last_tick = now
                self._cur = self._pick_talk(self._frames("talk"))
        elif st in CYCLE_STATES and len(self._frames(st)) > 1:
            self._pick()
        elif st == "idle" and self.cfg.get("idle_blink"):
            self._tick_idle_blink(now)
        return self._cur

    def _tick_idle_blink(self, now: float) -> None:
        frames = self._frames("idle")
        if len(frames) < 2:
            self._cur = frames[0] if frames else None
            return
        names = {p.name: p for p in frames}
        meta = self.a.meta.get("idle") or {}
        # olhos fechados: emotes.json["idle"]["blink"], senão o 2º frame
        blink = names.get(meta.get("blink")) if meta.get("blink") else frames[1]
        # olhos abertos: emotes.json["idle"]["default"], senão o 1º frame
        open_frame = names.get(meta.get("default")) or frames[0]
        close = float(self.cfg.get("blink_close_ms", 140)) / 1000.0
        if now >= self._blink_next:
            if now - self._blink_next < close:
                self._cur = blink           # piscada (olhos fechados)
            else:
                self._cur = open_frame       # reabre e agenda a próxima
                self._blink_next = self._sched_blink()
        else:
            self._cur = open_frame

    def current(self) -> Path | None:
        return self._cur
