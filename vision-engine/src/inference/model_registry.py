"""File-based model registry for tracking model lifecycle."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ModelStatus = Literal["candidate", "evaluated", "approved", "production", "archived"]


class ModelEntry:
    def __init__(
        self,
        name: str,
        variant: str,
        version: str,
        weights_path: str,
        status: ModelStatus = "candidate",
        metrics: dict | None = None,
        training_config: dict | None = None,
        license_info: str = "",
    ):
        self.name = name
        self.variant = variant
        self.version = version
        self.weights_path = weights_path
        self.status = status
        self.metrics = metrics or {}
        self.training_config = training_config or {}
        self.license_info = license_info
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.promoted_at = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "variant": self.variant,
            "version": self.version,
            "weights_path": self.weights_path,
            "status": self.status,
            "metrics": self.metrics,
            "training_config": self.training_config,
            "license_info": self.license_info,
            "created_at": self.created_at,
            "promoted_at": self.promoted_at,
        }


class ModelRegistry:
    """File-based registry for model lifecycle management."""

    def __init__(self, registry_dir: str = "models/registry"):
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def register(self, entry: ModelEntry) -> str:
        filepath = self._dir / f"{entry.name}_{entry.version}.json"
        filepath.write_text(json.dumps(entry.to_dict(), indent=2))
        return str(filepath)

    def list_models(self, status: ModelStatus | None = None) -> list[dict]:
        models = []
        for f in sorted(self._dir.glob("*.json")):
            data = json.loads(f.read_text())
            if status is None or data.get("status") == status:
                models.append(data)
        return models

    def get_production_model(self) -> dict | None:
        models = self.list_models(status="production")
        return models[0] if models else None

    def promote(self, name: str, version: str) -> bool:
        for f in self._dir.glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("status") == "production":
                data["status"] = "archived"
                f.write_text(json.dumps(data, indent=2))

        target = self._dir / f"{name}_{version}.json"
        if not target.exists():
            return False
        data = json.loads(target.read_text())
        data["status"] = "production"
        data["promoted_at"] = datetime.now(timezone.utc).isoformat()
        target.write_text(json.dumps(data, indent=2))
        return True
