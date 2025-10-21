import os
from dotenv import load_dotenv
load_dotenv() 

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio

# Import our client modules
from app import github_client, llm_client


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Initialize the FastAPI app
app = FastAPI()

# Pydantic Models
class SummaryRequest(BaseModel):
    username: str

# This model MUST match the JSON structure from the prompt
class AnalysisResponse(BaseModel):
    summary: str
    technologies: List[str]
    strengths: List[str]
    growth_areas: List[str]
    interview_questions: List[str]
    error: Optional[str] = None

# Mount Static Files (Using Absolute Path)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Serve HTML (Using Absolute Path)
    html_file_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(html_file_path) as f:
        return HTMLResponse(content=f.read(), status_code=200)

# API Endpoint
@app.post("/summarize", response_model=AnalysisResponse)
async def get_github_summary(request: SummaryRequest):
    """
    This is the main API endpoint.
    It now returns a structured JSON AnalysisResponse.
    """
    username = request.username
    if not username:
        raise HTTPException(status_code=400, detail="GitHub username is required.")

    try:
        # 1. Fetch profile and repos from GitHub concurrently
        profile_task = github_client.get_user_profile(username)
        repos_task = github_client.get_user_repos(username)
        profile, repos = await asyncio.gather(profile_task, repos_task)

        if not profile:
            raise HTTPException(status_code=404, detail="GitHub user not found.")

        # 2. For the top 5 repos, fetch their READMEs concurrently
        top_repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)[:5]
        readme_tasks = [github_client.get_readme_content(username, repo['name']) for repo in top_repos]
        readme_contents = await asyncio.gather(*readme_tasks)

        # Create a dictionary mapping repo name to its README content
        readmes = {repo['name']: content for repo, content in zip(top_repos, readme_contents) if content}

        # 3. Generate the structured summary using the LLM
        summary_data = await llm_client.generate_summary_from_github_data(profile, top_repos, readmes)

        if "error" in summary_data:
             raise HTTPException(status_code=500, detail=summary_data["error"])

        # Validate and return the data using our Pydantic model
        return AnalysisResponse(**summary_data)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal server error occurred: {str(e)}"}
        )