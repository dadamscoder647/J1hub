"""Local filesystem storage implementation."""

from __future__ import annotations

from pathlib import Path
from typing import IO
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .abstract_storage import AbstractStorage


class LocalStorage(AbstractStorage):
    """Persist files to the local filesystem."""

    def __init__(self, base_directory: str):
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)

    def save(self, file_obj: IO[bytes] | FileStorage, filename: str) -> str:
        """Save a file to the upload directory and return the path."""

        safe_name = secure_filename(filename) or f"upload_{uuid4().hex}"
        destination = self.base_directory / safe_name

        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while destination.exists():
            destination = self.base_directory / f"{stem}_{counter}{suffix}"
            counter += 1

        if isinstance(file_obj, FileStorage):
            file_obj.save(destination)
        else:  # pragma: no cover - fallback for non FileStorage objects
            with open(destination, "wb") as output:
                data = file_obj.read()
                output.write(data)

        return str(destination)
