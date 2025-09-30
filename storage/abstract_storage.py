"""Storage abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import IO, BinaryIO


class AbstractStorage(ABC):
    """Interface for storage backends."""

    @abstractmethod
    def save(self, file_obj: IO[bytes], filename: str) -> str:
        """Persist a file and return the stored (relative) path."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return whether the given relative path exists in storage."""

    @abstractmethod
    def open(self, path: str, mode: str = "rb") -> BinaryIO:
        """Open a stored file and return the file object."""
