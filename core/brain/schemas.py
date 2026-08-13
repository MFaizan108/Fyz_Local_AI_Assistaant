from typing import Optional

from pydantic import BaseModel, Field


class Intent(BaseModel):
    intent: str
    target: Optional[str] = None
    params: dict = Field(default_factory=dict)
    raw_text: Optional[str] = None
