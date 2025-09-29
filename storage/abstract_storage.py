"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import Protocol


class SupportsSave(Protocol):
    """Protocol for file-like objects that Flask provides."""

    def save(self, dst: str) -> None:  # pragma: no cover - interface definition
        """Save the file to the given destination."""


class AbstractStorage(ABC):
    """Contract for file storage implementations."""

    @abstractmethod
    def save(self, file_storage: SupportsSave, filename: str | None = None) -> str:
        """Persist the file and return an identifier for future retrieval."""

    @abstractmethod
    def url(self, filename: str) -> str:
        """Return an accessible URL for a stored file."""
