import json
import uuid
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional, Dict
from backend.models.job import Job, JobStatus
from backend.core.exceptions import SynConvertError

class QueueService:
    """Service for managing the persistent job queue."""

    def __init__(self, queue_file: str | Path):
        self._path = Path(queue_file)
        self._jobs: List[Job] = []
        self._load()

    def add(self, source: str, output: str, preset: str) -> Job:
        """Add or update a job in the queue."""
        existing = next((j for j in self._jobs if j.source == source), None)
        if existing:
            if existing.status in (JobStatus.FAILED, JobStatus.SKIPPED):
                existing.status = JobStatus.PENDING
                existing.error = None
                existing.output = output
                existing.preset = preset
                self._save()
            return existing

        job = Job(
            id=str(uuid.uuid4()),
            source=source,
            output=output,
            preset=preset
        )
        self._jobs.append(job)
        self._save()
        return job

    def get_pending(self) -> List[Job]:
        return [j for j in self._jobs if j.status == JobStatus.PENDING]

    def get_all(self) -> List[Job]:
        return list(self._jobs)

    def update_status(self, job_id: str, status: JobStatus, error: Optional[str] = None):
        job = next((j for j in self._jobs if j.id == job_id), None)
        if job:
            job.status = status
            job.error = error
            if status == JobStatus.IN_PROGRESS:
                job.attempts += 1
            self._save()

    def clear_completed(self) -> int:
        before = len(self._jobs)
        self._jobs = [j for j in self._jobs if j.status not in (JobStatus.DONE, JobStatus.SKIPPED)]
        self._save()
        return before - len(self._jobs)

    def reset_failed(self) -> int:
        count = 0
        for j in self._jobs:
            if j.status == JobStatus.FAILED:
                j.status = JobStatus.PENDING
                j.error = None
                count += 1
        if count: self._save()
        return count

    def remove_by_ids(self, ids: List[str]) -> int:
        """Remove specific jobs by their IDs. Returns count removed."""
        before = len(self._jobs)
        id_set = set(ids)
        self._jobs = [j for j in self._jobs if j.id not in id_set]
        self._save()
        return before - len(self._jobs)

    def clear_all_history(self) -> int:
        """Remove all non-pending jobs (done, failed, skipped). Returns count removed."""
        before = len(self._jobs)
        self._jobs = [j for j in self._jobs if j.status == JobStatus.PENDING]
        self._save()
        return before - len(self._jobs)

    def get_summary(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in JobStatus}
        for j in self._jobs:
            counts[j.status.value] += 1
        return counts

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(j) for j in self._jobs]
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            raise SynConvertError(f"Failed to save queue: {exc}")

    def _load(self):
        if not self._path.exists():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                raw = json.load(f)
            self._jobs = [
                Job(
                    id=d["id"],
                    source=d["source"],
                    output=d["output"],
                    preset=d["preset"],
                    status=JobStatus(d.get("status", "pending")),
                    error=d.get("error"),
                    attempts=d.get("attempts", 0),
                )
                for d in raw
            ]
            # Recovery logic for interrupted jobs
            recovered = 0
            for job in self._jobs:
                if job.status == JobStatus.IN_PROGRESS:
                    job.status = JobStatus.PENDING
                    job.error = None
                    recovered += 1
            if recovered: self._save()
        except Exception:
            self._jobs = []
