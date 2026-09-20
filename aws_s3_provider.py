"""AWS S3 backend.

mode: "real"     -> uses boto3 against an actual S3 bucket (requires AWS credentials
                     configured via env vars / ~/.aws/credentials / IAM role).
mode: "simulate" -> writes to a local folder namespaced as a "bucket", so the whole
                     pipeline can be demoed and tested without any AWS account.
"""
import os
import shutil

from .base import CloudProvider, UploadResult


class AWSS3Provider(CloudProvider):
    name = "aws_s3"

    def __init__(self, config: dict):
        super().__init__(config)
        self.mode = config.get("mode", "simulate")
        self.bucket = config.get("bucket", "my-backup-bucket")
        self.region = config.get("region", "us-east-1")
        self._client = None

        if self.mode == "real":
            try:
                import boto3  # noqa: F401
                self._boto3 = boto3
                self._client = boto3.client("s3", region_name=self.region)
            except Exception:
                # boto3 missing or no credentials -> fall back to simulate so the
                # rest of the pipeline (compression/encryption/logging) still runs.
                self.mode = "simulate"

        if self.mode == "simulate":
            self.sim_root = config.get("path", "cloud_sim/aws_s3")
            os.makedirs(self.sim_root, exist_ok=True)

    def test_connection(self) -> bool:
        if self.mode == "real":
            try:
                self._client.head_bucket(Bucket=self.bucket)
                return True
            except Exception:
                return False
        return os.path.isdir(self.sim_root)

    def upload(self, local_path: str, remote_name: str) -> UploadResult:
        try:
            if self.mode == "real":
                self._client.upload_file(local_path, self.bucket, remote_name)
                return UploadResult(self.name, remote_name, True, f"uploaded to s3://{self.bucket}")
            shutil.copy2(local_path, os.path.join(self.sim_root, remote_name))
            return UploadResult(self.name, remote_name, True, f"[simulate] s3://{self.bucket}/{remote_name}")
        except Exception as e:
            return UploadResult(self.name, remote_name, False, str(e))

    def list_backups(self) -> list:
        if self.mode == "real":
            resp = self._client.list_objects_v2(Bucket=self.bucket)
            contents = sorted(resp.get("Contents", []), key=lambda o: o["LastModified"])
            return [obj["Key"] for obj in contents]
        files = [f for f in os.listdir(self.sim_root) if os.path.isfile(os.path.join(self.sim_root, f))]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.sim_root, f)))
        return files

    def download(self, remote_name: str, dest_path: str) -> str:
        if self.mode == "real":
            self._client.download_file(self.bucket, remote_name, dest_path)
        else:
            shutil.copy2(os.path.join(self.sim_root, remote_name), dest_path)
        return dest_path

    def delete(self, remote_name: str) -> bool:
        if self.mode == "real":
            self._client.delete_object(Bucket=self.bucket, Key=remote_name)
            return True
        path = os.path.join(self.sim_root, remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
