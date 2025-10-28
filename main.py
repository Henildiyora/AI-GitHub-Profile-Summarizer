import os
from dotenv import load_dotenv
from sqlmodel import Session, select
from sqlalchemy import desc
load_dotenv() 

# Added Depends
from fastapi import Depends, FastAPI, HTTPException, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import io
from pypdf import PdfReader
import hashlib
import json
import secrets

# Import the new classes from our client modules
from app.github_client import GitHubClient
from app.llm_client import LLMClient
from app.ollama_client import OllamaClient
from app.gpt_client import GPTClient
from app.aggregator_client import AggregatorClient

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import Project, Candidate

# Path Definitions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
REPORTS_DIR = os.path.join(BASE_DIR, "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Initialize FastAPI App
app = FastAPI()

ANALYSIS_CACHE: Dict[str, Any] = {}

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
gemini_client = LLMClient()
ollama_client = OllamaClient()
gpt_client = GPTClient()
aggregator_client = AggregatorClient()

# Static Files Mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

# Function to create DB on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Dependency for getting a DB session
def get_session():
    with Session(engine) as session:
        yield session

# API Endpoint to CREATE a Project
class ProjectCreate(BaseModel):
    name: str
    job_description: str

@app.post("/projects/")
def create_project(project: ProjectCreate, session: Session = Depends(get_session)):
    db_project = Project.from_orm(project)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project

# API Endpoint to LIST all Projects
@app.get("/projects/", response_model=list[Project])
def list_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(Project)).all()
    return projects

# list_candidates_for_project endpoint
@app.get("/projects/{project_id}/candidates/", response_model=List[Candidate])
def list_candidates_for_project(project_id: int, session: Session = Depends(get_session)):
    """
    Fetches all candidates associated with a specific project ID.
    """
    candidates = session.exec(
        select(Candidate)
        .where(Candidate.project_id == project_id)
        .order_by(desc(Candidate.fit_score))
    ).all()
    if not candidates:
        # Return empty list, not an error, if no candidates yet
        return []
    return candidates

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
        return ""


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

@app.post("/projects/{project_id}/summarize", response_model=Candidate)
async def get_github_summary(
    project_id: int,
    username: str = Form(...),
    resume_file: UploadFile = File(...),
    linkedin_file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
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
    if not resume_file or resume_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="A valid PDF resume file is required.")
    
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get JD from the project object
    job_description = project.job_description

    try:
        # Read and parse the resume 
        resume_contents = await resume_file.read()
        resume_text = parse_pdf_resume(resume_contents)

        linkedin_text: Optional[str] = None
        linkedin_contents: Optional[bytes] = None 
        if linkedin_file:
            if linkedin_file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail="LinkedIn file must be a PDF.")
            linkedin_contents = await linkedin_file.read()
            linkedin_text = parse_pdf_resume(linkedin_contents)

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

        # Create a unique key based on ALL data being sent to the LLM
        profile_str = json.dumps(profile, sort_keys=True)
        repos_str = json.dumps(top_repos, sort_keys=True)
        readmes_str = json.dumps(readmes, sort_keys=True)
        
        key_string = (
            f"{job_description}:{resume_text}:{linkedin_text}:"
            f"{profile_str}:{repos_str}:{readmes_str}"
        )
        cache_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()

        # Check cache
        if cache_key in ANALYSIS_CACHE:
            print(f" Returning cached result for key: {cache_key}")
            final_summary_data = ANALYSIS_CACHE[cache_key]
        else:
            print(f"Generating new report. Cache key: {cache_key}")

            common_args = {
                "profile": profile, "repos": top_repos, "readmes": readmes,
                "job_description": job_description, "resume_text": resume_text,
                "linkedin_text": linkedin_text
            }

            tasks = [
                gemini_client.generate_summary_from_github_data(**common_args),
                # ollama_client.generate_summary_from_github_data(**common_args),
                # gpt_client.generate_summary_from_github_data(**common_args)
            ]
            
            # Run both models concurrently
            all_reports_data = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out errors
            valid_reports = []
            for i, result in enumerate(all_reports_data):
                if isinstance(result, Exception):
                    print(f"Error from model {i}: {result}")
                elif "error" in result:
                    print(f"API error from model {i}: {result['error']}")
                else:
                    valid_reports.append(result)

            if not valid_reports:
                raise HTTPException(status_code=500, detail="All AI models failed to generate a report.")
            
            # Aggregator Step
            if len(valid_reports) == 1:
                print(f"Only one model succeeded ({valid_reports[0].get('model_source', 'Unknown')}), using its report directly.")
                valid_reports[0].pop('model_source', None) 
                final_summary_data = valid_reports[0]
            else:
                print(f"--- Synthesizing {len(valid_reports)} reports...")
                final_summary_data = await aggregator_client.synthesize_reports(valid_reports)

            if "error" in final_summary_data:
                 raise HTTPException(status_code=500, detail=final_summary_data["error"])
            
            # Cache the raw dictionary
            ANALYSIS_CACHE[cache_key] = final_summary_data
            

            # Query for existing candidate first
            existing_candidate = session.exec(
                select(Candidate).where(
                    Candidate.project_id == project_id,
                    Candidate.github_username == username
                )
            ).first()

            # Extract fit score from the report
            fit_score = final_summary_data.get('fit_score') # Get score from final dict

            # Prepare file paths
            candidate_folder_name = f"{username.replace('/', '_')}_{project_id}"
            candidate_dir = os.path.join(REPORTS_DIR, candidate_folder_name)
            os.makedirs(candidate_dir, exist_ok=True)
            report_file_path = os.path.join(candidate_dir, "report.json")
            resume_path = os.path.join(candidate_dir, "resume.pdf")

            # Save report JSON (always overwrite)
            with open(report_file_path, "w") as f: json.dump(final_summary_data, f, indent=4)
            # Save resume PDF (always overwrite)
            with open(resume_path, "wb") as f: f.write(resume_contents)
            # Save LinkedIn PDF if provided (always overwrite)
            if linkedin_contents:
                linkedin_path = os.path.join(candidate_dir, "linkedin.pdf")
                with open(linkedin_path, "wb") as f: f.write(linkedin_contents)

            if existing_candidate:
                print(f"--- Updating existing candidate record ID: {existing_candidate.id} ---")
                existing_candidate.report_file_path = report_file_path
                existing_candidate.fit_score = fit_score # Update score
                # existing_candidate.name = username # Optionally update name if needed
                session.add(existing_candidate)
                session.commit()
                session.refresh(existing_candidate)
                db_candidate_to_return = existing_candidate
            else:
                print(f"--- Creating new candidate record ---")
                # Generate unique ID for NEW candidates
                unique_id = secrets.token_hex(3) # Generate 6 hex characters
                
                # Ensure uniqueness (extremely unlikely collision, but good practice)
                while session.exec(select(Candidate).where(Candidate.unique_id == unique_id)).first():
                    unique_id = secrets.token_hex(3)
                    
                new_candidate = Candidate(
                    unique_id=unique_id, # Save unique ID
                    name=username, # Use GitHub username as initial name
                    github_username=username,
                    report_file_path=report_file_path,
                    project_id=project_id,
                    fit_score=fit_score # Save score
                )
                session.add(new_candidate)
                session.commit()
                session.refresh(new_candidate)
                db_candidate_to_return = new_candidate

            return db_candidate_to_return

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"An unexpected error occurred: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal server error occurred: {str(e)}"}
        )