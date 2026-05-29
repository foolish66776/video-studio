"""
Async RunPod Serverless client — submit + polling.
Uses /run (async) + /status polling. Never /runsync.
"""
import asyncio
import logging
import time
from typing import AsyncGenerator

import httpx

from app.config import Settings
from app.models import JobResult, JobStatus

logger = logging.getLogger(__name__)

RUNPOD_BASE = "https://api.runpod.ai/v2"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_SUBMIT_RETRIES = 3


def _headers(settings: Settings) -> dict:
    return {"Authorization": f"Bearer {settings.runpod_api_key}"}


async def _post_with_retry(url: str, payload: dict, settings: Settings) -> dict:
    backoff = 2.0
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(MAX_SUBMIT_RETRIES):
            try:
                resp = await client.post(url, json=payload, headers=_headers(settings))
                if resp.status_code in RETRY_STATUSES and attempt < MAX_SUBMIT_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                if attempt == MAX_SUBMIT_RETRIES - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
    raise RuntimeError("Max retries exceeded on submit")


async def submit(endpoint_id: str, payload: dict, settings: Settings) -> str:
    """Submit a job. Returns job_id."""
    url = f"{RUNPOD_BASE}/{endpoint_id}/run"
    data = await _post_with_retry(url, payload, settings)
    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"RunPod submit returned no job id: {data}")
    logger.info("submitted job_id=%s endpoint=%s", job_id, endpoint_id)
    return job_id


async def poll(
    endpoint_id: str,
    job_id: str,
    settings: Settings,
) -> AsyncGenerator[tuple[JobStatus, str | None], None]:
    """
    Async generator that yields (status, video_url_or_None) tuples.
    Completes when job reaches COMPLETED / FAILED or timeout is reached.
    """
    url = f"{RUNPOD_BASE}/{endpoint_id}/status/{job_id}"
    deadline = time.monotonic() + settings.poll_timeout_seconds
    backoff = 1.0

    async with httpx.AsyncClient(timeout=30) as client:
        while time.monotonic() < deadline:
            await asyncio.sleep(settings.poll_interval_seconds)
            try:
                resp = await client.get(url, headers=_headers(settings))
                if resp.status_code in RETRY_STATUSES:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                resp.raise_for_status()
                backoff = 1.0
            except httpx.TimeoutException:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue

            data = resp.json()
            raw_status = data.get("status", "")
            try:
                status = JobStatus(raw_status)
            except ValueError:
                status = JobStatus.IN_PROGRESS

            elapsed = int(time.monotonic() - (deadline - settings.poll_timeout_seconds))
            logger.info("job_id=%s status=%s elapsed=%ds", job_id, status, elapsed)

            if status == JobStatus.COMPLETED:
                output = data.get("output") or {}
                video_url = (
                    output.get("video_url")
                    or output.get("s3_url")
                    or (output.get("videos") or [{}])[0].get("url")
                )
                yield status, video_url
                return

            elif status == JobStatus.FAILED:
                error = data.get("error") or str(data.get("output"))
                logger.error("job_id=%s FAILED: %s", job_id, error)
                yield status, None
                return

            else:
                yield status, None

    logger.error("job_id=%s timed out after %ds", job_id, settings.poll_timeout_seconds)
    yield JobStatus.FAILED, None


async def run_job(
    endpoint_id: str,
    payload: dict,
    settings: Settings,
) -> AsyncGenerator[tuple[str, JobResult | None], None]:
    """
    High-level helper: submit + poll. Yields (status_label, result_or_None).
    result is only set when done.
    """
    job_id = await submit(endpoint_id, payload, settings)
    yield "In coda...", None

    async for status, video_url in poll(endpoint_id, job_id, settings):
        if status == JobStatus.IN_QUEUE:
            yield "In coda...", None
        elif status == JobStatus.IN_PROGRESS:
            yield "Generazione in corso...", None
        elif status == JobStatus.COMPLETED:
            yield "Completato", JobResult(job_id=job_id, video_url=video_url)
        else:
            yield "Errore", JobResult(job_id=job_id, error=f"Job {job_id} fallito")
