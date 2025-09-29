from abc import ABC, abstractmethod

from werkzeug.datastructures import FileStorage


class AbstractStorage(ABC):
    @abstractmethod
    def save(self, file: FileStorage, filename: str) -> str:
        """Persist the uploaded file and return a URL or path."""
        raise NotImplementedError
