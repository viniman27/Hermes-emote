"""hermes-emote — widget de emote visual do Hermes para o TUI do Hermes.

Plugin de usuário (à prova de update). Renderiza imagens inline via kitty
graphics (Ghostty/kitty/WezTerm/iTerm2), reagindo aos estados do agente.
Não edita o cli.py do Hermes; tudo é monkey-patch defensivo.
"""
from __future__ import annotations

import os


def register(ctx) -> None:
    # Ponte gateway->CLI: registra se há pedido em andamento (ex.: Telegram).
    # Funciona no processo do gateway; no CLI é só leitura do arquivo.
    try:
        from .hermes_emote import gateway_link
        gateway_link.register_gateway_hooks(ctx)
    except Exception:
        pass

    # No processo do GATEWAY não há TUI — não instala o patch (evita importar a CLI).
    if os.environ.get("_HERMES_GATEWAY") == "1":
        ctx.register_command(
            "hermes-emote", _cmd,
            description="Controla o emote visual do Hermes (on/off/status)",
            args_hint="on|off|status",
        )
        return

    # O id da imagem é codificado na cor de frente -> truecolor obrigatório.
    # Best-effort cedo (o app já-criado também é forçado pelo widget).
    os.environ.setdefault("PROMPT_TOOLKIT_COLOR_DEPTH", "DEPTH_24_BIT")

    from .hermes_emote import patch

    try:
        patch.install()
    except Exception:
        # Nunca quebrar o Hermes por causa do emote.
        pass

    ctx.register_command(
        "hermes-emote",
        _cmd,
        description="Controla o emote visual do Hermes (on/off/status)",
        args_hint="on|off|status",
    )


def _cmd(raw_args: str):
    from .hermes_emote import patch

    em = patch.get_emote()
    arg = (raw_args or "").strip().lower()

    if em is None:
        return "hermes-emote: não está ativo. Veja ~/.hermes/plugins/hermes-emote/hermes-emote.log"

    if arg in ("on", "ligar"):
        em.set_enabled(True)
        return "hermes-emote: ligado."
    if arg in ("off", "desligar"):
        em.set_enabled(False)
        return "hermes-emote: desligado."

    # status (padrão)
    term = os.environ.get("TERM_PROGRAM", "?")
    states = ", ".join(sorted(em.assets.frames)) or "(nenhum)"
    nframes = sum(len(v) for v in em.assets.frames.values())
    lines = [
        f"hermes-emote: {'ligado' if em.cfg.get('enabled') else 'desligado'}"
        f" · set={em.cfg['emote_set']} · {len(em.assets.frames)} estados / {nframes} frames",
        f"  estado atual: {em.animator.state} · grade {em.cols}x{em.rows} · terminal {term}"
        f" · truecolor={'sim' if em._forced_depth else 'pendente'}",
        f"  estados disponíveis: {states}",
        "  comandos: /hermes-emote on | off | status",
    ]
    if term == "Apple_Terminal":
        lines.append("  ⚠ Apple Terminal NÃO renderiza imagem inline — use o Ghostty.")
    return "\n".join(lines)
