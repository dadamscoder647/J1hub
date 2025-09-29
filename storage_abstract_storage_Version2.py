from abc import ABC, abstractmethod

class AbstractStorage(ABC):
    @abstractmethod
    def save(self, file_storage, filename) -> str:
        pass

    @abstractmethod
    def url(self, filename) -> str:
        pass