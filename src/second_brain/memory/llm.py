from langchain_ollama import ChatOllama

from second_brain.config import LLM_MODEL, OLLAMA_BASE_URL


def get_llm(temperature: float = 0.2) -> ChatOllama:
    return ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
    )