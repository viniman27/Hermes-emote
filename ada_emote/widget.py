"""AdaEmote — orquestra estado + assets + renderer e injeta no TUI do Hermes.

Pontos-chave de segurança:
- Transmissão de imagem (escreve no stdout) só acontece no preload, chamado em
  momento pré-render (primeira montagem do layout). Durante a sessão, trocar de
  frame é só trocar qual id as células referenciam — sem I/O, thread-safe.
- A função de render (``fragments``) é pura: só lê o id atual e devolve células.
"""
from __future__ import annotations

import threading
import time
import weakref
from pathlib import Path

from . import config as _config
from . import kitty
from .animator import Animator
from .assets import Assets
from .log import get_logger

STATE_LABELS = {
    "idle": "ociosa", "think": "pensando", "talk": "respondendo",
    "read": "lendo", "write": "escrevendo", "tool": "ferramenta",
    "failure": "erro", "hi": "olá", "compact": "compactando", "success": "feito",
}


class AdaEmote:
    def __init__(self, plugin_dir: Path):
        self.log = get_logger()
        self.cfg = _config.load()
        self.rows = max(2, int(self.cfg["rows"]))
        self.cols = self.rows * 2
        self.assets = Assets(plugin_dir, str(self.cfg["emote_set"]), self.rows, self.cols,
                             cache_px=int(self.cfg["cache_px"]))
        self.animator = Animator(self.assets, self.cfg)
        self.lock = threading.RLock()
        self._cli_ref = None
        self._thread: threading.Thread | None = None
        self._stop = False
        self._preloaded = False
        self._last_id: int | None = None
        self._prev_running = False
        self._forced_depth = False
        self._info_lines: list[str] = []
        self._info_t = 0.0
        self._last_term_size = None
        self._resize_pending = 0.0

    # ---- estado ----
    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled")) and self.assets.available()

    def set_enabled(self, val: bool) -> None:
        with self.lock:
            self.cfg["enabled"] = bool(val)
            _config.save(self.cfg)
            if val:
                self.animator.set_state("hi")
                self._sync_current()
        self._invalidate(force=True)

    def set_state(self, state: str) -> None:
        if not self.enabled:
            return
        with self.lock:
            self.animator.set_state(state)
            self._sync_current()
        self._invalidate()

    def _sync_current(self) -> None:
        """Atualiza o id a renderizar. Após preload, ensure_transmitted é no-op."""
        path = self.animator.current()
        if path is None:
            self._last_id = None
            return
        self._last_id = self.assets.ensure_transmitted(path)

    # ---- render (puro, sem I/O) ----
    def height(self) -> int:
        if not self.enabled:
            return 0
        import shutil
        try:
            sz = shutil.get_terminal_size((100, 24))
            cols, lines = sz.columns, sz.lines
        except Exception:
            cols, lines = 100, 24
        # estreito demais: esconde
        if cols < int(self.cfg["hide_below_cols"]):
            return 0
        # baixo demais: esconde p/ NÃO espremer status bar + réguas + prompt
        if lines < self.rows + int(self.cfg.get("reserve_rows", 10)):
            return 0
        return self.rows

    def fragments(self):
        with self.lock:
            if not self.enabled or self._last_id is None:
                return []
            side = self._aligned_side(self.rows, self.cols)
            return kitty.placeholder_fragments(self._last_id, self.cols, self.rows,
                                               side_lines=side)

    def _aligned_side(self, rows: int, cols: int):
        """Lista (len rows) com as infos centradas verticalmente, truncadas à largura."""
        info = list(self._info_lines or [])
        if not info:
            return None
        import shutil
        try:
            term = shutil.get_terminal_size().columns
        except Exception:
            term = 80
        maxw = max(8, term - cols - 4)
        info = [(t[: maxw - 1] + "…") if len(t) > maxw else t for t in info]
        offset = max(0, (rows - len(info)) // 2)
        side = [""] * rows
        for i, t in enumerate(info):
            if offset + i < rows:
                side[offset + i] = t
        return side

    def _check_resize(self, cli, now: float) -> bool:
        """Detecta resize. NÃO escreve escapes (isso corromperia o prompt_toolkit).

        Durante o arraste, devolve True (o loop pausa a animação p/ não brigar com
        a recuperação de resize do Hermes). Quando o resize ASSENTA, limpa a flag
        ``_status_bar_suppressed_after_resize`` do Hermes — que ele só limparia na
        próxima entrada do usuário — pra a barra de status e as réguas voltarem.
        """
        import shutil
        try:
            sz = shutil.get_terminal_size((100, 24))
            cur = (sz.columns, sz.lines)
        except Exception:
            return False
        if cur != self._last_term_size:
            self._last_term_size = cur
            self._resize_pending = now
            return True
        if self._resize_pending:
            if (now - self._resize_pending) < 0.25:
                return True  # ainda assentando
            self._resize_pending = 0.0
            try:
                cli._status_bar_suppressed_after_resize = False
            except Exception:
                pass
            self._invalidate(force=True)
        return False

    def _phrase(self, now: float) -> str | None:
        phrases = self.cfg.get("phrases") or []
        rotate = int(self.cfg.get("phrase_rotate_s", 12) or 0)
        if not phrases or rotate <= 0:
            return None
        return str(phrases[int(now // rotate) % len(phrases)])

    def _refresh_info(self, cli, now: float) -> None:
        """Atualiza as infos laterais fora do render (a cada ~0.8s)."""
        if now - self._info_t < 0.8:
            return
        self._info_t = now
        if not self.cfg.get("show_info", True):
            self._info_lines = []
            return
        lines = ["Ada"]
        phrase = self._phrase(now)
        if phrase:
            lines.append(f"“{phrase}”")
        lines.append("· " + STATE_LABELS.get(self.animator.state, self.animator.state))
        try:
            snap = cli._get_status_bar_snapshot()
            model = snap.get("model_short")
            if model:
                lines.append("⚕ " + str(model))
            pct = snap.get("context_percent")
            if pct is not None:
                lines.append(f"ctx {pct}%")
            bg = int(snap.get("active_background_tasks", 0) or 0) + \
                int(snap.get("active_background_processes", 0) or 0)
            if bg:
                lines.append(f"▶ {bg} em bg")
            dur = snap.get("duration")
            if dur:
                lines.append(str(dur))
        except Exception:
            pass
        self._info_lines = lines

    # ---- ciclo de vida ----
    def attach(self, cli) -> None:
        """Chamado na primeira montagem do layout (pré-render): seguro p/ preload."""
        self._cli_ref = weakref.ref(cli)
        if not self._preloaded:
            try:
                self.assets.preload()
                self._preloaded = True
                with self.lock:
                    self.animator.set_state("hi")
                    self._sync_current()
                self.log.info("ada-emote ativo: %d estados, %d frames",
                              len(self.assets.frames),
                              sum(len(v) for v in self.assets.frames.values()))
            except Exception as e:
                self.log.info("preload error: %s", e)
            # registra o tamanho atual p/ não disparar um redraw espúrio no boot
            try:
                import shutil
                sz = shutil.get_terminal_size((100, 24))
                self._last_term_size = (sz.columns, sz.lines)
            except Exception:
                pass
        self._start_thread()

    def _start_thread(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ada-emote-anim")
        self._thread.start()

    def _cli(self):
        return self._cli_ref() if self._cli_ref else None

    def _force_truecolor(self, cli) -> None:
        """O id da imagem vai na cor de frente — o app PRECISA renderizar em 24-bit.
        Determinístico: força no app já criado (independe do timing do env var)."""
        if self._forced_depth:
            return
        app = getattr(cli, "_app", None)
        if app is None:
            return
        try:
            from prompt_toolkit.output.color_depth import ColorDepth
            app._color_depth = ColorDepth.DEPTH_24_BIT
            self._forced_depth = True
            self.log.info("color depth forçado para DEPTH_24_BIT")
        except Exception as e:
            self.log.info("não consegui forçar color depth: %s", e)

    def _invalidate(self, force: bool = False) -> None:
        cli = self._cli()
        if cli is None:
            return
        try:
            cli._invalidate(min_interval=0.0 if force else 0.08)
        except Exception:
            pass

    def _loop(self) -> None:
        while not self._stop:
            cli = self._cli()
            if cli is None:
                time.sleep(0.2)
                continue
            try:
                if self.enabled and not self._forced_depth:
                    self._force_truecolor(cli)
                now = time.monotonic()
                if self._check_resize(cli, now):
                    # resize em andamento: não anima (evita brigar com a recuperação)
                    time.sleep(0.08)
                    continue
                self._refresh_info(cli, now)
                running = bool(getattr(cli, "_agent_running", False))
                # bordas do turno: começa pensando, termina em idle
                if running and not self._prev_running:
                    self.set_state("think")
                elif not running and self._prev_running:
                    self.set_state("idle")
                self._prev_running = running

                st = self.animator.state
                animated = self.enabled and (
                    running
                    or bool(self.cfg["hold_ms"].get(st))
                    or (st == "idle" and self.cfg.get("idle_blink"))
                )
                if animated:
                    with self.lock:
                        prev = self._last_id
                        self.animator.tick()
                        self._sync_current()
                        changed = self._last_id != prev
                    if changed:
                        self._invalidate()
                    time.sleep(max(0.05, self.cfg["talk_tick_ms"] / 2000.0))
                else:
                    time.sleep(0.15)
            except Exception:
                time.sleep(0.2)
