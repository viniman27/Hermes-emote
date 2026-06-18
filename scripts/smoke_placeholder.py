#!/usr/bin/env python3
"""Diagnóstico: unicode placeholders SEM prompt_toolkit.

Isola o mecanismo de placeholder do prompt_toolkit. Transmite a Ada idle com
U=1 (virtual placement) e imprime as células de placeholder com a cor de frente
em truecolor (id na cor). Se a imagem aparecer, o Ghostty suporta placeholders e
o bug do teste anterior é só a profundidade de cor do prompt_toolkit.

Rodar DENTRO do Ghostty:
    python3 ~/.hermes/plugins/ada-emote/scripts/smoke_placeholder.py
"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN))
from ada_emote import kitty  # noqa: E402

IMG = PLUGIN / "emotes" / "Ada" / "idle" / "idle.png"
ROWS, COLS, IMG_ID = 10, 20, 13


def main():
    if not IMG.exists():
        print("imagem não encontrada:", IMG)
        return
    print("== placeholder SEM prompt_toolkit ==")
    print(f"id={IMG_ID} grade={COLS}x{ROWS} (cor de frente = #00000d)\n")

    kitty.transmit(IMG, IMG_ID, COLS, ROWS)

    # Imprime as células do placeholder com fg truecolor = id 13.
    sys.stdout.write(f"\x1b[38;2;0;0;{IMG_ID}m")
    for r in range(ROWS):
        for c in range(COLS):
            sys.stdout.write(kitty.PLACEHOLDER + chr(kitty._DIACRITICS[r]) + chr(kitty._DIACRITICS[c]))
        sys.stdout.write("\n")
    sys.stdout.write("\x1b[0m")
    sys.stdout.flush()
    print("\n^ apareceu a Ada idle? (s = placeholders OK / n = Ghostty sem suporte)")
    kitty.delete_image(IMG_ID)


if __name__ == "__main__":
    main()
