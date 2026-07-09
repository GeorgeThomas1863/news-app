import voyageai

from app import config

BATCH_SIZE = 128

_client = None


def get_client():
    global _client
    if _client is None:
        _client = voyageai.AsyncClient(api_key=config.VOYAGE_API_KEY)
    return _client


async def embed_texts(texts):
    """Vectors for texts, in order. Raises on API failure — the runner isolates per stage."""
    if not texts:
        return []

    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        chunk = texts[start : start + BATCH_SIZE]
        result = await get_client().embed(
            chunk, model=config.EMBED_MODEL, input_type="document"
        )
        vectors.extend(result.embeddings)
    return vectors
