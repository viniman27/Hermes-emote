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
        elif st == "idle":
            reg = self._idle_regular()
            self._cur = reg[0] if reg else frames[0]
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

    def _idle_regular(self):
        """Frames de idle 'olhos abertos' (exclui o frame de piscar)."""
        frames = self._frames("idle")
        if not frames:
            return []
        blink_name = (self.a.meta.get("idle") or {}).get("blink")
        reg = [p for p in frames if p.name != blink_name]
        return reg or frames

    def _idle_blink_frame(self):
        frames = self._frames("idle")
        if len(frames) < 2:
            return None
        names = {p.name: p for p in frames}
        bn = (self.a.meta.get("idle") or {}).get("blink")
        return names.get(bn) if bn else frames[-1]

    def idle_animated(self) -> bool:
        """idle anima se há piscar OU mais de um frame regular p/ ciclar."""
        return bool(self.cfg.get("idle_blink")) or len(self._idle_regular()) > 1

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
        elif st == "idle" and self.idle_animated():
            self._tick_idle(now)
        return self._cur

    def _tick_idle(self, now: float) -> None:
        """idle: cicla lentamente entre os frames regulares e pisca às vezes."""
        reg = self._idle_regular()
        if not reg:
            self._cur = None
            return
        # piscada tem prioridade
        if self.cfg.get("idle_blink"):
            blink = self._idle_blink_frame()
            if blink is not None and now >= self._blink_next:
                if now - self._blink_next < float(self.cfg.get("blink_close_ms", 140)) / 1000.0:
                    self._cur = blink       # olhos fechados
                    return
                self._blink_next = self._sched_blink()  # reabre e reagenda
        # ciclo lento dos frames regulares
        if len(reg) > 1:
            cyc = max(1, int(self.cfg.get("idle_cycle_ms", 900))) / 1000.0
            self._cur = reg[int(now / cyc) % len(reg)]
        else:
            self._cur = reg[0]

    def current(self) -> Path | None:
        return self._cur
