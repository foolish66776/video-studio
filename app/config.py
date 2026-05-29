from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # RunPod
    runpod_api_key: str
    runpod_endpoint_nano: str
    runpod_endpoint_eiv: str

    # fal.ai — keyframe generation
    fal_key: str
    fal_flux_model: str = "fal-ai/flux-lora"
    fal_flux_lora_url: str = ""
    fal_flux_lora_scale: float = 0.9

    # RunPod worker — character LoRA filenames (must exist on Network Volume)
    lora_nano: str = "nano_artigiano_v1.safetensors"
    lora_eiv: str = "eiv_v1.safetensors"
    lora_strength: float = 0.9

    # Cloudflare R2
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str = "nanobot-v-3"
    r2_endpoint: str           # https://<account_id>.r2.cloudflarestorage.com
    r2_signed_url_expiry: int = 3600

    # Polling
    poll_interval_seconds: int = 5
    poll_timeout_seconds: int = 900

    # Gradio basic auth
    gradio_auth_user: str
    gradio_auth_pass: str


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
