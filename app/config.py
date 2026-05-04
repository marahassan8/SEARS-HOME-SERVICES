from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """
    Ensure SQLAlchemy uses psycopg v3 driver.
    Supabase/Vercel commonly provide postgresql:// URLs, which default to psycopg2.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    app_name: str = "SHS Voice Diagnostic Agent"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/shs_voice"
    base_url: str = "http://localhost:8000"
    public_base_url: str = "http://localhost:8000"
    stt_provider: str = "twilio"
    tts_provider: str = "twilio"
    twilio_voice: str = "alice"
    twilio_speech_model: str = "phone_call"

    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    vision_model: str = "gpt-4o-mini"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@shs.local"

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_sms_from: str | None = None

    upload_dir: str = "/tmp/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
