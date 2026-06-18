# hermes-emote — design, riscos e troubleshooting

Widget de emote do Hermes (imagem inline reagindo ao estado do agente), feito como
**plugin de usuário** do Hermes para sobreviver a atualizações.

## Por que plugin, e não edição do cli.py

O `cli.py` do Hermes mora em `~/.hermes/hermes-agent/`, que é **sobrescrito a cada
update**. Qualquer edição direta ali é apagada. Plugins de usuário moram em
`~/.hermes/plugins/<nome>/`, **fora** do alvo do update, e são carregados
automaticamente (`plugin.yaml` + `register(ctx)`). Logo: zero edição no Hermes.

O plugin aplica *monkey-patch* nos métodos da `HermesCLI` em tempo de carga,
usando a referência viva da CLI que o Hermes entrega ao plugin manager
(`cli.py` faz `get_plugin_manager()._cli_ref = self`).

## De quais pontos internos do Hermes dependemos

Se um update do Hermes renomear/remover qualquer um destes, o emote se desliga
sozinho (graceful) e registra no log. Esta é a lista a revalidar após updates:

| Ponto interno | Papel | Verificado em (cli.py) |
|---|---|---|
| `HermesCLI._get_extra_tui_widgets()` | injeta o widget no layout do TUI | ~10867 |
| layout insere `*self._get_extra_tui_widgets()` entre spacer e status_bar | posição do widget | ~10927 |
| `_on_thinking(text)` | estado → think / idle | ~4448 |
| `_stream_delta(text)` | estado → talk | ~4714 |
| `_on_tool_gen_start(tool_name)` | estado → tool | ~8941 |
| `_on_tool_progress(event_type, function_name, ... is_error)` | read/write/tool/failure | ~8961 |
| `_agent_running` (flag) | gate da animação / volta a idle | ~3525 / ~11067 |
| `_invalidate(min_interval)` | pede repaint do TUI | ~3647 |
| `spinner_loop` (thread de 0.1s) | motor de animação existente | ~12918 |
| `get_plugin_manager()._cli_ref` | acesso à CLI viva a partir do plugin | ~11078 |
| hooks válidos: `on_session_start`, `on_session_end` | ciclo de vida | plugins.py ~140 |
| hook `pre_gateway_dispatch` + `gateway._running_agent_count()` | indicador "✈ Telegram: N" (gateway_link.py) | gateway/run.py ~6801 / ~3245 |

## Pré-requisito de terminal (NÃO é bug)

Imagem inline exige um terminal que fale um protocolo gráfico. Matriz:

| Terminal | Protocolo | Funciona? |
|---|---|---|
| Ghostty | kitty graphics | ✅ (recomendado) |
| kitty | kitty graphics | ✅ |
| WezTerm | iTerm2 / sixel | ✅ |
| iTerm2 | iTerm2 inline | ✅ |
| **Apple Terminal.app** | — | ❌ nunca renderiza imagem |
| tmux/zellij/screen | depende do passthrough | ⚠️ variável |

Teste rápido: `python3 scripts/smoke_kitty.py` **dentro do Ghostty**.
- Quadrado colorido aparece → protocolo OK.
- Nada aparece e `TERM_PROGRAM=Apple_Terminal` → você está no terminal errado.

## Como o emote convive com o prompt_toolkit (a parte difícil)

O prompt_toolkit desenha uma grade de células; ele não conhece sequências de
imagem. A imagem é colocada via **kitty unicode placeholders**: transmite-se a
imagem uma vez (por id), e o widget devolve células de placeholder que o terminal
substitui pela imagem. Assim o pt mede/limpa a área certo e não há disputa de
cursor. (Detalhe de implementação — documentar aqui quando estabilizar.)

## Falhas comuns e o que checar

- **Nada aparece, mas o Hermes funciona:** emote desligou. Ver o log do plugin
  (caminho a definir na implementação) — provavelmente um ponto interno mudou de
  nome num update. Revalidar a tabela acima.
- **Imagem aparece mas não some / fantasma ao rolar:** problema de limpeza de
  placement; conferir resize-recovery do Hermes e o id/placement do kitty.
- **Flicker:** a animação só deve invalidar enquanto `_agent_running`. Idle não
  repinta (Hermes evita isso de propósito por causa de tmux/Ghostty).
- **Terminal estreito/baixo:** widget se esconde via `_use_minimal_tui_chrome`.
- **Pasta de emotes vazia:** comportamento esperado é ficar inerte/oculto. As
  imagens são fornecidas pelo usuário; nada de assets do repo é usado.

## Duas exigências operacionais (não são bugs)

1. **Truecolor obrigatório.** O id da imagem é codificado na cor de frente das
   células de placeholder. Se o prompt_toolkit renderizar em 256 cores, o id se
   perde e nada aparece. O plugin força `DEPTH_24_BIT` de dois jeitos: env
   `PROMPT_TOOLKIT_COLOR_DEPTH` (cedo) e `app._color_depth` no app já criado
   (determinístico, via thread de animação). Se um dia o emote aparecer "em
   branco", confira no log se "color depth forçado" saiu.
2. **Plugin opt-in.** Plugins de usuário só carregam se o nome estiver em
   `plugins.enabled` no `~/.hermes/config.yaml`. `hermes-emote` já foi adicionado lá.
   Se sumir após um `migrate_config`, readicione `- hermes-emote`.

## Estado atual

- [x] Diagnóstico dos pontos de integração
- [x] Ghostty instalado, Hermes abre nele
- [x] Smoke test de kitty graphics (gradiente) — OK no Ghostty
- [x] Render inline dentro do prompt_toolkit (Teste B) — OK e troca de frame
- [x] Plugin scaffold (`plugin.yaml` + `register`) — carrega: enabled, sem erro
- [x] Renderer kitty (unicode placeholders) — `hermes_emote/kitty.py`
- [x] Máquina de estados ligada aos callbacks (5 métodos wrapped) — `patch.py`
- [x] Imagens do usuário em `emotes/Hermes/` (19 frames, 9 estados)
- [x] Preload com resize via Pillow (~174 KB/frame, ~4.4 MB total)
- [x] Comando `/hermes-emote on|off|status`
- [ ] Validação visual numa sessão real do Hermes no Ghostty

## Log

`~/.hermes/plugins/hermes-emote/hermes-emote.log` — carga do patch, color depth,
falhas de transmit/resize. Primeiro lugar a olhar se algo não aparecer.
