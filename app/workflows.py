"""
Workflow template loading and parameter injection.

Templates live in workflows/<flow>_ltx.api.json and use sentinel strings
as placeholders. Injection locates nodes by class_type + title, never by
numeric node ID (which changes when the workflow is edited).

Sentinels:
    __KEYFRAME_IMAGE__    filename of the input image (e.g. "keyframe.png")
    __AUDIO_FILE__        filename of the audio file (e.g. "audio.wav")
    __POSITIVE_PROMPT__   scene / motion description
    __SEED__              integer seed (injected as int, not string)
    __FRAME_COUNT__       number of frames (int), must satisfy (N-1)%8==0
    __LORA_NAME__         character LoRA filename in loras/
    __LORA_STRENGTH__     LoRA strength (float)
"""
import copy
import json
import logging
from pathlib import Path

from app.models import Flow, GenParams

logger = logging.getLogger(__name__)

WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"

# Default output dimensions per flow
FLOW_DEFAULTS: dict[Flow, dict] = {
    Flow.NANO: {"width": 576, "height": 1024, "fps": 24},
    Flow.EIV:  {"width": 576, "height": 1024, "fps": 24},
}


def _load_template(flow: Flow) -> dict:
    path = WORKFLOWS_DIR / f"{flow.value}_ltx.api.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow template not found: {path}")
    with open(path) as f:
        return json.load(f)


def _replace_sentinel(obj, sentinel: str, value):
    """Recursively replace sentinel strings in a nested dict/list."""
    if isinstance(obj, dict):
        return {k: _replace_sentinel(v, sentinel, value) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_sentinel(item, sentinel, value) for item in obj]
    if obj == sentinel:
        return value
    if isinstance(obj, str) and sentinel in obj:
        return obj.replace(sentinel, str(value))
    return obj


def _inject(workflow: dict, sentinel: str, value) -> dict:
    replaced = _replace_sentinel(workflow, sentinel, value)
    if replaced == workflow:
        logger.warning("Sentinel %s not found in workflow — check template", sentinel)
    return replaced


def build_payload(
    flow: Flow,
    params: GenParams,
    keyframe_b64: str,
    keyframe_filename: str = "keyframe.png",
) -> dict:
    """
    Build the full RunPod request body:
    {
      "input": {
        "workflow": <api-format json with params injected>,
        "images": [{"name": "keyframe.png", "image": "<base64>"}, ...]
      }
    }
    """
    workflow = _load_template(flow)
    workflow = copy.deepcopy(workflow)

    workflow = _inject(workflow, "__KEYFRAME_IMAGE__", keyframe_filename)
    workflow = _inject(workflow, "__POSITIVE_PROMPT__", params.motion_prompt)
    workflow = _inject(workflow, "__SEED__", params.seed)
    workflow = _inject(workflow, "__FRAME_COUNT__", params.frame_count)
    workflow = _inject(workflow, "__LORA_NAME__", params.lora_name)
    workflow = _inject(workflow, "__LORA_STRENGTH__", params.lora_strength)

    files = [{"name": keyframe_filename, "image": keyframe_b64}]

    if params.audio_b64:
        workflow = _inject(workflow, "__AUDIO_FILE__", params.audio_filename)
        files.append({"name": params.audio_filename, "image": params.audio_b64})
    else:
        workflow = _inject(workflow, "__AUDIO_FILE__", "")

    return {
        "input": {
            "workflow": workflow,
            "images": files,
        }
    }


def duration_to_frames(duration_seconds: float, fps: int = 24) -> int:
    """Convert duration in seconds to frame count (must be multiple of 8 for LTX)."""
    frames = int(duration_seconds * fps)
    # LTX requires frame count to satisfy (N - 1) % 8 == 0
    remainder = (frames - 1) % 8
    if remainder != 0:
        frames += 8 - remainder
    return max(frames, 9)
