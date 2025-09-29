import os
from werkzeug.utils import secure_filename
from .abstract_storage import AbstractStorage

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "./workspace/uploads")

class LocalStorage(AbstractStorage):
    def save(self, file_storage, filename):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file_storage.save(filepath)
        return filepath

    def url(self, filename):
        return f"/uploads/{filename}"