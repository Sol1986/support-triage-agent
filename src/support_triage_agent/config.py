import os

from dotenv import load_dotenv

load_dotenv()


def is_llm_enabled() -> bool:
    value = os.getenv("LLM_ENABLED", "false")
    return value.lower().strip() == "true"


def get_gemini_model() -> str:
    return os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash",
    )


def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

    return api_key


def is_database_enabled() -> bool:
    value = os.getenv("DATABASE_ENABLED", "false")
    return value.lower().strip() == "true"


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Add it to the environment.")

    return database_url
