# Hermes-emote

A live **emote widget for the [Hermes agent](https://github.com/NousResearch/hermes) CLI**: it renders a real
inline image (your character's portrait) above the prompt and reacts to what the
agent is doing — thinking, talking, reading, writing, running tools, failing — to
give the terminal a little soul.

It draws actual images **inside the existing TUI**, no separate window, using the
**kitty graphics protocol with Unicode placeholders**. It ships as a Hermes
**user plugin**, so it survives Hermes updates and never edits Hermes' source.

> Inspired by [**pi-emote**](https://github.com/JarodMica/jarods-pi-extensions)
> by JarodMica (for the Pi agent). This is an independent Python reimplementation
> of the idea for Hermes. See [Credits](#credits).

---

## Requirements

- **Hermes agent CLI** installed (`~/.hermes/`).
- A terminal that speaks an inline-image protocol — **kitty graphics**:
  - ✅ [Ghostty](https://ghostty.org) (recommended on macOS), kitty, WezTerm, iTerm2
  - ❌ **Apple Terminal.app does not support inline images** — nothing will show there.
- Python deps already present in Hermes' venv: `prompt_toolkit`, `Pillow`, `pyyaml`.

## How it works

- A small **state machine** (`animator.py`) maps real agent events to states:
  `hi · idle · think · talk · read · write · tool · failure · compact`.
- States come from Hermes' existing callbacks (thinking / streaming / tool
  lifecycle), wired via a defensive monkey-patch (`patch.py`) — the **only**
  coupling to Hermes.
- The image is drawn via **kitty Unicode placeholders** (`kitty.py`): the picture
  is transmitted once per frame and referenced by cells in a `prompt_toolkit`
  Window, so the TUI measures/clears the area correctly and never fights the cursor.
- Frames are **preloaded and downscaled** (Pillow) once at startup for a snappy,
  flicker-free swap during use.
- A side panel shows live info (name, state, model, context %, background tasks,
  rotating persona phrases).

## Install

```bash
# clone into Hermes' user-plugin folder
# (the TARGET dir must be named "hermes-emote" — that's the plugin key)
git clone https://github.com/viniman27/Hermes-emote ~/.hermes/plugins/hermes-emote
```

Enable it (user plugins are opt-in). In `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - hermes-emote        # add this line
```

Optionally copy the example config and tweak:

```bash
cp ~/.hermes/plugins/hermes-emote/config.example.yaml ~/.hermes/plugins/hermes-emote/config.yaml
```

Then **start Hermes in a graphics-capable terminal** (e.g. Ghostty). In-session:

```
/hermes-emote status      # show state, set, model, terminal
/hermes-emote on | off
```

## Add your own image set

No images are shipped — bring your own. Drop square PNG portraits under
`emotes/<SetName>/<state>/`:

```
emotes/Hermes/
  idle/   idle.png  idle_blink.png
  think/  think.png think_hard.png
  talk/   talk_close.png talk_small.png talk_mid.png talk_wide.png
  read/   read1.png read2.png
  write/  write1.png write2.png
  tool/   tool1.png tool2.png
  failure/ failure1.png failure2.png
  hi/     hi1.png hi2.png
  compact/ compact1.png
  emotes.json        # optional: blink frame, talk weights (see example)
```

Set `emote_set: <SetName>` in `config.yaml`. States with two frames animate by
alternating them; `idle` blinks by swapping `idle.png` ↔ `idle_blink.png`.

`emotes.json` (optional) example:

```json
{
  "idle":  { "default": "idle.png", "blink": "idle_blink.png" },
  "think": { "default": "think.png", "hard": "think_hard.png" },
  "talk":  { "weights": { "talk_close.png": 0.15, "talk_small.png": 0.3,
                          "talk_mid.png": 0.35, "talk_wide.png": 0.2 } }
}
```

## Configuration

| Key | Default | What it does |
|---|---|---|
| `enabled` | `true` | master on/off |
| `emote_set` | `Hermes` | folder under `emotes/` |
| `rows` | `10` | emote height in cells (width = rows×2) |
| `hide_below_cols` | `60` | hide if terminal narrower than this |
| `reserve_rows` | `10` | hide if not enough height for status bar/prompt |
| `show_info` | `true` | side info panel |
| `idle_blink` | `true` | blink while idle |
| `blink_close_ms` | `140` | eyes-closed duration per blink |
| `blink_min_ms` / `blink_max_ms` | `3000` / `6000` | interval between blinks |
| `talk_tick_ms` | `120` | mouth frame swap speed while talking |
| `cycle_ms` | `500` | frame swap for think/read/write/tool/failure |
| `phrases` / `phrase_rotate_s` | list / `12` | rotating side phrases |
| `cache_px` | `384` | max transmitted image size (resize on preload) |
| `hold_ms` | see file | how long transient states hold before idle |

## Troubleshooting

- **Nothing shows, Hermes works fine** → you're probably in Apple Terminal, or the
  app isn't in truecolor. The plugin forces 24-bit color (the image id is encoded
  in the foreground color). Check the log:
  `~/.hermes/plugins/hermes-emote/hermes-emote.log`.
- **Status bar / rules vanish on resize** → handled: Hermes hides them on resize
  until input; the plugin restores them once the resize settles.
- Full notes & the list of Hermes internals this depends on:
  [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

## Credits

- **Concept & original**: [pi-emote](https://github.com/JarodMica/jarods-pi-extensions)
  by JarodMica (Eiji Onchi) — an emote extension for the Pi agent. MIT licensed.
- **This project**: an independent Python reimplementation for the Hermes CLI.

## License

[MIT](LICENSE) 
