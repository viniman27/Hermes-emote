# Sixel renderer (experimental — Windows / non-kitty terminals)

> ⚠️ **Experimental and largely untested.** This was written without access to a
> sixel terminal. The encoder and terminal detection are verified; the on-screen
> **placement** inside prompt_toolkit is best-effort and may need tuning on real
> hardware. Feedback / PRs very welcome.

## Why this exists

The default renderer uses the **kitty graphics protocol with Unicode
placeholders**, which only some terminals speak (kitty, Ghostty, WezTerm). The
most common terminal on Windows — **Windows Terminal** — does *not* implement
kitty graphics, but it does support **sixel**. This renderer adds a sixel path so
the emote can show up there too.

## How to enable

Auto-detection picks the renderer per terminal (`renderer: auto`, the default):

| Terminal | Detected as |
|---|---|
| kitty / Ghostty / WezTerm | `kitty` |
| Windows Terminal (`WT_SESSION`) / mlterm | `sixel` |
| unknown | `kitty` |

Force it in `config.yaml`:

```yaml
renderer: sixel        # or: kitty, auto
sixel_cell_px: 20      # approximate cell height in px — tune the on-screen size
```

Or per-session via env (wins over config):

```bash
HERMES_EMOTE_RENDER=sixel
```

## How it works

- `terminal.py` — chooses `kitty` vs `sixel`.
- `sixel.py` — a **pure-Python sixel encoder** (only Pillow): loads the PNG,
  downsizes to `cols*… × rows*sixel_cell_px`, quantizes to ≤256 colors, and emits
  sixel bands. No `libsixel` / `img2sixel` needed.
- Integration with prompt_toolkit:
  - the widget renders `rows × cols` **blank cells** to reserve the area;
  - then a trailing **`[ZeroWidthEscape]`** fragment saves the cursor, moves up to
    the top of the reserved area, draws the sixel **over** the blank cells, and
    restores the cursor — so prompt_toolkit keeps measuring the layout correctly.
- Frames are pre-encoded at startup and cached (encoding is CPU-only, so it is
  safe to do off the render thread, unlike kitty's transmit).

## Known limitations

- **Sizing is approximate.** Sixel is pixel-based, not cell-based, so the image
  size in cells depends on your font's cell pixel size. Tune `sixel_cell_px`
  (bigger = larger emote) until it fills the reserved rows nicely.
- **Assumes the emote window starts at column 0.** If your layout indents it, the
  sixel may be offset horizontally.
- **Side info panel is kitty-only** for now (the sixel image covers those cells).
- **Resize / scroll** may leave artifacts; the image is redrawn on the next frame
  change, and the resize-settle repaint helps, but sixel is less forgiving than
  kitty placeholders here.
- Some terminals draw sixel with "scrolling" that moves the cursor; the cursor
  save/restore (`ESC 7` / `ESC 8`) compensates, but behavior varies.

## Helping test it

If you run Windows Terminal (or another sixel terminal):

1. `renderer: sixel` (or `HERMES_EMOTE_RENDER=sixel`), start Hermes.
2. If the image is too small/large, adjust `sixel_cell_px`.
3. If it's horizontally offset or leaves trails on resize, please open an issue
   with your terminal + OS — that's exactly the feedback needed to make this solid.
