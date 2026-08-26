from pydantic import BaseModel


class Pendency(BaseModel):
    name: str
    project_name: str


class Technology(BaseModel):
    name: str
    count: int


class ProjectMetrics(BaseModel):
    total_projects: int
    in_progress_count: int
    completed_count: int
    stopped_count: int
    ideas_count: int
    pendency_count: int
