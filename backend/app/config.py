"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider — 'anthropic' or 'openai'
    llm_provider: str = "anthropic"

    # Claude / Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Africa's Talking
    at_username: str = "sandbox"
    at_api_key: str = ""
    at_shortcode: str = "*384*69699#"

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "mbwira-verify"

    # Database
    database_url: str = "sqlite+aiosqlite:///./mbwira.db"

    # App
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    counselor_dashboard_password: str = "changeme"
    emergency_hotline: str = "112"
    isange_hotline: str = "3029"


settings = Settings()
