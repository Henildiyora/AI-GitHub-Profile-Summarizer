import os
import json
import secrets
import asyncio
import io
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select
from pypdf import PdfReader, PdfWriter
from fpdf import FPDF
from sqlalchemy import desc
from datetime import datetime

# Import core logic modules
from app.analysis.skill_extractor import calculate_technical_match
from app.analysis.github_metrics import calculate_complexity_score
from app.analysis.experience_calculator import calculate_experience_score
from app.analysis.domain_analyzer import calculate_domain_relevance
from app.analysis.scoring_engine import calculate_hybrid_score, generate_audit_trail

# Import clients & DB
from app.services.github_client import GitHubClient
from app.services.llm_client import LLMClient
from app.database import engine, create_db_and_tables
from app.models import Project, Candidate

load_dotenv()

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
REPORTS_DIR = os.path.join(BASE_DIR, "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

app = FastAPI()
github_client = GitHubClient()
llm_client = LLMClient()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def get_session():
    with Session(engine) as session:
        yield session

# PDF parser helper
def parse_pdf_resume(file_contents: bytes) -> str:
    '''
    Extract text from PDF bytes.
    
    Args:
        file_contents (bytes): PDF file content in bytes.
    
    returns: str
    '''
    try:
        reader = PdfReader(io.BytesIO(file_contents))
        return "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""
    

# PDF Generation Helper
class PDFReport(FPDF):
    '''
    Custom PDF class for generating candidate reports.
    '''
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'AI Candidate Fit Report', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def chapter_title(self, title):
        '''
        Create a chapter title in the PDF.

        Args:
            title (str): The title of the chapter.
        '''
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(4)

    def chapter_body(self, body):
        '''
        Add body text to the PDF.

        Args:
            body (str): The body text.'''
        self.set_font('Helvetica', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

def generate_report_pdf(candidate: Candidate, full_data: dict) -> bytes:
    '''
    Generate a PDF report for the candidate.

    Args:
        candidate (Candidate): Candidate ORM object.
        full_data (dict): Full JSON report data.

    returns: bytes
    '''
    pdf = PDFReport()
    pdf.add_page()
    
    # Header Info
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, f"Candidate: {candidate.github_username}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"ID: {candidate.unique_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%Y-%m-%d')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Display the Hybrid Scores
    pdf.set_font('Helvetica', 'B', 14)
    final_score = candidate.final_score if candidate.final_score is not None else 0
    pdf.cell(0, 10, f"Final Fit Score: {final_score}%", new_x="LMARGIN", new_y="NEXT")
    
    # Sub-scores line
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, f"Technical Skills: {candidate.technical_skills_score}% | Experience: {candidate.experience_level_score}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Project Complexity: {candidate.project_complexity_score}% | Domain Relevance: {candidate.domain_relevance_score}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 3. Summary
    pdf.chapter_title("Executive Summary")
    pdf.chapter_body(full_data.get("summary", "No summary available."))

    # 4. Evidence
    pdf.chapter_title("Key Strengths")
    # Check 'strong_evidence' (New System) OR 'role_strengths' (Old System backup)
    strengths = full_data.get("strong_evidence", []) or full_data.get("role_strengths", [])
    
    if not strengths:
        pdf.chapter_body("No specific strengths highlighted.")
    else:
        for item in strengths:
            pdf.chapter_body(f"- {item}")
    
    # 5. Red Flags & Weaknesses
    pdf.chapter_title("Red Flags & Weaknesses")
    
    # Red Flags
    red_flags = full_data.get("red_flags", [])
    for item in red_flags:
        pdf.chapter_body(f"[!] {item}")
        
    # Weaknesses
    weaknesses = full_data.get("weak_evidence", []) or full_data.get("role_weaknesses", [])
    for item in weaknesses:
        pdf.chapter_body(f"- {item}")
        
    # Missing Skills
    missing = full_data.get("missing_skills", [])
    if missing:
        pdf.chapter_body("Missing Skills:")
        for item in missing:
            pdf.chapter_body(f" [x] {item}")

    # 6. Interview Questions
    pdf.chapter_title("Suggested Interview Questions")
    for q in full_data.get("interview_questions", []):
        pdf.chapter_body(f"? {q}")

    return bytes(pdf.output())

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    '''
    Serve the main HTML page.
    '''
    html_file_path = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(html_file_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found.")
    
@app.get("/report_view", response_class=HTMLResponse)
async def read_report_view():
    '''
    Serve the report view HTML page.
    '''
    html_file_path = os.path.join(TEMPLATES_DIR, "report.html")
    try:
        with open(html_file_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="report.html not found.")

# Project management endpoints
class ProjectCreate(BaseModel):
    '''
    Pydantic model for creating a new project.
    '''
    name: str
    job_description: str
    
@app.post("/projects/", response_model=Project)
def create_project(project_data: ProjectCreate, session: Session = Depends(get_session)):
    '''
    Create a new project.
    '''
    db_project = Project(name=project_data.name, job_description=project_data.job_description)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project

@app.get("/projects/")
def list_projects(session: Session = Depends(get_session)):
    '''
    List all projects.
    '''
    return session.exec(select(Project)).all()

@app.get("/projects/{project_id}/candidates/")
def list_candidates(project_id: int, session: Session = Depends(get_session)):
    '''
    List all candidates for a given project, ordered by final score descending.
    '''
    return session.exec(select(Candidate).where(Candidate.project_id == project_id).order_by(desc(Candidate.final_score))).all()


@app.get("/projects/{project_id}/candidates/{candidate_id}/download")
async def download_candidate_report(
    project_id: int,
    candidate_id: int,
    include_resume: bool = False,
    include_linkedin: bool = False,
    session: Session = Depends(get_session)
):
    
    '''
    Download the candidate report as a PDF, optionally including resume and LinkedIn files.
    Args:
        project_id (int): The ID of the project.
        candidate_id (int): The ID of the candidate.
        include_resume (bool): Whether to include the resume PDF.
        include_linkedin (bool): Whether to include the LinkedIn PDF.
        session (Session): Database session.
        
    returns: Response

    '''

    # Fetch candidate
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    
    # Load the full JSON report
    try:
        with open(candidate.report_file_path, "r") as f:
            full_data = json.load(f)
    except:
        full_data = {}

    # Generate the AI Report PDF
    report_pdf_bytes = generate_report_pdf(candidate, full_data)
    
    # Merge with other files if requested
    merger = PdfWriter()
    
    # Add Report
    merger.append(io.BytesIO(report_pdf_bytes))
    
    # Add Resume
    if include_resume:
        resume_path = os.path.join(os.path.dirname(candidate.report_file_path), "resume.pdf")
        if os.path.exists(resume_path):
            merger.append(resume_path)
            
    # Add LinkedIn
    if include_linkedin:
        linkedin_path = os.path.join(os.path.dirname(candidate.report_file_path), "linkedin.pdf")
        if os.path.exists(linkedin_path):
            merger.append(linkedin_path)

    # 3. Return final PDF
    output_buffer = io.BytesIO()
    merger.write(output_buffer)
    merger.close()
    
    pdf_data = output_buffer.getvalue()
    
    headers = {
        'Content-Disposition': f'attachment; filename="{candidate.github_username}_report.pdf"'
    }
    return Response(content=pdf_data, media_type="application/pdf", headers=headers)

# Main candidate analysis endpoint
@app.post("/projects/{project_id}/summarize", response_model=Candidate)
async def analyze_candidate(
    project_id: int,
    username: str = Form(...),
    resume_file: UploadFile = File(...),
    linkedin_file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    
    '''
    Analyze a candidate's GitHub profile and resume against a project job description.
    Args:
        project_id (int): The ID of the project.
        username (str): GitHub username or URL.
        resume_file (UploadFile): Uploaded resume PDF file.
        linkedin_file (Optional[UploadFile]): Uploaded LinkedIn PDF file.
        session (Session): Database session.
    returns: Candidate
    '''

    # 1. Data Prep & Validation
    cleaned_username = username.strip() 
    if "github.com" in cleaned_username:
        # Split by github.com and take the last part
        parts = cleaned_username.split("github.com/")
        if len(parts) > 1:
            cleaned_username = parts[1]
            # Remove any trailing slashes or query params (e.g., /?ref=...)
            cleaned_username = cleaned_username.split("/")[0].split("?")[0]
    username = cleaned_username
    if not username: 
        raise HTTPException(status_code=400, detail="GitHub username is required.")

    # Fetch project
    project = session.get(Project, project_id)
    if not project: 
        raise HTTPException(404, "Project not found")
    
    # Parse Resume & LinkedIn
    resume_bytes = await resume_file.read()
    resume_text = parse_pdf_resume(resume_bytes)
    if not resume_text: 
        raise HTTPException(400, "Empty/Invalid Resume PDF")
    
    linkedin_text = ""
    if linkedin_file:
        linkedin_text = parse_pdf_resume(await linkedin_file.read())

    # 2. Fetch GitHub Data
    profile_task = github_client.get_user_profile(username)
    repos_task = github_client.get_user_repos(username)
    profile, repos = await asyncio.gather(profile_task, repos_task)
    if not profile: raise HTTPException(404, "GitHub user not found")
    
    # Fetch READMEs for deeper context
    top_repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)[:5]
    readme_tasks = [github_client.get_readme_content(username, repo['name']) for repo in top_repos]
    readmes_list = await asyncio.gather(*readme_tasks)
    readmes = {repo['name']: content for repo, content in zip(top_repos, readmes_list) if content}
    
    # Calculate Quantitative Scores
    # A. Technical Score (40%)
    tech_score, matches, missing = calculate_technical_match(resume_text + " " + json.dumps(repos), project.job_description)
    
    # B. Experience Score (25%)
    exp_score = calculate_experience_score(resume_text, project.job_description)
    
    # C. Complexity Score (20%)
    comp_score = calculate_complexity_score(repos)
    
    # D. Domain Score (15%)
    dom_score = calculate_domain_relevance(project.job_description, resume_text)

    # Pack scores for the LLM
    quantitative_data = {
        "technical_skills": tech_score,
        "experience_level": exp_score,
        "project_complexity": comp_score,
        "domain_relevance": dom_score,
        "details": {
            "matched_skills": matches,
            "missing_skills": missing
        }
    }

    # AI Analysis & Summary
    print(" Running AI Analysis")
    ai_result = await llm_client.generate_summary_from_github_data(
        profile, 
        top_repos, 
        readmes, 
        project.job_description, 
        resume_text, 
        linkedin_text, 
        quantitative_data
    )
    
    if "error" in ai_result: raise HTTPException(500, ai_result["error"])

    # 5. Calculate final hybrid score
    llm_adjustment = ai_result.get("llm_adjustment", 0)
    
    scoring_result = calculate_hybrid_score(
        tech_score, exp_score, comp_score, dom_score, llm_adjustment
    )
    
    # Generate audit trail
    audit_trail = generate_audit_trail(
        {"tech": tech_score, "exp": exp_score, "comp": comp_score, "dom": dom_score},
        {"adjustment": llm_adjustment, "reason": ai_result.get("adjustment_reasoning")}
    )

    # Save to DB
    # Check for existing candidate to update
    existing = session.exec(select(Candidate).where(Candidate.project_id == project_id, Candidate.github_username == username)).first()
    
    # Extract evidence lists safely
    evidence = ai_result.get("breakdown", {})
    
    candidate_data = {
        "name": username,
        "github_username": username,
        "report_file_path": "placeholder",
        "project_id": project_id,
        
        # Metrics
        "technical_skills_score": tech_score,
        "experience_level_score": exp_score,
        "project_complexity_score": comp_score,
        "domain_relevance_score": dom_score,
        
        # Final Scores
        "base_score": scoring_result["base_score"],
        "llm_adjustment": llm_adjustment,
        "final_score": scoring_result["final_score"],
        
        # Evidence & Audit
        "confidence_level": scoring_result["confidence_level"],
        "confidence_percentage": scoring_result["confidence_percentage"],
        "strong_evidence": evidence.get("strong_evidence", []),
        "weak_evidence": evidence.get("weak_evidence", []),
        "missing_skills": evidence.get("missing_skills", []),
        "red_flags": evidence.get("red_flags", []),
        "audit_trail": audit_trail
    }

    # Save full JSON report to file for the frontend to view details (Summary, Interview Questions)
    full_report = {
        **candidate_data,
        "summary": ai_result.get("summary"),
        "interview_questions": ai_result.get("interview_questions")
    }
    
    # File Saving Logic
    folder = os.path.join(REPORTS_DIR, f"{username}_{project_id}")
    os.makedirs(folder, exist_ok=True)
    report_path = os.path.join(folder, "report.json")
    with open(report_path, "w") as f: json.dump(full_report, f, indent=2)
    
    candidate_data["report_file_path"] = report_path # Update path
    
    if existing:
        for key, value in candidate_data.items():
            setattr(existing, key, value)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        unique_id = secrets.token_hex(3)
        new_cand = Candidate(unique_id=unique_id, **candidate_data)
        session.add(new_cand)
        session.commit()
        session.refresh(new_cand)
        return new_cand