#!/usr/bin/env python3
"""Smoke test nº2: imagem inline DENTRO do prompt_toolkit (via kitty placeholders).

Prova a parte difícil — colocar a imagem numa grade de células do prompt_toolkit
sem brigar com o cursor. Mostra a Hermes idle num Window; ESPAÇO troca de imagem
(idle -> think -> talk_mid), 'q' sai.

Rodar DENTRO do Ghostty com o python do Hermes:
    ~/.hermes/hermes-agent/.venv/bin/python \
        ~/.hermes/plugins/hermes-emote/scripts/smoke_pt_image.py

Se as imagens do Hermes aparecerem acima da barra de ajuda e trocarem ao apertar
espaço, o caminho está provado e dá pra embutir no Hermes.
"""
import sys
from pathlib import Path

# Torna o pacote hermes_emote importável (kitty.py).
PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN))

from hermes_emote import kitty  # noqa: E402
from prompt_toolkit import Application  # noqa: E402
from prompt_toolkit.output.color_depth import ColorDepth  # noqa: E402
from prompt_toolkit.key_binding import KeyBindings  # noqa: E402
from prompt_toolkit.layout import HSplit, Layout, Window  # noqa: E402
from prompt_toolkit.layout.controls import FormattedTextControl  # noqa: E402

EMOTES = PLUGIN / "emotes" / "Hermes"
ROWS = 10          # altura do emote em células
COLS = ROWS * 2    # largura (≈ quadrado, célula é ~1:2)

# (label, caminho, id estável)
FRAMES = [
    ("idle", EMOTES / "idle" / "idle.png", 11),
    ("think", EMOTES / "think" / "think.png", 12),
    ("talk_mid", EMOTES / "talk" / "talk_mid.png", 13),
]

state = {"i": 0}


def _transmit_all():
    for _label, fp, img_id in FRAMES:
        if fp.exists():
            kitty.transmit(fp, img_id, COLS, ROWS)


def _emote_fragments():
    _label, _fp, img_id = FRAMES[state["i"] % len(FRAMES)]
    return kitty.placeholder_fragments(img_id, COLS, ROWS)


def _help_fragments():
    label = FRAMES[state["i"] % len(FRAMES)][0]
    return [("", f"  estado: {label}   ·   ESPAÇO troca   ·   q sai")]


def main():
    if not EMOTES.exists():
        print(f"!! pasta de emotes não encontrada: {EMOTES}")
        return
    _transmit_all()

    kb = KeyBindings()

    @kb.add("q")
    @kb.add("c-c")
    def _(event):
        event.app.exit()

    @kb.add("space")
    def _(event):
        state["i"] += 1
        event.app.invalidate()

    body = HSplit([
        Window(content=FormattedTextControl(_emote_fragments), height=ROWS),
        Window(content=FormattedTextControl(_help_fragments), height=1),
    ])
    app = Application(
        layout=Layout(body),
        key_bindings=kb,
        full_screen=False,
        color_depth=ColorDepth.DEPTH_24_BIT,  # id da imagem vai na cor: NÃO rebaixar
    )
    app.run()
    # limpa as imagens do terminal ao sair
    for _l, _f, img_id in FRAMES:
        kitty.delete_image(img_id)
    print("ok — saiu do smoke test.")


if __name__ == "__main__":
    main()
