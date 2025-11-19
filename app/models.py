from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column
from typing import Optional, List, Dict, Any

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    job_description: str
    
    candidates: list["Candidate"] = Relationship(back_populates="project")

class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unique_id: str = Field(index=True, unique=True)
    name: str
    github_username: str = Field(index=True)
    report_file_path: str
    
    # Quantitative metrics (0-100)
    technical_skills_score: Optional[int] = Field(default=0)
    experience_level_score: Optional[int] = Field(default=0)
    project_complexity_score: Optional[int] = Field(default=0)
    domain_relevance_score: Optional[int] = Field(default=0)
    
    # Final hybrid scores
    base_score: Optional[int] = Field(default=0) # The math-only score
    llm_adjustment: Optional[int] = Field(default=0) # The AI's adjustment (+/- 20)
    final_score: Optional[int] = Field(default=0, index=True) # The final result
    
    # Confidence & XAI
    confidence_level: Optional[str] = Field(default="Low") # High, Medium, Low
    confidence_percentage: Optional[float] = Field(default=0.0)
    
    # We use sa_column=Column(JSON) to store lists/dicts in SQLite/Postgres
    strong_evidence: List[str] = Field(default=[], sa_column=Column(JSON))
    weak_evidence: List[str] = Field(default=[], sa_column=Column(JSON))
    missing_skills: List[str] = Field(default=[], sa_column=Column(JSON))
    red_flags: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Stores the full math breakdown for transparency
    audit_trail: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    project_id: int = Field(foreign_key="project.id")
    project: Project = Relationship(back_populates="candidates")