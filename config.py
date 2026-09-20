"""Loads and validates the YAML configuration file."""
import os
import yaml


DEFAULT_CONFIG = {
    "sources": [],
    "encryption": {"enabled": True, "password": "change-me-please"},
    "retention": {"keep_last": 5},
    "schedule": {"interval_minutes": 60},
    "providers": {
        "local": {"enabled": True, "path": "cloud_sim/local"},
        "aws_s3": {"enabled": False, "mode": "simulate", "bucket": "my-backup-bucket",
                   "region": "us-east-1", "path": "cloud_sim/aws_s3"},
        "gcs": {"enabled": False, "mode": "simulate", "bucket": "my-backup-bucket",
                "path": "cloud_sim/gcs"},
        "azure_blob": {"enabled": False, "mode": "simulate", "container": "backups",
                       "path": "cloud_sim/azure_blob"},
    },
}


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.config_path):
            self._write_default()
        with open(self.config_path, "r") as f:
            loaded = yaml.safe_load(f) or {}
        merged = self._deep_merge(DEFAULT_CONFIG, loaded)
        return merged

    def _write_default(self):
        with open(self.config_path, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, sort_keys=False)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, *keys, default=None):
        node = self.data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    @property
    def sources(self):
        return self.data.get("sources", [])

    @property
    def enabled_providers(self):
        return {
            name: cfg
            for name, cfg in self.data.get("providers", {}).items()
            if cfg.get("enabled")
        }
