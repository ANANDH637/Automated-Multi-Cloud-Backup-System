"""Google Cloud Storage backend.

mode: "real"     -> uses google-cloud-storage against an actual GCS bucket
                     (requires GOOGLE_APPLICATION_CREDENTIALS to be set).
mode: "simulate" -> writes to a local folder namespaced as a "bucket".
"""
import os
import shutil

from .base import CloudProvider, UploadResult


class GCSProvider(CloudProvider):
    name = "gcs"

    def __init__(self, config: dict):
        super().__init__(config)
        self.mode = config.get("mode", "simulate")
        self.bucket_name = config.get("bucket", "my-backup-bucket")
        self._bucket = None

        if self.mode == "real":
            try:
                from google.cloud import storage  # noqa: F401
                client = storage.Client()
                self._bucket = client.bucket(self.bucket_name)
            except Exception:
                self.mode = "simulate"

        if self.mode == "simulate":
            self.sim_root = config.get("path", "cloud_sim/gcs")
            os.makedirs(self.sim_root, exist_ok=True)

    def test_connection(self) -> bool:
        if self.mode == "real":
            try:
                return self._bucket.exists()
            except Exception:
                return False
        return os.path.isdir(self.sim_root)

    def upload(self, local_path: str, remote_name: str) -> UploadResult:
        try:
            if self.mode == "real":
                blob = self._bucket.blob(remote_name)
                blob.upload_from_filename(local_path)
                return UploadResult(self.name, remote_name, True, f"uploaded to gs://{self.bucket_name}")
            shutil.copy2(local_path, os.path.join(self.sim_root, remote_name))
            return UploadResult(self.name, remote_name, True, f"[simulate] gs://{self.bucket_name}/{remote_name}")
        except Exception as e:
            return UploadResult(self.name, remote_name, False, str(e))

    def list_backups(self) -> list:
        if self.mode == "real":
            blobs = sorted(self._bucket.list_blobs(), key=lambda b: b.updated)
            return [b.name for b in blobs]
        files = [f for f in os.listdir(self.sim_root) if os.path.isfile(os.path.join(self.sim_root, f))]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.sim_root, f)))
        return files

    def download(self, remote_name: str, dest_path: str) -> str:
        if self.mode == "real":
            self._bucket.blob(remote_name).download_to_filename(dest_path)
        else:
            shutil.copy2(os.path.join(self.sim_root, remote_name), dest_path)
        return dest_path

    def delete(self, remote_name: str) -> bool:
        if self.mode == "real":
            self._bucket.blob(remote_name).delete()
            return True
        path = os.path.join(self.sim_root, remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
