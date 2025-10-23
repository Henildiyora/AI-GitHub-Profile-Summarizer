import os
from dotenv import load_dotenv
load_dotenv() 

from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import io
from pypdf import PdfReader

# Import the new classes from our client modules
from app.github_client import GitHubClient
from app.llm_client import LLMClient

# Path Definitions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Initialize FastAPI App
app = FastAPI()

# Not nedded more, this content add into the Form() flides.
# # Pydantic Models (Unchanged)
# class SummaryRequest(BaseModel):
#     username: str
#     job_description: str

class FitReportResponse(BaseModel):
    fit_score: int
    summary: str
    role_strengths: List[str] 
    role_weaknesses: List[str] 
    red_flags: List[str]
    interview_questions: List[str]
    error: Optional[str] = None

# Create global instances of our clients
# These will be reused for all requests
github_client = GitHubClient()
llm_client = LLMClient()

# Static Files Mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def parse_pdf_resume(file_contents: bytes) -> str:
    """
    Extracts text from a PDF file's byte content.
    
    Args:
        file_contents (bytes): The raw bytes of the PDF file.

    Returns:
        str: The extracted text from the PDF.
    """
    try:
        pdf_file = io.BytesIO(file_contents)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        return text
    
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse PDF file. Error: {e}")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves the main index.html file.
    
    Returns:
        HTMLResponse: The content of the index.html file.
    """
    html_file_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(html_file_path) as f:
        return HTMLResponse(content=f.read(), status_code=200)

# API Endpoint
@app.post("/summarize", response_model=FitReportResponse)
async def get_github_summary(
    username: str = Form(...),
    job_description: str = Form(...),
    resume_file: UploadFile = File(...)
):
    """
        Main API endpoint to generate a candidate fit report.
        
        Now accepts FormData containing username, job description,
        and a PDF resume file.

        Args:
            username (str): The GitHub username (from form).
            job_description (str): The job description (from form).
            resume_file (UploadFile): The candidate's resume PDF (from file upload).

        Returns:
            FitReportResponse: The structured fit report.
    """
    if not username:
        raise HTTPException(status_code=400, detail="GitHub username is required.")
    if not job_description:
        raise HTTPException(status_code=400, detail="Job Description is required.")
    if not resume_file or resume_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="A valid PDF resume file is required.")

    try:
        # Read and parse the resume 
        resume_contents = await resume_file.read()
        resume_text = parse_pdf_resume(resume_contents)
        if not resume_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. The file might be empty or image-based.")

        # Fetch profile and repos from GitHub concurrently
        profile_task = github_client.get_user_profile(username)
        repos_task = github_client.get_user_repos(username)
        profile, repos = await asyncio.gather(profile_task, repos_task)

        if not profile:
            raise HTTPException(status_code=404, detail="GitHub user not found.")

        # For the top 5 repos, fetch their READMEs concurrently
        top_repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)[:5]
        readme_tasks = [
            github_client.get_readme_content(username, repo['name']) 
            for repo in top_repos
        ]
        readme_contents = await asyncio.gather(*readme_tasks)

        # Create a dictionary mapping repo name to its README content
        readmes = {repo['name']: content for repo, content in zip(top_repos, readme_contents) if content}

        # Generate the structured summary using the LLM
        summary_data = await llm_client.generate_summary_from_github_data(
            profile = profile,
            repos = top_repos,
            readmes = readmes,
            job_description = job_description,
            resume_text = resume_text
        )

        if "error" in summary_data:
             raise HTTPException(status_code=500, detail=summary_data["error"])

        # Validate and return the data using our Pydantic model
        return FitReportResponse(**summary_data)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"An unexpected error occurred: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal server error occurred: {str(e)}"}
        )