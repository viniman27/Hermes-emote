"""Log em arquivo — nunca quebra o Hermes; só registra para diagnóstico."""
from __future__ import annotations

import logging
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = PLUGIN_DIR / "hermes-emote.log"

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    lg = logging.getLogger("hermes_emote")
    lg.setLevel(logging.INFO)
    lg.propagate = False
    try:
        h = logging.FileHandler(LOG_PATH)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        lg.addHandler(h)
    except Exception:
        lg.addHandler(logging.NullHandler())
    _logger = lg
    return lg
