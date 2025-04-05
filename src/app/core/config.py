from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):

    DB_URL: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str
    AWS_BUCKET_NAME: str

    BEDROCK_REGION: str
    BEDROCK_ACCESS_KEY: str
    BEDROCK_SECRET_KEY: str

    WEAVIATE_URL: str
    WEAVIATE_API_KEY: str
    TOP_K: int

    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_EMBEDDINGS_API_KEY: str
    AZURE_OPENAI_API_VERSION: str

    COHERE_MODEL_ID: str
    HUGGINGFACE_API_KEY: str
    HUGGINGFACE_MODEL_NAME: str
    HUGGINGFACE_API_URL: str
    OPENAI_API_KEY: str

    TAVILY: str

    model_config = SettingsConfigDict(
        env_file=Path.cwd() / ".env",
        case_sensitive=True,
        from_attributes=True,
    )


config = Config()  # type:ignore
