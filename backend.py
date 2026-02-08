from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets
import jwt
import os
from email_service import send_reset_email


from database import conn, cursor
from security import hash_password, verify_password

# ---------------- CONFIG ----------------

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")
JWT_ALGO = "HS256"
TOKEN_EXP_DAYS = 7

# ---------------- APP ----------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local + frontend testing
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------

class AuthRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# ---------------- JWT HELPERS ----------------

def create_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

# ---------------- AUTH ----------------

@app.post("/signup")
def signup(data: AuthRequest):
    email = data.email.strip().lower()

    cursor.execute(
        "SELECT 1 FROM users WHERE email = %s",
        (email,)
    )
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(data.password)

    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
        (email, hashed)
    )
    conn.commit()

    return {"token": create_token(email)}


@app.post("/login")
def login(data: AuthRequest):
    email = data.email.strip().lower()

    cursor.execute(
        "SELECT password_hash FROM users WHERE email = %s",
        (data.email,)
    )
    row = cursor.fetchone()

    if not row or not verify_password(data.password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": create_token(data.email)}

@app.get("/me")
def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return {
            "email": payload["sub"],
            "status": "authenticated",
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------- FORGOT PASSWORD ----------------

@app.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    email = data.email.strip().lower()

    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    exists = cursor.fetchone()

    # Always return success (security)
    if not exists:
        return {"message": "If the email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    cursor.execute(
        """
        INSERT INTO password_resets (email, token, expires_at)
        VALUES (%s, %s, %s)
        """,
        (email, token, expires_at)
    )
    conn.commit()

    # ✅ SEND EMAIL HERE
    send_reset_email(email, token)

    return {"message": "If the email exists, a reset link has been sent"}


@app.post("/reset-password")
def reset_password(data: ResetPasswordRequest):
    cursor.execute(
        "SELECT email, expires_at FROM password_resets WHERE token = %s",
        (data.token,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    email, expires_at = row

    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=400, detail="Token expired")

    new_hash = hash_password(data.new_password)

    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE email = %s",
        (new_hash, email)
    )

    cursor.execute(
        "DELETE FROM password_resets WHERE token = %s",
        (data.token,)
    )

    conn.commit()

    return {"message": "Password reset successful"}




