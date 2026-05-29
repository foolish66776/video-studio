"""
Long video generation via sequential continuation.

Strategy: generate clips in sequence where each clip's first frame is the
last frame of the previous clip. Stitch all clips with ffmpeg.

Usage:
    results = await generate_long_video(
        endpoint_id, flow, params_list, keyframe_b64, settings
    )
    # returns path to the final stitched video
"""
import asyncio
import base64
import logging
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.models import Flow, GenParams

logger = logging.getLogger(__name__)


async def download_video(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def extract_last_frame(video_bytes: bytes, output_path: Path) -> None:
    """Use ffmpeg to extract the last frame of a video as PNG."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-sseof", "-0.1",
            "-i", tmp_path,
            "-vframes", "1",
            "-update", "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    Path(tmp_path).unlink(missing_ok=True)


def stitch_clips(clip_paths: list[Path], output_path: Path, fps: int = 24) -> Path:
    """Concatenate MP4 clips with ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
        list_path = f.name

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    Path(list_path).unlink(missing_ok=True)
    return output_path


def build_continuation_params(base_params: GenParams, n_clips: int) -> list[GenParams]:
    """
    Build a list of GenParams for n_clips sequential clips.
    Each clip uses the same motion_prompt and audio (audio is not continued,
    it must be pre-segmented or the same track is re-used).
    Seeds are incremented to avoid identical motion patterns.
    """
    return [
        GenParams(
            flow=base_params.flow,
            motion_prompt=base_params.motion_prompt,
            seed=base_params.seed + i,
            frame_count=base_params.frame_count,
            audio_b64=base_params.audio_b64,
            audio_filename=base_params.audio_filename,
            negative_prompt=base_params.negative_prompt,
        )
        for i in range(n_clips)
    ]
