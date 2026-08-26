from typing import Optional

from pydantic import BaseModel


class Command(BaseModel):
    command: str
    cwd: Optional[str] = None
