from types import SimpleNamespace

from app import config
from app.pipeline import embed


class FakeVoyageClient:
    def __init__(self):
        self.calls = []

    async def embed(self, texts, model=None, input_type=None, truncation=None):
        self.calls.append(
            {"texts": texts, "model": model, "input_type": input_type, "truncation": truncation}
        )
        return SimpleNamespace(embeddings=[[float(len(t))] for t in texts])


async def test_embed_texts_returns_vectors_in_order(monkeypatch):
    fake = FakeVoyageClient()
    monkeypatch.setattr(embed, "get_client", lambda: fake)

    result = await embed.embed_texts(["ab", "abcd"])

    assert result == [[2.0], [4.0]]
    assert fake.calls[0]["model"] == config.EMBED_MODEL
    assert fake.calls[0]["input_type"] == "document"
    assert fake.calls[0]["truncation"] is True


async def test_embed_texts_chunks_large_batches(monkeypatch):
    fake = FakeVoyageClient()
    monkeypatch.setattr(embed, "get_client", lambda: fake)
    texts = [f"text-{i}" for i in range(embed.BATCH_SIZE + 2)]

    result = await embed.embed_texts(texts)

    assert len(result) == embed.BATCH_SIZE + 2
    assert len(fake.calls) == 2
    assert len(fake.calls[0]["texts"]) == embed.BATCH_SIZE
    assert len(fake.calls[1]["texts"]) == 2


async def test_embed_texts_empty_list_makes_no_calls(monkeypatch):
    fake = FakeVoyageClient()
    monkeypatch.setattr(embed, "get_client", lambda: fake)

    result = await embed.embed_texts([])

    assert result == []
    assert fake.calls == []
