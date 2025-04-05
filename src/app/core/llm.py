from autogen_ext.models.ollama import OllamaChatCompletionClient


def get_llm_client():
    client = OllamaChatCompletionClient(model="qwen2.5-coder:14b")
    return client
