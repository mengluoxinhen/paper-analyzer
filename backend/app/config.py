import os
from pathlib import Path
from functools import lru_cache

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env():
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"").strip('"')
            if key and value and key not in os.environ:
                os.environ[key] = value


_load_env()


class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "mysql+asyncmy://root:password@127.0.0.1:3306/paper_analysis")
        self.llm_api_base = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        # MinerU v4 batch upload API
        self.mineru_api_token = os.getenv("MINERU_API_TOKEN", "")
        self.mineru_batch_url = os.getenv("MINERU_BATCH_URL", "https://mineru.net/api/v4/file-urls/batch")
        self.mineru_result_url = os.getenv("MINERU_RESULT_URL", "https://mineru.net/api/v4/extract-results/batch")
        self.mineru_model_version = os.getenv("MINERU_MODEL_VERSION", "vlm")
        self.mineru_poll_interval = float(os.getenv("MINERU_POLL_INTERVAL", "5.0"))
        self.mineru_poll_max_retries = int(os.getenv("MINERU_POLL_MAX_RETRIES", "60"))
        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        if not os.path.isabs(upload_dir):
            upload_dir = os.path.normpath(os.path.join(str(BASE_DIR), upload_dir))
        self.upload_dir = upload_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()

