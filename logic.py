import os
import json
import re

from langchain_groq import ChatGroq
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import PromptTemplate


# ---------------- LLM INITIALIZATION ----------------
# Uses env var: GROQ_API_KEY

llm = ChatGroq(
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)


# ---------------- HELPER ----------------

def clean_json_output(text: str) -> str:
    """Remove markdown code fences if LLM adds them"""
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


# ---------------- JOB EXTRACTION ----------------

def extract_job_details(job_url: str) -> dict:
    try:
        # Load webpage
        loader = WebBaseLoader(job_url)
        docs = loader.load()
        page_data = docs[0].page_content

        # Prompt for structured extraction
        prompt = PromptTemplate.from_template(
            """
You are an information extraction system.

From the text below, extract job details and return ONLY valid JSON
with the following keys:

- role
- experience
- skills
- description

TEXT:
{page_data}

RULES:
- Output ONLY JSON
- No markdown
- No explanation
"""
        )

        chain = prompt | llm
        response = chain.invoke({"page_data": page_data})

        raw_output = response.content.strip()
        cleaned = clean_json_output(raw_output)
        parsed = json.loads(cleaned)

        required_keys = {"role", "experience", "skills", "description"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("Missing required keys in extracted job data")

        return parsed

    except json.JSONDecodeError:
        return {
            "error": "LLM returned invalid JSON",
            "raw_output": raw_output
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# ---------------- COLD EMAIL GENERATION ----------------

def generate_cold_email(job_text: dict, sender_name: str) -> dict:
    try:
        prompt = PromptTemplate.from_template(
            """
Write a professional cold email applying for the following job.

Job Role: {role}
Experience Required: {experience}
Skills: {skills}
Job Description: {description}

Sender Name: {sender_name}

RULES:
- Professional tone
- Concise
- No emojis
"""
        )

        chain = prompt | llm

        response = chain.invoke({
            "role": job_text.get("role"),
            "experience": job_text.get("experience"),
            "skills": (
                ", ".join(job_text.get("skills"))
                if isinstance(job_text.get("skills"), list)
                else job_text.get("skills")
            ),
            "description": job_text.get("description"),
            "sender_name": sender_name
        })

        return {
            "email": response.content.strip()
        }

    except Exception as e:
        return {
            "error": str(e)
        }
