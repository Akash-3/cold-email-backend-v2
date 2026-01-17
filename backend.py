from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from logic import extract_job_details   # 👈 ACCESS TO MAIN CODE

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobRequest(BaseModel):
    url: str

@app.post("/extract-job")
def extract_job(data: JobRequest):
    result = extract_job_details(data.url)
    return result

