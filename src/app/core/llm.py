from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from app.core.config import config


def get_llm_client():
    # client = OllamaChatCompletionClient(model="qwen2.5-coder:14b")
    client = AzureOpenAIChatCompletionClient(
        azure_deployment=config.AZURE_MODEL_NAME,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_API_KEY,
        max_retries=1,
        temperature=0.3,
        model=config.AZURE_MODEL_NAME,
    )

    return client
