"""Kitty graphics — renderização de imagem inline via *unicode placeholders*.

Esta é a técnica que permite colocar uma imagem dentro de uma grade de células
(prompt_toolkit): a imagem é transmitida uma vez ao terminal (por id) criando um
*virtual placement*; depois, células com o caractere U+10EEEE + diacríticos de
linha/coluna, com o id codificado na cor de frente, fazem o terminal desenhar a
imagem ali. O prompt_toolkit só vê "texto" e mede/limpa a área corretamente.

Suportado por Ghostty/kitty. Não depende de Pillow.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

# Caractere base do placeholder (kitty).
PLACEHOLDER = "\U0010EEEE"

# Tabela oficial de diacríticos linha/coluna do kitty (rowcolumn-diacritics).
# Índice i -> code point que representa a linha/coluna i. Prefixo suficiente
# para imagens de até ~48 células em cada eixo (emote usa muito menos).
_DIACRITICS = [
    0x0305, 0x030D, 0x030E, 0x0310, 0x0312, 0x033D, 0x033E, 0x033F, 0x0346,
    0x034A, 0x034B, 0x034C, 0x0350, 0x0351, 0x0352, 0x0357, 0x035B, 0x0363,
    0x0364, 0x0365, 0x0366, 0x0367, 0x0368, 0x0369, 0x036A, 0x036B, 0x036C,
    0x036D, 0x036E, 0x036F, 0x0483, 0x0484, 0x0485, 0x0486, 0x0487, 0x0592,
    0x0593, 0x0594, 0x0595, 0x0597, 0x0598, 0x0599, 0x059C, 0x059D, 0x059E,
    0x059F, 0x05A0, 0x05A1,
]


def _diac(i: int) -> str:
    return chr(_DIACRITICS[i])


def transmit(
    image_path: str | Path,
    image_id: int,
    cols: int,
    rows: int,
    *,
    out=None,
) -> None:
    """Transmite a imagem e cria um *virtual placement* (id=image_id).

    Não desenha no cursor (U=1). As células de placeholder é que disparam o
    desenho. Idempotente o suficiente: re-transmitir o mesmo id só re-armazena.
    """
    out = out or sys.stdout
    data = Path(image_path).read_bytes()
    b64 = base64.b64encode(data)
    chunk = 4096
    control = f"a=T,U=1,i={image_id},c={cols},r={rows},f=100,q=2"
    i = 0
    first = True
    n = len(b64)
    if n == 0:
        return
    while i < n:
        piece = b64[i : i + chunk]
        i += chunk
        more = 1 if i < n else 0
        if first:
            out.write(f"\x1b_G{control},m={more};{piece.decode()}\x1b\\")
            first = False
        else:
            out.write(f"\x1b_Gm={more};{piece.decode()}\x1b\\")
    out.flush()


def placeholder_fragments(image_id: int, cols: int, rows: int,
                          side_lines=None, side_style: str = "fg:ansibrightblack"):
    """Fragmentos prompt_toolkit que desenham a imagem (id) numa grade rows×cols.

    Retorna uma lista de tuplas (style, text) com '\\n' entre linhas. O id da
    imagem vai na cor de frente (truecolor = id de 24 bits): id 5 -> #000005.

    ``side_lines`` (opcional): lista de strings (len == rows) renderada à direita
    da imagem, em ``side_style``. Cada item é o texto da linha (ou "" para vazio).
    São fragmentos separados — não afetam as células da imagem.
    """
    style = f"fg:#{image_id & 0xFFFFFF:06x}"
    side_lines = side_lines or []
    frags = []
    for r in range(rows):
        row_text = "".join(PLACEHOLDER + _diac(r) + _diac(c) for c in range(cols))
        frags.append((style, row_text))
        if r < len(side_lines) and side_lines[r]:
            item = side_lines[r]
            st, txt = item if isinstance(item, tuple) else (side_style, item)
            if txt:
                frags.append((st, "  " + txt))
        if r < rows - 1:
            frags.append(("", "\n"))
    return frags


def delete_image(image_id: int, *, out=None) -> None:
    """Remove a imagem/placement do terminal (ao desligar o emote)."""
    out = out or sys.stdout
    out.write(f"\x1b_Ga=d,d=i,i={image_id},q=2;\x1b\\")
    out.flush()
