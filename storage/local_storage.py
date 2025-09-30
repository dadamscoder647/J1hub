"""Local filesystem storage implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, BinaryIO

from werkzeug.utils import secure_filename

from config import Config

from .abstract_storage import AbstractStorage


class LocalStorage(AbstractStorage):
    """Persist files to the local filesystem under the configured upload directory."""

    def __init__(self, upload_dir: str | None = None):
        self.base_directory = Path(upload_dir or Config.UPLOAD_DIR)
        os.makedirs(self.base_directory, exist_ok=True)

    def save(self, file_obj: IO[bytes], filename: str) -> str:
        """Save a file and return the relative path within the upload directory."""

        safe_name = secure_filename(filename)
        if not safe_name:
            raise ValueError("Filename must contain at least one valid character.")

        destination = self.base_directory / safe_name
        if hasattr(file_obj, "save"):
            file_obj.save(destination)  # type: ignore[arg-type]
        else:
            with open(destination, "wb") as output:
                output.write(file_obj.read())

        return str(destination.relative_to(self.base_directory))

    def exists(self, path: str) -> bool:
        """Return True if the given relative path exists within the upload directory."""

        return (self.base_directory / path).exists()

    def open(self, path: str, mode: str = "rb") -> BinaryIO:
        """Open a stored file using the provided mode."""

        return open(self.base_directory / path, mode)
