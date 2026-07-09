import os
from sentence_transformers import SentenceTransformer

# Local model path (downloaded via ModelScope)
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "BAAI", "bge-small-zh-v1.5")
_model = None


def _get_model():
    global _model
    if _model is None:
        model_path = os.path.abspath(_MODEL_DIR)
        _model = SentenceTransformer(model_path)
    return _model


async def get_embedding(text: str) -> list[float]:
    return _get_model().encode(text, normalize_embeddings=True).tolist()


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    return _get_model().encode(texts, normalize_embeddings=True).tolist()