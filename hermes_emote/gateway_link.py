"""Ponte CLI <-> gateway: registra se há pedido em andamento (ex.: Telegram).

O Telegram roda no processo do *gateway* (separado do TUI). Não dá pra ler a
memória dele do CLI, então:

  - No processo do gateway, o hook ``pre_gateway_dispatch`` nos entrega o objeto
    ``gateway``. Capturamos a referência e subimos um poller leve que escreve, num
    arquivo compartilhado, quantos agentes estão processando agora
    (``gateway._running_agent_count()``) + as plataformas vistas recentemente.
  - No processo do CLI, o emote lê esse arquivo (com TTL) e mostra "✈ Telegram: N".

Tudo é à prova de falha: se algo mudar no gateway, o indicador some sem quebrar
nada. Nenhum escape é escrito; só um JSON pequeno.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .log import get_logger

PLUGIN_DIR = Path(__file__).resolve().parents[1]
INFLIGHT_PATH = PLUGIN_DIR / "gateway_inflight.json"

_poller_started = False
_lock = threading.Lock()
_gateway_ref = None
_recent_platforms: dict[str, float] = {}


# ----------------------------------------------------------------------------
# Lado do gateway
# ----------------------------------------------------------------------------
def register_gateway_hooks(ctx) -> None:
    """Registra o hook que captura o gateway e liga o poller. No-op no CLI."""
    try:
        ctx.register_hook("pre_gateway_dispatch", _on_dispatch)
    except Exception as e:
        get_logger().info("register_gateway_hooks falhou: %s", e)


def _platform_of(event) -> str | None:
    for getter in (
        lambda: getattr(getattr(event, "platform", None), "value", None),
        lambda: getattr(getattr(getattr(event, "source", None), "platform", None), "value", None),
        lambda: str(getattr(event, "platform", "")) or None,
    ):
        try:
            v = getter()
            if v:
                return str(v).lower()
        except Exception:
            pass
    return None


def _on_dispatch(event=None, gateway=None, **kwargs):
    """Fire no gateway a cada mensagem. Captura o gateway e nota a plataforma."""
    global _gateway_ref
    try:
        if gateway is not None:
            _gateway_ref = gateway
        plat = _platform_of(event)
        if plat:
            _recent_platforms[plat] = time.time()
        _ensure_poller()
    except Exception:
        pass
    return None  # nunca interfere no dispatch


def _ensure_poller() -> None:
    global _poller_started
    with _lock:
        if _poller_started:
            return
        _poller_started = True
    threading.Thread(target=_poll_loop, daemon=True, name="ada-gw-inflight").start()


def _poll_loop() -> None:
    log = get_logger()
    last_count = -1
    while True:
        try:
            gw = _gateway_ref
            count = 0
            if gw is not None:
                try:
                    count = int(gw._running_agent_count())
                except Exception:
                    count = 0
            now = time.time()
            plats = sorted(p for p, ts in _recent_platforms.items() if now - ts < 120)
            # escreve enquanto há atividade, e uma vez quando zera
            if count > 0 or (count == 0 and last_count > 0):
                try:
                    INFLIGHT_PATH.write_text(json.dumps(
                        {"count": count, "platforms": plats, "updated": now}))
                except Exception as e:
                    log.info("inflight write fail: %s", e)
            last_count = count
        except Exception:
            pass
        time.sleep(1.0 if (last_count and last_count > 0) else 1.5)


# ----------------------------------------------------------------------------
# Lado do CLI (emote)
# ----------------------------------------------------------------------------
def read_inflight(ttl: float = 5.0) -> dict | None:
    """Devolve {count, platforms, updated} se fresco e count>0, senão None."""
    try:
        if not INFLIGHT_PATH.exists():
            return None
        data = json.loads(INFLIGHT_PATH.read_text())
        if not isinstance(data, dict):
            return None
        if int(data.get("count", 0)) <= 0:
            return None
        if time.time() - float(data.get("updated", 0)) > ttl:
            return None
        return data
    except Exception:
        return None
