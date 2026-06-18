"""Descoberta de assets, redimensionamento em cache e transmissão kitty.

Estrutura esperada: emotes/<set>/<estado>/<frame>.png  (+ opcional emotes.json).
Estados conhecidos: idle, think, talk, read, write, tool, failure, hi, compact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import kitty
from .log import get_logger

STATES = ["idle", "think", "talk", "read", "write", "tool", "failure", "hi", "compact"]


class Assets:
    def __init__(self, plugin_dir: Path, emote_set: str, rows: int, cols: int, cache_px: int = 384):
        self.dir = Path(plugin_dir) / "emotes" / emote_set
        self.rows = rows
        self.cols = cols
        self.cache_px = cache_px
        self.cache_dir = Path(plugin_dir) / ".cache" / f"{emote_set}_{cache_px}"
        self.log = get_logger()
        self.frames: dict[str, list[Path]] = {}
        self.meta: dict = {}
        self._ids: dict[str, int] = {}
        self._next_id = 7000
        self._transmitted: set[tuple] = set()
        self._load()

    def _load(self) -> None:
        for st in STATES:
            d = self.dir / st
            if d.is_dir():
                pngs = sorted(p for p in d.glob("*.png"))
                if pngs:
                    self.frames[st] = pngs
        mj = self.dir / "emotes.json"
        if mj.exists():
            try:
                self.meta = json.loads(mj.read_text())
            except Exception as e:
                self.log.info("emotes.json parse error: %s", e)

    def available(self) -> bool:
        return bool(self.frames)

    def id_for(self, path: Path) -> int:
        s = str(path)
        if s not in self._ids:
            self._ids[s] = self._next_id
            self._next_id += 1
        return self._ids[s]

    def _resized(self, path: Path) -> Path:
        """Devolve uma versão pequena em cache (Pillow); cai pro original em falha."""
        try:
            from PIL import Image

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            h = hashlib.md5(str(path).encode()).hexdigest()[:10]
            out = self.cache_dir / f"{h}.png"
            if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
                im = Image.open(path).convert("RGBA")
                im.thumbnail((self.cache_px, self.cache_px))
                im.save(out)
            return out
        except Exception as e:
            self.log.info("resize fail %s: %s", path, e)
            return path

    def ensure_transmitted(self, path: Path) -> int:
        """Transmite (uma vez) e devolve o id. No-op se já transmitido nessa grade."""
        img_id = self.id_for(path)
        key = (img_id, self.cols, self.rows)
        if key in self._transmitted:
            return img_id
        src = self._resized(path)
        try:
            kitty.transmit(src, img_id, self.cols, self.rows)
            self._transmitted.add(key)
        except Exception as e:
            self.log.info("transmit fail %s: %s", path, e)
        return img_id

    def preload(self) -> None:
        """Transmite todos os frames. Chamar SÓ em momento seguro (pré-render)."""
        for _st, paths in self.frames.items():
            for p in paths:
                self.ensure_transmitted(p)

    def delete_all(self) -> None:
        for img_id in list(self._ids.values()):
            try:
                kitty.delete_image(img_id)
            except Exception:
                pass
