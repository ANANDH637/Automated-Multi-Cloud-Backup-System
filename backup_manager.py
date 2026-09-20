"""Orchestrates the full backup pipeline: compress -> encrypt -> upload -> retain."""
import os
import tempfile
import time
from datetime import datetime

from .config import Config
from .compression import compress_path
from .encryption import Encryptor
from .providers import PROVIDER_REGISTRY
from .logger import get_logger

logger = get_logger("backup_manager")


class BackupManager:
    def __init__(self, config: Config):
        self.config = config
        self.providers = self._init_providers()
        self.encryptor = None
        if config.get("encryption", "enabled", default=True):
            password = config.get("encryption", "password", default="change-me")
            self.encryptor = Encryptor(password)

    def _init_providers(self) -> dict:
        active = {}
        for name, cfg in self.config.enabled_providers.items():
            cls = PROVIDER_REGISTRY.get(name)
            if not cls:
                logger.warning("Unknown provider '%s' in config, skipping.", name)
                continue
            provider = cls(cfg)
            if provider.test_connection():
                active[name] = provider
                logger.info("Provider '%s' ready (mode=%s).", name, getattr(provider, "mode", "n/a"))
            else:
                logger.error("Provider '%s' failed connection test, skipping.", name)
        return active

    def run_backup(self) -> dict:
        """Backs up every configured source to every enabled provider. Returns a report dict."""
        report = {"timestamp": datetime.now().isoformat(), "sources": []}

        if not self.providers:
            logger.error("No active providers configured. Aborting backup run.")
            return report

        for source in self.config.sources:
            src_path = source["path"] if isinstance(source, dict) else source
            label = source.get("label") if isinstance(source, dict) else os.path.basename(src_path.rstrip("/"))

            if not os.path.exists(src_path):
                logger.warning("Source path does not exist, skipping: %s", src_path)
                continue

            source_report = {"path": src_path, "results": []}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{label}_{timestamp}.zip"

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, archive_name)
                logger.info("Compressing '%s' -> %s", src_path, archive_name)
                compress_path(src_path, zip_path)

                upload_path = zip_path
                remote_name = archive_name
                if self.encryptor:
                    enc_path = zip_path + ".enc"
                    self.encryptor.encrypt_file(zip_path, enc_path)
                    upload_path = enc_path
                    remote_name = archive_name + ".enc"
                    logger.info("Encrypted archive: %s", remote_name)

                for pname, provider in self.providers.items():
                    result = provider.upload(upload_path, remote_name)
                    source_report["results"].append(result.__dict__)
                    level = logging_info_or_error = logger.info if result.success else logger.error
                    level("[%s] %s -> %s", pname, remote_name, result.message)

            report["sources"].append(source_report)
            self._apply_retention(label)

        return report

    def _apply_retention(self, label: str):
        keep_last = self.config.get("retention", "keep_last", default=5)
        for pname, provider in self.providers.items():
            try:
                backups = [f for f in provider.list_backups() if f.startswith(label + "_")]
                excess = len(backups) - keep_last
                if excess > 0:
                    for old_file in backups[:excess]:
                        provider.delete(old_file)
                        logger.info("[%s] retention: deleted old backup %s", pname, old_file)
            except Exception as e:
                logger.error("[%s] retention check failed: %s", pname, e)

    def restore(self, remote_name: str, dest_dir: str, provider_name: str = None) -> str:
        provider_name = provider_name or next(iter(self.providers))
        provider = self.providers[provider_name]

        os.makedirs(dest_dir, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            downloaded = os.path.join(tmpdir, remote_name)
            provider.download(remote_name, downloaded)

            zip_path = downloaded
            if remote_name.endswith(".enc"):
                if not self.encryptor:
                    raise RuntimeError("File is encrypted but no encryption password configured.")
                zip_path = downloaded[:-4]
                self.encryptor.decrypt_file(downloaded, zip_path)

            from .compression import decompress_zip
            decompress_zip(zip_path, dest_dir)
        logger.info("Restored '%s' from '%s' into %s", remote_name, provider_name, dest_dir)
        return dest_dir

    def list_all_backups(self) -> dict:
        return {name: provider.list_backups() for name, provider in self.providers.items()}
