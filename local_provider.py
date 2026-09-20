"""Stores backups on the local filesystem. Always available, no credentials needed."""
import os
import shutil

from .base import CloudProvider, UploadResult


class LocalProvider(CloudProvider):
    name = "local"

    def __init__(self, config: dict):
        super().__init__(config)
        self.root = config.get("path", "cloud_sim/local")
        os.makedirs(self.root, exist_ok=True)

    def test_connection(self) -> bool:
        return os.path.isdir(self.root) and os.access(self.root, os.W_OK)

    def upload(self, local_path: str, remote_name: str) -> UploadResult:
        try:
            dest = os.path.join(self.root, remote_name)
            shutil.copy2(local_path, dest)
            return UploadResult(self.name, remote_name, True, "stored locally")
        except Exception as e:
            return UploadResult(self.name, remote_name, False, str(e))

    def list_backups(self) -> list:
        files = [f for f in os.listdir(self.root) if os.path.isfile(os.path.join(self.root, f))]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.root, f)))
        return files

    def download(self, remote_name: str, dest_path: str) -> str:
        shutil.copy2(os.path.join(self.root, remote_name), dest_path)
        return dest_path

    def delete(self, remote_name: str) -> bool:
        path = os.path.join(self.root, remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
