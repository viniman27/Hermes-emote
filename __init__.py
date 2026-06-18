"""ada-emote — widget de emote visual da Ada para o TUI do Hermes.

Plugin de usuário (à prova de update). Renderiza imagens inline via kitty
graphics (Ghostty/kitty/WezTerm/iTerm2), reagindo aos estados do agente.
Não edita o cli.py do Hermes; tudo é monkey-patch defensivo.
"""
from __future__ import annotations

import os


def register(ctx) -> None:
    # O id da imagem é codificado na cor de frente -> truecolor obrigatório.
    # Best-effort cedo (o app já-criado também é forçado pelo widget).
    os.environ.setdefault("PROMPT_TOOLKIT_COLOR_DEPTH", "DEPTH_24_BIT")

    from .ada_emote import patch

    try:
        patch.install()
    except Exception:
        # Nunca quebrar o Hermes por causa do emote.
        pass

    ctx.register_command(
        "ada-emote",
        _cmd,
        description="Controla o emote visual da Ada (on/off/status)",
        args_hint="on|off|status",
    )


def _cmd(raw_args: str):
    from .ada_emote import patch

    em = patch.get_emote()
    arg = (raw_args or "").strip().lower()

    if em is None:
        return "ada-emote: não está ativo. Veja ~/.hermes/plugins/ada-emote/ada-emote.log"

    if arg in ("on", "ligar"):
        em.set_enabled(True)
        return "ada-emote: ligado."
    if arg in ("off", "desligar"):
        em.set_enabled(False)
        return "ada-emote: desligado."

    # status (padrão)
    term = os.environ.get("TERM_PROGRAM", "?")
    states = ", ".join(sorted(em.assets.frames)) or "(nenhum)"
    nframes = sum(len(v) for v in em.assets.frames.values())
    lines = [
        f"ada-emote: {'ligado' if em.cfg.get('enabled') else 'desligado'}"
        f" · set={em.cfg['emote_set']} · {len(em.assets.frames)} estados / {nframes} frames",
        f"  estado atual: {em.animator.state} · grade {em.cols}x{em.rows} · terminal {term}"
        f" · truecolor={'sim' if em._forced_depth else 'pendente'}",
        f"  estados disponíveis: {states}",
        "  comandos: /ada-emote on | off | status",
    ]
    if term == "Apple_Terminal":
        lines.append("  ⚠ Apple Terminal NÃO renderiza imagem inline — use o Ghostty.")
    return "\n".join(lines)
