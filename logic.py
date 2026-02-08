import os
import json
import re


from langchain_groq import ChatGroq
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import PromptTemplate

# Load .env locally (ignored on Render)


# Initialize LLM using environment variable
llm = ChatGroq(
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    groq_api_Key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)


def clean_json_output(text: str) -> str:
    """
    Removes markdown code fences like ```json ... ```
    """
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def extract_job_details(job_url: str) -> dict:
    try:
        # Load webpage
        loader = WebBaseLoader(job_url)
        docs = loader.load()
        page_data = docs[0].page_content

        # Prompt to extract structured job data
        prompt = PromptTemplate.from_template(
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

            RULES:
            - Return ONLY JSON
            - No markdown
            - No explanation
            """
        )

        chain = prompt | llm
        response = chain.invoke({"page_data": page_data})

        raw_output = response.content.strip()
        cleaned_output = clean_json_output(raw_output)

        parsed = json.loads(cleaned_output)

        # Validate expected keys
        required_keys = {"role", "experience", "skills", "description"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("Missing required keys in LLM output")

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
