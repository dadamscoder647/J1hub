from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


from .user import User  # noqa: E402,F401
from .visa_document import VisaDocument  # noqa: E402,F401
