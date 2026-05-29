from enum import Enum
from dataclasses import dataclass, field


class Flow(str, Enum):
    NANO = "nano"
    EIV = "eiv"


class KeyframeMode(str, Enum):
    GENERATE = "generate"
    UPLOAD = "upload"


class JobStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class GenParams:
    flow: Flow
    motion_prompt: str
    seed: int
    frame_count: int
    audio_b64: str | None = None       # base64-encoded audio file for lip sync
    audio_filename: str = "audio.wav"
    lora_name: str = ""                # character LoRA filename in loras/
    lora_strength: float = 0.9        # character LoRA strength


@dataclass
class JobResult:
    job_id: str
    video_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.video_url is not None
