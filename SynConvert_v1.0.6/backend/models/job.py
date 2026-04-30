from dataclasses import dataclass
from enum import Enum
from typing import Optional

class JobStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    DONE        = "done"
    FAILED      = "failed"
    SKIPPED     = "skipped"

@dataclass
class Job:
    """Represents one file conversion task."""
    id: str
    source: str
    output: str
    preset: str
    status: JobStatus = JobStatus.PENDING
    error: Optional[str] = None
    attempts: int = 0
