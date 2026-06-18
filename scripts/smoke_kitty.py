#!/usr/bin/env python3
"""Smoke test: o terminal atual fala o kitty graphics protocol?

Sem dependências (nem Pillow). Gera um quadrado de gradiente em RGB cru e
transmite via kitty graphics protocol. Se você ver um quadrado colorido,
o terminal suporta imagem inline — caminho livre pro emote da Ada.

Uso (DENTRO do Ghostty):
    python3 ~/.hermes/plugins/ada-emote/scripts/smoke_kitty.py
    # opcional: testar com um PNG seu
    python3 ~/.hermes/plugins/ada-emote/scripts/smoke_kitty.py /caminho/imagem.png

Se rodar no Apple Terminal.app, NADA aparece — isso é esperado, ele não
suporta o protocolo.
"""
import base64
import os
import sys


def _term_info() -> str:
    return (
        f"TERM={os.environ.get('TERM','?')}  "
        f"TERM_PROGRAM={os.environ.get('TERM_PROGRAM','?')}  "
        f"KITTY_WINDOW_ID={os.environ.get('KITTY_WINDOW_ID','-')}"
    )


def _write_kitty(payload_b64: bytes, control: dict) -> None:
    """Emite uma imagem kitty em chunks de até 4096 chars base64."""
    ctrl = ",".join(f"{k}={v}" for k, v in control.items())
    chunk = 4096
    if len(payload_b64) <= chunk:
        sys.stdout.write(f"\x1b_G{ctrl};{payload_b64.decode()}\x1b\\")
        sys.stdout.flush()
        return
    first = True
    i = 0
    while i < len(payload_b64):
        piece = payload_b64[i : i + chunk]
        i += chunk
        more = 1 if i < len(payload_b64) else 0
        if first:
            sys.stdout.write(f"\x1b_G{ctrl},m={more};{piece.decode()}\x1b\\")
            first = False
        else:
            sys.stdout.write(f"\x1b_Gm={more};{piece.decode()}\x1b\\")
    sys.stdout.flush()


def test_generated_gradient() -> None:
    w = h = 160
    buf = bytearray()
    for y in range(h):
        for x in range(w):
            buf += bytes(((x * 255) // w, (y * 255) // h, 128))
    payload = base64.b64encode(bytes(buf))
    print("\n[1] Gradiente RGB gerado na hora (sem PNG, sem Pillow):")
    _write_kitty(payload, {"a": "T", "f": "24", "s": str(w), "v": str(h)})
    print("\n    ^ se você vê um quadrado colorido acima, kitty graphics FUNCIONA.\n")


def test_png_file(path: str) -> None:
    with open(path, "rb") as f:
        data = f.read()
    payload = base64.b64encode(data)
    print(f"\n[2] PNG do arquivo {path} (f=100, terminal decodifica):")
    _write_kitty(payload, {"a": "T", "f": "100"})
    print("\n    ^ se você vê a imagem acima, dá pra usar seus PNGs direto.\n")


def main() -> None:
    print("== smoke test kitty graphics ==")
    print(_term_info())
    if os.environ.get("TERM_PROGRAM") == "Apple_Terminal":
        print(
            "\n!! Você está no Apple Terminal.app — ele NÃO suporta imagem inline.\n"
            "   Rode este script DENTRO do Ghostty para o teste valer.\n"
        )
    test_generated_gradient()
    if len(sys.argv) > 1:
        test_png_file(sys.argv[1])
    print("Fim. Reporte o que apareceu (quadrado? imagem? nada?).")


if __name__ == "__main__":
    main()
