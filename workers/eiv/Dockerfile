FROM runpod/worker-comfyui:3.3.0-base

# Custom nodes for LTX-2.3 with lip sync
RUN comfy node install ComfyUI-LTXVideo
RUN comfy node install ComfyUI-KJNodes

# Point ComfyUI at the network volume for models
ENV COMFYUI_MODEL_PATH=/runpod-volume/models

# Models on Network Volume (NOT baked in) — attach volume at /runpod-volume:
#
#   models/checkpoints/ltx-2.3-22b-dev-fp8.safetensors
#   models/clip/gemma_3_12B_it_fp4_mixed.safetensors
#   models/upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors
#   models/loras/<nano_character_lora>.safetensors
#   models/loras/<eiv_character_lora>.safetensors
#
# Required env vars on the RunPod endpoint:
#   BUCKET_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
#   BUCKET_ACCESS_KEY_ID=
#   BUCKET_SECRET_ACCESS_KEY=
#   BUCKET_NAME=nanobot-v-3
