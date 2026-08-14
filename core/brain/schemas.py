from typing import List, Optional

from pydantic import BaseModel, Field


class Intent(BaseModel):
    intent: str
    target: Optional[str] = None
    params: dict = Field(default_factory=dict)
    raw_text: Optional[str] = None
    # Only populated when intent == "multi_step_task": a list of raw
    # {"intent", "target", "params"} dicts, each turned into its own Intent
    # and run through the normal single-intent execution/permission pipeline
    # by dispatch.py. Kept as plain dicts here (not List["Intent"]) to avoid
    # pydantic self-reference complexity for what's a thin pass-through.
    steps: Optional[List[dict]] = None
