from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .abstract_storage import AbstractStorage


class LocalStorage(AbstractStorage):
    def __init__(self, upload_dir: str) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: FileStorage, filename: str) -> str:
        safe_name = secure_filename(filename)
        if not safe_name:
            raise ValueError("Invalid filename")

        unique_name = f"{uuid4().hex}_{safe_name}"
        destination = self.upload_dir / unique_name
        file.save(destination)
        return str(destination)
