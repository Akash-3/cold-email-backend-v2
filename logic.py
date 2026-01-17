import json
import re
import os
from langchain_groq import ChatGroq
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()

def clean_json_output(text: str) -> str:
    """
    Removes markdown code fences like ```json ... ```
    """
    # Remove ```json and ```
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

# -------- READ API KEY FROM FILE --------
def load_groq_key():
    with open("groq_key.txt", "r") as f:
        return f.read().strip()

GROQ_API_KEY = load_groq_key()

# -------- INIT LLM --------
llm = ChatGroq(
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

def extract_job_details(job_url: str) -> dict:
    try:
        loader = WebBaseLoader(job_url)
        docs = loader.load()
        page_data = docs[0].page_content

        prompt_extract = PromptTemplate.from_template(
            """
            You are an information extraction system.

            From the text below, extract the job details and return
            ONLY valid JSON with the following keys:
            - role
            - experience
            - skills
            - description

            TEXT:
            {page_data}

            IMPORTANT:
            - Return ONLY JSON
            - No markdown
            - No explanation
            """
        )

        chain = prompt_extract | llm
        response = chain.invoke({"page_data": page_data})

        raw_output = response.content.strip()
        cleaned_output = clean_json_output(raw_output)

        parsed = json.loads(cleaned_output)

        required_keys = {"role", "experience", "skills", "description"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("Missing required keys")

        return parsed

    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON after cleaning",
            "raw_output": raw_output
        }

    except Exception as e:
        return {"error": str(e)}
