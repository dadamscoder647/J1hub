from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(64), nullable=False, default="user")
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"