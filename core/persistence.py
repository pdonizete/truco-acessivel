from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "estatisticas": {
        "vitorias": 0,
        "derrotas": 0,
        "partidas_concluidas": 0,
    },
    "preferencias": {
        "beep_habilitado": False,
        "dificuldade_padrao": "intermediario",
    },
    "partida_salva": None,
}


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_exists()

    def ensure_exists(self) -> None:
        if not self.path.exists():
            self.save(deepcopy(DEFAULT_CONFIG))

    def load(self) -> dict[str, Any]:
        self.ensure_exists()
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return self._merge_defaults(data)

    def save(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def update_preferences(self, **changes: Any) -> dict[str, Any]:
        data = self.load()
        data["preferencias"].update(changes)
        self.save(data)
        return data

    def save_match_snapshot(self, snapshot: dict[str, Any]) -> None:
        data = self.load()
        data["partida_salva"] = snapshot
        self.save(data)

    def clear_match_snapshot(self) -> None:
        data = self.load()
        data["partida_salva"] = None
        self.save(data)

    def record_match_result(self, player_won: bool) -> dict[str, Any]:
        data = self.load()
        data["estatisticas"]["partidas_concluidas"] += 1
        if player_won:
            data["estatisticas"]["vitorias"] += 1
        else:
            data["estatisticas"]["derrotas"] += 1
        data["partida_salva"] = None
        self.save(data)
        return data

    def _merge_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(DEFAULT_CONFIG)
        merged["estatisticas"].update(data.get("estatisticas", {}))
        merged["preferencias"].update(data.get("preferencias", {}))
        merged["partida_salva"] = data.get("partida_salva")
        return merged
