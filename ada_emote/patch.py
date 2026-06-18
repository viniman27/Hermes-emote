"""Monkey-patch defensivo da HermesCLI — ÚNICO ponto de acoplamento.

Tudo aqui é à prova de falha: se um método esperado sumir num update do Hermes,
o emote se desliga sozinho e registra no log, sem nunca quebrar o Hermes.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .log import get_logger
from .widget import AdaEmote

PLUGIN_DIR = Path(__file__).resolve().parents[1]

_emote: AdaEmote | None = None
_window = None
_installed = False


def get_emote() -> AdaEmote | None:
    return _emote


def _term_cols() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _map_tool(name: str | None) -> str:
    n = (name or "").lower()
    if any(x in n for x in ("read", "search", "grep", "list", "glob", "cat",
                            "vision", "fetch", "view", "get_file", "open")):
        return "read"
    if any(x in n for x in ("write", "edit", "patch", "create", "replace",
                            "append", "apply", "insert", "delete")):
        return "write"
    return "tool"


def _build_window():
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl

    return Window(
        content=FormattedTextControl(_emote.fragments),
        height=(lambda: _emote.height()),
        wrap_lines=False,
    )


def _wrap(cls, name: str, before, log) -> None:
    """Embrulha cls.name para chamar `before(self, *a, **k)` antes do original."""
    orig = getattr(cls, name, None)
    if orig is None:
        log.info("hook ausente (update mudou a API?): %s — emote parcial", name)
        return
    if getattr(orig, "_ada_wrapped", False):
        return

    def wrapped(self, *a, **k):
        try:
            before(self, *a, **k)
        except Exception:
            pass
        return orig(self, *a, **k)

    wrapped._ada_wrapped = True  # type: ignore[attr-defined]
    setattr(cls, name, wrapped)


def install() -> bool:
    """Aplica o patch. Retorna True se o ponto essencial (widget) foi instalado."""
    global _emote, _window, _installed
    log = get_logger()
    if _installed:
        return True
    try:
        import cli  # cli.py do Hermes é importável como módulo "cli"
    except Exception as e:
        log.info("não consegui importar cli: %s — emote desligado", e)
        return False

    cls = getattr(cli, "HermesCLI", None)
    if cls is None:
        log.info("HermesCLI não encontrada — emote desligado")
        return False

    _emote = AdaEmote(PLUGIN_DIR)
    if not _emote.assets.available():
        log.info("nenhum frame em emotes/%s — emote inerte", _emote.cfg["emote_set"])

    # 1) ponto essencial: injeção do widget no layout do TUI
    orig_widgets = getattr(cls, "_get_extra_tui_widgets", None)
    if orig_widgets is None:
        log.info("_get_extra_tui_widgets ausente — emote NÃO pode renderizar")
        return False
    if not getattr(orig_widgets, "_ada_wrapped", False):
        def _patched_widgets(self):
            widgets = list(orig_widgets(self))
            try:
                global _window
                _emote.attach(self)
                if _window is None:
                    _window = _build_window()
                widgets.append(_window)
            except Exception as e:
                log.info("falha ao injetar widget: %s", e)
            return widgets

        _patched_widgets._ada_wrapped = True  # type: ignore[attr-defined]
        setattr(cls, "_get_extra_tui_widgets", _patched_widgets)

    # 2) telemetria de estado (cada um é opcional/independente)
    _wrap(cls, "_on_thinking",
          lambda self, text="", *a, **k: _emote.set_state("think") if text else None, log)
    _wrap(cls, "_stream_delta",
          lambda self, text="", *a, **k: _emote.set_state("talk"), log)
    _wrap(cls, "_on_tool_gen_start",
          lambda self, tool_name="", *a, **k: _emote.set_state("tool"), log)
    _wrap(cls, "_on_tool_progress", _on_progress, log)

    _installed = True
    log.info("ada-emote: patch instalado")
    return True


def _on_progress(self, event_type, function_name=None, *a, **k):
    if event_type == "tool.started":
        _emote.set_state(_map_tool(function_name))
    elif event_type == "tool.completed" and k.get("is_error"):
        _emote.set_state("failure")
