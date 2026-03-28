from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Google Cloud
    gcp_project_id: str = "renci-prod"
    firestore_database: str = "(default)"
    gcs_bucket: str = "renci-assets"

    # App
    app_env: str = "development"
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
