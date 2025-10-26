from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    job_description: str

    # This links a project to its candidates
    candidates: list["Candidate"] = Relationship(back_populates="project")

class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    github_username: str = Field(index=True)
    report_file_path: str  # Path to the saved .json report

    project_id: int = Field(foreign_key="project.id")
    project: Project = Relationship(back_populates="candidates")