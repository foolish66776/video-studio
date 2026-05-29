FROM runpod/worker-comfyui:3.3.0-base

# Custom nodes for LTX-2.3 with lip sync
RUN comfy node install ComfyUI-LTXVideo
RUN comfy node install ComfyUI-KJNodes

# In Serverless, Network Volume is mounted at /runpod-volume.
# Our volume has models at: /runpod-volume/runpod-slim/ComfyUI/models/
# (same directory tree as when it was a pod, where /workspace = volume root)
ENV COMFYUI_MODEL_PATH=/runpod-volume/runpod-slim/ComfyUI/models

# Models already on the Network Volume (volume ID: tggv8kuamv):
#   runpod-slim/ComfyUI/models/checkpoints/ltx-2.3-22b-dev-fp8.safetensors        (28GB)
#   runpod-slim/ComfyUI/models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors  (8.8GB)
#   runpod-slim/ComfyUI/models/latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors
#   runpod-slim/ComfyUI/models/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors
#   runpod-slim/ComfyUI/models/loras/<nano_character_lora>.safetensors   (da aggiungere dopo training)
#
# Required env vars on the RunPod endpoint:
#   BUCKET_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
#   BUCKET_ACCESS_KEY_ID=
#   BUCKET_SECRET_ACCESS_KEY=
#   BUCKET_NAME=nanobot-v-3
