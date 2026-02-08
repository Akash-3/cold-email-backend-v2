from datetime import datetime, timedelta
from jose import jwt
import os

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=7)
    data.update({"exp": expire})

    token = jwt.encode(
        data,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return token
