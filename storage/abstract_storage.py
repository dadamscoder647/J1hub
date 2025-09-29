"""Storage abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import IO


class AbstractStorage(ABC):
    """Interface for storage backends."""

    @abstractmethod
    def save(self, file_obj: IO[bytes], filename: str) -> str:
        """Persist a file and return the stored path."""

        raise NotImplementedError
