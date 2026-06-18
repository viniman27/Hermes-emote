"""Config em camadas com defaults. Arquivo: ~/.hermes/plugins/hermes-emote/config.yaml"""
from __future__ import annotations

from pathlib import Path

import yaml

from .log import get_logger

PLUGIN_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PLUGIN_DIR / "config.yaml"

DEFAULTS: dict = {
    "enabled": True,
    "emote_set": "Hermes",        # pasta sob emotes/
    "rows": 10,                # altura do emote em células (largura = rows*2)
    "hide_below_cols": 60,     # esconde o widget se o terminal for mais estreito
    "reserve_rows": 10,        # esconde o emote se faltar altura p/ o resto (status/réguas/prompt)
    "show_info": True,         # texto informativo à direita da imagem (nome/estado/modelo/ctx)
    "info_color": "#ff5b5b",   # cor base (vermelho) do painel lateral
    "show_gateway": True,      # mostra "✈ Telegram: N" quando há pedido em andamento no gateway
    "phrases": [               # frases do Hermes que rotacionam no painel lateral
        "afiando a lâmina",
        "observando em silêncio",
        "medindo riscos",
        "sempre alerta",
        "pronta pra próxima",
    ],
    "phrase_rotate_s": 12,     # troca de frase a cada N segundos (0 = desliga as frases)
    "talk_tick_ms": 120,       # troca de frame ao "falar"
    "blink_min_ms": 3000,
    "blink_max_ms": 6000,
    "cycle_ms": 500,           # ciclo de frames em estados com múltiplos quadros
    "idle_cycle_ms": 900,      # ritmo do ciclo entre os frames de idle (idle, idle3..idleN)
    "idle_blink": True,        # piscar em idle (insere idle_blink no meio do ciclo)
    "blink_close_ms": 140,     # quanto tempo os olhos ficam fechados por piscada
    "cache_px": 384,           # reduz as imagens neste tamanho no preload (Pillow)
    "hold_ms": {               # quanto tempo segurar estados transitórios antes de voltar a idle
        "hi": 2000,
        "success": 1200,
        "failure": 1500,
        "compact": 1500,
    },
}


def load() -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    try:
        if CONFIG_PATH.exists():
            data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
            for k, v in data.items():
                if k == "hold_ms" and isinstance(v, dict):
                    cfg["hold_ms"] = {**DEFAULTS["hold_ms"], **v}
                elif k in DEFAULTS:
                    cfg[k] = v
    except Exception as e:
        get_logger().info("config load error: %s", e)
    return cfg


def save(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
    except Exception as e:
        get_logger().info("config save error: %s", e)
