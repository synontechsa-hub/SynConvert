"""Job queue for SynConvert.

Manages a persistent list of conversion jobs. State is written to a JSON
file after every status change so that interrupted runs can be resumed.

Job lifecycle:
    pending → in_progress → done
                         → failed
    (any) → skipped
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Iterator


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
    source: str          # Absolute source path (str for JSON serialisation)
    output: str          # Absolute output path
    preset: str          # Preset name, e.g. "720p_mobile"
    status: JobStatus = JobStatus.PENDING
    error: str | None = None
    attempts: int = 0

    @classmethod
    def create(cls, source: str, output: str, preset: str) -> "Job":
        return cls(id=str(uuid.uuid4()), source=source, output=output, preset=preset)

    def mark_in_progress(self) -> None:
        self.status = JobStatus.IN_PROGRESS
        self.attempts += 1

    def mark_done(self) -> None:
        self.status = JobStatus.DONE

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error

    def mark_skipped(self, reason: str = "") -> None:
        self.status = JobStatus.SKIPPED
        self.error = reason or None


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

class JobQueue:
    """Persistent job queue backed by a JSON file."""

    def __init__(self, queue_file: str | Path) -> None:
        self._path = Path(queue_file)
        self._jobs: list[Job] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, source: str, output: str, preset: str) -> Job:
        """Add a new pending job. Deduplicates by source path.
        If an existing job is failed or skipped, it resets it to pending.
        """
        existing = self._by_source(source)
        if existing:
            if existing.status in (JobStatus.FAILED, JobStatus.SKIPPED):
                existing.status = JobStatus.PENDING
                existing.error = None
                existing.output = output
                existing.preset = preset
                self._save()
            return existing

        job = Job.create(source=source, output=output, preset=preset)
        self._jobs.append(job)
        self._save()
        return job

    def add_many(self, entries: list[dict]) -> list[Job]:
        """Bulk-add jobs. Each entry must have 'source', 'output', 'preset'."""
        jobs = []
        for entry in entries:
            jobs.append(self.add(entry["source"], entry["output"], entry["preset"]))
        return jobs

    def pending(self) -> list[Job]:
        """Return all pending jobs in order."""
        return [j for j in self._jobs if j.status == JobStatus.PENDING]

    def all_jobs(self) -> list[Job]:
        return list(self._jobs)

    def update(self, job: Job) -> None:
        """Persist any status change on a job object."""
        self._save()

    def clear_completed(self) -> int:
        """Remove done/skipped jobs. Returns count removed."""
        before = len(self._jobs)
        self._jobs = [j for j in self._jobs if j.status not in (JobStatus.DONE, JobStatus.SKIPPED)]
        self._save()
        return before - len(self._jobs)

    def reset_failed(self) -> int:
        """Reset failed jobs back to pending for retry. Returns count reset."""
        count = 0
        for j in self._jobs:
            if j.status == JobStatus.FAILED:
                j.status = JobStatus.PENDING
                j.error = None
                count += 1
        if count:
            self._save()
        return count

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in JobStatus}
        for j in self._jobs:
            counts[j.status.value] += 1
        return counts

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(j) for j in self._jobs]
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
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
        except (json.JSONDecodeError, KeyError, TypeError):
            self._jobs = []  # Corrupt queue — start fresh

    def _by_source(self, source: str) -> Job | None:
        for j in self._jobs:
            if j.source == source:
                return j
        return None
