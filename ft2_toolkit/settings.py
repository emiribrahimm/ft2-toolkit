from __future__ import annotations

import json
import os
from pathlib import Path

FILE_PATH = Path(os.environ.get("APPDATA", Path.home())) / "FT2Toolkit" / "settings.json"


class Settings:
    def __init__(self, data: dict | None = None):
        self._features: dict = (data or {}).get("Features", {})

    def feature(self, key: str) -> dict:
        entry = self._features.setdefault(key, {})
        entry.setdefault("Enabled", False)
        entry.setdefault("Values", {})
        return entry

    @classmethod
    def load(cls) -> Settings:
        try:
            with open(FILE_PATH, encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return cls(data)
        except (OSError, ValueError):
            pass
        return cls()

    def save(self) -> None:
        try:
            FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(FILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"Features": self._features}, f, indent=2, ensure_ascii=False)
        except OSError:
            pass
