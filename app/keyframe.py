"""
Keyframe generation via fal.ai — Flux Dev + custom image LoRA.
Returns the keyframe as base64-encoded PNG.
"""
import base64
import os

import httpx

from app.config import Settings


def generate_keyframe(prompt: str, seed: int, settings: Settings) -> tuple[str, str]:
    """
    Call fal.ai Flux Dev + LoRA to generate a keyframe.

    Returns (base64_image, filename) where filename is 'keyframe.png'.
    Raises RuntimeError on failure.
    """
    import fal_client

    os.environ["FAL_KEY"] = settings.fal_key

    result = fal_client.subscribe(
        settings.fal_flux_model,
        arguments={
            "prompt": prompt,
            "loras": [{"path": settings.fal_flux_lora_url, "scale": settings.fal_flux_lora_scale}],
            "image_size": {"width": 576, "height": 1024},
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "seed": seed,
            "num_images": 1,
            "output_format": "png",
        },
    )

    images = result.get("images") or []
    if not images:
        raise RuntimeError(f"fal.ai returned no images: {result}")

    image_url = images[0]["url"]
    img_bytes = httpx.get(image_url, timeout=60).content
    return base64.b64encode(img_bytes).decode(), "keyframe.png"


def image_file_to_base64(path: str) -> tuple[str, str]:
    """Convert a local image file to (base64, filename)."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), os.path.basename(path)
