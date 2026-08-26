from pydantic import BaseModel


class Note(BaseModel):
    name: str
    path: str
    content: str = ''


class NoteUpdate(BaseModel):
    content: str


class Project(BaseModel):
    name: str
    status: str
    technologies: list[str] = []
    project_code_path: str
    pendency_count: int
    last_commit: str
    notes: list[Note] = []


class ProjectList(BaseModel):
    name: str
    relative_path: str
    status: str
    technologies: list[str] = []
