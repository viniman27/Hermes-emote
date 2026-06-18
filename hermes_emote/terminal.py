"""Detecção de terminal: escolhe o renderer de imagem (kitty vs sixel).

A escolha pode ser forçada por config (`renderer: kitty|sixel|auto`) ou pela
env `HERMES_EMOTE_RENDER`. Em `auto`, inspeciona variáveis de ambiente.

Tabela de decisão (auto):
  - kitty / Ghostty / WezTerm  -> "kitty"  (kitty graphics protocol)
  - Windows Terminal / mlterm  -> "sixel"
  - desconhecido               -> "kitty"  (mais comum entre terminais modernos)
"""
from __future__ import annotations

import os

VALID = ("kitty", "sixel")


def detect(config: dict | None = None) -> str:
    """Retorna 'kitty' ou 'sixel'."""
    # 1) override explícito
    env_force = os.environ.get("HERMES_EMOTE_RENDER", "").strip().lower()
    if env_force in VALID:
        return env_force
    pref = str((config or {}).get("renderer", "auto")).strip().lower()
    if pref in VALID:
        return pref

    e = os.environ
    term = e.get("TERM", "").lower()
    term_program = e.get("TERM_PROGRAM", "").lower()

    # kitty
    if e.get("KITTY_WINDOW_ID") or "kitty" in term:
        return "kitty"
    # Ghostty
    if term_program == "ghostty" or e.get("GHOSTTY_RESOURCES_DIR") or e.get("GHOSTTY_BIN_DIR"):
        return "kitty"
    # WezTerm (fala kitty graphics)
    if term_program == "wezterm" or e.get("WEZTERM_PANE") or e.get("WEZTERM_EXECUTABLE"):
        return "kitty"
    # Windows Terminal -> sixel
    if e.get("WT_SESSION") or e.get("WT_PROFILE_ID"):
        return "sixel"
    # mlterm e afins anunciam sixel via TERM
    if "mlterm" in term or "sixel" in term:
        return "sixel"
    # padrão seguro
    return "kitty"
