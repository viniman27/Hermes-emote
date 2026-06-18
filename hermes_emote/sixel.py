"""Encoder sixel puro em Python (só Pillow) + integração com prompt_toolkit.

EXPERIMENTAL. Diferente do kitty (que prende a imagem a células via unicode
placeholders), o sixel é "desenhado" no cursor. Para conviver com o prompt_toolkit
usamos:
  - células em branco para RESERVAR a área (rows×cols);
  - um fragmento ``[ZeroWidthEscape]`` no fim que salva o cursor, sobe até o topo
    da área reservada, desenha o sixel POR CIMA das células em branco e restaura
    o cursor — assim o pt continua medindo o layout corretamente.

Limitações conhecidas (ver docs/SIXEL.md): assume a janela do emote na coluna 0;
o tamanho em células é aproximado (sixel é por pixel, não por célula).
"""
from __future__ import annotations

from pathlib import Path


def _rle(ch: str, count: int) -> str:
    return f"!{count}{ch}" if count >= 4 else ch * count


def encode(path: str | Path, max_w: int, max_h: int) -> str:
    """Carrega PNG, reduz para caber em max_w×max_h e devolve a string sixel."""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    im.thumbnail((max_w, max_h))
    q = im.quantize(colors=256)
    w, h = q.size
    data = list(q.getdata())            # índices de paleta, flat (y*w + x)
    pal = q.getpalette() or []
    used = sorted(set(data))

    out = ["\x1bP0;0;0q", f'"1;1;{w};{h}']
    for n in used:
        r = pal[n * 3] if n * 3 < len(pal) else 0
        g = pal[n * 3 + 1] if n * 3 + 1 < len(pal) else 0
        b = pal[n * 3 + 2] if n * 3 + 2 < len(pal) else 0
        out.append(f"#{n};2;{round(r * 100 / 255)};{round(g * 100 / 255)};{round(b * 100 / 255)}")

    for top in range(0, h, 6):
        bh = min(6, h - top)
        # acumula, por cor, o bitmask de cada coluna (1 passada pela banda)
        cols_for_color: dict[int, bytearray] = {}
        for dy in range(bh):
            row = data[(top + dy) * w:(top + dy) * w + w]
            bit = 1 << dy
            for x in range(w):
                n = row[x]
                arr = cols_for_color.get(n)
                if arr is None:
                    arr = bytearray(w)
                    cols_for_color[n] = arr
                arr[x] |= bit
        band_colors = sorted(cols_for_color)
        for ci, n in enumerate(band_colors):
            arr = cols_for_color[n]
            out.append(f"#{n}")
            prev = None
            count = 0
            line = []
            for x in range(w):
                ch = chr(63 + arr[x])
                if ch == prev:
                    count += 1
                else:
                    if prev is not None:
                        line.append(_rle(prev, count))
                    prev = ch
                    count = 1
            if prev is not None:
                line.append(_rle(prev, count))
            out.append("".join(line))
            if ci < len(band_colors) - 1:
                out.append("$")          # sobrepõe próxima cor na mesma banda
        out.append("-")                  # próxima banda
    out.append("\x1b\\")
    return "".join(out)


def fragments(sixel_str: str, cols: int, rows: int):
    """Fragmentos prompt_toolkit: reserva rows×cols e desenha o sixel por cima."""
    frags = []
    blank = " " * cols
    for r in range(rows):
        frags.append(("", blank))
        if r < rows - 1:
            frags.append(("", "\n"))
    up = rows - 1
    seq = "\x1b7"                         # salva cursor (fim da última linha)
    if up > 0:
        seq += f"\x1b[{up}A"              # sobe ao topo da área
    seq += "\r" + sixel_str + "\x1b8"     # vai à coluna 0, desenha, restaura cursor
    frags.append(("[ZeroWidthEscape]", seq))
    return frags
