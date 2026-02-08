from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt, os, secrets

from database import conn, cursor
from security import hash_password, verify_password
from logic import extract_job_details, generate_cold_email
from email_service import send_reset_email

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://coldemailgenerator2.netlify.app/"],
    allow_methods=["https://coldemailgenerator2.netlify.app/"],
    allow_headers=["https://coldemailgenerator2.netlify.app/"],
)

# ---------- MODELS ----------

class Auth(BaseModel):
    email: str
    password: str

class JobRequest(BaseModel):
    url: str

class EmailRequest(BaseModel):
    job_text: str
    sender_name: str

class ForgotReq(BaseModel):
    email: str

class ResetReq(BaseModel):
    token: str
    new_password: str


# ---------- JWT ----------

def create_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


# ---------- AUTH ----------

@app.post("/signup")
def signup(data: Auth):
    cursor.execute("SELECT 1 FROM users WHERE email=%s", (data.email,))
    if cursor.fetchone():
        raise HTTPException(400, "User exists")

    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s,%s)",
        (data.email, hash_password(data.password))
    )
    conn.commit()
    return {"token": create_token(data.email)}


@app.post("/login")
def login(data: Auth):
    cursor.execute("SELECT password_hash FROM users WHERE email=%s", (data.email,))
    row = cursor.fetchone()

    if not row or not verify_password(data.password, row[0]):
        raise HTTPException(401, "Invalid credentials")

    return {"token": create_token(data.email)}


@app.get("/me")
def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")

    token = authorization.split()[1]
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    return {"email": payload["sub"]}


# ---------- CORE PRODUCT ----------

@app.post("/extract-job")
def extract_job(data: JobRequest):
    return extract_job_details(data.url)


@app.post("/generate-email")
def generate_email(data: EmailRequest):
    return generate_cold_email(data.job_text, data.sender_name)


# ---------- FORGOT PASSWORD ----------

@app.post("/forgot-password")
def forgot_password(data: ForgotReq):
    cursor.execute("SELECT 1 FROM users WHERE email=%s", (data.email,))
    if not cursor.fetchone():
        return {"message": "If email exists, reset link sent"}

    token = secrets.token_urlsafe(32)
    cursor.execute(
        "INSERT INTO password_resets (email, token) VALUES (%s,%s)",
        (data.email, token)
    )
    conn.commit()

    send_reset_email(data.email, token)
    return {"message": "If email exists, reset link sent"}


@app.post("/reset-password")
def reset_password(data: ResetReq):
    cursor.execute(
        "SELECT email FROM password_resets WHERE token=%s",
        (data.token,)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(400, "Invalid token")

    cursor.execute(
        "UPDATE users SET password_hash=%s WHERE email=%s",
        (hash_password(data.new_password), row[0])
    )
    cursor.execute("DELETE FROM password_resets WHERE token=%s", (data.token,))
    conn.commit()

    return {"message": "Password updated"}
