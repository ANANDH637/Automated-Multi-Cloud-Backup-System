"""Azure Blob Storage backend.

mode: "real"     -> uses azure-storage-blob against a real container
                     (requires AZURE_STORAGE_CONNECTION_STRING env var).
mode: "simulate" -> writes to a local folder namespaced as a "container".
"""
import os
import shutil

from .base import CloudProvider, UploadResult


class AzureBlobProvider(CloudProvider):
    name = "azure_blob"

    def __init__(self, config: dict):
        super().__init__(config)
        self.mode = config.get("mode", "simulate")
        self.container_name = config.get("container", "backups")
        self._container_client = None

        if self.mode == "real":
            try:
                from azure.storage.blob import BlobServiceClient  # noqa: F401
                conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
                service = BlobServiceClient.from_connection_string(conn_str)
                self._container_client = service.get_container_client(self.container_name)
            except Exception:
                self.mode = "simulate"

        if self.mode == "simulate":
            self.sim_root = config.get("path", "cloud_sim/azure_blob")
            os.makedirs(self.sim_root, exist_ok=True)

    def test_connection(self) -> bool:
        if self.mode == "real":
            try:
                return self._container_client.exists()
            except Exception:
                return False
        return os.path.isdir(self.sim_root)

    def upload(self, local_path: str, remote_name: str) -> UploadResult:
        try:
            if self.mode == "real":
                with open(local_path, "rb") as f:
                    self._container_client.upload_blob(remote_name, f, overwrite=True)
                return UploadResult(self.name, remote_name, True, f"uploaded to {self.container_name}")
            shutil.copy2(local_path, os.path.join(self.sim_root, remote_name))
            return UploadResult(self.name, remote_name, True, f"[simulate] {self.container_name}/{remote_name}")
        except Exception as e:
            return UploadResult(self.name, remote_name, False, str(e))

    def list_backups(self) -> list:
        if self.mode == "real":
            blobs = sorted(self._container_client.list_blobs(), key=lambda b: b.last_modified)
            return [b.name for b in blobs]
        files = [f for f in os.listdir(self.sim_root) if os.path.isfile(os.path.join(self.sim_root, f))]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.sim_root, f)))
        return files

    def download(self, remote_name: str, dest_path: str) -> str:
        if self.mode == "real":
            with open(dest_path, "wb") as f:
                f.write(self._container_client.download_blob(remote_name).readall())
        else:
            shutil.copy2(os.path.join(self.sim_root, remote_name), dest_path)
        return dest_path

    def delete(self, remote_name: str) -> bool:
        if self.mode == "real":
            self._container_client.delete_blob(remote_name)
            return True
        path = os.path.join(self.sim_root, remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
