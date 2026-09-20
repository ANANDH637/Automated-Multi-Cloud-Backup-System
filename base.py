"""Abstract interface every cloud storage backend must implement."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UploadResult:
    provider: str
    remote_name: str
    success: bool
    message: str = ""


class CloudProvider(ABC):
    name = "base"

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the backend is reachable / usable."""

    @abstractmethod
    def upload(self, local_path: str, remote_name: str) -> UploadResult:
        """Upload a local file to the remote backend."""

    @abstractmethod
    def list_backups(self) -> list:
        """Return a list of remote backup filenames, oldest first."""

    @abstractmethod
    def download(self, remote_name: str, dest_path: str) -> str:
        """Download a remote backup to a local path."""

    @abstractmethod
    def delete(self, remote_name: str) -> bool:
        """Delete a remote backup file."""
