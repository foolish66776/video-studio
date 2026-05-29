import logging

import gradio as gr
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.ui import build_ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

_app = FastAPI(title="video-studio")
settings = get_settings()


@_app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok"})


demo = build_ui()
app = gr.mount_gradio_app(
    _app,
    demo,
    path="/",
    auth=(settings.gradio_auth_user, settings.gradio_auth_pass),
    auth_message="Video Studio — inserisci le credenziali",
)
