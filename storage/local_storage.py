"""Local filesystem storage implementation."""

from __future__ import annotations

import os
import uuid
from typing import Optional

from flask import current_app
from werkzeug.utils import secure_filename

from .abstract_storage import AbstractStorage, SupportsSave


class LocalStorage(AbstractStorage):
    """Store uploaded files on the local filesystem."""

    def __init__(self, upload_folder: Optional[str] = None) -> None:
        self._upload_folder = upload_folder

    def _resolve_upload_folder(self) -> str:
        """Determine the folder used for uploads and ensure it exists."""

        folder = (
            self._upload_folder
            or current_app.config.get("UPLOAD_FOLDER")
            or os.environ.get("UPLOAD_FOLDER")
            or os.path.join(os.getcwd(), "uploads")
        )
        os.makedirs(folder, exist_ok=True)
        return folder

    def save(self, file_storage: SupportsSave, filename: str | None = None) -> str:
        folder = self._resolve_upload_folder()
        candidate_name = filename or getattr(file_storage, "filename", "") or uuid.uuid4().hex
        sanitized = secure_filename(candidate_name) or uuid.uuid4().hex
        destination = os.path.join(folder, sanitized)
        file_storage.save(destination)
        return sanitized

    def url(self, filename: str) -> str:
        base_url = current_app.config.get("UPLOAD_URL_PREFIX", "/uploads")
        return f"{base_url.rstrip('/')}/{filename}"
