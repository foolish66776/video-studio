"""
Gradio UI for Frank — Italian labels, zero ComfyUI vocabulary.
"""
import asyncio
import base64
import logging
import random
import tempfile
from pathlib import Path

import gradio as gr

from app.config import get_settings
from app.keyframe import generate_keyframe, image_file_to_base64
from app.models import Flow, GenParams
from app.runpod_client import run_job
from app.workflows import build_payload, duration_to_frames

logger = logging.getLogger(__name__)

FLOW_LABELS = {
    "Nano (animazione laboratorio)": Flow.NANO,
    "EIV (video realistico)":        Flow.EIV,
}

DURATION_PRESETS = {
    "5 secondi":  5.0,
    "10 secondi": 10.0,
    "15 secondi": 15.0,
}

ENDPOINT_MAP = {
    Flow.NANO: lambda s: s.runpod_endpoint_nano,
    Flow.EIV:  lambda s: s.runpod_endpoint_eiv,
}

LORA_MAP = {
    Flow.NANO: lambda s: s.lora_nano,
    Flow.EIV:  lambda s: s.lora_eiv,
}


async def _run_generation(
    flow_label: str,
    keyframe_mode: str,
    keyframe_prompt: str,
    keyframe_image,
    motion_prompt: str,
    audio_file,
    duration_label: str,
    seed_input: int,
    lora_strength: float,
) -> tuple:
    """
    Core generation coroutine. Returns (status_text, video_path, download_url).
    Yields intermediate status updates via gr.Progress (implicit through generator).
    """
    settings = get_settings()
    flow = FLOW_LABELS[flow_label]

    # --- Keyframe ---
    if keyframe_mode == "Genera da prompt":
        if not keyframe_prompt.strip():
            return "Inserisci un prompt per il keyframe.", None, None
        yield "Generazione keyframe in corso...", None, None
        try:
            kf_b64, kf_name = generate_keyframe(keyframe_prompt.strip(), seed_input, settings)
        except Exception as e:
            logger.exception("keyframe generation failed")
            return f"Errore keyframe: {e}", None, None
    else:
        if keyframe_image is None:
            return "Carica un'immagine keyframe.", None, None
        kf_b64, kf_name = image_file_to_base64(keyframe_image)

    # --- Audio ---
    audio_b64 = None
    audio_filename = "audio.wav"
    if audio_file is not None:
        with open(audio_file, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        audio_filename = Path(audio_file).name

    # --- Params ---
    fps = 24
    frame_count = duration_to_frames(DURATION_PRESETS[duration_label], fps)
    seed = seed_input if seed_input > 0 else random.randint(1, 2**31)

    params = GenParams(
        flow=flow,
        motion_prompt=motion_prompt.strip(),
        seed=seed,
        frame_count=frame_count,
        audio_b64=audio_b64,
        audio_filename=audio_filename,
        lora_name=LORA_MAP[flow](settings),
        lora_strength=lora_strength,
    )

    payload = build_payload(flow, params, kf_b64, kf_name)
    endpoint_id = ENDPOINT_MAP[flow](settings)

    # --- Submit + poll ---
    yield "Invio al worker GPU...", None, None

    video_url = None
    job_id = None

    async for status_label, result in run_job(endpoint_id, payload, settings):
        if result is not None:
            if result.ok:
                video_url = result.video_url
                job_id = result.job_id
            else:
                error_msg = result.error or "Errore sconosciuto"
                yield f"Generazione fallita — {error_msg}\n(job id: {result.job_id})", None, None
                return
        yield status_label, None, None

    if not video_url:
        yield "Generazione fallita — nessun URL video ricevuto.", None, None
        return

    # --- Download video locally for preview ---
    import httpx
    try:
        video_bytes = httpx.get(video_url, timeout=120).content
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(video_bytes)
        tmp.close()
        local_path = tmp.name
    except Exception as e:
        logger.exception("video download failed")
        yield f"Video generato ma download fallito: {e}\nURL diretto: {video_url}", None, video_url
        return

    yield f"Completato! (job: {job_id})", local_path, video_url


def build_ui() -> gr.Blocks:
    settings = get_settings()

    with gr.Blocks(title="Video Studio", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Video Studio")
        gr.Markdown("Genera video con il personaggio Nano o con EIV.")

        with gr.Row():
            with gr.Column(scale=1):
                flow_radio = gr.Radio(
                    choices=list(FLOW_LABELS.keys()),
                    value="Nano (animazione laboratorio)",
                    label="Flusso",
                )

                keyframe_mode_radio = gr.Radio(
                    choices=["Genera da prompt", "Carica immagine"],
                    value="Genera da prompt",
                    label="Keyframe",
                )

                keyframe_prompt_box = gr.Textbox(
                    label="Prompt keyframe",
                    placeholder="NANO_ARTIGIANO, steampunk gnome in workshop, dramatic lighting...",
                    lines=3,
                    visible=True,
                )

                keyframe_upload = gr.Image(
                    label="Immagine keyframe",
                    type="filepath",
                    visible=False,
                )

                motion_prompt_box = gr.Textbox(
                    label="Descrizione movimento / scena",
                    placeholder="Il nano esamina un ingranaggio, gesticolando mentre spiega...",
                    lines=3,
                )

                audio_upload = gr.Audio(
                    label="Audio (voce / lip sync)",
                    type="filepath",
                    sources=["upload", "microphone"],
                )

                duration_radio = gr.Radio(
                    choices=list(DURATION_PRESETS.keys()),
                    value="5 secondi",
                    label="Durata",
                )

                with gr.Accordion("Avanzate", open=False):
                    seed_input = gr.Number(
                        label="Seed (0 = casuale)",
                        value=0,
                        precision=0,
                        minimum=0,
                    )
                    lora_slider = gr.Slider(
                        label="Forza LoRA personaggio",
                        minimum=0.0,
                        maximum=1.5,
                        value=0.9,
                        step=0.05,
                    )

                generate_btn = gr.Button("Genera", variant="primary", size="lg")

            with gr.Column(scale=1):
                status_box = gr.Textbox(label="Stato", interactive=False, lines=2)
                video_out = gr.Video(label="Video generato")
                download_link = gr.Textbox(label="Link download diretto (R2)", interactive=False)

        # Toggle keyframe mode visibility
        def _toggle_keyframe_mode(mode: str):
            return (
                gr.update(visible=(mode == "Genera da prompt")),
                gr.update(visible=(mode == "Carica immagine")),
            )

        keyframe_mode_radio.change(
            _toggle_keyframe_mode,
            inputs=keyframe_mode_radio,
            outputs=[keyframe_prompt_box, keyframe_upload],
        )

        # Generation
        generate_btn.click(
            fn=_run_generation,
            inputs=[
                flow_radio,
                keyframe_mode_radio,
                keyframe_prompt_box,
                keyframe_upload,
                motion_prompt_box,
                audio_upload,
                duration_radio,
                seed_input,
                lora_slider,
            ],
            outputs=[status_box, video_out, download_link],
        )

    return demo
