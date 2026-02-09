import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

RESEND_API_URL = "https://api.resend.com/emails"


def send_reset_email(to_email: str, token: str):
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY not set")

    reset_link = f"https://coldemailgenerator2.netlify.app/reset-password?token={token}"

    payload = {
        "from": "AI COLD EMAIL GENERATOR <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "Reset your password",
        "html": f"""
        <p>Hello,</p>
        <p>You requested to reset your password.</p>
        <p>
            <a href="{reset_link}">
                Click here to reset your password
            </a>
        </p>
        <p>This link will expire in 15 minutes.</p>
        """
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        RESEND_API_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Resend error: {response.text}")
